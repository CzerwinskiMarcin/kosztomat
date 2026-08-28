from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.errors import AppError
from app.models import Comparison, ComparisonMatch
from app.schemas.comparisons import (
    ComparisonCreate,
    ComparisonOut,
    ComparisonSummary,
    FileRef,
    MatchOut,
    MatchSideOut,
)
from app.services.comparisons import comparison_summary, upsert_comparison

router = APIRouter(prefix='/comparisons', tags=['comparisons'])


def _to_out(comparison: Comparison, summary: dict[str, int]) -> ComparisonOut:
    return ComparisonOut(
        id=comparison.id,
        file_a=FileRef(id=comparison.file_a.id, display_name=comparison.file_a.display_name),
        file_b=FileRef(id=comparison.file_b.id, display_name=comparison.file_b.display_name),
        date_tolerance_days=comparison.date_tolerance_days,
        created_at=comparison.created_at,
        summary=ComparisonSummary(**summary),
    )


def _load_comparison(db: Session, comparison_id: int) -> Comparison:
    comparison = db.scalar(
        select(Comparison)
        .options(selectinload(Comparison.file_a), selectinload(Comparison.file_b))
        .where(Comparison.id == comparison_id)
    )
    if comparison is None:
        raise AppError(404, 'Comparison not found', 'COMPARISON_NOT_FOUND')
    return comparison


@router.post('', response_model=ComparisonOut, status_code=201)
def create_comparison(
    payload: ComparisonCreate, db: Session = Depends(get_db)
) -> ComparisonOut:
    comparison = upsert_comparison(
        db,
        payload.file_a_id,
        payload.file_b_id,
        payload.date_tolerance_days,
    )
    return _to_out(comparison, comparison_summary(db, comparison.id))


@router.get('', response_model=list[ComparisonOut])
def list_comparisons(db: Session = Depends(get_db)) -> list[ComparisonOut]:
    rows = list(
        db.scalars(
            select(Comparison)
            .options(selectinload(Comparison.file_a), selectinload(Comparison.file_b))
            .order_by(Comparison.created_at.desc())
        )
    )
    return [_to_out(row, comparison_summary(db, row.id)) for row in rows]


@router.get('/{comparison_id}', response_model=ComparisonOut)
def get_comparison(comparison_id: int, db: Session = Depends(get_db)) -> ComparisonOut:
    comparison = _load_comparison(db, comparison_id)
    return _to_out(comparison, comparison_summary(db, comparison.id))


@router.get('/{comparison_id}/matches', response_model=list[MatchOut])
def list_matches(
    comparison_id: int,
    kind: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    _load_comparison(db, comparison_id)
    query = (
        select(ComparisonMatch)
        .options(
            selectinload(ComparisonMatch.transaction_a),
            selectinload(ComparisonMatch.transaction_b),
        )
        .where(ComparisonMatch.comparison_id == comparison_id)
        .order_by(ComparisonMatch.id)
    )
    if kind:
        query = query.where(ComparisonMatch.kind == kind)
    rows = list(db.scalars(query))

    def side(transaction) -> MatchSideOut | None:
        if transaction is None:
            return None
        return MatchSideOut(
            id=transaction.id,
            booking_date=transaction.booking_date,
            amount=transaction.amount,
            description=transaction.description,
        )

    return [
        MatchOut(
            id=row.id,
            kind=row.kind,
            confidence=row.confidence,
            date_delta_days=row.date_delta_days,
            amount=row.amount,
            a=side(row.transaction_a),
            b=side(row.transaction_b),
        )
        for row in rows
    ]


@router.delete('/{comparison_id}', status_code=204)
def delete_comparison(comparison_id: int, db: Session = Depends(get_db)) -> None:
    comparison = _load_comparison(db, comparison_id)
    db.delete(comparison)
    db.commit()
