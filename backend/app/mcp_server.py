"""MCP server for AI headhunters, served over streamable HTTP at /mcp.

Each tool mirrors a REST operation of the same name (see the OpenAPI spec at
/openapi.json and docs/openapi.json) and calls the same service layer, so the
two interfaces cannot drift apart in behaviour or permissions.

Auth: `Authorization: Bearer <API key or session token>` belonging to a
headhunter. The transport is stateless (JSON responses, no session affinity), so
any number of API replicas can serve it.
"""
from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from app.config import settings
from app.core.errors import TroveError
from app.db import AsyncSessionLocal
from app.models.job import EmploymentType, JobStatus, WorkMode
from app.models.user import User
from app.schemas.document import DocumentContent, DocumentRead
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.schemas.meta import JobOptions
from app.schemas.profile import CandidateDetail, CandidateSummary
from app.schemas.user import UserRead
from app.services import candidate_service, document_service, job_service, user_service

INSTRUCTIONS = """\
Trove is a job-search portal. You act as a headhunter for one or more candidates.
Typical workflow:
1. list_candidates, then get_candidate to read their search preferences
   (titles, categories, employment types, locations, work modes, salary range, notes).
2. get_base_resume to read the candidate's detailed base resume as text.
3. Search for matching openings yourself, then create_job for each good match,
   with a fit_score from 1 (poor) to 5 (excellent) and notes explaining the fit.
   Use list_jobs first to avoid duplicates; create_job rejects a repeated apply_url.
4. Rewrite the base resume for that specific posting and upload it with
   upload_optimized_resume (Markdown in content_text is fine).
5. Use update_job to mark postings expired/unavailable when they close.
"""

mcp = MCPServer(
    name="trove",
    title="Trove",
    instructions=INSTRUCTIONS,
    version=settings.app_version,
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


@contextlib.asynccontextmanager
async def _session(ctx: Context) -> AsyncIterator[tuple[AsyncSession, User]]:
    """Open a DB session and resolve the calling headhunter from the HTTP headers."""
    headers = ctx.headers or {}
    scheme, _, token = (headers.get("authorization") or "").partition(" ")
    async with AsyncSessionLocal() as db:
        user = None
        if scheme.lower() == "bearer" and token:
            user = await user_service.resolve_token(db, token.strip())
        if user is None or not user.is_headhunter:
            raise ToolError("Unauthorized: a headhunter API key is required")
        try:
            yield db, user
        except TroveError as exc:
            raise ToolError(exc.detail) from exc


@mcp.tool(annotations=_READ_ONLY)
async def whoami(ctx: Context) -> UserRead:
    """The headhunter account this connection is authenticated as."""
    async with _session(ctx) as (_, user):
        return UserRead.model_validate(user)


@mcp.tool(annotations=_READ_ONLY)
async def list_candidates(ctx: Context) -> list[CandidateSummary]:
    """List active candidates with resume status and job counts."""
    async with _session(ctx) as (db, _):
        return await candidate_service.list_candidates(db)


@mcp.tool(annotations=_READ_ONLY)
async def get_candidate(candidate_id: str, ctx: Context) -> CandidateDetail:
    """A candidate's job-search preferences (titles, categories, employment types,
    locations, work modes, salary range, notes) and base-resume metadata."""
    async with _session(ctx) as (db, user):
        candidate = await candidate_service.resolve_candidate(db, user, candidate_id)
        return await candidate_service.get_detail(db, candidate)


@mcp.tool(annotations=_READ_ONLY)
async def get_base_resume(
    candidate_id: str, ctx: Context, include_file: bool = False
) -> DocumentContent:
    """Download a candidate's base resume. Returns extracted plain text in
    text_content; set include_file=true to also get the original file as base64."""
    async with _session(ctx) as (db, user):
        candidate = await candidate_service.resolve_candidate(db, user, candidate_id)
        doc = await document_service.get_base_resume(db, candidate)
        return document_service.to_content(doc, include_file)


@mcp.tool(annotations=_READ_ONLY)
async def get_job_options(ctx: Context) -> JobOptions:
    """Allowed values for job status, employment type and work mode, and the job
    categories already in use (reuse them for consistency)."""
    async with _session(ctx) as (db, _):
        return await job_service.job_options(db)


@mcp.tool(annotations=_READ_ONLY)
async def list_jobs(
    ctx: Context,
    candidate_id: str | None = None,
    status: list[JobStatus] | None = None,
    q: str | None = None,
) -> list[JobRead]:
    """List job postings, optionally for one candidate, filtered by status or a
    search string matched against title, company, location and category."""
    async with _session(ctx) as (db, user):
        jobs = await job_service.list_jobs(db, user, candidate_id=candidate_id, status=status, q=q)
        return [JobRead.model_validate(j) for j in jobs]


@mcp.tool(annotations=_READ_ONLY)
async def get_job(job_id: uuid.UUID, ctx: Context) -> JobRead:
    """One job posting, including optimized-resume metadata."""
    async with _session(ctx) as (db, user):
        return JobRead.model_validate(await job_service.get_job(db, user, job_id))


@mcp.tool(annotations=_WRITE)
async def create_job(
    candidate_id: uuid.UUID,
    title: str,
    apply_url: str,
    ctx: Context,
    company: str = "",
    status: JobStatus = JobStatus.new,
    category: str = "",
    employment_type: EmploymentType | None = None,
    location: str = "",
    work_mode: WorkMode | None = None,
    compensation: str = "",
    date_found: date | None = None,
    schedule: str = "",
    fit_score: int | None = None,
    notes: str = "",
) -> JobRead:
    """Post a job opening for a candidate. fit_score is 1 (poor) to 5 (excellent);
    explain the score in notes. date_found defaults to today. Fails if the
    candidate already has a job with the same apply_url."""
    payload = _validate(
        JobCreate,
        candidate_id=candidate_id,
        title=title,
        apply_url=apply_url,
        company=company,
        status=status,
        category=category,
        employment_type=employment_type,
        location=location,
        work_mode=work_mode,
        compensation=compensation,
        date_found=date_found,
        schedule=schedule,
        fit_score=fit_score,
        notes=notes,
    )
    async with _session(ctx) as (db, user):
        return JobRead.model_validate(await job_service.create_job(db, user, payload))


@mcp.tool(annotations=_WRITE)
async def update_job(
    job_id: uuid.UUID,
    ctx: Context,
    title: str | None = None,
    apply_url: str | None = None,
    company: str | None = None,
    status: JobStatus | None = None,
    category: str | None = None,
    employment_type: EmploymentType | None = None,
    location: str | None = None,
    work_mode: WorkMode | None = None,
    compensation: str | None = None,
    date_found: date | None = None,
    schedule: str | None = None,
    fit_score: int | None = None,
    notes: str | None = None,
) -> JobRead:
    """Change a job posting. Only the fields you pass are updated; e.g. set
    status to "expired" or "unavailable" when the posting closes."""
    fields: dict[str, Any] = {
        k: v
        for k, v in {
            "title": title,
            "apply_url": apply_url,
            "company": company,
            "status": status,
            "category": category,
            "employment_type": employment_type,
            "location": location,
            "work_mode": work_mode,
            "compensation": compensation,
            "date_found": date_found,
            "schedule": schedule,
            "fit_score": fit_score,
            "notes": notes,
        }.items()
        if v is not None
    }
    payload = _validate(JobUpdate, **fields)
    async with _session(ctx) as (db, user):
        return JobRead.model_validate(await job_service.update_job(db, user, job_id, payload))


@mcp.tool(annotations=_WRITE)
async def upload_optimized_resume(
    job_id: uuid.UUID,
    ctx: Context,
    filename: str = "optimized-resume.md",
    content_text: str | None = None,
    content_base64: str | None = None,
) -> DocumentRead:
    """Attach a resume rewritten for this specific job, replacing any earlier one.
    Pass Markdown/plain text in content_text, or a PDF/DOCX file in content_base64
    (with a matching filename extension)."""
    async with _session(ctx) as (db, user):
        job = await job_service.get_job(db, user, job_id)
        name, data = document_service.decode_payload(filename, content_text, content_base64)
        doc = await document_service.save_optimized_resume(db, job, user, name, data)
        return DocumentRead.model_validate(doc)


@mcp.tool(annotations=_READ_ONLY)
async def get_optimized_resume(
    job_id: uuid.UUID, ctx: Context, include_file: bool = False
) -> DocumentContent:
    """The optimized resume attached to a job, as extracted text (and base64 file
    if include_file=true)."""
    async with _session(ctx) as (db, user):
        job = await job_service.get_job(db, user, job_id)
        doc = await document_service.get_optimized_resume(db, job)
        return document_service.to_content(doc, include_file)


def _validate(model, **fields):
    from pydantic import ValidationError

    try:
        return model(**fields)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ToolError(f"Invalid arguments: {problems}") from exc


class MCPEndpoint:
    """ASGI app for /mcp: rejects unauthenticated requests up front, then hands
    off to the SDK's streamable-HTTP handler.

    The SDK's session manager can only run once, so a fresh one is created for
    every application lifespan (see `lifespan()`).
    """

    def __init__(self) -> None:
        self._app = None

    @contextlib.asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        starlette_app = mcp.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
            max_request_body_size=settings.max_upload_bytes * 2,
            # Bearer auth (below) is required, so Host-header pinning adds nothing
            # and would break deployments behind arbitrary hostnames.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        self._app = starlette_app
        async with mcp.session_manager.run():
            yield
        self._app = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._app is None:
            await JSONResponse({"detail": "MCP server not running"}, 503)(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        scheme, _, token = headers.get("authorization", "").partition(" ")
        user = None
        if scheme.lower() == "bearer" and token:
            async with AsyncSessionLocal() as db:
                user = await user_service.resolve_token(db, token.strip())
        if user is None or not user.is_headhunter:
            response = JSONResponse(
                {"detail": "A headhunter API key is required (Authorization: Bearer trove_…)"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        # The SDK app routes on the full path; normalise a trailing slash.
        if scope["path"] == "/mcp/":
            scope = {**scope, "path": "/mcp"}
        await self._app(scope, receive, send)


mcp_endpoint = MCPEndpoint()
