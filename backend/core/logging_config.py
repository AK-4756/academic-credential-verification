# backend/core/logging_config.py
# Structured JSON logging via structlog.
#
# Architecture Reference: docs/backend.md Section 24 (Logging Strategy)
# Build Order: implementation-roadmap.md Phase 6.1, Item 2
#
# Why structlog over stdlib logging:
#   - Produces JSON logs natively (parseable by log aggregators)
#   - Context variables (request_id, user_id) attached once per request
#   - Processors pipeline for consistent formatting
#   - Better async support than stdlib logging
#
# Log format: JSON (structured) in production, colored console in development.

from __future__ import annotations

import logging
import sys

import structlog

from core.config import settings


def setup_logging() -> None:
    """
    Configure structlog for the application.

    Development mode: Human-readable colored console output.
    Production mode: JSON-formatted logs for aggregation tools.

    This function should be called once at application startup (in main.py).
    """
    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.DEBUG:
        # Development: pretty-printed, colored console output
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True,
        )
    else:
        # Production: JSON output for log aggregation (ELK, Datadog, etc.)
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the root Python logger to use structlog's formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Usage:
        from core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("certificate_verified", certificate_id=cert_id, result="AUTHENTIC")

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(name)
