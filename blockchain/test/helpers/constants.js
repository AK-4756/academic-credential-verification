// blockchain/test/helpers/constants.js
// Test constants — populated during Sprint 3 (Contract Testing)
// Purpose: Centralize test data to avoid magic strings in test files

// GAS BUDGETS (from smart-contracts.md)
const GAS_BUDGETS = {
  storeCertificate: 110_000,    // Maximum acceptable gas
  revokeCertificate: 65_000,
  authorizeIssuer: 55_000,
  deauthorizeIssuer: 35_000,
  verifyCertificate: 0,          // View function — zero gas cost
};

// SAMPLE TEST UIDS
const TEST_UIDS = {
  VALID_UID: "TESTUNIV-2025-00001",
  DUPLICATE_UID: "TESTUNIV-2025-00001",   // same as VALID_UID — for duplicate tests
  SECOND_UID: "TESTUNIV-2025-00002",
  THIRD_UID: "OTHERUNIV-2025-00001",
  EMPTY_UID: "",
  OVERSIZED_UID: "A".repeat(51),          // 51 chars — exceeds max 50
  BOUNDARY_UID: "A".repeat(50),           // exactly 50 chars — boundary
  MIN_UID: "A",                           // 1 char — minimum valid
};

module.exports = {
  GAS_BUDGETS,
  TEST_UIDS,
};
