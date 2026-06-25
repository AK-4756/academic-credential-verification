// blockchain/scripts/deauthorize-issuer.js
// Sprint 2 implementation
// Purpose: Remove a university wallet from authorized issuers
//
// Usage:
//   ISSUER_ADDRESS=0x... npm run deauthorize:local
//   ISSUER_ADDRESS=0x... npm run deauthorize:sepolia
//
// Use case: University decommissioned, wallet compromised, or annual renewal
//
// Workflow:
// 1. Load contract address from deployments/{network}/CertificateRegistry.json
// 2. Connect to contract as owner wallet
// 3. Call deauthorizeIssuer(ISSUER_ADDRESS)
// 4. Wait for transaction confirmation
// 5. Verify: call isAuthorizedIssuer(ISSUER_ADDRESS) → should return false
// 6. Log result
//
// Implementation: Sprint 2
