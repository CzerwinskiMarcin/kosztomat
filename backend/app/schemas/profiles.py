from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ColumnMapping(BaseModel):
    booking_date: str | int
    amount: str | int | None = None
    description: str | int | None = None
    amount_debit: str | int | None = None
    amount_credit: str | int | None = None


class ProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    delimiter: str = ';'
    encoding: str = 'utf-8-sig'
    has_header: bool = True
    skip_rows: int = Field(default=0, ge=0)
    decimal_separator: str = ','
    thousand_separator: str = ' '
    date_format: str = '%d.%m.%Y'
    amount_mode: Literal['signed', 'absolute'] = 'signed'
    column_mapping: dict[str, Any]


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ImportConfig(BaseModel):
    delimiter: str = ';'
    encoding: str = 'utf-8-sig'
    has_header: bool = True
    skip_rows: int = Field(default=0, ge=0)
    decimal_separator: str = ','
    thousand_separator: str = ' '
    date_format: str = '%d.%m.%Y'
    amount_mode: Literal['signed', 'absolute'] = 'signed'
    column_mapping: dict[str, Any]


class SaveAsProfile(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class FileImportRequest(BaseModel):
    profile_id: int | None = None
    config: ImportConfig | None = None
    save_as_profile: SaveAsProfile | None = None
