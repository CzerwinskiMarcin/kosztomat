from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class FileRef(BaseModel):
    id: int
    display_name: str


class ComparisonCreate(BaseModel):
    file_a_id: int
    file_b_id: int
    date_tolerance_days: int = Field(default=7, ge=0, le=365)


class ComparisonSummary(BaseModel):
    exact: int
    probable: int
    unmatched_a: int
    unmatched_b: int
    total_a: int
    total_b: int


class ComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_a: FileRef
    file_b: FileRef
    date_tolerance_days: int
    created_at: datetime
    summary: ComparisonSummary


class MatchSideOut(BaseModel):
    id: int
    booking_date: date
    amount: Money
    description: str | None


class MatchOut(BaseModel):
    id: int
    kind: str
    confidence: int
    date_delta_days: int | None
    amount: Money
    a: MatchSideOut | None
    b: MatchSideOut | None
