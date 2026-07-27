"""Health check endpoint.

No authentication required — used by Docker HEALTHCHECK and load balancers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from src.api.schemas import HealthResponse
from src.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the current health status of the service. No authentication required.",
)
async def health_check() -> HealthResponse:
    """Return the service health status."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.env,
    )
