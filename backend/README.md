# Backend — Academic Credential Verification Platform

FastAPI backend for the Blockchain-Based Academic Credential Verification Platform.

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Framework | FastAPI | >= 0.110.0 |
| Server | Uvicorn | >= 0.29.0 |
| Database | PostgreSQL + asyncpg | 15+ |
| ORM | SQLAlchemy (async) | >= 2.0.0 |
| Migrations | Alembic | >= 1.13.0 |
| Validation | Pydantic v2 | >= 2.6.0 |
| Auth | JWT RS256 (python-jose) | >= 3.3.0 |
| Blockchain | Web3.py | >= 6.15.0 |
| Rate Limiting | SlowAPI | >= 0.1.9 |
| Logging | structlog | >= 24.1.0 |

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (required for Sprint 3)
- Hardhat local node running on port 8545 (for blockchain integration)

## Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Windows only: install python-magic-bin (replaces python-magic)
pip install python-magic-bin>=0.4.14

# 6. Create environment file from template
cp .env.example .env.development

# 7. Generate RS256 key pair (see JWT Keys section below)

# 8. Verify installation
python -c "import fastapi; import web3; print('OK')"
```

## Running the Server

```bash
# Development (with auto-reload)
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

When `SHOW_DOCS=True` in your environment:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Endpoints (Sprint 1)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check — returns `{"status": "ok"}` |

Full API routes (37 endpoints) will be added in Sprints 3-6.

## JWT Keys

Generate an RS256 key pair for JWT authentication:

```bash
# Generate private key
openssl genrsa -out private_key.pem 2048

# Extract public key
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

Then add the key contents to `.env.development` with newlines replaced by `\n`.

## Directory Structure

```
backend/
├── main.py                 ← FastAPI app entry point
├── requirements.txt        ← Production dependencies (15 packages)
├── requirements-dev.txt    ← Development dependencies
├── .env.example            ← Environment variable template
├── .env.development        ← Local dev env vars (gitignored)
├── .python-version         ← Python version specification
├── .gitignore              ← Python-specific ignores
│
├── core/                   ← App-wide infrastructure
│   ├── config.py           ← Pydantic Settings (reads .env)
│   ├── security.py         ← JWT, bcrypt (Sprint 3)
│   ├── exceptions.py       ← Custom exceptions (Sprint 3)
│   ├── logging_config.py   ← structlog config (Sprint 3)
│   └── constants.py        ← App constants (Sprint 3)
│
├── database/               ← SQLAlchemy engine + base (Sprint 3)
├── models/                 ← SQLAlchemy ORM models (Sprint 3)
├── schemas/                ← Pydantic schemas (Sprint 3)
├── repositories/           ← Data access layer (Sprint 4)
├── services/               ← Business logic (Sprint 4-6)
├── routers/                ← FastAPI route handlers (Sprint 4-6)
├── dependencies/           ← FastAPI DI (Sprint 3)
├── middleware/             ← Custom middleware (Sprint 3)
├── blockchain/             ← Web3.py + ABI (Sprint 2)
├── alembic/                ← Database migrations (Sprint 3)
├── tests/                  ← Test suite (Sprint 3+)
├── uploads/                ← Runtime file storage (gitignored)
└── utils/                  ← Infrastructure utilities (Sprint 4)
```

## Environment Variables

See `.env.example` for the complete list of 15 environment variables with descriptions.

## Architecture

- **Pattern**: Modular Monolith (single FastAPI app, clearly separated modules)
- **Layers**: API → Service → Repository → Infrastructure
- **API Prefix**: All routes under `/api/v1/`
- **Auth**: JWT RS256, 15-min access tokens, 7-day refresh tokens (httpOnly cookies)
- **Hashing**: SHA-256 for certificate verification, bcrypt for passwords

For full architecture details, see `docs/backend.md` and `docs/architecture.md`.
