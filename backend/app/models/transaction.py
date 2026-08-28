from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base

if TYPE_CHECKING:
    from app.models.source_file import SourceFile


class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = (
        Index('ix_transactions_file_amount_date', 'source_file_id', 'amount_abs', 'booking_date'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_file_id: Mapped[int] = mapped_column(
        ForeignKey('source_files.id', ondelete='CASCADE'), nullable=False, index=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_abs: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    source_file: Mapped['SourceFile'] = relationship(back_populates='transactions')
