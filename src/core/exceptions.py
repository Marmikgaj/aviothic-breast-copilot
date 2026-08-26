
"""Application exception hierarchy and FastAPI exception handlers.

Fail loud in development, fail soft in production (Rules.md §4).
All errors are returned as structured JSON — stack traces never leak to clients.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.logging import correlation_id_ctx, get_logger

logger = get_logger(__name__)


# ============================================================================
# Exception hierarchy
# ============================================================================


class AviothicError(Exception):
    """Base exception for all application errors.

    Args:
        detail: Human-readable error description.
        status_code: HTTP status code to return to the client.
        error_code: Machine-readable error code (e.g., ``"VALIDATION_ERROR"``).
    """

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code


class FileValidationError(AviothicError):
    """Raised when an uploaded file fails validation (size, MIME type, etc.)."""

    def __init__(self, detail: str, *, status_code: int = 422, error_code: str = "FILE_VALIDATION_ERROR") -> None:
        super().__init__(detail, status_code=status_code, error_code=error_code)


class FileTooLargeError(FileValidationError):
    """Raised when the uploaded file exceeds the maximum allowed size."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=413, error_code="FILE_TOO_LARGE")


class UnsupportedMimeTypeError(FileValidationError):
    """Raised when the uploaded file has an unsupported MIME type."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=415, error_code="UNSUPPORTED_MIME_TYPE")


class FileProcessingError(AviothicError):
    """Raised when file processing (PDF extraction, text cleaning) fails."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=500, error_code="FILE_PROCESSING_ERROR")


class OcrUnavailableError(AviothicError):
    """Raised when the Tesseract OCR binary is not installed or not on PATH."""

    def __init__(self) -> None:
        super().__init__(
            "Tesseract OCR binary not found. Install tesseract-ocr to process scanned documents.",
            status_code=503,
            error_code="OCR_UNAVAILABLE",
        )


class AuthenticationError(AviothicError):
    """Raised when authentication fails (missing or invalid API key)."""

    def __init__(self, detail: str = "Invalid or missing API key.") -> None:
        super().__init__(detail, status_code=401, error_code="AUTHENTICATION_ERROR")


class ReportNotFoundError(AviothicError):
    """Raised when a requested report does not exist."""

    def __init__(self, report_id: str) -> None:
        super().__init__(
            f"Report '{report_id}' not found.",
            status_code=404,
            error_code="REPORT_NOT_FOUND",
        )


# ============================================================================
# FastAPI exception handlers
# ============================================================================


def _build_error_response(status_code: int, error_code: str, detail: str) -> dict[str, Any]:
    """Build a structured error response body."""
    correlation_id = correlation_id_ctx.get() or "unknown"
    return {
        "error": {
            "code": error_code,
            "message": detail,
            "correlation_id": correlation_id,
        }
    }


async def aviothic_error_handler(request: Request, exc: AviothicError) -> JSONResponse:
    """Handle all AviothicError subclasses with structured JSON responses."""
    logger.warning(
        "Application error",
        error_code=exc.error_code,
        detail=exc.detail,
        status_code=exc.status_code,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(exc.status_code, exc.error_code, exc.detail),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak stack traces to clients."""
    logger.exception(
        "Unhandled exception",
        path=str(request.url),
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(500, "INTERNAL_ERROR", "An unexpected internal error occurred."),
    )
