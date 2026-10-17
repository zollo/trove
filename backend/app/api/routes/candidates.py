"""Candidates: search preferences and base resume.

`{candidate_id}` accepts a UUID or `me` (the caller). Candidates can only reach
their own record; headhunters can reach every candidate.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_headhunter, get_current_user
from app.api.files import file_response, read_upload
from app.db import get_db
from app.models.user import User
from app.schemas.document import DocumentContent, DocumentRead
from app.schemas.profile import CandidateDetail, CandidateSummary, ProfileRead, ProfileUpdate
from app.services import candidate_service, document_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateSummary], operation_id="list_candidates")
async def list_candidates(
    include_inactive: bool = False,
    _: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
) -> list[CandidateSummary]:
    """Every candidate, with resume and job counts (headhunters only)."""
    return await candidate_service.list_candidates(db, include_inactive)


@router.get("/{candidate_id}", response_model=CandidateDetail, operation_id="get_candidate")
async def get_candidate(
    candidate_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateDetail:
    """A candidate's search preferences and base-resume metadata."""
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    return await candidate_service.get_detail(db, candidate)


@router.put(
    "/{candidate_id}/profile", response_model=ProfileRead, operation_id="update_candidate_profile"
)
async def update_profile(
    candidate_id: str,
    payload: ProfileUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    """Replace the candidate's search preferences (titles, salary, locations…)."""
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    return await candidate_service.update_profile(db, candidate, payload)


@router.put(
    "/{candidate_id}/resume",
    response_model=DocumentRead,
    operation_id="upload_base_resume",
)
async def upload_base_resume(
    candidate_id: str,
    file: UploadFile = File(description="PDF, DOCX, DOC, ODT, RTF, TXT, MD or HTML."),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload (or replace) the candidate's detailed, generic base resume."""
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    name, data = await read_upload(file)
    return await document_service.save_base_resume(db, candidate, actor, name, data)


@router.get(
    "/{candidate_id}/resume",
    operation_id="download_base_resume",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}, "description": "The file."}},
)
async def download_base_resume(
    candidate_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the original base resume file."""
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    return file_response(await document_service.get_base_resume(db, candidate))


@router.get(
    "/{candidate_id}/resume/content",
    response_model=DocumentContent,
    operation_id="get_base_resume",
)
async def get_base_resume_content(
    candidate_id: str,
    include_file: bool = Query(False, description="Also return the file as base64."),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentContent:
    """Base resume metadata and extracted plain text, for rewriting by an AI headhunter."""
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    doc = await document_service.get_base_resume(db, candidate)
    return document_service.to_content(doc, include_file)


@router.delete(
    "/{candidate_id}/resume",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_base_resume",
)
async def delete_base_resume(
    candidate_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    candidate = await candidate_service.resolve_candidate(db, actor, candidate_id)
    await document_service.delete_base_resume(db, candidate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
