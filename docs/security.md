# Blockchain-Based Academic Credential Verification Platform
## Complete Security Architecture Blueprint — MVP Edition

---

# PRE-DESIGN REVIEW & ASSUMPTION EXTRACTION

## Review 1: Cross-Document Security Requirement Extraction

```
SECURITY REQUIREMENTS EXTRACTED FROM ALL APPROVED DOCUMENTS
═════════════════════════════════════════════════════════════

FROM ARCHITECTURE BLUEPRINT:
├── RS256 asymmetric JWT (private key signs, public key verifies)
├── Access token: 15-minute TTL, stored in React memory
├── Refresh token: 7-day TTL, httpOnly Secure SameSite=Strict cookie
├── Token rotation: every refresh invalidates old token
├── bcrypt cost factor 12 for password hashing
├── Account lockout: 5 failed attempts → 10-minute lockout
├── Rate limits: login 5/min, verify/upload 10/min, QR 30/min, general 100/min
├── CORS: only FRONTEND_URL whitelisted (never wildcard with credentials)
├── SHA-256 hash computed from raw binary file bytes (not text/metadata)
├── Blockchain is always the source of truth (database never trusted alone)
├── MetaMask signs all write transactions (private keys never on server)
├── Opaque QR tokens (not certificate UUID or hash) to prevent enumeration
├── UUID v4 primary keys (prevent IDOR enumeration)
├── Soft deletes on certificates (immutable audit trail)
└── No stack traces in API error responses

FROM DATABASE DESIGN:
├── UUID v4 primary keys on all tables
├── bcrypt password hash stored (never plaintext)
├── Refresh token stored as SHA-256 hash (never raw token)
├── Reset token stored as SHA-256 hash
├── DB-level immutability triggers on confirmed certificate fields
├── Append-only triggers on verification_logs and audit_log
├── Row-level ownership enforced via service layer
├── wallet_address format validated: CHECK constraint (^0x[0-9a-fA-F]{40}$)
├── sha256_hash format validated: CHECK constraint (^[0-9a-f]{64}$)
├── Minimal DB user privileges (credential_app_user)
└── Sensitive columns excluded from views (users_safe view)

FROM SMART CONTRACT ARCHITECTURE:
├── authorizedIssuers whitelist: only approved wallets can write
├── Owner ≠ issuer: contract owner cannot forge certificates
├── One-time write per certificate UID (no hash overwrite)
├── One-way revocation (ACTIVE → REVOKED, terminal)
├── onlyOriginalIssuer modifier for revocation
├── bytes32(0) hash rejected
├── Empty/oversized UID rejected (max 50 chars)
├── No external calls from contract (reentrancy impossible)
├── No tx.origin usage (phishing protection)
├── Solidity 0.8.19 (built-in overflow protection)
└── Custom errors (not require strings — less information leakage)

FROM BACKEND ARCHITECTURE:
├── python-magic for MIME type validation (not just extension)
├── Files stored outside web root, served via API
├── UUID filenames (no original filename on filesystem)
├── Path traversal prevention (realpath check against UPLOAD_ROOT)
├── Pydantic validates all inputs before business logic
├── Ownership checks in service layer (not just role checks)
├── Hierarchical custom exceptions (domain exceptions, not HTTP exceptions)
├── No stack traces to clients in production
├── Structured JSON logging (structlog)
├── All verification events logged (even failures)
└── Blockchain always queried for verification (never DB-only)

FROM FRONTEND ARCHITECTURE:
├── JWT in React memory (not localStorage or sessionStorage)
├── No dangerouslySetInnerHTML with user content
├── External links: rel="noopener noreferrer"
├── File validation: client-side MIME + size checks (defense in depth)
├── No console.log in production builds
├── Source maps disabled in production
├── CORS whitelist: only configured FRONTEND_URL
└── MetaMask: no private key access via web API
```

## Review 2: Threat Surface Inventory

```
THREAT SURFACE INVENTORY
══════════════════════════

SURFACE 1: Authentication Layer
Attack surface: Login endpoint, registration, token refresh
Threat actors: External attackers, credential stuffers, token thieves

SURFACE 2: API Endpoints (37 endpoints across 8 routers)
Attack surface: All /api/v1/* endpoints
Threat actors: Unauthorized users, privilege escalators, API abusers

SURFACE 3: File Upload System
Attack surface: POST /certificates/upload, POST /verify/upload
Threat actors: Malicious file uploaders, storage exhausters

SURFACE 4: Blockchain Layer
Attack surface: Smart contract functions, MetaMask integration
Threat actors: Unauthorized issuers, transaction replayers

SURFACE 5: Database
Attack surface: PostgreSQL via SQLAlchemy ORM
Threat actors: SQL injection attackers, data exfiltrators

SURFACE 6: Frontend Application
Attack surface: React SPA, localStorage/sessionStorage, DOM
Threat actors: XSS attackers, CSRF attackers, clickjackers

SURFACE 7: QR Verification (Public Endpoint)
Attack surface: GET /verify/qr/{token} (no auth required)
Threat actors: Token scrapers, verification result spoofers

SURFACE 8: Certificate Lifecycle
Attack surface: Issuance, verification, revocation workflows
Threat actors: Fraudulent issuers, tampered document submitters

SURFACE 9: Secrets and Configuration
Attack surface: .env files, private keys, database credentials
Threat actors: Insider threats, repository scanning bots

SURFACE 10: Dependencies
Attack surface: Python packages, npm packages, Solidity libraries
Threat actors: Supply chain attackers
```

## Review 3: Carried-Forward Security Assumptions

```
SECURITY ASSUMPTIONS CARRIED FORWARD
═══════════════════════════════════════

ASSUMPTION 01: RS256 JWT (Non-Negotiable from Architecture)
The private key signs tokens; only the backend holds it.
The public key verifies; it can be shared without enabling forgery.
Impact: JWT cannot be forged even if public key is leaked.

ASSUMPTION 02: MetaMask for All Blockchain Write Operations
Private keys never touch the backend server.
Impact: Server compromise cannot result in forged certificates.
The attacker must also compromise the university's MetaMask wallet.

ASSUMPTION 03: Blockchain as Ultimate Source of Truth
Database is operational layer; blockchain is cryptographic truth.
Impact: Database compromise cannot fake an authentic verification.
Verification ALWAYS queries blockchain.

ASSUMPTION 04: MVP Single-Developer Environment
No HSM, no enterprise KMS, no WAF, no CDN.
Impact: Security controls must be software-implemented and free/low-cost.
Mitigations are layered software controls, not infrastructure controls.

ASSUMPTION 05: Local/Sepolia Blockchain (Not Mainnet)
MVP uses Hardhat local + Sepolia testnet.
Impact: No real ETH cost. Security testing can be thorough without cost.
Mainnet deployment is post-MVP; security review required before mainnet.

ASSUMPTION 06: PDF Files Stored on Local Filesystem
Not S3, not encrypted at rest (MVP scope).
Impact: File system access control must rely on OS permissions + API gating.
Post-MVP: server-side encryption at rest.

ASSUMPTION 07: No Redis/Background Workers
Rate limiting uses in-memory store (SlowAPI default).
Impact: Rate limit counters reset on server restart.
This is acceptable for MVP; Redis is post-MVP hardening.

ASSUMPTION 08: No WAF or CDN
No Cloudflare, no AWS WAF, no Nginx WAF rules.
Impact: DDoS protection is limited to server-level rate limiting.
This is acceptable for MVP with limited traffic.

ASSUMPTION 09: HTTPS Enforced by Reverse Proxy
Nginx handles TLS termination; FastAPI sees plain HTTP.
Impact: Security headers (HSTS, etc.) must be set by Nginx, not FastAPI.

ASSUMPTION 10: Sepolia Testnet for Staging
Ethereum Sepolia is public; contract and transactions are visible.
Impact: No PII on chain (already designed: hash only).
Testnet visibility is acceptable for MVP validation.
```

---

# TABLE OF CONTENTS

1. Security Design Philosophy
2. Threat Model Overview
3. Security Architecture Overview
4. Authentication Security Design
5. JWT Security Strategy
6. Password Security Strategy
7. Authorization (RBAC) Security Design
8. Session Security Design
9. API Security Strategy
10. Backend Security Strategy
11. Frontend Security Strategy
12. Database Security Strategy
13. Smart Contract Security Strategy
14. Blockchain Transaction Security
15. Certificate Issuance Security
16. Certificate Verification Security
17. Certificate Revocation Security
18. File Upload Security
19. SHA-256 Integrity Protection Strategy
20. QR Verification Security
21. Input Validation Strategy
22. Data Validation Strategy
23. Error Handling Security
24. Logging Security
25. Audit Trail Security
26. Rate Limiting Strategy
27. Abuse Prevention Strategy
28. Secure Storage Strategy
29. Secrets Management Strategy
30. Dependency Security Strategy
31. Frontend Route Protection Strategy
32. Verification Result Integrity Strategy
33. Security Testing Strategy
34. Security Monitoring Strategy
35. Security Incident Response Plan
36. Security Validation Checklist
37. Security Readiness Checklist

---

# SECTION 1: SECURITY DESIGN PHILOSOPHY

## 1.1 The Five Security Governing Principles

These principles are non-negotiable. Every security decision in this document derives from them.

**Principle 1: Defense in Depth — Never Rely on a Single Control**
Every security requirement is addressed by at least two independent controls at different layers. Password brute-force is addressed by bcrypt slowness (cryptographic layer) AND account lockout (application layer) AND rate limiting (transport layer). If one control fails, two others remain. A single control is never trusted as the entire defense.

**Principle 2: Blockchain Immutability is the Trust Anchor**
The entire platform's trust model rests on one cryptographic guarantee: what is recorded on the blockchain cannot be altered. Every security decision reinforces this anchor. The backend cannot be trusted alone for verification. The database cannot be trusted alone for authenticity. Only the blockchain provides tamper-proof proof of issuance. Security controls at every other layer protect the integrity of the path to and from this anchor.

**Principle 3: Minimal Blast Radius — Limit What Can Be Damaged**
Every component operates with the minimum privileges required. The database user cannot DROP tables. The application cannot read private keys. University admins cannot revoke other universities' certificates. Students cannot access other students' credentials. If any single component is compromised, the damage is limited to that component's minimal privilege scope.

**Principle 4: Explicit Over Implicit — Security Must Be Visible**
Security controls are declared explicitly, not assumed. Every protected endpoint explicitly declares its authentication and role requirements. Every sensitive operation explicitly validates ownership. Every audit event is explicitly logged. Implicit security (assuming something is secure because it wasn't mentioned) is the source of most vulnerabilities.

**Principle 5: Fail Closed — Default to Rejection**
When in doubt, reject. An ambiguous authentication state → unauthenticated. An ambiguous role check → unauthorized. An ambiguous blockchain response → not authentic. A verification attempt that cannot reach the blockchain → not authentic (not "probably authentic"). The system never grants access on ambiguity; it always requires positive proof.

## 1.2 The Security Trust Hierarchy

```
TRUST HIERARCHY
════════════════

TIER 0 (ABSOLUTE TRUST): Ethereum Blockchain
├── Cannot be altered by any party in the system
├── Provides: certificate issuance proof, hash integrity, revocation state
└── Trusted because: cryptographic consensus protocol

TIER 1 (HIGH TRUST): Cryptographic Controls
├── RS256 JWT signature: trusted because private key is secret
├── SHA-256 hash: trusted because collision-resistant
├── bcrypt hash: trusted because computationally irreversible
└── MetaMask transaction signature: trusted because private key is user-held

TIER 2 (MEDIUM TRUST): Application Controls
├── RBAC role checks: trusted because JWT is signed (role cannot be forged)
├── Ownership checks: trusted because backend enforces, not frontend
├── Rate limiting: trusted because enforced server-side
└── Input validation: trusted because Pydantic validates before business logic

TIER 3 (LOW TRUST, VALIDATED): User Input
├── All client data: treated as potentially malicious until validated
├── File uploads: treated as potentially malicious until MIME + size validated
├── JWT tokens: treated as potentially invalid until RS256 signature verified
└── URL parameters: treated as potentially crafted until type-validated

TIER 4 (UNTRUSTED): External Systems
├── MetaMask wallet: user-controlled; we cannot guarantee it is secure
├── Browser environment: potentially compromised by XSS
└── Public internet: hostile environment

PRINCIPLE: Security flows from Tier 0 upward, never assumed from Tier 4 downward.
```

---

**[Design Decision A]** The security architecture is designed for **MVP with single-developer constraints** — it uses software controls, not enterprise infrastructure. **[Why]** The architecture explicitly excludes Kubernetes, WAF, and enterprise GDPR layers. Security must be achievable with free tools and standard library features. Every control in this document is implementable without paid infrastructure. **[Requirement satisfied]** "Realistic for MVP implementation, single developer, free development environment." **[Alternative rejected]** Enterprise security stack (CloudHSM, WAF, SIEM, etc.): appropriate for production with budget, completely unnecessary and inaccessible for MVP. Adds cost without MVP benefit.

---

# SECTION 2: THREAT MODEL OVERVIEW

## 2.1 STRIDE Threat Model

```
STRIDE THREAT MODEL — COMPLETE
═════════════════════════════════

SPOOFING (Impersonation)
═══════════════════════════
Threat S1: Attacker impersonates a university admin
Attack vector: Stolen credentials + JWT theft
Impact: Fraudulent certificates issued on blockchain (permanent)
Likelihood: MEDIUM
Mitigation:
├── bcrypt cost 12 (slow password cracking)
├── Account lockout (5 attempts)
├── RS256 JWT (signature cannot be forged)
├── MetaMask second factor (must also control wallet)
└── Rate limiting on login endpoint (5/min)
Residual risk: LOW

Threat S2: Attacker forges JWT token
Attack vector: HS256 secret exposure, algorithm confusion attack
Impact: Full platform access as any role
Likelihood: LOW
Mitigation:
├── RS256 asymmetric signing (no shared secret to steal)
└── Algorithm pinned in JWT decode (no algorithm confusion)
Residual risk: VERY LOW

Threat S3: Rogue university self-registers and issues fraudulent certs
Attack vector: Register as university → issue certs without verification
Impact: Fraudulent credentials on blockchain
Likelihood: MEDIUM
Mitigation:
├── University registration requires SUPER_ADMIN approval (is_verified flag)
├── Smart contract authorizedIssuers whitelist
└── Dual gate: platform approval + blockchain authorization
Residual risk: LOW

TAMPERING (Data Modification)
════════════════════════════════
Threat T1: Attacker modifies certificate PDF after issuance
Attack vector: Edit PDF → submit for verification
Impact: Tampered certificate passes verification
Likelihood: HIGH (primary platform threat)
Mitigation:
├── SHA-256 of original binary stored on blockchain
├── Verification recomputes hash from submitted file
├── Any modification → different hash → TAMPERED result
└── Blockchain hash is immutable (cannot be changed to match modified doc)
Residual risk: NEGLIGIBLE (SHA-256 collision probability: 1 in 2^128)

Threat T2: Attacker modifies sha256_hash in PostgreSQL database
Attack vector: SQL injection or direct DB access
Impact: Database shows wrong hash; could mislead verification
Likelihood: LOW
Mitigation:
├── DB-level immutability trigger (confirmed cert fields cannot change)
├── Verification ALWAYS queries blockchain (not DB hash)
├── Even if DB hash is changed, blockchain hash is correct
└── DB hash change → audit_log entry → detectable
Residual risk: VERY LOW (blockchain wins)

Threat T3: Smart contract certificate UID overwrite
Attack vector: Authorized issuer tries to store new hash for existing UID
Impact: Retroactive hash change → tampered cert appears valid
Likelihood: LOW (requires authorized wallet)
Mitigation:
└── Contract requires: !certificates[certUid].exists (one-time write)
Residual risk: NONE (contract-level enforcement)

REPUDIATION (Denial of Action)
══════════════════════════════════
Threat R1: University denies issuing a certificate
Attack vector: Claim certificate was fraudulently created
Impact: Legal dispute; platform trust degraded
Mitigation:
├── Blockchain record includes issuingUniversity address
├── TX signed by university's MetaMask private key
├── Ethereum transaction is public and permanent
└── DB audit_log records admin user who initiated issuance
Residual risk: VERY LOW

Threat R2: Employer denies performing fraudulent verification
Attack vector: Employer submits tampered cert, claims error
Mitigation:
├── verification_logs: records submitted_hash, stored_hash, IP, result
└── Immutable (DB trigger prevents modification)
Residual risk: LOW

INFORMATION DISCLOSURE
═══════════════════════
Threat I1: Student A accesses Student B's certificates
Attack vector: Guessing certificate UUIDs in API endpoints
Likelihood: LOW (UUID v4 is non-guessable)
Mitigation:
├── UUID v4 PKs (not sequential integers)
├── Ownership check in service layer
└── Backend returns 403 on ownership violation
Residual risk: VERY LOW

Threat I2: Blockchain reveals student PII
Attack vector: Query blockchain to extract personal information
Mitigation:
└── NO PII stored on blockchain (hash + wallet address only)
Residual risk: NONE (by architecture design)

Threat I3: JWT payload reveals sensitive data
Attack vector: Decode JWT (base64 is not encryption)
Mitigation:
├── JWT contains: user_id, role, university_id, email only
└── No passwords, no hashes, no PII beyond email in payload
Residual risk: LOW (minimal acceptable data in JWT)

DENIAL OF SERVICE
══════════════════
Threat D1: Login endpoint flooding
Attack vector: Rapid login attempts exhaust server resources
Mitigation:
├── Rate limiting: 5/min per IP on /auth/login
└── Account lockout: reduces server work per locked account
Residual risk: MEDIUM (no CDN/WAF in MVP)

Threat D2: Verification endpoint flooding
Attack vector: Spam large PDF uploads to exhaust storage + blockchain queries
Mitigation:
├── Rate limiting: 10/min per IP on /verify/upload
├── File size limit: 50MB maximum
└── Blockchain query rate limit: SlowAPI
Residual risk: MEDIUM (acceptable for MVP)

Threat D3: Blockchain gas griefing
Attack vector: Flood blockchain transactions to exhaust issuer ETH
Likelihood: LOW (requires authorized wallet access)
Mitigation:
└── Only authorized issuers can submit write transactions
Residual risk: LOW

ELEVATION OF PRIVILEGE
════════════════════════
Threat E1: Employer escalates to UNIVERSITY_ADMIN role
Attack vector: Manipulate JWT payload to change role
Mitigation:
├── RS256 signed JWT (payload modification invalidates signature)
├── Role re-validated from JWT on every request
└── Role embedded by backend at token creation (user cannot supply it)
Residual risk: NONE

Threat E2: University admin of University A manages University B's data
Attack vector: Supply University B's IDs in API requests
Mitigation:
├── Ownership check: user.university_id must match resource.university_id
└── Contract: onlyOriginalIssuer on revocation
Residual risk: VERY LOW
```

## 2.2 Risk Prioritization Matrix

```
RISK PRIORITIZATION MATRIX
════════════════════════════

Risk                                    Likelihood  Impact  Priority
────────────────────────────────────────────────────────────────────
Certificate PDF tampering               HIGH        CRITICAL  P1
Unauthorized certificate issuance      MEDIUM       CRITICAL  P1
Credential theft (login)               MEDIUM       HIGH      P1
JWT theft via XSS                      MEDIUM       HIGH      P1
File upload malicious content          MEDIUM       HIGH      P1
API abuse / rate limit bypass          HIGH         MEDIUM    P2
Database breach via SQL injection      LOW          CRITICAL  P2
IDOR certificate access                LOW          HIGH      P2
Smart contract unauthorized access     LOW          CRITICAL  P2
Verification fraud (fake AUTHENTIC)    LOW          CRITICAL  P2
Replay attack on verification          MEDIUM       MEDIUM    P3
DDoS on API endpoints                  MEDIUM       MEDIUM    P3
Dependency supply chain attack         LOW          HIGH      P3
Private key/secret exposure            LOW          CRITICAL  P1

P1: Must be addressed before MVP launch
P2: Must be addressed in MVP
P3: Mitigated in MVP; hardened post-MVP
```

---

# SECTION 3: SECURITY ARCHITECTURE OVERVIEW

## 3.1 Security Control Layers

```
SECURITY CONTROL LAYERS — COMPLETE
═════════════════════════════════════

LAYER 1: NETWORK / TRANSPORT SECURITY
├── TLS 1.2+ enforcement (Nginx reverse proxy)
├── HSTS header (Strict-Transport-Security: max-age=31536000)
├── CORS whitelist (only FRONTEND_URL, never wildcard with credentials)
└── Rate limiting (SlowAPI, per-endpoint)

LAYER 2: AUTHENTICATION SECURITY
├── RS256 JWT (asymmetric — private key never transmitted)
├── 15-minute access token TTL
├── Refresh token: httpOnly Secure SameSite=Strict cookie
├── Token rotation (single-use refresh tokens)
└── bcrypt cost factor 12

LAYER 3: AUTHORIZATION SECURITY
├── RBAC (role in JWT; verified on every endpoint)
├── Ownership checks (service layer, per-resource)
├── MetaMask wallet authorization (smart contract whitelist)
└── Account lockout (5 failed attempts)

LAYER 4: INPUT / VALIDATION SECURITY
├── Pydantic schema validation (all API inputs)
├── MIME type validation (python-magic, not extension)
├── File size limits (10MB upload, 50MB verify)
├── SQL injection prevention (SQLAlchemy ORM parameterization)
└── Path traversal prevention (realpath check)

LAYER 5: BUSINESS LOGIC SECURITY
├── Blockchain as source of truth for verification
├── Certificate immutability (DB trigger + contract enforcement)
├── Two-phase issuance (upload then sign — MetaMask required)
├── Tamper detection (SHA-256 comparison against chain)
└── Two-factor issuance (JWT + MetaMask wallet)

LAYER 6: DATA SECURITY
├── Passwords: bcrypt hash (never plaintext)
├── Refresh tokens: SHA-256 hash in DB (never raw token)
├── Reset tokens: SHA-256 hash in DB
├── Database user: minimal privilege (no DROP, no TRUNCATE)
└── Sensitive columns excluded from API responses (Pydantic exclusion)

LAYER 7: BLOCKCHAIN SECURITY
├── Smart contract: authorized issuer whitelist
├── Owner ≠ issuer separation (platform cannot forge)
├── One-time write per certificate UID
├── One-way revocation (terminal state)
└── No external calls from contract (no reentrancy)

LAYER 8: AUDIT / MONITORING SECURITY
├── Structured logging (every request + response)
├── Verification logs (append-only, DB trigger)
├── Audit log (every INSERT/UPDATE/DELETE on sensitive tables)
├── Authentication events logged (successes + failures)
└── Security events logged (failed auth, privilege violations)

LAYER INTERACTIONS:
If Layer 1 fails (TLS bypass) → Layer 2-8 remain intact
If Layer 2 fails (JWT stolen) → Layer 3 still checks role + ownership
If Layer 3 fails (RBAC bypassed) → Layer 5 still validates on blockchain
If Layer 5 fails → Layer 7 contract enforcement still blocks
Each layer is independent; compromise of one does not compromise all.
```

## 3.2 Security Boundary Map

```
SECURITY BOUNDARY MAP
══════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│  BOUNDARY 0: PUBLIC INTERNET (UNTRUSTED)                                │
│  Threat actors: anyone on the internet                                  │
│                                                                         │
│  Controls: TLS, Rate limiting, CORS                                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS only
┌───────────────────────────────▼─────────────────────────────────────────┐
│  BOUNDARY 1: NGINX REVERSE PROXY                                        │
│  Controls: TLS termination, HSTS, security headers, rate limit assist   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP (internal only)
┌───────────────────────────────▼─────────────────────────────────────────┐
│  BOUNDARY 2: FASTAPI APPLICATION                                        │
│  Controls: Auth dependency, RBAC, Pydantic, rate limiting, error handling│
│                                                                         │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │ Auth Layer │  │ RBAC Layer   │  │ Business Logic + Blockchain    │  │
│  │ JWT verify │  │ Role check   │  │ Service Layer                  │  │
│  │            │  │ Ownership    │  │ Hash service, Blockchain svc   │  │
│  └────────────┘  └──────────────┘  └────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────┬───────────────┘
                           │                             │
              ┌────────────▼──────────┐     ┌────────────▼────────────────┐
              │  BOUNDARY 3: DB       │     │  BOUNDARY 4: BLOCKCHAIN     │
              │  PostgreSQL           │     │  Ethereum (Hardhat/Sepolia)  │
              │  Controls:            │     │  Controls:                  │
              │  - Minimal privilege  │     │  - Authorized issuer list   │
              │  - Immutability trig  │     │  - One-time write           │
              │  - Audit triggers     │     │  - One-way revocation       │
              │  - Parameterized SQL  │     │  - No external calls        │
              └───────────────────────┘     └─────────────────────────────┘
```

---

# SECTION 4: AUTHENTICATION SECURITY DESIGN

## 4.1 Authentication Security Architecture

```
AUTHENTICATION SECURITY DESIGN — COMPLETE
══════════════════════════════════════════

AUTHENTICATION FLOW SECURITY ANALYSIS:
─────────────────────────────────────────

STEP 1: Credential Receipt
User submits: { email, password }
Security controls:
├── HTTPS only (plaintext credential theft impossible via TLS)
├── Rate limit: 5 requests/minute per IP
├── Input validation: Pydantic schema (email format, non-empty password)
└── Request logged (IP, user-agent, timestamp — NOT the password)

STEP 2: User Lookup
Backend queries: UserRepository.get_by_email(email)
Security controls:
├── Parameterized query (SQL injection impossible)
├── Same response time for found vs not-found users:
│   timing_safe_lookup: user found → bcrypt.verify (slow)
│                        user not found → bcrypt.verify(dummy_hash) (same time)
│   Why: if "user not found" returns faster, timing reveals valid emails
└── Consistent error message: "Invalid credentials" (not "User not found")

STEP 3: Account State Validation
Check order (fail fast, cheapest checks first):
1. Account locked? (locked_until > now)
2. Account active? (is_active == True)
3. Password correct? (bcrypt.verify — most expensive, last)
Reason: if account is locked, no bcrypt needed (saves CPU)

STEP 4: Password Verification
bcrypt.verify(submitted_password, stored_hash)
Security properties:
├── bcrypt cost factor 12 (~300ms per verify — attacker gets ~3 checks/second)
├── Adaptive: increase cost as hardware improves
└── Salt embedded in hash (every hash is unique even for same password)

STEP 5: Failed Attempt Handling
On wrong password:
├── Increment: users.failed_login_attempts += 1
├── If attempts >= 5:
│   └── Lock: users.locked_until = NOW() + 10 minutes
├── Log: user_login_failed { email_hash, ip, attempt_count }
│   Note: hash the email in logs (not plaintext) to reduce PII in logs
└── Return: "Invalid credentials" (same message for wrong email/password)

STEP 6: Successful Authentication
├── Reset: failed_login_attempts = 0
├── Update: last_login_at, last_login_ip
├── Generate: access_token (RS256 JWT, 15-min TTL)
├── Generate: refresh_token (64-byte cryptographically random)
├── Hash: SHA-256(refresh_token) → store hash in refresh_tokens table
├── Set cookie: Set-Cookie: refresh_token={raw}; HttpOnly; Secure;
│              SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=604800
└── Return body: { access_token, user: { id, email, role, ... } }
    Note: user object NEVER includes password_hash, reset_token, etc.


BRUTE FORCE PROTECTION MATRIX:
─────────────────────────────────

Attack: Online brute force (rapid login attempts)
Controls:
├── Rate limit: 5/min per IP → max 5 attempts/min
├── Account lockout: 5 wrong attempts → 10-min lockout
└── bcrypt slow: even if rate limits bypassed, 300ms per check

Remaining capacity with all controls:
5/min × 60 min = 300 attempts/hour max
At 300ms/check: practically limited to 200/hour
Keyspace of 8-char password: ~100 trillion
Time to brute force: millions of years

Attack: Credential stuffing (known username/password pairs)
Controls:
├── Same rate limit applies per IP
├── Lockout after 5 attempts per account
└── Log correlation can detect distributed stuffing

Attack: Password spraying (one password, many accounts)
Controls:
├── Rate limit per IP (5/min)
└── Lockout per account after 5 attempts

Note: More sophisticated attacks (residential proxy rotation) are
post-MVP concern. MVP rate limiting is IP-based.
```

---

**[Design Decision A]** The password verification is intentionally **slow (bcrypt cost 12, ~300ms)** and uses **timing-safe comparison** (dummy hash check for missing users). **[Why]** Fast verification creates timing side channels that reveal whether a username exists and enables rapid brute force. bcrypt's intentional slowness limits online attacks to ~3 attempts/second maximum even if rate limiting is bypassed. The dummy hash for non-existent users ensures the same response time whether the email exists or not, preventing user enumeration via timing. **[Requirement satisfied]** Protection against password attacks; user enumeration prevention. **[Alternative rejected]** SHA-256 for password hashing: cryptographically fast (defeats the purpose), no built-in salt rotation, vulnerable to GPU-accelerated brute force. Argon2: stronger than bcrypt in theory but adds external dependency; bcrypt is the well-audited, widely deployed standard.

---

# SECTION 5: JWT SECURITY STRATEGY

## 5.1 JWT Security Architecture

```
JWT SECURITY STRATEGY — COMPLETE
══════════════════════════════════

JWT ALGORITHM: RS256 (RSA Signature with SHA-256)
────────────────────────────────────────────────────

Why RS256 over HS256:
├── HS256: single shared secret (sign + verify)
│   Risk: any service that can verify can also forge tokens
│   Risk: secret rotation is disruptive
└── RS256: private key (sign only) + public key (verify only)
    Benefit: public key can be distributed without enabling forgery
    Benefit: key rotation: new private key → deploy without secret coordination
    Benefit: audit: which key signed this token? (key ID in header)

Key specifications:
├── Algorithm: RS256 (asymmetric RSA + SHA-256)
├── Key size: 2048-bit minimum RSA (4096-bit recommended post-MVP)
├── Private key: PEM format, stored in JWT_PRIVATE_KEY env var
├── Public key: PEM format, stored in JWT_PUBLIC_KEY env var
├── Key storage: environment variables only (never in code, never in DB)
└── Key rotation: described in Section 29 (Secrets Management)

JWT PAYLOAD SECURITY:
──────────────────────
Payload content:
{
  "sub": "user-uuid",              // Subject: user ID (UUID, non-guessable)
  "role": "UNIVERSITY_ADMIN",      // Role: embedded from DB at token creation
  "university_id": "uuid | null",  // Scopes university admin access
  "email": "user@domain.com",      // For display only
  "jti": "unique-uuid",            // JWT ID: enables revocation tracking
  "iat": timestamp,                // Issued at
  "exp": timestamp,                // Expiry (15 minutes from iat)
  "iss": "credential-platform"     // Issuer: validates token source
}

What is NOT in the payload:
├── password_hash (obvious)
├── sha256_hash values (unnecessary)
├── wallet_address (privacy)
└── Any financial or highly sensitive data

Why role is in JWT payload:
├── Eliminates DB query for role check on every request
├── Role is signed → cannot be forged without private key
└── If user's role changes, their existing tokens still show old role
    (acceptable: tokens expire in 15 min; user must re-login for role change)

JWT VALIDATION — COMPLETE CHECKLIST:
──────────────────────────────────────
Every JWT decode operation validates:
1. Signature: RS256 signature valid against public key
2. Expiry (exp): token not expired (15-min window)
3. Issuer (iss): matches configured ISSUER value
4. Algorithm: exactly RS256 (no "none" algorithm, no HS256 downgrade)
5. Subject (sub): valid UUID format
6. Role: valid UserRole enum value
7. User exists in DB: UserRepository.get_by_id(sub) must return active user

Why validate user exists AND is_active on every request:
├── JWT is valid for 15 minutes after issuance
├── In 15 minutes, a user's account could be deactivated
├── Without this check, deactivated users could continue operating
└── This is the cost of stateless JWT: one extra DB query per request
    Alternative: shorter TTL (5 min) without DB check — rejected (too disruptive)

ALGORITHM CONFUSION ATTACK PREVENTION:
────────────────────────────────────────
Attack: Attacker changes JWT header algorithm to "none" or "HS256"
Defense:
└── JWT decode must specify: algorithms=["RS256"] (explicit whitelist)
    If algorithm is not RS256 → reject immediately
    The JWT library must not use the algorithm from the JWT header itself

TOKEN STORAGE SECURITY:
────────────────────────
Access Token:
├── Storage: React memory (AuthContext state)
├── XSS protection: yes (memory not accessible to injected scripts)
└── Persistence: lost on page refresh → restored via refresh token

Refresh Token:
├── Storage: httpOnly cookie
│   HttpOnly: JS cannot read it (XSS cannot steal refresh token)
│   Secure: only sent over HTTPS
│   SameSite=Strict: not sent on cross-site requests (CSRF protection)
│   Path=/api/v1/auth/refresh: only sent to refresh endpoint (minimal exposure)
└── DB: SHA-256 hash of raw token (raw token never stored)

Why SHA-256 hash of refresh token in DB:
├── If DB is compromised, raw refresh tokens are not exposed
├── Attacker has hashes but cannot reverse to raw tokens
└── SHA-256 is appropriate here (not bcrypt) because:
    Refresh tokens are 64-byte cryptographically random values
    (not user-chosen passwords, so no need for GPU-resistant hash)
    A single SHA-256 comparison is fast (legitimate use, many users)

TOKEN REVOCATION STRATEGY:
────────────────────────────
Access Token: NO server-side revocation in MVP
├── Rationale: 15-minute TTL limits damage from stolen token
├── On logout: refresh token is revoked (future access tokens cannot be issued)
└── On password change: ALL refresh tokens revoked → all sessions terminated

Refresh Token: Server-side revocation
├── Each token is single-use (rotation: use revokes old, issues new)
├── Revoked tokens: is_revoked = True in refresh_tokens table
├── Logout: mark current refresh token as revoked
└── Theft detection: if revoked token is used → revoke ALL user tokens
    Reason: token already used but is being used again → stolen

Post-MVP improvement: Access token denylist (Redis-backed JTI denylist)
for immediate revocation of compromised access tokens.
```

---

**[Design Decision A]** Access tokens are stored in **React memory**, not localStorage or cookies. Refresh tokens are in **httpOnly cookies**. **[Why]** This is the most secure configuration for a browser-based application. localStorage is readable by any JavaScript (XSS steals token instantly). Regular cookies are also readable by JS. Only httpOnly cookies are truly inaccessible to JavaScript. The access token in memory is lost on refresh but is restored silently via the httpOnly refresh cookie — the user never notices. **[Requirement satisfied]** JWT theft prevention; XSS protection. **[Alternative rejected]** All-localStorage: simpler but XSS vulnerable — catastrophic for a platform where credential theft enables fraudulent certificate issuance. All-httpOnly cookies: CSRF protection required (SameSite=Strict handles this but adds complexity). The hybrid memory+httpOnly cookie approach is the industry-recommended pattern.

---

# SECTION 6: PASSWORD SECURITY STRATEGY

## 6.1 Password Lifecycle Security

```
PASSWORD SECURITY STRATEGY — COMPLETE
═══════════════════════════════════════

PASSWORD STORAGE:
──────────────────
Algorithm: bcrypt
Cost factor: 12 (verify: ~300ms on modern hardware)
Why 12 (not higher): 
├── 10: ~75ms (too fast for 2025 hardware)
├── 12: ~300ms (strong protection, acceptable login latency)
├── 14: ~1200ms (good security, poor UX for mobile)
└── Verify at deployment: benchmark on actual hardware; adjust if <100ms

bcrypt properties:
├── Adaptive (cost factor can increase over time)
├── Built-in per-hash salt (no separate salt column needed)
├── 72-character input limit (bcrypt truncates at 72 chars — acceptable)
└── Output: 60-character string stored in password_hash column

PASSWORD REQUIREMENTS (enforced at API + frontend):
────────────────────────────────────────────────────
Minimum requirements:
├── Length: 8 characters minimum
├── Uppercase: at least 1
├── Lowercase: at least 1
├── Number: at least 1
└── No maximum length (attacker cannot exhaust bcrypt — it truncates at 72)

Why these specific requirements:
├── Length 8: minimum for meaningful password space
├── Mixed case + number: increases keyspace significantly
└── No special character requirement: reduces user friction
    (special chars cause more "forgotten password" events than they prevent attacks)

Password validation:
├── Backend: Pydantic field validator (enforced always)
├── Frontend: React Hook Form + Pydantic mirror (UX only, not security)
└── Rejected passwords: silent rejection with message (no suggestions)

PASSWORD CHANGE SECURITY:
───────────────────────────
On password change:
1. Verify: current password must be provided
2. Validate: new password meets requirements
3. Hash: new password with bcrypt (cost 12)
4. Update: password_hash + password_changed_at in DB
5. Revoke: ALL existing refresh tokens for this user
6. Log: password_changed event (user_id, ip, timestamp)

Why revoke all refresh tokens on password change:
If attacker has a refresh token, they can keep issuing access tokens
indefinitely even after the user changes their password.
Revoking all tokens forces all sessions to re-authenticate
with the new password.

PASSWORD RESET SECURITY:
──────────────────────────
Reset flow:
1. User requests reset via email
2. Backend: generate 64-byte cryptographically random token
3. Store: SHA-256(token) in users.reset_token_hash (not raw token)
4. Email: send raw token to registered email (not stored anywhere)
5. Token TTL: 1 hour (enforced by reset_token_expires_at)
6. Use: verify SHA-256(submitted_token) == stored hash
7. After use: clear reset_token_hash immediately (one-time use)

Reset token security properties:
├── Raw token never in database (only hash stored)
├── Email is the delivery channel (attacker must control email)
├── 1-hour expiry (limits window of opportunity)
├── Single-use (token destroyed after use)
└── Token format: 86 chars (URL-safe base64 of 64 bytes)

WHAT IS NEVER DONE WITH PASSWORDS:
────────────────────────────────────
├── Never logged (not even hashed — logged as "[PASSWORD]" placeholder)
├── Never stored in plaintext anywhere
├── Never stored as MD5 or SHA-256 (these are not password hashing functions)
├── Never sent back to user (not even in admin tools)
└── Never in error messages (even "password too short" doesn't echo input)
```

---

# SECTION 7: AUTHORIZATION (RBAC) SECURITY DESIGN

## 7.1 RBAC Security Architecture

```
RBAC SECURITY DESIGN — COMPLETE
═════════════════════════════════

RBAC SECURITY LAYERS:
─────────────────────

LAYER 1: Role Embedding at Token Creation
├── Role read from DB at login
├── Embedded in signed JWT payload
└── Cannot be changed by user (JWT is signed with RS256 private key)

LAYER 2: Role Verification at Every Request
├── JWT decoded on every request
├── Role extracted from token payload
├── require_role(role) dependency applied per endpoint
└── Mismatch → HTTP 403 Forbidden

LAYER 3: Ownership Verification in Service Layer
├── Role check: "Are you a university admin?"
├── Ownership check: "Is this your university's certificate?"
└── Both must pass for resource access

LAYER 4: Blockchain Authorization
├── Smart contract: authorizedIssuers[msg.sender] check
├── Independent of application RBAC
└── Cannot be bypassed via API manipulation

WHY FOUR LAYERS (not one):
Each layer protects against different failure modes:
├── Layer 1 fails: JWT secret exposed → still need Layer 2 (decode check)
├── Layer 2 fails: code bug → still need Layer 3 (service check)
├── Layer 3 fails: service bug → still need Layer 4 (contract check)
└── Layer 4 fails: impossible without wallet key (cryptographic)


ROLE PERMISSION ENFORCEMENT RULES:
────────────────────────────────────

UNIVERSITY_ADMIN can:
├── Read/write own university's certificates
├── Initiate blockchain transactions (via MetaMask)
├── View verification logs for own university's certificates
└── Cannot touch any other university's data

STUDENT can:
├── Read own certificates only (ownership check: cert.student_id == user.id)
├── Download own certificate files
├── Generate share links for own certificates
└── Cannot view other students' data

EMPLOYER can:
├── Upload certificates for verification
├── View own verification results only (ownership: log.verifier_user_id == user.id)
└── Cannot access university or student administrative data

PRIVILEGE ESCALATION ATTACK MATRIX:
──────────────────────────────────────
Attack: Student tries to access POST /certificates/issue
Defense: require_role("UNIVERSITY_ADMIN") → 403 (role in JWT is STUDENT)

Attack: University admin tries to revoke another university's certificate
Defense: Ownership check → certificate.university_id != user.university_id → 403
         AND contract: onlyOriginalIssuer modifier rejects wrong wallet

Attack: Employer tries to read student certificate details
Defense: Endpoint /student/credentials/* requires role=STUDENT → 403

Attack: Client manipulates JWT payload to change role
Defense: RS256 signature verification → signature invalid → 401

SUPER_ADMIN ROLE:
──────────────────
Architecture defines SUPER_ADMIN for platform administration.
Security properties:
├── Not a regular user role (no self-registration to SUPER_ADMIN)
├── Created directly in DB during deployment (not via API)
├── Can verify universities (set is_verified=True)
└── Cannot issue certificates (still not in authorizedIssuers on contract)
    This prevents platform operator from forging credentials.
```

---

**[Design Decision A]** Ownership checks are implemented in the **service layer**, not the API layer or database layer. **[Why]** The service layer has access to both the current user (from JWT via dependency injection) and the resource being accessed (from the repository). The API layer (routers) should not reach into the database for ownership checks — that violates layer separation. The database layer (repositories) should not contain authorization logic — that couples data access to business rules. The service layer is the correct security control point for ownership verification. **[Requirement satisfied]** Prevents IDOR; protects student data isolation; university admin scoping. **[Alternative rejected]** Database Row Level Security (RLS): would work but makes authorization invisible in code review, harder to test, and tightly coupled to database schema. API layer ownership checks: violates layer separation and makes routers bloated with business rule logic.

---

# SECTION 8: SESSION SECURITY DESIGN

## 8.1 Session Lifecycle Security

```
SESSION SECURITY DESIGN — COMPLETE
════════════════════════════════════

SESSION ARCHITECTURE OVERVIEW:
─────────────────────────────────
This platform uses a TOKEN-BASED session model (stateless JWT),
not a server-side session store.

Comparison:
Server-side sessions:
├── Pro: immediate revocation
├── Pro: no token storage problem
├── Con: server state (not scalable)
└── Con: requires session store (Redis complexity for MVP)

Stateless JWT:
├── Pro: no server state
├── Pro: scales horizontally
├── Con: revocation requires workaround (refresh token revocation)
└── Con: access token lives 15 minutes after logout

Decision: Stateless JWT with refresh token revocation (per architecture)
Rationale: 15-minute TTL is acceptable risk for MVP


SESSION ESTABLISHMENT:
────────────────────────
On login success:
├── Access token (JWT, 15-min) → response body (React memory)
├── Refresh token (opaque, 7-day) → httpOnly Secure SameSite=Strict cookie
└── Both tokens stored in DB (refresh token as hash)


SESSION PERSISTENCE ACROSS PAGE REFRESH:
──────────────────────────────────────────
Problem: access token in memory is lost on page refresh
Solution:
1. App.jsx useEffect on mount
2. POST /auth/refresh (cookie auto-sent by browser)
3. New access token returned
4. Session restored silently

Security of this flow:
├── httpOnly cookie cannot be read by JS (XSS safe)
├── SameSite=Strict: cookie not sent cross-site (CSRF safe)
├── Refresh rotated: old token revoked on every use
└── Failed refresh: user redirected to login (not error exposed)


SESSION TERMINATION:
─────────────────────
Explicit logout:
├── POST /api/v1/auth/logout
├── Backend: revoke refresh token (is_revoked = True)
├── Frontend: clear AuthContext (access token gone)
└── Cookie: Max-Age=0 (cleared by backend response)

Auto-logout (token expiry):
├── Access token expires → 401 response
├── Axios interceptor: attempt refresh
├── Refresh token valid: new access token, request retried (silent)
└── Refresh token invalid/expired: frontend dispatches LOGOUT → login page

Session invalidation events:
├── Explicit logout: current session revoked
├── Password change: ALL sessions revoked (all refresh tokens)
├── Account deactivation: is_active=False → JWT validation rejects
└── Suspicious activity (stolen token detected): ALL sessions revoked


CSRF PROTECTION:
─────────────────
CSRF is relevant when credentials are in cookies.
Our design:
├── Refresh token: SameSite=Strict (browser won't send cross-site)
├── API calls: use JSON body + Authorization header (not form-based)
├── JavaScript Fetch/Axios: cannot be triggered by CSRF (requires JS)
└── No state-changing form submissions (all POST via JavaScript)

Result: CSRF attack impossible because:
1. SameSite=Strict prevents cookie being sent cross-site
2. Our API requires JSON + Bearer token (not form data)
3. CSRF requires the victim's browser to submit a form
   (attacker cannot use Fetch API cross-origin due to CORS)


CONCURRENT SESSION POLICY:
────────────────────────────
MVP: Multiple concurrent sessions allowed
Rationale: University admin may need desktop + laptop access
Security implication: stolen token can coexist with legitimate session
Mitigation: 15-minute TTL limits damage window
Post-MVP: session listing + selective revocation
```

---

# SECTION 9: API SECURITY STRATEGY

## 9.1 Complete API Security Architecture

```
API SECURITY STRATEGY — COMPLETE
══════════════════════════════════

API SECURITY CONTROLS BY LAYER:
─────────────────────────────────

TRANSPORT LAYER:
├── HTTPS enforced (Nginx; HTTP → HTTPS redirect)
├── TLS 1.2 minimum (TLS 1.0/1.1 disabled in Nginx config)
├── HSTS: Strict-Transport-Security: max-age=31536000; includeSubDomains
└── Certificate: Let's Encrypt (free, auto-renewed)

REQUEST LAYER:
├── CORS: allowed_origins from FRONTEND_URL env var only
│   NEVER: allow_origins=["*"] with allow_credentials=True
│   This combination would allow any site to make credentialed requests
├── Content-Type validation: JSON body requires Content-Type: application/json
├── Request size limit: MAX_REQUEST_SIZE = 15MB (accommodates file uploads)
└── X-Request-ID: generated per request (UUID); returned in response headers

RESPONSE SECURITY HEADERS:
├── X-Content-Type-Options: nosniff
│   Prevents MIME type sniffing (important for file downloads)
├── X-Frame-Options: DENY
│   Prevents clickjacking
├── Referrer-Policy: strict-origin-when-cross-origin
│   Limits referrer information leakage
└── Server: (removed — hide framework/version)

These headers are set by Nginx; FastAPI adds X-Request-ID and X-Content-Type-Options.


AUTHENTICATION SECURITY PER ENDPOINT:
───────────────────────────────────────
Public endpoints (no auth):
├── POST /auth/login
├── POST /auth/register
├── POST /auth/refresh (uses cookie, not Bearer)
└── GET /verify/qr/{token}

Protected endpoints (require Bearer JWT):
└── All other /api/v1/* endpoints

File-serving endpoints:
└── GET /student/credentials/{id}/download
    Extra check: Bearer JWT + ownership check + file path validation


INJECTION ATTACK PREVENTION:
──────────────────────────────
SQL Injection:
├── Protection: SQLAlchemy ORM (parameterized queries by default)
├── All DB operations via ORM (no raw SQL strings with user input)
└── Verification: code review rule — no raw string concatenation in queries

NoSQL Injection: Not applicable (no NoSQL database)

Command Injection:
├── Protection: no subprocess calls with user input
├── No exec(), eval() with dynamic content
└── File operations: pathlib + realpath check (no shell=True)

Template Injection: Not applicable (no server-side templates)

XSS via API Response:
├── FastAPI returns JSON (not HTML)
├── React escapes all dynamic content
└── Content-Type: application/json (browsers don't execute JSON)


INFORMATION DISCLOSURE PREVENTION:
────────────────────────────────────
In error responses:
├── Never include: stack traces, SQL queries, file paths, env vars
├── Never include: internal service names, framework versions
└── Return: generic error message + error code

In API responses:
├── Never include: password_hash in user responses
├── Never include: reset_token_hash
├── Never include: internal database IDs that shouldn't be exposed
└── Use Pydantic response schemas to control exactly what is serialized

Server header:
└── Remove "Server: uvicorn" / "Server: python" headers (information leakage)


API VERSIONING SECURITY:
─────────────────────────
All endpoints: /api/v1/ prefix
When v2 is needed: v1 runs alongside v2 during deprecation period
Security implication: old vulnerable v1 endpoints cannot be accessed after v1 sunset
The versioning strategy ensures controlled deprecation, not indefinite legacy exposure.
```

---

# SECTION 10: BACKEND SECURITY STRATEGY

## 10.1 FastAPI Application Security

```
BACKEND SECURITY STRATEGY — COMPLETE
═════════════════════════════════════

PYTHON SECURITY CONFIGURATION:
────────────────────────────────
Application mode:
├── DEBUG=False in production (disables debug endpoints, tracebacks)
├── SHOW_DOCS=False in production (disables /docs and /redoc)
│   Why: Swagger UI provides attacker with complete API map
└── LOG_LEVEL=INFO (not DEBUG — debug logs may contain sensitive data)

Python-specific security:
├── No eval() with user input (code injection prevention)
├── No pickle with untrusted data (deserialization attack prevention)
├── No yaml.load() with user data (use yaml.safe_load())
└── No exec() with user input

SECURITY-CRITICAL DEPENDENCY USAGE:
──────────────────────────────────────

hashlib (SHA-256):
├── Used for: hashing files, hashing tokens
├── NOT used for: password hashing (bcrypt is used instead)
└── Security note: hashlib.sha256 is deterministic and fast —
    appropriate for file fingerprinting, NOT for passwords

python-jose (JWT):
├── Configuration: algorithms=["RS256"] (explicit whitelist — prevents algorithm confusion)
├── verify_signature=True (explicit — never disable)
└── audience/issuer validation enabled

passlib (bcrypt):
├── Configuration: schemes=["bcrypt"], deprecated="auto"
├── rounds=12 (cost factor 12)
└── Never downgrade to sha256_crypt or plaintext

python-magic (MIME detection):
├── Must be installed with libmagic system dependency
├── Used in: file upload validation
└── Reads actual file header bytes (not filename/extension)

MIDDLEWARE SECURITY ORDER:
───────────────────────────
Middleware stack (order is security-critical):
1. CORS: first (reject cross-origin requests before any processing)
2. RequestID: generate trace ID (all subsequent logs tagged)
3. StructuredLogging: log request details (BEFORE auth — to log failed auth)
4. RateLimiter: before auth (prevent resource exhaustion without auth overhead)
5. (Auth happens in FastAPI dependency, not middleware)

Why auth as dependency (not middleware):
├── Middleware: applies globally, needs complex exclusion list
├── Dependency: opt-in per endpoint (explicit security declaration)
└── Missed exclusion in middleware → security hole
    Missing dependency on endpoint → more obvious in code review

ENVIRONMENT ISOLATION:
───────────────────────
Development:
├── Hardhat local blockchain
├── Local PostgreSQL
├── Debug=True (local only)
└── CORS: localhost:3000

Staging (Sepolia):
├── Sepolia testnet
├── Staging PostgreSQL
├── Debug=False
└── CORS: staging frontend URL

Production: (post-MVP)
├── Mainnet or Polygon
├── Production PostgreSQL
├── Debug=False
└── CORS: production frontend URL only

Never cross environments:
├── Production credentials never in development
└── Development wallets never authorized on staging/production contracts
```

---

# SECTION 11: FRONTEND SECURITY STRATEGY

## 11.1 React Application Security

```
FRONTEND SECURITY STRATEGY — COMPLETE
═══════════════════════════════════════

XSS (CROSS-SITE SCRIPTING) PREVENTION:
────────────────────────────────────────
React's default protection:
├── JSX escapes all dynamic content automatically
├── {user.name} → HTML-encoded (not raw HTML)
└── Strings rendered as text, not markup

Rules that must be followed:
├── NEVER use dangerouslySetInnerHTML with user-supplied content
│   Exception: sanitized markdown (post-MVP, not in MVP)
├── NEVER set innerHTML directly via DOM manipulation
├── NEVER use eval() with dynamic content
└── NEVER use Function() constructor with dynamic content

URLs from user input:
├── NEVER use: window.location.href = userInput
├── ALWAYS use: navigate() from React Router (internal routes only)
└── For external links: validate href starts with http/https (not javascript:)
    href="javascript:..." is an XSS vector in anchor tags

Content Security Policy (CSP):
Set by Nginx:
├── default-src 'self'
├── script-src 'self' (no inline scripts — Vite produces external bundles)
├── style-src 'self' (TailwindCSS compiled to external file)
├── img-src 'self' data: (for QR code data URIs)
├── connect-src 'self' {API_URL} {BLOCKCHAIN_RPC_URL}
└── frame-ancestors 'none' (prevents embedding in iframes)

Why CSP matters for JWT security:
├── Even if XSS is found, CSP may prevent exfiltration
├── Inline script injection blocked (most XSS payloads use inline scripts)
└── No eval() → blocks common XSS techniques


SENSITIVE DATA IN FRONTEND:
────────────────────────────

Access token:
├── Location: React state (JavaScript memory)
├── Not in: localStorage, sessionStorage, cookies
├── Cleared on: logout, page navigation doesn't clear it
└── XSS impact: if XSS runs, it CAN steal memory (so prevent XSS first)

SHA-256 hashes:
├── Displayed: first 16 chars + "..." (truncated)
├── Copy: full hash via clipboard API (user-initiated)
└── Never in URL parameters (visible in server logs, browser history)

Certificate UIDs:
├── Displayed as-is (e.g., MIT-2025-00142)
├── Acceptable in URLs (/university/certificates/MIT-2025-00142)
└── Not sensitive (required for blockchain lookup)

Wallet addresses:
├── Display: truncated (0x1234...5678)
└── Full address never logged to console in production


BUILD-TIME SECURITY:
─────────────────────
Vite production build:
├── Source maps: disabled (prevents reverse engineering of app logic)
│   vite.config.js: build.sourcemap = false
├── Console.log removal:
│   vite.config.js: esbuild.drop = ['console', 'debugger']
├── Minification: enabled (obfuscation + size reduction)
└── Tree shaking: removes unused code (reduces attack surface)

Environment variables:
├── VITE_ prefix: only these are included in build
├── Never include: JWT private keys, DB passwords, blockchain RPC secrets
│   (All backend secrets; frontend never needs them)
└── Safe to include: VITE_API_URL, VITE_CONTRACT_ADDRESS


DEPENDENCY SECURITY (FRONTEND):
─────────────────────────────────
npm audit: run before every deployment
├── npm audit --audit-level=high (fail on high severity)
└── Review: moderate vulnerabilities individually

package-lock.json: committed to Git
├── Exact versions pinned
└── Prevents version drift introducing vulnerable packages

Third-party scripts: NONE
├── No Google Analytics (MVP)
├── No CDN-loaded scripts
└── Why: third-party scripts run in same JavaScript context (XSS risk)
    If script is compromised, it can read access token from React state
```

---

# SECTION 12: DATABASE SECURITY STRATEGY

## 12.1 PostgreSQL Security Architecture

```
DATABASE SECURITY STRATEGY — COMPLETE
═══════════════════════════════════════

DATABASE ACCESS CONTROL:
─────────────────────────
Application database user: credential_app_user
Permissions:
├── SELECT, INSERT, UPDATE on operational tables
├── SELECT, INSERT on verification_logs (no UPDATE, no DELETE)
├── SELECT, INSERT on audit_log (no UPDATE, no DELETE)
└── USAGE on sequences

Permissions NOT granted:
├── DROP TABLE (prevents accidental/malicious table deletion)
├── TRUNCATE (prevents mass data deletion)
├── CREATE TABLE (prevents schema modification)
├── ALTER TABLE (prevents schema modification)
├── DELETE on audit tables (immutability enforcement)
└── SUPERUSER (never grant superuser to app)

Separation of roles:
├── credential_app_user: runtime application access (above)
├── credential_readonly: reporting/analytics (SELECT only)
├── credential_admin: DBA-only (not used by application)
└── postgres (superuser): only for initial setup, never by app

Connection security:
├── Database connection string: from DATABASE_URL env var (never hardcoded)
├── SSL mode: require (enforce encrypted connection to DB)
│   DATABASE_URL format: postgresql+asyncpg://user:pass@host/db?ssl=require
└── Connection pool: pool_pre_ping=True (detect stale connections)


SQL INJECTION PREVENTION:
──────────────────────────
All database operations via SQLAlchemy ORM:
├── SELECT: select(Model).where(Model.id == parameter) → parameterized
├── INSERT: db.add(Model(**data)) → parameterized
├── UPDATE: update(Model).where(Model.id == id).values(**data) → parameterized
└── No raw SQL: no text("SELECT * FROM users WHERE email = '" + email + "'")

Verification: Code review checklist item:
└── grep -r "text(" backend/ — review any raw SQL for parameterization


SENSITIVE DATA PROTECTION IN DATABASE:
──────────────────────────────────────────
Passwords:
└── Column: password_hash VARCHAR(255)
    Storage: bcrypt(password, cost=12)
    Never: plaintext, MD5, SHA-256 without salt

Refresh tokens:
└── Column: token_hash VARCHAR(64)
    Storage: SHA-256(raw_token)
    Never: raw token value

Reset tokens:
└── Column: reset_token_hash VARCHAR(64)
    Storage: SHA-256(raw_token)
    Never: raw token value

Email verification tokens:
└── Column: email_verify_token VARCHAR(128)
    Storage: SHA-256(raw_token)
    Note: stored as hash, delivered to user via email

Certificate SHA-256 hash:
└── Column: sha256_hash VARCHAR(64)
    This is NOT a secret — it's the document fingerprint.
    It IS sensitive in that it must be immutable once confirmed.
    Immutability enforced by: DB trigger + smart contract (two layers)


DATABASE-LEVEL INTEGRITY CONTROLS:
────────────────────────────────────
DB triggers (enforce immutability):
├── prevent_confirmed_hash_change: raises exception if sha256_hash
│   is modified on a CONFIRMED certificate
├── prevent_immutable_field_change: blocks core field updates on CONFIRMED certs
├── prevent_verification_log_update: UPDATE/DELETE on verification_logs rejected
└── prevent_audit_log_update: UPDATE/DELETE on audit_log rejected

CHECK constraints (enforce data integrity):
├── wallet_address: ^0x[0-9a-fA-F]{40}$ (valid Ethereum address format)
├── sha256_hash: ^[0-9a-f]{64}$ (valid SHA-256 hex string)
├── tx_hash: ^0x[0-9a-fA-F]{64}$ (valid Ethereum TX hash)
└── email: ^[^@\s]+@[^@\s]+\.[^@\s]+$ (valid email format)

These constraints provide a second layer of validation after Pydantic:
even if Pydantic is bypassed, the DB rejects malformed data.


DATA ENCRYPTION (MVP SCOPE):
──────────────────────────────
At rest: NOT encrypted at MVP (filesystem/OS-level access control)
In transit: SSL/TLS enforced for DB connections
Sensitive fields: hashed (not encrypted — hashing is sufficient for passwords/tokens)

Post-MVP encryption targets:
├── certificate.file_path → encrypt PDF content at rest
├── student PII fields → field-level encryption
└── Full-disk encryption (OS level for server)

MVP rationale:
Full encryption at rest requires key management infrastructure
(encryption at rest without key rotation is worse than nothing).
The MVP's threat model focuses on remote attacks (not physical server access).
Physical server access is out of scope for MVP.
```

---

# SECTION 13: SMART CONTRACT SECURITY STRATEGY

## 13.1 Contract Security Architecture

```
SMART CONTRACT SECURITY STRATEGY — COMPLETE
═════════════════════════════════════════════

SMART CONTRACT THREAT MATRIX:
───────────────────────────────

Threat: Unauthorized certificate storage
Attack: Non-authorized wallet calls storeCertificate()
Defense: onlyAuthorizedIssuer modifier
└── authorizedIssuers[msg.sender] must be true → revert if not

Threat: Certificate hash overwrite
Attack: Authorized issuer calls storeCertificate() with same UID + different hash
Defense: require(!certificates[certUid].exists) check in storeCertificate()
└── One-time write: once stored, cannot be overwritten by any party

Threat: Cross-university revocation
Attack: University A calls revokeCertificate() on University B's certificate
Defense: onlyOriginalIssuer modifier
└── certificates[certUid].issuingUniversity must equal msg.sender

Threat: Owner forges certificates
Attack: Contract owner calls storeCertificate() to create fraudulent cert
Defense: Owner cannot call storeCertificate() (not in authorizedIssuers by default)
└── CannotAuthorizeOwner: owner explicitly blocked from self-authorization

Threat: Zero-hash storage
Attack: Authorized issuer stores bytes32(0) hash
Defense: validCertHash modifier
└── certHash != bytes32(0) required → revert if zero hash

Threat: Certificate UID hijacking
Attack: Authorized issuer registers another university's cert UID first
Defense: CertificateAlreadyExists revert + DB cross-validation
└── issuingUniversity != expected university → backend detects mismatch

Threat: Reentrancy attack
Attack: Malicious contract calls back into CertificateRegistry during execution
Defense: NO external calls in contract (structural impossibility)
└── Contract makes zero external calls → reentrancy impossible by design

Threat: Integer overflow
Attack: Overflow certificate counters or timestamps
Defense: Solidity 0.8.19 built-in overflow protection (checked arithmetic)
└── All arithmetic reverts on overflow automatically

Threat: Algorithm confusion (signature)
Defense: MetaMask signs via eth_signTransaction (Ethereum standard)
└── Ethereum's secp256k1 signature scheme is the standard; no algorithm choice

Threat: Front-running storeCertificate()
Attack: Observer reads pending TX; submits own TX with same params + higher gas
Defense: Even if front-run succeeds, issuingUniversity = attacker wallet
└── Backend cross-validates issuingUniversity == university.wallet_address
└── Hash match but wrong issuer → CRITICAL error logged; cert marked FAILED

SOLIDITY SECURITY PATTERNS APPLIED:
──────────────────────────────────────

Checks-Effects-Interactions (CEI) pattern:
├── Checks: All require/modifier checks run first
├── Effects: State changes happen after checks
└── Interactions: NO external calls (nothing to put here)

Access control:
├── onlyOwner (admin functions)
├── onlyAuthorizedIssuer (write functions)
├── onlyOriginalIssuer (revocation)
└── No tx.origin used anywhere (phishing protection)

Input validation:
├── validCertUid: length > 0, length <= 50
├── validCertHash: hash != bytes32(0)
└── Address validation: != address(0) for all address parameters

Custom errors (EIP-838):
├── Gas efficient (less information leakage than string messages)
└── Typed errors enable specific client-side error handling

EVENT EMISSION SECURITY:
─────────────────────────
All state-changing functions emit events:
├── CertificateStored: indexed certUid + hash + issuer
├── CertificateRevoked: indexed certUid + revoker
├── IssuerAuthorized/Deauthorized: indexed addresses
└── OwnershipTransferred: indexed addresses

Security benefit of events:
├── Permanent record in Ethereum transaction logs
├── Cannot be deleted (unlike DB records)
├── Queryable by off-chain monitoring tools
└── Compromise detection: unexpected IssuerAuthorized event is visible
```

---

**[Design Decision A]** The smart contract makes **zero external calls** — this is the primary reentrancy defense. **[Why]** Reentrancy attacks require the contract to call an external address, which can then call back into the contract during the first call's execution. With no external calls, this attack class is structurally impossible — not just mitigated by a guard. Adding a reentrancy guard on a contract with no external calls is security theater; avoiding external calls is defense by design. **[Requirement satisfied]** Smart contract misuse prevention; certificate integrity. **[Alternative rejected]** ReentrancyGuard (OpenZeppelin): would work but implies there's an attack surface being protected when there isn't. Adds a dependency and gives false confidence.

---

# SECTION 14: BLOCKCHAIN TRANSACTION SECURITY

## 14.1 Transaction Security Design

```
BLOCKCHAIN TRANSACTION SECURITY — COMPLETE
════════════════════════════════════════════

TRANSACTION SIGNING SECURITY:
───────────────────────────────
All write transactions signed by MetaMask:
├── Private key: user's MetaMask wallet (never on server)
├── Signing: eth_signTransaction via MetaMask web API
└── Backend role: verify receipts only (never signs)

Why MetaMask (not server-side signing):
├── Server compromise cannot create fraudulent certificates
├── Private key in MetaMask: encrypted in browser, password-protected
└── Two-factor: JWT (knowledge) + MetaMask (possession)

TRANSACTION VALIDATION PIPELINE:
──────────────────────────────────
After frontend receives TX receipt:
POST /certificates/confirm-hash { certificate_id, blockchain_tx_hash }

Backend validation steps:
1. Validate tx_hash format: ^0x[0-9a-fA-F]{64}$
2. Get TX receipt: web3.eth.get_transaction_receipt(tx_hash)
   If None → TX not mined: status=SUBMITTED, try again later
3. Check receipt.status == 1 (success)
   If 0 → TX failed: mark FAILED, log error
4. Call getCertificateRecord(cert_uid) on contract
   Verify: record.exists == True
5. Cross-validate hash:
   Stored chain hash == DB cert.sha256_hash
   If mismatch → CRITICAL: log alert, mark FAILED
6. Cross-validate issuer:
   record.issuingUniversity == university.wallet_address
   If mismatch → CRITICAL: log alert, mark FAILED
7. Only if all pass: mark certificate as CONFIRMED

This pipeline prevents:
├── Fake TX hash submission (receipt lookup fails)
├── TX to different contract (cert not found on expected contract)
├── Hash forgery (cross-validation catches mismatch)
└── Wrong issuer (front-running detection)


REPLAY ATTACK PREVENTION:
───────────────────────────
Ethereum native protection:
├── Each TX has a nonce (per-wallet sequential number)
├── Same nonce cannot be used twice by same wallet
└── MetaMask auto-manages nonces

Application-level protection:
├── certificate_uid is unique (UNIQUE constraint in DB + contract check)
├── A TX for the same cert_uid cannot be replayed:
│   First TX: certUID stored, exists=True
│   Second TX: CertificateAlreadyExists revert
└── Replay of a revocation TX: CertificateAlreadyRevoked revert

NETWORK SECURITY:
──────────────────
Chain ID validation:
├── Backend config: NETWORK_CHAIN_ID (31337 local, 11155111 Sepolia)
├── Transactions must be on the expected chain
└── MetaMask rejects transactions for wrong network (user-facing)

RPC URL security:
├── BLOCKCHAIN_RPC_URL: in environment variable (never hardcoded)
├── Local (Hardhat): http://127.0.0.1:8545 (localhost only)
└── Sepolia: Infura/Alchemy URL with project-specific API key

TRANSACTION STATUS TRACKING:
──────────────────────────────
All transactions recorded in blockchain_transactions table:
├── PENDING: TX submitted to mempool
├── SUBMITTED: TX included in a block (waiting for backend confirmation)
├── CONFIRMED: Backend validated all cross-checks
├── FAILED: TX reverted or cross-validation failed
└── REPLACED: TX was speed-up/cancelled (rare)

Monitoring alert triggers:
├── FAILED status after expected confirmation time
├── Hash mismatch in cross-validation
└── Unexpected issuer address
```

---

# SECTION 15: CERTIFICATE ISSUANCE SECURITY

## 15.1 Issuance Security Architecture

```
CERTIFICATE ISSUANCE SECURITY — COMPLETE
══════════════════════════════════════════

ISSUANCE ATTACK SURFACE:
─────────────────────────
Attack 1: Unauthorized issuance (non-university user)
Controls:
├── API: require_role("UNIVERSITY_ADMIN") → 403 if not admin
└── Contract: onlyAuthorizedIssuer → revert if wallet not whitelisted

Attack 2: University Admin issues cert for wrong student
Controls:
├── recipient_email: must match a registered student account
└── student.user_id stored in certificate (permanent record of intended recipient)

Attack 3: Hash manipulation between upload and blockchain storage
Scenario: Attacker intercepts API response and sends different hash to contract
Controls:
├── Backend stores sha256_hash during upload (DB record)
├── Contract stores hash from MetaMask TX
├── confirm-hash endpoint: cross-validates both hashes
└── Mismatch → CRITICAL error → certificate not confirmed

Attack 4: Same PDF resubmitted for multiple different students
Controls:
└── sha256_hash UNIQUE constraint in DB: second upload rejected with DuplicateCertificateError
    Why this matters: prevents one PDF being "issued" to multiple students

Attack 5: PDF modified between hash computation and blockchain confirmation
Scenario: Hash computed from original, PDF saved to disk, PDF modified before blockchain TX
Controls:
├── Hash computed from file bytes BEFORE saving to disk (sequence matters)
├── File saved to disk immediately after hash computation
└── No window for modification between hash and save

ISSUANCE SECURITY SEQUENCE (ordered by security concern):
───────────────────────────────────────────────────────────

Step 1: Authenticate + Authorize
├── JWT validation (RS256 signature + expiry)
├── Role check: UNIVERSITY_ADMIN
├── University is_verified check
└── wallet_address not None

Step 2: File Validation
├── MIME type: python-magic reads file header (not extension)
├── Accepted: application/pdf only
├── Size: <= 10MB
└── Non-empty: > 0 bytes

Step 3: Student Validation
├── recipient_email → find student account
└── Student must be registered (prevents phantom certificates)

Step 4: Hash Computation (BEFORE file save)
├── Read file bytes fully into memory
├── SHA-256 digest computed
├── Hash format validated: 64 lowercase hex chars
└── Hash uniqueness checked in DB

Step 5: File Save
├── UUID filename (not original name)
├── Path: /uploads/certificates/{university_id}/{uuid}.pdf
├── realpath check: path does not escape UPLOAD_ROOT
└── OS file permissions: 640 (owner read/write, group read)

Step 6: DB Record Creation
├── Transaction wraps: certificate_create + blockchain_tx_create
└── blockchain_status = PENDING

Step 7: Return to Frontend (hash + cert_id only)
└── Frontend constructs MetaMask transaction using the hash

Step 8: MetaMask Transaction (frontend)
└── See Section 14 for blockchain transaction security

Step 9: Confirmation + Cross-Validation
└── See Section 14 for TX validation pipeline
```

---

# SECTION 16: CERTIFICATE VERIFICATION SECURITY

## 16.1 Verification Security Architecture

```
CERTIFICATE VERIFICATION SECURITY — COMPLETE
═════════════════════════════════════════════

VERIFICATION ATTACK SURFACE:
──────────────────────────────

Attack 1: Verification fraud — submitting original cert while tampering was done
Scenario: Employer submits original cert but has tampered version on file
Controls:
├── Verification uses the submitted file's hash (not any stored hash)
├── Employer has no ability to "pre-submit" a known-good hash
└── Result: honest verification of exactly what is submitted

Attack 2: Hash pre-image attack — finding a different document with same hash
Attack: Find a tampered PDF that produces the same SHA-256 hash as original
Defense: SHA-256 collision resistance (1 in 2^128 probability)
└── Computationally impossible in practice

Attack 3: Man-in-the-middle during blockchain query
Scenario: Attacker intercepts RPC response and substitutes false hash
Defense:
├── HTTPS to RPC endpoint (TLS protects transit)
├── Signed Ethereum data (blockchain node responses are cryptographically verifiable)
└── If RPC response is tampered: blockchain data would be invalid/unverifiable

Attack 4: Database hash manipulation to fake authentic result
Scenario: DB compromised; sha256_hash changed to match tampered document
Defense:
└── Verification ALWAYS uses blockchain hash (not DB hash)
    Even if DB is compromised, blockchain hash cannot be changed
    Tampered DB hash → mismatch with blockchain → detectable inconsistency

Attack 5: Verification endpoint flooding
Defense:
├── Rate limit: 10/min per IP on POST /verify/upload
└── File size limit: 50MB maximum (reduces resource abuse)

Attack 6: Public QR endpoint probing
Scenario: Attacker systematically scans /verify/qr/{token} values
Defense:
├── Token is 64-byte URL-safe base64 (86 chars, ~2^512 keyspace)
├── Rate limit: 30/min per IP
└── Tokens are opaque (contain no guessable structure)


VERIFICATION INTEGRITY GUARANTEES:
────────────────────────────────────

AUTHENTIC result: (the hardest to fake)
├── submitted_hash == blockchain_stored_hash (verified on chain)
├── Certificate status == ACTIVE on chain (not REVOKED)
└── Certificate record exists in DB (for metadata display)
    (DB existence is supplemental — chain verification is primary)

TAMPERED result: (the most important to detect correctly)
├── submitted_hash != blockchain_stored_hash
└── This is computed from the file the verifier uploaded
    Cannot be faked: verifier would need the exact original PDF
    OR a SHA-256 collision (computationally impossible)

REVOKED result:
├── Certificate status == REVOKED on chain
└── Even if hash matches: REVOKED takes precedence
    An employer cannot use "it matches" to bypass revocation

NOT_FOUND result:
└── certificate_uid not found on chain (never anchored)
    Could be: fake certificate, unregistered certificate, typo


VERIFICATION LOG INTEGRITY:
─────────────────────────────
Every verification creates a verification_log record:
├── submitted_hash: what was uploaded
├── stored_hash: what was on blockchain
├── hash_match: boolean comparison result
├── blockchain_verified: was blockchain actually queried
├── result: AUTHENTIC/TAMPERED/REVOKED/NOT_FOUND
└── Immutable: DB trigger prevents UPDATE/DELETE

Why log both hashes:
├── For TAMPERED results: both hashes prove tampering occurred
├── For forensic investigation: exact evidence preserved
└── Cannot be retroactively altered to hide tampering events
```

---

# SECTION 17: CERTIFICATE REVOCATION SECURITY

## 17.1 Revocation Security Architecture

```
CERTIFICATE REVOCATION SECURITY — COMPLETE
════════════════════════════════════════════

REVOCATION ATTACK SURFACE:
────────────────────────────

Attack 1: Unauthorized revocation (wrong university)
Defense:
├── API: ownership check (cert.university_id == user.university_id)
└── Contract: onlyOriginalIssuer modifier (issuing wallet must match)

Attack 2: Mass revocation via compromised admin account
Scenario: Admin credentials stolen; attacker revokes all university's certs
Defense:
├── MetaMask required: stolen credentials alone insufficient
├── Two-factor: must also control the university's MetaMask wallet
├── Rate limit: revocations are rate-limited
└── Monitoring: spike in revocation events triggers alert

Attack 3: Revocation of non-existent certificate
Defense:
└── Contract: certificateMustExist modifier → CertificateNotFound revert

Attack 4: Double revocation
Defense:
└── Contract: certificateMustBeActive modifier → CertificateAlreadyRevoked revert

Attack 5: Revocation reversal
Attack: Attempt to un-revoke a revoked certificate
Defense:
├── Contract: REVOKED is terminal state (no un-revoke function)
└── No application function to un-revoke

Attack 6: Revocation without reason (audit gap)
Defense:
└── API requires reason (min 10 chars): no silent unexplained revocations


REVOCATION SECURITY SEQUENCE:
───────────────────────────────

Phase 1: Initiation (API)
├── JWT validation: UNIVERSITY_ADMIN
├── Ownership: cert.university_id == user.university_id
├── State check: cert.blockchain_status == CONFIRMED (cannot revoke PENDING)
├── State check: cert.is_active == True (not already revoked)
├── Blockchain check: isAuthorizedIssuer(university.wallet_address)
└── Blockchain check: cert record issuer == university.wallet_address

Phase 2: Signing (MetaMask)
├── University admin signs revokeCertificate(cert_uid)
├── Contract: onlyAuthorizedIssuer + certificateMustExist +
│            certificateMustBeActive + onlyOriginalIssuer
└── Gas paid by university wallet (confirmation of institutional intent)

Phase 3: Confirmation (API)
├── TX receipt validation (same as issuance confirmation)
├── getCertificateRecord: verify status == REVOKED on chain
├── DB update: is_active = False, blockchain_status = REVOKED
└── Audit log: CERTIFICATE_REVOKED event recorded

POST-REVOCATION EFFECTS:
─────────────────────────
Immediate:
├── Any new verification → returns REVOKED result
├── QR scan → verification result shows REVOKED
└── Student credential detail → shows REVOKED badge

Permanent:
├── Cannot be un-revoked (contract + DB)
├── Historical verification logs preserved
└── Blockchain record permanently shows REVOKED
    (anyone can query the blockchain and see the revocation)
```

---

# SECTION 18: FILE UPLOAD SECURITY

## 18.1 File Upload Security Architecture

```
FILE UPLOAD SECURITY — COMPLETE
═════════════════════════════════

FILE UPLOAD THREAT MATRIX:
────────────────────────────

Threat F1: Malicious file disguised as PDF
Attack: Upload script.exe renamed to cert.pdf
Defense:
├── python-magic: reads actual file header bytes (PDF magic: %PDF-)
├── Rejects file if MIME type != application/pdf
└── Extension alone is never trusted

Threat F2: Server-Side Request Forgery (SSRF) via PDF
Attack: Specially crafted PDF with embedded URLs triggers server-side requests
Defense:
├── PDFs are not parsed or rendered by the server
├── Only binary content is hashed (SHA-256)
└── No PDF parsing library called (no libpoppler, no pdfminer on upload path)

Threat F3: Path traversal via filename
Attack: Upload with filename: ../../etc/passwd
Defense:
├── UUID filename used for storage (original filename discarded for path)
├── Stored path: /uploads/{university_id}/{generated_uuid}.pdf
└── os.path.realpath(constructed_path) must start with UPLOAD_ROOT

Threat F4: Storage exhaustion
Attack: Rapid large file uploads to fill disk
Defense:
├── File size limit: 10MB per certificate upload
├── Rate limit: 10/min per IP on /certificates/upload
└── Total storage monitoring (alert at 80% usage — post-MVP)

Threat F5: Zip bomb (decompression bomb)
Not applicable: PDFs don't require decompression in our pipeline.
We read raw bytes; no decompression step.

Threat F6: Directory listing
Attack: Access /uploads/ directory to enumerate all certificates
Defense:
└── /uploads/ is outside Nginx web root (not served directly)
    Files served via API (/student/credentials/{id}/download)
    with authentication + ownership check

Threat F7: Insecure file serving
Attack: Guess certificate file path and download without authorization
Defense:
├── UUID filenames (path is non-guessable)
├── Files not served from web root (Nginx config)
└── Download endpoint: requires JWT + ownership check


FILE UPLOAD VALIDATION PIPELINE:
──────────────────────────────────
1. Content-Length check (before reading):
   If Content-Length > MAX_FILE_SIZE → reject immediately (don't read body)
   
2. MIME type detection (python-magic):
   Read first 1024 bytes → detect MIME type
   Accept: application/pdf only
   
3. Full file read:
   Read complete file into memory for SHA-256 computation
   
4. Size validation (post-read):
   file_bytes length > 0 AND <= 10MB
   
5. Hash computation:
   SHA-256(file_bytes) → 64-char hex string
   
6. Filename generation:
   stored_filename = str(uuid.uuid4()) + ".pdf"
   
7. Path construction + validation:
   full_path = os.path.join(UPLOAD_ROOT, university_id, stored_filename)
   realpath = os.path.realpath(full_path)
   assert realpath.startswith(os.path.realpath(UPLOAD_ROOT))
   
8. File write:
   Write file_bytes to full_path
   Set OS permissions: 640 (owner rw, group r, other none)

This sequence is fixed and must be followed exactly.
Any deviation creates a security gap.


FILE DOWNLOAD SECURITY:
────────────────────────
Endpoint: GET /student/credentials/{id}/download
Controls:
├── JWT authentication required (not public)
├── Role: STUDENT only
├── Ownership: certificate.student_id == current_user.id
├── Load file_path from DB (not from URL parameter)
│   File path is NEVER a URL parameter (prevents path traversal)
├── Validate: os.path.exists(file_path)
├── Validate: os.path.realpath(file_path).startswith(UPLOAD_ROOT)
└── Response headers:
    Content-Type: application/pdf
    Content-Disposition: attachment; filename="{cert_uid}.pdf"
    X-Content-Type-Options: nosniff
    Cache-Control: private, no-store
```

---

# SECTION 19: SHA-256 INTEGRITY PROTECTION STRATEGY

## 19.1 Hash Integrity Architecture

```
SHA-256 INTEGRITY PROTECTION STRATEGY — COMPLETE
══════════════════════════════════════════════════

SHA-256 AS CRYPTOGRAPHIC BRIDGE:
──────────────────────────────────
The SHA-256 hash is the single most security-critical value in the system.
It connects:
├── Off-chain: the physical PDF document
├── On-chain: the blockchain-anchored fingerprint
└── Verification: the employer's submitted document

If this bridge is compromised, the platform's core guarantee fails.

HASH COMPUTATION SECURITY RULES:
──────────────────────────────────
Rule 1: Hash computed from raw binary file bytes (not text, not metadata)
├── Any byte-level change to the PDF → completely different hash
└── Visual-only changes (pixel, metadata, annotation) are also detected

Rule 2: Hash computed BEFORE file is saved to disk
├── Sequence: read → hash → validate hash → save
└── No opportunity for file modification between hash and save

Rule 3: Hash computed server-side (not client-side)
├── Client-side hash computation: attacker could submit pre-computed hash
│   for a different (legitimate) file while submitting a tampered file
└── Server computes hash from the actual bytes it receives

Rule 4: Hash stored as lowercase hex (64 chars)
└── Case-insensitive comparison not needed (always lowercase)

Rule 5: Hash format validated before storage
└── Pydantic validator + DB CHECK constraint: ^[0-9a-f]{64}$

Rule 6: Hash is UNIQUE in the database
└── UNIQUE constraint: prevents same PDF being registered twice
    (prevents "one PDF issued to many students" fraud)

Rule 7: Hash NEVER changes after CONFIRMED status
└── DB trigger: prevent_confirmed_hash_change raises exception if attempted

Rule 8: Blockchain hash is always the verification source
└── Verification uses: blockchain.verifyCertificate(uid, bytes32(submitted_hash))
    Never: database.certificates.sha256_hash == submitted_hash


HASH FORMAT CONVERSION SECURITY:
──────────────────────────────────
Python to Ethereum:
├── Python: sha256_hash = "abc123...def456" (64 lowercase hex chars)
├── Conversion: bytes.fromhex(sha256_hash) → 32 bytes
├── Web3.py: Web3.to_bytes(hexstr="0x" + sha256_hash) → bytes32
└── Security: must validate 64 hex chars before conversion (no padding tricks)

Ethereum to Python (for display/comparison):
├── Web3.py: Web3.to_hex(bytes32_value) → "0x" + 64 hex chars
├── Strip "0x": hex_string = chain_hash[2:]
└── Normalize to lowercase: hex_string.lower()


CONSTANT-TIME HASH COMPARISON:
────────────────────────────────
For token/hash comparisons:
├── Use hmac.compare_digest(hash_a, hash_b) — constant time
└── NOT: hash_a == hash_b — early exit leaks timing information

For certificate hash verification:
├── Comparison is done by the smart contract (EVM equality is constant-time)
└── Python comparison (for cross-validation) uses hmac.compare_digest


WHAT HASH INTEGRITY PROVES:
─────────────────────────────
When verification returns AUTHENTIC:
"The file you uploaded produces the same SHA-256 hash as the file
that [university_wallet_address] anchored on the blockchain on [date]."

This PROVES:
├── The file content is identical to what the university anchored
├── No byte was changed (addition, deletion, or modification)
└── The university's wallet explicitly submitted this exact fingerprint

This DOES NOT PROVE:
├── The underlying educational achievement (off-chain claim)
├── The identity of the physical person named in the certificate
└── The legitimacy of the issuing university (verified separately by platform)
```

---

# SECTION 20: QR VERIFICATION SECURITY

## 20.1 QR Code Security Architecture

```
QR VERIFICATION SECURITY — COMPLETE
═════════════════════════════════════

QR TOKEN SECURITY:
───────────────────
Token generation: secrets.token_urlsafe(48)
├── 48 bytes input → 64 chars URL-safe base64 output
├── Keyspace: 2^(48×8) = 2^384
│   At 1 billion attempts/second: 2^319 years to exhaust
└── Uniqueness: UNIQUE constraint in DB (astronomically rare collision handled by retry)

Token design:
├── OPAQUE: contains no information about the certificate
├── NOT the certificate UUID (prevents enumeration)
├── NOT the SHA-256 hash (prevents information leakage)
└── Single-use token → multiple scans are all valid (by design — scan count tracked)

Token lifecycle:
├── Created: when certificate is confirmed on blockchain
├── Active: is_active=True (all scans work)
├── Deactivated: when certificate is revoked (is_active=False set)
└── Expired: expires_at (optional, NULL by default in MVP)

QR ENDPOINT SECURITY:
─────────────────────
GET /verify/qr/{token}
├── Authentication: NONE REQUIRED (public endpoint)
├── Why public: QR verification is the core public-access feature
│   Students share QR links; recipients scan without accounts
└── Rate limit: 30 requests/minute per IP (prevents token enumeration)

Public endpoint security analysis:
Rate limit of 30/min + 64-char token keyspace:
├── 30/min = 1800/hour = 43,200/day attempts from one IP
├── Keyspace: 2^384 possible tokens
└── Time to find valid token: 2^363 years — computationally impossible

QR IMAGE SECURITY:
───────────────────
QR image served at GET /qr/{token}/image:
├── No authentication required (QR images are public)
├── Token in URL is the access control (opaque)
└── Image served from: /uploads/qr/{cert_id}.png (outside web root)
    Via: streaming response with Content-Type: image/png

QR code content:
└── Encodes only: https://{FRONTEND_URL}/verify/{token}
    No certificate data, no hash, no UID in QR code itself

QR SCAN SECURITY (browser-based scanner):
───────────────────────────────────────────
html5-qrcode camera access:
├── Permission: camera permission required (browser prompt)
├── Data stays in browser: no camera data sent to server
├── Scan result: URL extracted from QR → navigated to internally
└── HTTPS required: camera access denied on non-HTTPS origins

QR URL validation:
├── Extracted URL must start with: https://{FRONTEND_URL}/verify/
└── Reject: any QR that doesn't match expected URL format
    Prevents QR phishing: attacker creates QR pointing to malicious URL
    that looks like the verification page but is fake

Malicious QR code scenario:
Attack: Attacker creates QR code with malicious URL
        (e.g., https://evil.com/verify/FAKE-TOKEN-LOOKS-LEGIT)
Defense: Frontend QR scanner validates URL origin before navigation
Result: Malicious QR ignored; user shown "Invalid QR code" message
```

---

# SECTION 21: INPUT VALIDATION STRATEGY

## 21.1 Multi-Layer Input Validation

```
INPUT VALIDATION STRATEGY — COMPLETE
═══════════════════════════════════════

VALIDATION ARCHITECTURE (THREE LAYERS):
─────────────────────────────────────────

LAYER 1: Transport / Protocol Level
├── Content-Type: application/json required for JSON endpoints
├── Content-Length: size limit for request body
├── URL parameter format: UUID validation in path params
└── Query parameter types: int for page/limit, string for filters

LAYER 2: Schema Level (Pydantic)
├── Type coercion: string "42" → int 42 (where appropriate)
├── Type rejection: wrong types produce 422 immediately
├── Field validators: format, length, pattern, custom logic
└── Model validators: cross-field rules

LAYER 3: Business Rule Level (Service Layer)
├── Uniqueness: email not already registered
├── State: certificate is CONFIRMED before revoke
├── Existence: student account exists for recipient_email
└── Ownership: this is your certificate

All three layers run independently.
A bypass of Layer 1 hits Layer 2.
A bypass of Layer 2 hits Layer 3.
Defense in depth for input validation.


PYDANTIC VALIDATION RULES — COMPLETE:
────────────────────────────────────────

Email fields:
├── Type: EmailStr (Pydantic validates format)
├── Normalize: lowercase (field_validator: email.lower())
└── Max length: 255 chars (matches DB VARCHAR(255))

Password fields (registration only):
├── Min length: 8 chars
├── Pattern: must contain [A-Z], [a-z], [0-9]
└── Max length: 72 chars (bcrypt truncation limit — beyond is accepted but truncated)

UUID path parameters:
├── Type: UUID (Pydantic validates format)
└── Rejects: non-UUID strings (prevent IDOR enumeration attempts with sequential IDs)

SHA-256 hash fields:
└── Pattern: ^[0-9a-f]{64}$ (exactly 64 lowercase hex chars)

Ethereum address fields:
└── Pattern: ^0x[0-9a-fA-F]{40}$ (valid Ethereum address format)

Transaction hash fields:
└── Pattern: ^0x[0-9a-fA-F]{64}$ (valid Ethereum TX hash)

Certificate UID:
└── Pattern: ^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$ (UNIV-YEAR-SEQUENCE)

Date fields:
├── Type: date (ISO-8601 format validated)
└── Custom: issue_date <= today (not in the future)

String length limits (selected fields):
├── degree_title: 300 chars max
├── field_of_study: 300 chars max
├── revocation_reason: 10 chars min, 500 chars max
├── university_name: 300 chars max
└── company_name: 300 chars max

Pagination parameters:
├── page: int, >= 1, default 1
├── limit: int, >= 1, <= 100, default 20
└── Prevent: page=0, limit=999999 (resource exhaustion)


WHAT INPUT VALIDATION PREVENTS:
─────────────────────────────────
├── SQL injection: ORM parameterization + type validation
├── Path traversal: UUID format + server-side path validation
├── Type confusion: explicit type declarations
├── Oversized inputs: length limits at Pydantic level
├── Invalid formats: pattern validation (wallet, hash, UID)
└── Future date certificates: date constraint

WHAT INPUT VALIDATION DOES NOT PREVENT:
─────────────────────────────────────────
├── Authenticated user submitting valid-format but wrong data
│   (business rule violation — handled by service layer)
├── Hash collision (computationally impossible — not a validation problem)
└── MetaMask signing wrong transaction (user UX issue — not input validation)
```

---

# SECTION 22: DATA VALIDATION STRATEGY

## 22.1 Data Integrity Across the Stack

```
DATA VALIDATION STRATEGY — COMPLETE
══════════════════════════════════════

DATA VALIDATION ARCHITECTURE:
───────────────────────────────

VALIDATION POINT 1: Frontend (React Hook Form)
Purpose: Immediate UX feedback
When: On field blur + on form submit
What: Format, required, length, pattern
NOT for security: can be bypassed by direct API calls
IS for security: first gate, reduces malformed data reaching API

VALIDATION POINT 2: Pydantic schemas (FastAPI)
Purpose: Type and format validation
When: Before any route handler executes
What: Type coercion, format patterns, length limits, cross-field rules
HTTP 422 response if validation fails (automatic)
IS for security: cannot be bypassed via API

VALIDATION POINT 3: Service layer (Python)
Purpose: Business rule validation
When: Before any DB write
What: Uniqueness, state consistency, ownership, existence
Raises: Domain exceptions → HTTP 409/400/403
IS for security: contextual business rules

VALIDATION POINT 4: Database constraints (PostgreSQL)
Purpose: Data integrity at storage level
When: On INSERT/UPDATE operations
What: CHECK constraints, UNIQUE constraints, NOT NULL, FK integrity
Raises: DB integrity errors (caught by SQLAlchemy, translated to service errors)
IS for security: final gate, even if all above bypassed

VALIDATION POINT 5: Smart contract (Solidity)
Purpose: Blockchain data integrity
When: On every write function call
What: Hash format, UID format, authorization, state consistency
Raises: Transaction revert (transaction fails entirely)
IS for security: absolute final gate for blockchain operations

DATA CONSISTENCY GUARANTEES:
──────────────────────────────
Database ↔ Blockchain consistency:
├── certificates.sha256_hash must equal chain hash after CONFIRMED
├── certificates.blockchain_status must reflect chain state
├── Enforced by: backend cross-validation on confirm-hash endpoint
└── Detected by: verify endpoint (always queries chain, not just DB)

Temporal consistency:
├── issue_date: validated <= today at issuance
├── confirmed_at: set from block timestamp (not server clock)
└── revoked_at: set from block timestamp (tamper-proof)

Relationship integrity:
├── certificates.student_id: FK → users.id (student must exist)
├── certificates.university_id: FK → universities.id (university must exist)
└── ON DELETE RESTRICT: prevents deleting referenced entities
```

---

# SECTION 23: ERROR HANDLING SECURITY

## 23.1 Secure Error Handling Architecture

```
ERROR HANDLING SECURITY — COMPLETE
════════════════════════════════════

ERROR HANDLING SECURITY PRINCIPLES:
──────────────────────────────────────

Principle 1: Never reveal implementation details
BAD: "SQLALCHEMY ERROR: relation 'certificate' does not exist at line 42"
GOOD: "An error occurred processing your request"

Principle 2: Never reveal system topology
BAD: "Unable to connect to blockchain node at http://127.0.0.1:8545"
GOOD: "Blockchain service temporarily unavailable"

Principle 3: Never reveal user account existence through error messages
BAD: "No account found with this email" (reveals email not registered)
GOOD: "Invalid credentials" (same for wrong email and wrong password)

Principle 4: Use different internal and external error representations
Internal: full exception with stack trace (logs only)
External: sanitized message + error code (response body)

Principle 5: Log what attackers should not see; show what users need
Log: full error, IP, path, user_id, stack trace
Show: generic message + request_id (for support reference)


INFORMATION LEAKAGE PREVENTION IN ERRORS:
────────────────────────────────────────────

What is NEVER in API error responses:
├── Stack traces
├── File paths (/home/user/backend/services/auth_service.py)
├── Database connection strings
├── SQL queries (even sanitized)
├── Internal service names (blockchain_service, hash_service)
├── Framework version (FastAPI 0.110, SQLAlchemy 2.0)
├── Python version
├── Server hostname/IP
└── Environment variable names

What IS in API error responses (intentionally):
├── Error code: machine-readable (e.g., "CERTIFICATE_NOT_FOUND")
├── Message: human-readable, safe (e.g., "Certificate not found")
├── Request ID: for support correlation (not sensitive)
└── Timestamp: ISO-8601 UTC (not sensitive)


SECURITY-RELEVANT ERROR CODE MAPPING:
────────────────────────────────────────
Error Condition         → HTTP Code → Error Code
──────────────────────────────────────────────────────────────────
Wrong email/password    → 401       → INVALID_CREDENTIALS
Account locked          → 423       → ACCOUNT_LOCKED (with unlock time)
JWT expired             → 401       → TOKEN_EXPIRED
JWT invalid             → 401       → TOKEN_INVALID
Wrong role              → 403       → INSUFFICIENT_PERMISSIONS
Wrong ownership         → 403       → ACCESS_DENIED
Certificate not found   → 404       → CERTIFICATE_NOT_FOUND
Already revoked         → 409       → CERTIFICATE_ALREADY_REVOKED
Duplicate certificate   → 409       → DUPLICATE_CERTIFICATE
Invalid file type       → 400       → INVALID_FILE_TYPE
File too large          → 400       → FILE_TOO_LARGE
Blockchain unavailable  → 503       → BLOCKCHAIN_UNAVAILABLE
Transaction failed      → 502       → BLOCKCHAIN_TX_FAILED

Note on ACCOUNT_LOCKED vs INVALID_CREDENTIALS:
One could argue that revealing "account locked" is user enumeration.
Decision: Show account lock status with unlock time (better UX).
Rationale: Account is locked because the attacker already found a valid account.
Showing "account locked" doesn't help the attacker further.
Not showing it creates bad UX for legitimate users.


GLOBAL EXCEPTION HANDLER SECURITY:
────────────────────────────────────
Catch-all handler for unhandled exceptions:
├── Log: CRITICAL level, full traceback (to file/log aggregator)
├── Response: HTTP 500 + generic message
│   "An unexpected error occurred. Request ID: {request_id}"
├── Alert: immediate notification mechanism (post-MVP: email/Slack)
└── NEVER: let raw Python exception propagate to HTTP response
```

---

# SECTION 24: LOGGING SECURITY

## 24.1 Security-Focused Logging Architecture

```
LOGGING SECURITY — COMPLETE
═════════════════════════════

WHAT MUST NEVER BE LOGGED:
────────────────────────────
├── Passwords (in any form, at any log level)
│   Example: POST /auth/login body must not log password field
├── Access tokens (full JWT)
├── Refresh tokens (raw value)
├── Reset tokens (raw value)
├── Database connection strings
├── Private keys (JWT RS256, Ethereum)
├── Credit card numbers (not applicable — no payments in MVP)
└── Any value that could be used for authentication if exposed

WHAT MUST BE LOGGED (security events):
────────────────────────────────────────
Authentication events:
├── LOGIN_SUCCESS: user_id, ip, user_agent, timestamp
├── LOGIN_FAILURE: email_sha256 (not plaintext email), ip, attempt_count, timestamp
│   Why email_sha256: allows correlation across attempts without storing PII in logs
├── ACCOUNT_LOCKED: user_id, ip, locked_until, timestamp
├── TOKEN_REFRESH: user_id, ip, timestamp
├── LOGOUT: user_id, ip, timestamp
└── PASSWORD_CHANGED: user_id, ip, timestamp

Certificate events:
├── CERTIFICATE_UPLOAD: university_id, cert_id, file_size, timestamp
├── CERTIFICATE_HASH_COMPUTED: cert_id, hash_prefix (first 8 chars only), timestamp
├── BLOCKCHAIN_TX_SUBMITTED: cert_id, tx_hash, network, timestamp
├── CERTIFICATE_CONFIRMED: cert_id, tx_hash, block_number, timestamp
├── CERTIFICATE_REVOCATION_INITIATED: cert_id, university_id, reason_length, timestamp
└── CERTIFICATE_REVOKED: cert_id, tx_hash, block_number, timestamp

Verification events:
├── VERIFICATION_STARTED: verifier_id|null, method, ip, timestamp
├── VERIFICATION_BLOCKCHAIN_QUERIED: cert_uid, query_time_ms, timestamp
├── VERIFICATION_COMPLETE: result, cert_id|null, processing_ms, timestamp
├── VERIFICATION_ERROR: error_type, cert_id|null, ip, timestamp
└── QR_SCAN_COMPLETED: token_prefix (first 8 chars), result, ip, timestamp

Security events:
├── UNAUTHORIZED_ACCESS: path, user_id|null, ip, role_required, role_presented
├── OWNERSHIP_VIOLATION: resource_type, resource_id, user_id, ip
├── RATE_LIMIT_EXCEEDED: path, ip, limit, timestamp
├── SUSPICIOUS_ACTIVITY: description, ip, user_id|null
└── CONTRACT_CROSS_VALIDATION_FAILURE: cert_id, expected_hash, actual_hash

Log format (structured JSON via structlog):
{
  "timestamp": "ISO-8601-UTC",
  "level": "INFO|WARNING|ERROR|CRITICAL",
  "event": "LOGIN_FAILURE",
  "request_id": "uuid",
  "user_id": "uuid|null",
  "ip_address": "xxx.xxx.xxx.xxx",
  "user_agent": "Mozilla/...",
  "attempt_count": 3
}


LOG SECURITY CONTROLS:
────────────────────────
Log file permissions:
├── Owner: application user (r/w)
├── Group: log readers (r only)
└── Other: no access

Log retention:
├── Authentication logs: 90 days minimum
├── Certificate event logs: permanent (legal requirement)
├── Verification logs: permanent (in DB via verification_logs table)
└── Error logs: 30 days

Log tampering prevention:
├── Application writes to log file (not read-back)
├── Post-MVP: ship logs to centralized log server immediately
└── Append-only log file (no modification of past entries)
```

---

# SECTION 25: AUDIT TRAIL SECURITY

## 25.1 Audit Trail Architecture

```
AUDIT TRAIL SECURITY — COMPLETE
═════════════════════════════════

TWO-LAYER AUDIT TRAIL:
────────────────────────

LAYER 1: Verification Logs (Domain Audit)
Tables: verification_logs
Purpose: Business-level audit of every verification attempt
Append-only: DB trigger prevents UPDATE and DELETE
Retention: Permanent (never deleted)
Access: University admin (own certs), Employer (own verifications)

LAYER 2: Audit Log (Technical Change Audit)
Table: audit_log
Purpose: Every INSERT/UPDATE/DELETE on sensitive tables
Written by: PostgreSQL triggers (not application code)
Why DB triggers: cannot be bypassed by application bugs or code paths
Retention: Permanent
Access: SUPER_ADMIN / DBA only

AUDIT TRAIL IMMUTABILITY:
───────────────────────────

Enforcement mechanism:
├── DB trigger: prevent_verification_log_update
│   Raises exception if UPDATE is attempted on verification_logs
├── DB trigger: prevent_verification_log_delete
│   Raises exception if DELETE is attempted on verification_logs
├── DB trigger: prevent_audit_log_update
│   Raises exception if UPDATE or DELETE on audit_log
└── Application user permission: no UPDATE/DELETE on audit tables

Why DB-level enforcement (not application-level):
├── Application code can be changed
├── A bug or malicious change in application code could bypass app-level audit
└── Database trigger cannot be bypassed by application logic
    Only DBA-level PostgreSQL access can modify triggers
    (and that access is logged by PostgreSQL itself)


WHAT THE AUDIT TRAIL PROVES:
──────────────────────────────

Audit scenario: "Did University X issue this certificate?"
Evidence:
├── certificates table: university_id, issued_by, created_at
├── blockchain_transactions: tx_hash, from_address, block_number
├── audit_log: INSERT record for certificate (when created, by what DB user)
└── Blockchain: CertificateStored event (issuingUniversity, timestamp)

Audit scenario: "Was this certificate tampered with?"
Evidence:
├── verification_logs: submitted_hash (attacker's file hash)
├── verification_logs: stored_hash (blockchain hash — the original)
├── hash_match: False (explicit tamper evidence)
└── Blockchain: getCertificateRecord (immutable original hash)

Audit scenario: "Who verified this certificate and when?"
Evidence:
└── verification_logs: verifier_user_id, ip_address, verified_at, result

Audit scenario: "Was the audit trail tampered?"
Evidence:
├── DB trigger prevents modification (application-level)
├── audit_log records any attempted UPDATE/DELETE (even if trigger fails somehow)
└── PostgreSQL pg_audit extension (post-MVP) for complete DB-level audit
```

---

# SECTION 26: RATE LIMITING STRATEGY

## 26.1 Rate Limiting Architecture

```
RATE LIMITING STRATEGY — COMPLETE
═══════════════════════════════════

RATE LIMITING IMPLEMENTATION:
───────────────────────────────
Library: SlowAPI (FastAPI-compatible)
Storage: In-memory (default for MVP)
Key function: client IP address (X-Forwarded-For aware)

Important: X-Forwarded-For awareness
├── Behind Nginx reverse proxy: client IP is in X-Forwarded-For
├── Direct access: use request.client.host
└── SlowAPI configured to extract real IP from forwarded headers
    Never trust X-Forwarded-For from untrusted sources (only from Nginx)


RATE LIMITS BY ENDPOINT:
─────────────────────────

CRITICAL SECURITY ENDPOINTS:
├── POST /api/v1/auth/login
│   Limit: 5 requests/minute per IP
│   Reason: Brute force protection for credential stuffing
│   On limit: HTTP 429 + "Too many login attempts. Try again in 60 seconds."
│
├── POST /api/v1/auth/register
│   Limit: 10 requests/minute per IP
│   Reason: Prevent mass account creation
│   On limit: HTTP 429
│
└── POST /api/v1/auth/refresh
    Limit: 20 requests/minute per IP
    Reason: Prevent refresh token scanning
    On limit: HTTP 429

CERTIFICATE OPERATIONS:
├── POST /api/v1/certificates/upload
│   Limit: 10 requests/minute per IP
│   Reason: Prevent storage exhaustion + hash flooding
│   On limit: HTTP 429
│
└── POST /api/v1/certificates/*/revoke
    Limit: 5 requests/minute per IP
    Reason: Prevent mass revocation attempts
    On limit: HTTP 429

VERIFICATION ENDPOINTS:
├── POST /api/v1/verify/upload
│   Limit: 10 requests/minute per IP
│   Reason: Blockchain query rate + server resource protection
│   On limit: HTTP 429
│
└── GET /api/v1/verify/qr/{token}
    Limit: 30 requests/minute per IP
    Reason: Public endpoint — more permissive but protected
    On limit: HTTP 429

GENERAL API:
└── All other endpoints: 100 requests/minute per IP
    Reason: General abuse prevention
    On limit: HTTP 429


RATE LIMIT RESPONSE FORMAT:
────────────────────────────
HTTP 429 Too Many Requests
Headers:
├── X-RateLimit-Limit: 5
├── X-RateLimit-Remaining: 0
├── X-RateLimit-Reset: {unix timestamp when limit resets}
└── Retry-After: 60

Body: { "error": { "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Try again in 60 seconds." } }


RATE LIMITING BYPASS SCENARIOS:
─────────────────────────────────
Scenario: Attacker uses distributed IPs (residential proxy network)
Defense: Per-account lockout (5 attempts → lock, regardless of IP diversity)
Limitation: Cannot prevent distributed attacks on unregistered email enumeration
Post-MVP mitigation: CAPTCHA on login endpoint after N failures

Scenario: Rate limit state lost on server restart
Defense: In-memory rate limits reset; lockout state is in PostgreSQL (persistent)
Impact: Brief window of rate limit bypass after restart
Post-MVP mitigation: Redis-backed rate limit store

Scenario: Load balanced servers with separate rate limit states
Impact: N servers = N × rate limit effective
Post-MVP mitigation: Shared Redis rate limit store across instances
```

---

# SECTION 27: ABUSE PREVENTION STRATEGY

## 27.1 Abuse Prevention Architecture

```
ABUSE PREVENTION STRATEGY — COMPLETE
═══════════════════════════════════════

ABUSE SCENARIO CATALOG:
─────────────────────────

ABUSE 1: Certificate Spam (issuing thousands of fake certificates)
Attack: Authorized university admin issues massive volume of certificates
Indication: Abnormal volume from one university_id
Controls:
├── Rate limiting: 10/min per IP on /certificates/upload
├── Each cert requires: MetaMask signing (user must approve each TX)
│   User cannot automate MetaMask approvals (user interaction required)
└── Monitoring: alert if certificate count exceeds expected daily volume

ABUSE 2: Verification Flooding (exhausting blockchain quota)
Attack: Rapid file uploads to POST /verify/upload
Controls:
├── Rate limiting: 10/min per IP
└── File size limit: 50MB maximum per upload

ABUSE 3: QR Token Enumeration
Attack: Sequential scanning of /verify/qr/{token}
Controls:
├── Token keyspace: 2^384 (brute force impossible)
└── Rate limit: 30/min per IP

ABUSE 4: Storage Exhaustion
Attack: Upload maximum-size files rapidly to fill disk
Controls:
├── Rate limiting: 10/min × 50MB = 500MB max per minute per IP
├── File size limit: 10MB (certificate upload), 50MB (verification)
└── Disk monitoring: alert at 80% usage (operational control)

ABUSE 5: Account Farming
Attack: Create many fake employer/student accounts
Controls:
├── Rate limiting: 10 registrations/min per IP
└── Email verification requirement (post-MVP)

ABUSE 6: Verification History Scraping
Attack: Employer scrapes all verification results to build credential database
Controls:
├── Each employer sees only their own verifications
└── Ownership check on GET /employer/verifications

ABUSE 7: Blockchain Transaction Flooding
Attack: Submit many failed transactions to exhaust university gas
Controls:
├── MetaMask requires user approval per TX (manual step)
└── Account deauthorization (post-compromise response)

SUSPICIOUS ACTIVITY DETECTION:
────────────────────────────────
Patterns to detect and log (post-MVP automated alerting):
├── Same IP: > 20 failed login attempts in 5 minutes
├── Same user: > 3 failed login attempts to different accounts
├── Verification spike: > 100 verifications in 1 hour from one IP
├── Certificate spike: > 50 certificates in 1 hour from one university
└── Revocation spike: > 10 revocations in 1 hour from one university

These patterns are logged as SUSPICIOUS_ACTIVITY events.
MVP: logged and manually reviewed.
Post-MVP: automated alerts + temporary IP blocking.
```

---

# SECTION 28: SECURE STORAGE STRATEGY

## 28.1 Data Storage Security

```
SECURE STORAGE STRATEGY — COMPLETE
═════════════════════════════════════

STORAGE CATEGORY ANALYSIS:
────────────────────────────

CATEGORY 1: Database Storage (PostgreSQL)
What: User accounts, certificates, verification logs, tokens (hashed)
Security:
├── Connection: SSL/TLS encrypted
├── Access: credential_app_user (minimal privilege)
├── Sensitive fields: hashed (passwords, tokens)
└── Immutability: DB triggers on sensitive tables

CATEGORY 2: File Storage (Local Filesystem)
What: Certificate PDFs
Security:
├── Location: /uploads/ (outside Nginx web root)
├── Filenames: UUID-based (no original filename on disk)
├── Permissions: 640 (owner rw, group r, other none)
├── Access: via API only (authenticated + ownership check)
└── Path traversal: realpath validation

CATEGORY 3: Blockchain Storage (Ethereum)
What: SHA-256 hashes, wallet addresses, timestamps, status
Security:
├── Immutable: cannot be changed by any party
├── Public: visible to everyone (no PII stored)
└── Permanent: records survive platform shutdown

CATEGORY 4: Browser Storage (Frontend)
What: Access token (React memory only)
Security:
├── Memory: cleared on page close/refresh
├── Not accessible: by other tabs, by extensions (in most cases)
└── Restored: via httpOnly cookie → silent refresh

WHAT IS NEVER STORED WHERE:
─────────────────────────────
passwords → never in plaintext anywhere
private keys → never on server (MetaMask only, user device)
JWT access token → never in localStorage or sessionStorage
raw refresh token → never in DB (only SHA-256 hash)
raw reset token → never in DB (only SHA-256 hash)
PDFs → never on blockchain
student PII → never on blockchain
wallet private keys → never in code or config files
API secrets → never committed to Git

BROWSER STORAGE POLICY:
────────────────────────
localStorage: NOT USED (XSS accessible)
sessionStorage: NOT USED (XSS accessible)
Regular cookies: NOT USED for tokens
httpOnly cookies: Used for refresh token ONLY
React state/memory: Used for access token

This policy is non-negotiable.
Any deviation must be reviewed and approved.
```

---

# SECTION 29: SECRETS MANAGEMENT STRATEGY

## 29.1 Secrets Lifecycle Architecture

```
SECRETS MANAGEMENT STRATEGY — COMPLETE
════════════════════════════════════════

SECRETS INVENTORY:
───────────────────
Backend secrets (in .env file, never in code):
├── DATABASE_URL          → PostgreSQL connection string + credentials
├── JWT_PRIVATE_KEY       → RS256 private key (PEM, RSA 2048-bit)
├── JWT_PUBLIC_KEY        → RS256 public key (PEM)
├── BLOCKCHAIN_RPC_URL    → Infura/Alchemy URL with API key
├── CONTRACT_ADDRESS      → Deployed contract address
├── NETWORK_CHAIN_ID      → Ethereum chain ID
├── UPLOAD_ROOT           → Base path for file storage
└── FRONTEND_URL          → Allowed CORS origin

Blockchain secrets:
├── DEPLOYER_PRIVATE_KEY  → Ethereum wallet for contract deployment (hardhat .env)
└── SEPOLIA_RPC_URL        → Alchemy/Infura endpoint (hardhat .env)

Frontend "secrets" (not actually secret — included in bundle):
├── VITE_API_URL          → Backend API URL (public by nature)
└── VITE_CONTRACT_ADDRESS → Contract address (public by nature)

Note: Frontend "environment variables" are compiled into the JS bundle.
They are visible to anyone who inspects the source code.
NEVER put backend secrets or private keys in VITE_ variables.


SECRET STORAGE RULES:
──────────────────────
Development:
├── .env file (local only, gitignored)
└── Never committed to Git

Staging/Production:
├── Environment variables injected at runtime
├── NOT from .env file (too easy to accidentally commit)
└── Managed by: server environment, process manager (PM2), or CI/CD pipeline

Repository:
├── .gitignore: .env, *.pem, *.key (committed)
├── .env.example: template with placeholder values (committed)
└── Git history: scan for accidentally committed secrets (secret scanner)

Pre-commit hook (git hooks):
└── Scan for patterns: password=, secret=, private_key=, DATABASE_URL=
    Reject commit if pattern found in staged files
    Tool: detect-secrets (pip) or gitleaks


JWT KEY PAIR MANAGEMENT:
─────────────────────────
Initial generation:
├── openssl genrsa -out private_key.pem 2048
├── openssl rsa -in private_key.pem -pubout -out public_key.pem
└── Convert PEM to environment variable format (escape newlines)

Key rotation procedure:
├── Step 1: Generate new key pair
├── Step 2: Deploy new private key alongside old public key
│   (Both public keys accepted briefly during transition)
├── Step 3: Issue new tokens with new private key
├── Step 4: Wait for all old tokens to expire (15 minutes)
└── Step 5: Remove old public key from accepted keys

Why rotation matters:
├── If private key is compromised: attacker can forge JWTs indefinitely
├── Rotation limits the exposure window
└── Rotation should be done whenever a team member leaves


SECRET SCANNING:
─────────────────
Before every commit:
└── Run: detect-secrets scan (or equivalent) to detect credentials in staged files

Continuous (post-MVP):
└── GitHub Advanced Security secret scanning (free for public repos)
    Or: GitLab secret detection
```

---

# SECTION 30: DEPENDENCY SECURITY STRATEGY

## 30.1 Supply Chain Security

```
DEPENDENCY SECURITY STRATEGY — COMPLETE
═════════════════════════════════════════

PYTHON DEPENDENCY SECURITY:
────────────────────────────
requirements.txt: pinned exact versions
├── Format: package==1.2.3 (not package>=1.2.3)
├── Why pinned: prevents automatic uptake of vulnerable new versions
└── Trade-off: requires manual updates (acceptable for MVP)

Vulnerability scanning:
├── pip audit (built-in PyPI advisory database check)
│   Command: pip audit --requirement requirements.txt
│   Run: before every deployment
└── Fail: if any high-severity vulnerability found

Dependency minimization:
└── Only install packages that are actually used
    Each extra dependency is an attack surface.
    Current backend dependencies: reviewed in backend architecture.
    No convenience libraries (e.g., requests when httpx is available).

JAVASCRIPT DEPENDENCY SECURITY:
─────────────────────────────────
package-lock.json: committed to repository
├── Contains: exact resolved versions + integrity hashes
└── Prevents: dependency resolution to different (possibly compromised) versions

npm audit:
├── Command: npm audit --audit-level=high
├── Run: before every deployment
└── Fail: if high-severity vulnerability found

Subresource integrity (SRI):
├── External CDN resources: NOT used (per frontend architecture)
└── Why relevant: if external JS were used, SRI hash would be required

SOLIDITY DEPENDENCY SECURITY:
────────────────────────────────
OpenZeppelin: NOT used in MVP smart contract
├── Decision: custom implementation for MVP simplicity
├── Contract is small enough for single-file audit
└── Post-MVP: consider OpenZeppelin AccessControl for role management

Solidity version pinning:
└── pragma solidity ^0.8.19 (pinned, not floating)
    Floating pragma (>=0.8.0) could compile with vulnerable compiler versions

Hardhat security:
├── hardhat + hardhat-toolbox: pinned in package.json
└── npm audit: covers Hardhat dependencies


DEPENDENCY UPDATE POLICY:
───────────────────────────
Security patches: Apply within 7 days of discovery
Minor updates: Apply monthly (review changelog)
Major updates: Evaluate on next sprint (breaking changes risk)

Process:
1. pip audit / npm audit identifies vulnerability
2. Upgrade specific package: pip install package==new_version
3. Run full test suite
4. If tests pass: update requirements.txt/package-lock.json
5. Deploy to staging first
6. Monitor for regressions
7. Deploy to production
```

---

# SECTION 31: FRONTEND ROUTE PROTECTION STRATEGY

## 31.1 Client-Side Route Security

```
FRONTEND ROUTE PROTECTION STRATEGY — COMPLETE
═══════════════════════════════════════════════

ROUTE PROTECTION PHILOSOPHY:
──────────────────────────────
Frontend route protection is UX security (prevents accidental access)
Backend API protection is true security (prevents unauthorized data access)

Both are required:
├── Frontend only: API is unprotected → actual data exposed
├── Backend only: UX is confusing → users land on wrong pages
└── Both: secure + good UX

PrivateRoute Security Logic:
─────────────────────────────
Input: requiredRole (string), children (React component)
Process:

Step 1: Check isLoading (auth state being determined)
→ Show: full-screen loading spinner
→ Why: prevents false redirect to /auth/login during session restoration
   (without this, page refresh always bounces to login before cookie refresh completes)

Step 2: Check isAuthenticated == false
→ Store: window.sessionStorage.setItem('intended_path', location.pathname)
→ Redirect: to /auth/login
→ After login: read intended_path → navigate there (seamless redirect-back)

Step 3: Check user.role != requiredRole
→ Redirect: to user's own dashboard (not error page)
→ Why: if student accidentally navigates to /university/issue,
       redirect them to /student/dashboard (not an error)
   This is UX-friendly while still preventing wrong-role access

Step 4: All checks pass → render children

ROLE-TO-ROUTE ISOLATION:
──────────────────────────
UNIVERSITY_ADMIN routes: /university/*
├── These paths do not exist in student/employer context
├── Even if a student types /university/issue → Step 3 redirect
└── No university portal component is ever rendered for non-university users

STUDENT routes: /student/*
└── Same isolation — other roles redirected to own dashboard

EMPLOYER routes: /employer/*
└── Same isolation

Public route: /verify/:token
├── No authentication required
├── No PrivateRoute wrapper
└── Accessible by anyone with a valid QR token


ROUTE PARAMETER SECURITY:
───────────────────────────
Certificate IDs in URLs:
├── Format: UUID v4 (non-guessable)
├── Frontend extracts: useParams() → certificateId
├── Frontend uses: to fetch data via API
└── Backend validates: UUID format + ownership before returning data

QR tokens in URLs:
├── Format: 64-char URL-safe base64 (non-guessable)
├── No ownership required: public endpoint
└── Rate limited: 30/min per IP

URL parameter tampering:
├── User types: /student/credentials/{other-student-uuid}
├── Frontend: sends API request with that UUID
├── Backend: finds cert, checks ownership → 403
└── Frontend: shows "Access denied" or "Credential not found"
    (Ownership protection is backend-enforced; frontend is secondary)
```

---

# SECTION 32: VERIFICATION RESULT INTEGRITY STRATEGY

## 32.1 Verification Result Security

```
VERIFICATION RESULT INTEGRITY STRATEGY — COMPLETE
══════════════════════════════════════════════════

THE VERIFICATION RESULT MUST BE TRUSTWORTHY.
This is the platform's primary output. If it can be falsified, the platform has no value.

RESULT INTEGRITY PIPELINE:
────────────────────────────

Source of truth determination:
├── AUTHENTIC source: blockchain.verifyCertificate() returns (true, ACTIVE)
├── TAMPERED source: blockchain.verifyCertificate() returns (false, ACTIVE)
├── REVOKED source: blockchain.verifyCertificate() returns (false/true, REVOKED)
└── NOT_FOUND source: certificate.exists == false on chain

The result is COMPUTED from blockchain state, not retrieved from DB.
No application code can override the blockchain result.

ATTACK: Can the result be manipulated?
──────────────────────────────────────
Attack: Employer modifies verification request in transit
Defense: HTTPS protects transit; server recomputes hash from submitted file

Attack: Backend returns wrong result
Defense: Verification result is logged (verification_logs is immutable)
         Any pattern of wrong results would be detectable in audit logs

Attack: Database manipulation changes result
Defense: Backend doesn't use DB hash for comparison (uses blockchain only)

Attack: Blockchain RPC returns wrong data
Defense: 
├── HTTPS to RPC endpoint (transit protected)
├── Ethereum cryptographic signatures on all data
└── RPC data integrity: blockchain data is signed by consensus
    A tampered RPC response would have invalid Ethereum signatures

Attack: Attacker serves a fake verification page
Defense:
├── Platform URL is HTTPS (certificate validates domain ownership)
├── CSP prevents injection of fake content
└── QR codes encode the correct platform URL (not user-supplied)


RESULT DISPLAY INTEGRITY:
───────────────────────────
VerificationResultPage receives: VerificationResult object
├── result: "AUTHENTIC" | "TAMPERED" | "REVOKED" | "NOT_FOUND"
├── blockchain_proof: { tx_hash, block_number, issuer_address, stored_at }
└── tamper_evidence: { submitted_hash, stored_hash, match }

The frontend renders this data — it cannot fabricate it.
If an attacker injects XSS to modify the DOM to show green "AUTHENTIC"
for a tampered cert, the injected page would have no Etherscan link
(that would require fabricating a real TX hash), making the fraud
detectable to careful verifiers.

The Etherscan link is the ultimate user-verifiable proof:
Users can click the TX hash → Etherscan → see the actual stored hash
and compare to the submitted certificate's hash independently.
This is the "trust but verify" mechanism available to all users.


PREVENTING RESULT SPOOFING:
────────────────────────────
What prevents an attacker from claiming a certificate is AUTHENTIC?
├── They cannot create a blockchain record (not an authorized issuer)
├── They cannot forge an Etherscan TX link (TX would not exist on Ethereum)
└── Even if they forge the UI, the verification_logs records what actually happened
    If the verifier logs the verification, the log shows the real result

What prevents a platform operator from claiming TAMPERED on a good cert?
├── The blockchain result is deterministic and publicly verifiable
├── Any party can call verifyCertificate() on the contract directly
└── The immutable verification_logs preserves what was actually returned
```

---

# SECTION 33: SECURITY TESTING STRATEGY

## 33.1 Security Testing Architecture

```
SECURITY TESTING STRATEGY — COMPLETE
═══════════════════════════════════════

SECURITY TESTING PHILOSOPHY:
──────────────────────────────
Security testing is not separate from regular testing —
security test cases are integrated into the test suite.
Every security control has a corresponding test that
verifies it works and a test that attempts to bypass it.

SECURITY TEST CATEGORIES:
───────────────────────────

CATEGORY 1: Authentication Tests
├── Correct credentials → access granted
├── Wrong password → 401 (not 200)
├── Wrong email → 401 (same message as wrong password)
├── Expired JWT → 401
├── Tampered JWT payload → 401 (signature invalid)
├── HS256 JWT submitted to RS256 endpoint → 401 (algorithm rejected)
├── JWT with "none" algorithm → 401
├── After 5 failed attempts → account locked (423)
├── Locked account → cannot login even with correct password
└── Refresh with revoked token → 401

CATEGORY 2: Authorization Tests
├── Student role → /university/issue → 403
├── Employer role → /certificates/ → 403
├── University admin → /student/credentials → 403
├── Student A → /student/credentials/{Student B cert ID} → 403
├── University A admin → revoke University B certificate → 403
├── Unauthenticated → any protected endpoint → 401

CATEGORY 3: Input Validation Tests
├── Invalid email format → 422
├── Password < 8 chars → 422
├── SHA-256 hash not 64 chars → 422
├── Wallet address wrong format → 422
├── TX hash wrong format → 422
├── Empty string for required field → 422
├── Integer overflow attempt in page parameter → 422
└── SQL injection in search parameter → no SQL error (ORM protects)

CATEGORY 4: File Upload Security Tests
├── Non-PDF file (script.exe) → 400 (MIME validation)
├── File renamed to .pdf but not PDF → 400 (python-magic detects)
├── Zero-byte file → 400
├── File > 10MB → 400
├── Filename with path traversal (../../etc/passwd) → safe UUID stored
└── Concurrent uploads of same file → second fails with DUPLICATE_CERTIFICATE

CATEGORY 5: Certificate Integrity Tests
├── Verify original PDF → AUTHENTIC
├── Verify modified PDF (1 byte changed) → TAMPERED
├── Verify completely different PDF → TAMPERED or NOT_FOUND
├── Verify revoked certificate → REVOKED
├── Verify non-existent certificate UID → NOT_FOUND

CATEGORY 6: Rate Limiting Tests
├── 6th login attempt in 1 minute → 429
├── Verify after 11 uploads in 1 minute → 429
└── Rate limit resets after window

CATEGORY 7: Smart Contract Security Tests
├── Non-authorized wallet calls storeCertificate → revert
├── Authorized wallet stores same UID twice → revert CertificateAlreadyExists
├── University A wallet revokes University B cert → revert NotOriginalIssuer
├── Storing bytes32(0) hash → revert InvalidCertificateHash
├── Storing empty UID → revert InvalidCertificateUid
├── Owner calls storeCertificate (without being authorized) → revert
└── Double revocation attempt → revert CertificateAlreadyRevoked


TOOLS FOR SECURITY TESTING:
─────────────────────────────
Backend:
├── pytest + httpx: integration tests (all security test cases above)
├── pip audit: dependency vulnerability scanning
└── bandit: Python static analysis for security issues
    bandit -r backend/ (detects: hardcoded passwords, SQL injection, eval)

Frontend:
├── axe-core (jest-axe): accessibility + basic DOM security
└── npm audit: dependency vulnerability scanning

Smart Contract:
├── Hardhat tests: all smart contract security tests
└── slither (optional): static analysis for Solidity
    Detects: reentrancy, integer overflow, access control issues

Manual:
├── OWASP Top 10 checklist review (quarterly)
├── Auth bypass attempts (manual)
└── JWT manipulation (manual: jwt.io to decode + tamper)
```

---

# SECTION 34: SECURITY MONITORING STRATEGY

## 34.1 Monitoring Architecture

```
SECURITY MONITORING STRATEGY — COMPLETE
═════════════════════════════════════════

MVP MONITORING STACK:
──────────────────────
MVP uses: Structured logs + manual review (no SIEM)
Post-MVP: Log aggregation (Datadog, CloudWatch, ELK stack)

WHAT TO MONITOR (AND WHEN TO ALERT):
────────────────────────────────────────

CRITICAL ALERTS (immediate action required):
├── CONTRACT_CROSS_VALIDATION_FAILURE
│   Condition: blockchain_hash != db_hash after confirmation
│   Action: investigate immediately; cert should not be confirmed
│   
├── UNEXPECTED_ISSUER_ADDRESS
│   Condition: TX issuer != expected university wallet
│   Action: front-running suspected; investigate; do not confirm cert
│   
├── MASS_REVOCATION_SPIKE
│   Condition: > 10 revocations from one university in 1 hour
│   Action: contact university; possible wallet compromise
│   
└── REPEATED_HASH_MISMATCH_SAME_CERT
    Condition: same certificate verified as TAMPERED > 5 times
    Action: notify university; tampered document in circulation

HIGH PRIORITY ALERTS (investigate within 1 hour):
├── MULTIPLE_ACCOUNT_LOCKOUTS_SAME_IP
│   Condition: > 5 different accounts locked from same IP in 1 hour
│   Action: possible credential stuffing; block IP
│   
├── AUDIT_LOG_MODIFICATION_ATTEMPT
│   Condition: UPDATE/DELETE attempted on audit_log
│   Action: possible insider threat; investigate immediately
│   
├── RAPID_CERTIFICATE_ISSUANCE
│   Condition: > 100 certificates from one university in 1 day
│   Action: contact university; verify legitimacy
│   
└── BLOCKCHAIN_SERVICE_UNAVAILABLE
    Condition: > 5 consecutive failed RPC calls
    Action: check RPC endpoint; switch to backup RPC

MEDIUM PRIORITY (investigate within 24 hours):
├── VERIFICATION_VOLUME_SPIKE
│   Condition: > 500 verifications in 1 hour from one IP
│   Action: possible competitive intelligence scraping
│   
├── FAILED_AUTH_VOLUME
│   Condition: > 100 failed auth attempts in 1 hour across all IPs
│   Action: review for credential stuffing campaign
│   
└── DEPENDENCY_VULNERABILITY_DISCOVERED
    Condition: pip audit / npm audit returns high severity
    Action: patch within 7 days

LOG MONITORING QUERIES (daily review for MVP):
────────────────────────────────────────────────
Query: Count of TAMPERED verification results (daily)
Purpose: Track fraud patterns; identify compromised certificates

Query: Failed authentication count by IP (daily)
Purpose: Detect credential stuffing campaigns

Query: Revocation count by university (weekly)
Purpose: Anomaly detection

Query: Certificate issuance volume by university (weekly)
Purpose: Validate expected activity

BLOCKCHAIN MONITORING:
───────────────────────
Monitor: IssuerAuthorized/IssuerDeauthorized events
Reason: Unexpected issuer changes indicate platform compromise

Monitor: CertificateRevoked event volume
Reason: Unusual spikes indicate wallet compromise

Monitor: Contract ownership changes (OwnershipTransferred event)
Reason: Platform admin wallet compromise
```

---

# SECTION 35: SECURITY INCIDENT RESPONSE PLAN

## 35.1 Incident Response Architecture

```
SECURITY INCIDENT RESPONSE PLAN — COMPLETE
════════════════════════════════════════════

INCIDENT SEVERITY LEVELS:
───────────────────────────
CRITICAL (respond within 1 hour):
├── Private key compromise (JWT or Ethereum wallet)
├── Database breach (unauthorized access to user/certificate data)
├── Smart contract unauthorized issuance detected
└── Mass certificate revocation (wallet compromise suspected)

HIGH (respond within 4 hours):
├── Active credential stuffing campaign
├── JWT algorithm confusion attack in progress
├── File upload bypass leading to malicious file storage
└── Audit log tampering attempt detected

MEDIUM (respond within 24 hours):
├── Single account compromised
├── Dependency vulnerability discovered (high severity)
└── Unusual verification pattern (possible scraping)

LOW (respond within 1 week):
├── Low-severity dependency vulnerability
└── Failed intrusion attempts (no breach)


INCIDENT RESPONSE PROCEDURES:
───────────────────────────────

PROCEDURE IR-1: JWT Private Key Compromise
──────────────────────────────────────────
Detection: Forged tokens detected; unknown user IDs in JWTs
Immediate:
├── Generate new RS256 key pair
├── Deploy new private key (invalidates all existing tokens)
├── All active users will receive 401 → forced re-login
├── No access tokens valid (15-min TTL ensures fast invalidation)
└── Log: key compromise event with estimated exposure window
Recovery:
└── Monitor for fraudulent actions taken with forged tokens

PROCEDURE IR-2: University Wallet Compromise
─────────────────────────────────────────────
Detection: Unexpected certificates or revocations from university wallet
Immediate:
├── Notify university (immediately)
├── Call: deauthorizeIssuer(compromised_wallet) on contract
│   This prevents future fraudulent issuances
├── Review: all certificates issued in last 24 hours from that wallet
└── Identify: any certificates issued after last legitimate issuance
Recovery:
├── University generates new wallet (new MetaMask address)
├── Call: authorizeIssuer(new_wallet) on contract
├── For fraudulent certificates: cannot auto-revoke (wallet deauthorized)
│   Must individually assess and handle each fraudulent cert
│   Contact employers who may have received fraudulent certs
└── Future: ownerEmergencyRevoke function (post-MVP improvement)

PROCEDURE IR-3: Database Breach
─────────────────────────────────
Detection: Unusual DB queries; unauthorized access logs; data exfil detected
Immediate:
├── Revoke database credentials (change DB password)
├── Force-logout all users (revoke all refresh tokens: set all is_revoked=True)
├── Generate new JWT private key (forces re-login)
└── Assess: what data was accessed (user records, certificate data)
Recovery:
├── Credential breach: all users notified to change passwords
│   Note: passwords are bcrypt hashed; cracking is slow but possible
├── Certificate data: assess which records were exposed
└── Blockchain data: not affected (blockchain is separate from DB)

PROCEDURE IR-4: Platform Owner Account Compromise
──────────────────────────────────────────────────
Detection: Unexpected IssuerAuthorized events on blockchain
Immediate:
├── Transfer contract ownership: transferOwnership(new_secure_wallet)
│   This requires access to the current owner's wallet (MetaMask)
│   If wallet is compromised: race condition — transfer ASAP
├── Audit: all issuer authorization changes in last 24 hours
└── Deauthorize: any unknown issuers added by attacker
Recovery:
└── Review all certificates issued via unauthorized issuer wallets

PROCEDURE IR-5: Mass Data Breach (hypothetical worst case)
────────────────────────────────────────────────────────────
Immediate:
├── Take service offline (maintenance mode)
├── Revoke all authentication tokens
├── Notify: all affected users (legal obligation)
└── Preserve: logs + evidence for forensic investigation
Recovery:
├── Full security audit before restart
├── Patch vulnerability that enabled breach
└── Restore from last clean backup

COMMUNICATION TEMPLATE (for university notification):
───────────────────────────────────────────────────────
Subject: Security Alert — Action Required for Your University Account

We have detected potentially unauthorized activity on your university's
credential issuance account. As a precaution, we have suspended your
issuing capability while we investigate.

Action required:
1. Do not use your current MetaMask wallet for certificate operations
2. Contact us at [security contact] to verify recent activity
3. If your wallet is compromised, you will need to set up a new wallet

Your existing issued certificates remain valid and unaffected.
```

---

# SECTION 36: SECURITY VALIDATION CHECKLIST

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     SECURITY VALIDATION CHECKLIST                            ║
║         Verifying all security requirements are addressed                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════
AUTHENTICATION SECURITY
═══════════════════════════════════════════════════════════════════
☑ Passwords hashed with bcrypt cost factor 12 ✓
☑ RS256 asymmetric JWT signing ✓
☑ Access token 15-minute TTL ✓
☑ Refresh token httpOnly Secure SameSite=Strict ✓
☑ Refresh token stored as SHA-256 hash (not raw) ✓
☑ Token rotation on every refresh ✓
☑ Account lockout after 5 failed attempts ✓
☑ Same error message for wrong email/password ✓
☑ Timing-safe dummy hash for missing users ✓
☑ Session invalidation on password change ✓
☑ Algorithm pinned to RS256 (no algorithm confusion) ✓

═══════════════════════════════════════════════════════════════════
AUTHORIZATION SECURITY
═══════════════════════════════════════════════════════════════════
☑ RBAC enforced on every protected endpoint ✓
☑ Ownership check in service layer ✓
☑ University admin scoped to own university ✓
☑ Student scoped to own certificates ✓
☑ Employer scoped to own verification results ✓
☑ Smart contract: authorized issuer whitelist ✓
☑ Smart contract: owner ≠ issuer separation ✓
☑ Privilege escalation: JWT role not client-supplied ✓

═══════════════════════════════════════════════════════════════════
CERTIFICATE INTEGRITY
═══════════════════════════════════════════════════════════════════
☑ SHA-256 computed from raw binary file bytes ✓
☑ Hash computed server-side (not client-side) ✓
☑ Hash computed before file save ✓
☑ Hash is UNIQUE in database ✓
☑ Hash immutable after CONFIRMED (DB trigger) ✓
☑ Blockchain always queried for verification ✓
☑ DB hash never used as verification source ✓
☑ Two-phase issuance (upload + MetaMask confirm) ✓
☑ TX cross-validation (hash + issuer) ✓
☑ Revocation is permanent one-way transition ✓

═══════════════════════════════════════════════════════════════════
FILE UPLOAD SECURITY
═══════════════════════════════════════════════════════════════════
☑ MIME type validation via python-magic ✓
☑ File size limits enforced ✓
☑ UUID filename (no original filename on disk) ✓
☑ Path traversal prevention (realpath check) ✓
☑ Files stored outside web root ✓
☑ Files served via authenticated API only ✓
☑ File permissions: 640 ✓

═══════════════════════════════════════════════════════════════════
API SECURITY
═══════════════════════════════════════════════════════════════════
☑ HTTPS enforced (Nginx) ✓
☑ HSTS header configured ✓
☑ CORS whitelist (not wildcard with credentials) ✓
☑ Rate limiting on all endpoints ✓
☑ Input validation via Pydantic ✓
☑ SQL injection prevention (ORM parameterization) ✓
☑ No stack traces in API responses ✓
☑ Security headers: X-Content-Type-Options, X-Frame-Options ✓
☑ Swagger UI disabled in production ✓
☑ Debug mode disabled in production ✓

═══════════════════════════════════════════════════════════════════
SMART CONTRACT SECURITY
═══════════════════════════════════════════════════════════════════
☑ Authorized issuer whitelist ✓
☑ Owner cannot issue certificates ✓
☑ One-time write per certificate UID ✓
☑ One-way revocation (terminal state) ✓
☑ Only original issuer can revoke ✓
☑ Zero hash rejected ✓
☑ No external calls (reentrancy impossible) ✓
☑ No tx.origin usage ✓
☑ Solidity 0.8.19 (built-in overflow protection) ✓
☑ Algorithm pinned (Solidity uses secp256k1 natively) ✓

═══════════════════════════════════════════════════════════════════
FRONTEND SECURITY
═══════════════════════════════════════════════════════════════════
☑ JWT in React memory (not localStorage) ✓
☑ No dangerouslySetInnerHTML with user content ✓
☑ External links: rel="noopener noreferrer" ✓
☑ QR URL validation before navigation ✓
☑ Source maps disabled in production ✓
☑ Console.log removed in production ✓
☑ CSP headers configured ✓
☑ MetaMask: no private key access ✓

═══════════════════════════════════════════════════════════════════
DATABASE SECURITY
═══════════════════════════════════════════════════════════════════
☑ Minimal privilege DB user ✓
☑ SSL connection to database ✓
☑ DB immutability triggers on certificate fields ✓
☑ Append-only triggers on audit tables ✓
☑ CHECK constraints for data format validation ✓
☑ Sensitive columns never in API responses ✓

═══════════════════════════════════════════════════════════════════
OPERATIONAL SECURITY
═══════════════════════════════════════════════════════════════════
☑ Secrets in environment variables (not code) ✓
☑ .env gitignored ✓
☑ .env.example committed (template) ✓
☑ Structured security event logging ✓
☑ Immutable audit trail ✓
☑ Rate limiting on sensitive endpoints ✓
☑ Dependency vulnerability scanning ✓
☑ Incident response procedures defined ✓

═══════════════════════════════════════════════════════════════════
FINAL VERDICT: ALL SECURITY REQUIREMENTS ADDRESSED ✓
SECURITY ARCHITECTURE IS COMPLETE AND READY FOR IMPLEMENTATION ✓
═══════════════════════════════════════════════════════════════════
```

---

# SECTION 37: SECURITY READINESS CHECKLIST

```
SECURITY READINESS CHECKLIST
══════════════════════════════

═══════════════════════════════════════
PRE-DEVELOPMENT: SECURITY SETUP
═══════════════════════════════════════
☐ Generate RS256 key pair: openssl genrsa -out private_key.pem 2048
☐ Generate public key: openssl rsa -in private_key.pem -pubout -out public_key.pem
☐ Store keys in .env (never commit)
☐ Create .gitignore: .env, *.pem, *.key, /uploads/
☐ Configure git pre-commit hook for secret detection
☐ Create .env.example with all required variable names

═══════════════════════════════════════
PRE-LAUNCH: BACKEND SECURITY
═══════════════════════════════════════
☐ bcrypt cost 12 benchmarked: verify ~300ms on deployment hardware
☐ JWT algorithm: verify RS256 pinned in decode call
☐ Rate limiting: tested with curl loop (5 rapid POSTs to /auth/login → 6th = 429)
☐ Account lockout: verified (5 wrong passwords → account locked)
☐ File upload: tested with .exe renamed .pdf → rejected
☐ SQL injection: verified ORM parameterization (grep for raw SQL)
☐ Error responses: verified no stack traces in production mode
☐ pip audit: 0 high-severity vulnerabilities
☐ bandit scan: review output for critical issues
☐ DEBUG=False, SHOW_DOCS=False in production .env

═══════════════════════════════════════
PRE-LAUNCH: FRONTEND SECURITY
═══════════════════════════════════════
☐ Source maps: build.sourcemap=false verified in vite.config.js
☐ Console.log removal: verified in production build
☐ localStorage: grep -r "localStorage" src/ → 0 results
☐ sessionStorage: grep -r "sessionStorage" src/ → 0 results
   Exception: 'intended_path' for auth redirect (acceptable)
☐ dangerouslySetInnerHTML: grep -r "dangerouslySetInnerHTML" src/ → 0 results
☐ npm audit: 0 high-severity vulnerabilities

═══════════════════════════════════════
PRE-LAUNCH: DATABASE SECURITY
═══════════════════════════════════════
☐ credential_app_user created with minimal privileges
☐ No SUPERUSER for application
☐ Immutability triggers deployed: test by attempting UPDATE on confirmed cert
☐ Audit triggers deployed: verify audit_log captures changes
☐ SSL connection to database: verify in DATABASE_URL (ssl=require)
☐ Default public access revoked: REVOKE ALL ON ALL TABLES FROM PUBLIC

═══════════════════════════════════════
PRE-LAUNCH: SMART CONTRACT SECURITY
═══════════════════════════════════════
☐ Contract deployed to Sepolia testnet
☐ Contract verified on Etherscan (source visible)
☐ Owner wallet: hardware wallet or well-secured MetaMask
☐ Authorized issuers: verified list matches expected universities
☐ Test: non-authorized wallet → storeCertificate → fails
☐ Test: double store → fails (CertificateAlreadyExists)
☐ Test: cross-university revoke → fails (NotOriginalIssuer)

═══════════════════════════════════════
PRE-LAUNCH: NGINX / INFRASTRUCTURE
═══════════════════════════════════════
☐ HTTPS enforced (HTTP → HTTPS redirect)
☐ TLS 1.2+ only (TLS 1.0/1.1 disabled)
☐ HSTS header: Strict-Transport-Security: max-age=31536000
☐ X-Content-Type-Options: nosniff
☐ X-Frame-Options: DENY
☐ Server header: removed
☐ /uploads/ directory: NOT in Nginx web root
☐ CSP header configured

═══════════════════════════════════════
POST-LAUNCH: ONGOING SECURITY
═══════════════════════════════════════
☐ Weekly: pip audit + npm audit
☐ Daily: review security event logs
☐ Monthly: review rate limit violations
☐ Quarterly: OWASP Top 10 checklist review
☐ Incident response plan: team briefed on procedures
```

---

# SECURITY ARCHITECTURE SUMMARY

```
SECURITY ARCHITECTURE SUMMARY
═══════════════════════════════

Authentication:   RS256 JWT + bcrypt(12) + refresh token rotation
Authorization:    RBAC (3 roles) + ownership checks + blockchain whitelist
Hashing:          SHA-256 (file integrity) + bcrypt (passwords)
Session:          Memory (access) + httpOnly cookie (refresh)
Transport:        TLS 1.2+ + HSTS
Database:         Minimal privilege + immutability triggers + audit log
Blockchain:       Authorized issuer whitelist + one-time write
File Security:    MIME validation + UUID filenames + API-only serving
Input Validation: Pydantic (format) + Service (business) + DB (constraints)
Audit:            Immutable logs + verification_logs + audit_log
Monitoring:       Structured logs + security event catalog
Incident Response: 5 procedures for critical security events

Security layers: 8 (each independent, each additive)
Two-factor trust: JWT (knowledge) + MetaMask (possession)
Blockchain immutability: Absolute tamper evidence
Test coverage: 50+ security-specific test cases
```

---

# ARCHITECTURE COMPLIANCE REPORT

```
ARCHITECTURE COMPLIANCE REPORT
════════════════════════════════

Documents Reviewed:
├── ✓ Architecture Blueprint (architecture.md)
├── ✓ Database Design (database.md)
├── ✓ Smart Contract Architecture (smart-contracts.md)
├── ✓ Backend Architecture (backend.md)
├── ✓ Frontend Architecture (frontend.md)
├── ✓ AI Project Context (ai-context.md)
└── ✓ Project Rules (project-rules.md)

Assumptions Documented: 10 (all honored)
Approved Technology Decisions Overridden: NONE
New Technologies Introduced: NONE
Previous Decisions Modified: NONE

All security controls are implementable with the approved tech stack:
├── bcrypt: passlib[bcrypt] (Python)
├── RS256 JWT: python-jose[cryptography] (Python)
├── MIME validation: python-magic (Python)
├── Rate limiting: slowapi (FastAPI)
├── Smart contract security: Solidity built-ins + custom modifiers
├── Frontend security: React defaults + build config
└── Database security: PostgreSQL native (triggers, constraints)
```

---

# SECURITY RISK ASSESSMENT

```
SECURITY RISK ASSESSMENT — POST-MITIGATION
════════════════════════════════════════════

Risk                            Pre-Mit  Post-Mit  Residual
────────────────────────────────────────────────────────────
Certificate PDF tampering       CRITICAL CRITICAL  NEGLIGIBLE
  (SHA-256 + blockchain = mathematically infeasible)

Unauthorized cert issuance      CRITICAL HIGH      LOW
  (JWT + MetaMask + contract whitelist = 3 barriers)

JWT forgery                     HIGH     HIGH      VERY LOW
  (RS256 asymmetric = no shared secret to steal)

Password brute force            HIGH     HIGH      LOW
  (bcrypt 12 + lockout + rate limit = ~years per account)

SQL injection                   HIGH     HIGH      VERY LOW
  (ORM parameterization = SQL injection structurally impossible)

XSS + token theft               HIGH     HIGH      LOW
  (Memory storage + httpOnly cookie = no localStorage target)

IDOR certificate access         HIGH     MEDIUM    VERY LOW
  (UUID PKs + ownership checks = guessing + authorization)

Smart contract misuse           HIGH     CRITICAL  VERY LOW
  (authorized whitelist + no external calls = narrow attack surface)

Database breach                 MEDIUM   CRITICAL  LOW
  (minimal privilege + encrypted transit = limited blast radius)

File upload malware             HIGH     HIGH      LOW
  (python-magic + API-only serving = malware cannot execute)

Blockchain TX replay            MEDIUM   MEDIUM    NEGLIGIBLE
  (Ethereum nonces + one-time UID write = replay blocked)

Verification fraud              CRITICAL CRITICAL  VERY LOW
  (blockchain truth + immutable logs = fraud is detectable)

Overall Platform Security Level: APPROPRIATE FOR MVP
Post-MVP improvements documented in each section.
```

---

# FINAL VERDICT & SECURITY READINESS STATUS

```
╔══════════════════════════════════════════════════════════════════╗
║                      FINAL VERDICT                               ║
║                                                                  ║
║  STATUS: APPROVED FOR IMPLEMENTATION                             ║
║                                                                  ║
║  This security architecture blueprint:                           ║
║  ├── Addresses all P1 (critical) risks before launch             ║
║  ├── Addresses all P2 (high) risks within MVP scope              ║
║  ├── Mitigates P3 risks with documented post-MVP improvements    ║
║  ├── Uses only approved technology stack controls                ║
║  ├── Is realistic for single-developer MVP implementation        ║
║  ├── Requires no paid enterprise infrastructure                  ║
║  └── Provides layered defense at every attack surface            ║
║                                                                  ║
║  Security controls are:                                          ║
║  ├── Implementable with approved libraries                       ║
║  ├── Testable with the defined test strategy                     ║
║  ├── Auditable via the defined audit trail                       ║
║  └── Recoverable via the incident response procedures            ║
║                                                                  ║
║  SECURITY READINESS STATUS: READY FOR DEVELOPMENT               ║
╚══════════════════════════════════════════════════════════════════╝
```

---

> **This document is the binding security architecture blueprint for the Blockchain-Based Academic Credential Verification Platform MVP. Every security control defined here must be implemented as specified. Any deviation — changing bcrypt cost factor, altering JWT storage location, bypassing blockchain verification, or weakening input validation — requires a formal security review and documented risk acceptance before proceeding.**