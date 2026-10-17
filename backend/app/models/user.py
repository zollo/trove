"""User accounts: candidates and headhunters."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDMixin, str_enum

if TYPE_CHECKING:
    from app.models.profile import CandidateProfile


class UserRole(enum.StrEnum):
    candidate = "candidate"
    headhunter = "headhunter"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, "user_role"), default=UserRole.candidate, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def is_headhunter(self) -> bool:
        return self.role == UserRole.headhunter
