"""User management (headhunters only): accounts and candidates' magic login links."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_headhunter
from app.core.security import hash_password
from app.db import get_db
from app.models.user import User
from app.schemas.login_link import LoginLinkCreated, LoginLinkRead
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import login_link_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead], operation_id="list_users")
async def list_users(
    _: User = Depends(get_current_headhunter), db: AsyncSession = Depends(get_db)
) -> list[User]:
    result = await db.execute(select(User).order_by(User.role, User.display_name))
    return list(result.scalars())


@router.post(
    "", response_model=UserRead, status_code=status.HTTP_201_CREATED, operation_id="create_user"
)
async def create_user(
    payload: UserCreate,
    _: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        role=payload.role,
    )


@router.patch("/{user_id}", response_model=UserRead, operation_id="update_user")
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.is_active is False and user.id == actor.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/{user_id}/login-links",
    response_model=LoginLinkCreated,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_login_link",
)
async def create_login_link(
    user_id: uuid.UUID,
    actor: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
) -> LoginLinkCreated:
    """Generate a magic sign-in link for a candidate. It works once and expires after 24 hours."""
    link, token = await login_link_service.create(db, actor, user_id)
    return LoginLinkCreated(
        **LoginLinkRead.model_validate(link).model_dump(),
        url=login_link_service.link_url(token),
        token=token,
    )


@router.get(
    "/{user_id}/login-links",
    response_model=list[LoginLinkRead],
    operation_id="list_login_links",
)
async def list_login_links(
    user_id: uuid.UUID,
    _: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    """A candidate's login links that are still unused and unexpired."""
    return await login_link_service.list_active(db, user_id)


@router.delete(
    "/{user_id}/login-links",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revoke_login_links",
)
async def revoke_login_links(
    user_id: uuid.UUID,
    _: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    """Revoke every unused login link of a candidate."""
    await login_link_service.revoke_all(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
