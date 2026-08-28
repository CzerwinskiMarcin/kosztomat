from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Comparison, ComparisonMatch, SourceFile, Transaction
from app.services.matching import MatchInput, match_transactions


def _require_imported_file(session: Session, file_id: int) -> SourceFile:
    source_file = session.get(SourceFile, file_id)
    if source_file is None:
        raise AppError(404, f'File {file_id} not found', 'FILE_NOT_FOUND')
    if source_file.status != 'imported':
        raise AppError(409, f'File {file_id} is not imported', 'FILE_NOT_IMPORTED')
    return source_file


def _to_inputs(rows: list[Transaction]) -> list[MatchInput]:
    return [
        MatchInput(
            id=row.id,
            row_index=row.row_index,
            booking_date=row.booking_date,
            amount_abs=row.amount_abs,
        )
        for row in rows
    ]


def comparison_summary(session: Session, comparison_id: int) -> dict[str, int]:
    counts = dict(
        session.execute(
            select(ComparisonMatch.kind, func.count())
            .where(ComparisonMatch.comparison_id == comparison_id)
            .group_by(ComparisonMatch.kind)
        ).all()
    )
    exact = counts.get('exact', 0)
    probable = counts.get('probable', 0)
    unmatched_a = counts.get('unmatched_a', 0)
    unmatched_b = counts.get('unmatched_b', 0)
    return {
        'exact': exact,
        'probable': probable,
        'unmatched_a': unmatched_a,
        'unmatched_b': unmatched_b,
        'total_a': exact + probable + unmatched_a,
        'total_b': exact + probable + unmatched_b,
    }


def upsert_comparison(
    session: Session,
    file_a_id: int,
    file_b_id: int,
    date_tolerance_days: int = 7,
) -> Comparison:
    if file_a_id == file_b_id:
        raise AppError(400, 'Cannot compare a file with itself', 'SAME_FILE')

    _require_imported_file(session, file_a_id)
    _require_imported_file(session, file_b_id)

    existing = session.scalar(
        select(Comparison).where(
            Comparison.file_a_id == file_a_id,
            Comparison.file_b_id == file_b_id,
        )
    )
    if existing is not None:
        session.execute(delete(ComparisonMatch).where(ComparisonMatch.comparison_id == existing.id))
        session.delete(existing)
        session.flush()

    rows_a = list(
        session.scalars(
            select(Transaction)
            .where(Transaction.source_file_id == file_a_id)
            .order_by(Transaction.row_index)
        )
    )
    rows_b = list(
        session.scalars(
            select(Transaction)
            .where(Transaction.source_file_id == file_b_id)
            .order_by(Transaction.row_index)
        )
    )

    outcomes = match_transactions(_to_inputs(rows_a), _to_inputs(rows_b), date_tolerance_days)
    comparison = Comparison(
        file_a_id=file_a_id,
        file_b_id=file_b_id,
        date_tolerance_days=date_tolerance_days,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(comparison)
    session.flush()

    for outcome in outcomes:
        session.add(
            ComparisonMatch(
                comparison_id=comparison.id,
                kind=outcome.kind,
                confidence=outcome.confidence,
                transaction_a_id=outcome.transaction_a_id,
                transaction_b_id=outcome.transaction_b_id,
                date_delta_days=outcome.date_delta_days,
                amount=outcome.amount,
            )
        )
    session.commit()
    return session.scalar(
        select(Comparison)
        .options(selectinload(Comparison.file_a), selectinload(Comparison.file_b))
        .where(Comparison.id == comparison.id)
    )
