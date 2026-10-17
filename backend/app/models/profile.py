"""A candidate's job-search preferences."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import JSONType, str_enum

if TYPE_CHECKING:
    from app.models.user import User


class SalaryPeriod(enum.StrEnum):
    year = "year"
    hour = "hour"


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    headline: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Lists of free-text values (titles, categories, locations) or enum values
    # (employment types, work modes); see schemas/profile.py.
    desired_titles: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    job_categories: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    employment_types: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    locations: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    work_modes: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    salary_period: Mapped[SalaryPeriod] = mapped_column(
        str_enum(SalaryPeriod, "salary_period"), nullable=False, default=SalaryPeriod.year
    )

    # Anything else the headhunter should know (must-haves, deal-breakers...).
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="profile")
