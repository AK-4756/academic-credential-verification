# backend/main.py
# FastAPI application entry point — complete middleware stack + exception handlers.
#
# Architecture Reference: docs/architecture.md Section 5.1
# Backend Reference: docs/backend.md Sections 6.2 (Middleware), 23 (Exception Handling)
# Build Order: implementation-roadmap.md Phase 6.1, Item 8
#
# Middleware Stack (executed in reverse order for responses):
#   1. CORSMiddleware — CORS headers
#   2. RequestIDMiddleware — X-Request-ID UUID per request
#   3. StructuredLoggingMiddleware — JSON request/response logging
#   4. SlowAPI Rate Limiter — per-endpoint rate limiting via @limiter.limit()
#
# Exception Handlers:
#   - AppException → structured error response with correct HTTP status
#   - RateLimitExceeded → 429 with documented error envelope + Retry-After header
#   - RequestValidationError → 422 with field-level details
#   - Exception → 500 generic error (no stack traces in production)
#
# Run: uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/api/v1/docs (when SHOW_DOCS=True)

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.config import settings
from core.exceptions import AppException
from core.logging_config import get_logger, setup_logging
from dependencies.rate_limiting import limiter, rate_limit_exceeded_handler

# ─── Initialize Logging ──────────────────────────────────────────────────────
# Must happen before any logger is created
setup_logging()
logger = get_logger(__name__)


# ─── Application Factory ─────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Blockchain-Based Academic Credential Verification — Backend API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json" if settings.SHOW_DOCS else None,
    docs_url="/api/v1/docs" if settings.SHOW_DOCS else None,
    redoc_url="/api/v1/redoc" if settings.SHOW_DOCS else None,
)


# ─── Middleware Stack ─────────────────────────────────────────────────────────
# Order matters: registered first = outermost wrapper = runs first on request.
# See: docs/backend.md Section 6.2 (Middleware Stack — Ordered Specification)

# Middleware 1: CORS
# Security rule (from docs): NEVER use allow_origins=["*"] with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,  # 10 minutes preflight cache
)

# Middleware 2 & 3: RequestID + Logging (custom)
# Imported from middleware package and added via startup event to avoid
# circular imports (middleware may need settings/logging).
from middleware.request_id_middleware import RequestIDMiddleware  # noqa: E402
from middleware.logging_middleware import LoggingMiddleware  # noqa: E402

app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Middleware 4: Rate Limiter (SlowAPI)
# The limiter instance is created in dependencies/rate_limiting.py.
# Per-endpoint limits are applied via @limiter.limit() decorators in routers (Phase 7).
# SlowAPIMiddleware handles rate limit headers on responses.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ─── Global Exception Handlers ───────────────────────────────────────────────
# Design Decision (from docs): Services raise domain exceptions (AppException),
# NOT HTTPException. These handlers translate domain exceptions to HTTP responses.
# This keeps services transport-agnostic.


def _utc_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle all AppException subclasses.

    Response envelope (from docs/backend.md Section 29):
    {
        "success": false,
        "error": {
            "code": "MACHINE_READABLE_CODE",
            "message": "Human-readable message",
            "details": null | dict | list
        },
        "request_id": "uuid",
        "timestamp": "ISO 8601"
    }
    """
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "app_exception",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
        request_id=request_id,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request_id,
            "timestamp": _utc_timestamp(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic/FastAPI request validation errors.

    Transforms FastAPI's native validation errors into our standard
    error envelope with field-level detail.
    """
    request_id = getattr(request.state, "request_id", None)

    # Extract field-level validation details
    details = []
    for error in exc.errors():
        details.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        "validation_error",
        request_id=request_id,
        path=str(request.url.path),
        error_count=len(details),
    )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
            },
            "request_id": request_id,
            "timestamp": _utc_timestamp(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.

    SECURITY: In production (DEBUG=False), no stack traces or internal
    error details are exposed to the client. Only a generic error message
    is returned. Full details are logged server-side for debugging.
    """
    request_id = getattr(request.state, "request_id", None)

    # Always log the full traceback server-side
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=str(request.url.path),
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc() if settings.DEBUG else None,
    )

    # In production, never leak internal details
    message = str(exc) if settings.DEBUG else "An unexpected error occurred"

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "details": None,
            },
            "request_id": request_id,
            "timestamp": _utc_timestamp(),
        },
    )


# ─── Health Check ─────────────────────────────────────────────────────────────
# Completion criterion from implementation-roadmap.md:
#   GET /health → 200 {"status": "ok"}


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.

    Returns 200 with status "ok" when the server is running.
    Used by monitoring systems and deployment verification.
    """
    return {"status": "ok"}


# ─── Startup Event ───────────────────────────────────────────────────────────


@app.on_event("startup")
async def on_startup() -> None:
    """Application startup tasks."""
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
        docs_enabled=settings.SHOW_DOCS,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Application shutdown — clean up database connections and resources."""
    from database.connection import close_engine
    await close_engine()
    logger.info("application_shutdown")


# ─── API Routers ─────────────────────────────────────────────────────────────
# All API routes are mounted under /api/v1/ prefix via router-level prefixes.
# Registration order follows docs/backend.md Section 27.1.

from routers.auth_router import router as auth_router  # noqa: E402
from routers.university_router import router as university_router  # noqa: E402
from routers.certificate_router import router as certificate_router  # noqa: E402
from routers.student_router import router as student_router  # noqa: E402
from routers.employer_router import router as employer_router  # noqa: E402
from routers.verification_router import router as verification_router  # noqa: E402
from routers.qr_router import router as qr_router  # noqa: E402
from routers.log_router import router as log_router  # noqa: E402

app.include_router(auth_router)
app.include_router(university_router)
app.include_router(certificate_router)
app.include_router(student_router)
app.include_router(employer_router)
app.include_router(verification_router)
app.include_router(qr_router)
app.include_router(log_router)
