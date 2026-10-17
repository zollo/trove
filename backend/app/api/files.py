"""Helpers for multipart uploads and file downloads."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Response, UploadFile

from app.config import settings
from app.core.errors import TooLarge
from app.models.document import Document


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    # Read one byte past the limit so oversize files are rejected without
    # buffering arbitrarily large bodies.
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise TooLarge(f"File exceeds the {settings.max_upload_mb} MB limit")
    return file.filename or "resume", data


def file_response(doc: Document) -> Response:
    ascii_name = doc.filename.encode("ascii", "ignore").decode() or "resume"
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(doc.filename)}"
    return Response(
        content=doc.data,
        media_type=doc.content_type,
        headers={"Content-Disposition": disposition, "Cache-Control": "private, no-store"},
    )
