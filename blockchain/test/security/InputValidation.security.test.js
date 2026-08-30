// blockchain/test/security/InputValidation.security.test.js
// Security Tests: Input Validation — SC-IV-01 through SC-IV-07
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Security — Input Validation", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployAndAuthorizeFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    await contract.authorizeIssuer(univ1.address);
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("SC-IV-01: Zero bytes32 hash rejected by storeCertificate()", async function () {
    const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
    await expect(
      contract.connect(univ1).storeCertificate("TEST-2025-00001", ethers.ZeroHash)
    ).to.be.revertedWithCustomError(contract, "InvalidCertificateHash");
  });

  it("SC-IV-02: Empty string uid rejected by storeCertificate()", async function () {
    const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
    const hash = ethers.keccak256(ethers.toUtf8Bytes("cert"));
    await expect(
      contract.connect(univ1).storeCertificate("", hash)
    ).to.be.revertedWithCustomError(contract, "InvalidCertificateUid")
      .withArgs("", 0n);
  });

  it("SC-IV-03: 51-character uid rejected by storeCertificate()", async function () {
    const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
    const oversized = "A".repeat(51);
    const hash = ethers.keccak256(ethers.toUtf8Bytes("cert"));
    await expect(
      contract.connect(univ1).storeCertificate(oversized, hash)
    ).to.be.revertedWithCustomError(contract, "InvalidCertificateUid")
      .withArgs(oversized, 51n);
  });

  it("SC-IV-04: 50-character uid accepted (boundary condition)", async function () {
    const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
    const boundary = "A".repeat(50);
    const hash = ethers.keccak256(ethers.toUtf8Bytes("cert"));
    await expect(
      contract.connect(univ1).storeCertificate(boundary, hash)
    ).to.not.be.reverted;
  });

  it("SC-IV-05: Zero address rejected by authorizeIssuer()", async function () {
    const { contract } = await loadFixture(deployAndAuthorizeFixture);
    await expect(
      contract.authorizeIssuer(ethers.ZeroAddress)
    ).to.be.revertedWithCustomError(contract, "CannotAuthorizeZeroAddress");
  });

  it("SC-IV-06: Zero address rejected by transferOwnership()", async function () {
    const { contract } = await loadFixture(deployAndAuthorizeFixture);
    await expect(
      contract.transferOwnership(ethers.ZeroAddress)
    ).to.be.revertedWithCustomError(contract, "CannotTransferToZeroAddress");
  });

  it("SC-IV-07: Owner address rejected by authorizeIssuer()", async function () {
    const { contract, owner } = await loadFixture(deployAndAuthorizeFixture);
    await expect(
      contract.authorizeIssuer(owner.address)
    ).to.be.revertedWithCustomError(contract, "CannotAuthorizeOwner")
      .withArgs(owner.address);
  });
});
