// blockchain/hardhat.config.js
// Hardhat 2.22.x configuration for the Academic Credential Verification Platform
// CommonJS format — Hardhat 2 uses CommonJS by default (no .cjs extension needed)
//
// Architecture Reference: docs/smart-contracts.md
// Repository Structure: docs/repository-structure.md

require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// ─── Environment Variable Loading ───────────────────────────────────────────
// All secrets loaded from .env file (gitignored)
// Empty string fallback allows compilation/testing without deployment credentials
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || "";
const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL || "";
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";
const REPORT_GAS = process.env.REPORT_GAS !== undefined;

// ─── Network Account Configuration ──────────────────────────────────────────
// Only include accounts array when key is available
// Prevents "invalid private key" error when key is empty string
const sepoliaAccounts = DEPLOYER_PRIVATE_KEY
  ? [DEPLOYER_PRIVATE_KEY]
  : [];

// ─── Hardhat Configuration Object ───────────────────────────────────────────
/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {

  // ─── Solidity Compiler ─────────────────────────────────────────────────
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
        // runs: 200 — Balanced optimization
        // Lower value (1): Optimize for deployment cost, higher execution gas
        // Value 200: Industry standard — optimizes for ~200 function calls
        // Higher value (1000+): Optimize for execution, higher deploy cost
        // CertificateRegistry has frequent verifyCertificate() calls (reads)
        // and infrequent storeCertificate() calls (writes). 200 is appropriate.
      },
      viaIR: false,
      // viaIR: false — DO NOT ENABLE
      // viaIR can alter storage slot assignments.
      // CertificateRegistry storage layout is explicitly planned.
      // Enabling viaIR without storage layout verification is risky.
      // Reference: smart-contracts.md Section 3 (State Variables)
      outputSelection: {
        "*": {
          "*": [
            "abi",            // Required: backend Web3.py + frontend ethers.js
            "evm.bytecode",   // Required: deployment
            "evm.deployedBytecode", // Required: size verification
            "storageLayout",  // Required: verify slot assignments per architecture
          ],
        },
      },
    },
  },

  // ─── Network Configuration ─────────────────────────────────────────────
  networks: {

    // Default Hardhat Network (in-process, no external node needed)
    // Used by: npm run test, npm run compile, npm run deploy:local
    hardhat: {
      chainId: 31337,
      // MetaMask recognizes chainId 31337 as "Hardhat Network"
      mining: {
        auto: true,        // Mine immediately on transaction submission
        interval: 0,       // No artificial delay between blocks
        // auto: true is essential for fast test execution
        // Without it: tests would wait for mining interval
      },
      accounts: {
        count: 20,          // 20 test accounts available in tests
        accountsBalance: "10000000000000000000000", // 10,000 ETH per account
        // These accounts are deterministic based on mnemonic
        // Account #0 private key (public knowledge, dev only):
        // ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
      },
      allowUnlimitedContractSize: false,
      // false: Enforces EIP-170 24KB contract size limit
      // Catches oversized contracts during development, not at deployment
      // CertificateRegistry is expected ~8-12KB — well within limit
      gasPrice: "auto",
      // Hardhat automatically determines appropriate gas pricing
    },

    // Localhost Network (connects to running `npm run node` instance)
    // Used by: npm run deploy:localhost (after starting npm run node separately)
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
      // Same chainId as hardhat network — MetaMask uses same configuration
      timeout: 60000, // 60 second timeout for operations
    },

    // Sepolia Testnet
    // Used by: npm run deploy:sepolia, npm run verify:sepolia
    sepolia: {
      url: SEPOLIA_RPC_URL,
      chainId: 11155111,
      accounts: sepoliaAccounts,
      gasMultiplier: 1.2,
      // 1.2 = 20% buffer above estimated gas
      // Prevents "out of gas" failures due to estimation inaccuracy
      // Sepolia estimation can be slightly under actual cost
      timeout: 120000, // 120 second timeout (network can be slow)
    },

  },

  // ─── Gas Reporter Configuration ────────────────────────────────────────
  gasReporter: {
    enabled: REPORT_GAS,
    // Only display gas table when REPORT_GAS env var is set
    // npm run test → no gas table (faster output reading)
    // npm run test:gas → gas table displayed
    currency: "USD",
    outputFile: "gas-report.txt",
    // Saves report to file for tracking optimization progress
    noColors: false,
    // false: Colored output in terminal
    // Note: Set to true in CI environments that don't support color
    excludeContracts: [],
    // Include all contracts in gas reporting
    src: "contracts/",

    // GAS BUDGETS (from smart-contracts.md — enforce in test assertions):
    // storeCertificate:  ≤ 110,000 gas
    // revokeCertificate: ≤  65,000 gas
    // authorizeIssuer:   ≤  55,000 gas
    // verifyCertificate: 0 gas (view function — free)
    // These are NOT enforced by gasReporter config
    // They are verified by reviewing the gas-report.txt output
  },

  // ─── Etherscan Verification ────────────────────────────────────────────
  // Applies to: npm run verify:sepolia
  etherscan: {
    apiKey: {
      sepolia: ETHERSCAN_API_KEY,
      // Sepolia uses the same Etherscan key as mainnet
      // Key type: "Etherscan" (not "Blockscout" or others)
    },
    customChains: [],
    // Sepolia is natively supported — no custom chain configuration needed
  },

  // ─── Hardhat Paths ─────────────────────────────────────────────────────
  paths: {
    sources: "./contracts",     // Solidity source files location
    tests: "./test",            // Test files location
    cache: "./cache",           // Compilation cache location
    artifacts: "./artifacts",   // Compiled artifacts location
  },

  // ─── Mocha Configuration ───────────────────────────────────────────────
  // Mocha is the test runner used by Hardhat
  mocha: {
    timeout: 60000,
    // 60 second timeout per test
    // Default (2000ms) is too short for blockchain operations
    // Some integration tests may submit multiple transactions
    // 60 seconds accommodates even complex multi-TX test scenarios
    reporter: "spec",
    // "spec": Human-readable output with nested describe/it structure
    // Alternative "min": Minimal output (fewer lines)
    // "spec" is preferred for readability during development
  },
};
