# backend/core/config.py
# Pydantic Settings — centralized configuration from environment variables
#
# Architecture Reference: docs/backend.md Section 27 (core/config.py)
# Environment Variables: docs/repository-structure.md Section 7.1
#
# All configuration is loaded from .env files via pydantic-settings.
# Default values are set for development convenience.
# Production values MUST be set via environment variables or .env.production.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Reads from .env.development in development (via env_file).
    All secrets (JWT keys, DATABASE_URL) must be set in the .env file
    and are NEVER committed to version control.
    """

    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://username:password@localhost:5432/credential_db"

    # --- JWT Authentication (RS256) ---
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Blockchain ---
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    CONTRACT_ADDRESS: str = ""
    NETWORK_CHAIN_ID: int = 31337
    NETWORK_NAME: str = "hardhat"

    # --- File Upload ---
    UPLOAD_ROOT: str = "./uploads"
    MAX_FILE_SIZE_BYTES: int = 10_485_760  # 10MB

    # --- Frontend CORS ---
    FRONTEND_URL: str = "http://localhost:5173"

    # --- Application ---
    SHOW_DOCS: bool = True
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


# Singleton settings instance — import this throughout the application
# Usage: from core.config import settings
settings = Settings()
