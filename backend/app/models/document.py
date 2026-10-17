"""Uploaded resumes: a candidate's base resume, or a per-job optimized resume.

File bytes live in the database (resumes are small), so the API is stateless and
needs no shared volume across replicas.
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDMixin, str_enum

if TYPE_CHECKING:
    from app.models.job import Job


class DocumentKind(enum.StrEnum):
    base_resume = "base_resume"
    optimized_resume = "optimized_resume"


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    kind: Mapped[DocumentKind] = mapped_column(
        str_enum(DocumentKind, "document_kind"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Set (and unique) for optimized resumes only.
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=True
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Loaded only when explicitly requested (downloads).
    data: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    # Plain-text extraction (PDF/DOCX/TXT/MD) for AI headhunters; None if unsupported.
    text_content: Mapped[str | None] = deferred(mapped_column(Text, nullable=True))

    job: Mapped["Job | None"] = relationship(back_populates="optimized_resume")
