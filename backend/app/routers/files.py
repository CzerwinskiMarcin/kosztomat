from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.models import Comparison, SourceFile, SourceProfile, Transaction
from app.schemas.files import (
    FileOut,
    FilePatch,
    ImportErrorItem,
    ImportResult,
    PreviewOut,
    TransactionOut,
    TransactionPage,
)
from app.schemas.profiles import FileImportRequest
from app.services import storage
from app.services.csv_import import parse_transactions, preview_csv, read_file_bytes

router = APIRouter(prefix='/files', tags=['files'])


def _file_out(source_file: SourceFile, duplicate_of_file_id: int | None = None) -> FileOut:
    return FileOut.model_validate(source_file).model_copy(
        update={'duplicate_of_file_id': duplicate_of_file_id}
    )


def _get_file(db: Session, file_id: int) -> SourceFile:
    source_file = db.scalar(
        select(SourceFile)
        .options(selectinload(SourceFile.profile))
        .where(SourceFile.id == file_id)
    )
    if source_file is None:
        raise AppError(404, 'File not found', 'FILE_NOT_FOUND')
    return source_file


@router.get('', response_model=list[FileOut])
def list_files(db: Session = Depends(get_db)) -> list[FileOut]:
    rows = db.scalars(
        select(SourceFile)
        .options(selectinload(SourceFile.profile))
        .order_by(SourceFile.uploaded_at.desc())
    )
    return [_file_out(row) for row in rows]


@router.post('', response_model=FileOut, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> FileOut:
    filename = Path(file.filename or 'upload.csv').name
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.csv', '.txt'}:
        raise AppError(400, 'Only .csv and .txt files are accepted', 'INVALID_FILE_TYPE')

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise AppError(413, 'File is larger than 10 MB', 'FILE_TOO_LARGE')
    if not content:
        raise AppError(400, 'File is empty', 'EMPTY_FILE')

    checksum = storage.sha256_bytes(content)
    duplicate = db.scalar(
        select(SourceFile).where(SourceFile.checksum_sha256 == checksum).limit(1)
    )

    source_file = SourceFile(
        display_name=filename,
        original_filename=filename,
        stored_path='',
        byte_size=len(content),
        checksum_sha256=checksum,
        status='uploaded',
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(source_file)
    db.flush()
    source_file.stored_path = storage.write_upload(source_file.id, filename, content)
    db.commit()
    source_file = _get_file(db, source_file.id)
    return _file_out(source_file, duplicate.id if duplicate else None)


@router.get('/{file_id}', response_model=FileOut)
def get_file(file_id: int, db: Session = Depends(get_db)) -> FileOut:
    return _file_out(_get_file(db, file_id))


@router.patch('/{file_id}', response_model=FileOut)
def rename_file(file_id: int, payload: FilePatch, db: Session = Depends(get_db)) -> FileOut:
    source_file = _get_file(db, file_id)
    source_file.display_name = payload.display_name
    db.commit()
    return _file_out(_get_file(db, file_id))


@router.delete('/{file_id}', status_code=204)
def delete_file(file_id: int, db: Session = Depends(get_db)) -> None:
    source_file = _get_file(db, file_id)
    comparisons = list(
        db.scalars(
            select(Comparison).where(
                or_(Comparison.file_a_id == file_id, Comparison.file_b_id == file_id)
            )
        )
    )
    for comparison in comparisons:
        db.delete(comparison)
    relative_path = source_file.stored_path
    db.delete(source_file)
    db.commit()
    storage.delete_upload(relative_path)


@router.get('/{file_id}/preview', response_model=PreviewOut)
def preview_file(
    file_id: int,
    encoding: str | None = None,
    delimiter: str | None = None,
    skip_rows: int = Query(default=0, ge=0),
    has_header: bool = True,
    db: Session = Depends(get_db),
) -> PreviewOut:
    source_file = _get_file(db, file_id)
    content = read_file_bytes(storage.absolute_path(source_file.stored_path))
    payload = preview_csv(
        content,
        encoding=encoding,
        delimiter=delimiter,
        has_header=has_header,
        skip_rows=skip_rows,
    )
    return PreviewOut(**payload)


@router.post('/{file_id}/import', response_model=ImportResult)
def import_file(
    file_id: int,
    payload: FileImportRequest,
    db: Session = Depends(get_db),
) -> ImportResult:
    source_file = _get_file(db, file_id)
    if payload.profile_id is not None:
        profile = db.get(SourceProfile, payload.profile_id)
        if profile is None:
            raise AppError(404, 'Profile not found', 'PROFILE_NOT_FOUND')
        config = {
            'delimiter': profile.delimiter,
            'encoding': profile.encoding,
            'has_header': profile.has_header,
            'skip_rows': profile.skip_rows,
            'decimal_separator': profile.decimal_separator,
            'thousand_separator': profile.thousand_separator,
            'date_format': profile.date_format,
            'amount_mode': profile.amount_mode,
            'column_mapping': profile.column_mapping,
        }
        profile_id = profile.id
    elif payload.config is not None:
        config = payload.config.model_dump()
        profile_id = None
        if payload.save_as_profile is not None:
            existing = db.scalar(
                select(SourceProfile).where(SourceProfile.name == payload.save_as_profile.name)
            )
            if existing is not None:
                raise AppError(400, 'A profile with this name already exists', 'PROFILE_NAME_TAKEN')
            profile = SourceProfile(name=payload.save_as_profile.name, **config)
            db.add(profile)
            db.flush()
            profile_id = profile.id
    else:
        raise AppError(400, 'Provide profile_id or config', 'IMPORT_CONFIG_REQUIRED')

    content = read_file_bytes(storage.absolute_path(source_file.stored_path))
    try:
        parsed, errors = parse_transactions(content, **config)
    except ValueError as exc:
        source_file.status = 'failed'
        source_file.error_message = str(exc)
        db.commit()
        raise AppError(400, str(exc), 'IMPORT_FAILED') from exc

    if errors:
        source_file.status = 'failed'
        source_file.error_message = errors[0].message
        db.commit()
        return ImportResult(
            file=_file_out(_get_file(db, file_id)),
            errors=[
                ImportErrorItem(row_index=item.row_index, message=item.message)
                for item in errors[:20]
            ],
        )

    db.execute(delete(Transaction).where(Transaction.source_file_id == file_id))
    for row in parsed:
        db.add(
            Transaction(
                source_file_id=file_id,
                row_index=row.row_index,
                booking_date=row.booking_date,
                amount=row.amount,
                amount_abs=abs(row.amount),
                description=row.description,
                raw_payload=row.raw_payload,
            )
        )
    source_file.status = 'imported'
    source_file.row_count = len(parsed)
    source_file.error_message = None
    source_file.profile_id = profile_id
    source_file.imported_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return ImportResult(file=_file_out(_get_file(db, file_id)), errors=[])


@router.get('/{file_id}/transactions', response_model=TransactionPage)
def list_transactions(
    file_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    q: str | None = None,
    db: Session = Depends(get_db),
) -> TransactionPage:
    _get_file(db, file_id)
    filters = [Transaction.source_file_id == file_id]
    if q:
        filters.append(Transaction.description.ilike(f'%{q}%'))
    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    rows = list(
        db.scalars(
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.row_index)
            .offset(offset)
            .limit(limit)
        )
    )
    return TransactionPage(
        items=[TransactionOut.model_validate(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )
