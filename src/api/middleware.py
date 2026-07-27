"""HTTP middleware for cross-cutting concerns.

- ``CorrelationIdMiddleware``: assigns a UUID to every request for log traceability.
- ``AuthMiddleware``: enforces API key authentication on all non-exempt paths.
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.core.config import get_settings
from src.core.logging import correlation_id_ctx, get_logger

logger = get_logger(__name__)

# OpenAPI security scheme definition for Swagger UI
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Paths that bypass authentication.
_AUTH_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique correlation ID to every incoming request.

    The ID is stored in a context variable (accessible from structlog processors)
    and added to the ``X-Correlation-ID`` response header.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request with a correlation ID."""
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_ctx.set(cid)

        logger.debug("Request started", method=request.method, path=str(request.url.path))

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key authentication via the ``X-API-Key`` header.

    Paths listed in ``_AUTH_EXEMPT_PATHS`` are skipped (e.g., ``/health``).

    Returns a JSON error response directly instead of raising an exception,
    because middleware exceptions bypass FastAPI's exception handler stack.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate the API key for non-exempt paths."""
        path = request.url.path.rstrip("/")

        if path in _AUTH_EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()
        provided_key = request.headers.get("X-API-Key")

        if not provided_key or provided_key != settings.api_key:
            logger.warning(
                "Authentication failed",
                path=path,
                has_key=bool(provided_key),
            )
            correlation_id = correlation_id_ctx.get() or "unknown"
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "AUTHENTICATION_ERROR",
                        "message": "Invalid or missing API key.",
                        "correlation_id": correlation_id,
                    }
                },
            )

        return await call_next(request)
