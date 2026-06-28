# backend/main.py
# FastAPI application entry point
#
# Architecture Reference: docs/architecture.md Section 5.1
# Backend Reference: docs/backend.md (Application Pattern: Modular Monolith)
#
# Sprint 1: Minimal skeleton — app instantiation + /health endpoint
# Sprint 3: Full middleware stack, router inclusion, database lifecycle,
#            exception handlers, and startup/shutdown events will be added.
#
# Run: uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/api/v1/docs (when SHOW_DOCS=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

# ─── Application Factory ─────────────────────────────────────────────────────

app = FastAPI(
    title="Academic Credential Verification Platform",
    description="Blockchain-Based Academic Credential Verification — Backend API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json" if settings.SHOW_DOCS else None,
    docs_url="/api/v1/docs" if settings.SHOW_DOCS else None,
    redoc_url="/api/v1/redoc" if settings.SHOW_DOCS else None,
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
# Frontend URL from environment (dev: http://localhost:5173)
# Full middleware stack (JWT, Rate Limit, Logger, Error Handler) added in Sprint 3.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
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


# ─── API Version Prefix ──────────────────────────────────────────────────────
# All API routes will be mounted under /api/v1/ prefix (Sprint 3)
# Example: /api/v1/auth/login, /api/v1/certificates/, /api/v1/verify/
