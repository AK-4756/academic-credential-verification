# Blockchain-Based Academic Credential Verification Platform

A decentralized academic credential verification system designed to reduce academic fraud by enabling trusted certificate issuance, secure student credential management, and fast employer verification through blockchain-backed records.

## Overview

This project aims to provide a trusted digital infrastructure for academic records. Universities issue credentials, students manage and present them, and employers verify their authenticity without relying on manual confirmation or paper-based trust.

The platform combines:

- a React frontend for role-based user interactions
- a FastAPI backend for secure business logic and APIs
- a PostgreSQL database for structured metadata storage
- Solidity smart contracts for blockchain-backed certificate integrity
- Hardhat for local blockchain development and smart contract testing
- MetaMask-based wallet interaction for blockchain write operations

## Key Features

- University credential issuance workflow
- Student credential ownership and access
- Employer verification of academic records
- Blockchain-backed authenticity checks
- QR-based verification support
- JWT-based authentication and role-based access design
- Audit logging and verification tracking
- Database-driven credential metadata management

## Technology Stack

- React
- Vite
- TailwindCSS
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Solidity
- Hardhat
- MetaMask
- Web3.py
- Python JWT / security tooling

## Current Status

This repository is currently in a foundation / MVP-development stage.

The project structure, architecture, database models, backend security setup, blockchain contract scaffolding, and roadmap documentation are in place, but full end-to-end feature flows and production-hardening are still in progress.

## Project Structure

```text
academic-credential-verification/
├── backend/               # FastAPI application, routes, services, models
├── blockchain/             # Solidity contracts, Hardhat config, tests, scripts
├── frontend/              # React + Vite application
├── docs/                  # Architecture, backend, database, and roadmap docs
├── README.md              # Project overview
├── .gitignore
└── ...
```

## Architecture Summary

The application follows a modular monolith pattern with clear separation between:

- frontend presentation layer
- backend API layer
- database persistence layer
- blockchain trust layer

The core design principle is that certificate metadata is stored in PostgreSQL, while the cryptographic proof is anchored to the blockchain so it can be independently verified.

## Requirements

Before running the project, ensure the following are installed:

- Python 3.11+
- PostgreSQL 15+
- Node.js and npm
- Hardhat / local blockchain tooling
- MetaMask for blockchain wallet interaction

## Getting Started

### 1. Backend setup

```bash
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Then start the backend:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at:

- http://localhost:8000
- Swagger docs when enabled: http://localhost:8000/api/v1/docs

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend typically runs on a local Vite port such as:

- http://localhost:5173
- or the next available port if 5173 is occupied

### 3. Blockchain setup

```bash
cd blockchain
npm install
npx hardhat node
```

This starts the local Hardhat blockchain used for contract deployment and testing.

## Environment Configuration

The backend uses environment files for configuration such as:

- database URL
- JWT keys
- blockchain RPC URL
- frontend URL
- app settings

Configure the relevant `.env` files before starting the application.

## Documentation

Detailed architecture and implementation notes are available in the `docs/` folder, including:

- architecture overview
- backend structure
- database design
- security notes
- roadmap and implementation planning

## Notes

This project is intended to be a secure, decentralized credential verification platform, but it is still under active development. The current repository should be treated as a foundation-stage implementation rather than a fully production-ready system.

## License

No license has been assigned yet. If this repository is intended for public use, a license should be added before distribution.

## Contributing

Contributions are welcome as the project continues to evolve. Please ensure changes are consistent with the current architecture and project documentation before submitting updates.
