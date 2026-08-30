# backend/middleware/logging_middleware.py
# Middleware 3: StructuredLoggingMiddleware
#
# Architecture Reference: docs/backend.md Section 6.2 (Middleware Stack)
#
# Logs for every request:
#   - timestamp, method, path, client IP, user_agent, request_id
# Logs on response:
#   - status_code, processing_time_ms
#
# SECURITY (from docs): Do NOT log request bodies (may contain passwords/PII).

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log structured request/response metadata for every HTTP request.

    Captures:
    - Request: method, path, client IP, user agent, request ID
    - Response: status code, processing time in milliseconds

    Security: Request bodies are NEVER logged (may contain passwords, PII).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        # Extract client IP (X-Forwarded-For aware for reverse proxy)
        client_ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )
        # X-Forwarded-For may contain multiple IPs; take the first (original client)
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        request_id = getattr(request.state, "request_id", None)

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Skip logging for health check to reduce noise
        if request.url.path == "/health":
            return response

        logger.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            query=str(request.url.query) if request.url.query else None,
            status_code=response.status_code,
            client_ip=client_ip,
            user_agent=request.headers.get("User-Agent"),
            request_id=request_id,
            processing_time_ms=process_time_ms,
        )

        return response
