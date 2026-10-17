"""Candidate search-preference schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.job import EmploymentType, WorkMode
from app.models.profile import SalaryPeriod
from app.schemas.document import DocumentRead


def _clean(values: list[str]) -> list[str]:
    seen: list[str] = []
    for v in values:
        v = v.strip()
        if v and v not in seen:
            seen.append(v)
    return seen


class ProfileBase(BaseModel):
    headline: str = Field(default="", max_length=255, description="One-line summary.")
    desired_titles: list[str] = Field(default_factory=list, description="Job titles sought.")
    job_categories: list[str] = Field(default_factory=list, description="e.g. Engineering.")
    employment_types: list[EmploymentType] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list, description="Preferred locations.")
    work_modes: list[WorkMode] = Field(default_factory=list)
    willing_to_relocate: bool = False
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(
        default="USD", pattern=r"^[A-Za-z]{3}$", description="ISO 4217 code, e.g. USD."
    )
    salary_period: SalaryPeriod = SalaryPeriod.year
    notes: str = Field(default="", max_length=10000, description="Must-haves, deal-breakers…")


class ProfileUpdate(ProfileBase):
    @model_validator(mode="after")
    def _normalise(self) -> ProfileUpdate:
        self.desired_titles = _clean(self.desired_titles)
        self.job_categories = _clean(self.job_categories)
        self.locations = _clean(self.locations)
        self.salary_currency = self.salary_currency.upper()
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        return self


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime | None = None


class CandidateSummary(BaseModel):
    """A candidate as a headhunter sees them in a list."""

    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    headline: str = ""
    has_base_resume: bool = False
    job_count: int = 0
    open_job_count: int = 0


class CandidateDetail(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    profile: ProfileRead
    base_resume: DocumentRead | None = None
