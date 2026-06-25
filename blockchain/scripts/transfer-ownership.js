// blockchain/scripts/transfer-ownership.js
// Sprint 2 implementation
// Purpose: Transfer contract ownership (emergency use)
//
// Usage:
//   NEW_OWNER=0x... npm run transfer:local
//   NEW_OWNER=0x... npm run transfer:sepolia
//
// Workflow:
// 1. Load contract address from deployments/{network}/CertificateRegistry.json
// 2. Connect to contract as current owner wallet
// 3. Display current owner address
// 4. Display new owner address (NEW_OWNER env var)
// 5. Prompt for confirmation (safety check)
// 6. Call transferOwnership(NEW_OWNER)
// 7. Wait for transaction confirmation
// 8. Verify: call getOwner() → should return NEW_OWNER
// 9. Log result
//
// Security: Requires confirmation prompt before executing
// Use case: Current owner wallet compromised; handoff to new team
//
// Implementation: Sprint 2
