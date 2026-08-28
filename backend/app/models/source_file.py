from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.profile import SourceProfile
    from app.models.transaction import Transaction


class SourceFile(Base):
    __tablename__ = 'source_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey('source_profiles.id', ondelete='SET NULL'), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='uploaded')
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped['SourceProfile | None'] = relationship(back_populates='files')
    transactions: Mapped[list['Transaction']] = relationship(
        back_populates='source_file', cascade='all, delete-orphan'
    )
