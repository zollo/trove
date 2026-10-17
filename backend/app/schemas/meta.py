"""Reference data and build info schemas."""
from __future__ import annotations

from pydantic import BaseModel


class Option(BaseModel):
    value: str
    label: str


class JobOptions(BaseModel):
    statuses: list[Option]
    employment_types: list[Option]
    work_modes: list[Option]
    salary_periods: list[Option]
    categories: list[str]


class BuildInfo(BaseModel):
    version: str
    git_commit: str
    build_time: str
    environment: str
    public_url: str
    api_docs_url: str
    openapi_url: str
    mcp_url: str
