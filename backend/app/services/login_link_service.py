"""Magic login links: headhunters generate a single-use, 24-hour sign-in link for a candidate.

Only the SHA-256 of the token is stored. Redeeming marks the link used with a
conditional UPDATE, so two concurrent redemptions cannot both succeed.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import Invalid, NotFound
from app.models.login_link import LoginLink
from app.models.user import User, UserRole

LINK_LIFETIME = timedelta(hours=24)
# SPA route that redeems the link. The token goes in the fragment so it never
# reaches server or proxy access logs, nor the Referer header.
LINK_PATH = "/auth/link#"


class LinkRejected(Exception):
    """The token is unknown, used, expired, or its account can't sign in this way."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def link_url(token: str, base_url: str | None = None) -> str:
    return f"{(base_url or settings.public_url).rstrip('/')}{LINK_PATH}{token}"


async def _candidate(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    if user.role != UserRole.candidate:
        raise Invalid("Login links can only be generated for candidates")
    return user


async def create(
    db: AsyncSession, actor: User, user_id: uuid.UUID
) -> tuple[LoginLink, str]:
    user = await _candidate(db, user_id)
    if not user.is_active:
        raise Invalid("This candidate is deactivated")
    now = _now()
    # Housekeeping: links past their expiry can never be used again.
    await db.execute(delete(LoginLink).where(LoginLink.expires_at < now))
    token = secrets.token_urlsafe(32)
    link = LoginLink(
        user_id=user.id,
        created_by_id=actor.id,
        token_hash=_hash(token),
        expires_at=now + LINK_LIFETIME,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link, token


async def list_active(db: AsyncSession, user_id: uuid.UUID) -> list[LoginLink]:
    await _candidate(db, user_id)
    result = await db.execute(
        select(LoginLink)
        .where(
            LoginLink.user_id == user_id,
            LoginLink.used_at.is_(None),
            LoginLink.expires_at > _now(),
        )
        .order_by(LoginLink.created_at.desc())
    )
    return list(result.scalars())


async def revoke_all(db: AsyncSession, user_id: uuid.UUID) -> None:
    await _candidate(db, user_id)
    await db.execute(
        delete(LoginLink).where(LoginLink.user_id == user_id, LoginLink.used_at.is_(None))
    )
    await db.commit()


async def redeem(db: AsyncSession, token: str) -> User:
    """Consume the link and return its candidate, or raise LinkRejected."""
    now = _now()
    link = (
        await db.execute(select(LoginLink).where(LoginLink.token_hash == _hash(token)))
    ).scalar_one_or_none()
    if link is None:
        raise LinkRejected
    claimed = await db.execute(
        update(LoginLink)
        .where(
            LoginLink.id == link.id,
            LoginLink.used_at.is_(None),
            LoginLink.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    if claimed.rowcount != 1:
        raise LinkRejected
    user = await db.get(User, link.user_id)
    if user is None or not user.is_active or user.role != UserRole.candidate:
        raise LinkRejected
    return user
