// blockchain/test/integration/VerificationFlow.test.js
// Integration Tests: Verification Flow — IT-VF-01 through IT-VF-05
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Integration — Verification Flow", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndIssueFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);

    const certUid = "MIT-2025-00001";
    const certHash = ethers.keccak256(ethers.toUtf8Bytes("original diploma PDF bytes"));
    await contract.connect(univ1).storeCertificate(certUid, certHash);

    return { contract, owner, univ1, univ2, student, employer, attacker, certUid, certHash };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("IT-VF-01: AUTHENTIC path — exact hash match, active certificate", async function () {
    const { contract, certUid, certHash } = await loadFixture(deployAndIssueFixture);
    const [isValid, status] = await contract.verifyCertificate(certUid, certHash);
    expect(isValid).to.be.true;
    expect(status).to.equal(0n); // ACTIVE
  });

  it("IT-VF-02: TAMPERED path — single char difference in hash content", async function () {
    const { contract, certUid } = await loadFixture(deployAndIssueFixture);
    // Original: "original diploma PDF bytes" — Tampered: single char change
    const tamperedHash = ethers.keccak256(ethers.toUtf8Bytes("original diploma PDF byteS"));
    const [isValid, status] = await contract.verifyCertificate(certUid, tamperedHash);
    expect(isValid).to.be.false;
    expect(status).to.equal(0n); // ACTIVE (cert exists but hash mismatch)
  });

  it("IT-VF-03: REVOKED path — verify after revocation with matching hash", async function () {
    const { contract, univ1, certUid, certHash } = await loadFixture(deployAndIssueFixture);
    await contract.connect(univ1).revokeCertificate(certUid);
    const [isValid, status] = await contract.verifyCertificate(certUid, certHash);
    expect(isValid).to.be.false;
    expect(status).to.equal(1n); // REVOKED
  });

  it("IT-VF-04: NOT_FOUND path — certificate uid never stored", async function () {
    const { contract } = await loadFixture(deployAndIssueFixture);
    const unknownHash = ethers.keccak256(ethers.toUtf8Bytes("unknown cert"));
    const [isValid, status] = await contract.verifyCertificate("NEVER-STORED-UID", unknownHash);
    expect(isValid).to.be.false;
    expect(status).to.equal(0n); // ACTIVE (default for non-existent)
  });

  it("IT-VF-05: Verify before and after revocation — confirm state change", async function () {
    const { contract, univ1, certUid, certHash } = await loadFixture(deployAndIssueFixture);

    // Before revocation: AUTHENTIC
    const [validBefore, statusBefore] = await contract.verifyCertificate(certUid, certHash);
    expect(validBefore).to.be.true;
    expect(statusBefore).to.equal(0n);

    // Revoke
    await contract.connect(univ1).revokeCertificate(certUid);

    // After revocation: REVOKED
    const [validAfter, statusAfter] = await contract.verifyCertificate(certUid, certHash);
    expect(validAfter).to.be.false;
    expect(statusAfter).to.equal(1n);
  });
});
