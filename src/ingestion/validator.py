"""Upload file validation — size, MIME type, and magic-byte verification.

All input is validated before any processing happens (Rules.md §5).
Defends against spoofed Content-Type headers by checking file magic bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import UploadFile

from src.core.config import Settings
from src.core.exceptions import FileTooLargeError, FileValidationError, UnsupportedMimeTypeError
from src.core.logging import get_logger

logger = get_logger(__name__)

# PDF magic bytes: ``%PDF`` at the start of the file.
_PDF_MAGIC_BYTES = b"%PDF"

# Allowed MIME types that map to the magic byte checks we support.
_MIME_TO_MAGIC: dict[str, bytes] = {
    "application/pdf": _PDF_MAGIC_BYTES,
}


@dataclass(frozen=True)
class ValidatedFile:
    """Result of a successful file validation.

    Attributes:
        filename: Original uploaded filename.
        content: Raw file bytes.
        mime_type: Validated MIME type.
        size_bytes: File size in bytes.
    """

    filename: str
    content: bytes
    mime_type: str
    size_bytes: int


async def validate_upload(*, file: UploadFile, settings: Settings) -> ValidatedFile:
    """Validate an uploaded file for size, MIME type, and magic bytes.

    Args:
        file: The uploaded file from the FastAPI request.
        settings: Application settings containing validation thresholds.

    Returns:
        A ``ValidatedFile`` with the validated file content and metadata.

    Raises:
        FileTooLargeError: If the file exceeds ``settings.upload_max_bytes``.
        UnsupportedMimeTypeError: If the MIME type is not allowed.
        FileValidationError: If the file content doesn't match the claimed type.
    """
    # Read the full file content.
    content = await file.read()
    size_bytes = len(content)
    filename = file.filename or "unnamed_upload"
    claimed_mime = file.content_type or "application/octet-stream"

    logger.info(
        "Validating upload",
        filename=filename,
        claimed_mime=claimed_mime,
        size_bytes=size_bytes,
    )

    # --- Size check ---
    if size_bytes == 0:
        raise FileValidationError("Uploaded file is empty.")

    if size_bytes > settings.upload_max_bytes:
        max_mb = settings.upload_max_bytes / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise FileTooLargeError(f"File size ({actual_mb:.1f} MB) exceeds the maximum allowed size ({max_mb:.0f} MB).")

    if claimed_mime not in settings.allowed_mime_types:
        allowed = ", ".join(sorted(settings.allowed_mime_types))
        raise UnsupportedMimeTypeError(f"MIME type '{claimed_mime}' is not supported. Allowed types: {allowed}.")

    # --- Magic byte verification (defense against spoofed Content-Type) ---
    expected_magic = _MIME_TO_MAGIC.get(claimed_mime)
    if expected_magic and not content[: len(expected_magic)].startswith(expected_magic):
        logger.warning(
            "Magic byte mismatch",
            filename=filename,
            claimed_mime=claimed_mime,
        )
        raise FileValidationError(
            f"File content does not match the claimed MIME type '{claimed_mime}'. "
            "The file may be corrupted or mislabeled."
        )

    logger.info("Upload validation passed", filename=filename, size_bytes=size_bytes)

    return ValidatedFile(
        filename=filename,
        content=content,
        mime_type=claimed_mime,
        size_bytes=size_bytes,
    )
