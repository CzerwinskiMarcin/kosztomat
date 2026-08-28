from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money
from app.schemas.profiles import ProfileOut


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    original_filename: str
    byte_size: int
    checksum_sha256: str
    profile_id: int | None
    status: str
    row_count: int
    error_message: str | None
    uploaded_at: datetime
    imported_at: datetime | None
    profile: ProfileOut | None = None
    duplicate_of_file_id: int | None = None


class FilePatch(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)


class PreviewOut(BaseModel):
    encoding: str
    delimiter: str
    has_header: bool
    skip_rows: int
    headers: list[str]
    rows: list[list[str]]
    row_count: int
    detected_encoding: str
    detected_delimiter: str


class ImportErrorItem(BaseModel):
    row_index: int
    message: str


class ImportResult(BaseModel):
    file: FileOut
    errors: list[ImportErrorItem] = []


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_index: int
    booking_date: date
    amount: Money
    description: str | None
    raw_payload: dict[str, Any]


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    offset: int
    limit: int
