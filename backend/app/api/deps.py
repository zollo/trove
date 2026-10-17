"""Shared FastAPI dependencies: auth + role checks."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.services import user_service

# Accepts either a session JWT (from /api/auth/login) or a `trove_…` API key.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="A session token from POST /api/auth/login, or a headhunter API key (trove_…).",
)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _credentials_error
    user = await user_service.resolve_token(db, creds.credentials)
    if user is None:
        raise _credentials_error
    return user


async def get_current_headhunter(user: User = Depends(get_current_user)) -> User:
    if not user.is_headhunter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Headhunter privileges required"
        )
    return user
