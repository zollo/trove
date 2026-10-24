"""User lookups, authentication (passwords, JWTs, API keys) and API-key management."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.core.security import (
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    is_api_key,
    verify_password,
)
from app.models.api_key import ApiKey
from app.models.profile import CandidateProfile
from app.models.user import User, UserRole


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str | None,
    display_name: str = "",
    role: UserRole = UserRole.candidate,
    google_sub: str | None = None,
) -> User:
    if await get_by_email(db, email):
        raise Conflict("Email already registered")
    user = User(
        email=email.lower(),
        display_name=display_name or email.split("@")[0],
        hashed_password=hash_password(password) if password else None,
        role=role,
        google_sub=google_sub,
        google_email=email.lower() if google_sub else None,
    )
    if role == UserRole.candidate:
        user.profile = CandidateProfile()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def resolve_token(db: AsyncSession, token: str) -> User | None:
    """Return the active user behind a bearer token (session JWT or API key)."""
    if is_api_key(token):
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(token)))
        key = result.scalar_one_or_none()
        if key is None:
            return None
        key.last_used_at = datetime.now(UTC)
        await db.commit()
        user = key.user
    else:
        try:
            payload = decode_access_token(token)
            user_id = uuid.UUID(str(payload.get("sub")))
        except (jwt.PyJWTError, ValueError):
            return None
        user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


async def list_api_keys(db: AsyncSession, user: User) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars())


async def create_api_key(db: AsyncSession, user: User, name: str) -> tuple[ApiKey, str]:
    key = generate_api_key()
    row = ApiKey(user_id=user.id, name=name.strip(), prefix=key[:12], key_hash=hash_api_key(key))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, key


async def delete_api_key(db: AsyncSession, user: User, key_id: uuid.UUID) -> None:
    row = await db.get(ApiKey, key_id)
    if row is None or row.user_id != user.id:
        raise NotFound("API key not found")
    await db.delete(row)
    await db.commit()
