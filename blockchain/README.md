# CertificateRegistry Smart Contract

Blockchain component of the Academic Credential Verification Platform.

## Overview

The `CertificateRegistry` contract provides immutable, trustless storage
of SHA-256 hashes for academic certificates on the Ethereum blockchain.

- **Network**: Hardhat Local (development) | Sepolia (staging)
- **Language**: Solidity ^0.8.19
- **Framework**: Hardhat 2.22.x

## Prerequisites

- Node.js ≥ 18.0.0 (v22 recommended)
- npm ≥ 9.0.0
- MetaMask browser extension (Chrome)

## Setup

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env
# Edit .env with your values (see .env.example for guidance)
```

## Development Workflow

### Start Local Blockchain
```bash
npm run node        # Start Hardhat node on http://127.0.0.1:8545
npm run node:reset  # Start fresh node (no prior state)
```

### Compile
```bash
npm run compile
```

### Test
```bash
npm run test              # All tests
npm run test:unit         # Unit tests only (fast)
npm run test:integration  # Integration tests
npm run test:security     # Security tests
npm run test:coverage     # With coverage report
npm run test:gas          # With gas usage table
```

### Deploy Locally
```bash
# With running node (npm run node in separate terminal)
npm run deploy:localhost

# To in-process network
npm run deploy:local
```

### Deploy to Sepolia
```bash
# Ensure SEPOLIA_RPC_URL and DEPLOYER_PRIVATE_KEY are set in .env
npm run deploy:sepolia
npm run verify:sepolia -- 0xCONTRACT_ADDRESS
```

### Lint
```bash
npm run lint          # Check Solidity files
npm run lint:fix      # Auto-fix fixable issues
```

## Contract Addresses

| Network       | Address                          |
|---------------|----------------------------------|
| Hardhat Local | See `deployments/hardhat-local/` |
| Sepolia       | See `deployments/sepolia/`       |

## Test Accounts (Local Development Only)

Account #0 (Deployer/Owner):
- Address: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`
- Private Key: `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`
- ⚠️ **Public key — development only — never use on mainnet**

Account #1 (University Test Wallet):
- Address: `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`
- Private Key: `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`

## Gas Budgets

| Function            | Budget     |
|---------------------|------------|
| storeCertificate    | ≤ 110,000  |
| revokeCertificate   | ≤ 65,000   |
| authorizeIssuer     | ≤ 55,000   |
| verifyCertificate   | 0 (free)   |

## Coverage Targets

| Metric     | Target |
|------------|--------|
| Statements | ≥ 95%  |
| Branches   | ≥ 95%  |
| Functions  | 100%   |
| Lines      | ≥ 95%  |

## Architecture

See: [`../docs/smart-contracts.md`](../docs/smart-contracts.md)
