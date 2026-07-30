from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageSequence, UnidentifiedImageError
from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg"}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
PDF_SIGNATURE = b"%PDF-"


class DocumentValidationError(Exception):
    pass


@dataclass
class DocumentMetadata:
    extension: str
    mime_type: str
    page_count: int


def _infer_signature_mime(content: bytes) -> str | None:
    if content.startswith(PDF_SIGNATURE):
        return "application/pdf"
    if content.startswith(PNG_SIGNATURE):
        return "image/png"
    if content.startswith(JPEG_SOI):
        return "image/jpeg"
    return None


def validate_document(filename: str, provided_mime: str | None, content: bytes) -> DocumentMetadata:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError("Unsupported file type.")

    signature_mime = _infer_signature_mime(content)
    if signature_mime is None:
        raise DocumentValidationError("The uploaded file is not a valid PDF or image.")

    normalized_provided_mime = (provided_mime or "").split(";")[0].strip().lower()
    if normalized_provided_mime and normalized_provided_mime not in ALLOWED_MIME:
        raise DocumentValidationError("Unsupported file type.")
    if normalized_provided_mime and normalized_provided_mime != signature_mime:
        raise DocumentValidationError("File content does not match declared file type.")

    if signature_mime == "application/pdf":
        page_count = _count_pdf_pages(content)
    else:
        page_count = _count_image_frames(content)
    return DocumentMetadata(extension=extension, mime_type=signature_mime, page_count=page_count)


def _count_pdf_pages(content: bytes) -> int:
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
    except Exception as exc:  # pragma: no cover - pypdf internals
        raise DocumentValidationError("The PDF is unreadable or malformed.") from exc
    if reader.is_encrypted:
        raise DocumentValidationError("Encrypted PDFs are not supported.")
    return len(reader.pages)


def _count_image_frames(content: bytes) -> int:
    try:
        with Image.open(io.BytesIO(content)) as image:
            return sum(1 for _ in ImageSequence.Iterator(image))
    except UnidentifiedImageError as exc:
        raise DocumentValidationError("The uploaded image is unreadable.") from exc
