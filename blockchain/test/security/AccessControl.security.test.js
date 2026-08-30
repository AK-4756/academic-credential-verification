// blockchain/test/security/AccessControl.security.test.js
// Security Tests: Access Control — SC-AC-01 through SC-AC-07
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Security — Access Control", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndIssueFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);

    const certUid = "TESTUNIV-2025-00001";
    const certHash = ethers.keccak256(ethers.toUtf8Bytes("test cert"));
    await contract.connect(univ1).storeCertificate(certUid, certHash);

    return { contract, owner, univ1, univ2, student, employer, attacker, certUid, certHash };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("SC-AC-01: Random wallet cannot call storeCertificate()", async function () {
    const { contract, attacker } = await loadFixture(deployAndIssueFixture);
    const hash = ethers.keccak256(ethers.toUtf8Bytes("malicious cert"));
    await expect(
      contract.connect(attacker).storeCertificate("FAKE-2025-00001", hash)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
      .withArgs(attacker.address);
  });

  it("SC-AC-02: Random wallet cannot call revokeCertificate()", async function () {
    const { contract, attacker, certUid } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(attacker).revokeCertificate(certUid)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
      .withArgs(attacker.address);
  });

  it("SC-AC-03: Random wallet cannot call authorizeIssuer()", async function () {
    const { contract, owner, attacker, univ2 } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(attacker).authorizeIssuer(univ2.address)
    ).to.be.revertedWithCustomError(contract, "NotContractOwner")
      .withArgs(attacker.address, owner.address);
  });

  it("SC-AC-04: Random wallet cannot call deauthorizeIssuer()", async function () {
    const { contract, owner, attacker, univ1 } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(attacker).deauthorizeIssuer(univ1.address, "reason")
    ).to.be.revertedWithCustomError(contract, "NotContractOwner")
      .withArgs(attacker.address, owner.address);
  });

  it("SC-AC-05: Authorized issuer cannot call authorizeIssuer()", async function () {
    const { contract, owner, univ1, univ2 } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(univ1).authorizeIssuer(univ2.address)
    ).to.be.revertedWithCustomError(contract, "NotContractOwner")
      .withArgs(univ1.address, owner.address);
  });

  it("SC-AC-06: Owner cannot call storeCertificate()", async function () {
    const { contract, owner } = await loadFixture(deployAndIssueFixture);
    const hash = ethers.keccak256(ethers.toUtf8Bytes("owner cert attempt"));
    await expect(
      contract.connect(owner).storeCertificate("OWNER-2025-00001", hash)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
      .withArgs(owner.address);
  });

  it("SC-AC-07: Owner cannot call revokeCertificate()", async function () {
    const { contract, owner, certUid } = await loadFixture(deployAndIssueFixture);
    await expect(
      contract.connect(owner).revokeCertificate(certUid)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer")
      .withArgs(owner.address);
  });
});
