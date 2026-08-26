"""FastAPI application factory.

Creates and configures the application with middleware, exception handlers,
routers, and lifespan management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.middleware import AuthMiddleware, CorrelationIdMiddleware
from src.api.routers import health, upload
from src.core.config import get_settings
from src.core.exceptions import AviothicError, aviothic_error_handler, unhandled_exception_handler
from src.core.logging import get_logger, setup_logging


# pyrefly: ignore [deprecated]
@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    log = get_logger(__name__)

    # Ensure the upload directory exists.
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    log.info(
        "Application started",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.env,
        upload_dir=str(settings.upload_dir),
        upload_max_bytes=settings.upload_max_bytes,
    )

    yield  # Application is running.

    log.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    settings = get_settings()

    # Initialize structured logging before anything else.
    setup_logging(log_level=settings.log_level, is_production=settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-powered clinical copilot for breast cancer report analysis. "
            "Extracts structured entities, supports grounded Q&A, and generates clinical summaries. "
            "**This is an assistive tool — it does not replace clinical judgment.**"
        ),
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=_lifespan,
    )

    # ---- Middleware (order matters: outermost first) ----
    # CORS — permissive in dev, locked down in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID — must run before auth so errors have trace IDs.
    app.add_middleware(CorrelationIdMiddleware)

    # Authentication — enforces API key on non-exempt routes.
    app.add_middleware(AuthMiddleware)

    # ---- Exception handlers ----
    app.add_exception_handler(AviothicError, aviothic_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

    # ---- Routers ----
    app.include_router(health.router)
    app.include_router(upload.router)

    return app
