"""Resume filename handling and text extraction."""
from __future__ import annotations

import io

import docx

from app.core import resume_text


def test_safe_filename():
    assert resume_text.safe_filename("../../etc/passwd") == "passwd"
    assert resume_text.safe_filename('C:\\Users\\me\\My "CV".pdf') == "My CV.pdf"
    assert resume_text.safe_filename("") == "resume"


def test_allowed_types():
    assert resume_text.is_allowed("cv.PDF")
    assert resume_text.is_allowed("cv.docx")
    assert not resume_text.is_allowed("cv.exe")
    assert resume_text.content_type_for("cv.md") == "text/markdown"


def test_extract_docx():
    document = docx.Document()
    document.add_paragraph("Jane Doe — Platform Engineer")
    buf = io.BytesIO()
    document.save(buf)
    assert "Platform Engineer" in resume_text.extract_text("cv.docx", buf.getvalue())


def test_extract_broken_pdf_returns_none():
    assert resume_text.extract_text("cv.pdf", b"not a pdf") is None
