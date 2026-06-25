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
// Usage:
//   npm run deploy:local       (in-process Hardhat Network)
//   npm run deploy:localhost   (running node via npm run node)
//   npm run deploy:sepolia     (Sepolia testnet — requires .env credentials)
//
// Implementation: Sprint 2
