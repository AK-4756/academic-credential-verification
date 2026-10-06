# MVP Completion Plan
**Academic Credential Verification Platform**

Produced: 2026-09-30
Basis: Full repository audit + all approved architecture documents

> **IMPORTANT:** This document is derived from **actual repository evidence**, not from
> stale progress-tracker or roadmap documents. Where they conflict, the repository wins.

---

## 1. Current Verified State

| Item | Status | Evidence |
|------|--------|----------|
| Backend — all 12 services | COMPLETE | `backend/services/` — 12 files present |
| Backend — all 8 routers (32 endpoints) | COMPLETE | `backend/routers/` — 9 files present |
| Backend — all 10 repositories | COMPLETE | `backend/repositories/` — 11 files |
| Backend — all 10 ORM models | COMPLETE | `backend/models/` — 11 files |
| Backend — all 11 Pydantic schema files | COMPLETE | `backend/schemas/` — 11 files |
| Backend — all 6 dependencies files | COMPLETE | `backend/dependencies/` — 6 files |
| Backend — 15 Alembic migrations (001–015) | COMPLETE | `backend/alembic/versions/` — 15 files |
| Backend test suite — 180/180 passing | VERIFIED | Last run 2026-09-29, exit code 0 |
| Smart contract — `CertificateRegistry.sol` | COMPILED | `blockchain/artifacts/` — artifacts present |
| Smart contract — all test files written | WRITTEN | 10 test files in `blockchain/test/` |
| Smart contract — 102/102 Hardhat tests passing | CLAIMED | Stated in `docs/ai-context.md`; not re-run in this audit |
| Smart contract — deployment scripts | STUBS | All 7 scripts are comment-only placeholders ("Implementation: Sprint 2") |
| Smart contract — deployed to local Hardhat | NOT DONE | `blockchain/deployments/hardhat-local/` contains only `.gitkeep` |
| Smart contract — deployed to Sepolia | NOT DONE | `blockchain/deployments/sepolia/` contains only `.gitkeep` |
| Backend `CONTRACT_ADDRESS` configured | EMPTY | `.env.development` line 18: `CONTRACT_ADDRESS=` (blank) |
| Backend blockchain connectivity (end-to-end) | NOT TESTED | P10 tests mock blockchain; no real Hardhat calls made |
| Frontend — Vite + React + Tailwind foundation | COMPLETE | `frontend/package.json`, `vite.config.js`, `tailwind.config.js` present |
| Frontend — `App.jsx` | PLACEHOLDER | Renders "App is working" text only |
| Frontend — routing | NOT STARTED | `frontend/src/routes/` is empty |
| Frontend — all pages | NOT STARTED | `frontend/src/pages/` is empty |
| Frontend — all components | NOT STARTED | `frontend/src/components/` is empty |
| Frontend — API client | NOT STARTED | `frontend/src/api/` is empty |
| Frontend — context providers | NOT STARTED | `frontend/src/context/` is empty |
| Frontend — custom hooks | NOT STARTED | `frontend/src/hooks/` is empty |
| ABI distributed to backend | PRESENT | `backend/blockchain/abi/CertificateRegistry.json` present |
| ABI distributed to frontend | NOT DONE | `frontend/blockchain/` directory does not exist |

---

## 2. Completed Work

### P1–P10 Backend — COMPLETE

All backend code was implemented during Sprints 4–5 and tested through P1–P10:

| Component | Files | Tests |
|-----------|-------|-------|
| Core infrastructure (config, security, logging, middleware) | 8 files | Passing |
| Database layer (models, connection, migrations) | 25 files | 31 repo integration tests |
| Repository layer (10 repositories) | 11 files | Passing |
| Pydantic schema layer | 11 files | Passing |
| Service layer (12 services) | 12 files | 109 unit + integration tests |
| API router layer (8 routers, 32 endpoints) | 9 files | 21 auth integration tests |
| Blockchain integration service (read-only) | 3 files | 21 unit tests |

**Total backend tests: 180/180 passing.**

Production defects discovered during testing and fixed:
1. `tx_hash` nullable (migration 014 applied)
2. QR generation nested transaction fixed
3. `student_id` FK wrong reference fixed
4. Revocation reason persistence via `error_message` field
5. `SUBMITTED` added to `transaction_status` enum (migration 015 applied)
6. `Certificate.blockchain_tx_hash` → `_get_store_tx_hash()` helper
7. `initiate_revocation()` guard order corrected

### Sprint 2–3 Smart Contract — COMPLETE

- `CertificateRegistry.sol` — fully implemented (~300 lines)
- `ICertificateRegistry.sol` — interface present
- All test files written (10 files, 102 claimed-passing tests)
- Contract compiled (artifacts in `blockchain/artifacts/`)

---

## 3. Remaining MVP Features

| MVP Feature | Actual State | Remaining Work | Priority |
|-------------|--------------|----------------|----------|
| Backend API (all 32 endpoints) | COMPLETE | None | — |
| JWT auth + RBAC | COMPLETE | None | — |
| Certificate issuance service | COMPLETE | None | — |
| Certificate verification service | COMPLETE | None | — |
| Certificate revocation service | COMPLETE | None | — |
| QR verification service | COMPLETE | None | — |
| Smart contract (compiled) | COMPLETE | Deploy + connect | — |
| Deploy scripts (deploy.js, authorize-issuer.js) | STUBS | Implement both scripts | CRITICAL |
| Local Hardhat deployment | NOT DONE | Run deploy, authorize issuer | CRITICAL |
| Backend CONTRACT_ADDRESS set | EMPTY | Set after deployment | CRITICAL |
| End-to-end blockchain connectivity | NOT TESTED | Deploy → connect → test | CRITICAL |
| Frontend — Vite/React/Tailwind | SCAFFOLD | None (foundation ready) | — |
| Frontend — Axios API client | NOT STARTED | Implement client.js + 7 API modules | HIGH |
| Frontend — AuthContext | NOT STARTED | JWT flow, session restore | HIGH |
| Frontend — Routing + PrivateRoute | NOT STARTED | AppRoutes.jsx + RoleGuard | HIGH |
| Frontend — Login + Register pages | NOT STARTED | LoginPage, RegisterPage | HIGH |
| Frontend — primitive components | NOT STARTED | Button, Input, Modal, etc. | HIGH |
| Frontend — University portal | NOT STARTED | Dashboard, issuance wizard, revocation | HIGH |
| Frontend — Student portal | NOT STARTED | My credentials, download, share | HIGH |
| Frontend — Employer portal | NOT STARTED | Verify by file, QR scan, result display | HIGH |
| Frontend — Public verification page | NOT STARTED | /verify/{token} route, no auth | HIGH |
| MetaMask integration (storeCertificate signing) | NOT STARTED | BlockchainContext, ethers.js TX | HIGH |
| MetaMask integration (revokeCertificate signing) | NOT STARTED | Same as above | HIGH |
| ABI distributed to frontend | NOT DONE | Copy after deploy, create contractABI.js | HIGH |
| QR scanner (Employer — camera) | NOT STARTED | html5-qrcode wrapper component | MEDIUM |
| Verification result UI (4 outcomes) | NOT STARTED | VerificationResultPage | HIGH |
| PDF download (Student) | NOT STARTED | GET /student/credentials/{id}/download | HIGH |
| Sepolia testnet deployment | NOT DONE | After local validated | MEDIUM |
| Etherscan contract verification | NOT DONE | After Sepolia deployment | LOW |
| API tests (tests/api/) | NOT STARTED | FastAPI TestClient endpoint tests | MEDIUM |
| Security tests (tests/security/) | NOT STARTED | RBAC bypass, rate limit, upload | MEDIUM |
| Frontend unit tests | NOT STARTED | Post-MVP or parallel | LOW |
| Production NGINX config | NOT STARTED | Post-demo | LOW |
| bandit / npm audit scan | NOT DONE | Pre-Sepolia | MEDIUM |

---

## 4. Roadmap Audit

### Items from `implementation-roadmap.md` classified by necessity:

| Roadmap Item | Classification | Reason |
|---|---|---|
| Deploy scripts (deploy.js, authorize-issuer.js) | MUST HAVE FOR MVP | Without deployment, backend-blockchain link is broken |
| Local Hardhat deployment | MUST HAVE FOR MVP | Cannot demonstrate end-to-end without it |
| Frontend API client (Axios + interceptors) | MUST HAVE FOR MVP | All portals depend on it |
| Frontend auth flow (login, register, session restore) | MUST HAVE FOR MVP | Entry to all portals |
| Frontend routing + PrivateRoute | MUST HAVE FOR MVP | Structure for all pages |
| Frontend primitive components (11) | MUST HAVE FOR MVP | Used by all portal pages |
| Frontend layout components | MUST HAVE FOR MVP | AuthenticatedLayout, Navbar, Sidebar |
| University portal (issuance wizard + MetaMask) | MUST HAVE FOR MVP | Core demonstration workflow |
| Student portal (view + download + share) | MUST HAVE FOR MVP | Core student workflow |
| Employer portal (upload verify + QR scan + result) | MUST HAVE FOR MVP | Core employer workflow |
| Public verification page (/verify/{token}) | MUST HAVE FOR MVP | Employer/student sharing requires it |
| MetaMask blockchain context | MUST HAVE FOR MVP | Certificate issuance + revocation require it |
| ABI distribution to frontend | MUST HAVE FOR MVP | Prerequisite for MetaMask signing |
| Verification result UI (all 4 outcomes) | MUST HAVE FOR MVP | Core verification demonstration |
| Loading + error + empty states | SHOULD HAVE | Important UX but can be minimal |
| Sepolia testnet deployment | SHOULD HAVE | Demo readiness; needed for final submission |
| API endpoint tests (tests/api/) | SHOULD HAVE | Confidence without full E2E automation |
| Security tests (tests/security/) | SHOULD HAVE | RBAC and upload security validation |
| Cross-browser testing | SHOULD HAVE | Chrome is primary; can defer Firefox/Safari |
| Performance benchmarks | CAN DEFER | Functional correctness is priority |
| Frontend unit tests (Vitest) | CAN DEFER | Backend tests provide most confidence |
| Frontend integration tests (RTL + MSW) | CAN DEFER | Manual E2E covers this adequately |
| Accessibility audit (axe) | NICE TO HAVE | Post-MVP polish |
| CI/CD pipeline | CAN DEFER | Not needed for MVP demo |
| NGINX configuration | CAN DEFER | Demo can use direct uvicorn + Vite |
| Production deployment guide | CAN DEFER | Post-MVP |
| Etherscan contract verification | CAN DEFER | Useful but not blocking demo |
| bandit / pip audit / npm audit | SHOULD HAVE | Run once before Sepolia |
| Gas optimization review | CAN DEFER | Contract is within budget per ai-context |

---

## 5. Critical Path

The shortest dependency chain from current state to a demonstrable MVP:

```
[DONE] Backend API complete (180/180 tests)
[DONE] Smart contract compiled + Hardhat tests claimed 102/102
    |
    v
[P11] Implement deploy.js + authorize-issuer.js scripts
      Deploy to local Hardhat -> set CONTRACT_ADDRESS in .env
      -> Backend now has live blockchain connection
    |
    v
[P11] Implement + run Hardhat->backend integration tests
      -> Proves end-to-end blockchain path works
    |
    +----------------------------------------------+
    v                                              v
[P12] Frontend foundation                    (can parallel: API tests)
      API client, AuthContext, routing,
      PrivateRoute, primitive components,
      layout, login/register pages
    |
    v
[P13] University portal
      Dashboard, issuance wizard (Step1/2/3),
      MetaMask signing, certificate list,
      detail, revocation
    |
    v
[P14] Student + Employer + Public portals
      Student: credentials, download, share
      Employer: file upload verify, QR scan, result
      Public: /verify/{token} (no login)
    |
    v
[P15] API + security tests + E2E validation
      tests/api/ -- all 32 endpoints
      tests/security/ -- RBAC, uploads, rate limiting
      Manual E2E: 5 complete journeys
    |
    v
[P16] Sepolia deployment + final demo readiness
      Deploy to Sepolia, configure backend env,
      bandit/npm audit, production build
```

---

## 6. Dependencies

| Phase | Hard Dependencies |
|-------|------------------|
| P11 — Blockchain deployment | P10 complete (done) |
| P11 — Blockchain integration tests | Deploy scripts implemented, Hardhat running |
| P12 — Frontend foundation | Backend must be running (for API client testing) |
| P13 — University portal | P12 complete; Hardhat deployed (for MetaMask TX) |
| P14 — Student/Employer portals | P13 complete (need issued certificates for testing) |
| P14 — Public verification page | P14 QR/share feature; any stage |
| P15 — API + security tests | All backend endpoints complete (done) |
| P15 — E2E manual tests | P14 complete |
| P16 — Sepolia deployment | P15 complete, Sepolia ETH available |

---

## 7. Parallel Work Opportunities

| Parallel Track A | Parallel Track B |
|-----------------|-----------------|
| P11: Blockchain deployment scripts | P11d: Backend API tests (`tests/api/`) |
| (must finish first) | (backend is already complete — can start anytime) |
| P12: Frontend foundation | P15b: Backend security tests (`tests/security/`) |
| P13: University portal | — |
| P14: Student + Employer portals | — |

**Note:** `tests/api/` and `tests/security/` can be written **now** using `httpx.AsyncClient`
against the real FastAPI app. These do not depend on frontend or blockchain deployment.
They can be written in parallel with P11 (blockchain deployment work).

---

## 8. Frontend Gap Analysis

### What exists
- Vite 8 + React 19 + Tailwind 3.4 — installed, configured
- `tailwind.config.js` — semantic color tokens defined (primary, success, danger, warning, neutral, blockchain)
- `vite.config.js` — `@/` alias configured, production drops console/debugger
- `index.html` — Inter font preconnect, meta viewport
- `src/main.jsx` — ReactDOM mount
- `src/App.jsx` — Placeholder only
- `src/index.css` — exists
- All `src/` subdirectories created but **empty**: `api/`, `blockchain/`, `components/`, `context/`, `hooks/`, `pages/`, `routes/`, `tests/`, `utils/`

### API Layer (`src/api/`) — 8 files needed
- `client.js` — Axios instance, JWT interceptor, 401→refresh retry, withCredentials
- `auth.api.js`, `certificate.api.js`, `student.api.js`, `verification.api.js`
- `employer.api.js`, `qr.api.js`, `log.api.js`

### Blockchain Layer (`frontend/blockchain/`) — 2 files needed
- `contractABI.js` — exported from `blockchain/artifacts/` after deploy
- `contractAddress.js` — generated by `deploy.js` with chain ID mapping

### Context Providers (`src/context/`) — 3 files needed
- `NotificationContext.jsx` — toast notifications
- `AuthContext.jsx` — JWT state, login/logout, session restoration from cookie
- `BlockchainContext.jsx` — MetaMask connection, chainId, account

### Custom Hooks (`src/hooks/`) — 8 files needed
- `useAuth`, `useAuthorization`, `useMetaMask`, `useTransaction`
- `useNotification`, `usePagination`, `useClipboard` + others

### Routing (`src/routes/`) — 2 files needed
- `AppRoutes.jsx` — all 23 routes with lazy loading
- `PrivateRoute.jsx` — isLoading → spinner, !authenticated → /auth/login, wrong role → redirect

### Primitive Components (`src/components/shared/ui/`) — 11 files needed
- `Button`, `Input`, `Select`, `Textarea`, `Badge`, `Spinner`, `Alert`, `Modal`, `Tooltip`, `Avatar`, `Divider`

### Layout Components (`src/components/layout/`) — 5 files needed
- `PublicLayout`, `AuthenticatedLayout`, `Navbar`, `Sidebar`, `PageHeader`

### Composite/Feature Components — ~15 files needed
- `HashDisplay`, `BlockchainProof`, `FileUploadZone`, `CertificateTable`
- `WalletConnector`, `TransactionStatus`, `IssuanceStepper`
- `VerificationResultCard`, `QRScanner`, `QRDisplay`, `SharePanel`
- `CredentialCard`, `CertificateDisplay` + others

### Pages (`src/pages/`) — 17 pages needed

| Page | Portal | Auth Required |
|------|--------|---------------|
| `LoginPage` | Auth | No |
| `RegisterPage` | Auth | No |
| `UniversityDashboard` | University | UNIVERSITY_ADMIN |
| `IssueCertificatePage` | University | UNIVERSITY_ADMIN |
| `CertificateListPage` | University | UNIVERSITY_ADMIN |
| `CertificateDetailPage` | University | UNIVERSITY_ADMIN |
| `RevokeCertificatePage` | University | UNIVERSITY_ADMIN |
| `StudentDashboard` | Student | STUDENT |
| `MyCredentialsPage` | Student | STUDENT |
| `CredentialDetailPage` | Student | STUDENT |
| `ShareCredentialPage` | Student | STUDENT |
| `EmployerDashboard` | Employer | EMPLOYER |
| `VerifyCertificatePage` | Employer | EMPLOYER |
| `VerificationResultPage` | Employer | EMPLOYER |
| `QRScanPage` | Employer | EMPLOYER |
| `VerificationHistoryPage` | Employer | EMPLOYER |
| `PublicVerificationPage` | Public | None |

### Blockchain calls that stay backend-side

Per architecture: **all blockchain WRITES go through MetaMask on the frontend**.
The backend is read-only from blockchain.

| Operation | Who does it |
|-----------|-------------|
| `storeCertificate()` | MetaMask (frontend) signs, sends |
| `revokeCertificate()` | MetaMask (frontend) signs, sends |
| `verifyCertificate()` | Backend (eth_call, read-only, free) |
| `getCertificateRecord()` | Backend (eth_call, read-only, free) |
| `isAuthorizedIssuer()` | Backend (eth_call) |

Frontend only needs: ethers.js (already installed) + ABI + contract address to call `storeCertificate` and `revokeCertificate` through MetaMask.

### Minimum UI for MVP demo

The MVP does NOT require:
- Batch CSV upload modal
- Loading skeletons (simple text "Loading..." acceptable)
- Advanced empty state illustrations
- Dark mode
- Accessibility audit
- Cross-browser beyond Chrome
- Verification history pagination

The MVP DOES require:
- Working login/register for all 3 roles
- Full issuance wizard (3 steps, MetaMask)
- Certificate list + basic detail view
- Revocation flow (MetaMask)
- Student credential view + PDF download + share QR
- Employer upload verification + result (all 4 outcomes)
- Employer QR scan → result
- Public /verify/{token} page
- Basic error states (try/catch → error message)

---

## 9. Blockchain Deployment Gap Analysis

### Current state (evidence-based)

| Item | State | Evidence |
|------|-------|----------|
| Contract source (`CertificateRegistry.sol`) | Complete | 300 lines, fully implemented |
| Contract compiled | Done | `blockchain/artifacts/` present |
| Contract ABI (backend) | Present | `backend/blockchain/abi/CertificateRegistry.json` |
| Contract ABI (frontend) | Missing | `frontend/blockchain/` does not exist |
| `deploy.js` | STUB | File is comment-only placeholder |
| `authorize-issuer.js` | STUB | File is comment-only placeholder |
| `check-certificate.js` | STUB | File is comment-only placeholder |
| `transfer-ownership.js` | STUB | File is comment-only placeholder |
| `deauthorize-issuer.js` | STUB | File is comment-only placeholder |
| `abi-config.js` | Implemented | Path constants present |
| `address-config.js` | Implemented | Template function present |
| Deployed to local Hardhat | Not done | `hardhat-local/` contains only `.gitkeep` |
| Deployed to Sepolia | Not done | `sepolia/` contains only `.gitkeep` |
| `CONTRACT_ADDRESS` in backend `.env` | EMPTY | `.env.development` line 18: blank |
| `VITE_CONTRACT_ADDRESS` in frontend `.env` | Not set | Not confirmed in `frontend/.env.development` |
| Backend blockchain service tested end-to-end | Not done | P10 tests mock blockchain_service |
| University wallet authorized on chain | Not done | Cannot be done without deployment |

### Exact remaining blockchain work

**Step 1 — Implement `blockchain/scripts/deploy.js`**
- Deploy `CertificateRegistry` contract
- Wait for transaction receipt
- Save deployment record to `deployments/hardhat-local/CertificateRegistry.json`
- Copy ABI to `backend/blockchain/abi/CertificateRegistry.json`
- Generate `frontend/blockchain/contractABI.js` (JS export)
- Generate `frontend/blockchain/contractAddress.js` (chain-ID map)
- Log contract address

**Step 2 — Implement `blockchain/scripts/authorize-issuer.js`**
- Load deployment record to get contract address
- Connect as owner (Hardhat account #0)
- Call `authorizeIssuer(ISSUER_ADDRESS)` with university test wallet
- Verify via `isAuthorizedIssuer()` returns True

**Step 3 — Run local deployment**
```bash
# Terminal 1
cd blockchain && npx hardhat node

# Terminal 2
npx hardhat run scripts/deploy.js --network localhost
ISSUER_ADDRESS=0x... npx hardhat run scripts/authorize-issuer.js --network localhost
```

**Step 4 — Configure backend**
- Set `CONTRACT_ADDRESS=<deployed address>` in `backend/.env.development`

**Step 5 — Configure frontend**
- Set `VITE_CONTRACT_ADDRESS=<deployed address>` in `frontend/.env.development`

**Step 6 — Verify connection**
- Run backend `is_authorized_issuer()` against deployed contract
- Confirm `blockchain_service.get_certificate_count()` returns 0

**Step 7 — Sepolia (after local MVP validated)**
- Get Sepolia ETH from faucets (do this early — request in parallel with P12/P13)
- Set `SEPOLIA_RPC_URL` and `DEPLOYER_PRIVATE_KEY` in `blockchain/.env`
- Run `npx hardhat run scripts/deploy.js --network sepolia`
- Configure backend + frontend `.env` for Sepolia

---

## 10. Remaining Testing Strategy

### Currently passing: 180 backend tests (P1–P10)

### REQUIRED BEFORE MVP DEMO

| Test Type | Files | Scope | Estimated Count |
|-----------|-------|-------|-----------------|
| Blockchain integration tests | `tests/integration/test_blockchain_integration.py` (new) | Backend → real Hardhat node: store, verify, revoke, authorize | ~15 tests |
| API endpoint tests | `tests/api/` (empty — needs files) | All 32 endpoints via httpx.AsyncClient | ~40 tests |
| Manual E2E journeys | Manual execution | 5 complete user journeys (issuance, verify, tampered, QR, revoke) | 5 workflows |

### RECOMMENDED BEFORE FINAL SUBMISSION

| Test Type | Scope | Notes |
|-----------|-------|-------|
| Backend security tests (`tests/security/`) | RBAC bypass, rate limiting, file upload attacks, JWT algorithm confusion | `tests/security/` dir is currently empty |
| bandit scan | `bandit -r backend/` | Quick, run once |
| npm audit | `npm audit --audit-level=high` in `frontend/` and `blockchain/` | Quick |
| Hardhat coverage report | Re-run `npx hardhat coverage` | Should confirm >95% |

### CAN BE DEFERRED

| Test Type | Reason |
|-----------|--------|
| Frontend unit tests (Vitest) | No frontend components yet; defer to post-P14 |
| Frontend integration tests (RTL + MSW) | Manual E2E covers this adequately for MVP |
| Accessibility audit (axe) | Nice-to-have, not MVP-blocking |
| Performance benchmarks | Functionality before performance |
| Cross-browser testing | Chrome is primary; defer Firefox/Safari |

---

## 11. Tasks We Can Defer

| Task | Why Safe to Defer | Post-MVP? |
|------|------------------|-----------|
| Frontend unit tests (Vitest) | 180 backend tests + manual E2E cover confidence | Yes |
| Frontend integration tests (RTL + MSW) | Manual E2E fills this gap | Yes |
| Accessibility audit | Not required for demo | Yes |
| NGINX configuration | Demo uses direct uvicorn + Vite dev server | Yes |
| Docker / containerization | Architecture explicitly excludes Docker for MVP | Yes |
| Etherscan contract verification | Useful but not demo-blocking | After Sepolia deploy |
| CI/CD pipeline | Not required for single-developer MVP | Yes |
| Batch CSV certificate upload | Advanced university feature | Yes |
| Verification history pagination | Can show all on one page for demo | Yes |
| Advanced loading skeletons | Simple "Loading..." text is acceptable | Yes |
| Empty state illustrations | Functional text-only empty states acceptable | Yes |
| Dark mode | Not in approved spec | Yes |
| Email notifications | Explicitly excluded from MVP in backend.md | Yes |
| MetaMask mobile support | Chrome extension on desktop is primary | Yes |
| Sepolia deployment | SHOULD HAVE but not blocking local demo | After local MVP |

---

## 12. Tasks We Can Remove

These items from the roadmap are no longer needed or are already complete:

| Item | Status | Reason |
|------|--------|--------|
| Sprint 4 Phase 1–10 (backend implementation) | DONE — remove from plan | Completed via P1–P10 |
| Sprint 5 D1–D7 (certificate services) | DONE — remove from plan | Completed early during Sprint 4 |
| Sprint 1 setup (Vite, Hardhat, PostgreSQL init) | DONE — remove from plan | Foundation in place |
| Sprint 2–3 contract development + testing | DONE — remove from plan | Contract complete, tests written |
| "Manual Postman walkthrough" (Sprint 5 D9) | REMOVE | Replaced by 180 automated tests |
| Sprint 3 "production audit" | DONE — remove from plan | Contract audited as part of testing |
| Sprint 11 "full testing sprint" (as originally scoped) | COMPRESS | 180 tests already cover most; need API + security tests only |
| Sprint 12 "security hardening" (full week) | COMPRESS | Most security is built-in; need bandit + audit scan |

---

## 13. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Blockchain deploy scripts need significant implementation — 5 stub files | HIGH | HIGH | Prioritize P11; `abi-config.js` and `address-config.js` are documented reference points |
| MetaMask signing flow complexity — frontend → blockchain → backend confirm | HIGH | HIGH | Test MetaMask TX in isolation before building UI; Hardhat account #0 key is known |
| CORS + httpOnly cookie — Axios withCredentials + FastAPI CORS | HIGH | MEDIUM | Backend already configured for localhost:5173; verify on first frontend test |
| bytes32 hash conversion — Python hex vs Solidity bytes32 | MEDIUM | CRITICAL | Backend unit tests for `_get_store_tx_hash` pass; verify match via Hardhat console |
| Hardhat node state loss on restart | VERY HIGH | LOW | Re-run deploy + authorize scripts after restart; seed data is idempotent |
| MetaMask cannot be automated in E2E tests | CERTAIN | MEDIUM | Manual E2E for MetaMask steps; automate everything else |
| QR scanner camera permissions on desktop | LOW | MEDIUM | Manual URL fallback implemented per architecture |
| Frontend volume — ~65 files from zero | HIGH | HIGH | Prioritize portals in order: university → student → employer |
| Sepolia ETH faucet availability | HIGH | LOW | Request from multiple faucets early; 0.5 ETH is sufficient |
| ABI mismatch after contract redeployment | MEDIUM | HIGH | `deploy.js` will auto-copy ABI; document restart procedure |
| TailwindCSS PurgeCSS removing dynamic status classes | MEDIUM | LOW | Add status colors to `safelist` in `tailwind.config.js` |

---

## 14. AI/Claude Session Optimization

### Complexity and session estimates per phase

| Phase | Deliverable | Complexity | AI Sessions Est. | Model Tier | Notes |
|-------|-------------|-----------|-----------------|------------|-------|
| P11a | Deploy scripts (deploy.js, authorize-issuer.js) | MEDIUM | 1 focused session | Flash | ethers.js deployment; well-documented |
| P11b | Blockchain integration tests | MEDIUM | 1 focused session | Flash | Similar to P10 pattern |
| P11c | API tests (tests/api/) | MEDIUM | 1–2 sessions | Flash | httpx TestClient; 32 endpoints |
| P12 | Frontend foundation | HIGH | 2–3 sessions | Sonnet/Pro | Architectural; JWT interceptors; routing |
| P13 | University portal (issuance wizard + MetaMask) | HIGH | 2–3 sessions | Sonnet/Pro | MetaMask integration is highest risk |
| P14a | Student portal | MEDIUM | 1–2 sessions | Flash/Sonnet | Simpler read-only flows |
| P14b | Employer portal (verify + QR + result) | MEDIUM | 1–2 sessions | Flash/Sonnet | QR scanner has moderate complexity |
| P14c | Public verification page | LOW | 1 session | Flash | Simple read-only page |
| P15 | Security tests + bandit + E2E validation | MEDIUM | 1–2 sessions | Flash/Sonnet | — |
| P16 | Sepolia deployment + final demo readiness | MEDIUM | 1 session | Flash | Script-level work |

**Total estimated AI sessions: 13–20 sessions**

### Optimization strategies

1. **Group related frontend work** — Do not separate Button, Input, Spinner into separate sessions; do all 11 primitives in one session.
2. **Reuse P10 patterns** — Integration tests follow the exact same conftest + fixture pattern already established.
3. **Use Flash for read-heavy research** — Architecture lookup, env config, routine file writing.
4. **Reserve Sonnet/Pro for** — MetaMask frontend integration, complex state management (AuthContext + interceptors), and the issuance wizard (multi-step state machine).
5. **Deploy scripts are not complex** — `deploy.js` follows well-known Hardhat pattern; Flash tier is sufficient.
6. **Batch frontend pages** — Student portal (4 pages) can be one session. Employer portal (5 pages) can be one session.

---

## 15. Recommended Execution Order

```
PHASE   MILESTONE                               PARALLEL OK?
------  --------------------------------------  ----------------
P11a    Blockchain deploy scripts               No (foundation)
P11b    Local deployment + backend connect      No (depends P11a)
P11c    Blockchain integration tests            After P11b
P11d    API endpoint tests (tests/api/)         YES -- parallel to P11a/b
------  --------------------------------------  ----------------
P12     Frontend foundation                     After P11b (needs live backend)
        (API client, auth, routing,
         primitives, layout, login)
------  --------------------------------------  ----------------
P13     University portal                       After P12
        (dashboard, issuance wizard,
         MetaMask, revocation)
------  --------------------------------------  ----------------
P14     Student + Employer + Public portals     After P13
        (student: view/download/share)          (student/employer can parallel)
        (employer: upload/QR/result)
        (public: /verify/{token})
------  --------------------------------------  ----------------
P15     Security tests + bandit + E2E           After P14
        5 manual E2E journeys
------  --------------------------------------  ----------------
P16     Sepolia deployment + demo readiness     After P15
```

---

## 16. Definition of Done

The MVP is **complete and demonstrable** when ALL of the following are true:

### Backend (already achieved)
- [x] 180/180 backend tests passing
- [x] All 32 API endpoints registered
- [x] Auth, issuance, verification, revocation, QR services functional

### Blockchain (P11)
- [ ] `deploy.js` implemented and executes without error
- [ ] Contract deployed to local Hardhat; deployment record saved
- [ ] University test wallet authorized via `authorize-issuer.js`
- [ ] `CONTRACT_ADDRESS` set in backend `.env.development`
- [ ] `backend/blockchain/blockchain_service.py` verified against deployed contract
- [ ] ABI distributed to `frontend/blockchain/`

### Testing (P11c + P15)
- [ ] Blockchain integration tests: all passing against real Hardhat
- [ ] API endpoint tests: all 32 endpoints tested
- [ ] Security tests: RBAC, upload, rate limiting verified
- [ ] 5 manual E2E journeys: all documented and passing

### Frontend (P12–P14)
- [ ] Login/register works for all 3 roles
- [ ] JWT never appears in localStorage
- [ ] University admin: full issuance wizard completes with MetaMask
- [ ] University admin: certificate visible as CONFIRMED
- [ ] University admin: revocation flow works with MetaMask
- [ ] Student: sees certificate, downloads PDF, accesses share page with QR
- [ ] Employer: upload original PDF → AUTHENTIC (green)
- [ ] Employer: upload modified PDF → TAMPERED (red)
- [ ] Employer: upload revoked cert PDF → REVOKED (orange)
- [ ] Employer: QR scan → correct verification result
- [ ] Public: `/verify/{token}` shows result without login
- [ ] No console errors in normal operation

---

## 17. Post-MVP Work

The following items are explicitly deferred to after the MVP demo is complete:

1. **Sepolia mainnet-ready deployment** — Contract verified on Etherscan
2. **Production NGINX configuration** — Security headers, HTTPS, uploads isolation
3. **Frontend unit + integration tests** (Vitest + RTL) — Deferred
4. **Accessibility audit** (axe DevTools) — WCAG 2.1 AA compliance
5. **Email notifications** — Certificate issuance confirmation
6. **Batch CSV certificate upload** — University admin efficiency feature
7. **Performance optimization** — Load testing, DB query optimization
8. **CI/CD pipeline** — GitHub Actions for automated testing
9. **Docker containerization** — For consistent deployment
10. **Advanced MetaMask features** — Wrong network detection, wallet switching

---

## 18. Final Decision Summary

| Decision | Recommended |
|---------|-------------|
| Implement deployment scripts or defer? | IMPLEMENT NOW — critical path blocker |
| Write API tests now or after frontend? | NOW — backend is ready, parallel to P11 |
| Write security tests now or after frontend? | After P15 — E2E proves security; formal tests validate |
| Build frontend testing in parallel with feature work? | DEFER — prioritize working features |
| Deploy to Sepolia before or after frontend? | AFTER local validation (P15); Sepolia is for final submission |
| Compress Sprint 11 (full testing sprint)? | YES — 180 tests already done; need API + security tests only |
| Compress Sprint 12 (security hardening)? | YES — bandit + audit scan is 1 day, not 1 week |
| Do all 12 original sprints? | NO — Sprints 1–6 are complete; effectively at Sprint 7 start |
| Remove frontend unit tests from MVP scope? | YES, defer — does not harm demo capability |

---

## 19. Milestone Plan

| Milestone | Deliverable | Priority | Complexity | Est. AI Sessions | MVP Critical? |
|-----------|-------------|----------|-----------|-----------------|---------------|
| **M-P11a: Blockchain Deployment** ✅ COMPLETE | `deploy.js` + `authorize-issuer.js` implemented; deployed to Hardhat (chain 31337); `CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3` set; ABI in backend + frontend; 6/6 backend connectivity checks passed; 102/102 Hardhat tests passed; 180/180 backend tests no regressions | CRITICAL | MEDIUM | 1 | YES |
| **M-P11b: Blockchain + API Tests** | Blockchain integration tests (real Hardhat); API endpoint tests (`tests/api/`, 32 endpoints) | HIGH | MEDIUM | 2 | YES |
| **M-P12: Frontend Foundation** | `api/client.js` + 7 API modules; `AuthContext` (JWT flow, session restore); `AppRoutes` + `PrivateRoute`; 11 primitive components; layout (Navbar, Sidebar); `LoginPage` + `RegisterPage` | HIGH | HIGH | 2–3 | YES |
| **M-P13: University Portal** | `WalletConnector`, `TransactionStatus`; 3-step issuance wizard; `CertificateListPage`, `CertificateDetailPage`, `RevokeCertificatePage` | HIGH | HIGH | 2–3 | YES |
| **M-P14: Student + Employer + Public Portals** | Student: `MyCredentialsPage`, `CredentialDetailPage`, `ShareCredentialPage`, PDF download; Employer: `VerifyCertificatePage`, `VerificationResultPage` (4 states), `QRScanPage`, `VerificationHistoryPage`; Public: `PublicVerificationPage` | HIGH | MEDIUM | 2–3 | YES |
| **M-P15: Validation + Security** | 5 manual E2E journeys documented; backend security tests; `bandit` scan; `npm audit`; fix any failures | MEDIUM | MEDIUM | 1–2 | YES |
| **M-P16: Sepolia + Demo Readiness** | Contract deployed to Sepolia; backend configured; production frontend build; README updated with demo guide | MEDIUM | MEDIUM | 1 | SHOULD |

**Total MVP-critical milestones remaining: 6 (P11a through P15)**

---

## 20. December Feasibility Assessment

### Classification: **ACHIEVABLE WITH DISCIPLINE**

### Evidence for optimism

- The entire backend (hardest, most architecturally complex part) is **complete and fully tested**. This eliminates the highest-risk work.
- The smart contract is complete, tested, and compiled. Only deployment scripts need implementing.
- The frontend foundation (Vite + Tailwind + package.json) is configured. Zero dependency issues.
- The architecture is exhaustively documented. Every frontend page, component, and API integration point is specified in `docs/frontend.md`. There is no design ambiguity.
- The backend API is live. The frontend has a working API to develop against.
- P10 testing proved the backend service logic is correct for all key scenarios.

### Evidence for caution

- The **frontend is 100% unbuilt**. This is a large workload: 17 pages, ~65 component/hook/context files, MetaMask integration.
- The **blockchain deployment scripts are stubs**. This is a smaller but prerequisite task.
- The MetaMask signing integration is the highest-risk frontend task (frontend → ethers.js → MetaMask → TX hash → backend confirm).
- Available AI session capacity limits the pace.

### Workload estimate

| Milestone | Min Weeks | Max Weeks |
|-----------|-----------|-----------|
| M-P11a (blockchain deploy) | 0.5 | 1 |
| M-P11b (blockchain + API tests) | 0.5 | 1 |
| M-P12 (frontend foundation) | 1 | 2 |
| M-P13 (university portal) | 1 | 2 |
| M-P14 (student + employer + public) | 1.5 | 2.5 |
| M-P15 (validation + security) | 0.5 | 1 |
| M-P16 (Sepolia + demo readiness) | 0.5 | 1 |
| **Total** | **5.5 weeks** | **10.5 weeks** |

With the project at 2026-09-30 and December 2026 deadline, approximately **12 weeks** of runway exist.

**The optimistic estimate (5.5 weeks) is comfortably within the deadline.**
**The pessimistic estimate (10.5 weeks) is still within the deadline with ~1.5 weeks buffer.**

### Conditions for success

1. **Discipline on scope** — Do not add features not in the approved MVP. Every addition compresses the buffer.
2. **Frontend in logical order** — Foundation → University → Student → Employer. Do not build in parallel across portals.
3. **Deploy blockchain early** — M-P11a must be the very next task. Delay here creates a chain delay.
4. **Avoid rework** — The MetaMask integration pattern must be tested in isolation (Hardhat console) before building the full UI around it.
5. **Do not rebuild what's working** — The backend is proven. Do not refactor backend code during frontend work.

### Why not "COMFORTABLY ACHIEVABLE"

The frontend volume (~65 files, MetaMask integration complexity, and the fact that it is entirely from scratch) introduces genuine schedule risk. A single integration issue with MetaMask or the Axios interceptor pattern could consume a week. "Achievable with discipline" accurately captures this.

### Why not "HIGH RISK"

The backend is complete and tested. The architecture is fully documented. The smart contract works. The hardest integration work (blockchain ↔ backend) is designed, implemented, and tested at the service layer. We are building on solid foundations.

---

*End of MVP Completion Plan — 2026-09-30*
