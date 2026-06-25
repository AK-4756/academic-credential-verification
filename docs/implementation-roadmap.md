# Blockchain-Based Academic Credential Verification Platform
## Complete Implementation Roadmap — MVP Edition

---

# PRE-PLANNING REVIEW & ASSUMPTION EXTRACTION

## Cross-Document Architecture Summary

```
VERIFIED DECISIONS FROM ALL APPROVED DOCUMENTS
════════════════════════════════════════════════

FROM ARCHITECTURE BLUEPRINT:
├── Single FastAPI monolith (not microservices)
├── React + Vite SPA (not Next.js, not SSR)
├── PostgreSQL with async SQLAlchemy + asyncpg
├── Hardhat local → Sepolia testnet progression
├── MetaMask for all blockchain write operations
├── JWT: RS256, 15-min access token, 7-day refresh (httpOnly cookie)
├── SHA-256 hashing via Python hashlib (stdlib)
├── QR codes via opaque tokens (not certificate UUIDs)
├── Web3.py for blockchain read operations
└── Alembic for database migrations

FROM DATABASE DESIGN:
├── 10 tables: universities, users, students, employers, certificates,
│             blockchain_transactions, qr_verifications, verification_logs,
│             refresh_tokens, audit_log
├── UUID v4 primary keys throughout
├── 6 custom ENUM types
├── DB-level immutability triggers on confirmed certificates
├── Append-only triggers on verification_logs and audit_log
├── 49 indexes for query performance
└── Migrations ordered: 001-012 (sequential)

FROM SMART CONTRACT ARCHITECTURE:
├── Single contract: CertificateRegistry.sol
├── Functions: storeCertificate, revokeCertificate, verifyCertificate,
│             getCertificateRecord, authorizeIssuer, deauthorizeIssuer
├── Hardhat local (chainId 31337) → Sepolia (chainId 11155111)
├── ABI copied to backend/blockchain/abi/ AND frontend/blockchain/
└── >95% test coverage target

FROM BACKEND ARCHITECTURE:
├── 11 services, 8 routers, 9 repositories, 37 endpoints
├── 4-layer: API → Service → Repository → Infrastructure
├── python-magic for MIME validation
├── Pydantic v2 for all schema validation
├── SlowAPI for rate limiting
└── structlog for structured JSON logging

FROM FRONTEND ARCHITECTURE:
├── 17 pages, 23 routes, 45 components
├── React Hook Form for all forms
├── Context API + useReducer (no Redux)
├── Axios with JWT interceptor + auto-refresh
├── html5-qrcode for QR scanning
└── 3 context providers: Auth, Blockchain, Notification

FROM SECURITY ARCHITECTURE:
├── bcrypt cost factor 12
├── RS256 JWT with explicit algorithm pinning
├── Rate limits per endpoint (defined)
├── Input validation: 3 layers (Pydantic + Service + DB constraints)
├── File security: MIME, UUID filenames, outside web root
└── Immutable audit trail (DB triggers)
```

## Carried-Forward Assumptions

```
IMPLEMENTATION ASSUMPTIONS
════════════════════════════

ASSUMPTION 01: Single Developer + AI Assistance
One developer builds the entire system.
AI assists with code generation, debugging, and review.
Timeline is calibrated for this context.

ASSUMPTION 02: Development Machine Requirements
├── OS: macOS/Linux/Windows (WSL recommended for Windows)
├── RAM: 8GB minimum (16GB recommended)
├── Node.js: 18+ LTS
├── Python: 3.11+
├── PostgreSQL: 15+ (local installation or Docker)
├── Git: 2.40+
└── Browser: Chrome/Chromium (MetaMask extension available)

ASSUMPTION 03: No Existing Codebase
Starting from zero. Every file is created in this implementation.

ASSUMPTION 04: Free Development Tools Only
├── Hardhat local node: free
├── Sepolia testnet: free (faucets provide test ETH)
├── PostgreSQL: free (local installation)
├── Infura/Alchemy: free tier (RPC endpoint for Sepolia)
└── GitHub: free (public or private repository)

ASSUMPTION 05: Development Order is Non-Negotiable
Infrastructure before application.
Database before backend services.
Backend before frontend.
Integration testing after both backend and frontend.

ASSUMPTION 06: No Docker for MVP
Direct process execution as per architecture decision.
PostgreSQL installed locally, not containerized.
FastAPI run directly via uvicorn.

ASSUMPTION 07: Iterative Testing
Each component is tested as it is built.
Not deferred to a separate testing phase.
This reduces integration bugs significantly.

ASSUMPTION 08: MetaMask in Chrome
Development and testing uses Chrome browser.
MetaMask extension installed and configured with test wallets.

ASSUMPTION 09: Environment Variables Strategy
One .env.development file per component.
.env.example committed to Git.
.env never committed.

ASSUMPTION 10: Sprint Length = 1 Week
Each sprint represents approximately 5-7 working days.
Total estimated MVP: 12-14 sprints for a focused developer.
```

---

# SECTION 1: DEVELOPMENT STRATEGY

## 1.1 Core Strategy Philosophy

The implementation follows three strategic principles that make a complex blockchain application buildable by a single developer:

**Strategy 1: Proven Foundation First**
Every higher-level component depends on lower-level components being correct. A bug in the database schema propagates into every service. A bug in the smart contract invalidates every certificate. The strategy insists that each foundation layer is proven working before the next layer is built on top of it. This is not just good practice — for a blockchain application where some records are permanent, foundation errors are catastrophically expensive to fix.

**Strategy 2: Vertical Slices Over Horizontal Layers**
After the foundation is established, features are built in complete vertical slices rather than completing an entire horizontal layer before moving to the next. For example, the certificate issuance feature is built end-to-end (contract function → backend service → frontend form) before moving to the certificate verification feature. This approach produces something demonstrable at every stage and catches integration issues early.

**Strategy 3: Test at the Layer, Not Just at the End**
Each module has its tests written and passing before development moves forward. A smart contract is tested before the backend service that calls it is written. A backend service is tested before the frontend that calls it is built. This principle makes integration testing fast because individual components are already proven.

## 1.2 Technology Stack Configuration Matrix

```
TECHNOLOGY DEPENDENCY MATRIX
══════════════════════════════

Layer               Technology          Version     Configuration
──────────────────────────────────────────────────────────────────────────────
Blockchain Layer    Solidity            0.8.19      Via Hardhat compiler
                    Hardhat             2.22+       hardhat.config.js
                    Ethers.js           6.x         Hardhat built-in
                    MetaMask            Latest      Browser extension

Backend Layer       Python              3.11+       Virtual environment
                    FastAPI             0.110+      uvicorn server
                    SQLAlchemy          2.0+        Async mode
                    asyncpg             0.29+       PostgreSQL async driver
                    Alembic             1.13+       Migrations
                    Pydantic            v2          Schema validation
                    python-jose         3.3+        JWT (RS256)
                    passlib[bcrypt]     1.7.4+      Password hashing
                    web3                6.15+       Blockchain reads
                    python-magic        0.4.27+     MIME detection
                    slowapi             0.1.9+      Rate limiting
                    structlog           24.1+       Structured logging
                    qrcode[pil]         7.4+        QR generation

Database Layer      PostgreSQL          15+         Local installation
                    pgcrypto            Extension   gen_random_uuid()

Frontend Layer      React               18+         Vite template
                    Vite                5+          Build tool
                    TailwindCSS         3.4+        Utility CSS
                    React Router        v6          Client routing
                    Axios               1.6+        HTTP client
                    React Hook Form     7.x         Form management
                    Ethers.js           6.x         Blockchain (frontend)
                    html5-qrcode        2.3+        QR scanning
                    qrcode              1.5+        QR display

Dev Tools           Git                 2.40+       Version control
                    GitHub              -           Remote repository
                    Hardhat toolbox     5.x         Testing + coverage
```

---

**[Design Decision A]** The implementation follows **Infrastructure-First ordering** (blockchain → database → backend → frontend) rather than feature-first (build one complete feature before moving to another). **[Why]** For a blockchain application, the smart contract defines the data model that both the database and backend must align with. Building the contract first and proving it works eliminates the risk of building a backend that doesn't match the contract's expectations. **[Requirement satisfied]** All architecture documents follow this sequence. **[Alternative rejected]** Feature-first development: would require building a stub/mock of the smart contract, then throwing it away when the real contract is implemented. Creates throwaway work and dangerous divergence between mock and real behavior.

---

# SECTION 2: BUILD ORDER RATIONALE

## 2.1 Dependency Chain Analysis

```
DEPENDENCY CHAIN — WHY THIS ORDER
════════════════════════════════════

1. PROJECT SETUP (must be first)
   └── Reason: Everything else depends on having a Git repo,
       folder structure, and environment configuration.
       No code can be written without this foundation.

2. SMART CONTRACT (must be second)
   ├── Reason: The contract defines the certificate_uid format,
   │   hash storage format, and blockchain interaction patterns.
   ├── The database certificate_uid format MUST match the contract's
   │   expected string key format.
   ├── The backend's hash conversion must produce what the contract
   │   expects (bytes32).
   └── Building this first means the contract ABI can be copied to
       backend and frontend before those layers are written.

3. DATABASE (third — after contract)
   ├── Reason: The database schema is designed to mirror the
   │   blockchain state (blockchain_status ENUM, sha256_hash format,
   │   certificate_uid format).
   ├── All backend services depend on the database schema.
   └── Migrations run before any backend code touches the database.

4. BACKEND CORE (fourth — after database)
   ├── Reason: Authentication, RBAC, and core infrastructure must
   │   exist before any feature service can be built.
   ├── Security configuration (bcrypt, JWT RS256 keys) must be
   │   established before any endpoint is exposed.
   └── The Axios interceptor in the frontend depends on the exact
       JWT format and error codes the backend produces.

5. BACKEND SERVICES (fifth — after core)
   ├── Certificate service depends on: Hash service, Blockchain service, File service
   ├── Verification service depends on: Hash service, Blockchain service
   └── QR service depends on: Certificate service
       Building in dependency order within services prevents
       import errors and service coupling issues.

6. FRONTEND FOUNDATION (sixth — after backend)
   ├── Reason: The API client (Axios + interceptors) depends on
   │   knowing the exact API response format.
   ├── The BlockchainContext depends on the ABI being ready.
   └── Auth flow depends on the exact JWT payload structure.

7. FRONTEND PORTALS (seventh — sequential)
   ├── University portal first: most complex (blockchain signing)
   ├── Student portal second: simpler (read-only + share)
   └── Employer portal third: verification flow (unique UI needs)

8. INTEGRATION TESTING (eighth)
   └── Tests the combined system — requires all components to be built.

9. SECURITY HARDENING (ninth)
   └── Final security controls applied after functionality is proven.

CRITICAL PATH:
Contract ABI → Backend blockchain/service → Frontend blockchain layer
This path must never be blocked. If the contract changes, the ABI
must be re-copied to backend and frontend immediately.
```

## 2.2 Why Each Dependency Cannot Be Skipped

```
RATIONALE FOR STRICT ORDERING
═══════════════════════════════

Cannot skip contract before database:
→ certificate_uid format used in BOTH contract (string key) and DB (VARCHAR(50))
→ sha256_hash: DB stores 64-char hex; contract stores bytes32
→ These must match. If contract changes, DB must change.
→ Establishing contract first prevents DB redesign.

Cannot skip database before backend:
→ All SQLAlchemy models reference table names defined in migrations
→ Running backend without migrations → immediate startup error
→ Repository layer imports ORM models → import error if models don't match schema

Cannot skip backend auth before backend services:
→ All service endpoints use: get_current_user, require_role dependencies
→ These dependencies import from auth module
→ Circular import if services try to use auth before auth is built

Cannot skip backend before frontend:
→ Axios client.js needs: VITE_API_URL (backend must exist to test against)
→ JWT interceptor needs: exact token format (backend defines this)
→ Error code mapping needs: exact error codes (backend defines these)

Cannot skip any portal component before its API endpoints:
→ useCertificates hook calls POST /certificates/upload
→ If endpoint doesn't exist, hook cannot be tested
→ Testing hooks against real endpoints catches real integration bugs
```

---

# SECTION 3: PROJECT SETUP PHASE

## 3.1 Repository Architecture

```
REPOSITORY SETUP SPECIFICATION
═════════════════════════════════

REPOSITORY STRUCTURE:
├── Repository name: blockchain-credential-platform
├── Type: Single monorepo (all components in one repo)
├── Visibility: Private (during development)
└── Branch strategy: main (protected) + develop + feature/*

MONOREPO RATIONALE:
├── Easier to manage ABI sharing between blockchain/ and backend/frontend/
├── Single CI pipeline (future)
├── Coordinated versioning
└── Single README with full setup instructions


TOP-LEVEL DIRECTORY CREATION ORDER:
─────────────────────────────────────
Step 1: Initialize repository
Step 2: Create directory skeleton:

blockchain-credential-platform/
├── README.md
├── .gitignore                    ← First file committed
├── blockchain/                   ← Smart contracts (Hardhat)
├── backend/                      ← FastAPI application
├── frontend/                     ← React + Vite application
├── docs/                         ← Architecture documents
│   ├── architecture.md
│   ├── database.md
│   ├── smart-contracts.md
│   ├── backend.md
│   ├── frontend.md
│   └── security.md
└── scripts/                      ← Utility scripts (setup, reset)


GIT STRATEGY:
──────────────
Branch naming:
├── main: production-ready code (protected)
├── develop: integration branch
├── feature/blockchain-setup
├── feature/database-migrations
├── feature/auth-service
├── feature/certificate-issuance
├── feature/verification-service
└── feature/university-portal

Commit convention:
format: {type}: {scope}: {description}
types: feat, fix, chore, test, docs, refactor, security
examples:
├── feat: blockchain: add CertificateRegistry contract
├── feat: backend: add certificate issuance service
├── chore: setup: initialize project structure
└── test: smart-contract: add revocation tests

Pull Request policy:
├── Each feature branch → PR to develop
├── develop → main: after milestone testing
└── No direct push to main

.gitignore content (critical items):
├── .env (all environments)
├── *.pem (private keys)
├── node_modules/
├── __pycache__/
├── .venv/
├── blockchain/artifacts/ (generated)
├── blockchain/cache/ (generated)
├── backend/uploads/ (certificate PDFs)
└── coverage/
```

## 3.2 Environment Configuration

```
ENVIRONMENT VARIABLES SETUP
════════════════════════════

BLOCKCHAIN .env (blockchain/.env):
├── DEPLOYER_PRIVATE_KEY=            ← Test wallet private key (Hardhat)
├── SEPOLIA_RPC_URL=                 ← Infura/Alchemy Sepolia endpoint
├── ETHERSCAN_API_KEY=               ← For contract verification
└── INITIAL_OWNER_ADDRESS=           ← Optional override for owner

BACKEND .env (backend/.env):
├── DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/credential_db
├── JWT_PRIVATE_KEY=                 ← RS256 PEM private key
├── JWT_PUBLIC_KEY=                  ← RS256 PEM public key
├── JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
├── JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
├── BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
├── CONTRACT_ADDRESS=                ← Set after contract deployment
├── NETWORK_CHAIN_ID=31337
├── NETWORK_NAME=hardhat
├── UPLOAD_ROOT=/absolute/path/to/backend/uploads
├── MAX_FILE_SIZE_BYTES=10485760
├── FRONTEND_URL=http://localhost:5173
├── SHOW_DOCS=True
└── LOG_LEVEL=DEBUG

FRONTEND .env (frontend/.env.development):
├── VITE_API_URL=http://localhost:8000
└── VITE_CONTRACT_ADDRESS=           ← Set after contract deployment

.env.example files (committed to Git):
├── blockchain/.env.example: all keys with placeholder comments
├── backend/.env.example: all keys with placeholder comments
└── frontend/.env.example: all keys with placeholder comments


RS256 KEY GENERATION SEQUENCE:
────────────────────────────────
Step 1: Generate 2048-bit RSA private key
Step 2: Extract public key from private key
Step 3: Convert PEM to single-line format for .env storage
        (escape newlines as \n in the env var value)
Step 4: Test: encode a JWT with private key, decode with public key

PostgreSQL database setup sequence:
Step 1: Create database: credential_db
Step 2: Create application user: credential_app_user
Step 3: Grant privileges per database design
Step 4: Enable extension: pgcrypto
Step 5: Verify connection from backend .env DATABASE_URL
```

## 3.3 Dependency Installation Sequence

```
INSTALLATION SEQUENCE — CRITICAL ORDER
════════════════════════════════════════

BLOCKCHAIN SETUP:
─────────────────
1. cd blockchain/
2. npm init -y
3. npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
4. npx hardhat init (select: "Create a JavaScript project")
5. Remove default contract files (Lock.sol, etc.)
6. Configure hardhat.config.js per architecture specification
7. Verify: npx hardhat compile (no errors on empty contracts/)

BACKEND SETUP:
───────────────
1. cd backend/
2. python -m venv .venv
3. source .venv/bin/activate (or .venv\Scripts\activate on Windows)
4. Install in order (dependencies matter):
   pip install fastapi uvicorn[standard]
   pip install sqlalchemy[asyncio] asyncpg alembic
   pip install pydantic[email] pydantic-settings
   pip install python-jose[cryptography] passlib[bcrypt]
   pip install python-multipart
   pip install web3
   pip install qrcode[pil]
   pip install python-magic
   pip install slowapi
   pip install structlog
   pip install pytest pytest-asyncio httpx
5. pip freeze > requirements.txt
6. Verify: python -c "import fastapi; print('FastAPI OK')"
7. Verify: python -c "import web3; print('Web3 OK')"
8. Initialize Alembic: alembic init alembic

FRONTEND SETUP:
────────────────
1. cd frontend/
2. npm create vite@latest . -- --template react
   (select React + JavaScript — NOT TypeScript per architecture)
3. npm install
4. npm install -D tailwindcss postcss autoprefixer
5. npx tailwindcss init -p
6. npm install react-router-dom
7. npm install axios
8. npm install react-hook-form
9. npm install ethers
10. npm install html5-qrcode
11. npm install qrcode
12. Configure tailwind.config.js with content paths and custom tokens
13. Configure vite.config.js with path alias @/ → src/
14. Verify: npm run dev (Vite dev server starts on port 5173)
```

---

# SECTION 4: DATABASE IMPLEMENTATION PHASE

## 4.1 Migration Creation Sequence

```
DATABASE IMPLEMENTATION ORDER
═══════════════════════════════

PHASE 4.1: Alembic Configuration
─────────────────────────────────
Step 1: Configure alembic/env.py
├── Import all ORM models
├── Set target_metadata = Base.metadata
└── Configure async engine for migrations

Step 2: Verify connection works
└── alembic current (should show no revisions initially)


PHASE 4.2: ORM Model Creation Order
─────────────────────────────────────
Models must be created in dependency order (FK targets before FK sources):

Order 1: database/base.py (Base declarative class)
Order 2: models/university_model.py (no FKs to other app tables)
Order 3: models/user_model.py (FK to universities)
Order 4: models/student_model.py (FK to users)
Order 5: models/employer_model.py (FK to users)
Order 6: models/certificate_model.py (FK to universities, users)
Order 7: models/blockchain_transaction_model.py (FK to certificates)
Order 8: models/qr_verification_model.py (FK to certificates, users)
Order 9: models/verification_log_model.py (FK to certificates, users, qr_verifications)
Order 10: models/refresh_token_model.py (FK to users)

Each model file created → import verified → no circular import errors


PHASE 4.3: Migration Files (in sequence)
──────────────────────────────────────────

Migration 001: create_enum_types
├── Creates: user_role, blockchain_status, transaction_type,
│            transaction_status, verification_method, verification_result
└── Must be first: all subsequent tables reference these ENUMs

Migration 002: create_universities
├── Creates: universities table
└── Depends on: 001 (no ENUMs yet, but establishes convention)

Migration 003: create_users
├── Creates: users table
└── Depends on: 002 (FK to universities)

Migration 004: create_students
├── Creates: students table
└── Depends on: 003 (FK to users)

Migration 005: create_employers
├── Creates: employers table
└── Depends on: 003 (FK to users)

Migration 006: create_certificates
├── Creates: certificates table
└── Depends on: 002, 003 (FK to universities, users)

Migration 007: create_blockchain_transactions
├── Creates: blockchain_transactions table
└── Depends on: 006 (FK to certificates)

Migration 008: create_qr_verifications
├── Creates: qr_verifications table
└── Depends on: 006, 003 (FK to certificates, users)

Migration 009: create_verification_logs
├── Creates: verification_logs table
└── Depends on: 006, 003, 008 (FK to certificates, users, qr_verifications)

Migration 010: create_refresh_tokens
├── Creates: refresh_tokens table
└── Depends on: 003 (FK to users)

Migration 011: create_audit_log
└── Creates: audit_log table + trigger function

Migration 012: create_indexes
├── Creates: all 49 indexes defined in database design
└── Must be last: tables must exist before indexes are created

Migration 013: create_triggers
├── Creates: immutability triggers on certificates
├── Creates: append-only triggers on verification_logs
└── Creates: audit trigger on sensitive tables


PHASE 4.4: Migration Execution + Verification
──────────────────────────────────────────────
Step 1: alembic upgrade head
Step 2: Verify all tables exist: \dt in psql
Step 3: Verify all ENUMs exist: \dT in psql
Step 4: Verify all indexes: \di in psql
Step 5: Test trigger: attempt UPDATE on verification_logs → should fail

PHASE 4.5: Seed Data
──────────────────────
Seed data for development ONLY (not production):

Seed 1: SUPER_ADMIN user
├── email: admin@platform.dev
├── password: (bcrypt hashed, stored in .env.development only)
└── role: SUPER_ADMIN

Seed 2: Test University
├── name: "Test University"
├── short_code: "TESTUNIV"
├── is_verified: False (must be verified via API)
└── status: pending verification

Seed 3: Test University Admin
├── email: admin@testuniv.edu
├── role: UNIVERSITY_ADMIN
└── university_id: linked to Test University

Note: All seed data is in a separate seed script, never in migrations.
Migrations are schema-only. Seeds are environment-specific.


COMPLETION CRITERIA FOR DATABASE PHASE:
────────────────────────────────────────
☐ alembic upgrade head runs without errors
☐ All 10 tables created and verified
☐ All 6 ENUM types created
☐ All 49 indexes present
☐ All triggers created and tested
☐ ORM models load without import errors
☐ Session factory connects to database successfully
☐ Test CRUD operations via Python REPL succeed
```

---

# SECTION 5: SMART CONTRACT IMPLEMENTATION PHASE

## 5.1 Contract Development Sequence

```
SMART CONTRACT IMPLEMENTATION ORDER
═════════════════════════════════════

PHASE 5.1: Contract File Creation
────────────────────────────────────

File: contracts/CertificateRegistry.sol
Build order within the file:
1. SPDX license + pragma solidity ^0.8.19
2. NatSpec contract documentation
3. ENUM: CertificateStatus { ACTIVE, REVOKED }
4. STRUCT: CertificateRecord { hash, issuer, issuedAt, revokedAt, status, exists }
5. CUSTOM ERRORS (14 error types as specified)
6. EVENTS (5 events: Stored, Revoked, IssuerAuthorized, IssuerDeauthorized, OwnershipTransferred)
7. STATE VARIABLES (5: owner, authorizedIssuers, certificates, totalCertificates, totalRevocations)
8. MODIFIERS (7: onlyOwner, onlyAuthorizedIssuer, certificateMustExist,
              certificateMustBeActive, onlyOriginalIssuer, validCertHash, validCertUid)
9. CONSTRUCTOR
10. ADMIN FUNCTIONS (authorizeIssuer, deauthorizeIssuer, transferOwnership)
11. WRITE FUNCTIONS (storeCertificate, revokeCertificate)
12. VIEW FUNCTIONS (verifyCertificate, getCertificateRecord, isAuthorizedIssuer, getOwner,
                   getCertificateCount, getRevocationCount)

File: contracts/interfaces/ICertificateRegistry.sol
├── Extract all external function signatures
├── Include event declarations
└── Include struct and enum declarations

After each step:
└── npx hardhat compile (must have 0 errors)


PHASE 5.2: Compilation Verification
─────────────────────────────────────
After complete contract is written:
├── npx hardhat compile
├── Verify: artifacts/contracts/CertificateRegistry.sol/ created
├── Verify: CertificateRegistry.json contains ABI field
└── Verify: bytecode is present (not empty)

ABI EXTRACTION (critical step after compilation):
├── Copy ABI JSON to: backend/blockchain/abi/CertificateRegistry.json
└── Copy ABI JSON to: frontend/blockchain/contractABI.js (as JS export)


PHASE 5.3: Test File Creation
───────────────────────────────
Test files created BEFORE running any test:

test/unit/CertificateRegistry.access.test.js
├── 20 test cases (TC-AC-01 through TC-AC-20)
└── Tests: owner, authorizeIssuer, deauthorizeIssuer, transferOwnership

test/unit/CertificateRegistry.storage.test.js
├── 20 test cases (TC-ST-01 through TC-ST-20)
└── Tests: storeCertificate success + all revert conditions

test/unit/CertificateRegistry.verification.test.js
├── 15 test cases (TC-VR-01 through TC-VR-15)
└── Tests: verifyCertificate all return combinations

test/unit/CertificateRegistry.revocation.test.js
├── 15 test cases (TC-RV-01 through TC-RV-15)
└── Tests: revokeCertificate success + all revert conditions

test/integration/IssuanceFlow.test.js
test/integration/VerificationFlow.test.js
test/integration/RevocationFlow.test.js

test/security/AccessControl.security.test.js
test/security/InputValidation.security.test.js
test/security/EdgeCases.security.test.js


PHASE 5.4: Test Execution + Coverage
──────────────────────────────────────
Step 1: npx hardhat test
├── All 87 test cases must PASS
└── 0 failures accepted before moving to deployment

Step 2: npx hardhat coverage
├── Line coverage: >= 95%
├── Branch coverage: >= 95%
├── Function coverage: 100%
└── If coverage below target: add missing tests before proceeding

Step 3: Gas report review
├── npx hardhat test --report-gas
├── storeCertificate: <= 110,000 gas ✓
├── revokeCertificate: <= 65,000 gas ✓
└── authorizeIssuer: <= 55,000 gas ✓


PHASE 5.5: Local Deployment
─────────────────────────────
scripts/deploy.js created first:
├── Compile contract
├── Deploy CertificateRegistry
├── Wait for deployment confirmation
├── Log: contract address, TX hash, block number
├── Save to deployments/hardhat-local/CertificateRegistry.json
└── Copy ABI to backend + frontend paths

Deployment sequence:
Step 1: npx hardhat node (in separate terminal — keep running)
Step 2: npx hardhat run scripts/deploy.js --network hardhat
Step 3: Copy CONTRACT_ADDRESS to backend/.env and frontend/.env.development
Step 4: npx hardhat run scripts/authorize-issuer.js --network hardhat
        (with test university wallet address)
Step 5: Verify: npx hardhat run scripts/check-certificate.js --network hardhat


PHASE 5.6: Post-Deployment Verification
─────────────────────────────────────────
Verification checklist:
☐ Contract deployed at expected address
☐ getCertificateCount() returns 0
☐ getOwner() returns deployer address
☐ ABI copied to backend/blockchain/abi/CertificateRegistry.json
☐ ABI copied to frontend/blockchain/contractABI.js
☐ CONTRACT_ADDRESS set in backend/.env
☐ VITE_CONTRACT_ADDRESS set in frontend/.env.development
☐ Test wallet authorized: isAuthorizedIssuer(wallet) returns true
☐ storeCertificate() works via Hardhat console test call
☐ verifyCertificate() works via Hardhat console test call


PHASE 5.7: Sepolia Deployment (Staging)
──────────────────────────────────────────
This phase done after MVP is functionally complete on local Hardhat.
Prerequisites:
├── Sepolia ETH in deployer wallet (from faucet)
├── SEPOLIA_RPC_URL set (Infura or Alchemy)
└── ETHERSCAN_API_KEY set

Steps:
Step 1: npx hardhat run scripts/deploy.js --network sepolia
Step 2: Wait for 6 block confirmations
Step 3: npx hardhat verify --network sepolia CONTRACT_ADDRESS
Step 4: Update backend/.env (BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, NETWORK_CHAIN_ID=11155111)
Step 5: Update frontend/.env (VITE_CONTRACT_ADDRESS)
Step 6: Full end-to-end test on Sepolia


COMPLETION CRITERIA FOR SMART CONTRACT PHASE:
────────────────────────────────────────────────
☐ Contract compiles without warnings
☐ 87/87 tests passing
☐ >95% test coverage achieved
☐ Gas report within budget
☐ Deployed to local Hardhat successfully
☐ ABI distributed to backend and frontend
☐ CONTRACT_ADDRESS set in all .env files
☐ Test issuance verified via Hardhat console
☐ Test verification verified via Hardhat console
```

---

# SECTION 6: BACKEND IMPLEMENTATION PHASE

## 6.1 Backend Build Order

```
BACKEND IMPLEMENTATION ORDER — COMPLETE
═════════════════════════════════════════

PHASE 6.1: Application Entry Point + Configuration
─────────────────────────────────────────────────────
Files to create (in order):

1. core/config.py
   ├── Pydantic Settings class
   ├── All env variables defined with types
   └── lru_cache for singleton pattern

2. core/logging_config.py
   ├── structlog configuration
   └── JSON formatter for production

3. core/constants.py
   └── Application-wide constants

4. core/exceptions.py
   ├── AppException base class
   ├── All 15 exception subclasses
   └── HTTP status code mapping

5. core/security.py
   ├── RS256 JWT signing (create_access_token)
   ├── RS256 JWT decoding (verify_token)
   ├── bcrypt password hashing (hash_password)
   ├── bcrypt verification (verify_password)
   ├── Refresh token generation (generate_refresh_token)
   └── SHA-256 token hashing (hash_token)

6. database/connection.py
   ├── SQLAlchemy async engine
   ├── async_sessionmaker
   └── Connection pool configuration

7. database/base.py
   └── SQLAlchemy declarative base

8. main.py
   ├── FastAPI app instantiation
   ├── CORS middleware (FRONTEND_URL from config)
   ├── RequestID middleware
   ├── Logging middleware
   ├── Rate limiter initialization
   ├── Global exception handlers
   └── Health check endpoint: GET /health

Verification step:
└── uvicorn main:app --reload
    GET http://localhost:8000/health → {"status": "ok"}
    GET http://localhost:8000/api/v1/openapi.json → OpenAPI spec loads


PHASE 6.2: ORM Models (already exist from database phase)
───────────────────────────────────────────────────────────
Import all models in main.py to ensure they're registered:
└── from models import * (all model files imported)

Verify: uvicorn startup shows no import errors


PHASE 6.3: Dependencies
──────────────────────────
dependencies/database.py → get_db() async generator
dependencies/auth.py → get_current_user()
dependencies/rbac.py → require_role() factory function
dependencies/services.py → get_blockchain_service(), get_file_storage()
dependencies/rate_limiting.py → SlowAPI limiter config

Each dependency verified by importing in Python REPL without errors.


PHASE 6.4: Repositories
─────────────────────────
Build order (same as model order):

repositories/base_repository.py
├── Abstract base with: get_by_id, create, update, list
└── Async session parameter pattern established

repositories/user_repository.py
└── All 10 methods as specified in backend architecture

repositories/university_repository.py
└── All 10 methods

repositories/student_repository.py
repositories/employer_repository.py

repositories/certificate_repository.py
└── All 11 methods (including get_next_uid_sequence — critical method)

repositories/blockchain_transaction_repository.py
repositories/qr_verification_repository.py
repositories/verification_log_repository.py
repositories/refresh_token_repository.py

After each repository:
└── Write basic unit test (test with in-memory SQLite to verify query logic)


PHASE 6.5: Infrastructure Services
────────────────────────────────────

utils/hash_service.py
├── generate_hash_from_file(file_bytes: bytes) → str
├── compare_hashes(a, b) → bool (constant-time)
└── hex_to_bytes32(), bytes32_to_hex() conversion utilities

Test immediately:
├── hash_service test: same bytes → same hash
├── hash_service test: different bytes → different hash
└── hash_service test: output is 64 lowercase hex chars

utils/file_storage_service.py
├── save_certificate(file_bytes, university_id, cert_id) → str
├── get_certificate(file_path) → bytes
└── save_qr_image(image_bytes, cert_id) → str

utils/qr_generator_service.py
└── generate(url: str) → bytes (PNG image)

utils/security_service.py
└── (thin wrapper around core/security.py functions)

blockchain/web3_client.py
└── Web3.py connection setup, contract instance

blockchain/blockchain_service.py
├── verify_certificate(cert_uid, hash_hex) → BlockchainVerificationResult
├── get_certificate_record(cert_uid) → ChainCertificateRecord | None
├── get_transaction_receipt(tx_hash) → TransactionReceipt | None
├── is_authorized_issuer(wallet_address) → bool
└── get_certificate_count() → int

Test blockchain service against running Hardhat node:
├── Deploy test certificate via Hardhat console
└── Python: blockchain_service.get_certificate_record("TEST-2025-00001") → record


PHASE 6.6: Pydantic Schemas
────────────────────────────────
schemas/common_schemas.py
├── StandardResponse (success envelope)
├── PaginatedResponse (paginated data envelope)
├── ErrorResponse (error envelope)
└── Pagination (page, limit, total, has_next, has_prev)

schemas/auth_schemas.py
schemas/user_schemas.py
schemas/university_schemas.py
schemas/student_schemas.py
schemas/employer_schemas.py
schemas/certificate_schemas.py
schemas/verification_schemas.py
schemas/qr_schemas.py
schemas/log_schemas.py

Each schema file: import in Python REPL, verify no validation errors on example data.


PHASE 6.7: Authentication Service + Router
────────────────────────────────────────────
services/auth_service.py
├── register_user()
├── authenticate_user()
├── refresh_access_token()
├── logout()
└── All methods fully implemented

routers/auth_router.py
├── POST /api/v1/auth/register
├── POST /api/v1/auth/login
├── POST /api/v1/auth/refresh
└── POST /api/v1/auth/logout

Register router in main.py.

TEST AUTH ENDPOINTS (before any other service):
├── POST /auth/register → 201 (new user created)
├── POST /auth/register (duplicate) → 409
├── POST /auth/login → 200 + access_token + refresh cookie
├── POST /auth/login (wrong password) → 401
├── POST /auth/login (5 times wrong) → account locked
├── POST /auth/refresh → 200 + new access_token
└── POST /auth/logout → 204

This test block MUST PASS before any other endpoint is built.
Auth is the foundation; if it's wrong, everything built on it is compromised.


PHASE 6.8: University Service + Router
────────────────────────────────────────
services/university_service.py
routers/university_router.py

Endpoints implemented and tested:
├── GET /api/v1/universities/
└── GET /api/v1/universities/{university_id}
    PUT /api/v1/universities/{id}/wallet


PHASE 6.9: Certificate Issuance Service + Router
──────────────────────────────────────────────────
This is the most complex backend service. Build in stages:

Stage A: File upload + hash computation
├── POST /certificates/upload
├── MIME type validation (python-magic)
├── SHA-256 computation
├── DB record creation (PENDING status)
└── Test: upload real PDF → get back sha256_hash

Stage B: Blockchain confirmation
├── POST /certificates/confirm-hash
├── TX receipt validation (web3.eth.get_transaction_receipt)
├── Cross-validation (hash + issuer address)
├── Status update to CONFIRMED
└── Test: upload PDF → simulate TX → confirm → CONFIRMED status

Stage C: Certificate listing + detail
├── GET /certificates/
└── GET /certificates/{id}


PHASE 6.10: Student Service + Router
──────────────────────────────────────
services/student_credential_service.py
routers/student_router.py

├── GET /student/credentials
├── GET /student/credentials/{id}
├── GET /student/credentials/{id}/download (file stream)
└── POST /student/credentials/{id}/share


PHASE 6.11: Verification Service + Router
───────────────────────────────────────────
services/verification_service.py
routers/verification_router.py

├── POST /verify/upload (employer file upload verification)
└── GET  /verify/qr/{token} (public QR verification)

TEST CRITICAL VERIFICATION SCENARIOS:
├── Upload original PDF → result: AUTHENTIC
├── Upload modified PDF (1 byte changed) → result: TAMPERED
├── Upload unknown PDF → result: NOT_FOUND
├── Upload original PDF of revoked cert → result: REVOKED
└── QR token lookup → AUTHENTIC result

These 5 scenarios MUST ALL PASS before moving to frontend.


PHASE 6.12: QR Service + Router
──────────────────────────────────
services/qr_verification_service.py
routers/qr_router.py

├── POST /qr/generate/{certificate_id}
└── GET  /qr/{token}/image


PHASE 6.13: Verification Log + Employer Routers
─────────────────────────────────────────────────
routers/log_router.py
├── GET /logs/
└── GET /logs/{certificate_id}

routers/employer_router.py
├── GET  /employer/profile
├── PUT  /employer/profile
├── GET  /employer/dashboard
├── GET  /employer/verifications
└── GET  /employer/verifications/{id}


PHASE 6.14: Certificate Revocation Service
─────────────────────────────────────────────
services/certificate_revocation_service.py
Add to certificate_router.py:
├── POST /certificates/{id}/revoke
└── POST /certificates/{id}/confirm-revocation


PHASE 6.15: Security Hardening
────────────────────────────────
After all endpoints are functional:
├── Rate limiting: add @limiter.limit() to all endpoints
├── Review: all endpoints have correct require_role() dependency
├── Review: all resource endpoints have ownership checks
├── Verify: DEBUG=False mode shows no stack traces in error responses
└── Run: bandit -r backend/ (security static analysis)


COMPLETION CRITERIA FOR BACKEND PHASE:
────────────────────────────────────────
☐ uvicorn starts with 0 errors
☐ All 37 endpoints registered (verify via /openapi.json)
☐ Auth flow works (register → login → refresh → logout)
☐ Certificate upload computes correct SHA-256
☐ Blockchain confirmation cross-validates correctly
☐ Verification returns correct result for all 4 scenarios
☐ Rate limiting active on auth + verify endpoints
☐ Ownership checks block cross-user access
☐ No stack traces in production-mode error responses
☐ bandit scan: no critical or high issues
```

---

# SECTION 7: FRONTEND IMPLEMENTATION PHASE

## 7.1 Frontend Build Order

```
FRONTEND IMPLEMENTATION ORDER — COMPLETE
═════════════════════════════════════════

PHASE 7.1: Project Foundation
───────────────────────────────
Already done in setup phase (Vite init, npm installs).

Now configure:
1. tailwind.config.js
   ├── Define semantic color tokens:
   │   primary, success, danger, warning, neutral, blockchain
   ├── Configure content paths for all .jsx files
   └── Add custom font: Inter (Google Fonts import in index.html)

2. vite.config.js
   └── Add path alias: @/ → src/

3. src/index.css
   └── @tailwind directives + any global CSS resets

4. src/main.jsx
   └── ReactDOM.createRoot mount (minimal, just render App)

5. src/App.jsx
   └── Placeholder: returns <div>App is working</div>

Verify: npm run dev → browser shows "App is working"
This is the foundation verification.


PHASE 7.2: API Client
──────────────────────
src/api/client.js
├── Axios base instance with baseURL from import.meta.env.VITE_API_URL
├── withCredentials: true (for httpOnly cookie)
├── 30-second timeout
├── Request interceptor: add Authorization header
├── Response interceptor: 401 → try refresh → retry OR logout
└── Module-level token store (updated by AuthContext on login/refresh)

src/api/auth.api.js → login, register, refreshToken, logout
src/api/certificate.api.js → all certificate endpoints
src/api/student.api.js → all student endpoints
src/api/verification.api.js → verify endpoints
src/api/employer.api.js → employer profile + history
src/api/qr.api.js → QR image endpoint
src/api/log.api.js → log endpoints

Test API client in isolation:
└── In browser console: import { login } from '@/api/auth.api'
    login('test@email.com', 'wrongpassword')
    → Should get 401 (backend running; CORS allowing localhost:5173)


PHASE 7.3: Context Providers
──────────────────────────────
context/NotificationContext.jsx (build first — needed by all others)
├── Notification state + reducer
├── Add/remove notification actions
└── Toast component rendered by this context

context/AuthContext.jsx
├── User state, accessToken, isAuthenticated, isLoading
├── LOGIN, LOGOUT, TOKEN_REFRESHED, AUTH_LOADED actions
├── useEffect on mount: attempt token refresh (session restoration)
└── Exposes: user, isAuthenticated, isLoading, dispatch

context/BlockchainContext.jsx
├── MetaMask account, chainId, isConnected, isConnecting
├── CONNECT, DISCONNECT, NETWORK_CHANGED actions
└── Only populated for UNIVERSITY_ADMIN users

Update src/App.jsx:
└── Wrap app with: NotificationContext > AuthContext > BlockchainContext

Test: Log in via API → AuthContext shows isAuthenticated=true, user object populated


PHASE 7.4: Custom Hooks
─────────────────────────
hooks/auth/useAuth.js → reads from AuthContext
hooks/auth/useAuthorization.js → computed permission flags
hooks/blockchain/useMetaMask.js → MetaMask connection logic
hooks/blockchain/useTransaction.js → TX state machine
hooks/shared/useNotification.js → toast dispatch
hooks/shared/usePagination.js → page/limit/total management
hooks/shared/useClipboard.js → copy to clipboard + feedback

Each hook: verify it returns expected shape in React DevTools


PHASE 7.5: Routing Architecture
──────────────────────────────────
routes/AppRoutes.jsx
├── All 23 routes defined
├── Nested route structure per frontend architecture
└── Lazy loading for portal route bundles

components/layout/PrivateRoute.jsx
├── Step 1: isLoading → full-screen spinner
├── Step 2: !isAuthenticated → store intended_path → /auth/login
└── Step 3: wrong role → redirect to own dashboard

Update src/App.jsx:
└── <Router><AppRoutes /></Router> + context providers

Test routing:
├── Navigate to /student/dashboard without login → redirects to /auth/login
├── Login as student → redirects to /student/dashboard
├── Try to navigate to /university/dashboard → redirects to /student/dashboard
└── Navigate to /verify/{random-token} → renders PublicVerificationPage (no redirect)


PHASE 7.6: Primitive Components
──────────────────────────────────
Build in order (each depends on previous):

1. Button.jsx → primary, secondary, danger, ghost, link variants + loading
2. Input.jsx → with label association support
3. Select.jsx → controlled dropdown
4. Textarea.jsx → multi-line input
5. Badge.jsx → colored pill/rectangular
6. Spinner.jsx → sm/md/lg sizes
7. Alert.jsx → info/success/warning/error
8. Modal.jsx → backdrop + focus trap + portal
9. Tooltip.jsx → hover/focus
10. Avatar.jsx → initials-based
11. Divider.jsx → horizontal separator

For each: verify it renders in Storybook-style isolation test page.


PHASE 7.7: Layout Components
──────────────────────────────
components/layout/PublicLayout.jsx → centered card, minimal header
components/layout/VerificationLayout.jsx → minimal header, full width
components/layout/Navbar.jsx → logo, user menu
components/layout/Sidebar.jsx → role-specific nav items
components/layout/PageHeader.jsx → title + breadcrumb + action slot
components/layout/AuthenticatedLayout.jsx → Navbar + Sidebar + content area

Test: Navigate to /auth/login → renders with PublicLayout ✓


PHASE 7.8: Auth Pages
───────────────────────
pages/auth/LoginPage.jsx
├── Email + password form (React Hook Form)
├── Client validation
├── API call → AuthContext dispatch LOGIN
├── Redirect to dashboard
└── Error states: 401, 423 (locked), network error

pages/auth/RegisterPage.jsx
├── Role selector (Student/University Admin/Employer)
├── Conditional fields per role
├── API call → success → redirect to login
└── Server error mapping to form fields

Test registration + login flow completely:
├── Register new student → login → see student dashboard ✓
├── Register new employer → login → see employer dashboard ✓
├── Register university admin → login → see university dashboard ✓


PHASE 7.9: University Portal
──────────────────────────────
Build in this order (most complex portal):

STEP 1: components/shared/composite/WalletConnector.jsx
├── MetaMask detection, connect button, status display
└── Test: connect MetaMask → wallet address shown ✓

STEP 2: pages/university/UniversityDashboard.jsx
├── Stats cards (mock data first, then API integration)
├── Wallet status widget
├── Recent certificates table
└── Test: dashboard loads with real API data ✓

STEP 3: components/university/IssuanceStepper.jsx +
        IssuanceStep1.jsx + IssuanceStep2.jsx + IssuanceStep3.jsx

STEP 4: pages/university/IssueCertificatePage.jsx
├── Full 3-step issuance wizard
├── File upload zone with MIME validation
├── MetaMask transaction signing
├── Blockchain confirmation
└── QR code display on completion

TEST COMPLETE ISSUANCE FLOW:
├── Login as university admin
├── Connect MetaMask (authorized wallet)
├── Upload test PDF
├── Step 1: form submitted → sha256_hash received
├── Step 2: MetaMask popup → approve → tx submitted
├── Step 3: tx confirmed → certificate CONFIRMED
├── QR code generated and displayed
└── Certificate visible in certificate list ✓

STEP 5: pages/university/CertificateListPage.jsx
STEP 6: pages/university/CertificateDetailPage.jsx
STEP 7: pages/university/RevokeCertificatePage.jsx

TEST REVOCATION FLOW:
├── Navigate to certificate detail
├── Click "Revoke Certificate"
├── Enter reason + confirm UID
├── MetaMask popup → approve → revoked ✓


PHASE 7.10: Student Portal
────────────────────────────
pages/student/StudentDashboard.jsx
pages/student/MyCredentialsPage.jsx
pages/student/CredentialDetailPage.jsx
├── CertificateDisplay (styled certificate card component)
└── Download PDF button

pages/student/ShareCredentialPage.jsx
├── QR code display + download
└── Copy verification URL button

TEST STUDENT FLOW:
├── Login as student (whose cert was issued above)
├── See certificate in dashboard ✓
├── View credential detail (styled card) ✓
├── Download PDF ✓
├── Share page: copy URL + QR displayed ✓


PHASE 7.11: Employer Portal
─────────────────────────────
pages/employer/EmployerDashboard.jsx
pages/employer/VerifyCertificatePage.jsx
├── File upload zone
├── Processing steps animation
└── Navigate to result on complete

pages/employer/VerificationResultPage.jsx
├── AUTHENTIC: green banner + certificate details + blockchain proof
├── TAMPERED: red banner + forensic evidence (expanded)
├── REVOKED: orange banner + revocation info
└── NOT_FOUND: gray banner

pages/employer/QRScanPage.jsx
├── html5-qrcode camera scanner
├── Manual URL fallback
└── Navigate to /verify/{token} on scan

pages/employer/VerificationHistoryPage.jsx

TEST EMPLOYER VERIFICATION:
├── Login as employer
├── Upload original certificate PDF → AUTHENTIC ✓
├── Upload modified PDF → TAMPERED ✓
├── Scan QR code from student portal → AUTHENTIC ✓
└── Check verification history → previous results shown ✓


PHASE 7.12: Public Verification Page
──────────────────────────────────────
pages/public/PublicVerificationPage.jsx
├── No auth required
├── Loads on mount: GET /verify/qr/{token}
├── Result display (all 4 outcomes)
└── Mobile-responsive layout

TEST: Navigate to /verify/{valid-token} → AUTHENTIC shown ✓
TEST: Navigate to /verify/{invalid-token} → NOT_FOUND shown ✓


PHASE 7.13: Polish + Error States
────────────────────────────────────
For each page, implement:
├── Loading skeletons (while data fetches)
├── Error state with retry button
├── Empty state with helpful CTA
└── Verify empty state messages are role-appropriate


COMPLETION CRITERIA FOR FRONTEND PHASE:
────────────────────────────────────────
☐ All 17 pages render without console errors
☐ All 23 routes navigate correctly
☐ Auth flow complete (register, login, refresh, logout)
☐ University issuance flow works end-to-end
☐ Student credential view, download, share works
☐ Employer file upload verification returns correct results
☐ QR scanner works on mobile Chrome
☐ Public verification page works without login
☐ No localStorage/sessionStorage usage for JWT
☐ All forms validate before submission
☐ All loading states implemented
☐ All error states implemented
```

---

# SECTION 8: INTEGRATION PHASE

## 8.1 Integration Verification Sequences

```
INTEGRATION PHASE — COMPLETE
══════════════════════════════

INTEGRATION 1: Frontend ↔ Backend (API Layer)
───────────────────────────────────────────────
Test sequence (requires both running):

Auth Integration:
├── Frontend login form → POST /auth/login → JWT in memory ✓
├── Axios interceptor attaches token to all subsequent requests ✓
├── Token expires → interceptor refreshes silently → request retried ✓
└── Logout → cookie cleared → subsequent requests return 401 ✓

File Upload Integration:
├── Frontend FileUploadZone → FormData → Axios multipart → Backend MIME check ✓
├── Upload progress shown (Axios onUploadProgress) ✓
└── sha256_hash returned from backend → displayed in Step 1 ✓

Blockchain Integration (frontend ↔ backend ↔ blockchain):
├── Frontend receives hash → ethers.js converts to bytes32 ✓
├── MetaMask signs storeCertificate(uid, bytes32_hash) ✓
├── Frontend sends tx_hash to POST /certificates/confirm-hash ✓
├── Backend verifies TX on chain ✓
└── Backend returns CONFIRMED status ✓

Verification Integration:
├── Employer uploads PDF → backend hashes → blockchain queried → result returned ✓
├── QR token → backend looks up → blockchain queried → result returned ✓
└── Frontend displays result matching backend enum value ✓


INTEGRATION 2: Backend ↔ Database
───────────────────────────────────
Test all repository methods against real PostgreSQL:
├── UserRepository.get_by_email: returns user with all fields ✓
├── CertificateRepository.get_next_uid_sequence: atomic + unique ✓
├── Concurrent issuance: two requests simultaneously → UIDs are different ✓
├── Immutability trigger: attempt to UPDATE sha256_hash on CONFIRMED cert → exception ✓
├── Append-only trigger: attempt UPDATE on verification_log → exception ✓
└── Audit log: UPDATE on users table → audit_log entry created ✓


INTEGRATION 3: Backend ↔ Blockchain (Web3.py)
───────────────────────────────────────────────
Test all blockchain service operations:
├── Issue cert via MetaMask → getCertificateRecord returns record ✓
├── blockchain_service.verify_certificate(uid, original_hash) → (True, ACTIVE) ✓
├── blockchain_service.verify_certificate(uid, tampered_hash) → (False, ACTIVE) ✓
├── Revoke cert → blockchain_service.verify_certificate → (False, REVOKED) ✓
└── blockchain_service.is_authorized_issuer(wallet) → True ✓


INTEGRATION 4: End-to-End User Journey Tests
─────────────────────────────────────────────
Full flow test 1: Certificate Issuance Journey
1. Register university admin account
2. Login → navigate to university dashboard
3. Connect MetaMask (authorized test wallet)
4. Navigate to Issue Certificate
5. Fill form (test student email, degree, date)
6. Upload test PDF
7. Observe: sha256_hash displayed, certificate UID assigned
8. Click "Sign Transaction" → MetaMask popup → approve
9. Observe: TX hash, "confirming..." state
10. Backend confirms → QR code generated
11. Observe: QR displayed, certificate shows CONFIRMED
12. Login as student → see certificate in credentials list
Expected: Entire flow completes without error

Full flow test 2: Verification Journey (Authentic)
1. Login as employer
2. Navigate to Verify Certificate
3. Upload the same PDF used in test 1
4. Observe: processing steps animation
5. Navigate to result page
6. Observe: AUTHENTIC result, blockchain proof, certificate details
7. Click Etherscan link → TX visible on Hardhat explorer
Expected: AUTHENTIC result with all details

Full flow test 3: Tampered Certificate Detection
1. Take the same PDF → open in hex editor → change 1 byte
2. Login as employer
3. Upload modified PDF
4. Observe: TAMPERED result
5. Observe: forensic evidence section (submitted hash ≠ stored hash)
Expected: TAMPERED result, both hashes shown

Full flow test 4: QR Verification Journey
1. Login as student
2. Navigate to Share Credential
3. Copy QR code verification URL
4. Open new browser tab (incognito — not logged in)
5. Paste URL → navigate
6. Observe: PublicVerificationPage loads, AUTHENTIC shown
7. On mobile: scan QR with camera → same result
Expected: AUTHENTIC result without login

Full flow test 5: Certificate Revocation
1. Login as university admin
2. Navigate to certificate detail
3. Click Revoke → enter reason → enter certificate UID to confirm
4. MetaMask popup → approve → confirmed
5. Login as employer
6. Upload the same certificate PDF
7. Observe: REVOKED result
Expected: REVOKED result with revocation date and reason
```

---

# SECTION 9: TESTING PHASE

## 9.1 Test Suite Architecture

```
TESTING PHASE — COMPLETE SPECIFICATION
════════════════════════════════════════

TEST EXECUTION SEQUENCE (run in this order):
─────────────────────────────────────────────

LEVEL 1: Smart Contract Tests (run on every contract change)
├── npx hardhat test
├── All 87 test cases: unit + integration + security
├── Coverage: npx hardhat coverage → >95%
└── Gas: npx hardhat test --report-gas → within budget

LEVEL 2: Backend Unit Tests
├── pytest tests/unit/ -v
├── Services tested with mocked repositories
├── Hash service: determinism, format, constant-time comparison
├── Blockchain service: mocked Web3.py responses
└── Coverage: pytest --cov=backend → >85%

LEVEL 3: Backend Integration Tests
├── pytest tests/integration/ -v
├── Full workflow tests against real test database
├── Real blockchain calls against Hardhat local node
└── Covers: auth flow, issuance flow, verification flow, revocation flow

LEVEL 4: Backend API Tests
├── pytest tests/api/ -v
├── httpx TestClient against real FastAPI app
├── Tests all 37 endpoints
└── Includes: auth, RBAC, ownership, rate limiting

LEVEL 5: Frontend Unit Tests
├── npm test (Vitest)
├── All custom hooks tested via renderHook
├── All primitive + composite components tested
└── Coverage: >80% on components/ and hooks/

LEVEL 6: Frontend Integration Tests
├── RTL + MSW API mocking
├── Key user journeys in simulated browser
└── Critical: auth flow, verification result display

LEVEL 7: Security Tests
├── Backend: pytest tests/security/ -v
│   Covers: auth bypass, role escalation, injection attempts, file upload
├── Contract: test/security/ (Hardhat)
│   Covers: unauthorized access, double operations, cross-user attacks
└── Frontend: jest-axe accessibility violations

LEVEL 8: End-to-End Tests
├── Manual execution of 5 full journey tests (Section 8)
└── Documented pass/fail with screenshots

SECURITY-SPECIFIC TEST CHECKLIST:
────────────────────────────────────
☐ Login with wrong email → 401 (same message as wrong password)
☐ Login with wrong password → 401
☐ Login 6 times wrong → 401 then 423 (locked)
☐ JWT with algorithm "none" → 401 rejected
☐ JWT with HS256 (not RS256) → 401 rejected
☐ JWT payload role changed (tampered) → 401 (signature invalid)
☐ Student accesses POST /certificates/upload → 403
☐ Student accesses another student's credential → 403
☐ Employer accesses /student/credentials → 403
☐ University admin revokes another university's cert → 403
☐ Upload script.exe renamed to .pdf → 400 (MIME rejected)
☐ Upload empty file → 400
☐ Upload 11MB file → 400 (size limit)
☐ Path traversal filename → UUID stored safely
☐ QR token with invalid format → 404
☐ Rate limit: 6th login attempt → 429
☐ Rate limit: 11th verify/upload → 429


PERFORMANCE BENCHMARKS (manual):
──────────────────────────────────
☐ SHA-256 computation for 10MB PDF: < 2 seconds
☐ POST /certificates/upload: < 5 seconds (10MB PDF)
☐ POST /verify/upload + blockchain query: < 10 seconds
☐ GET /verify/qr/{token}: < 5 seconds
☐ Dashboard load: < 3 seconds
```

---

# SECTION 10: DEPLOYMENT PREPARATION PHASE

## 10.1 Production Configuration

```
DEPLOYMENT PREPARATION — COMPLETE
═══════════════════════════════════

ENVIRONMENT VARIABLE PRODUCTION CHECKLIST:
────────────────────────────────────────────

Backend Production .env changes:
├── DATABASE_URL=postgresql+asyncpg://prod_user:strong_pass@db_host:5432/credential_db_prod
├── JWT_PRIVATE_KEY=<2048-bit RSA private key PEM — from secure generation>
├── JWT_PUBLIC_KEY=<corresponding public key PEM>
├── BLOCKCHAIN_RPC_URL=https://sepolia.infura.io/v3/{PROJECT_ID}
├── CONTRACT_ADDRESS=<Sepolia deployed contract address>
├── NETWORK_CHAIN_ID=11155111 (Sepolia)
├── NETWORK_NAME=sepolia
├── UPLOAD_ROOT=/production/path/to/secure/uploads
├── MAX_FILE_SIZE_BYTES=10485760
├── FRONTEND_URL=https://yourdomain.com (HTTPS — exact URL)
├── SHOW_DOCS=False (CRITICAL: disable Swagger in production)
├── DEBUG=False
└── LOG_LEVEL=INFO

Frontend Production .env:
├── VITE_API_URL=https://api.yourdomain.com
└── VITE_CONTRACT_ADDRESS=<Sepolia contract address>


PRODUCTION BUILD CHECKLIST:
─────────────────────────────

Backend:
☐ DEBUG=False verified
☐ SHOW_DOCS=False verified (visit /docs → 404)
☐ CORS: only production FRONTEND_URL (not localhost)
☐ Rate limiting: verify SlowAPI active
☐ bcrypt cost 12: benchmark on production hardware (must be ~300ms)
☐ RS256 keys: generated on production server (private key never transmitted)
☐ File upload directory: outside web root, created with 750 permissions
☐ PostgreSQL: production user has minimal privileges (not SUPERUSER)
☐ Database SSL: ssl=require in DATABASE_URL
☐ Log format: JSON (structured, not debug text)
☐ bandit scan: 0 critical, 0 high issues

Frontend:
☐ npm run build completes with 0 errors
☐ dist/ directory created
☐ Source maps: ABSENT from dist/ (vite.config.js: build.sourcemap=false)
☐ Console.logs: ABSENT from built JS (vite esbuild.drop=['console','debugger'])
☐ VITE_API_URL: HTTPS URL (not HTTP)
☐ No localhost URLs in built bundle

Smart Contract:
☐ Deployed to Sepolia testnet
☐ Contract verified on Etherscan (source visible)
☐ ABI files: copied to backend and frontend from Sepolia deployment
☐ CONTRACT_ADDRESS: Sepolia address (not local Hardhat)
☐ At least one university wallet authorized on Sepolia contract


NGINX CONFIGURATION REQUIREMENTS:
────────────────────────────────────
Security headers required:
├── Strict-Transport-Security: max-age=31536000; includeSubDomains
├── X-Content-Type-Options: nosniff
├── X-Frame-Options: DENY
├── Referrer-Policy: strict-origin-when-cross-origin
└── Content-Security-Policy: (defined per frontend security architecture)

HTTP → HTTPS redirect: required (301 permanent)
/uploads/ directory: NOT in Nginx web root
TLS: 1.2 minimum (disable TLS 1.0, TLS 1.1)
Certificate: Let's Encrypt (via Certbot)


PRE-LAUNCH VALIDATION:
───────────────────────
☐ Health check: GET /health → {"status": "ok"}
☐ API accessible at HTTPS URL
☐ Login works on production
☐ File upload works on production
☐ Blockchain connection: is_authorized_issuer returns correct result
☐ QR scan works on mobile browser
☐ Rate limiting verified on production (login 6x → 429)
☐ CORS: requests from frontend URL succeed; from random URL fail
☐ Swagger UI returns 404 or is not accessible
☐ /uploads/ not accessible directly via browser (returns 403/404)
☐ No sensitive data in browser network tab response headers
```

---

# SECTION 11: DETAILED SPRINT PLAN

## Sprint Overview

```
SPRINT PLAN OVERVIEW
══════════════════════

Total Sprints: 12
Sprint Duration: 1 week each
Developer: Single developer with AI assistance
Estimated Total: 12-14 weeks

Sprint Structure:
├── Sprint 1: Project Setup + Smart Contract Development
├── Sprint 2: Smart Contract Testing + Deployment + Database Setup
├── Sprint 3: Backend Core (Config, Auth, Security)
├── Sprint 4: Backend Infrastructure Services
├── Sprint 5: Backend Certificate Services
├── Sprint 6: Backend Verification + Revocation Services
├── Sprint 7: Frontend Foundation + Auth Pages
├── Sprint 8: University Portal
├── Sprint 9: Student + Employer Portals
├── Sprint 10: Public Verification + Integration
├── Sprint 11: Testing Phase (All Levels)
└── Sprint 12: Security Hardening + Deployment Prep
```

## Sprint 1: Project Setup + Smart Contract

```
SPRINT 1: PROJECT SETUP + SMART CONTRACT DEVELOPMENT
═════════════════════════════════════════════════════

SPRINT GOAL:
Have the project repository set up, development environment configured,
and the CertificateRegistry smart contract written and compiling.

WEEK: 1
DURATION: 5-7 working days

DELIVERABLES:
├── D1: Git repository initialized with branch strategy
├── D2: Top-level directory structure created
├── D3: Architecture documents in docs/ directory
├── D4: .gitignore with all correct exclusions
├── D5: blockchain/ package.json + hardhat.config.js configured
├── D6: backend/ virtual environment + requirements.txt
├── D7: frontend/ Vite + React + TailwindCSS initialized
├── D8: All .env.example files created
├── D9: RS256 key pair generated (private key in backend/.env only)
├── D10: PostgreSQL database created with application user
├── D11: CertificateRegistry.sol complete and compiling
├── D12: ICertificateRegistry.sol interface created
├── D13: ABI extracted to backend/blockchain/abi/
└── D14: ABI exported to frontend/blockchain/contractABI.js

DEPENDENCIES:
├── Node.js 18+ installed
├── Python 3.11+ installed
├── PostgreSQL 15+ installed
├── Git installed
├── Chrome + MetaMask extension installed
└── Code editor (VS Code recommended)

DAILY BREAKDOWN:
Day 1: Repository setup, directory structure, .gitignore, all .env.example files
Day 2: Backend environment setup (venv, all pip installs, requirements.txt)
Day 3: Frontend setup (Vite init, all npm installs, TailwindCSS config)
Day 4: Blockchain setup (Hardhat init, config), PostgreSQL database creation
Day 5: RS256 key generation, CertificateRegistry.sol (data structures + errors)
Day 6: CertificateRegistry.sol (functions), compile verification, ABI extraction
Day 7: Code review, fix compilation warnings, commit all to develop branch

COMPLETION CRITERIA:
☐ git status: all files committed, no unstaged changes
☐ npx hardhat compile: exits with code 0, 0 errors
☐ python -c "import fastapi; import web3; print('OK')" → OK
☐ npm run dev: Vite dev server starts on port 5173
☐ psql -U credential_app_user -d credential_db: connection successful
☐ RS256 test: encode JWT with private key → decode with public key → payload matches
☐ ABI file exists at: backend/blockchain/abi/CertificateRegistry.json

RISKS THIS SPRINT:
├── python-magic libmagic system dependency: may require brew/apt install
├── PostgreSQL user permission setup: may need superuser for initial setup
└── RS256 key format: PEM → env var escaping requires careful handling
```

## Sprint 2: Smart Contract Testing + Database

```
SPRINT 2: SMART CONTRACT TESTING + DATABASE IMPLEMENTATION
═══════════════════════════════════════════════════════════

SPRINT GOAL:
Smart contract has >95% test coverage and passes all 87 tests.
Database schema is fully implemented with all tables, triggers, and indexes.

WEEK: 2
DURATION: 5-7 working days

DELIVERABLES:
├── D1: All 87 smart contract test cases written
├── D2: 87/87 tests passing
├── D3: Test coverage >95% verified
├── D4: Gas report within budget for all functions
├── D5: Contract deployed to local Hardhat node
├── D6: Deployment record in deployments/hardhat-local/
├── D7: CONTRACT_ADDRESS set in backend/.env and frontend/.env
├── D8: All 10 ORM model files created
├── D9: All 13 Alembic migrations written
├── D10: alembic upgrade head runs successfully
├── D11: All 10 tables verified in PostgreSQL
├── D12: All 6 ENUM types created
├── D13: All 49 indexes created
├── D14: All immutability + audit triggers verified working
└── D15: Seed script creates test data successfully

DEPENDENCIES:
├── Sprint 1 completed (contract source, database access)
└── Hardhat node runnable (npx hardhat node works)

DAILY BREAKDOWN:
Day 1: Unit tests for access control (TC-AC-01 to TC-AC-20)
Day 2: Unit tests for storage + verification (TC-ST-01 to TC-VR-15)
Day 3: Unit tests for revocation, integration + security tests
Day 4: Fix any failing tests, achieve >95% coverage
Day 5: Deploy to local Hardhat, authorize test wallet, verify scripts
Day 6: ORM models (all 10), base repository
Day 7: Alembic migrations (001-013), alembic upgrade head, trigger verification

COMPLETION CRITERIA:
☐ npx hardhat test: 87/87 PASSING
☐ npx hardhat coverage: >95% line + branch, 100% function
☐ Gas report: all functions within budget
☐ npx hardhat node: running, contract deployed
☐ isAuthorizedIssuer(test_wallet): returns True
☐ alembic upgrade head: exits 0
☐ All 10 tables in psql \dt output
☐ Trigger test: UPDATE on confirmed cert → exception raised
☐ Trigger test: UPDATE on verification_log → exception raised

RISKS THIS SPRINT:
├── Gas budget may be exceeded by complex modifier chains
│   Mitigation: review gas report early, optimize if needed
├── Alembic migration ordering: FK constraints may fail if wrong order
│   Mitigation: strictly follow dependency order in Section 4
└── Trigger creation: PostgreSQL-specific syntax may need debugging
```

## Sprint 3: Backend Core

```
SPRINT 3: BACKEND CORE
════════════════════════

SPRINT GOAL:
Authentication, authorization, and core infrastructure fully operational.
All 37 endpoints registered. Auth endpoints tested and working.

WEEK: 3
DURATION: 5-7 working days

DELIVERABLES:
├── D1: core/config.py with all settings
├── D2: core/exceptions.py with 15 exception classes
├── D3: core/security.py (JWT RS256 + bcrypt + token utilities)
├── D4: core/logging_config.py (structlog JSON)
├── D5: database/connection.py (async engine + sessionmaker)
├── D6: main.py (app, middleware, routers, exception handlers)
├── D7: dependencies/ (get_db, get_current_user, require_role, get_blockchain)
├── D8: All 9 repository files created
├── D9: All Pydantic schema files created
├── D10: services/auth_service.py complete
├── D11: routers/auth_router.py complete
├── D12: GET /health → 200 working
└── D13: All auth endpoints tested and passing

DEPENDENCIES:
├── Sprint 1 (environment, keys)
├── Sprint 2 (database schema ready)
└── Hardhat node running (blockchain service needs it for startup)

DAILY BREAKDOWN:
Day 1: core/* files, database/connection.py, main.py skeleton
Day 2: All dependencies/* files, rate limiter setup
Day 3: All repository files (using base repository pattern)
Day 4: All Pydantic schema files (validate with example data)
Day 5: services/auth_service.py (all 5 methods)
Day 6: routers/auth_router.py, register in main.py
Day 7: Test all auth endpoints (pytest tests/api/test_auth_endpoints.py)

COMPLETION CRITERIA:
☐ uvicorn main:app: starts with 0 errors
☐ GET /health: 200 {"status": "ok"}
☐ POST /auth/register: 201 (new user)
☐ POST /auth/register (duplicate): 409
☐ POST /auth/login: 200 + access_token in body + refresh cookie
☐ POST /auth/login (wrong pass): 401
☐ POST /auth/login x5 wrong: account locked on 5th
☐ POST /auth/refresh: 200 + new access_token + new cookie
☐ POST /auth/logout: 204 + cookie cleared
☐ Protected endpoint without token: 401
☐ Protected endpoint with wrong role: 403
☐ All pytest tests/api/test_auth_endpoints.py: PASSING

RISKS THIS SPRINT:
├── RS256 JWT decode: algorithm must be explicitly pinned to ["RS256"]
│   Mitigation: verify algorithm confusion test case passes
├── httpOnly cookie + CORS: withCredentials required on Axios
│   Mitigation: test cookie roundtrip before other services
└── Async SQLAlchemy session management: session must commit before refresh
```

## Sprint 4: Backend Infrastructure Services

```
SPRINT 4: BACKEND INFRASTRUCTURE SERVICES
═══════════════════════════════════════════

SPRINT GOAL:
All infrastructure services (hashing, file storage, blockchain, QR)
implemented and tested. University + student services complete.

WEEK: 4
DURATION: 5-7 working days

DELIVERABLES:
├── D1: utils/hash_service.py (SHA-256 + comparison + conversion)
├── D2: utils/file_storage_service.py (save + retrieve PDFs)
├── D3: utils/qr_generator_service.py (generate QR PNG)
├── D4: blockchain/web3_client.py (Web3.py connection)
├── D5: blockchain/blockchain_service.py (all 5 methods)
├── D6: services/university_service.py
├── D7: routers/university_router.py
├── D8: services/student_service.py
├── D9: services/employer_service.py
├── D10: Unit tests for hash_service (determinism, format, timing)
├── D11: Unit tests for blockchain_service (mocked Web3)
└── D12: Integration tests: blockchain_service against real Hardhat

DEPENDENCIES:
├── Sprint 3 (auth working, repositories ready)
└── Hardhat node with contract deployed

DAILY BREAKDOWN:
Day 1: hash_service.py + hash_service tests (all passing)
Day 2: file_storage_service.py (save/retrieve PDFs, path validation)
Day 3: qr_generator_service.py, blockchain/web3_client.py
Day 4: blockchain/blockchain_service.py (all 5 methods)
Day 5: Test blockchain service against Hardhat (all scenarios)
Day 6: university_service + router, student_service, employer_service
Day 7: Integration tests: file upload + hash + blockchain query chain

COMPLETION CRITERIA:
☐ hash_service: same PDF → same hash (10 repetitions)
☐ hash_service: modified PDF → different hash
☐ hash_service: output is always 64 lowercase hex chars
☐ file_storage_service: PDF saved at correct path with UUID filename
☐ file_storage_service: path traversal attempt rejected
☐ blockchain_service.verify_certificate: AUTHENTIC for matching hash
☐ blockchain_service.verify_certificate: TAMPERED for different hash
☐ blockchain_service.verify_certificate: REVOKED for revoked cert
☐ blockchain_service.get_certificate_record: returns correct struct
☐ University endpoints: GET / and GET /{id} working

RISKS THIS SPRINT:
├── python-magic MIME detection may fail on some PDF variants
│   Mitigation: test with multiple PDF files (created by Word, Google Docs, LaTeX)
├── Web3.py bytes32 conversion must match exactly what contract expects
│   Mitigation: verify conversion by storing hash via Hardhat and reading via Web3.py
└── File storage path: must work on both macOS (/ separators) and Linux
```

## Sprint 5: Backend Certificate Services

```
SPRINT 5: BACKEND CERTIFICATE ISSUANCE + CORE SERVICES
══════════════════════════════════════════════════════════

SPRINT GOAL:
Complete certificate issuance service with blockchain integration.
Upload → hash → PENDING → MetaMask (manual test) → CONFIRMED.

WEEK: 5
DURATION: 5-7 working days

DELIVERABLES:
├── D1: services/certificate_issuance_service.py (Phase 1: upload + hash)
├── D2: services/certificate_issuance_service.py (Phase 2: confirmation)
├── D3: services/qr_verification_service.py
├── D4: routers/certificate_router.py (all 6 certificate endpoints)
├── D5: routers/qr_router.py
├── D6: services/student_credential_service.py (all 4 methods)
├── D7: routers/student_router.py (all 4 endpoints)
├── D8: Integration tests: complete issuance flow
└── D9: Manual test: complete 5-step issuance flow via Postman

DEPENDENCIES:
├── Sprint 4 (hash service, file service, blockchain service ready)
└── Hardhat node with authorized test wallet

DAILY BREAKDOWN:
Day 1: certificate_issuance_service.py Phase 1 (upload + hash + PENDING)
Day 2: POST /certificates/upload endpoint, test via Postman
Day 3: certificate_issuance_service.py Phase 2 (confirmation + cross-validation)
Day 4: POST /certificates/confirm-hash endpoint, test via Postman
       Manual: use MetaMask to actually sign a storeCertificate TX
Day 5: GET /certificates/ and GET /certificates/{id}, certificate detail
Day 6: qr_verification_service.py, qr_router.py, student_credential_service.py
Day 7: student_router.py, integration tests, revocation initiation endpoint

COMPLETION CRITERIA:
☐ POST /certificates/upload: returns sha256_hash + certificate_id
☐ POST /certificates/upload: MIME rejection for non-PDF
☐ POST /certificates/upload: duplicate hash → 409
☐ Manual: MetaMask signs TX → tx_hash obtained
☐ POST /certificates/confirm-hash: CONFIRMED status returned
☐ POST /certificates/confirm-hash: cross-validation detects hash mismatch
☐ GET /certificates/: returns paginated list for university admin
☐ GET /student/credentials: returns student's certificates
☐ GET /student/credentials/{id}/download: returns PDF stream
☐ QR code generated automatically on CONFIRMED status

RISKS THIS SPRINT:
├── MetaMask manual test: developer must have Hardhat wallet in MetaMask
│   Mitigation: import Hardhat default account #0 private key into MetaMask
├── TX cross-validation timing: TX may not be mined immediately
│   Mitigation: implement polling with 3-retry logic
└── Certificate UID sequence: concurrent requests may conflict
    Mitigation: use SELECT FOR UPDATE or atomic increment
```

## Sprint 6: Backend Verification + Revocation

```
SPRINT 6: BACKEND VERIFICATION + REVOCATION + LOG SERVICES
════════════════════════════════════════════════════════════

SPRINT GOAL:
All verification scenarios working (AUTHENTIC, TAMPERED, REVOKED, NOT_FOUND).
Certificate revocation complete. All 37 endpoints live.

WEEK: 6
DURATION: 5-7 working days

DELIVERABLES:
├── D1: services/verification_service.py (file upload + QR verification)
├── D2: services/verification_log_service.py
├── D3: routers/verification_router.py
├── D4: services/certificate_revocation_service.py
├── D5: Add revocation endpoints to certificate_router.py
├── D6: services/employer_service.py (profile + history)
├── D7: routers/employer_router.py
├── D8: routers/log_router.py
├── D9: All 37 endpoints registered and returning correct responses
├── D10: Security tests: auth bypass, RBAC violations, file upload
└── D11: bandit scan: 0 critical/high issues

DEPENDENCIES:
├── Sprint 5 (issuance complete — need confirmed certificates to test verification)

DAILY BREAKDOWN:
Day 1: verification_service.py (verify_by_file_upload)
Day 2: verification_service.py (verify_by_qr_token), verification_router.py
Day 3: Test all 4 verification scenarios thoroughly
Day 4: certificate_revocation_service.py, add revocation endpoints
Day 5: Test revocation flow (initiate → MetaMask → confirm → REVOKED)
Day 6: employer_router.py, log_router.py, verification_log_service.py
Day 7: Security tests, bandit scan, fix issues, rate limiting verification

COMPLETION CRITERIA:
☐ POST /verify/upload: AUTHENTIC for original PDF
☐ POST /verify/upload: TAMPERED for modified PDF (1 byte changed)
☐ POST /verify/upload: NOT_FOUND for unknown PDF
☐ GET /verify/qr/{token}: correct result for valid token
☐ GET /verify/qr/{invalid}: 404
☐ POST /certificates/{id}/revoke: initiation returns instructions
☐ POST /certificates/{id}/confirm-revocation: REVOKED status
☐ POST /verify/upload on revoked cert: REVOKED result
☐ All 37 endpoints return correct responses (verified via OpenAPI)
☐ bandit -r backend/: 0 critical, 0 high
☐ Rate limit test: 11th verify/upload → 429

RISKS THIS SPRINT:
├── Verification result for TAMPERED: backend must query blockchain
│   (not just compare DB hashes) — verify this in code review
├── Revocation cross-validation: same pattern as issuance confirmation
└── Verification log immutability: test that log creation works
    but UPDATE/DELETE triggers correctly reject modifications
```

## Sprint 7: Frontend Foundation + Auth

```
SPRINT 7: FRONTEND FOUNDATION + AUTH
═══════════════════════════════════════

SPRINT GOAL:
Complete frontend foundation (API client, contexts, routing, primitives).
Auth pages fully working with real backend.

WEEK: 7
DURATION: 5-7 working days

DELIVERABLES:
├── D1: TailwindCSS semantic color tokens configured
├── D2: Vite path alias @/ configured
├── D3: api/client.js (Axios + interceptors + auto-refresh)
├── D4: All 8 API module files (auth, cert, student, verify, employer, qr, log)
├── D5: context/NotificationContext.jsx + toast component
├── D6: context/AuthContext.jsx (login, logout, refresh, session restoration)
├── D7: context/BlockchainContext.jsx (MetaMask connection)
├── D8: All 8 custom hooks created
├── D9: routes/AppRoutes.jsx (all 23 routes)
├── D10: components/layout/PrivateRoute.jsx (all 3 steps)
├── D11: All 11 primitive components built and verified
├── D12: All layout components (PublicLayout, Navbar, Sidebar, PageHeader)
├── D13: pages/auth/LoginPage.jsx
└── D14: pages/auth/RegisterPage.jsx

DEPENDENCIES:
├── Sprint 6 (all backend endpoints working)
└── Backend running on localhost:8000

DAILY BREAKDOWN:
Day 1: TailwindCSS config, Vite alias, api/client.js + interceptors
Day 2: All 8 API modules, NotificationContext + toast
Day 3: AuthContext (login, logout, token refresh, session restoration)
Day 4: BlockchainContext, all 8 custom hooks, AppRoutes.jsx
Day 5: PrivateRoute.jsx, all 11 primitive components
Day 6: Layout components (PublicLayout, AuthenticatedLayout, Navbar, Sidebar)
Day 7: LoginPage.jsx + RegisterPage.jsx, test complete auth flow

COMPLETION CRITERIA:
☐ Register new student → 201 response ✓
☐ Login → access_token in AuthContext, user object populated ✓
☐ Page refresh → session restored silently via cookie refresh ✓
☐ Wrong role route → redirected to own dashboard ✓
☐ Unauthenticated → /auth/login redirect ✓
☐ Logout → AuthContext cleared, cookie deleted ✓
☐ All 11 primitives: render correctly, hover states work ✓
☐ Sidebar: correct items for each role ✓
☐ JWT NEVER appears in localStorage (verify via DevTools > Application) ✓

RISKS THIS SPRINT:
├── Axios interceptor: refresh token retry logic is complex
│   Mitigation: build incrementally, test with real expired tokens
├── Session restoration: must handle race condition with PrivateRoute
│   Mitigation: isLoading state properly prevents premature redirect
└── MetaMask detection: BlockchainContext must not block for non-university roles
```

## Sprint 8: University Portal

```
SPRINT 8: UNIVERSITY PORTAL
══════════════════════════════

SPRINT GOAL:
Complete university admin portal: dashboard, certificate issuance
(full 3-step wizard with MetaMask), list, detail, and revocation.

WEEK: 8
DURATION: 5-7 working days

DELIVERABLES:
├── D1: components/shared/composite/* (all 11 composite components)
├── D2: components/shared/feature/WalletConnector.jsx
├── D3: components/shared/feature/TransactionStatus.jsx
├── D4: components/university/IssuanceStepper.jsx
├── D5: components/university/IssuanceStep1.jsx (form + file upload)
├── D6: components/university/IssuanceStep2.jsx (MetaMask signing)
├── D7: components/university/IssuanceStep3.jsx (confirmation + QR)
├── D8: pages/university/UniversityDashboard.jsx
├── D9: pages/university/IssueCertificatePage.jsx
├── D10: pages/university/CertificateListPage.jsx
├── D11: pages/university/CertificateDetailPage.jsx
├── D12: pages/university/RevokeCertificatePage.jsx
└── D13: End-to-end issuance test passes via browser

DEPENDENCIES:
├── Sprint 7 (auth + primitives + layout working)
├── Backend running with contract deployed
├── MetaMask installed with authorized test wallet

DAILY BREAKDOWN:
Day 1: All composite components (HashDisplay, BlockchainProof, StatusBadge, FileUploadZone)
Day 2: WalletConnector.jsx, TransactionStatus.jsx
Day 3: IssuanceStepper + Step1 (file upload form)
Day 4: IssuanceStep2 (MetaMask signing flow)
Day 5: IssuanceStep3 (confirmation + QR display), UniversityDashboard
Day 6: CertificateListPage + CertificateDetailPage
Day 7: RevokeCertificatePage, end-to-end test

COMPLETION CRITERIA:
☐ Connect MetaMask → wallet address shown in Navbar ✓
☐ Upload PDF → sha256_hash displayed in Step 1 ✓
☐ Click Sign → MetaMask popup appears ✓
☐ Approve in MetaMask → TX hash shown, confirming state ✓
☐ TX confirmed → Step 3: certificate UID, QR code shown ✓
☐ Certificate list shows new certificate with CONFIRMED badge ✓
☐ Certificate detail shows blockchain proof with TX hash ✓
☐ Revoke → confirm → MetaMask → confirmed → REVOKED badge ✓

RISKS THIS SPRINT:
├── ethers.js bytes32 conversion: must exactly match what contract expects
│   Mitigation: test by comparing to Hardhat console output
├── MetaMask timing: TX may take several seconds
│   Mitigation: TransactionStatus component shows all states including pending
└── Step wizard state: losing step state on browser back button
    Mitigation: store step state in React state, not URL
```

## Sprint 9: Student + Employer Portals

```
SPRINT 9: STUDENT + EMPLOYER PORTALS
═══════════════════════════════════════

SPRINT GOAL:
Complete student portal (view, download, share) and employer portal
(file upload verification, QR scan, result display, history).

WEEK: 9
DURATION: 5-7 working days

DELIVERABLES:
├── D1: components/student/CredentialCard.jsx
├── D2: components/student/CertificateDisplay.jsx (styled cert card)
├── D3: components/student/ShareCredentialPanel.jsx
├── D4: pages/student/StudentDashboard.jsx
├── D5: pages/student/MyCredentialsPage.jsx
├── D6: pages/student/CredentialDetailPage.jsx
├── D7: pages/student/ShareCredentialPage.jsx
├── D8: components/employer/VerificationUpload.jsx
├── D9: components/employer/QRScanner.jsx (html5-qrcode)
├── D10: pages/employer/EmployerDashboard.jsx
├── D11: pages/employer/VerifyCertificatePage.jsx
├── D12: pages/employer/VerificationResultPage.jsx (all 4 states)
├── D13: pages/employer/QRScanPage.jsx
├── D14: pages/employer/VerificationHistoryPage.jsx
└── D15: pages/public/PublicVerificationPage.jsx

DEPENDENCIES:
├── Sprint 8 (university portal working — need issued certificates for testing)

DAILY BREAKDOWN:
Day 1: Student components (CredentialCard, CertificateDisplay, SharePanel)
Day 2: Student pages (Dashboard, MyCredentials, CredentialDetail)
Day 3: ShareCredentialPage, test complete student flow
Day 4: VerificationUpload component (file upload + processing steps)
Day 5: VerificationResultPage (all 4 result states)
Day 6: QRScanPage (camera scanner + manual fallback), EmployerDashboard
Day 7: VerificationHistoryPage, PublicVerificationPage

COMPLETION CRITERIA:
☐ Student: sees certificate in dashboard ✓
☐ Student: credential detail shows styled certificate card ✓
☐ Student: downloads PDF (real file) ✓
☐ Student: share page shows QR + copy URL ✓
☐ Employer: upload original PDF → AUTHENTIC (green banner) ✓
☐ Employer: upload modified PDF → TAMPERED (red banner + forensics) ✓
☐ Employer: upload unknown PDF → NOT_FOUND (gray banner) ✓
☐ Employer: upload revoked cert PDF → REVOKED (orange banner) ✓
☐ Employer: QR scanner opens camera ✓
☐ QR scan → result displayed correctly ✓
☐ Public page: /verify/{token} shows result without login ✓
☐ Public page: works on mobile Chrome ✓
```

## Sprint 10: Integration + End-to-End

```
SPRINT 10: INTEGRATION + END-TO-END TESTING
═════════════════════════════════════════════

SPRINT GOAL:
All 5 end-to-end user journey tests passing.
All integration points verified.
Loading states, error states, empty states complete.

WEEK: 10
DURATION: 5-7 working days

DELIVERABLES:
├── D1: All 5 E2E journeys tested and documented
├── D2: Loading skeletons on all data-fetching pages
├── D3: Error states with retry buttons on all pages
├── D4: Empty states on all list/dashboard pages
├── D5: NotFoundPage implementation
├── D6: Cross-browser testing (Chrome, Firefox, Safari)
├── D7: Mobile responsive verification (375px, 768px, 1280px)
└── D8: Performance benchmarks documented

DAILY BREAKDOWN:
Day 1: E2E test 1 (issuance journey) → document result
Day 2: E2E test 2 (AUTHENTIC verification) + E2E test 3 (TAMPERED)
Day 3: E2E test 4 (QR verification) + E2E test 5 (revocation)
Day 4: Loading skeletons for all pages
Day 5: Error states, empty states, NotFoundPage
Day 6: Cross-browser testing, mobile responsive testing
Day 7: Performance benchmarks, fix issues, documentation update

COMPLETION CRITERIA:
☐ E2E Test 1: Issuance → CONFIRMED → QR generated (pass)
☐ E2E Test 2: Employer uploads original → AUTHENTIC (pass)
☐ E2E Test 3: Employer uploads modified → TAMPERED (pass)
☐ E2E Test 4: QR scan → public verification (pass)
☐ E2E Test 5: Revocation → REVOKED verification (pass)
☐ All pages have loading skeleton
☐ All pages have error state with retry
☐ All list pages have empty state
☐ Mobile: QR scan works on iOS Safari and Android Chrome
☐ No console errors on any page in normal operation
```

## Sprint 11: Testing Phase

```
SPRINT 11: COMPREHENSIVE TESTING
══════════════════════════════════

SPRINT GOAL:
All automated test suites passing. Security tests passing.
Accessibility verified. No critical bugs.

WEEK: 11
DURATION: 5-7 working days

DELIVERABLES:
├── D1: Backend unit tests complete (pytest tests/unit/)
├── D2: Backend integration tests complete (pytest tests/integration/)
├── D3: Backend API tests complete (pytest tests/api/)
├── D4: Backend security tests complete (pytest tests/security/)
├── D5: Frontend unit tests (Vitest: hooks + components)
├── D6: Frontend integration tests (RTL + MSW)
├── D7: Accessibility audit (axe DevTools on all pages)
├── D8: Performance test results documented
└── D9: Bug fix sprint (fix all test failures)

DAILY BREAKDOWN:
Day 1: Backend unit tests (hash_service, blockchain_service, auth_service)
Day 2: Backend integration tests (full workflow: issue → verify → revoke)
Day 3: Backend API tests (all 37 endpoints) + security tests
Day 4: Frontend unit tests (all hooks + key components)
Day 5: Frontend integration tests (auth flow, verification display)
Day 6: Accessibility audit, performance benchmarks
Day 7: Fix all identified bugs, re-run test suite

COMPLETION CRITERIA:
☐ pytest: all tests PASSING (0 failures)
☐ Backend coverage: >85% lines
☐ Vitest: all frontend tests PASSING
☐ Frontend component coverage: >80%
☐ Security tests: all PASSING (TAMPERED detected, RBAC blocks, etc.)
☐ axe DevTools: 0 critical accessibility violations on key pages
☐ No HIGH severity bugs remaining
```

## Sprint 12: Security Hardening + Deployment Prep

```
SPRINT 12: SECURITY HARDENING + DEPLOYMENT PREPARATION
═══════════════════════════════════════════════════════

SPRINT GOAL:
All security controls verified and hardened. Application ready
for deployment to staging (Sepolia testnet).

WEEK: 12
DURATION: 5-7 working days

DELIVERABLES:
├── D1: bandit scan: 0 critical, 0 high issues
├── D2: npm audit: 0 high-severity vulnerabilities
├── D3: pip audit: 0 high-severity vulnerabilities
├── D4: Rate limiting tested and verified on all endpoints
├── D5: All error responses sanitized (no stack traces in production mode)
├── D6: Production .env template complete
├── D7: Production build: npm run build (0 errors, no source maps)
├── D8: Contract deployed to Sepolia testnet
├── D9: Contract verified on Etherscan
├── D10: Sepolia end-to-end test complete
├── D11: Nginx configuration documented
├── D12: Deployment checklist verified
└── D13: Final security validation checklist signed off

DAILY BREAKDOWN:
Day 1: bandit + pip audit + npm audit → fix all findings
Day 2: Production .env configuration, all security headers verified
Day 3: Production frontend build (source maps disabled, console logs removed)
Day 4: Sepolia testnet contract deployment + Etherscan verification
Day 5: Backend config updated for Sepolia, full E2E test on Sepolia
Day 6: Nginx config documentation, deployment checklist verification
Day 7: Final review, README update with deployment guide

COMPLETION CRITERIA:
☐ bandit -r backend/: 0 critical, 0 high
☐ npm audit --audit-level=high: 0 vulnerabilities
☐ pip audit --audit-level=high: 0 vulnerabilities
☐ SHOW_DOCS=False: /docs returns 404
☐ DEBUG=False: error response has no stack trace
☐ Source maps: absent from npm run build output
☐ Console.logs: absent from production build
☐ Sepolia: contract deployed and verified on Etherscan
☐ Sepolia: full issuance + verification flow works
☐ All security validation checklist items: CHECKED
```

---

# SECTION 12: ESTIMATED DEVELOPMENT SEQUENCE

## 12.1 Week-by-Week Timeline

```
DEVELOPMENT TIMELINE — SINGLE DEVELOPER
═══════════════════════════════════════════

WEEK 1 (Sprint 1): Project Setup + Smart Contract Development
──────────────────────────────────────────────────────────────
Mon: Repository setup, directory structure, .gitignore, .env.example files
Tue: Backend virtualenv, pip installs, requirements.txt
Wed: Frontend Vite init, npm installs, TailwindCSS, Vite alias
Thu: Blockchain Hardhat setup, PostgreSQL database + user creation
Fri: RS256 key generation, CertificateRegistry.sol (data structures + errors + events)
Sat: CertificateRegistry.sol (modifiers + functions), compile verification
Sun: ABI extraction, distribute to backend + frontend, commit to Git

Milestone: Contract compiles, ABI distributed, all dev environments working


WEEK 2 (Sprint 2): Smart Contract Testing + Database
─────────────────────────────────────────────────────
Mon: Access control tests (TC-AC-01 to TC-AC-20)
Tue: Storage + verification tests (TC-ST-01 to TC-VR-15)
Wed: Revocation + integration + security tests (all 87 total)
Thu: Fix failing tests, achieve >95% coverage, gas report review
Fri: Contract deployment to Hardhat, deployment scripts, authorize test wallet
Sat: ORM models (all 10), Alembic setup
Sun: All 13 migrations written and executed, triggers verified

Milestone: 87/87 tests pass, database schema complete


WEEK 3 (Sprint 3): Backend Core
──────────────────────────────────
Mon: core/config.py, core/exceptions.py, core/security.py (JWT + bcrypt)
Tue: core/logging_config.py, database/connection.py, main.py skeleton
Wed: dependencies/ (get_db, get_current_user, require_role, rate limiter)
Thu: All 9 repository files
Fri: All Pydantic schema files
Sat: services/auth_service.py (all 5 methods)
Sun: routers/auth_router.py, test all auth endpoints

Milestone: All auth endpoints tested and passing


WEEK 4 (Sprint 4): Backend Infrastructure Services
────────────────────────────────────────────────────
Mon: utils/hash_service.py + tests (determinism, format, timing)
Tue: utils/file_storage_service.py (save, retrieve, path validation)
Wed: utils/qr_generator_service.py, blockchain/web3_client.py
Thu: blockchain/blockchain_service.py (all 5 methods)
Fri: Test blockchain service against Hardhat (all scenarios)
Sat: services/university_service.py + router
Sun: services/student_service.py, services/employer_service.py

Milestone: Blockchain read operations working, university + student services complete


WEEK 5 (Sprint 5): Backend Certificate Issuance
──────────────────────────────────────────────────
Mon: certificate_issuance_service.py Phase 1 (upload + hash + PENDING)
Tue: POST /certificates/upload endpoint, test via Postman
Wed: certificate_issuance_service.py Phase 2 (confirmation + cross-validation)
Thu: POST /certificates/confirm-hash, manual MetaMask test
Fri: GET /certificates/ and GET /certificates/{id}, QR service
Sat: student_credential_service.py + student_router.py
Sun: Integration tests: complete issuance flow

Milestone: Complete issuance flow working (upload → MetaMask → CONFIRMED → QR)


WEEK 6 (Sprint 6): Backend Verification + Revocation
───────────────────────────────────────────────────────
Mon: verification_service.py (verify_by_file_upload)
Tue: verification_service.py (verify_by_qr_token), verification_router.py
Wed: Test all 4 verification scenarios (AUTHENTIC, TAMPERED, REVOKED, NOT_FOUND)
Thu: certificate_revocation_service.py, revocation endpoints
Fri: Test revocation flow, employer_router.py, log_router.py
Sat: Security tests (auth bypass, RBAC, file upload)
Sun: bandit scan, rate limiting verification, final backend review

Milestone: All 37 endpoints working, all verification scenarios correct


WEEK 7 (Sprint 7): Frontend Foundation + Auth
──────────────────────────────────────────────
Mon: TailwindCSS config, Vite alias, api/client.js + interceptors
Tue: All 8 API modules, NotificationContext + toast component
Wed: AuthContext (login, logout, token refresh, session restoration)
Thu: BlockchainContext, all 8 custom hooks, AppRoutes.jsx
Fri: PrivateRoute.jsx, all 11 primitive components
Sat: Layout components (PublicLayout, AuthenticatedLayout, Navbar, Sidebar)
Sun: LoginPage + RegisterPage, test complete auth flow in browser

Milestone: Auth flow works in browser, routing correct, JWT never in localStorage


WEEK 8 (Sprint 8): University Portal
──────────────────────────────────────
Mon: All 11 composite components (HashDisplay, BlockchainProof, FileUploadZone, etc.)
Tue: WalletConnector.jsx, TransactionStatus.jsx
Wed: IssuanceStepper + IssuanceStep1 (form + file upload)
Thu: IssuanceStep2 (MetaMask signing flow)
Fri: IssuanceStep3 (confirmation + QR), UniversityDashboard
Sat: CertificateListPage + CertificateDetailPage
Sun: RevokeCertificatePage, end-to-end issuance test

Milestone: Complete issuance and revocation in browser with MetaMask


WEEK 9 (Sprint 9): Student + Employer Portals
────────────────────────────────────────────────
Mon: Student components (CredentialCard, CertificateDisplay, SharePanel)
Tue: Student pages (Dashboard, MyCredentials, CredentialDetail)
Wed: ShareCredentialPage, test student flow
Thu: VerificationUpload component, VerificationResultPage (all 4 states)
Fri: QRScanPage (camera scanner), EmployerDashboard
Sat: VerificationHistoryPage, PublicVerificationPage
Sun: Test all portals, QR scanner on mobile Chrome

Milestone: All 3 portals working, QR scan works on mobile


WEEK 10 (Sprint 10): Integration + E2E
────────────────────────────────────────
Mon: E2E test 1 (issuance journey)
Tue: E2E test 2 (AUTHENTIC) + E2E test 3 (TAMPERED)
Wed: E2E test 4 (QR verification) + E2E test 5 (revocation)
Thu: Loading skeletons on all pages
Fri: Error states, empty states, NotFoundPage
Sat: Cross-browser testing, mobile responsive testing
Sun: Performance benchmarks, fix issues

Milestone: All 5 E2E journeys passing


WEEK 11 (Sprint 11): Testing Phase
────────────────────────────────────
Mon: Backend unit tests (pytest tests/unit/)
Tue: Backend integration tests (pytest tests/integration/)
Wed: Backend API + security tests
Thu: Frontend unit tests (Vitest)
Fri: Frontend integration tests + accessibility audit
Sat: Fix all test failures and accessibility issues
Sun: Re-run all test suites, document results

Milestone: All test suites passing, 0 accessibility violations


WEEK 12 (Sprint 12): Security + Deployment
───────────────────────────────────────────
Mon: bandit + pip audit + npm audit, fix all findings
Tue: Production .env, security header verification
Wed: Production frontend build (no source maps, no console logs)
Thu: Sepolia testnet deployment + Etherscan verification
Fri: Backend config for Sepolia, Sepolia E2E test
Sat: Nginx config documentation, deployment checklist
Sun: Final review, README update

Milestone: MVP deployed to Sepolia testnet, all security controls verified


OPTIONAL WEEKS 13-14 (buffer for complexity):
─────────────────────────────────────────────
Week 13: Bug fixes from user testing
Week 14: Performance optimization, final polish
```

## 12.2 Milestone Summary

```
MILESTONE SUMMARY
══════════════════

Milestone M1 (End Week 1): Development Environment Ready
├── Contract compiles
├── All dev environments configured
└── ABI distributed

Milestone M2 (End Week 2): Foundation Proven
├── 87/87 contract tests pass
└── Database schema complete

Milestone M3 (End Week 3): Backend Auth Working
└── All auth endpoints tested

Milestone M4 (End Week 4): Backend Services Working
└── Hashing, file storage, blockchain reads working

Milestone M5 (End Week 6): Complete Backend
├── All 37 endpoints working
└── All 4 verification scenarios correct

Milestone M6 (End Week 7): Frontend Foundation
└── Auth flow working in browser

Milestone M7 (End Week 8): University Portal
└── Issuance + revocation in browser

Milestone M8 (End Week 9): All Portals
└── Student + employer portals working

Milestone M9 (End Week 10): Integration Complete
└── All 5 E2E journeys passing

Milestone M10 (End Week 11): All Tests Pass
└── Automated test suites complete

Milestone M11 (End Week 12): MVP COMPLETE
├── Security hardened
└── Deployed to Sepolia testnet
```

---

# SECTION 13: RISK MANAGEMENT PLAN

## 13.1 Risk Register

```
RISK REGISTER — COMPLETE
══════════════════════════

TECHNICAL RISKS
────────────────

RISK TR-01: python-magic libmagic System Dependency
Likelihood: HIGH (common on macOS/Windows)
Impact: MEDIUM (blocks file upload security)
Description: python-magic requires libmagic C library which is not
             pre-installed on all operating systems.
Mitigation:
├── Document installation: brew install libmagic (macOS)
│                          apt install libmagic1 (Ubuntu)
│                          Windows: download libmagic DLL
└── Alternative: python-magic-bin (includes libmagic) as fallback
Detection: pip install python-magic && python -c "import magic" → test immediately in setup
Resolution: If python-magic-bin doesn't work on Windows: use WSL

RISK TR-02: MetaMask in Development Environment
Likelihood: MEDIUM
Impact: HIGH (blocks complete issuance testing)
Description: MetaMask requires HTTPS in some configurations.
             localhost:5173 should work but some features may be restricted.
Mitigation:
├── Use localhost (not 127.0.0.1) — MetaMask supports http://localhost
├── Add test private key from Hardhat to MetaMask manually
└── Document: which Hardhat account to import
Detection: Connect MetaMask to localhost:5173 in Chrome → test in Week 5
Resolution: If HTTPS required: use Vite HTTPS plugin (mkcert)

RISK TR-03: Web3.py Bytes32 Conversion Mismatch
Likelihood: MEDIUM
Impact: CRITICAL (prevents blockchain hash verification)
Description: Python SHA-256 hex string must convert to exactly the
             bytes32 format the Solidity contract expects.
             Any padding, endianness, or encoding mismatch breaks verification.
Mitigation:
├── Write conversion test first (Week 4): Python hex → bytes32 → Hardhat compare
├── Reference: Web3.to_bytes(hexstr="0x" + sha256_hex_string)
└── Cross-validate: store hash via Python, read via Hardhat → must match exactly
Detection: blockchain_service test in Week 4
Resolution: Adjust conversion function until Hardhat confirm matches

RISK TR-04: Async SQLAlchemy Complexity
Likelihood: MEDIUM
Impact: MEDIUM (integration bugs, session management)
Description: Async SQLAlchemy with asyncpg has known quirks around
             session lifecycle, lazy loading, and transaction management.
Mitigation:
├── Always use expire_on_commit=False in session config
├── Always use selectinload() for relationships (no lazy loading in async)
└── Transaction context managed at service layer (not repository)
Detection: First database tests in Week 3
Resolution: Use synchronous SQLAlchemy fallback if async issues persist (MVP viable)

RISK TR-05: TailwindCSS PurgeCSS Removing Dynamic Classes
Likelihood: MEDIUM (common with status-based colors)
Impact: LOW-MEDIUM (styling breaks in production)
Description: If status badge colors are computed dynamically:
             bg-${color}-500 → PurgeCSS removes these as unused classes.
Mitigation:
├── Use safelist in tailwind.config.js for all status colors
├── OR use full class names in component code (not dynamic string construction)
└── Test: npm run build, open dist/ in browser, verify colors render
Detection: Production build test in Week 12
Resolution: Add all status colors to TailwindCSS safelist

RISK TR-06: QR Scanner Camera Permissions on Desktop
Likelihood: LOW
Impact: MEDIUM (QR scan feature partially breaks)
Description: html5-qrcode may have issues on desktop browsers
             requesting camera access.
Mitigation:
├── Primary QR use case is mobile — ensure mobile works first
├── Implement manual URL entry fallback (already in architecture)
└── Test on multiple devices: Android Chrome, iOS Safari, desktop Chrome
Detection: QR scanner testing in Week 9
Resolution: Document browser support; promote manual entry as primary for desktop


INTEGRATION RISKS
─────────────────

RISK IR-01: CORS Configuration Complexity
Likelihood: HIGH (almost always an issue)
Impact: MEDIUM (frontend cannot call backend)
Description: CORS between Vite localhost:5173 and FastAPI localhost:8000.
             The refresh token cookie requires specific CORS + credential settings.
Mitigation:
├── Configure CORS in backend: allow_origins=["http://localhost:5173"]
├── Set: allow_credentials=True
├── Axios: withCredentials: true on ALL requests (including refresh)
└── Test: login → set cookie → subsequent request sends cookie
Detection: First frontend → backend test in Week 7
Resolution: Step through CORS configuration systematically

RISK IR-02: MetaMask Network Configuration Mismatch
Likelihood: MEDIUM
Impact: HIGH (all blockchain operations fail)
Description: MetaMask must be connected to the same network as the
             Hardhat node (chainId 31337). Wrong network = all TXs fail.
Mitigation:
├── Add Hardhat network to MetaMask: localhost:8545, chainId 31337
├── Show "Wrong Network" warning in WalletConnector component
└── Frontend checks chainId on every TX attempt
Detection: First MetaMask signing test in Week 8
Resolution: WalletConnector prompts user to switch network

RISK IR-03: Axios Interceptor Infinite Loop on Auth Failure
Likelihood: MEDIUM (common implementation bug)
Impact: HIGH (app becomes unusable after session expires)
Description: If the refresh endpoint itself returns 401, the interceptor
             might try to refresh again, creating an infinite loop.
Mitigation:
├── Track: is_refreshing flag in client.js
├── Check: if request URL is /auth/refresh → do NOT retry on 401
└── On refresh failure: immediately dispatch LOGOUT
Detection: Test with expired refresh token in Week 7
Resolution: Add URL check to interceptor before attempting refresh

RISK IR-04: Frontend Contract ABI Mismatch After Contract Redeployment
Likelihood: HIGH (contract will be redeployed multiple times in development)
Impact: HIGH (all blockchain frontend calls fail silently or with wrong params)
Description: If the contract is modified and redeployed, the ABI in
             frontend/blockchain/contractABI.js becomes stale.
Mitigation:
├── deploy.js script AUTOMATICALLY copies ABI after deployment
├── Document: "always run deploy script, never manually copy ABI"
├── Add ABI version check: compare contract version on chain to expected
└── Checklist item in every deploy: "verify ABI matches deployed contract"
Detection: After any contract redeployment
Resolution: Re-run deploy.js script


BLOCKCHAIN RISKS
─────────────────

RISK BR-01: Hardhat Node State Lost on Restart
Likelihood: VERY HIGH (Hardhat in-memory by default)
Impact: MEDIUM (all deployed contracts and issued certificates lost)
Description: Hardhat's in-memory blockchain resets on every restart.
             All development test data is lost.
Mitigation:
├── Accept that Hardhat local node is in-memory
│   This resets chain state on restart
├── After restart: re-run deployment script
└── Always run seed data script after fresh deployment
Detection: Any Hardhat restart during development
Resolution: Document restart procedure; make seed data script idempotent

RISK BR-02: Sepolia Testnet ETH Faucet Rate Limiting
Likelihood: HIGH
Impact: LOW-MEDIUM (deployment delayed)
Description: Sepolia faucets have rate limits and sometimes run dry.
             Need enough Sepolia ETH for deployment + testing.
Mitigation:
├── Request from multiple faucets early (before deployment sprint)
├── Faucets: sepoliafaucet.com, Alchemy Sepolia Faucet, Chainlink Faucet
├── Estimate needed: 0.5 ETH covers extensive testing
└── Request in Week 1 (takes time to accumulate)
Detection: During Sepolia deployment (Week 12)
Resolution: Request from additional faucets; use Alchemy faucet (more reliable)

RISK BR-03: Infura/Alchemy Free Tier Rate Limiting
Likelihood: MEDIUM
Impact: MEDIUM (blockchain reads slow or fail under testing load)
Description: Free tier RPC endpoints have request rate limits.
             Under testing load (rapid verifications), hits may be throttled.
Mitigation:
├── Use Hardhat local node for all development (no rate limits)
├── Sepolia testing: pace tests to avoid rate limits
└── Consider: two free tier accounts if needed
Detection: Sepolia testing in Week 12
Resolution: Add retry logic with exponential backoff in blockchain_service.py


TESTING RISKS
─────────────

RISK TS-01: Test Database Pollution Between Tests
Likelihood: HIGH (common issue without careful setup)
Impact: MEDIUM (flaky tests that sometimes pass, sometimes fail)
Description: If tests share database state, test execution order matters.
             A test that creates a certificate may affect another test's count.
Mitigation:
├── Use transactions in tests: wrap each test in a transaction, roll back after
├── OR: use a separate test database (credential_db_test)
└── Never run integration tests against development database
Detection: First time two integration tests run and interfere
Resolution: Implement transaction-per-test pattern via pytest fixture

RISK TS-02: MetaMask Cannot Be Automated in E2E Tests
Likelihood: CERTAIN (MetaMask requires user interaction by design)
Impact: MEDIUM (issuance workflow cannot be fully automated)
Description: MetaMask intentionally blocks automation to prevent
             malicious sites from auto-signing transactions.
Mitigation:
├── E2E tests that require MetaMask: manual execution only
├── Blockchain interaction can be tested via Hardhat signers (no MetaMask)
├── Backend integration tests use Hardhat wallet directly (bypass MetaMask)
└── Document: which tests require manual execution
Detection: First attempt to automate MetaMask in Week 11
Resolution: Accept manual E2E for blockchain steps; automate everything else

RISK TS-03: SHA-256 Test Vectors Not Matching
Likelihood: LOW
Impact: CRITICAL (if hash computation is wrong, verification never works)
Description: If the Python SHA-256 output doesn't match a known test
             vector, the entire verification system is broken.
Mitigation:
├── Use NIST SHA-256 test vectors as the first hash_service test
├── Known vector: SHA-256("abc") = "ba7816bf8f01cfea414140de5dae2ec73b00361bbef0469f8849c6c2f7ff62"
└── This test runs before any other hash service usage
Detection: hash_service test in Week 4 (must pass before proceeding)
Resolution: If Python hashlib produces wrong output → impossible (it's stdlib)
           The issue would be in encoding/decoding, not the hash itself
```

---

# SECTION 14: IMPLEMENTATION VALIDATION CHECKLIST

```
╔══════════════════════════════════════════════════════════════════════════════╗
║               IMPLEMENTATION VALIDATION CHECKLIST                            ║
║       Verify every item before declaring MVP implementation complete         ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════
PROJECT SETUP
═══════════════════════════════════════════════════════════════════
☐ Git repository initialized with main + develop branches
☐ .gitignore excludes: .env, *.pem, node_modules, __pycache__, uploads/
☐ All .env.example files committed (no actual secrets)
☐ All three components start successfully (Hardhat, FastAPI, Vite)
☐ PostgreSQL connection verified from backend
☐ RS256 key pair generated and tested

═══════════════════════════════════════════════════════════════════
SMART CONTRACT
═══════════════════════════════════════════════════════════════════
☐ CertificateRegistry.sol compiles with 0 errors and 0 warnings
☐ 87/87 Hardhat tests PASSING
☐ Test coverage: line ≥95%, branch ≥95%, function 100%
☐ Gas: storeCertificate ≤110,000, revoke ≤65,000, authorize ≤55,000
☐ Deployed to local Hardhat (chainId 31337)
☐ ABI at backend/blockchain/abi/CertificateRegistry.json
☐ ABI at frontend/blockchain/contractABI.js
☐ CONTRACT_ADDRESS in backend/.env and frontend/.env.development
☐ isAuthorizedIssuer(test_wallet) returns True

═══════════════════════════════════════════════════════════════════
DATABASE
═══════════════════════════════════════════════════════════════════
☐ alembic upgrade head: exits 0
☐ 10 tables present (\dt in psql)
☐ 6 ENUM types present (\dT in psql)
☐ 49 indexes present (\di in psql)
☐ Immutability trigger: UPDATE on confirmed cert raises exception
☐ Append-only trigger: UPDATE on verification_log raises exception
☐ Audit trigger: INSERT on users creates audit_log entry
☐ Seed data created (SUPER_ADMIN + test university + test admin)

═══════════════════════════════════════════════════════════════════
BACKEND
═══════════════════════════════════════════════════════════════════
☐ uvicorn main:app: starts with 0 errors
☐ GET /health → 200 {"status": "ok"}
☐ All 37 endpoints in /openapi.json
☐ POST /auth/register → 201 (new user created)
☐ POST /auth/login → 200 + access_token + httpOnly refresh cookie
☐ POST /auth/login (wrong password ×5) → account locked (423)
☐ POST /auth/refresh → 200 + new access_token + new cookie
☐ POST /auth/logout → 204 + cookie cleared
☐ POST /certificates/upload → sha256_hash computed correctly
☐ POST /certificates/upload (non-PDF) → 400
☐ POST /certificates/confirm-hash → CONFIRMED status
☐ POST /verify/upload (original PDF) → AUTHENTIC
☐ POST /verify/upload (modified PDF) → TAMPERED
☐ POST /verify/upload (unknown PDF) → NOT_FOUND
☐ GET /verify/qr/{valid_token} → AUTHENTIC
☐ POST /certificates/{id}/revoke + confirm → REVOKED
☐ POST /verify/upload (revoked cert) → REVOKED
☐ bandit -r backend/: 0 critical, 0 high issues

═══════════════════════════════════════════════════════════════════
FRONTEND
═══════════════════════════════════════════════════════════════════
☐ npm run dev: starts on localhost:5173
☐ npm run build: exits 0, no source maps in dist/
☐ Auth flow: register → login → dashboard redirect
☐ Session restoration: page refresh → session restored silently
☐ JWT: confirmed NOT in localStorage (DevTools > Application)
☐ Wrong role navigation → correct redirect
☐ University: issuance wizard completes with MetaMask
☐ University: certificate visible as CONFIRMED after issuance
☐ University: revocation works with MetaMask
☐ Student: sees own certificates, downloads PDF
☐ Student: share page shows QR + copy URL
☐ Employer: file upload → AUTHENTIC result (green banner)
☐ Employer: file upload → TAMPERED result (red banner + forensics)
☐ Employer: QR scanner opens camera
☐ Public: /verify/{token} works without login
☐ Public: works on mobile Chrome

═══════════════════════════════════════════════════════════════════
SECURITY
═══════════════════════════════════════════════════════════════════
☐ Rate limit: 6th login → 429
☐ Rate limit: 11th verify/upload → 429
☐ RBAC: student cannot access POST /certificates/upload → 403
☐ RBAC: employer cannot access /student/credentials → 403
☐ Ownership: student A cannot access student B's credential → 403
☐ JWT algorithm confusion: HS256 token → 401
☐ JWT algorithm "none": → 401
☐ File upload: .exe renamed .pdf → 400
☐ Error responses: no stack traces in production mode
☐ Swagger: /docs → 404 (production mode)
☐ localStorage: no JWT or tokens stored

═══════════════════════════════════════════════════════════════════
END-TO-END JOURNEYS
═══════════════════════════════════════════════════════════════════
☐ E2E Test 1: Issuance journey → CONFIRMED + QR generated
☐ E2E Test 2: AUTHENTIC verification via file upload
☐ E2E Test 3: TAMPERED certificate detected correctly
☐ E2E Test 4: QR code scanned → verification result shown
☐ E2E Test 5: Revocation → subsequent verification shows REVOKED

═══════════════════════════════════════════════════════════════════
DEPLOYMENT READINESS
═══════════════════════════════════════════════════════════════════
☐ Contract deployed to Sepolia testnet
☐ Contract verified on Etherscan
☐ All E2E tests pass on Sepolia (with real Sepolia ETH)
☐ Production .env files prepared (not committed)
☐ npm run build: production bundle created
☐ Nginx security headers documented
☐ Deployment checklist from security architecture verified

═══════════════════════════════════════════════════════════════════
FINAL MVP VERDICT: ALL ITEMS CHECKED → IMPLEMENTATION COMPLETE
═══════════════════════════════════════════════════════════════════
```

---

# SECTION 15: FINAL READINESS ASSESSMENT

## 15.1 Pre-Implementation Readiness Verification

```
FINAL READINESS ASSESSMENT
════════════════════════════

QUESTION 1: Can the developer start immediately?
Answer: YES
Requirements:
☐ Node.js 18+ installed
☐ Python 3.11+ installed
☐ PostgreSQL 15+ installed
☐ Chrome + MetaMask extension installed
☐ Git installed
☐ GitHub account
☐ Code editor (VS Code recommended)
☐ Infura or Alchemy account (free tier)
All requirements can be satisfied in < 2 hours.


QUESTION 2: Is any architectural decision ambiguous?
Answer: NO
Every decision is documented in one of these approved documents:
├── Architecture blueprint: framework choices, patterns
├── Database design: every table, column, constraint, index, trigger
├── Smart contract architecture: every function, modifier, event
├── Backend architecture: every service, repository, endpoint
├── Frontend architecture: every page, component, route
└── Security architecture: every control, rate limit, validation rule

If implementation produces a question not answered by these documents:
→ Build the simplest implementation that satisfies the requirement
→ Document the decision in a decisions.md file


QUESTION 3: Are there any missing dependencies between components?
Answer: NO (verified via dependency chain analysis in Section 2)
Every component has clearly identified predecessors.
No component needs to be built before its dependencies.


QUESTION 4: Can this be built by one developer with AI assistance?
Answer: YES
Timeline: 12 weeks (with 2-week buffer available)
AI assistance value areas:
├── Code generation for boilerplate (Pydantic schemas, repository methods)
├── Debugging complex async SQLAlchemy issues
├── Solidity syntax and security pattern verification
├── CSS/TailwindCSS class combinations for UI components
├── Test case generation (given function signatures)
└── Error message interpretation and resolution


QUESTION 5: What is the most likely point of failure?
Answer: Three high-risk integration points

Risk 1 (Week 5): MetaMask signing + backend confirmation
├── Most novel integration: frontend MetaMask → backend Web3.py
├── Mitigation: test this in isolation (Hardhat console) before building UI
└── Spend extra time here; this is the core of the blockchain integration

Risk 2 (Week 7): JWT httpOnly cookie + Axios interceptor
├── Most commonly misconfigured auth pattern
├── Mitigation: verify cookie round-trip before building any portal page
└── Follow the exact configuration from security architecture

Risk 3 (Week 4): bytes32 hash conversion Python ↔ Solidity
├── Silent failure: wrong conversion produces wrong TAMPERED/AUTHENTIC results
├── Mitigation: verify with known test vector before trusting any result
└── Cross-validate: Python hash → stored on chain → read via Python → must match


QUESTION 6: What must be done before writing any code?
Answer: Six prerequisites (can be done in sequence on Day 1)

1. Read all architecture documents in full (4-6 hours)
2. Set up development environment (2-4 hours)
3. Create GitHub repository and branch structure (30 minutes)
4. Generate RS256 key pair and store securely (30 minutes)
5. Create PostgreSQL database and user (1 hour)
6. Verify: Python, Node.js, Chrome + MetaMask all working (1 hour)

Total Day 0 preparation: 8-12 hours
After Day 0: Sprint 1 can begin immediately.


IMPLEMENTATION READINESS STATUS:
══════════════════════════════════

Architecture:          ✅ COMPLETE
Database Design:       ✅ COMPLETE
Smart Contract Design: ✅ COMPLETE
Backend Design:        ✅ COMPLETE
Frontend Design:       ✅ COMPLETE
Security Design:       ✅ COMPLETE
Implementation Roadmap:✅ COMPLETE

┌──────────────────────────────────────────────────────────────────┐
│                   FINAL VERDICT                                   │
│                                                                   │
│  STATUS: IMPLEMENTATION CAN BEGIN IMMEDIATELY                     │
│                                                                   │
│  All architectural decisions are made.                           │
│  All component interfaces are defined.                           │
│  All integration points are documented.                          │
│  All risks are identified with mitigations.                      │
│  All dependencies are ordered.                                   │
│                                                                   │
│  Begin with Sprint 1, Day 1:                                     │
│  "Repository setup, directory structure, .gitignore"             │
│                                                                   │
│  IMPLEMENTATION READINESS STATUS: READY TO BUILD                │
└──────────────────────────────────────────────────────────────────┘
```

---

> **This implementation roadmap is the binding build plan for the Blockchain-Based Academic Credential Verification Platform MVP. Every sprint, every day plan, every completion criterion, and every risk mitigation is derived from the approved architecture documents. No new architectural decisions are required. Implementation begins at Sprint 1, Day 1, following the sequence defined in this document without deviation.**