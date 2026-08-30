# backend/middleware/request_id_middleware.py
# Middleware 2: RequestIDMiddleware
#
# Architecture Reference: docs/backend.md Section 6.2 (Middleware Stack)
#
# Purpose:
#   - Generate a UUID v4 for every incoming request
#   - Attach it to request.state.request_id (accessible by downstream handlers)
#   - Return it as X-Request-ID response header (for client-side tracing)
#   - Bind it to structlog context (appears in all log entries for this request)
#
# If the client sends an X-Request-ID header, it is used as-is (for tracing
# across microservices). Otherwise, a new UUID is generated.

from __future__ import annotations

from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assign a unique request ID to every HTTP request.

    The ID is:
    1. Stored in request.state.request_id for access by handlers
    2. Bound to structlog context for automatic inclusion in all logs
    3. Returned as X-Request-ID response header for client correlation
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use client-provided request ID if present, otherwise generate
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        # Store on request state for access by exception handlers and routes
        request.state.request_id = request_id

        # Bind to structlog context — all logs during this request include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Process the request
        response = await call_next(request)

        # Include in response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id

        return response
