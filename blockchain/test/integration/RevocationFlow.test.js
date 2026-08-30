// blockchain/test/integration/RevocationFlow.test.js
// Integration Tests: Revocation Flow — IT-RF-01 through IT-RF-03
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Integration — Revocation Flow", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployRegistryFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("IT-RF-01: Issue → verify authentic → revoke → verify revoked (complete lifecycle)", async function () {
    const { contract, univ1 } = await loadFixture(deployRegistryFixture);

    const uid = "MIT-2025-00001";
    const hash = ethers.keccak256(ethers.toUtf8Bytes("diploma content"));

    // Issue
    await contract.connect(univ1).storeCertificate(uid, hash);
    expect(await contract.getCertificateCount()).to.equal(1n);

    // Verify authentic
    const [valid1, status1] = await contract.verifyCertificate(uid, hash);
    expect(valid1).to.be.true;
    expect(status1).to.equal(0n);

    // Revoke
    await contract.connect(univ1).revokeCertificate(uid);
    expect(await contract.getRevocationCount()).to.equal(1n);

    // Verify revoked
    const [valid2, status2] = await contract.verifyCertificate(uid, hash);
    expect(valid2).to.be.false;
    expect(status2).to.equal(1n);

    // Record confirms
    const record = await contract.getCertificateRecord(uid);
    expect(record.status).to.equal(1n);
    expect(record.revokedAt).to.be.greaterThan(0n);
    expect(record.certificateHash).to.equal(hash); // unchanged
  });

  it("IT-RF-02: Two universities — A revokes own cert; B's cert unaffected", async function () {
    const { contract, univ1, univ2 } = await loadFixture(deployRegistryFixture);

    const uidA = "MIT-2025-00001";
    const hashA = ethers.keccak256(ethers.toUtf8Bytes("MIT diploma"));
    const uidB = "STANFORD-2025-00001";
    const hashB = ethers.keccak256(ethers.toUtf8Bytes("Stanford diploma"));

    await contract.connect(univ1).storeCertificate(uidA, hashA);
    await contract.connect(univ2).storeCertificate(uidB, hashB);

    // A revokes own cert
    await contract.connect(univ1).revokeCertificate(uidA);

    // A's cert is revoked
    const [validA, statusA] = await contract.verifyCertificate(uidA, hashA);
    expect(validA).to.be.false;
    expect(statusA).to.equal(1n);

    // B's cert is unaffected
    const [validB, statusB] = await contract.verifyCertificate(uidB, hashB);
    expect(validB).to.be.true;
    expect(statusB).to.equal(0n);
  });

  it("IT-RF-03: Revocation by original issuer after another issuer is added", async function () {
    const { contract, univ1, univ2 } = await loadFixture(deployRegistryFixture);

    // univ1 issues cert
    const uid = "MIT-2025-00001";
    const hash = ethers.keccak256(ethers.toUtf8Bytes("MIT diploma"));
    await contract.connect(univ1).storeCertificate(uid, hash);

    // univ2 is already authorized but cannot revoke univ1's cert
    await expect(
      contract.connect(univ2).revokeCertificate(uid)
    ).to.be.revertedWithCustomError(contract, "NotOriginalIssuer");

    // univ1 successfully revokes own cert
    await contract.connect(univ1).revokeCertificate(uid);
    const record = await contract.getCertificateRecord(uid);
    expect(record.status).to.equal(1n);
  });
});
