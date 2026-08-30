# backend/schemas/common_schemas.py
# Shared Pydantic schemas: response envelopes, pagination, common types.
#
# Architecture Reference: docs/backend.md Section 29.1 (Request & Response Standards)
# Directory Reference: docs/backend.md Section 27.1 (schemas/common_schemas.py)
# Build Order: implementation-roadmap.md Sprint 4, Phase 5
#
# Standard Envelopes (from docs Section 29.1):
#   SuccessResponse   — { success: true, data, message, timestamp }
#   PaginatedResponse — { success: true, data: { items, pagination }, timestamp }
#   ErrorResponse     — { success: false, error: { code, message, details }, request_id, timestamp }
#
# Pagination (from docs Section 29.1):
#   Default page: 1, default limit: 20, max limit: 100

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

_UTC = timezone.utc


# ─── Pagination ──────────────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    """
    Pagination query parameters.

    Docs: Section 29.1 — page=1, limit=20, max 100.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    )

    @property
    def skip(self) -> int:
        """Compute offset for repository queries."""
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """
    Pagination metadata in paginated responses.

    Docs Section 29.1:
    { total, page, limit, pages, has_next, has_prev }
    """

    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(cls, total: int, page: int, limit: int) -> PaginationMeta:
        """Construct pagination metadata from total, page, and limit."""
        pages = max(1, math.ceil(total / limit)) if limit > 0 else 1
        return cls(
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )


# ─── Standard Success Response Envelope ──────────────────────────────────────


class SuccessResponse(BaseModel):
    """
    Standard success response envelope.

    Docs Section 29.1:
    { "success": true, "data": { ... }, "message": "...", "timestamp": "..." }
    """

    success: bool = True
    data: Any = None
    message: str = "Operation successful"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=_UTC))

    model_config = ConfigDict(from_attributes=True)


# ─── Standard Paginated Response Envelope ────────────────────────────────────


class PaginatedData(BaseModel):
    """
    Inner data structure for paginated responses.

    Docs Section 29.1:
    { "items": [...], "pagination": { total, page, limit, pages, has_next, has_prev } }
    """

    items: list[Any]
    pagination: PaginationMeta


class PaginatedResponse(BaseModel):
    """
    Standard paginated response envelope.

    Docs Section 29.1:
    { "success": true, "data": { "items": [...], "pagination": {...} }, "timestamp": "..." }
    """

    success: bool = True
    data: PaginatedData
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=_UTC))


# ─── Standard Error Response Envelope ────────────────────────────────────────


class ErrorDetail(BaseModel):
    """
    Error payload within the error response.

    Docs Section 29.1:
    { "code": "ERROR_CODE", "message": "...", "details": [...] | null }
    """

    code: str
    message: str
    details: list[Any] | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response envelope.

    Docs Section 29.1:
    { "success": false, "error": { code, message, details },
      "request_id": "uuid", "timestamp": "..." }
    """

    success: bool = False
    error: ErrorDetail
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=_UTC))


# ─── Generic Message Response ────────────────────────────────────────────────


class MessageResponse(BaseModel):
    """Simple message-only response (e.g., logout, password change)."""

    message: str
