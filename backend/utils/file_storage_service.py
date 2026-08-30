# backend/utils/file_storage_service.py
# Local filesystem storage for certificate PDFs and QR images.
#
# Architecture Reference: docs/backend.md Section 21.1 (File Storage Strategy)
# Directory Reference: docs/backend.md Section 27.1 (utils/file_storage_service.py)
# Build Order: implementation-roadmap.md Sprint 4, Phase 6 (infrastructure services)
#
# MVP Implementation: LocalFileStorageService
#   Root: /uploads/ (configurable via UPLOAD_ROOT env var)
#   Cert path: /uploads/certificates/{university_id}/{cert_id}.pdf
#   QR path: /uploads/qr/{cert_id}.png
#   Auto-create directories on first write.
#
# Security (from docs Section 21.1):
#   - Files stored outside web root (not directly URL-accessible)
#   - UUID filenames prevent path traversal
#   - Access only via API with authorization checks

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from core.config import settings
from core.exceptions import FileNotFoundOnDiskError


def _get_upload_root() -> Path:
    """Get the configured upload root directory."""
    return Path(settings.UPLOAD_ROOT)


def save_certificate(
    file_bytes: bytes,
    university_id: UUID,
    cert_id: UUID,
) -> str:
    """
    Save a certificate PDF to the local filesystem.

    Docs Section 21.1:
    Path: /uploads/certificates/{university_id}/{cert_id}.pdf
    Auto-creates directory on first write.

    Args:
        file_bytes: Raw PDF bytes.
        university_id: University UUID for directory scoping.
        cert_id: Certificate UUID for filename.

    Returns:
        Relative file path (for DB storage).
    """
    relative_dir = Path("certificates") / str(university_id)
    full_dir = _get_upload_root() / relative_dir
    full_dir.mkdir(parents=True, exist_ok=True)

    relative_path = relative_dir / f"{cert_id}.pdf"
    full_path = _get_upload_root() / relative_path

    full_path.write_bytes(file_bytes)
    return str(relative_path)


def get_certificate(file_path: str) -> bytes:
    """
    Read a certificate PDF from the local filesystem.

    Args:
        file_path: Relative path (as stored in DB).

    Returns:
        Raw PDF bytes.

    Raises:
        FileNotFoundOnDiskError: If the file does not exist on disk.
    """
    full_path = _get_upload_root() / file_path
    if not full_path.exists():
        raise FileNotFoundOnDiskError()
    return full_path.read_bytes()


def save_qr_image(
    image_bytes: bytes,
    cert_id: UUID,
) -> str:
    """
    Save a QR code image to the local filesystem.

    Docs Section 21.1:
    Path: /uploads/qr/{cert_id}.png

    Args:
        image_bytes: Raw PNG image bytes.
        cert_id: Certificate UUID for filename.

    Returns:
        Relative file path (for DB storage).
    """
    relative_dir = Path("qr")
    full_dir = _get_upload_root() / relative_dir
    full_dir.mkdir(parents=True, exist_ok=True)

    relative_path = relative_dir / f"{cert_id}.png"
    full_path = _get_upload_root() / relative_path

    full_path.write_bytes(image_bytes)
    return str(relative_path)
