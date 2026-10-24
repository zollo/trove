"""Job postings and their per-job optimized resumes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_headhunter, get_current_user
from app.api.files import read_upload, send_file
from app.core.resume_export import ExportFormat
from app.db import get_db
from app.models.job import JobStatus
from app.models.user import User
from app.schemas.document import DocumentContent, DocumentRead
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.schemas.meta import JobOptions
from app.services import document_service, job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


class ResumeTextUpload(BaseModel):
    """JSON alternative to the multipart upload, convenient for AI tools."""

    filename: str = Field(default="optimized-resume.md", max_length=255)
    content_text: str | None = Field(default=None, description="Resume as Markdown/plain text.")
    content_base64: str | None = Field(default=None, description="A binary file (PDF/DOCX).")


@router.get("/options", response_model=JobOptions, operation_id="get_job_options")
async def job_options(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> JobOptions:
    """Allowed values for status, employment type and work mode, plus categories in use."""
    return await job_service.job_options(db)


@router.get("", response_model=list[JobRead], operation_id="list_jobs")
async def list_jobs(
    candidate_id: str | None = Query(None, description="Headhunters: filter by candidate."),
    status_: list[JobStatus] | None = Query(None, alias="status"),
    q: str | None = Query(None, description="Search title, company, location, category."),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Jobs visible to the caller: a candidate's own, or all for headhunters."""
    return await job_service.list_jobs(db, actor, candidate_id=candidate_id, status=status_, q=q)


@router.post(
    "", response_model=JobRead, status_code=status.HTTP_201_CREATED, operation_id="create_job"
)
async def create_job(
    payload: JobCreate,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    """Post a job for a candidate. 409 if that candidate already has the same apply_url."""
    return await job_service.create_job(db, actor, payload)


@router.get("/{job_id}", response_model=JobRead, operation_id="get_job")
async def get_job(
    job_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.get_job(db, actor, job_id)


@router.patch("/{job_id}", response_model=JobRead, operation_id="update_job")
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial update. Candidates may change only `status` and `notes`."""
    return await job_service.update_job(db, actor, job_id, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_job")
async def delete_job(
    job_id: uuid.UUID,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    await job_service.delete_job(db, actor, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{job_id}/resume", response_model=DocumentRead, operation_id="upload_optimized_resume_file"
)
async def upload_optimized_resume(
    job_id: uuid.UUID,
    file: UploadFile = File(description="PDF, DOCX, DOC, ODT, RTF, TXT, MD or HTML."),
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    """Upload (or replace) the resume optimized for this specific job."""
    job = await job_service.get_job(db, actor, job_id)
    name, data = await read_upload(file)
    return await document_service.save_optimized_resume(db, job, actor, name, data)


@router.put(
    "/{job_id}/resume/content",
    response_model=DocumentRead,
    operation_id="upload_optimized_resume",
)
async def upload_optimized_resume_content(
    job_id: uuid.UUID,
    payload: ResumeTextUpload,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    """Same as the multipart upload, but takes JSON text or base64 content."""
    job = await job_service.get_job(db, actor, job_id)
    name, data = document_service.decode_payload(
        payload.filename, payload.content_text, payload.content_base64
    )
    return await document_service.save_optimized_resume(db, job, actor, name, data)


@router.get(
    "/{job_id}/resume",
    operation_id="download_optimized_resume",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}, "description": "The file."}},
)
async def download_optimized_resume(
    job_id: uuid.UUID,
    format: ExportFormat | None = Query(
        None,
        description="Convert to PDF or DOCX. Omit to get the file as uploaded; a file "
        "already in the requested format is returned unchanged.",
    ),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the tailored resume, optionally converted to PDF or DOCX."""
    job = await job_service.get_job(db, actor, job_id)
    doc = await document_service.get_optimized_resume(db, job)
    return send_file(*document_service.export(doc, format))


@router.get(
    "/{job_id}/resume/content",
    response_model=DocumentContent,
    operation_id="get_optimized_resume",
)
async def get_optimized_resume_content(
    job_id: uuid.UUID,
    include_file: bool = Query(False, description="Also return the file as base64."),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentContent:
    job = await job_service.get_job(db, actor, job_id)
    doc = await document_service.get_optimized_resume(db, job)
    return document_service.to_content(doc, include_file)


@router.delete(
    "/{job_id}/resume",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_optimized_resume",
)
async def delete_optimized_resume(
    job_id: uuid.UUID,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.get_job(db, actor, job_id)
    await document_service.delete_optimized_resume(db, job)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
