// blockchain/test/unit/CertificateRegistry.storage.test.js
// Unit Tests: Certificate Storage — TC-ST-01 through TC-ST-20
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("CertificateRegistry — Certificate Storage", function () {

  // ── Test Data ───────────────────────────────────────────────────────────────
  const CERT_UID = "TESTUNIV-2025-00001";
  const SECOND_UID = "TESTUNIV-2025-00002";
  const THIRD_UID = "OTHERUNIV-2025-00001";

  let VALID_HASH, DIFFERENT_HASH;
  before(function () {
    VALID_HASH = ethers.keccak256(ethers.toUtf8Bytes("sample certificate"));
    DIFFERENT_HASH = ethers.keccak256(ethers.toUtf8Bytes("different certificate"));
  });

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndAuthorizeFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  // ── Success Path ────────────────────────────────────────────────────────────
  describe("Success Path", function () {
    it("TC-ST-01: storeCertificate() succeeds with valid uid and hash from authorized issuer", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH)
      ).to.not.be.reverted;
    });

    it("TC-ST-02: correctly stores certificateHash", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.certificateHash).to.equal(VALID_HASH);
    });

    it("TC-ST-03: correctly stores issuingUniversity as msg.sender", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.issuingUniversity).to.equal(univ1.address);
    });

    it("TC-ST-04: correctly records block.timestamp as issuedAt", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const tx = await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.issuedAt).to.equal(block.timestamp);
    });

    it("TC-ST-05: sets status to ACTIVE (0)", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.status).to.equal(0n);
    });

    it("TC-ST-06: sets exists to true", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.exists).to.be.true;
    });

    it("TC-ST-07: sets revokedAt to 0", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const record = await contract.getCertificateRecord(CERT_UID);
      expect(record.revokedAt).to.equal(0n);
    });

    it("TC-ST-08: increments totalCertificates by 1", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const before = await contract.getCertificateCount();
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      const after = await contract.getCertificateCount();
      expect(after - before).to.equal(1n);
    });
  });

  // ── Event Emission ──────────────────────────────────────────────────────────
  describe("Event Emission", function () {
    it("TC-ST-09: emits CertificateStored with correct indexed parameters", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const tx = contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await expect(tx)
        .to.emit(contract, "CertificateStored")
        .withArgs(CERT_UID, VALID_HASH, univ1.address, anyValue, anyValue);
    });

    it("TC-ST-10: emits correct non-indexed parameters (issuedAt, totalCount)", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const tx = contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await expect(tx)
        .to.emit(contract, "CertificateStored")
        .withArgs(CERT_UID, VALID_HASH, univ1.address, anyValue, 1n);
    });
  });

  // ── Failure Paths ───────────────────────────────────────────────────────────
  describe("Failure Paths", function () {
    it("TC-ST-11: reverts with NotAuthorizedIssuer for unauthorized caller", async function () {
      const { contract, attacker } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.connect(attacker).storeCertificate(CERT_UID, VALID_HASH)
      ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
        .withArgs(attacker.address);
    });

    it("TC-ST-12: reverts with InvalidCertificateHash for bytes32(0)", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.connect(univ1).storeCertificate(CERT_UID, ethers.ZeroHash)
      ).to.be.revertedWithCustomError(contract, "InvalidCertificateHash");
    });

    it("TC-ST-13: reverts with InvalidCertificateUid for empty string", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.connect(univ1).storeCertificate("", VALID_HASH)
      ).to.be.revertedWithCustomError(contract, "InvalidCertificateUid")
        .withArgs("", 0n);
    });

    it("TC-ST-14: reverts with InvalidCertificateUid for 51-char string", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const oversized = "A".repeat(51);
      await expect(
        contract.connect(univ1).storeCertificate(oversized, VALID_HASH)
      ).to.be.revertedWithCustomError(contract, "InvalidCertificateUid")
        .withArgs(oversized, 51n);
    });

    it("TC-ST-15: reverts with CertificateAlreadyExists on duplicate uid", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await expect(
        contract.connect(univ1).storeCertificate(CERT_UID, DIFFERENT_HASH)
      ).to.be.revertedWithCustomError(contract, "CertificateAlreadyExists")
        .withArgs(CERT_UID);
    });
  });

  // ── Boundary & Multi-issuer ─────────────────────────────────────────────────
  describe("Boundary & Multi-Issuer", function () {
    it("TC-ST-16: accepts exact 50-character uid (boundary test)", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const boundaryUid = "A".repeat(50);
      await expect(
        contract.connect(univ1).storeCertificate(boundaryUid, VALID_HASH)
      ).to.not.be.reverted;
    });

    it("TC-ST-17: two different authorized issuers can each store their own certificates", async function () {
      const { contract, univ1, univ2 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await contract.connect(univ2).storeCertificate(THIRD_UID, DIFFERENT_HASH);
      const r1 = await contract.getCertificateRecord(CERT_UID);
      const r2 = await contract.getCertificateRecord(THIRD_UID);
      expect(r1.exists).to.be.true;
      expect(r2.exists).to.be.true;
      expect(r1.issuingUniversity).to.equal(univ1.address);
      expect(r2.issuingUniversity).to.equal(univ2.address);
    });

    it("TC-ST-18: same issuer can store multiple certificates with different uids", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await contract.connect(univ1).storeCertificate(SECOND_UID, DIFFERENT_HASH);
      expect((await contract.getCertificateRecord(CERT_UID)).exists).to.be.true;
      expect((await contract.getCertificateRecord(SECOND_UID)).exists).to.be.true;
    });

    it("TC-ST-19: getCertificateCount() returns correct count after multiple stores", async function () {
      const { contract, univ1, univ2 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.connect(univ1).storeCertificate(CERT_UID, VALID_HASH);
      await contract.connect(univ1).storeCertificate(SECOND_UID, DIFFERENT_HASH);
      await contract.connect(univ2).storeCertificate(THIRD_UID, VALID_HASH);
      expect(await contract.getCertificateCount()).to.equal(3n);
    });

    it("TC-ST-20: getCertificateRecord() returns zero-value struct for non-existent uid", async function () {
      const { contract } = await loadFixture(deployAndAuthorizeFixture);
      const record = await contract.getCertificateRecord("NONEXISTENT-UID");
      expect(record.exists).to.be.false;
      expect(record.certificateHash).to.equal(ethers.ZeroHash);
      expect(record.issuingUniversity).to.equal(ethers.ZeroAddress);
      expect(record.status).to.equal(0n);
      expect(record.issuedAt).to.equal(0n);
      expect(record.revokedAt).to.equal(0n);
    });
  });
});
