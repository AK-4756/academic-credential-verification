// blockchain/test/security/EdgeCases.security.test.js
// Security Tests: Edge Cases — SC-EC-01 through SC-EC-06
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Security — Edge Cases", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndIssueFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);

    const certUid = "TESTUNIV-2025-00001";
    const certHash = ethers.keccak256(ethers.toUtf8Bytes("edge case cert"));
    await contract.connect(univ1).storeCertificate(certUid, certHash);

    return { contract, owner, univ1, univ2, student, employer, attacker, certUid, certHash };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("SC-EC-01: Cannot store certificate with same UID as existing (exact duplicate)", async function () {
    const { contract, univ1, certUid } = await loadFixture(deployAndIssueFixture);
    const newHash = ethers.keccak256(ethers.toUtf8Bytes("different content"));
    await expect(
      contract.connect(univ1).storeCertificate(certUid, newHash)
    ).to.be.revertedWithCustomError(contract, "CertificateAlreadyExists")
      .withArgs(certUid);
  });

  it("SC-EC-02: Cannot revoke already-revoked certificate", async function () {
    const { contract, univ1, certUid } = await loadFixture(deployAndIssueFixture);
    await contract.connect(univ1).revokeCertificate(certUid);
    await expect(
      contract.connect(univ1).revokeCertificate(certUid)
    ).to.be.revertedWithCustomError(contract, "CertificateAlreadyRevoked");
  });

  it("SC-EC-03: Cannot cross-revoke between universities", async function () {
    const { contract, univ1, univ2, certUid } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(univ2).revokeCertificate(certUid)
    ).to.be.revertedWithCustomError(contract, "NotOriginalIssuer")
      .withArgs(univ2.address, univ1.address);
  });

  it("SC-EC-04: Deauthorized issuer cannot issue new certificates", async function () {
    const { contract, univ1 } = await loadFixture(deployAndIssueFixture);
    await contract.deauthorizeIssuer(univ1.address, "testing deauth");

    const newHash = ethers.keccak256(ethers.toUtf8Bytes("new cert after deauth"));
    await expect(
      contract.connect(univ1).storeCertificate("TESTUNIV-2025-00002", newHash)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
      .withArgs(univ1.address);
  });

  it("SC-EC-05: Previously issued certs by deauthorized issuer remain AUTHENTIC", async function () {
    const { contract, univ1, certUid, certHash } = await loadFixture(deployAndIssueFixture);
    await contract.deauthorizeIssuer(univ1.address, "testing deauth");

    // Old cert still verifies
    const [isValid, status] = await contract.verifyCertificate(certUid, certHash);
    expect(isValid).to.be.true;
    expect(status).to.equal(0n); // ACTIVE
  });

  it("SC-EC-06: Cannot transfer ownership to current owner (no-op guard)", async function () {
    const { contract, owner } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.transferOwnership(owner.address)
    ).to.be.revertedWithCustomError(contract, "AlreadyOwner");
  });
});
