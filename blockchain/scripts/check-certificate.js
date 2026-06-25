// blockchain/scripts/check-certificate.js
// Sprint 2 implementation
// Purpose: Query certificate status from command line
//
// Usage:
//   CERT_UID=MIT-2025-00001 npm run check:local
//   CERT_UID=MIT-2025-00001 npm run check:sepolia
//
// Workflow:
// 1. Load contract address from deployments/{network}/CertificateRegistry.json
// 2. Connect to contract (read-only, no signing required)
// 3. Call getCertificateRecord(CERT_UID)
// 4. Display: hash, issuer address, timestamp, revocation status
// 5. Call verifyCertificate(CERT_UID, hash) for verification status
//
// Output: Certificate record including hash, issuer, status, timestamps
//
// Implementation: Sprint 2
