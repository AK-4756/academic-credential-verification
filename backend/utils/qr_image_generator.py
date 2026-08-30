# backend/utils/qr_image_generator.py
# QR code PNG image generator using the qrcode library.
#
# Architecture Reference: docs/backend.md Section 17 (QR Verification Service)
# Build Order: implementation-roadmap.md Phase 6.5 (Infrastructure Utilities)
#
# Specifications (from docs Section 17):
#   Image size: 400x400 pixels
#   Error correction: Level M (15% recovery)
#   Border: 4 modules
#   Format: PNG
#   Content: verification URL string

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from core.config import settings
from core.constants import QR_BORDER_MODULES, QR_ERROR_CORRECTION, QR_IMAGE_SIZE


def generate_qr_image_bytes(verification_url: str) -> bytes:
    """
    Generate a QR code PNG image from a verification URL.

    Args:
        verification_url: The URL to encode in the QR code.

    Returns:
        Raw PNG image bytes.
    """
    qr = qrcode.QRCode(
        version=None,  # Auto-determine version from data size
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=QR_BORDER_MODULES,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Resize to documented 400x400 pixels
    img = img.resize((QR_IMAGE_SIZE, QR_IMAGE_SIZE))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def get_qr_image_path(token: str) -> Path:
    """
    Get the filesystem path for a QR image by token.

    QR images are stored at: {UPLOAD_ROOT}/qr/{token}.png

    Args:
        token: The QR verification token.

    Returns:
        Full filesystem path to the QR image.
    """
    return Path(settings.UPLOAD_ROOT) / "qr" / f"{token}.png"


def save_qr_image_for_token(token: str, verification_url: str) -> Path:
    """
    Generate and save a QR code image for a token.

    Args:
        token: The QR verification token (used as filename).
        verification_url: The URL to encode.

    Returns:
        Full filesystem path where the image was saved.
    """
    image_bytes = generate_qr_image_bytes(verification_url)
    path = get_qr_image_path(token)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image_bytes)
    return path
