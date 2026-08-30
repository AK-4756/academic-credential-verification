// blockchain/test/unit/CertificateRegistry.revocation.test.js
// Unit Tests: Certificate Revocation — TC-RV-01 through TC-RV-15
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("CertificateRegistry — Certificate Revocation", function () {

  // ── Test Data ───────────────────────────────────────────────────────────────
  const CERT_UID = "TESTUNIV-2025-00001";

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndIssueFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);

    const certHash = ethers.keccak256(ethers.toUtf8Bytes("sample certificate"));
    const tx = await contract.connect(univ1).storeCertificate(CERT_UID, certHash);
    const receipt = await tx.wait();
    const block = await ethers.provider.getBlock(receipt.blockNumber);

    return {
      contract, owner, univ1, univ2, student, employer, attacker,
      certHash, issuedAt: block.timestamp,
    };
  }

  // ── Success Path ────────────────────────────────────────────────────────────
  describe("Success Path", function () {
    it("TC-RV-01: revokeCertificate() succeeds for original issuer on active certificate", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      await expect(
        contract.connect(univ1).revokeCertificate(CERT_UID)
      ).to.not.be.reverted;
    });

    it("TC-RV-02: changes status from ACTIVE to REVOKED", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const before = await contract.getCertificateRecord(CERT_UID);
      expect(before.status).to.equal(0n); // ACTIVE
      await contract.connect(univ1).revokeCertificate(CERT_UID);
      const after = await contract.getCertificateRecord(CERT_UID);
      expect(after.status).to.equal(1n); // REVOKED
    });

    it("TC-RV-03: sets revokedAt to block.timestamp", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const tx = await contract.connect(univ1).revokeCertificate(CERT_UID);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.revokedAt).to.equal(block.timestamp);
    });

    it("TC-RV-04: does NOT change certificateHash", async function () {
      const { contract, univ1, certHash } = await loadFixture(deployAndIssueFixture);
      await contract.connect(univ1).revokeCertificate(CERT_UID);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.certificateHash).to.equal(certHash);
    });

    it("TC-RV-05: does NOT change issuingUniversity", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      await contract.connect(univ1).revokeCertificate(CERT_UID);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.issuingUniversity).to.equal(univ1.address);
    });

    it("TC-RV-06: increments totalRevocations by 1", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const before = await contract.getRevocationCount();
      await contract.connect(univ1).revokeCertificate(CERT_UID);
      const after = await contract.getRevocationCount();
      expect(after - before).to.equal(1n);
    });

    it("TC-RV-07: emits CertificateRevoked with correct indexed params", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const tx = contract.connect(univ1).revokeCertificate(CERT_UID);
      await expect(tx)
        .to.emit(contract, "CertificateRevoked")
        .withArgs(CERT_UID, univ1.address, anyValue, 1n);
    });
  });

  // ── Failure Paths ───────────────────────────────────────────────────────────
  describe("Failure Paths", function () {
    it("TC-RV-08: reverts with NotAuthorizedIssuer for non-issuer", async function () {
      const { contract, attacker } = await loadFixture(deployAndIssueFixture);
      await expect(
        contract.connect(attacker).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
        .withArgs(attacker.address);
    });

    it("TC-RV-09: reverts with CertificateNotFound for non-existent uid", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      await expect(
        contract.connect(univ1).revokeCertificate("NONEXISTENT-UID")
      ).to.be.revertedWithCustomError(contract, "CertificateNotFound")
        .withArgs("NONEXISTENT-UID");
    });

    it("TC-RV-10: reverts with CertificateAlreadyRevoked on second call", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      await contract.connect(univ1).revokeCertificate(CERT_UID);
      await expect(
        contract.connect(univ1).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "CertificateAlreadyRevoked");
    });

    it("TC-RV-11: reverts with NotOriginalIssuer for different authorized issuer", async function () {
      const { contract, univ1, univ2 } = await loadFixture(deployAndIssueFixture);
      await expect(
        contract.connect(univ2).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "NotOriginalIssuer")
        .withArgs(univ2.address, univ1.address);
    });

    it("TC-RV-12: reverts with NotAuthorizedIssuer for contract owner", async function () {
      const { contract, owner } = await loadFixture(deployAndIssueFixture);
      await expect(
        contract.connect(owner).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
        .withArgs(owner.address);
    });

    it("TC-RV-13: deauthorized issuer cannot revoke their own previously-issued certificate", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      await contract.deauthorizeIssuer(univ1.address, "deauth for test");
      await expect(
        contract.connect(univ1).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
        .withArgs(univ1.address);
    });
  });

  // ── Post-Revocation ─────────────────────────────────────────────────────────
  describe("Post-Revocation", function () {
    it("TC-RV-14: verifyCertificate returns (false, REVOKED) for any hash", async function () {
      const { contract, univ1, certHash } = await loadFixture(deployAndIssueFixture);
      await contract.connect(univ1).revokeCertificate(CERT_UID);

      const [isValid1, status1] = await contract.verifyCertificate(CERT_UID, certHash);
      expect(isValid1).to.be.false;
      expect(status1).to.equal(1n); // REVOKED

      const fakeHash = ethers.keccak256(ethers.toUtf8Bytes("fake"));
      const [isValid2, status2] = await contract.verifyCertificate(CERT_UID, fakeHash);
      expect(isValid2).to.be.false;
      expect(status2).to.equal(1n); // REVOKED
    });

    it("TC-RV-15: CertificateAlreadyRevoked error includes original revokedAt timestamp", async function () {
      const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
      const tx = await contract.connect(univ1).revokeCertificate(CERT_UID);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);

      await expect(
        contract.connect(univ1).revokeCertificate(CERT_UID)
      ).to.be.revertedWithCustomError(contract, "CertificateAlreadyRevoked")
        .withArgs(CERT_UID, block.timestamp);
    });
  });
});
