// blockchain/scripts/authorize-issuer.js
// Authorize a university wallet to issue certificates on-chain.
//
// Usage:
//   ISSUER_ADDRESS=0x<wallet> npm run authorize:local
//   ISSUER_ADDRESS=0x<wallet> npm run authorize:localhost
//   ISSUER_ADDRESS=0x<wallet> npm run authorize:sepolia
//
// Workflow:
//   1. Load deployment record from deployments/{network}/CertificateRegistry.json
//   2. Connect to deployed contract as owner (account #0 for local networks)
//   3. Check if wallet is already authorized
//   4. Call authorizeIssuer(ISSUER_ADDRESS) — only succeeds from owner account
//   5. Wait for transaction confirmation
//   6. Verify: call isAuthorizedIssuer(ISSUER_ADDRESS) → must return true
//   7. Print result

const { ethers, network } = require("hardhat");
const fs = require("fs");
const path = require("path");

const { DEPLOYMENTS_DIR } = require("./abi-config");

// Network → deployment subfolder mapping (same as deploy.js)
const NETWORK_FOLDER = {
  hardhat: "hardhat-local",
  localhost: "hardhat-local",
  sepolia: "sepolia",
};

async function main() {
  const networkName = network.name;
  const chainId = (await ethers.provider.getNetwork()).chainId;

  console.log("=".repeat(60));
  console.log("  Authorize Certificate Issuer");
  console.log("=".repeat(60));
  console.log(`  Network  : ${networkName}`);
  console.log(`  Chain ID : ${chainId}`);
  console.log("");

  // ── Read ISSUER_ADDRESS from environment ──────────────────────────────────
  const issuerAddress = process.env.ISSUER_ADDRESS;
  if (!issuerAddress) {
    throw new Error(
      "ISSUER_ADDRESS environment variable is required.\n" +
      "Usage: ISSUER_ADDRESS=0x<wallet> npm run authorize:local"
    );
  }

  // Validate it's a plausible Ethereum address
  if (!issuerAddress.match(/^0x[0-9a-fA-F]{40}$/)) {
    throw new Error(`Invalid ISSUER_ADDRESS: "${issuerAddress}" (must be 0x + 40 hex chars)`);
  }

  const checksummedIssuer = ethers.getAddress(issuerAddress);
  console.log(`  Issuer address: ${checksummedIssuer}`);
  console.log("");

  // ── Load deployment record ────────────────────────────────────────────────
  console.log("[1/5] Loading deployment record...");

  const folderKey = NETWORK_FOLDER[networkName] || networkName;
  const recordPath = path.join(DEPLOYMENTS_DIR, folderKey, "CertificateRegistry.json");

  if (!fs.existsSync(recordPath)) {
    throw new Error(
      `Deployment record not found: ${recordPath}\n` +
      `Deploy the contract first: npm run deploy:local`
    );
  }

  const record = JSON.parse(fs.readFileSync(recordPath, "utf8"));
  const contractAddress = record.address;

  console.log(`      Contract address: ${contractAddress}`);
  console.log(`      Deployed at     : ${record.deployedAt}`);

  // ── Connect to contract ───────────────────────────────────────────────────
  console.log("[2/5] Connecting to contract...");

  const [owner] = await ethers.getSigners();
  console.log(`      Using owner account: ${owner.address}`);

  const contract = await ethers.getContractAt("CertificateRegistry", contractAddress, owner);

  // Verify caller is actually the owner
  const onChainOwner = await contract.getOwner();
  if (onChainOwner.toLowerCase() !== owner.address.toLowerCase()) {
    throw new Error(
      `Account mismatch!\n` +
      `  On-chain owner: ${onChainOwner}\n` +
      `  Current signer: ${owner.address}\n` +
      `Only the owner can authorize issuers.`
    );
  }
  console.log(`      On-chain owner verified: ${onChainOwner}`);

  // ── Check if already authorized ───────────────────────────────────────────
  console.log("[3/5] Checking current authorization status...");

  const alreadyAuthorized = await contract.isAuthorizedIssuer(checksummedIssuer);
  if (alreadyAuthorized) {
    console.log(`      Status: ALREADY AUTHORIZED — nothing to do.`);
    console.log("");
    console.log("=".repeat(60));
    console.log(`  ${checksummedIssuer}`);
    console.log("  is already an authorized issuer. No transaction sent.");
    console.log("=".repeat(60));
    return;
  }
  console.log(`      Status: NOT authorized — proceeding to authorize.`);

  // ── Call authorizeIssuer() ────────────────────────────────────────────────
  console.log("[4/5] Sending authorizeIssuer() transaction...");

  const tx = await contract.authorizeIssuer(checksummedIssuer);
  console.log(`      TX Hash: ${tx.hash}`);
  console.log(`      Waiting for confirmation...`);

  const receipt = await tx.wait(1);
  console.log(`      Confirmed in block: ${receipt.blockNumber}`);
  console.log(`      Gas used          : ${receipt.gasUsed.toString()}`);

  // ── Verify authorization on-chain ─────────────────────────────────────────
  console.log("[5/5] Verifying authorization on-chain...");

  const isNowAuthorized = await contract.isAuthorizedIssuer(checksummedIssuer);

  if (!isNowAuthorized) {
    throw new Error(
      `Authorization verification FAILED — isAuthorizedIssuer() returned false ` +
      `after the transaction was confirmed. This is unexpected.`
    );
  }

  console.log(`      isAuthorizedIssuer(${checksummedIssuer}) = ${isNowAuthorized}`);

  // ── Summary ───────────────────────────────────────────────────────────────
  console.log("");
  console.log("=".repeat(60));
  console.log("  Authorization COMPLETE");
  console.log("=".repeat(60));
  console.log(`  Issuer   : ${checksummedIssuer}`);
  console.log(`  Contract : ${contractAddress}`);
  console.log(`  TX Hash  : ${tx.hash}`);
  console.log(`  Block    : ${receipt.blockNumber}`);
  console.log(`  Verified : isAuthorizedIssuer() = true`);
  console.log("=".repeat(60));
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error("\n[AUTHORIZE FAILED]", err.message || err);
    process.exit(1);
  });
