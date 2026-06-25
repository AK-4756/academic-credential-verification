// blockchain/scripts/abi-config.js
// ABI distribution path configuration
// Used by: deploy.js and any script that distributes the ABI
//
// WHY SEPARATE FILE:
// Multiple scripts need to know where to copy the ABI.
// Centralizing paths here means if the monorepo structure changes,
// only this file needs updating.

const path = require("path");

// Blockchain component root
const BLOCKCHAIN_ROOT = path.resolve(__dirname, "..");

// Repository root (one level up from blockchain/)
const REPO_ROOT = path.resolve(BLOCKCHAIN_ROOT, "..");

// Source: Where Hardhat puts the compiled artifact
const ABI_SOURCE = path.join(
  BLOCKCHAIN_ROOT,
  "artifacts",
  "contracts",
  "CertificateRegistry.sol",
  "CertificateRegistry.json"
);

// Destination 1: Backend needs the full ABI JSON for Web3.py
const BACKEND_ABI_DEST = path.join(
  REPO_ROOT,
  "backend",
  "blockchain",
  "abi",
  "CertificateRegistry.json"
);

// Destination 2: Frontend needs ABI as a JS export for ethers.js
const FRONTEND_ABI_DEST = path.join(
  REPO_ROOT,
  "frontend",
  "blockchain",
  "contractABI.js"
);

// Destination 3: Frontend contract address file
const FRONTEND_ADDRESS_DEST = path.join(
  REPO_ROOT,
  "frontend",
  "blockchain",
  "contractAddress.js"
);

// Deployment records directory
const DEPLOYMENTS_DIR = path.join(BLOCKCHAIN_ROOT, "deployments");

module.exports = {
  BLOCKCHAIN_ROOT,
  REPO_ROOT,
  ABI_SOURCE,
  BACKEND_ABI_DEST,
  FRONTEND_ABI_DEST,
  FRONTEND_ADDRESS_DEST,
  DEPLOYMENTS_DIR,
};
