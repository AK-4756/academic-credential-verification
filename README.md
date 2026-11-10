# CertiChain: Decentralized Academic Credential Verification

Engineered a tamper-proof credential verification platform combining a React/Vite frontend with a FastAPI/Python backend and a Solidity blockchain ledger, enabling zero-trust verification for academic institutions.

## Tech Stack
* **Frontend:** React, Vite, Tailwind CSS
* **Backend & APIs:** Python, FastAPI, Web3.py, JWT Authentication
* **Database:** PostgreSQL, SQLAlchemy, Alembic
* **Web3 / Ledger:** Solidity, Hardhat, MetaMask

## Architectural Impact
* **High-Speed Validation:** Built a lightweight FastAPI backend to instantly cross-reference PostgreSQL records before executing heavy blockchain verification.
* **Decentralized Security:** Wrote and deployed Solidity smart contracts via Hardhat to permanently log credential hashes, eliminating database tampering risks.
* **Optimized Client:** Designed a low-latency React/Vite interface styled with Tailwind for seamless institutional uploads and rapid student verifications.

## Architecture & Project Structure
The application follows a modular monolith pattern. The core design principle is that certificate metadata is stored in PostgreSQL, while the cryptographic proof is anchored to the blockchain so it can be independently verified.

```text
academic-credential-verification/
├── backend/               # FastAPI application, routes, services, models
├── blockchain/            # Solidity contracts, Hardhat config, tests
├── frontend/              # React + Vite application
├── docs/                  # Architecture, database, and roadmap docs
└── README.md
```

## Local Setup & Installation

### Prerequisites
Install Git, Python 3.11+, Node.js 18+, npm, and PostgreSQL 15+. Start PostgreSQL and configure your database before launching the backend.

### 1. Clone the repository
```powershell
git clone [https://github.com/AK-4756/academic-credential-verification.git](https://github.com/AK-4756/academic-credential-verification.git)
Set-Location academic-credential-verification
```

### 2. Configure and install the backend
```powershell
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
# Ensure your .env file is configured with your DATABASE_URL
uvicorn main:app --reload --port 8000
```
*API available at http://localhost:8000/api/v1/docs*

### 3. Install and run the frontend
Open a second PowerShell terminal:
```powershell
Set-Location academic-credential-verification\frontend
npm install
npm run dev
```

### 4. Install and run the local blockchain
Open a third PowerShell terminal:
```powershell
Set-Location academic-credential-verification\blockchain
npm install
npx hardhat node
```
