# CertiChain: Decentralized Academic Credential Verification

**Built via AI-Augmented Engineering:** This platform was architected and shipped rapidly by orchestrating **Trae AI IDE** and **Claude** to handle complex full-stack generation, database migrations, and smart contract deployments.

CertiChain is a tamper-proof credential verification platform combining a React/Vite frontend with a FastAPI/Python backend and a Solidity blockchain ledger, enabling zero-trust verification for academic institutions.

## 🧠 AI-Augmented Development Workflow

* **Rapid Architecture:** Leveraged AI coding agents to instantly scaffold the modular monolith structure, bridging a modern web frontend with Web3 infrastructure.
* **Backend & Smart Contracts:** Orchestrated Claude to generate robust FastAPI routes, SQLAlchemy data models, and secure Solidity smart contracts for hash storage.

## 🏗️ System Architecture Flow

The core design principle stores certificate metadata in PostgreSQL for high-speed querying, while cryptographic proofs are anchored to the blockchain for independent, trustless verification.

```text
[React/Vite Client] 
       │ (REST API / JWT Auth)
[FastAPI Backend] ─── (SQLAlchemy) ─── [PostgreSQL] (Off-chain Metadata)
       │ (Web3.py)
[Hardhat Node / EVM] (On-chain Cryptographic Proofs)

```

## 🛠️ Tech Stack

* **Frontend:** React, Vite, Tailwind CSS
* **Backend & APIs:** Python 3.11, FastAPI, Web3.py, JWT Authentication
* **Database:** PostgreSQL, SQLAlchemy, Alembic
* **Web3 / Ledger:** Solidity, Hardhat, MetaMask

## ⚡ Architectural Impact

* **High-Speed Validation:** Built a lightweight FastAPI backend to instantly cross-reference PostgreSQL records before executing heavy blockchain verification.
* **Decentralized Security:** Wrote and deployed Solidity smart contracts via Hardhat to permanently log credential hashes, eliminating database tampering risks.
* **Optimized Client:** Designed a low-latency React/Vite interface styled with Tailwind for seamless institutional uploads and rapid student verifications.

---

## 🚀 Local Setup & Installation

**Prerequisites:** Install Git, Python 3.11+, Node.js 18+, npm, and PostgreSQL 15+. Start PostgreSQL and ensure your `.env` file is configured with your `DATABASE_URL` before launching.

### 1. Clone the Repository

```powershell
git clone https://github.com/AK-4756/academic-credential-verification.git
cd academic-credential-verification

```

### 2. Run the Local Blockchain (Terminal 1)

```powershell
cd blockchain
npm install
npx hardhat node

```

### 3. Start the Backend (Terminal 2)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start the FastAPI server
uvicorn main:app --reload --port 8000

```

*API Documentation available at: http://localhost:8000/api/v1/docs*

### 4. Start the Frontend (Terminal 3)

```powershell
cd frontend
npm install
npm run dev

```

---
