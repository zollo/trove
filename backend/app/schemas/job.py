"""Job posting schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job import EmploymentType, JobStatus, WorkMode
from app.schemas.document import DocumentRead

# Shared field definitions so create/update/read stay in sync.
_TITLE = Field(min_length=1, max_length=255, description="Role name / job title.")
_APPLY_URL = Field(min_length=1, max_length=2048, description="Where the candidate applies.")
_FIT = Field(default=None, ge=1, le=5, description="Job-fit score, 1 (poor) to 5 (great).")


def _check_url(v: str | None) -> str | None:
    if v is not None and not v.lower().startswith(("http://", "https://", "mailto:")):
        raise ValueError("apply_url must start with http://, https:// or mailto:")
    return v


class JobCreate(BaseModel):
    candidate_id: uuid.UUID = Field(description="The candidate this posting is for.")
    title: str = _TITLE
    apply_url: str = _APPLY_URL
    company: str = Field(default="", max_length=255)
    status: JobStatus = JobStatus.new
    category: str = Field(default="", max_length=120, description="Job category, e.g. Engineering.")
    employment_type: EmploymentType | None = None
    location: str = Field(default="", max_length=255)
    work_mode: WorkMode | None = None
    compensation: str = Field(default="", max_length=255, description="e.g. $150k-$180k + bonus.")
    date_found: date | None = Field(default=None, description="Defaults to today.")
    schedule: str = Field(default="", max_length=255, description="Shift / schedule.")
    fit_score: int | None = _FIT
    notes: str = Field(default="", max_length=20000)

    _url = field_validator("apply_url")(_check_url)


class JobUpdate(BaseModel):
    """Partial update: only the fields sent are changed.

    Candidates may change `status` and `notes`; headhunters may change everything.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    apply_url: str | None = Field(default=None, min_length=1, max_length=2048)
    company: str | None = Field(default=None, max_length=255)
    status: JobStatus | None = None
    category: str | None = Field(default=None, max_length=120)
    employment_type: EmploymentType | None = None
    location: str | None = Field(default=None, max_length=255)
    work_mode: WorkMode | None = None
    compensation: str | None = Field(default=None, max_length=255)
    date_found: date | None = None
    schedule: str | None = Field(default=None, max_length=255)
    fit_score: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=20000)

    _url = field_validator("apply_url")(_check_url)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str = ""
    title: str
    company: str
    apply_url: str
    status: JobStatus
    category: str
    employment_type: EmploymentType | None
    location: str
    work_mode: WorkMode | None
    compensation: str
    date_found: date
    schedule: str
    fit_score: int | None
    notes: str
    optimized_resume: DocumentRead | None = None
    created_at: datetime
    updated_at: datetime
