"""Magic login link schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_by_id: uuid.UUID | None
    created_at: datetime
    expires_at: datetime


class LoginLinkCreated(LoginLinkRead):
    url: str = Field(
        description="Sign-in link for the candidate. Works once, until expires_at; shown only once."
    )
    token: str = Field(
        description="The secret part of `url`; redeem with POST /api/auth/login-link."
    )


class LoginLinkRedeem(BaseModel):
    token: str = Field(min_length=16, max_length=256)
