"""Candidates: access control, listing, and search preferences.

Headhunters can see and act for every candidate; a candidate only for themself.
Anywhere a candidate id is accepted, the literal "me" means the caller.
"""
from __future__ import annotations

import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, Invalid, NotFound
from app.models.document import Document, DocumentKind
from app.models.job import Job, JobStatus
from app.models.profile import CandidateProfile
from app.models.user import User, UserRole
from app.schemas.document import DocumentRead
from app.schemas.profile import CandidateDetail, CandidateSummary, ProfileRead, ProfileUpdate

# Statuses that mean "nothing more to do here".
CLOSED_STATUSES = (
    JobStatus.rejected,
    JobStatus.not_interested,
    JobStatus.expired,
    JobStatus.unavailable,
)


async def resolve_candidate(db: AsyncSession, actor: User, ref: str | uuid.UUID) -> User:
    """Load the candidate `ref` points at, enforcing access for `actor`."""
    if isinstance(ref, str) and ref == "me":
        candidate_id = actor.id
    else:
        try:
            candidate_id = ref if isinstance(ref, uuid.UUID) else uuid.UUID(str(ref))
        except ValueError as exc:
            raise Invalid("candidate_id must be a UUID or 'me'") from exc

    if not actor.is_headhunter and candidate_id != actor.id:
        raise Forbidden("Candidates can only access their own data")
    candidate = await db.get(User, candidate_id)
    if candidate is None or candidate.role != UserRole.candidate:
        raise NotFound("Candidate not found")
    return candidate


async def ensure_profile(db: AsyncSession, candidate: User) -> CandidateProfile:
    if candidate.profile is None:
        candidate.profile = CandidateProfile()
        await db.commit()
        await db.refresh(candidate)
    assert candidate.profile is not None
    return candidate.profile


async def get_base_resume_meta(db: AsyncSession, candidate_id: uuid.UUID) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.candidate_id == candidate_id, Document.kind == DocumentKind.base_resume
        )
    )
    return result.scalar_one_or_none()


async def get_detail(db: AsyncSession, candidate: User) -> CandidateDetail:
    profile = await ensure_profile(db, candidate)
    resume = await get_base_resume_meta(db, candidate.id)
    return CandidateDetail(
        id=candidate.id,
        email=candidate.email,
        display_name=candidate.display_name,
        is_active=candidate.is_active,
        profile=ProfileRead.model_validate(profile),
        base_resume=DocumentRead.model_validate(resume) if resume else None,
    )


async def update_profile(
    db: AsyncSession, candidate: User, payload: ProfileUpdate
) -> ProfileRead:
    profile = await ensure_profile(db, candidate)
    for field, value in payload.model_dump(mode="json").items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return ProfileRead.model_validate(profile)


async def list_candidates(
    db: AsyncSession, include_inactive: bool = False
) -> list[CandidateSummary]:
    job_counts = (
        select(
            Job.candidate_id.label("cid"),
            func.count(Job.id).label("total"),
            func.sum(case((Job.status.in_(CLOSED_STATUSES), 0), else_=1)).label("open"),
        )
        .group_by(Job.candidate_id)
        .subquery()
    )
    resumes = (
        select(Document.candidate_id.label("cid"))
        .where(Document.kind == DocumentKind.base_resume)
        .subquery()
    )
    stmt = (
        select(
            User,
            func.coalesce(job_counts.c.total, 0),
            func.coalesce(job_counts.c.open, 0),
            resumes.c.cid.is_not(None),
        )
        .outerjoin(job_counts, job_counts.c.cid == User.id)
        .outerjoin(resumes, resumes.c.cid == User.id)
        .where(User.role == UserRole.candidate)
        .order_by(func.lower(User.display_name))
    )
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    rows = (await db.execute(stmt)).all()
    return [
        CandidateSummary(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            headline=user.profile.headline if user.profile else "",
            has_base_resume=bool(has_resume),
            job_count=int(total),
            open_job_count=int(open_),
        )
        for user, total, open_, has_resume in rows
    ]
