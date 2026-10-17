"""Liveness/readiness endpoints and build info."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.meta import BuildInfo

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="health")
async def health() -> dict:
    """Liveness — always cheap, no dependencies."""
    return {"status": "ok", "env": settings.env}


@router.get("/health/ready", operation_id="readiness")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness — checks the database."""
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"database": db_ok}


@router.get("/build-info", response_model=BuildInfo, tags=["meta"], operation_id="build_info")
async def build_info(_: User = Depends(get_current_user)) -> BuildInfo:
    """Current build plus the URLs integrations need. Requires authentication."""
    base = settings.public_url.rstrip("/")
    return BuildInfo(
        version=settings.app_version,
        git_commit=settings.git_commit,
        build_time=settings.build_time,
        environment=settings.env,
        public_url=base,
        api_docs_url=f"{base}/docs",
        openapi_url=f"{base}/openapi.json",
        mcp_url=f"{base}/mcp",
    )
