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
