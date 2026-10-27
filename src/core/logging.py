"""Structured logging configuration using ``structlog``.

No ``print()`` statements — Rules.md §2. All logging goes through structlog
with JSON output in production and pretty-printed output in development.
Correlation IDs are injected into every log line via a context var.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, cast

import structlog

# Context variable holding the per-request correlation ID.
# Set by the CorrelationIdMiddleware on each incoming request.
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def _add_correlation_id(
    logger: Any,  # noqa: ANN401
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Structlog processor that injects the current correlation ID into log events."""
    cid = correlation_id_ctx.get()
    if cid is not None:
        event_dict["correlation_id"] = cid
    return event_dict


def setup_logging(*, log_level: str = "INFO", is_production: bool = False) -> None:
    """Configure structlog and stdlib logging for the application.

    Args:
        log_level: Minimum log level (e.g., ``"INFO"``, ``"DEBUG"``).
        is_production: If ``True``, output JSON lines. Otherwise, pretty-print
            with colors for local development.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_correlation_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        # JSON output for structured log aggregation in production.
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable, colorized output for development.
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet noisy third-party loggers.
    for noisy_logger_name in ("uvicorn.access", "uvicorn.error", "httpx"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger, optionally with a name.

    Args:
        name: Optional logger name (typically ``__name__``).

    Returns:
        A bound structlog logger instance.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
