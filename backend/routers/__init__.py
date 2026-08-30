# backend/routers/__init__.py
# Router layer package — FastAPI route handlers.
#
# Architecture Reference: docs/backend.md Section 27.1 (routers/)
# Build Order: implementation-roadmap.md Sprint 4, Phase 7
#
# 8 domain routers registered in main.py:
#   auth_router         -> /api/v1/auth
#   university_router   -> /api/v1/universities
#   certificate_router  -> /api/v1/certificates
#   student_router      -> /api/v1/student
#   employer_router     -> /api/v1/employer
#   verification_router -> /api/v1/verify
#   qr_router           -> /api/v1/qr
#   log_router          -> /api/v1/logs
