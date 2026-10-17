"""User & auth schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=255)
    role: UserRole = UserRole.candidate


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=255)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AuthConfig(BaseModel):
    registration_enabled: bool
