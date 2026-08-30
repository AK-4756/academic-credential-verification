# backend/core/__init__.py
# Core infrastructure package — config, security, exceptions, logging, constants
#
# Modules:
#   config.py         — Pydantic Settings (environment variables)
#   constants.py      — Application-wide constants and Python ENUM mirrors
#   exceptions.py     — Custom exception hierarchy (20+ classes)
#   security.py       — JWT RS256, bcrypt, token generation
#   logging_config.py — structlog JSON logging configuration
