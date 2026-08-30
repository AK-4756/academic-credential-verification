# backend/dependencies/rate_limiting.py
# SlowAPI rate limiter configuration and custom 429 handler.
#
# Architecture Reference: docs/backend.md Section 6.2 (Middleware Stack)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3
#
# Rate Limiting Strategy (from docs):
#   Engine: SlowAPI (wrapper around the Python `limits` library)
#   Storage: In-memory for MVP (Redis-ready interface for future scaling)
#   Client Identification: Client IP via get_remote_address (X-Forwarded-For aware)
#   Enforcement: Per-endpoint via @limiter.limit() decorators on route handlers
#
# Specific Rate Limits (documented in backend.md Section 6.2):
#   POST /api/v1/auth/login          — 5 req/min   (brute force protection)
#   POST /api/v1/auth/register       — 10 req/min  (account farming protection)
#   POST /api/v1/auth/refresh         — 20 req/min  (token scanning protection)
#   POST /api/v1/certificates/upload  — 10 req/min  (storage abuse protection)
#   POST /api/v1/certificates/*/revoke — 5 req/min  (mass revocation protection)
#   POST /api/v1/verify/upload        — 10 req/min  (RPC abuse protection)
#   GET  /api/v1/verify/qr/{token}    — 30 req/min  (public endpoint protection)
#   All other endpoints               — 100 req/min (general protection)
#
# The @limiter.limit() decorators are applied in Phase 7 (API Routers).
# This module creates the limiter instance and the custom 429 handler.

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ─── Limiter Instance ────────────────────────────────────────────────────────
# Singleton limiter — attached to app.state.limiter in main.py.
# Client identification: IP address (X-Forwarded-For aware for reverse proxy).
# Storage: In-memory (default) — no Redis dependency for MVP.

limiter = Limiter(key_func=get_remote_address)


# ─── Custom 429 Handler ──────────────────────────────────────────────────────


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom handler for HTTP 429 Too Many Requests.

    Returns the documented error envelope format consistent with all other
    error responses in the application (see docs/backend.md Section 29).

    Response format:
        {
            "success": false,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Try again in 60 seconds.",
                "details": null
            },
            "request_id": "<uuid>",
            "timestamp": "<ISO 8601>"
        }

    Response headers:
        Retry-After: 60

    Args:
        request: The rate-limited HTTP request.
        exc: The SlowAPI RateLimitExceeded exception.

    Returns:
        JSONResponse with 429 status and documented error envelope.
    """
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Try again in 60 seconds.",
                "details": None,
            },
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers={
            "Retry-After": "60",
        },
    )
