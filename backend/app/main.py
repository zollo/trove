"""Trove FastAPI application: REST API at /api, MCP at /mcp."""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.routing import Route

from app.api.routes import api_router
from app.config import settings
from app.core.errors import TroveError
from app.db import AsyncSessionLocal
from app.mcp_server import mcp_endpoint
from app.models.user import UserRole
from app.services import user_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trove")

DESCRIPTION = """\
Trove is a job-search portal shared by **candidates** and their **headhunters**
(human or AI).

* Authenticate with `Authorization: Bearer <token>`: a session token from
  `POST /api/auth/login`, or a headhunter API key (`trove_…`) created in the UI.
* Wherever a `candidate_id` is accepted, `me` means the caller.
* The same operations are exposed as **MCP tools** over streamable HTTP at `/mcp`;
  each tool is named after the `operationId` of its REST counterpart.
"""


async def _bootstrap_headhunter() -> None:
    """Create the initial headhunter account if it does not exist yet."""
    async with AsyncSessionLocal() as db:
        if await user_service.get_by_email(db, settings.bootstrap_headhunter_email):
            return
        password = settings.bootstrap_headhunter_password or secrets.token_urlsafe(12)
        await user_service.create_user(
            db,
            email=settings.bootstrap_headhunter_email,
            password=password,
            display_name="Headhunter",
            role=UserRole.headhunter,
        )
        if settings.bootstrap_headhunter_password:
            logger.info("Bootstrapped headhunter %s", settings.bootstrap_headhunter_email)
        else:
            logger.warning(
                "Bootstrapped headhunter %s with generated password %s "
                "(set BOOTSTRAP_HEADHUNTER_PASSWORD to choose one)",
                settings.bootstrap_headhunter_email,
                password,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await _bootstrap_headhunter()
    except Exception:  # noqa: BLE001
        # Don't crash the API if bootstrap fails (e.g. migrations not yet run).
        logger.exception("Headhunter bootstrap failed; continuing")
    async with mcp_endpoint.lifespan():
        yield


app = FastAPI(
    title="Trove",
    description=DESCRIPTION,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TroveError)
async def _trove_error(_: Request, exc: TroveError) -> JSONResponse:
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


app.include_router(api_router)
# Plain Starlette routes stay out of the OpenAPI schema.
app.router.routes.append(Route("/mcp", endpoint=mcp_endpoint, methods=["GET", "POST", "DELETE"]))
app.router.routes.append(Route("/mcp/", endpoint=mcp_endpoint, methods=["GET", "POST", "DELETE"]))


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "Trove", "version": app.version, "docs": "/docs", "mcp": "/mcp"}
