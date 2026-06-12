# AI PROJECT CONTEXT

## Project Name

Blockchain-Based Academic Credential Verification Platform

## Current Project Phase

Implementation Planning

## Project Goal

Build a decentralized academic credential verification platform where:

- Universities issue certificates
- Students manage and view certificates
- Employers verify certificate authenticity
- Certificate hashes are stored on blockchain
- Tampered certificates are detected instantly
- QR-based verification is supported

---

## Approved Technology Stack

Frontend:

- React
- Vite
- TailwindCSS

Backend:

- FastAPI (Python)

Database:

- PostgreSQL

Blockchain:

- Solidity
- Hardhat

Wallet:

- MetaMask

Hashing:

- SHA-256

Authentication:

- Email + Password + JWT

Authorization:

- RBAC

Version Control:

- Git + GitHub

---

## RBAC Roles

### University

- Login
- Issue certificates
- Upload certificates
- Revoke certificates

### Student

- Login
- View certificates
- Download certificates
- Share verification links

### Employer

- Login
- Upload certificates for verification
- Scan QR codes
- View verification results

---

## Certificate Storage Strategy

Approved Design:

Certificate PDF
→ Generate SHA-256 Hash
→ Store Hash on Blockchain
→ Store PDF Off-Chain

Never store PDFs directly on blockchain.

---

## Verification Workflow

Employer uploads certificate PDF
→ Generate SHA-256 Hash
→ Retrieve blockchain hash
→ Compare hashes

Result:

- Match = Authentic
- Mismatch = Tampered

---

## Included MVP Features

- University Portal
- Student Portal
- Employer Portal
- Authentication
- Authorization
- SHA-256 Hashing
- Blockchain Hash Storage
- Certificate Verification
- Certificate Revocation
- QR Verification
- Verification Logs

---

## Excluded Features

- AI OCR
- AI Fraud Detection
- zk-SNARKs
- Gas Prediction
- Merkle Batch Minting
- IPFS
- Filecoin
- Kubernetes
- Microservices
- Advanced GDPR Layer

---

## Project Rules

1. Use React + Vite + TailwindCSS.
2. Use FastAPI.
3. Use PostgreSQL.
4. Use Solidity + Hardhat.
5. Use SHA-256 hashing.
6. Use JWT authentication.
7. Use RBAC with University, Student, and Employer roles.
8. Store certificate hashes on blockchain.
9. Do not store PDFs on blockchain.
10. Follow approved architecture documents.
11. Do not introduce new technologies without approval.
12. MVP first, no advanced AI features.

---

## Completed Documents

- architecture.md
- database.md
- smart-contracts.md
- project-rules.md

---

## Pending Documents

- backend.md
- frontend.md
- security.md

---

## Instructions For Any AI

Before generating code or architecture:

1. Follow all project rules.
2. Do not modify approved technology choices.
3. Do not introduce additional frameworks.
4. Do not redesign existing architecture.
5. Build only within the approved MVP scope.
6. Ask for approval before making architectural changes.

## Current Progress

Architecture: ✅ Completed
Database Design: ✅ Completed
Smart Contract Architecture: ✅ Completed
Backend Architecture: ✅ Completed
Frontend Architecture: ⬜ Pending
Security Architecture: ⬜ Pending
Implementation: ⬜ Not Started
Testing: ⬜ Not Started
Deployment: ⬜ Not Started
