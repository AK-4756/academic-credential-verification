# backend/dependencies/database.py
# Database session dependency — canonical import path.
#
# Architecture Reference: docs/backend.md Section 20 (Database Access Strategy)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3
#
# Re-exports get_db from database.connection to provide the documented
# import path: `from dependencies.database import get_db`
#
# The actual session lifecycle (create, yield, close) is implemented
# in database/connection.py. This module provides a stable dependency
# path that routers use, decoupled from the infrastructure layer.

from database.connection import get_db

__all__ = ["get_db"]
