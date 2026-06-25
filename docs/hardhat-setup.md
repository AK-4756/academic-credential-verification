# Hardhat Project Setup Implementation Guide
## Sprint 1 — Foundation Setup
### `academic-credential-verification/blockchain/`

---

# PRE-IMPLEMENTATION REVIEW

## Smart Contract Architecture Requirements (from smart-contracts.md)

```
VERIFIED REQUIREMENTS BEFORE SETUP
════════════════════════════════════

CONTRACT TARGET:
├── Contract Name: CertificateRegistry
├── Solidity Version: ^0.8.19
├── Framework: Hardhat 2.22.x (confirmed project decision)
├── Networks: Hardhat local (chainId 31337) + Sepolia (chainId 11155111)
└── No Solidity implementation in Sprint 1

GAS BUDGETS (referenced for test configuration):
├── storeCertificate: ~85,000-110,000 gas
├── revokeCertificate: ~35,000-65,000 gas
├── authorizeIssuer: ~46,000-55,000 gas
└── verifyCertificate: 0 (view function)

TEST COVERAGE TARGET: >95% line, >95% branch, 100% function

ABI DISTRIBUTION:
├── Source: blockchain/artifacts/contracts/
├── Destination 1: backend/blockchain/abi/CertificateRegistry.json
└── Destination 2: frontend/blockchain/contractABI.js

DEPLOYMENT RECORDS (committed to Git):
├── deployments/hardhat-local/CertificateRegistry.json
└── deployments/sepolia/CertificateRegistry.json

SCRIPTS REQUIRED:
├── deploy.js
├── authorize-issuer.js
├── deauthorize-issuer.js
├── check-certificate.js
└── transfer-ownership.js
```

## Hardhat Version Decision: 2.22.x

```
HARDHAT 2.22.x — PROJECT DECISION
════════════════════════════════════

This project uses Hardhat 2.22.x (NOT Hardhat 3.x). Reasons:
├── Existing smart-contract architecture was designed around Hardhat 2 conventions
├── Existing tooling assumes @nomicfoundation/hardhat-toolbox@^4.0.0
├── Existing testing strategy assumes Mocha (Hardhat 2 default test runner)
├── All approved documentation and examples use CommonJS require() syntax
├── Hardhat 3.x migration is NOT approved for this project
└── Node.js 18+ is sufficient (project uses Node.js 22)

HARDHAT 2.22.x KEY CHARACTERISTICS:
├── CommonJS by default: Uses require() and module.exports natively
│   Config file: hardhat.config.js (standard .js extension)
│
├── Plugin system: Stable plugin API via require()
│   Pattern: require("@nomicfoundation/hardhat-toolbox")
│
├── hardhat-toolbox@^4.0.0: Bundles ethers.js v6, chai, mocha,
│   hardhat-gas-reporter, solidity-coverage, hardhat-verify
│
├── Ignition: Not used — custom scripts/ per architecture
│   Decision: deploy.js scripts are primary deployment mechanism
│
└── Node version: Requires Node.js 18+ (project uses Node.js 22)

CONFIGURATION APPROACH:
We use hardhat.config.js (standard JavaScript) with CommonJS syntax.
This is the default and simplest approach for Hardhat 2.22.x.
No ESM configuration or .cjs extension is needed.
```

---

# SECTION 1: EXACT FOLDER STRUCTURE TO CREATE

## 1.1 Complete Directory Layout

```
FOLDERS TO CREATE (in exact order)
════════════════════════════════════

academic-credential-verification/
└── blockchain/                        ← Hardhat workspace root
    │
    ├── contracts/                     ← Solidity source files (Sprint 2)
    │   └── interfaces/                ← Interface definitions (Sprint 2)
    │
    ├── scripts/                       ← Deployment and management scripts
    │   ├── deploy.js                  ← Primary deployment script
    │   ├── authorize-issuer.js        ← University wallet authorization
    │   ├── deauthorize-issuer.js      ← University offboarding
    │   ├── check-certificate.js       ← Manual verification tool
    │   └── transfer-ownership.js      ← Emergency ownership transfer
    │
    ├── test/                          ← Contract test suite
    │   ├── unit/                      ← Individual function tests
    │   ├── integration/               ← Workflow tests
    │   └── security/                  ← Adversarial tests
    │
    ├── deployments/                   ← Deployment records (committed)
    │   ├── hardhat-local/             ← Local Hardhat network records
    │   └── sepolia/                   ← Sepolia testnet records
    │
    ├── ignition/                      ← Hardhat Ignition (not used; custom scripts preferred)
    │   └── modules/                   ← Empty — deploy.js is primary deployment mechanism
    │
    ├── artifacts/                     ← Compiled output (gitignored)
    ├── cache/                         ← Hardhat cache (gitignored)
    ├── coverage/                      ← Coverage reports (gitignored)
    │
    ├── hardhat.config.js              ← Hardhat configuration (CommonJS)
    ├── package.json                   ← npm project definition
    ├── package-lock.json              ← Locked versions (committed)
    ├── .env                           ← Secrets (gitignored)
    ├── .env.example                   ← Template (committed)
    ├── .gitignore                     ← Blockchain-specific gitignore
    ├── .solhint.json                  ← Solidity linter config
    └── README.md                      ← Blockchain component docs
```

## 1.2 Folder Creation Commands

```bash
# Navigate to repository root first
cd academic-credential-verification

# Create all directories in one command
mkdir -p blockchain/contracts/interfaces \
         blockchain/scripts \
         blockchain/test/unit \
         blockchain/test/integration \
         blockchain/test/security \
         blockchain/deployments/hardhat-local \
         blockchain/deployments/sepolia \
         blockchain/ignition/modules

# Navigate into blockchain workspace
cd blockchain

# Verify structure was created correctly
find . -type d | sort
```

**Expected output of `find . -type d | sort`:**
```
.
./contracts
./contracts/interfaces
./deployments
./deployments/hardhat-local
./deployments/sepolia
./ignition
./ignition/modules
./scripts
./test
./test/integration
./test/security
./test/unit
```

---

**[A — Why Required]** The directory structure establishes the exact layout defined in the repository blueprint and smart contract architecture. Every directory has a specific purpose: `contracts/` for source code, `test/` with three sub-categories matching the 87 test cases, `deployments/` for committed network records, and `scripts/` for the five management scripts defined in the architecture.

**[B — Project Requirement Satisfied]** Satisfies the repository structure blueprint requirement and the smart contract architecture's test organization (unit/integration/security). The `deployments/` directory structure supports both the local Hardhat workflow and the Sepolia staging workflow defined in the implementation roadmap.

**[C — Before Moving to Next Step]** Verify that `find . -type d | sort` produces exactly the expected output above. All directories must exist before proceeding to package initialization. If any directory is missing, re-run the mkdir command.

---

# SECTION 2: EXACT npm COMMANDS TO RUN

## 2.1 Complete Installation Sequence

```bash
# STEP 1: Verify Node.js version (Hardhat 2.22.x requires Node 18+)
node --version
# Expected: v18.x.x or higher (project uses v22.x.x)
# If lower: install Node.js 22 LTS from nodejs.org before continuing

# STEP 2: Verify npm version
npm --version
# Expected: 9.x.x or higher (comes with Node 18+)

# STEP 3: Initialize npm project inside blockchain/
# Run from: academic-credential-verification/blockchain/
npm init -y
# Creates: package.json with default values
# We will overwrite package.json content in Section 4

# STEP 4: Install Hardhat 2.22.x
npm install --save-dev hardhat@^2.22.0

# STEP 5: Verify Hardhat version installed
npx hardhat --version
# Expected: 2.22.x

# STEP 6: Install Hardhat Toolbox (compatible with Hardhat 2.22.x)
npm install --save-dev @nomicfoundation/hardhat-toolbox@^4.0.0

# STEP 7: Install dotenv for environment variable loading
npm install --save-dev dotenv@^16.4.0

# STEP 8: Install solhint for Solidity linting (optional but recommended)
npm install --save-dev solhint@^4.5.0

# STEP 9: Run Hardhat initialization to get base config
npx hardhat init
# When prompted:
# ❯ Create a JavaScript project    ← SELECT THIS
#   Create a TypeScript project
#   Create an empty hardhat.config.js
#   Quit
#
# Root: [current directory] ← PRESS ENTER (accept default)
# Add .gitignore: ← YES
# Install dependencies: ← YES (installs any missing peer deps)

# STEP 10: Remove Hardhat's default sample files
# They conflict with our architecture
rm contracts/Lock.sol 2>/dev/null || true
rm test/Lock.js 2>/dev/null || true
rm ignition/modules/Lock.js 2>/dev/null || true

# STEP 11: Verify clean installation
npx hardhat compile
# Expected: "Nothing to compile" (no contracts yet)

npx hardhat test
# Expected: "No test files found" or "0 passing"
```

## 2.2 Verification Commands

```bash
# Verify all packages installed correctly
npm list --depth=0

# Expected output (versions may vary):
# blockchain@1.0.0
# ├── @nomicfoundation/hardhat-toolbox@4.x.x
# ├── dotenv@16.x.x
# ├── hardhat@2.22.x
# └── solhint@4.x.x

# Check for vulnerabilities
npm audit

# Verify Hardhat can connect to network configuration
npx hardhat node --no-mining &
sleep 2
npx hardhat console --network localhost
# Type: .exit to quit

# Stop the node
pkill -f "hardhat node" 2>/dev/null || true
```

---

**[A — Why Required]** The exact command sequence matters for Hardhat 2.22.x. The `--save-dev` flag is critical — smart contracts have no runtime npm dependencies. `npx hardhat init` generates the base configuration that we then customize. Removing default files (Lock.sol, Lock.js) prevents confusion with our actual contract files.

**[B — Project Requirement Satisfied]** Satisfies "Use Solidity + Hardhat" project rule. The `hardhat-toolbox` package bundles ethers.js, chai, mocha, hardhat-gas-reporter, solidity-coverage, and hardhat-verify — all required for the >95% coverage target and gas budget verification.

**[C — Before Moving to Next Step]** Confirm `npx hardhat compile` exits with code 0 and shows "Nothing to compile". Confirm `npm list --depth=0` shows exactly the four packages listed. Do not proceed to package.json configuration if any installation failed.

---

# SECTION 3: REQUIRED DEPENDENCIES AND WHY

## 3.1 Dependency Specification

```
DEPENDENCY ANALYSIS — COMPLETE
════════════════════════════════

PRODUCTION DEPENDENCIES: NONE
──────────────────────────────
Smart contracts execute on the EVM, not in Node.js.
npm packages are not available at contract execution time.
The "dependencies" key in package.json must be empty or omitted.

WHY NO PRODUCTION DEPS:
If any package appears in "dependencies" (not devDependencies),
it signals a misunderstanding of how smart contracts work.
Code review should flag any production dependency immediately.


DEVELOPMENT DEPENDENCIES: 5 PACKAGES
───────────────────────────────────────

PACKAGE 1: hardhat@^2.22.0
━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Core development framework and local EVM
What it provides:
├── In-process Ethereum Virtual Machine (EVM)
├── Solidity compiler integration (solc)
├── Task runner for compile, test, deploy
├── Hardhat Network: local blockchain for development
│   ├── Instant mining (immediate TX confirmation in tests)
│   ├── Stack traces for Solidity errors (unlike real networks)
│   ├── console.log() in Solidity (debugging aid)
│   └── 20 pre-funded test accounts (10,000 ETH each)
├── Plugin ecosystem integration point
└── Network management (local, testnet, mainnet)

Why Hardhat 2.22.x (not 3.x):
├── Architecture designed around Hardhat 2 conventions
├── Stable, well-documented plugin ecosystem
├── CommonJS by default (no ESM migration needed)
└── Active maintenance with security patches

Why Hardhat over alternatives:
├── Foundry (Rust): Would require new toolchain; not approved
├── Truffle: Deprecated by ConsenSys; not recommended
├── Remix: Browser-based only; not suitable for CI/CD integration
└── Hardhat: Approved in architecture, strongest JS ecosystem


PACKAGE 2: @nomicfoundation/hardhat-toolbox@^4.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: All-in-one bundle of testing and deployment tools
What it includes (sub-packages, no separate installation needed):

ethers.js v6:
├── Used in: test files and scripts for contract interaction
├── Why: Same library used in frontend/blockchain/transactions.js
│   Ensures hash conversion patterns validated in tests
│   match exactly what the frontend sends to MetaMask
└── Version 6 matters: v6 has breaking changes from v5

@nomicfoundation/hardhat-chai-matchers:
├── Provides: .revertedWith(), .revertedWithCustomError(), .emit()
├── Why needed: Testing custom errors and events from smart-contracts.md
│   Example: expect(tx).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
└── Essential for verifying all 14 custom errors in CertificateRegistry

@nomicfoundation/hardhat-network-helpers:
├── Provides: loadFixture(), time.increase(), mine(), snapshot()
├── Why needed: loadFixture() is essential for test isolation
│   Without it: deploy contract once per test (87× = very slow)
│   With it: deploy once, snapshot, restore per test (fast)
└── time.increase(): For testing time-dependent logic (future expiry features)

hardhat-gas-reporter:
├── Provides: Gas cost table per function during test runs
├── Why needed: Verify gas budgets from architecture are met
│   storeCertificate ≤ 110,000 gas
│   revokeCertificate ≤ 65,000 gas
│   authorizeIssuer ≤ 55,000 gas
└── Output: Table in console + gas-report.txt file

solidity-coverage:
├── Provides: Istanbul-based code coverage for Solidity
├── Why needed: Architecture requires >95% line, >95% branch, 100% function
├── Output: coverage/ directory with HTML report + lcov.info
└── Integration: Works with hardhat test automatically (--coverage flag)

@nomicfoundation/hardhat-verify:
├── Provides: Etherscan source code verification
├── Why needed: Architecture requires contract verification on Etherscan
│   "Anyone can verify the platform is running this exact code"
└── Usage: npx hardhat verify --network sepolia CONTRACT_ADDRESS

chai:
├── Provides: expect(), assert() assertion library
├── Why needed: All test assertions use chai
└── Works with: hardhat-chai-matchers for Solidity-specific assertions

mocha:
├── Provides: describe(), it(), before(), after() test structure
├── Why needed: Test runner framework for all 87 test cases
└── Configuration: Timeout must be increased for blockchain operations


PACKAGE 3: dotenv@^16.4.0
━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Load .env file into process.env at startup
Used in: hardhat.config.js (first line: require('dotenv').config())
Why needed:
├── DEPLOYER_PRIVATE_KEY must not appear in hardhat.config.js
│   (hardhat.config.js is committed to Git)
├── SEPOLIA_RPC_URL contains API key in the URL
└── ETHERSCAN_API_KEY for source verification

Security principle: process.env loads from .env file which is gitignored.
The hardhat.config.js accesses values via: process.env.VARIABLE_NAME


PACKAGE 4: solhint@^4.5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Solidity source code linter
Used in: npm run lint script
Why needed:
├── Catches common Solidity security antipatterns before testing
├── Enforces style consistency for code review
├── Flags dangerous patterns: tx.origin, selfdestruct, inline assembly
├── Validates NatSpec documentation is present
└── Checks pragma version matches configuration

Rules configured (in .solhint.json):
├── no-unused-vars: Catches unused state variables
├── avoid-tx-origin: Enforces msg.sender (security requirement)
├── compiler-version: Enforces ^0.8.19 pragma
├── func-visibility: Enforces explicit visibility on all functions
└── no-empty-blocks: Catches accidentally empty functions


PACKAGE 5: cross-env@^7.0.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Cross-platform environment variable setting
Used in: npm run test:gas script
Why needed:
├── Windows uses SET VAR=value, Mac/Linux uses VAR=value
├── cross-env normalizes this across all platforms
└── Required for REPORT_GAS=true in test:gas script


TOTAL PACKAGES: 5 (hardhat, hardhat-toolbox, dotenv, solhint, cross-env)
Minimal footprint reduces attack surface and dependency conflicts.
```

---

**[A — Why Required]** Each package serves a specific, documented purpose tied directly to architecture requirements. No package is installed "just in case." The `hardhat-toolbox` bundles provide unified versioning — all testing tools are tested together by the Nomicfoundation team, eliminating version compatibility issues between ethers, chai, and mocha.

**[B — Project Requirement Satisfied]** `hardhat-gas-reporter` satisfies the gas budget verification requirement. `solidity-coverage` satisfies the >95% coverage requirement. `hardhat-verify` satisfies the Etherscan verification requirement for Sepolia deployment. `ethers.js` (bundled) satisfies the need to validate bytes32 hash conversion that the frontend also uses.

**[C — Before Moving to Next Step]** Run `npm list --depth=0` and confirm all four packages appear. Run `npx hardhat --version` and confirm version 3.x.x. Run `npx hardhat compile` and confirm exit code 0. Do not proceed to package.json configuration until all packages are verified.

---

# SECTION 4: PACKAGE.JSON SETUP

## 4.1 Complete package.json

Create the file at `blockchain/package.json` with this exact content:

```json
{
  "name": "academic-credential-verification-contracts",
  "version": "1.0.0",
  "description": "CertificateRegistry smart contract for the Blockchain-Based Academic Credential Verification Platform",
  "private": true,
  "license": "MIT",
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=9.0.0"
  },
  "scripts": {
    "compile": "hardhat compile",
    "compile:force": "hardhat compile --force",
    "clean": "hardhat clean",
    "test": "hardhat test",
    "test:unit": "hardhat test test/unit/**/*.test.js",
    "test:integration": "hardhat test test/integration/**/*.test.js",
    "test:security": "hardhat test test/security/**/*.test.js",
    "test:coverage": "hardhat coverage",
    "test:gas": "cross-env REPORT_GAS=true hardhat test",
    "node": "hardhat node",
    "node:reset": "hardhat node --no-deploy",
    "node:fork": "hardhat node --fork https://eth-sepolia.g.alchemy.com/v2/$ALCHEMY_API_KEY",
    "deploy:local": "hardhat run scripts/deploy.js --network hardhat",
    "deploy:localhost": "hardhat run scripts/deploy.js --network localhost",
    "deploy:sepolia": "hardhat run scripts/deploy.js --network sepolia",
    "authorize:local": "hardhat run scripts/authorize-issuer.js --network hardhat",
    "authorize:localhost": "hardhat run scripts/authorize-issuer.js --network localhost",
    "authorize:sepolia": "hardhat run scripts/authorize-issuer.js --network sepolia",
    "deauthorize:local": "hardhat run scripts/deauthorize-issuer.js --network hardhat",
    "deauthorize:sepolia": "hardhat run scripts/deauthorize-issuer.js --network sepolia",
    "check:local": "hardhat run scripts/check-certificate.js --network hardhat",
    "check:sepolia": "hardhat run scripts/check-certificate.js --network sepolia",
    "transfer:local": "hardhat run scripts/transfer-ownership.js --network hardhat",
    "transfer:sepolia": "hardhat run scripts/transfer-ownership.js --network sepolia",
    "verify:sepolia": "hardhat verify --network sepolia",
    "lint": "solhint 'contracts/**/*.sol'",
    "lint:fix": "solhint 'contracts/**/*.sol' --fix",
    "size": "hardhat size-contracts",
    "audit": "npm audit --audit-level=high"
  },
  "keywords": [
    "blockchain",
    "credentials",
    "verification",
    "ethereum",
    "solidity"
  ],
  "devDependencies": {
    "@nomicfoundation/hardhat-toolbox": "^4.0.0",
    "cross-env": "^7.0.3",
    "dotenv": "^16.4.0",
    "hardhat": "^2.22.0",
    "solhint": "^4.5.0"
  }
}
```

## 4.2 Script Explanations

```
SCRIPT CATALOG EXPLANATIONS
═════════════════════════════

COMPILATION SCRIPTS:
├── compile: Standard compilation of all .sol files
├── compile:force: Force recompile (bypasses cache) — use after config changes
└── clean: Remove artifacts/ and cache/ — use when debugging compile issues

TESTING SCRIPTS:
├── test: Run all 87 test cases (unit + integration + security)
├── test:unit: Run only unit tests (~70 tests) — fast feedback loop
├── test:integration: Run only workflow tests (~12 tests)
├── test:security: Run only adversarial tests (~19 tests)
├── test:coverage: Full test suite with Istanbul coverage report
└── test:gas: Full test suite with gas usage table (REPORT_GAS=true)

NETWORK SCRIPTS:
├── node: Start Hardhat local node (state resets on restart)
├── node:reset: Start fresh Hardhat node (clears all blockchain state)
└── node:fork: Start node forking Sepolia state (future use case)

DEPLOYMENT SCRIPTS:
├── deploy:local: Deploy to in-process Hardhat Network (for testing)
├── deploy:localhost: Deploy to running node (npm run node must be active)
└── deploy:sepolia: Deploy to Sepolia testnet (requires credentials in .env)

MANAGEMENT SCRIPTS:
├── authorize:*: Add university wallet to contract's authorized issuers
├── deauthorize:*: Remove university wallet from authorized issuers
├── check:*: Query certificate status (debugging tool)
└── transfer:*: Emergency ownership transfer

VERIFICATION:
└── verify:sepolia: Publish contract source to Etherscan
    Usage: npm run verify:sepolia -- 0xCONTRACT_ADDRESS

MAINTENANCE:
├── lint: Check all .sol files for style and security issues
├── lint:fix: Auto-fix fixable lint issues
├── size: Check compiled contract byte sizes
└── audit: npm security audit (run before every deployment)

NOTE ON cross-env:
test:gas uses cross-env for Windows/Mac/Linux compatibility.
cross-env is included in devDependencies (already installed with npm install).
This sets REPORT_GAS=true environment variable cross-platform.
```

## 4.3 Why CommonJS

```
COMMONJS vs ESM DECISION
═════════════════════════

Hardhat 2.22.x uses CommonJS by default.
We choose CommonJS because:

1. Architecture specifies JavaScript (not TypeScript)
2. All approved script examples use require() syntax
3. The deploy.js scripts use require() for deployment records
4. CommonJS is simpler for single-developer MVP
5. Avoids top-level await issues in older Node versions

With Hardhat 2.22.x (CommonJS is default):
├── hardhat.config.js → uses require() and module.exports
├── scripts/*.js → uses require() and module.exports
└── test/*.js → uses require() (mocha/chai standard pattern)

Alternative ("type": "module"):
├── Would require: hardhat.config.js with import/export
├── Would require: scripts/*.mjs or package.json type=module
└── Would require: dynamic import() for require()-only packages
    This complexity is unnecessary for MVP scope.
```

---

**[A — Why Required]** The `package.json` defines every developer interaction with the blockchain component. The scripts section means no developer needs to memorize `hardhat run scripts/deploy.js --network hardhat` — they simply run `npm run deploy:local`. The `"private": true` field prevents accidental npm publish. The `engines` field enforces Node.js 18+ requirement for Hardhat 2.22.x.

**[B — Project Requirement Satisfied]** The script naming convention (`deploy:local`, `deploy:sepolia`, `authorize:local`) directly implements the two-network workflow from the implementation roadmap. The test scripts implement the three-category test organization (unit/integration/security) required by the smart contract architecture.

**[C — Before Moving to Next Step]** After replacing `package.json` content, run `npm install` to ensure the lock file is updated. Run `npm run compile` and confirm exit code 0. Run `npm run test` and confirm exit code 0. Do not proceed to Hardhat configuration if either command fails.

---

# SECTION 5: HARDHAT CONFIGURATION SETUP

## 5.1 hardhat.config.js

Create the file at `blockchain/hardhat.config.js`:

```javascript
// blockchain/hardhat.config.js
// Hardhat 2.22.x configuration — CommonJS is the default format
// Standard .js extension — Hardhat 2.22.x uses CommonJS by default
// No .cjs extension needed, no "type": "commonjs" needed in package.json

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
      confirmations: 6,
      // Wait for 6 blocks after deployment before declaring success
      // ~72 seconds at 12 seconds/block (Ethereum post-Merge)
      // Ensures transaction is deeply embedded before ABI is distributed
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

  // ─── Coverage Configuration ────────────────────────────────────────────
  // Applies to: npm run test:coverage
  // Tool: solidity-coverage (Istanbul-based)
  solcoverageOptions: {
    // Note: solidity-coverage config is in .solcover.js file
    // See blockchain/.solcover.js for configuration
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
```

## 5.2 Configuration Notes for Hardhat 2.22.x

```
HARDHAT 2.22.x CONFIGURATION NOTES
════════════════════════════════════

FILE NAMING: hardhat.config.js (standard JavaScript)
────────────────────────────────────────────────────────
Hardhat 2.22.x is CommonJS by default.
Using .js is the standard and simplest approach.
Hardhat 2 looks for hardhat.config.js in the project root.
No .cjs extension is needed.

PLUGIN REGISTRATION: require()
────────────────────────────────────────────
With CommonJS format, plugins are loaded via:
require("@nomicfoundation/hardhat-toolbox")
This is the standard Hardhat 2.x pattern.

NETWORK TIMEOUT VALUES:
────────────────────────
localhost: 60,000ms — Local node is fast but may start slowly
sepolia: 120,000ms — Public testnet can be congested

SOLIDITY COVERAGE IN HARDHAT 2.22.x:
────────────────────────────────────
Coverage configuration is in a separate .solcover.js file.
The solcoverageOptions key in hardhat.config.js is a placeholder.
Actual config: blockchain/.solcover.js

HARDHAT TOOLBOX COMPATIBILITY:
────────────────────────────────
@nomicfoundation/hardhat-toolbox@^4.0.0 is built for Hardhat 2.x
If compatibility issues arise:
npm install --save-dev @nomicfoundation/hardhat-toolbox@latest
This ensures the latest compatible version for Hardhat 2.
```

---

**[A — Why Required]** The Hardhat configuration is the single source of truth for how contracts are compiled, tested, and deployed. Every setting is deliberate: the optimizer runs value (200) balances deployment and execution costs for the CertificateRegistry access pattern; `viaIR: false` protects the planned storage layout; `allowUnlimitedContractSize: false` catches oversized contracts during development.

**[B — Project Requirement Satisfied]** The Sepolia network configuration satisfies the staging deployment requirement. The gas reporter satisfies the gas budget verification requirement. The coverage configuration satisfies the >95% coverage requirement. The Etherscan configuration satisfies the source verification requirement from the architecture.

**[C — Before Moving to Next Step]** After creating `hardhat.config.js`, run `npx hardhat compile` and confirm zero errors. Run `npx hardhat node` in a separate terminal and confirm the node starts on port 8545 with 20 accounts. Run `CTRL+C` to stop the node. Do not proceed to environment variables if compilation fails.

---

# SECTION 6: ENVIRONMENT VARIABLE SETUP

## 6.1 blockchain/.env (Gitignored — Developer Creates)

```bash
# Create the .env file from the example
cp .env.example .env

# Then populate with actual values (instructions below)
```

The `.env` file content for development:

```bash
# =============================================================================
# blockchain/.env
# GITIGNORED — Never commit this file
# Copy from .env.example and populate with actual values
# =============================================================================

# ─── Deployer Configuration ──────────────────────────────────────────────────

# Private key of the Ethereum wallet used for contract deployment
# DEVELOPMENT: Use Hardhat Account #0 (see CONTRIBUTING.md for the key)
# STAGING (Sepolia): Use a dedicated deployment wallet with Sepolia ETH
# WARNING: NEVER use a mainnet wallet private key here
# WARNING: NEVER use a wallet with real ETH here (development only)
DEPLOYER_PRIVATE_KEY=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# ─── Network Configuration ───────────────────────────────────────────────────

# Sepolia testnet RPC endpoint
# Get from: Infura (infura.io) or Alchemy (alchemy.com) — free tier available
# Format: https://sepolia.infura.io/v3/YOUR_PROJECT_ID
#      OR: https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
# Not needed for local Hardhat development — only for Sepolia deployment
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/your_infura_project_id

# ─── Verification ────────────────────────────────────────────────────────────

# Etherscan API key for contract source code verification
# Get from: https://etherscan.io/myapikey (free account required)
# Used by: npm run verify:sepolia
ETHERSCAN_API_KEY=your_etherscan_api_key

# ─── Optional Configuration ──────────────────────────────────────────────────

# Set to any non-empty value to enable gas reporting in test output
# Usage: REPORT_GAS=true npm run test
# Or use the script: npm run test:gas
# REPORT_GAS=true

# CoinMarketCap API key for USD gas cost estimates in gas reporter
# Optional — without it, gas reporter shows units only (sufficient for MVP)
# Get from: https://coinmarketcap.com/api/
# COINMARKETCAP_API_KEY=your_api_key

# Override deployer as initial contract owner (if using multisig/hardware wallet)
# Leave empty to make deployer the contract owner
# Format: 0x-prefixed Ethereum address
# INITIAL_OWNER_ADDRESS=0x...

# Alchemy API key (alternative to SEPOLIA_RPC_URL for node forking)
# ALCHEMY_API_KEY=your_alchemy_api_key
```

## 6.2 blockchain/.env.example (Committed to Git)

Create the file at `blockchain/.env.example`:

```bash
# =============================================================================
# blockchain/.env.example
# COMMITTED TO GIT — Template for developers to create their .env
# Copy this file: cp .env.example .env
# Then populate with your actual values
# =============================================================================

# ─── REQUIRED: Deployer Configuration ────────────────────────────────────────

# Private key of the Ethereum wallet used for contract deployment
# DEVELOPMENT: Use Hardhat Account #0 private key (see CONTRIBUTING.md)
# STAGING: Generate a dedicated Sepolia wallet — DO NOT use your main wallet
# SECURITY: Never use a wallet containing real ETH
# FORMAT: 64-character hex string (with or without 0x prefix)
DEPLOYER_PRIVATE_KEY=your_deployer_private_key_here

# ─── REQUIRED FOR SEPOLIA: Network Configuration ─────────────────────────────

# Sepolia testnet JSON-RPC endpoint URL
# Options:
#   Infura: https://sepolia.infura.io/v3/YOUR_PROJECT_ID
#   Alchemy: https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
#   QuickNode: https://your-endpoint.quiknode.pro/YOUR_TOKEN/
# Not needed for local Hardhat development
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/your_project_id

# ─── REQUIRED FOR SEPOLIA: Etherscan Verification ────────────────────────────

# Etherscan API key for contract source verification (after Sepolia deployment)
# Get at: https://etherscan.io/myapikey
# Used by: npm run verify:sepolia -- CONTRACT_ADDRESS
ETHERSCAN_API_KEY=your_etherscan_api_key

# ─── OPTIONAL: Gas Reporting ─────────────────────────────────────────────────

# Uncomment to enable gas reporting during all test runs
# Or use: npm run test:gas (automatically sets this)
# REPORT_GAS=true

# ─── OPTIONAL: USD Gas Cost Estimates ────────────────────────────────────────

# CoinMarketCap API key for USD-denominated gas cost estimates
# Without this: gas reporter shows gas units only (sufficient for MVP)
# Get at: https://coinmarketcap.com/api/
# COINMARKETCAP_API_KEY=your_api_key

# ─── OPTIONAL: Contract Owner Override ───────────────────────────────────────

# If contract owner should be different from deployer address
# Leave commented to use deployer as owner
# Use case: Deploy from hot wallet, immediately transfer to hardware wallet
# INITIAL_OWNER_ADDRESS=0x...

# ─── OPTIONAL: Alchemy API Key ───────────────────────────────────────────────

# Required if using node forking feature (npm run node:fork)
# ALCHEMY_API_KEY=your_alchemy_api_key
```

## 6.3 Variable Security Classification

```
ENVIRONMENT VARIABLE SECURITY MATRIX
══════════════════════════════════════

Variable                Classification    Commit?   Notes
─────────────────────────────────────────────────────────────────────────
DEPLOYER_PRIVATE_KEY    CRITICAL SECRET   NO        Ethereum wallet private key
SEPOLIA_RPC_URL         LOW-MED SECRET    NO        Contains API key in URL
ETHERSCAN_API_KEY       LOW SECRET        NO        Rate-limit risk if exposed
REPORT_GAS              NOT SECRET        Optional  Can be CLI env var
COINMARKETCAP_API_KEY   LOW SECRET        NO        Rate-limit risk
INITIAL_OWNER_ADDRESS   NOT SECRET        Optional  Ethereum address (public)
ALCHEMY_API_KEY         LOW-MED SECRET    NO        Contains API key


DEVELOPMENT vs STAGING KEY SEPARATION:
────────────────────────────────────────
Development DEPLOYER_PRIVATE_KEY:
├── Value: Hardhat Account #0 key (publicly documented)
├── Key: ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
├── Address: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
├── Balance: 10,000 ETH (on Hardhat Network only — fake ETH)
└── Risk: Zero — key is publicly known; only works on local network

Staging DEPLOYER_PRIVATE_KEY:
├── Value: Generated fresh for staging environment
├── Generate: openssl rand -hex 32
├── Address: New Ethereum address with Sepolia ETH from faucet
├── Balance: 0.5+ Sepolia ETH (testnet only — no real value)
└── Risk: Low — Sepolia ETH has no real value

WHY DIFFERENT KEYS:
If a developer accidentally copies the staging key to development .env,
using it on the local Hardhat network causes no security issue.
But if the local key were accidentally used with real ETH funding,
that would be a problem. Separation prevents any ambiguity.


GRACEFUL DEGRADATION (missing variables):
────────────────────────────────────────────
Missing DEPLOYER_PRIVATE_KEY:
├── hardhat compile → ✅ works (no key needed)
├── hardhat test → ✅ works (uses built-in accounts)
├── deploy:local → ✅ works (uses hardhat account #0 automatically)
└── deploy:sepolia → ❌ fails with "no private key configured"
    This is correct behavior — explicit failure before attempting deployment

Missing SEPOLIA_RPC_URL:
└── deploy:sepolia → ❌ fails with "invalid URL"
    Prevents silent deployment to wrong network

Missing ETHERSCAN_API_KEY:
└── verify:sepolia → ❌ fails with "API key required"
    Deployment itself works; only verification step fails
```

---

**[A — Why Required]** Environment variable isolation prevents the most catastrophic failure mode: a private key committed to a public Git repository. The graceful degradation design means developers can compile and test without any `.env` file, but deployment to real networks fails explicitly with clear errors.

**[B — Project Requirement Satisfied]** Satisfies the security architecture requirement: "All secrets in environment variables; .env gitignored; no secrets committed to Git." Satisfies the two-network workflow requirement (local development without credentials, Sepolia deployment with credentials).

**[C — Before Moving to Next Step]** Verify that `git ls-files | grep "\.env$"` returns nothing (`.env` is not tracked). Verify that `.env.example` appears in `git ls-files`. Verify that running `npm run compile` works without any `.env` values set by temporarily renaming `.env` to `.env.backup`.

---

# SECTION 7: LOCAL BLOCKCHAIN WORKFLOW

## 7.1 Daily Development Workflow

```
LOCAL DEVELOPMENT WORKFLOW
════════════════════════════

TERMINAL SETUP (recommended 2-terminal workflow):

TERMINAL 1 — Hardhat Node (persistent, always running)
──────────────────────────────────────────────────────
# Start from blockchain/ directory
npm run node

Expected output:
═══════════════════════════════════════════════════════════
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
Private Key: 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

[... 18 more accounts ...]

⚠️  WARNING: These are development accounts. Never use on mainnet!
═══════════════════════════════════════════════════════════
Keep this terminal running throughout development session.
State persists within the session (resets on node restart).


TERMINAL 2 — Active Development
─────────────────────────────────
# All development commands run here

COMPILATION:
npm run compile
# Output: "Compiled 1 Solidity file successfully" (after contract is written)

TESTING:
npm run test:unit          # Fast: ~30 seconds (unit tests only)
npm run test:integration   # Medium: ~60 seconds (workflow tests)
npm run test               # Full: ~90 seconds (all 87 tests)

GAS ANALYSIS:
npm run test:gas           # Full test suite with gas table
# Output includes per-function gas usage

COVERAGE:
npm run test:coverage      # Generates HTML report in coverage/
# Open: coverage/index.html in browser


CONTRACT DEVELOPMENT CYCLE (Test-Driven Development):
──────────────────────────────────────────────────────
For each contract feature (Sprint 2):

Step 1: Write failing test
  test/unit/CertificateRegistry.storage.test.js
  → Add test case for the feature
  → npm run test:unit → test FAILS (expected)

Step 2: Implement in Solidity
  contracts/CertificateRegistry.sol
  → Write the function implementation

Step 3: Compile
  npm run compile
  → Fix any compilation errors

Step 4: Verify test passes
  npm run test:unit
  → Test should PASS now

Step 5: Check gas usage
  npm run test:gas
  → Verify function is within budget

Step 6: Run full suite
  npm run test
  → Ensure no regressions


LOCAL DEPLOYMENT CYCLE (after completing contract features):
──────────────────────────────────────────────────────────────
Step 1: Ensure node is running (Terminal 1: npm run node)

Step 2: Deploy contract to localhost
  npm run deploy:localhost
  Expected output:
  "Deploying CertificateRegistry..."
  "CertificateRegistry deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3"
  "Deployment record saved to deployments/hardhat-local/CertificateRegistry.json"
  "ABI copied to backend/blockchain/abi/CertificateRegistry.json"
  "ABI copied to frontend/blockchain/contractABI.js"

Step 3: Authorize university test wallet
  npm run authorize:localhost
  Expected output:
  "Authorizing issuer: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
  "IssuerAuthorized event emitted"
  "isAuthorizedIssuer: true"

Step 4: Update backend .env
  backend/.env:
  CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
  BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
  NETWORK_CHAIN_ID=31337

Step 5: Update frontend .env.development
  frontend/.env.development:
  VITE_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3

Step 6: Restart backend and frontend dev servers
  (New contract = new address; restart required to pick up new .env values)


CHAIN STATE MANAGEMENT:
─────────────────────────
State PERSISTS within the session:
├── Contract deployments survive node restart
├── Issued certificates survive node restart
├── Development sessions resume where they left off
└── Data location: blockchain/cache/hardhat-network-database/

When to RESET state:
├── Starting fresh test scenario: npm run node:reset
├── After major contract changes that invalidate old data
├── When state is confusing debugging session
└── Command: npm run node:reset (starts fresh, no deploy history)


METAMASK LOCAL SETUP (one-time developer setup):
──────────────────────────────────────────────────
In Chrome with MetaMask extension:

Add Hardhat Local Network:
├── Open MetaMask → Settings → Networks → Add Network
├── Network Name: Hardhat Local
├── RPC URL: http://127.0.0.1:8545
├── Chain ID: 31337
├── Currency Symbol: ETH
└── Block Explorer URL: (leave empty)

Import Development Account:
├── MetaMask → Import Account → Private Key
├── Paste: ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
├── Account shows: 10,000 ETH (when Hardhat node is running)
└── This is Hardhat Account #0 — publicly known — development only

⚠️ SECURITY NOTE: Use a separate Chrome profile for Hardhat development.
   Never mix development wallets with real-fund wallets.
```

## 7.2 Common Troubleshooting

```
LOCAL WORKFLOW TROUBLESHOOTING
════════════════════════════════

ERROR: "Error: listen EADDRINUSE :::8545"
CAUSE: Another process is using port 8545
FIX:
  lsof -i :8545 | grep LISTEN
  kill -9 [PID]
  npm run node

ERROR: "Error: Cannot find module 'hardhat'"
CAUSE: npm install not run or ran outside blockchain/ directory
FIX:
  cd academic-credential-verification/blockchain
  npm install

ERROR: MetaMask shows "Wrong Network" after MetaMask reopens
CAUSE: Hardhat node restarted (new session = new network state)
FIX:
  MetaMask → Switch to Hardhat Local network
  If network is gone: MetaMask → Add Network (repeat setup)

ERROR: "Transaction reverted without a reason string"
CAUSE: Old contract ABI, wrong contract address, or assertion failure
FIX:
  Verify CONTRACT_ADDRESS in backend/.env matches deployments/hardhat-local/
  Re-run: npm run deploy:localhost
  Re-run: npm run authorize:localhost

ERROR: "nonce too high" in MetaMask
CAUSE: MetaMask has cached nonces from a reset Hardhat node
FIX:
  MetaMask → Settings → Advanced → Reset Account
  This clears cached nonces without removing the account

ERROR: Coverage report shows <95%
CAUSE: Missing test cases for specific branches
FIX:
  Open: coverage/index.html in browser
  Find: Red or yellow highlighted lines (uncovered)
  Write: Test cases that execute those code paths
```

---

**[A — Why Required]** The local development workflow is the daily operating procedure for Sprint 2 (contract development). Every step is documented because blockchain development has unique failure modes not present in regular web development — MetaMask nonce issues, network state resets, and ABI synchronization problems are common sources of hours-long debugging sessions when not anticipated.

**[B — Project Requirement Satisfied]** The two-terminal workflow satisfies the requirement for a persistent local blockchain during development. The chain state within a session enables realistic integration testing where certificate data survives script runs. The MetaMask setup satisfies the wallet integration requirement.

**[C — Before Moving to Next Step]** Successfully start the Hardhat node (`npm run node`). Verify port 8545 is listening: `nc -zv 127.0.0.1 8545`. Verify MetaMask connects to Hardhat Local network and shows 10,000 ETH for Account #0. Verify `npm run deploy:localhost` works after Sprint 2 contract is written (placeholder check now).

---

# SECTION 8: SEPOLIA PREPARATION WORKFLOW

## 8.1 Sepolia Setup Sequence

```
SEPOLIA PREPARATION WORKFLOW
════════════════════════════

PHASE 1: Obtain Sepolia Testnet ETH (Do This Now — Sprint 1)
─────────────────────────────────────────────────────────────
Faucets have rate limits and ETH may take time to arrive.
Request Sepolia ETH in Sprint 1 even though deployment is Sprint 12.

Step 1: Generate a dedicated Sepolia deployment wallet
  # In your terminal (NOT the blockchain/ directory)
  # Method A: Use MetaMask to create a new account
  MetaMask → Create Account → Copy address
  
  # Method B: Generate via openssl (save private key securely)
  openssl rand -hex 32
  # This generates a private key; derive address using MetaMask import

Step 2: Save the wallet information
  # In a password manager or secure notes (NOT in any project file):
  STAGING_DEPLOYER_ADDRESS=0x[your_new_address]
  STAGING_DEPLOYER_PRIVATE_KEY=[your_new_private_key]

Step 3: Request Sepolia ETH from multiple faucets
  Target balance: 0.5 ETH minimum (covers deployment + testing)
  
  Faucet 1: https://sepoliafaucet.com
  └── Provides: 0.5 ETH per day (requires Alchemy account)
  
  Faucet 2: https://faucets.chain.link (Chainlink)
  └── Provides: 0.5 LINK + 0.1 ETH (requires wallet with mainnet ETH)
  
  Faucet 3: https://www.infura.io/faucet/sepolia
  └── Provides: 0.5 ETH (requires Infura account)
  
  Faucet 4: https://faucet.quicknode.com/ethereum/sepolia
  └── Provides: 0.1 ETH per request

Step 4: Monitor balance
  https://sepolia.etherscan.io/address/[your_address]
  Wait until balance shows ≥ 0.5 ETH before attempting deployment


PHASE 2: Configure RPC Endpoint
──────────────────────────────────
Step 1: Create Infura account
  Go to: https://app.infura.io/register
  Verify email → Create new API key

Step 2: Configure for Sepolia
  Dashboard → API Keys → Your Key → Endpoints → Ethereum
  Enable: Sepolia network
  Copy: https://sepolia.infura.io/v3/YOUR_PROJECT_ID

Step 3: OR use Alchemy (alternative)
  Go to: https://www.alchemy.com/
  Create account → Create App → Select Ethereum + Sepolia
  Copy: https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY

Step 4: Add to blockchain/.env
  SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/your_actual_project_id

Step 5: Verify connection (no contract needed)
  npx hardhat run --network sepolia scripts/check-certificate.js
  # This will fail since contract isn't deployed yet, but should show
  # network connectivity rather than "connection refused"


PHASE 3: Configure Etherscan API
───────────────────────────────────
Step 1: Register at etherscan.io
  Go to: https://etherscan.io/register

Step 2: Generate API key
  Go to: https://etherscan.io/myapikey
  Click: Add → Name: "credential-platform-dev"
  Copy: API key string

Step 3: Add to blockchain/.env
  ETHERSCAN_API_KEY=your_etherscan_api_key


PHASE 4: Test Sepolia Configuration (Verification Only)
─────────────────────────────────────────────────────────
# Test that RPC connection works (contract doesn't exist yet)
npx hardhat run --network sepolia - << 'EOF'
const { ethers } = require("hardhat");
async function main() {
  const provider = ethers.provider;
  const blockNumber = await provider.getBlockNumber();
  console.log("Connected to Sepolia. Block number:", blockNumber);
  const [deployer] = await ethers.getSigners();
  const balance = await provider.getBalance(deployer.address);
  console.log("Deployer:", deployer.address);
  console.log("Balance:", ethers.formatEther(balance), "ETH");
}
main().catch(console.error);
EOF

Expected output:
"Connected to Sepolia. Block number: 6543210"
"Deployer: 0x[your_staging_deployer_address]"
"Balance: 0.5 ETH"


PHASE 5: Sepolia Deployment Flow (Sprint 12 Preview)
──────────────────────────────────────────────────────
This documents the complete Sepolia deployment for Sprint 12.
Setup now; execute in Sprint 12.

Pre-deployment checklist:
☐ npm run test (all 87 tests passing)
☐ npm run test:coverage (>95% all metrics)
☐ npm run test:gas (all within budget)
☐ npm audit (0 high-severity vulnerabilities)
☐ Sepolia wallet has ≥ 0.5 ETH
☐ SEPOLIA_RPC_URL confirmed working (Phase 4 above)
☐ ETHERSCAN_API_KEY configured
☐ DEPLOYER_PRIVATE_KEY updated to staging key (not dev key)

Deployment:
npm run deploy:sepolia

Expected output:
"Network: sepolia (chainId: 11155111)"
"Deploying CertificateRegistry..."
"Waiting for 6 confirmations..."
"CertificateRegistry deployed to: 0x..."
"Transaction: https://sepolia.etherscan.io/tx/0x..."
"Deployment record: deployments/sepolia/CertificateRegistry.json"
"ABI synchronized to backend and frontend"

Post-deployment:
npm run verify:sepolia -- 0xCONTRACT_ADDRESS
# Wait 30-60 seconds for Etherscan to index the contract
# Then visit: https://sepolia.etherscan.io/address/0xCONTRACT_ADDRESS#code
# Expected: "Contract Source Code Verified"
```

---

**[A — Why Required]** Sepolia ETH from faucets can take hours to arrive and faucets sometimes go offline. Setting up Sepolia access in Sprint 1 (even though deployment happens in Sprint 12) prevents a blocking delay when the deployment sprint arrives. The RPC and Etherscan configuration must be in place before any staging testing.

**[B — Project Requirement Satisfied]** Satisfies the Sepolia testnet staging requirement from the implementation roadmap. The Etherscan verification step satisfies the architecture requirement: "Contract source code published to Etherscan. Anyone can verify the platform is running exactly this code."

**[C — Before Moving to Next Step]** Verify that the Sepolia connection test (Phase 4 command) shows a block number and your deployer balance. Save your Sepolia deployer private key in a password manager. Confirm `.env` contains the actual SEPOLIA_RPC_URL (not the placeholder). Proceed to testing structure setup.

---

# SECTION 9: TESTING SETUP STRUCTURE

## 9.1 Test Directory Architecture

```
TEST DIRECTORY SETUP
═════════════════════

blockchain/test/
├── unit/                              ← 70 test cases (Sprints 2-3)
│   ├── CertificateRegistry.access.test.js
│   │   Contains: TC-AC-01 through TC-AC-20 (access control)
│   │   Tests: onlyOwner, authorizeIssuer, deauthorizeIssuer, transferOwnership
│   │
│   ├── CertificateRegistry.storage.test.js
│   │   Contains: TC-ST-01 through TC-ST-20 (hash storage)
│   │   Tests: storeCertificate all success + revert conditions
│   │
│   ├── CertificateRegistry.verification.test.js
│   │   Contains: TC-VR-01 through TC-VR-15 (verification)
│   │   Tests: verifyCertificate all return value combinations
│   │
│   └── CertificateRegistry.revocation.test.js
│       Contains: TC-RV-01 through TC-RV-15 (revocation)
│       Tests: revokeCertificate success + all revert conditions
│
├── integration/                       ← 12 test cases (Sprint 2)
│   ├── IssuanceFlow.test.js
│   │   Tests: Complete deploy → authorize → issue → verify workflow
│   │
│   ├── VerificationFlow.test.js
│   │   Tests: AUTHENTIC, TAMPERED, REVOKED, NOT_FOUND scenarios
│   │
│   └── RevocationFlow.test.js
│       Tests: Issue → verify authentic → revoke → verify revoked
│
└── security/                          ← 19 test cases (Sprint 2)
    ├── AccessControl.security.test.js
    │   Tests: Unauthorized access attempts (7 test cases)
    │
    ├── InputValidation.security.test.js
    │   Tests: Zero hash, empty UID, oversized UID (7 test cases)
    │
    └── EdgeCases.security.test.js
        Tests: Double store, cross-university revoke, double revoke (5 cases)
```

## 9.2 Test Configuration Files

Create `blockchain/test/.mocharc.yml`:

```yaml
# blockchain/test/.mocharc.yml
# Mocha configuration for Hardhat tests
timeout: 60000        # 60 seconds per test (blockchain ops are slow)
reporter: spec         # Human-readable nested output
exit: true            # Force exit after tests complete
```

Create `blockchain/.solcover.js`:

```javascript
// blockchain/.solcover.js
// Coverage configuration for solidity-coverage
module.exports = {
  skipFiles: [
    'contracts/interfaces/',  // Interfaces have no executable code
  ],
  configureYulOptimizer: false,
  // false: Consistent with viaIR: false in hardhat.config.js
  // Changing this would affect coverage measurement accuracy
  
  // Note: These are the MINIMUM files to skip
  // Do not skip any implementation files — all must be covered
};
```

## 9.3 Test Helper Structure

Create `blockchain/test/helpers/` directory and placeholder files:

```bash
mkdir -p blockchain/test/helpers

# Create placeholder helper files (populated in Sprint 2)
touch blockchain/test/helpers/constants.js
touch blockchain/test/helpers/fixtures.js
touch blockchain/test/helpers/utils.js
```

Create `blockchain/test/helpers/constants.js` (configuration only, no implementation):

```javascript
// blockchain/test/helpers/constants.js
// Test constants — populated in Sprint 2 during contract development
// Purpose: Centralize test data to avoid magic strings in test files

// These constants will be populated in Sprint 2:

// GAS BUDGETS (from smart-contracts.md)
const GAS_BUDGETS = {
  storeCertificate: 110_000,    // Maximum acceptable gas
  revokeCertificate: 65_000,
  authorizeIssuer: 55_000,
  deauthorizeIssuer: 35_000,
  verifyCertificate: 0,          // View function — zero gas cost
};

// CERTIFICATE UID FORMAT (from database design)
const CERT_UID_FORMAT = /^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$/;
// Example valid UID: "MIT-2025-00001"
// Max length: 50 characters (matches DB VARCHAR(50))

// SAMPLE TEST UIDS (populated in Sprint 2)
const TEST_UIDS = {
  // VALID_UID: "TESTUNIV-2025-00001",
  // DUPLICATE_UID: "TESTUNIV-2025-00001",  // same as VALID_UID
  // EMPTY_UID: "",
  // OVERSIZED_UID: "A".repeat(51),
};

// SAMPLE TEST HASHES (populated in Sprint 2)
const TEST_HASHES = {
  // VALID_HASH: ethers.keccak256(ethers.toUtf8Bytes("sample certificate")),
  // ZERO_HASH: ethers.ZeroHash,  // bytes32(0) — should be rejected
  // DIFFERENT_HASH: ethers.keccak256(ethers.toUtf8Bytes("different certificate")),
};

module.exports = {
  GAS_BUDGETS,
  CERT_UID_FORMAT,
  TEST_UIDS,
  TEST_HASHES,
};
```

Create `blockchain/test/helpers/fixtures.js` (structure only):

```javascript
// blockchain/test/helpers/fixtures.js
// Hardhat fixture functions for efficient test setup
// Uses loadFixture() from @nomicfoundation/hardhat-network-helpers
//
// WHY FIXTURES:
// Without fixtures: Deploy contract before EACH test (87 deployments = slow)
// With fixtures: Deploy once, snapshot state, restore per test (fast)
// loadFixture() handles snapshot/restore automatically
//
// These fixture functions will be populated in Sprint 2:

// deployRegistryFixture — populated in Sprint 2
// Returns: { contract, owner, university, student, employer, attacker }

// deployAndAuthorizeFixture — populated in Sprint 2
// Returns: { contract, owner, authorizedUniversity, ... }

// deployAndIssueFixture — populated in Sprint 2
// Returns: { contract, issuedCertificateUid, issuedCertificateHash, ... }

module.exports = {
  // Fixtures exported here in Sprint 2
};
```

## 9.4 Coverage Requirements

```
COVERAGE REQUIREMENTS — ENFORCEMENT STRATEGY
═════════════════════════════════════════════

TARGETS (from smart-contracts.md):
├── Statements: ≥ 95%
├── Branches:   ≥ 95%
├── Functions:  100%   ← Every function must be called in tests
└── Lines:      ≥ 95%

HOW TO VERIFY:
npm run test:coverage

Output will include:
┌──────────────────────────────┬──────────┬──────────┬────────┬──────────┐
│ File                         │ % Stmts  │ % Branch │ % Funcs│ % Lines  │
├──────────────────────────────┼──────────┼──────────┼────────┼──────────┤
│ contracts/                   │          │          │        │          │
│   CertificateRegistry.sol    │   97.83  │   95.45  │  100   │   97.83  │
└──────────────────────────────┴──────────┴──────────┴────────┴──────────┘

HOW TO IDENTIFY MISSING COVERAGE:
Open: coverage/index.html in browser
├── Red highlights: Uncovered lines
├── Yellow highlights: Partially covered branches
└── Green highlights: Fully covered

ACTION ON COVERAGE FAILURE:
If functions < 100%:
  Find the uncovered function in coverage/index.html
  Write a test case that calls that function
  Re-run npm run test:coverage

If branches < 95%:
  Find yellow-highlighted if/else branches
  Write tests for the uncovered branch paths
  Key: Every modifier has 2 branches (pass and fail)
       Every require() has 2 branches (success and revert)

COVERAGE OF MODIFIERS:
Each modifier test requires TWO test cases:
├── Test 1: Modifier passes → function executes
└── Test 2: Modifier fails → function reverts
Both test cases count toward branch coverage.
```

---

**[A — Why Required]** The test structure mirrors the three-category organization defined in the smart contract architecture (unit/integration/security). The helper files centralize test data to prevent "magic strings" in test files — a common source of hard-to-debug test failures. The `.solcover.js` configuration ensures interfaces are excluded from coverage measurement (they have no executable code).

**[B — Project Requirement Satisfied]** The three-category test structure satisfies the 87 test case requirement from the smart contract architecture. The `.mocharc.yml` 60-second timeout satisfies the requirement that tests handle multi-transaction blockchain operations without false timeouts. The coverage configuration satisfies the >95% coverage target.

**[C — Before Moving to Next Step]** Create all directories and placeholder files. Run `npm run test` and confirm it shows "0 tests passing" (not an error). Run `npm run test:coverage` and confirm it generates a `coverage/` directory (even with 0 tests, it runs). Do not proceed to deployment structure without these confirmations.

---

# SECTION 10: DEPLOYMENT SETUP STRUCTURE

## 10.1 Deployment Files Architecture

```
DEPLOYMENT STRUCTURE OVERVIEW
═══════════════════════════════

blockchain/deployments/
├── hardhat-local/
│   └── CertificateRegistry.json    ← Written by deploy.js (committed)
└── sepolia/
    └── CertificateRegistry.json    ← Written by deploy.js (committed)


DEPLOYMENT RECORD FORMAT:
────────────────────────────
Each CertificateRegistry.json follows this exact schema:

{
  "contractName": "CertificateRegistry",
  "network": "hardhat-local",
  "chainId": 31337,
  "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
  "transactionHash": "0xabc123...",
  "blockNumber": 1,
  "blockHash": "0xdef456...",
  "deployer": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
  "deployedAt": "2025-09-01T10:00:00.000Z",
  "solidityVersion": "0.8.19",
  "optimizerEnabled": true,
  "optimizerRuns": 200,
  "contractVersion": "1.0.0",
  "authorizedIssuers": [],
  "notes": "Initial deployment — Sprint 2"
}


WHY EACH FIELD:
├── contractName: Identifies which contract (repo may have multiple in future)
├── network: Human-readable network identifier
├── chainId: Machine-readable for programmatic network verification
├── address: Where to find the contract (primary consumer of this file)
├── transactionHash: Proof of deployment (verifiable on Etherscan)
├── blockNumber: Timestamp anchor for deployment
├── blockHash: Block verification reference
├── deployer: Which wallet deployed (for accountability)
├── deployedAt: ISO timestamp for deployment history
├── solidityVersion: Audit trail for compiler version used
├── optimizerEnabled/Runs: Audit trail for compilation settings
├── contractVersion: Manual version bump for tracking major changes
├── authorizedIssuers: Wallets authorized at deployment time (initially [])
└── notes: Deployment context for future developers


DEPLOYMENT RECORD GITIGNORE POLICY:
─────────────────────────────────────
deployments/ → COMMITTED TO GIT
artifacts/ → GITIGNORED

Why deployment records are committed:
├── Contract address is PUBLIC (on blockchain)
├── TX hash is PUBLIC (on blockchain)
├── No secrets in deployment records
├── Team-wide access to current contract address
└── Git history provides deployment audit trail
```

## 10.2 scripts/ Placeholder Files

Create placeholder script files in `blockchain/scripts/`:

```javascript
// blockchain/scripts/deploy.js
// Sprint 2 implementation
// Purpose: Deploy CertificateRegistry to target network
// Post-deployment: Write deployment record + distribute ABI
//
// Workflow:
// 1. Compile contract (if not already compiled)
// 2. Deploy CertificateRegistry
// 3. Wait for confirmations (6 on Sepolia, 1 on local)
// 4. Write deployment record to deployments/{network}/CertificateRegistry.json
// 5. Copy ABI to backend/blockchain/abi/CertificateRegistry.json
// 6. Generate frontend/blockchain/contractABI.js
// 7. Log all relevant information
//
// Implementation: Sprint 2
```

```javascript
// blockchain/scripts/authorize-issuer.js
// Sprint 2 implementation
// Purpose: Authorize a university wallet to issue certificates
//
// Usage: 
//   ISSUER_ADDRESS=0x... npm run authorize:localhost
//   ISSUER_ADDRESS=0x... npm run authorize:sepolia
//
// Workflow:
// 1. Load contract address from deployments/{network}/CertificateRegistry.json
// 2. Connect to contract as owner wallet
// 3. Call authorizeIssuer(ISSUER_ADDRESS)
// 4. Wait for transaction confirmation
// 5. Verify: call isAuthorizedIssuer(ISSUER_ADDRESS) → should return true
// 6. Log result
//
// Implementation: Sprint 2
```

```javascript
// blockchain/scripts/deauthorize-issuer.js
// Sprint 2 implementation
// Purpose: Remove a university wallet from authorized issuers
//
// Usage:
//   ISSUER_ADDRESS=0x... npm run deauthorize:sepolia
//
// Use case: University decommissioned, wallet compromised, or annual renewal
//
// Implementation: Sprint 2
```

```javascript
// blockchain/scripts/check-certificate.js
// Sprint 2 implementation
// Purpose: Query certificate status from command line
//
// Usage:
//   CERT_UID=MIT-2025-00001 npm run check:local
//   CERT_UID=MIT-2025-00001 npm run check:sepolia
//
// Output: Certificate record including hash, issuer, status, timestamps
//
// Implementation: Sprint 2
```

```javascript
// blockchain/scripts/transfer-ownership.js
// Sprint 2 implementation
// Purpose: Transfer contract ownership (emergency use)
//
// Usage:
//   NEW_OWNER=0x... npm run transfer:local
//   NEW_OWNER=0x... npm run transfer:sepolia
//
// Security: Requires confirmation prompt before executing
// Use case: Current owner wallet compromised; handoff to new team
//
// Implementation: Sprint 2
```

## 10.3 ABI Distribution Path Configuration

Create `blockchain/scripts/abi-config.js`:

```javascript
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
```

---

**[A — Why Required]** The deployment structure with committed records provides a team-wide single source of truth for contract addresses. The `abi-config.js` centralizes path configuration so that if the monorepo layout changes, only one file needs updating rather than every deployment script. Script placeholders with documented workflows enable Sprint 2 to begin immediately without structural confusion.

**[B — Project Requirement Satisfied]** The deployment records satisfy the implementation roadmap requirement: "Deployment record committed to deployments/{network}/." The `abi-config.js` satisfies the ABI synchronization strategy requirement from the architecture: ABI distributed to both backend and frontend upon deployment.

**[C — Before Moving to Next Step]** Verify all script placeholder files exist with `ls -la blockchain/scripts/`. Verify `abi-config.js` parses correctly: `node blockchain/scripts/abi-config.js` (it will output nothing but should not error). Verify the deployment directories exist: `ls -la blockchain/deployments/`.

---

# SECTION 11: ABI MANAGEMENT STRATEGY

## 11.1 ABI Lifecycle Documentation

```
ABI MANAGEMENT STRATEGY — COMPLETE
════════════════════════════════════

THE ABI IS THE MOST CRITICAL INTEGRATION POINT.
A stale ABI causes silent failures that waste hours of debugging.

ABI FLOW:
─────────

Solidity Source (CertificateRegistry.sol)
         │
         │ npm run compile
         ▼
artifacts/contracts/CertificateRegistry.sol/CertificateRegistry.json
         │
         │ deploy.js post-deployment step
         │ OR: scripts/copy-abi.sh (manual sync)
         ├──────────────────────────────────────────────┐
         ▼                                              ▼
backend/blockchain/abi/                  frontend/blockchain/
CertificateRegistry.json                contractABI.js
         │                                              │
         │ Python: web3.eth.contract(abi=ABI)           │ JS: new ethers.Contract(
         ▼                                              │    addr, ABI, signer)
blockchain_service.py                   transactions.js
(Read-only calls: verify, get, count)   (MetaMask: store, revoke)


THREE ABI COPIES:
──────────────────
Copy 1: blockchain/artifacts/ (Source — gitignored)
├── Generated by: npm run compile
├── Contains: Full artifact JSON (ABI + bytecode + metadata)
└── Never manually edit this file

Copy 2: backend/blockchain/abi/CertificateRegistry.json (committed)
├── Contains: Only the ABI array (extracted from artifacts)
├── Consumed by: blockchain_service.py via web3.eth.contract(abi=ABI)
└── Format: JSON array of function/event/error definitions

Copy 3: frontend/blockchain/contractABI.js (committed)
├── Contains: ABI as JavaScript export
├── Consumed by: transactions.js via new ethers.Contract(addr, ABI, signer)
└── Format:
    export const CONTRACT_ABI = [...];
    export const CONTRACT_VERSION = "1.0.0";


SYNC TRIGGERS — WHEN TO RUN ABI COPY:
──────────────────────────────────────
ALWAYS sync after:
├── Any change to contracts/CertificateRegistry.sol
├── Any change to contracts/interfaces/ICertificateRegistry.sol
└── Any Hardhat compiler version or optimizer change

NOT needed after:
├── Test file changes (test files don't affect ABI)
├── Script changes (deploy.js etc. don't affect ABI)
└── Configuration changes that don't affect compilation

AUTOMATED SYNC (via deploy.js):
Every deployment automatically copies the ABI.
This is the primary sync mechanism.

MANUAL SYNC (without redeployment):
When contract NatSpec or comments changed (ABI may not change)
but we want to ensure sync:
Use root-level: scripts/verify-abi-sync.sh (Sprint 1 setup)


ABI VALIDATION:
────────────────
Before distributing, deploy.js validates ABI contains required functions:

Required in ABI (from smart-contracts.md):
├── storeCertificate (nonpayable)
├── revokeCertificate (nonpayable)
├── verifyCertificate (view)
├── getCertificateRecord (view)
├── authorizeIssuer (nonpayable)
├── deauthorizeIssuer (nonpayable)
├── isAuthorizedIssuer (view)
├── getOwner (view)
├── getCertificateCount (view)
└── transferOwnership (nonpayable)

Required events in ABI:
├── CertificateStored
├── CertificateRevoked
├── IssuerAuthorized
├── IssuerDeauthorized
└── OwnershipTransferred

Required custom errors in ABI:
├── NotContractOwner
├── NotAuthorizedIssuer
├── NotOriginalIssuer
├── CertificateAlreadyExists
├── CertificateNotFound
├── CertificateAlreadyRevoked
├── InvalidCertificateHash
└── InvalidCertificateUid
    [... all 14 custom errors from smart-contracts.md]

If validation fails → deploy.js stops with descriptive error
"ABI validation failed: missing function 'storeCertificate'"
→ This means the contract is incomplete; do not distribute.


STALE ABI DETECTION:
─────────────────────
The root-level scripts/verify-abi-sync.sh (created in repo setup) checks:

1. Compute SHA-256 of ABI field in artifacts/
2. Compare with SHA-256 of backend/blockchain/abi/CertificateRegistry.json
3. Compare with ABI content in frontend/blockchain/contractABI.js
4. Output:
   "✅ All ABI copies are in sync"
   OR "❌ ABI mismatch detected in backend — run npm run deploy:localhost"
   OR "❌ ABI mismatch detected in frontend — run npm run deploy:localhost"

Run this check: Before starting backend or frontend development sessions
Incorporate into: npm run dev or startup scripts


BACKEND ABI CONSUMPTION (Web3.py):
────────────────────────────────────
In backend/blockchain/blockchain_service.py:

Contract initialization:
  with open("blockchain/abi/CertificateRegistry.json") as f:
    abi = json.load(f)  # Or abi = json.load(f)["abi"] if full artifact

  contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
  )

The ABI is loaded once at service initialization.
If ABI changes: Backend must be restarted to load new ABI.


FRONTEND ABI CONSUMPTION (ethers.js):
───────────────────────────────────────
In frontend/blockchain/transactions.js:

  import { CONTRACT_ABI } from './contractABI.js';
  import { CONTRACT_ADDRESS } from './contractAddress.js';

  const contract = new ethers.Contract(
    CONTRACT_ADDRESS,
    CONTRACT_ABI,
    signer  // MetaMask signer
  );

The ABI is a compile-time import (bundled by Vite).
If ABI changes: Vite dev server auto-reloads (hot module replacement).
```

## 11.2 contractAddress.js Template

Create `blockchain/scripts/address-config.js`:

```javascript
// blockchain/scripts/address-config.js
// Contract address configuration for different networks
// This file helps generate the frontend contractAddress.js
//
// The actual network detection happens in the frontend via:
//   const { chainId } = await provider.getNetwork()
//   CONTRACT_ADDRESSES[chainId]

// Network chain IDs
const CHAIN_IDS = {
  HARDHAT_LOCAL: 31337,
  SEPOLIA: 11155111,
  // MAINNET: 1  (post-MVP)
};

// Template for frontend/blockchain/contractAddress.js
// Generated by deploy.js — do not edit manually
const FRONTEND_ADDRESS_TEMPLATE = (network, address) => `
// frontend/blockchain/contractAddress.js
// AUTO-GENERATED by blockchain/scripts/deploy.js
// Do not edit manually — run npm run deploy:${network} to update
// Last updated: ${new Date().toISOString()}

export const CONTRACT_ADDRESSES = {
  [${CHAIN_IDS.HARDHAT_LOCAL}]: "${network === 'hardhat-local' ? address : '0x0000000000000000000000000000000000000000'}",
  [${CHAIN_IDS.SEPOLIA}]: "${network === 'sepolia' ? address : '0x0000000000000000000000000000000000000000'}",
};

export const SUPPORTED_CHAIN_IDS = [${CHAIN_IDS.HARDHAT_LOCAL}, ${CHAIN_IDS.SEPOLIA}];

export const getContractAddress = (chainId) => {
  const address = CONTRACT_ADDRESSES[chainId];
  if (!address || address === '0x0000000000000000000000000000000000000000') {
    throw new Error(\`No contract deployed on chain \${chainId}\`);
  }
  return address;
};
`;

module.exports = {
  CHAIN_IDS,
  FRONTEND_ADDRESS_TEMPLATE,
};
```

---

**[A — Why Required]** ABI management is the #1 source of integration bugs in blockchain applications. A developer who changes a function signature in the Solidity contract but forgets to update the ABI in the backend will spend hours debugging a "function not found" error that looks like a configuration issue. The automated sync via `deploy.js` and the `verify-abi-sync.sh` script eliminate this failure mode.

**[B — Project Requirement Satisfied]** Satisfies the architecture requirement: "ABI: blockchain/artifacts/ → backend/blockchain/abi/ + frontend/blockchain/contractABI.js" from the repository structure blueprint. The validation step satisfies the security requirement that the contract must be complete before deployment.

**[C — Before Moving to Next Step]** Verify `blockchain/scripts/abi-config.js` exists and contains correct relative paths. Verify the `deployments/` directory structure matches the expected format. Do not proceed until all script placeholder files are created and the paths are verified.

---

# SECTION 12: HARDHAT-SPECIFIC FILES

## 12.1 Solhint Configuration

Create `blockchain/.solhint.json`:

```json
{
  "extends": "solhint:recommended",
  "rules": {
    "compiler-version": ["error", "^0.8.19"],
    "avoid-suicide": "error",
    "avoid-throw": "error",
    "avoid-tx-origin": "error",
    "reentrancy": "error",
    "state-visibility": "error",
    "func-visibility": ["error", { "ignoreConstructors": false }],
    "no-empty-blocks": "warn",
    "no-unused-vars": "warn",
    "gas-custom-errors": "warn",
    "quotes": ["error", "double"],
    "const-name-snakecase": "error",
    "event-name-camelcase": "error",
    "func-name-mixedcase": "error",
    "modifier-name-mixedcase": "error",
    "var-name-mixedcase": "error",
    "contract-name-camelcase": "error",
    "imports-on-top": "error",
    "no-complex-fallback": "warn",
    "mark-callable-contracts": "off"
  }
}
```

## 12.2 Blockchain-Specific .gitignore

Create `blockchain/.gitignore`:

```gitignore
# =============================================================================
# blockchain/.gitignore
# Blockchain component-specific gitignore
# Global patterns are in root .gitignore
# This file handles Hardhat-specific generated files
# =============================================================================

# ─── Secrets ─────────────────────────────────────────────────────────────────
.env
*.pem
*.key
*_key.pem
*-key.pem

# ─── Hardhat Generated Files ──────────────────────────────────────────────────
artifacts/
cache/
coverage/
gas-report.txt

# ─── Chain State ──────────────────────────────────────────────────────────────
# Generated by: npm run node
cache/hardhat-network-database/

# ─── Dependencies ─────────────────────────────────────────────────────────────
node_modules/

# ─── Build Reports ────────────────────────────────────────────────────────────
coverage.json
.coverage_artifacts/
.coverage_cache/
.coverage_contracts/

# ─── IDE Files ────────────────────────────────────────────────────────────────
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# ─── NOT Gitignored (Committed) ───────────────────────────────────────────────
# deployments/ → Deployment records (committed — no secrets)
# .env.example → Environment template (committed — no secrets)
# package-lock.json → Locked versions (committed)
# hardhat.config.js → Configuration (committed — no secrets)
# test/ → All test files (committed)
# scripts/ → Deployment scripts (committed)
# contracts/ → Solidity source (committed)
```

## 12.3 blockchain/README.md

Create `blockchain/README.md`:

```markdown
# CertificateRegistry Smart Contract

Blockchain component of the Academic Credential Verification Platform.

## Overview

The `CertificateRegistry` contract provides immutable, trustless storage
of SHA-256 hashes for academic certificates on the Ethereum blockchain.

- **Network**: Hardhat Local (development) | Sepolia (staging)
- **Language**: Solidity ^0.8.19
- **Framework**: Hardhat 2.22.x

## Prerequisites

- Node.js >= 18.0.0 (v22 recommended)
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
npm run node        # Persistent state (survives restart)
npm run node:reset  # Fresh state
```

### Compile
```bash
npm run compile
```

### Test
```bash
npm run test              # All tests
npm run test:unit         # Unit tests only (fast)
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

## Contract Addresses

| Network       | Address                    |
|---------------|----------------------------|
| Hardhat Local | See deployments/hardhat-local/ |
| Sepolia       | See deployments/sepolia/   |

## Test Accounts (Local Development Only)

Account #0 (Deployer/Owner):
- Address: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`
- Private Key: `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`
- ⚠️ Public key — development only — never use on mainnet

## Gas Budgets

| Function            | Budget     |
|---------------------|------------|
| storeCertificate    | ≤ 110,000  |
| revokeCertificate   | ≤ 65,000   |
| authorizeIssuer     | ≤ 55,000   |
| verifyCertificate   | 0 (free)   |

## Architecture

See: `../docs/smart-contracts.md`
```

---

# SECTION 12 (CONTINUED): VERIFICATION CHECKLIST

## 12.4 Sprint 1 Blockchain Complete Verification

```
╔══════════════════════════════════════════════════════════════════════════════╗
║              SPRINT 1 BLOCKCHAIN SETUP — VERIFICATION CHECKLIST              ║
║     Verify every item before declaring Sprint 1 blockchain setup complete    ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════
PHASE 1: PREREQUISITES VERIFIED
═══════════════════════════════════════════════════════════════════
☐ Node.js version: node --version → v18.x.x or higher (v22 recommended)
☐ npm version: npm --version → v9.x.x or higher
☐ Git configured: git config user.name (returns a value)
☐ Chrome installed with MetaMask extension
☐ Infura or Alchemy account created
☐ Etherscan account created and API key obtained
☐ Sepolia ETH requested from at least 2 faucets

═══════════════════════════════════════════════════════════════════
PHASE 2: DIRECTORY STRUCTURE
═══════════════════════════════════════════════════════════════════
☐ blockchain/contracts/ exists
☐ blockchain/contracts/interfaces/ exists
☐ blockchain/scripts/ exists
☐ blockchain/test/unit/ exists
☐ blockchain/test/integration/ exists
☐ blockchain/test/security/ exists
☐ blockchain/test/helpers/ exists
☐ blockchain/deployments/hardhat-local/ exists
☐ blockchain/deployments/sepolia/ exists
☐ blockchain/ignition/modules/ exists

Verify: find blockchain -type d | sort
Expected: 12 directories total (per Section 1.1 layout)

═══════════════════════════════════════════════════════════════════
PHASE 3: npm PACKAGES
═══════════════════════════════════════════════════════════════════
☐ package.json contains "private": true
☐ package.json contains "engines": { "node": ">=18.0.0" }
☐ All 26 npm scripts defined per Section 4
☐ Only 5 devDependencies (hardhat, hardhat-toolbox, cross-env, dotenv, solhint)
☐ dependencies section is ABSENT or EMPTY
☐ npm install completed without errors
☐ package-lock.json exists

Verify: npm list --depth=0
Expected: 5 packages (hardhat, @nomicfoundation/hardhat-toolbox, cross-env, dotenv, solhint)

Verify: npm audit
Expected: 0 high-severity vulnerabilities

═══════════════════════════════════════════════════════════════════
PHASE 4: HARDHAT CONFIGURATION
═══════════════════════════════════════════════════════════════════
☐ hardhat.config.js exists (standard CommonJS)
☐ Solidity version: exactly "0.8.19"
☐ optimizer.enabled: true
☐ optimizer.runs: 200
☐ viaIR: false (explicitly set)
☐ hardhat network chainId: 31337
☐ hardhat network mining.auto: true
☐ localhost network configured
☐ sepolia network chainId: 11155111
☐ sepolia network gasMultiplier: 1.2
☐ sepolia network gasMultiplier: 1.2
☐ gasReporter.enabled: conditional on REPORT_GAS env var
☐ etherscan.apiKey configured
☐ mocha.timeout: 60000

Verify: npx hardhat compile
Expected: exits code 0, "Nothing to compile" (no contracts yet)

Verify: npx hardhat --version
Expected: 2.22.x

═══════════════════════════════════════════════════════════════════
PHASE 5: ENVIRONMENT VARIABLES
═══════════════════════════════════════════════════════════════════
☐ blockchain/.env exists (locally)
☐ blockchain/.env.example exists and is committed
☐ .env.example has 7 variable definitions (3 required, 4 optional)
☐ blockchain/.env has DEPLOYER_PRIVATE_KEY set (dev key for local)
☐ blockchain/.env has SEPOLIA_RPC_URL set (your actual Infura/Alchemy URL)
☐ blockchain/.env has ETHERSCAN_API_KEY set (your actual key)

Security verification:
☐ git ls-files blockchain/ | grep "\.env$" → returns NOTHING
☐ git ls-files blockchain/ | grep "\.env\.example" → returns .env.example
☐ grep -r "DEPLOYER_PRIVATE_KEY=" blockchain/ --include="*.js" --include="*.json" → returns NOTHING (only in .env)
☐ cat blockchain/.env | grep PRIVATE_KEY shows actual key value (file exists locally)

═══════════════════════════════════════════════════════════════════
PHASE 6: HARDHAT NODE FUNCTIONALITY
═══════════════════════════════════════════════════════════════════
Start node in separate terminal: npm run node

☐ Node starts without errors
☐ Binds to: http://127.0.0.1:8545/ (not 0.0.0.0)
☐ Shows 20 accounts with 10,000 ETH each
☐ Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

MetaMask verification (with node running):
☐ MetaMask: Add Network → Hardhat Local (chainId 31337, RPC 127.0.0.1:8545)
☐ MetaMask: Import Account #0 → Shows 10,000 ETH

Stop node: Ctrl+C in Terminal 1

═══════════════════════════════════════════════════════════════════
PHASE 7: TESTING INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════
☐ blockchain/test/.mocharc.yml exists with timeout: 60000
☐ blockchain/.solcover.js exists
☐ blockchain/test/helpers/constants.js exists
☐ blockchain/test/helpers/fixtures.js exists
☐ blockchain/test/helpers/utils.js exists

Verify: npm run test
Expected: exits code 0
Acceptable: "No test files found" or "0 passing"
NOT acceptable: Any error or crash

Verify: npm run test:coverage
Expected: Creates coverage/ directory (even empty)
Acceptable: May show 0% coverage (no contracts yet)
NOT acceptable: Error or crash

☐ coverage/ directory created by test:coverage run
☐ coverage/ is gitignored: git ls-files coverage/ → NOTHING

═══════════════════════════════════════════════════════════════════
PHASE 8: SCRIPT PLACEHOLDERS
═══════════════════════════════════════════════════════════════════
☐ blockchain/scripts/deploy.js exists (with documentation comments)
☐ blockchain/scripts/authorize-issuer.js exists
☐ blockchain/scripts/deauthorize-issuer.js exists
☐ blockchain/scripts/check-certificate.js exists
☐ blockchain/scripts/transfer-ownership.js exists
☐ blockchain/scripts/abi-config.js exists with correct paths
☐ blockchain/scripts/address-config.js exists

Verify abi-config.js paths are correct:
node -e "const c = require('./scripts/abi-config.js'); console.log(c.ABI_SOURCE)"
Expected: Absolute path ending in:
.../blockchain/artifacts/contracts/CertificateRegistry.sol/CertificateRegistry.json

node -e "const c = require('./scripts/abi-config.js'); console.log(c.BACKEND_ABI_DEST)"
Expected: Absolute path ending in:
.../backend/blockchain/abi/CertificateRegistry.json

node -e "const c = require('./scripts/abi-config.js'); console.log(c.FRONTEND_ABI_DEST)"
Expected: Absolute path ending in:
.../frontend/blockchain/contractABI.js

═══════════════════════════════════════════════════════════════════
PHASE 9: DEPLOYMENT STRUCTURE
═══════════════════════════════════════════════════════════════════
☐ blockchain/deployments/hardhat-local/ exists and is committed
☐ blockchain/deployments/sepolia/ exists and is committed
☐ artifacts/ is gitignored: git ls-files artifacts/ → NOTHING

Verify deployment directories are tracked:
git ls-files blockchain/deployments/
Expected: Shows both directories (even if empty — may need .gitkeep)

☐ .gitkeep files added to keep empty directories:
  touch blockchain/deployments/hardhat-local/.gitkeep
  touch blockchain/deployments/sepolia/.gitkeep
  git add blockchain/deployments/

═══════════════════════════════════════════════════════════════════
PHASE 10: CONFIGURATION FILES
═══════════════════════════════════════════════════════════════════
☐ blockchain/.solhint.json exists with avoid-tx-origin: error rule
☐ blockchain/.gitignore exists with artifacts/, cache/, .env listed
☐ blockchain/README.md exists with setup instructions

Verify solhint works (no contracts yet — should show "no files"):
npm run lint
Expected: No errors (nothing to lint yet)

═══════════════════════════════════════════════════════════════════
PHASE 11: SEPOLIA CONNECTIVITY (if configured)
═══════════════════════════════════════════════════════════════════
☐ SEPOLIA_RPC_URL is a real endpoint (not placeholder)
☐ Sepolia connection test passes (Section 8, Phase 4 command)
☐ Deployer balance shows ≥ 0.1 Sepolia ETH (request more if not)

═══════════════════════════════════════════════════════════════════
PHASE 12: COMPLETE FUNCTIONAL VERIFICATION
═══════════════════════════════════════════════════════════════════
Run each command and verify exit code 0:

☐ npm run compile → "Nothing to compile"
☐ npm run test → "0 passing" or "No test files found"
☐ npm run test:coverage → creates coverage/ directory
☐ npm run lint → No errors (nothing to lint)
☐ npm audit → 0 high-severity vulnerabilities
☐ npx hardhat node → Node starts (Ctrl+C to stop)
☐ npx hardhat --version → Shows 3.x.x

═══════════════════════════════════════════════════════════════════
SPRINT 1 COMPLETION DECLARATION
═══════════════════════════════════════════════════════════════════

☐ ALL 60+ checklist items above are verified
☐ No secrets committed to Git (verified by git ls-files checks)
☐ All commands exit with code 0
☐ Directory structure matches Section 1 layout exactly
☐ package-lock.json committed to Git

─────────────────────────────────────────────────────────────────
SPRINT 1 BLOCKCHAIN SETUP STATUS:

  ☐ INCOMPLETE — Return to failed phase above
  ☐ COMPLETE — Ready for Sprint 2 (CertificateRegistry.sol development)
─────────────────────────────────────────────────────────────────
```

---

**[A — Why Required]** The verification checklist is the completion gate for Sprint 1. Without systematic verification, subtle issues (wrong Node version, missing gitignore entries, incorrect abi-config.js paths) surface during Sprint 2 as mysterious failures that waste hours to debug.

**[B — Project Requirement Satisfied]** Satisfies the sprint completion criteria from the implementation roadmap: "All development environments configured", "Contract deploys to local Hardhat", and "ABI distributed to backend and frontend."

**[C — Before Moving to Next Step]** Every checkbox in the verification checklist must be checked. Run the functional verification commands in sequence. Do not begin Sprint 2 (CertificateRegistry.sol development) until all 12 phases are verified complete. The smart contract implementation requires a fully configured, verified development environment to be productive.

---

# FINAL SUMMARY

## Sprint 1 Blockchain Setup — What Was Accomplished

```
SPRINT 1 BLOCKCHAIN SETUP SUMMARY
════════════════════════════════════

ENVIRONMENT ESTABLISHED:
├── Node.js 18+ requirement verified (using Node.js 22)
├── Hardhat 2.22.x installed and configured
├── 5 development packages installed (minimal footprint)
├── CommonJS configuration (hardhat.config.js)
└── Mocha test runner configured (60s timeout)

DIRECTORY STRUCTURE CREATED:
├── contracts/ + interfaces/ (Sprint 2 ready)
├── test/unit/ + integration/ + security/ (Sprint 2 ready)
├── test/helpers/ + placeholder files
├── scripts/ + 7 script files (Sprint 2 implementations)
├── deployments/hardhat-local/ + sepolia/
└── ignition/modules/ (available but not primary workflow)

CONFIGURATION COMPLETE:
├── hardhat.config.js (full specification per architecture)
├── .env + .env.example (6 variables documented)
├── .solhint.json (security rules including avoid-tx-origin)
├── .gitignore (blockchain-specific exclusions)
├── .solcover.js (interface files excluded from coverage)
└── .mocharc.yml (60s timeout, spec reporter)

WORKFLOW DOCUMENTED:
├── Local development: 2-terminal workflow
├── Chain state management (resets on node restart)
├── MetaMask setup instructions
├── Sepolia preparation (ETH, RPC, Etherscan)
└── ABI sync strategy (automated via deploy.js)

SECURITY VERIFIED:
├── No secrets in any committed file
├── .env gitignored and confirmed
├── Deployment wallet separation (dev vs staging)
└── Solhint rules prevent tx.origin usage

READY FOR:
Sprint 2 — CertificateRegistry.sol Development
├── Write failing tests first (TDD)
├── Implement contract functions
├── Achieve >95% coverage
└── Verify gas budgets
```

---

> **This Hardhat Project Setup Implementation Guide is complete. All configuration decisions are derived from the approved smart-contracts.md architecture, the repository-structure.md blueprint, and the project-rules.md constraints. No Solidity implementation code has been generated. Sprint 2 (CertificateRegistry.sol development) begins when all verification checklist items are confirmed complete.**