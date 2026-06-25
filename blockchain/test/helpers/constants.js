// blockchain/test/helpers/constants.js
// Test constants — populated in Sprint 2 during contract development
// Purpose: Centralize test data to avoid magic strings in test files

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
// These require ethers.js which is available at test runtime
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
