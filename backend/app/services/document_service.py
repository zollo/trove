"""Storing and fetching resumes (base and per-job optimized)."""
from __future__ import annotations

import base64
import binascii

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.config import settings
from app.core import resume_text
from app.core.errors import Invalid, NotFound, TooLarge
from app.models.document import Document, DocumentKind
from app.models.job import Job
from app.models.user import User
from app.schemas.document import DocumentContent


def _validate(filename: str, data: bytes) -> str:
    name = resume_text.safe_filename(filename)
    if not resume_text.is_allowed(name):
        allowed = ", ".join(sorted(resume_text.ALLOWED_TYPES))
        raise Invalid(f"Unsupported file type. Allowed: {allowed}")
    if not data:
        raise Invalid("The file is empty")
    if len(data) > settings.max_upload_bytes:
        raise TooLarge(f"File exceeds the {settings.max_upload_mb} MB limit")
    return name


def decode_payload(
    filename: str, content_text: str | None, content_base64: str | None
) -> tuple[str, bytes]:
    """Turn API/MCP JSON upload fields into (filename, bytes)."""
    if (content_text is None) == (content_base64 is None):
        raise Invalid("Provide exactly one of content_text or content_base64")
    if content_text is not None:
        if not resume_text.is_allowed(filename):
            filename = f"{filename or 'resume'}.md"
        return filename, content_text.encode("utf-8")
    try:
        return filename, base64.b64decode(content_base64 or "", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise Invalid("content_base64 is not valid base64") from exc


async def _load(db: AsyncSession, stmt) -> Document | None:
    result = await db.execute(stmt.options(undefer(Document.data), undefer(Document.text_content)))
    return result.scalar_one_or_none()


async def _store(
    db: AsyncSession,
    existing: Document | None,
    *,
    kind: DocumentKind,
    candidate_id,
    job_id,
    uploader: User,
    filename: str,
    data: bytes,
) -> Document:
    name = _validate(filename, data)
    doc = existing or Document(kind=kind, candidate_id=candidate_id, job_id=job_id)
    doc.filename = name
    doc.content_type = resume_text.content_type_for(name)
    doc.size_bytes = len(data)
    doc.data = data
    doc.text_content = resume_text.extract_text(name, data)
    doc.uploaded_by_id = uploader.id
    if existing is None:
        db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


def base_resume_stmt(candidate_id):
    return select(Document).where(
        Document.candidate_id == candidate_id, Document.kind == DocumentKind.base_resume
    )


def optimized_resume_stmt(job_id):
    return select(Document).where(
        Document.job_id == job_id, Document.kind == DocumentKind.optimized_resume
    )


async def save_base_resume(
    db: AsyncSession, candidate: User, uploader: User, filename: str, data: bytes
) -> Document:
    existing = await _load(db, base_resume_stmt(candidate.id))
    return await _store(
        db,
        existing,
        kind=DocumentKind.base_resume,
        candidate_id=candidate.id,
        job_id=None,
        uploader=uploader,
        filename=filename,
        data=data,
    )


async def get_base_resume(db: AsyncSession, candidate: User) -> Document:
    doc = await _load(db, base_resume_stmt(candidate.id))
    if doc is None:
        raise NotFound("This candidate has not uploaded a base resume yet")
    return doc


async def delete_base_resume(db: AsyncSession, candidate: User) -> None:
    doc = await get_base_resume(db, candidate)
    await db.delete(doc)
    await db.commit()


async def save_optimized_resume(
    db: AsyncSession, job: Job, uploader: User, filename: str, data: bytes
) -> Document:
    existing = await _load(db, optimized_resume_stmt(job.id))
    doc = await _store(
        db,
        existing,
        kind=DocumentKind.optimized_resume,
        candidate_id=job.candidate_id,
        job_id=job.id,
        uploader=uploader,
        filename=filename,
        data=data,
    )
    await db.refresh(job)
    return doc


async def get_optimized_resume(db: AsyncSession, job: Job) -> Document:
    doc = await _load(db, optimized_resume_stmt(job.id))
    if doc is None:
        raise NotFound("No optimized resume has been uploaded for this job")
    return doc


async def delete_optimized_resume(db: AsyncSession, job: Job) -> None:
    doc = await get_optimized_resume(db, job)
    await db.delete(doc)
    await db.commit()


def to_content(doc: Document, include_file: bool) -> DocumentContent:
    out = DocumentContent.model_validate(doc)
    out.text_content = doc.text_content
    if include_file:
        out.content_base64 = base64.b64encode(doc.data).decode()
    return out
