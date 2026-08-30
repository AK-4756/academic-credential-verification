# backend/services/__init__.py
# Service layer package — business logic between API and repositories.
#
# Architecture Reference: docs/backend.md Section 27.1 (services/)
# Build Order: implementation-roadmap.md Sprint 4, Phase 6
#
# Service layer responsibilities (from docs):
#   - Business logic
#   - Transaction boundaries (async with db.begin())
#   - Authorization/ownership checks
#   - Domain-level validation
#   - Cross-repository orchestration
#   - Coordination with utility/infrastructure components
#
# Services do NOT:
#   - Raise HTTPException (they raise domain exceptions)
#   - Access request/response objects directly
#   - Commit/rollback outside of db.begin() context
#
# Each service module exposes functions (not classes) that accept
# db: AsyncSession and other parameters. This keeps the service
# layer stateless and easy to test.
#
# Service catalog (11 modules — matches docs/backend.md Section 27.1):
#   auth_service.py                  — Registration, login, refresh, logout
#   user_service.py                  — Profile, password, deactivation
#   university_service.py            — Registration, verification, wallet, dashboard
#   student_service.py               — Profile creation
#   student_credential_service.py    — Credential listing, detail, sharing, dashboard
#   employer_service.py              — Profile, verification history, dashboard
#   certificate_issuance_service.py  — Two-phase issuance (upload -> confirm)
#   certificate_revocation_service.py — Two-phase revocation (initiate -> confirm)
#   verification_service.py          — File upload + QR token verification
#   qr_verification_service.py       — QR code token lifecycle
#   verification_log_service.py      — Append-only verification audit log
