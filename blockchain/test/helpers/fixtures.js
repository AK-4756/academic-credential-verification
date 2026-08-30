// blockchain/test/helpers/fixtures.js
// Hardhat fixture functions for efficient test setup
// Uses loadFixture() from @nomicfoundation/hardhat-network-helpers
const { ethers } = require("hardhat");

// ── Fixture 1: Fresh Deployment ──────────────────────────────────────────────
// Returns a freshly deployed contract with named signers
async function deployRegistryFixture() {
  const [owner, univ1, univ2, student, employer, attacker] =
    await ethers.getSigners();

  const Factory = await ethers.getContractFactory("CertificateRegistry");
  const contract = await Factory.deploy();

  return { contract, owner, univ1, univ2, student, employer, attacker };
}

// ── Fixture 2: Deployed + Authorized Issuers ─────────────────────────────────
// univ1 and univ2 are authorized issuers
async function deployAndAuthorizeFixture() {
  const { contract, owner, univ1, univ2, student, employer, attacker } =
    await deployRegistryFixture();

  await contract.authorizeIssuer(univ1.address);
  await contract.authorizeIssuer(univ2.address);

  return { contract, owner, univ1, univ2, student, employer, attacker };
}

// ── Fixture 3: Deployed + Authorized + One Certificate Issued ────────────────
// univ1 has issued TESTUNIV-2025-00001
async function deployAndIssueFixture() {
  const { contract, owner, univ1, univ2, student, employer, attacker } =
    await deployAndAuthorizeFixture();

  const certUid = "TESTUNIV-2025-00001";
  const certHash = ethers.keccak256(ethers.toUtf8Bytes("sample certificate pdf content"));

  const tx = await contract.connect(univ1).storeCertificate(certUid, certHash);
  const receipt = await tx.wait();
  const block = await ethers.provider.getBlock(receipt.blockNumber);

  return {
    contract, owner, univ1, univ2, student, employer, attacker,
    certUid, certHash, issuedAt: block.timestamp,
  };
}

module.exports = {
  deployRegistryFixture,
  deployAndAuthorizeFixture,
  deployAndIssueFixture,
};
