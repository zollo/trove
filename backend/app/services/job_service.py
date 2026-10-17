"""Job postings: listing, creation, updates and permissions."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.models.job import EmploymentType, Job, JobStatus, WorkMode
from app.models.profile import SalaryPeriod
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate
from app.schemas.meta import JobOptions, Option
from app.services import candidate_service

# Fields a candidate may change on their own jobs.
CANDIDATE_EDITABLE = {"status", "notes"}


def _label(value: str) -> str:
    return value.replace("_", " ").capitalize().replace("Onsite", "On-site")


def _options(enum_cls) -> list[Option]:
    return [Option(value=m.value, label=_label(m.value)) for m in enum_cls]


async def job_options(db: AsyncSession) -> JobOptions:
    result = await db.execute(
        select(Job.category).where(Job.category != "").distinct().order_by(Job.category)
    )
    return JobOptions(
        statuses=_options(JobStatus),
        employment_types=_options(EmploymentType),
        work_modes=_options(WorkMode),
        salary_periods=_options(SalaryPeriod),
        categories=list(result.scalars()),
    )


async def list_jobs(
    db: AsyncSession,
    actor: User,
    *,
    candidate_id: str | uuid.UUID | None = None,
    status: list[JobStatus] | None = None,
    q: str | None = None,
) -> list[Job]:
    stmt = select(Job)
    if not actor.is_headhunter:
        stmt = stmt.where(Job.candidate_id == actor.id)
    elif candidate_id:
        candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
        stmt = stmt.where(Job.candidate_id == candidate.id)
    if status:
        stmt = stmt.where(Job.status.in_(status))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Job.title).like(like),
                func.lower(Job.company).like(like),
                func.lower(Job.location).like(like),
                func.lower(Job.category).like(like),
            )
        )
    stmt = stmt.order_by(Job.date_found.desc(), Job.created_at.desc())
    return list((await db.execute(stmt)).scalars())


async def get_job(db: AsyncSession, actor: User, job_id: uuid.UUID) -> Job:
    job = await db.get(Job, job_id)
    if job is None or (not actor.is_headhunter and job.candidate_id != actor.id):
        raise NotFound("Job not found")
    return job


async def create_job(db: AsyncSession, actor: User, payload: JobCreate) -> Job:
    if not actor.is_headhunter:
        raise Forbidden("Only headhunters can post jobs")
    candidate = await candidate_service.resolve_candidate(db, actor, payload.candidate_id)

    # Guard against an AI headhunter posting the same opening twice.
    dup = await db.execute(
        select(Job.id).where(Job.candidate_id == candidate.id, Job.apply_url == payload.apply_url)
    )
    existing = dup.scalar_one_or_none()
    if existing:
        raise Conflict(f"This candidate already has a job with that apply_url (id {existing})")

    data = payload.model_dump(exclude={"candidate_id"})
    data["date_found"] = data["date_found"] or date.today()
    job = Job(candidate_id=candidate.id, created_by_id=actor.id, **data)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job(db: AsyncSession, actor: User, job_id: uuid.UUID, payload: JobUpdate) -> Job:
    job = await get_job(db, actor, job_id)
    changes = payload.model_dump(exclude_unset=True)
    if not actor.is_headhunter:
        blocked = set(changes) - CANDIDATE_EDITABLE
        if blocked:
            raise Forbidden(f"Candidates can only change {', '.join(sorted(CANDIDATE_EDITABLE))}")
    for required in ("title", "apply_url", "status", "date_found"):
        if required in changes and changes[required] is None:
            raise Invalid(f"{required} cannot be null")
    for field, value in changes.items():
        if isinstance(value, str) and field not in ("notes",):
            value = value.strip()
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, actor: User, job_id: uuid.UUID) -> None:
    if not actor.is_headhunter:
        raise Forbidden("Only headhunters can delete jobs")
    job = await get_job(db, actor, job_id)
    await db.delete(job)
    await db.commit()
