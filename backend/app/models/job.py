"""Job postings found by a headhunter for a candidate."""
from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDMixin, str_enum

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class JobStatus(enum.StrEnum):
    # Candidate-side progress...
    new = "new"
    interested = "interested"
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"
    not_interested = "not_interested"
    # ...and headhunter-side availability.
    expired = "expired"
    unavailable = "unavailable"


class EmploymentType(enum.StrEnum):
    permanent = "permanent"
    contract = "contract"
    contract_to_hire = "contract_to_hire"
    part_time = "part_time"
    temporary = "temporary"
    internship = "internship"
    freelance = "freelance"
    other = "other"


class WorkMode(enum.StrEnum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    # One posting per apply link per candidate (create_job reports duplicates).
    __table_args__ = (
        UniqueConstraint("candidate_id", "apply_url", name="uq_jobs_candidate_apply_url"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    apply_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), nullable=False, default=JobStatus.new, index=True
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        str_enum(EmploymentType, "employment_type"), nullable=True
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    work_mode: Mapped[WorkMode | None] = mapped_column(
        str_enum(WorkMode, "work_mode"), nullable=True
    )
    compensation: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    date_found: Mapped[date] = mapped_column(Date, nullable=False)
    schedule: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Headhunter's 1-5 evaluation of how well the role fits the candidate.
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    candidate: Mapped["User"] = relationship(foreign_keys=[candidate_id], lazy="selectin")
    optimized_resume: Mapped["Document | None"] = relationship(
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def candidate_name(self) -> str:
        return self.candidate.display_name if self.candidate else ""
