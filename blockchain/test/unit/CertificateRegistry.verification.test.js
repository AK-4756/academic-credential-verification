// blockchain/test/unit/CertificateRegistry.verification.test.js
// Unit Tests: Certificate Verification — TC-VR-01 through TC-VR-15
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("CertificateRegistry — Certificate Verification", function () {

  // ── Test Data ───────────────────────────────────────────────────────────────
  const CERT_UID = "TESTUNIV-2025-00001";
  const MIN_UID = "A";

  let VALID_HASH, DIFFERENT_HASH;
  before(function () {
    VALID_HASH = ethers.keccak256(ethers.toUtf8Bytes("sample certificate"));
    DIFFERENT_HASH = ethers.keccak256(ethers.toUtf8Bytes("different certificate"));
  });

  // ── Fixtures ────────────────────────────────────────────────────────────────
  async function deployAndIssueFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);

    const certHash = ethers.keccak256(ethers.toUtf8Bytes("sample certificate"));
    await contract.connect(univ1).storeCertificate(CERT_UID, certHash);

    return { contract, owner, univ1, univ2, student, employer, attacker, certHash };
  }

  async function deployIssueAndRevokeFixture() {
    const result = await deployAndIssueFixture();
    const tx = await result.contract.connect(result.univ1).revokeCertificate(CERT_UID);
    const receipt = await tx.wait();
    const block = await ethers.provider.getBlock(receipt.blockNumber);
    return { ...result, revokedAt: block.timestamp };
  }

  // ── verifyCertificate() ─────────────────────────────────────────────────────
  describe("verifyCertificate()", function () {
    it("TC-VR-01: returns (true, ACTIVE) for exact hash match on active cert", async function () {
      const { contract, certHash } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.verifyCertificate(CERT_UID, certHash);
      expect(isValid).to.be.true;
      expect(status).to.equal(0n); // ACTIVE
    });

    it("TC-VR-02: returns (false, ACTIVE) for hash mismatch on active cert", async function () {
      const { contract } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.verifyCertificate(CERT_UID, DIFFERENT_HASH);
      expect(isValid).to.be.false;
      expect(status).to.equal(0n); // ACTIVE
    });

    it("TC-VR-03: returns (false, REVOKED) for matching hash on revoked cert", async function () {
      const { contract, certHash } = await loadFixture(deployIssueAndRevokeFixture);
      const [isValid, status] = await contract.verifyCertificate(CERT_UID, certHash);
      expect(isValid).to.be.false;
      expect(status).to.equal(1n); // REVOKED
    });

    it("TC-VR-04: returns (false, REVOKED) for non-matching hash on revoked cert", async function () {
      const { contract } = await loadFixture(deployIssueAndRevokeFixture);
      const [isValid, status] = await contract.verifyCertificate(CERT_UID, DIFFERENT_HASH);
      expect(isValid).to.be.false;
      expect(status).to.equal(1n); // REVOKED
    });

    it("TC-VR-05: returns (false, ACTIVE) for non-existent cert uid", async function () {
      const { contract, certHash } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.verifyCertificate("NONEXIST-UID", certHash);
      expect(isValid).to.be.false;
      expect(status).to.equal(0n); // ACTIVE (default)
    });

    it("TC-VR-06: can be called by any address (unauthorized caller)", async function () {
      const { contract, certHash, attacker } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.connect(attacker).verifyCertificate(CERT_UID, certHash);
      expect(isValid).to.be.true;
      expect(status).to.equal(0n);
    });

    it("TC-VR-07: can be called by any signer (view function accessibility)", async function () {
      const { contract, certHash, student } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.connect(student).verifyCertificate(CERT_UID, certHash);
      expect(isValid).to.be.true;
      expect(status).to.equal(0n);
    });

    it("TC-VR-08: returns correct result for minimum-length uid (1 char)", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const minHash = ethers.keccak256(ethers.toUtf8Bytes("min uid cert"));
      await contract.connect(univ1).storeCertificate(MIN_UID, minHash);
      const [isValid, status] = await contract.verifyCertificate(MIN_UID, minHash);
      expect(isValid).to.be.true;
      expect(status).to.equal(0n);
    });

    it("TC-VR-09: with submitted bytes32(0) returns (false, ACTIVE)", async function () {
      const { contract } = await loadFixture(deployAndIssueFixture);
      const [isValid, status] = await contract.verifyCertificate(CERT_UID, ethers.ZeroHash);
      expect(isValid).to.be.false;
      expect(status).to.equal(0n);
    });

    it("TC-VR-10: multiple verifications do not alter state", async function () {
      const { contract, certHash } = await loadFixture(deployAndIssueFixture);
      const countBefore = await contract.getCertificateCount();
      await contract.verifyCertificate(CERT_UID, certHash);
      await contract.verifyCertificate(CERT_UID, certHash);
      await contract.verifyCertificate(CERT_UID, certHash);
      const countAfter = await contract.getCertificateCount();
      expect(countAfter).to.equal(countBefore);
    });
  });

  // ── getCertificateRecord() ──────────────────────────────────────────────────
  describe("getCertificateRecord()", function () {
    it("TC-VR-11: returns correct full struct for existing cert", async function () {
      const { contract, certHash, univ1 } = await loadFixture(deployAndIssueFixture);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.certificateHash).to.equal(certHash);
      expect(record.issuingUniversity).to.equal(univ1.address);
      expect(record.status).to.equal(0n);
      expect(record.exists).to.be.true;
      expect(record.issuedAt).to.be.greaterThan(0n);
      expect(record.revokedAt).to.equal(0n);
    });

    it("TC-VR-12: returns exists=false for non-existent cert", async function () {
      const { contract } = await loadFixture(deployAndIssueFixture);
      const record = await contract.getCertificateRecord("FAKE-UID");
      expect(record.exists).to.be.false;
    });

    it("TC-VR-13: shows REVOKED status after revocation", async function () {
      const { contract } = await loadFixture(deployIssueAndRevokeFixture);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.status).to.equal(1n); // REVOKED
    });

    it("TC-VR-14: shows revokedAt timestamp after revocation", async function () {
      const { contract, revokedAt } = await loadFixture(deployIssueAndRevokeFixture);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.revokedAt).to.equal(revokedAt);
    });

    it("TC-VR-15: issuingUniversity matches original issuer", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.issuingUniversity).to.equal(univ1.address);
    });
  });
});
