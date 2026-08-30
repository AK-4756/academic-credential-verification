# backend/routers/auth_router.py
# Authentication endpoints — register, login, refresh, logout.
#
# Architecture Reference: docs/backend.md Section 7.1 (Authentication Service Design)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   POST /api/v1/auth/register  — Public, RATE_LIMIT_REGISTER (10/min)
#   POST /api/v1/auth/login     — Public, RATE_LIMIT_LOGIN (5/min)
#   POST /api/v1/auth/refresh   — Cookie auth, RATE_LIMIT_REFRESH (20/min)
#   POST /api/v1/auth/logout    — Bearer JWT

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import (
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REFRESH,
    RATE_LIMIT_REGISTER,
)
from core.exceptions import InvalidCredentialsError
from dependencies import get_current_active_user, get_db, limiter
from models.user_model import User
from schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    SuccessResponse,
    TokenRefreshResponse,
)
from services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ─── POST /register ──────────────────────────────────────────────────────────


@router.post("/register", status_code=201)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    No auto-login on registration; user must login explicitly.
    """
    result = await auth_service.register_user(
        registration_data=body.model_dump(),
        db=db,
    )
    return SuccessResponse(
        data=RegisterResponse(**result),
        message="Registration successful",
    )


# ─── POST /login ─────────────────────────────────────────────────────────────


@router.post("/login")
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and issue access + refresh tokens.

    Returns JWT in body; sets refresh_token as httpOnly cookie.
    """
    result = await auth_service.authenticate_user(
        email=body.email,
        password=body.password,
        request_ip=request.client.host if request.client else "unknown",
        db=db,
    )

    # Set refresh token cookie (docs Section 7.1)
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth/refresh",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return LoginResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        user=result["user"],
    )


# ─── POST /refresh ───────────────────────────────────────────────────────────


@router.post("/refresh")
@limiter.limit(RATE_LIMIT_REFRESH)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using the refresh_token cookie.

    Single-use rotation: revokes old token, issues new pair.
    """
    refresh_token_raw = request.cookies.get("refresh_token")
    if not refresh_token_raw:
        raise InvalidCredentialsError(message="No refresh token provided")

    result = await auth_service.refresh_access_token(
        refresh_token_raw=refresh_token_raw,
        request_ip=request.client.host if request.client else "unknown",
        db=db,
    )

    # Set new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth/refresh",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return TokenRefreshResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
    )


# ─── POST /logout ────────────────────────────────────────────────────────────


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout by revoking refresh token and clearing cookie.
    """
    refresh_token_raw = request.cookies.get("refresh_token")
    if refresh_token_raw:
        await auth_service.logout(
            refresh_token_raw=refresh_token_raw,
            db=db,
        )

    # Clear cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth/refresh",
    )

    return MessageResponse(message="Logged out successfully")
