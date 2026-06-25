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
