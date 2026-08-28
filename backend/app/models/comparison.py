from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.source_file import SourceFile
    from app.models.transaction import Transaction


class Comparison(Base):
    __tablename__ = 'comparisons'
    __table_args__ = (UniqueConstraint('file_a_id', 'file_b_id', name='uq_comparison_pair'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_a_id: Mapped[int] = mapped_column(
        ForeignKey('source_files.id', ondelete='CASCADE'), nullable=False
    )
    file_b_id: Mapped[int] = mapped_column(
        ForeignKey('source_files.id', ondelete='CASCADE'), nullable=False
    )
    date_tolerance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    file_a: Mapped['SourceFile'] = relationship(foreign_keys=[file_a_id])
    file_b: Mapped['SourceFile'] = relationship(foreign_keys=[file_b_id])
    matches: Mapped[list['ComparisonMatch']] = relationship(
        back_populates='comparison', cascade='all, delete-orphan'
    )


class ComparisonMatch(Base):
    __tablename__ = 'comparison_matches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparison_id: Mapped[int] = mapped_column(
        ForeignKey('comparisons.id', ondelete='CASCADE'), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_a_id: Mapped[int | None] = mapped_column(
        ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True
    )
    transaction_b_id: Mapped[int | None] = mapped_column(
        ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True
    )
    date_delta_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    comparison: Mapped[Comparison] = relationship(back_populates='matches')
    transaction_a: Mapped['Transaction | None'] = relationship(foreign_keys=[transaction_a_id])
    transaction_b: Mapped['Transaction | None'] = relationship(foreign_keys=[transaction_b_id])
