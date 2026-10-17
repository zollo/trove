"""Resume (document) schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentKind


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: DocumentKind
    candidate_id: uuid.UUID
    job_id: uuid.UUID | None = None
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocumentContent(DocumentRead):
    """Metadata plus the extracted text (and optionally the raw file, base64)."""

    text_content: str | None = None
    content_base64: str | None = None
