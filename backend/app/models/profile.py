from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


class SourceProfile(Base):
    __tablename__ = 'source_profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    delimiter: Mapped[str] = mapped_column(String(8), nullable=False, default=';')
    encoding: Mapped[str] = mapped_column(String(40), nullable=False, default='utf-8-sig')
    has_header: Mapped[bool] = mapped_column(nullable=False, default=True)
    skip_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decimal_separator: Mapped[str] = mapped_column(String(4), nullable=False, default=',')
    thousand_separator: Mapped[str] = mapped_column(String(4), nullable=False, default=' ')
    date_format: Mapped[str] = mapped_column(String(40), nullable=False, default='%d.%m.%Y')
    amount_mode: Mapped[str] = mapped_column(String(16), nullable=False, default='signed')
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[list['SourceFile']] = relationship(back_populates='profile')  # noqa: F821
