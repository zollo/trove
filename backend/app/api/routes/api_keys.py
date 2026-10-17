"""Personal API keys for headhunter integrations (REST and MCP)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_headhunter
from app.db import get_db
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.services import user_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead], operation_id="list_api_keys")
async def list_keys(
    user: User = Depends(get_current_headhunter), db: AsyncSession = Depends(get_db)
):
    return await user_service.list_api_keys(db, user)


@router.post(
    "",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_api_key",
)
async def create_key(
    payload: ApiKeyCreate,
    user: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    """Create a key. The full key is returned once; only a hash is stored."""
    row, key = await user_service.create_api_key(db, user, payload.name)
    return ApiKeyCreated(**ApiKeyRead.model_validate(row).model_dump(), key=key)


@router.delete(
    "/{key_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_api_key"
)
async def delete_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_headhunter),
    db: AsyncSession = Depends(get_db),
):
    await user_service.delete_api_key(db, user, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
