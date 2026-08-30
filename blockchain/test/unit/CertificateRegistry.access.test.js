// blockchain/test/unit/CertificateRegistry.access.test.js
// Unit Tests: Access Control — TC-AC-01 through TC-AC-20
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("CertificateRegistry — Access Control", function () {

  // ── Fixtures ────────────────────────────────────────────────────────────────
  async function deployRegistryFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  async function deployAndAuthorizeFixture() {
    const { contract, owner, univ1, univ2, student, employer, attacker } =
      await deployRegistryFixture();
    await contract.authorizeIssuer(univ1.address);
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  // ── Deployment ──────────────────────────────────────────────────────────────
  describe("Deployment", function () {
    it("TC-AC-01: Owner is correctly set to deployer address after deployment", async function () {
      const { contract, owner } = await loadFixture(deployRegistryFixture);
      expect(await contract.getOwner()).to.equal(owner.address);
    });
  });

  // ── authorizeIssuer() ───────────────────────────────────────────────────────
  describe("authorizeIssuer()", function () {
    it("TC-AC-02: succeeds when called by owner", async function () {
      const { contract, univ1 } = await loadFixture(deployRegistryFixture);
      await contract.authorizeIssuer(univ1.address);
      expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.true;
    });

    it("TC-AC-03: reverts with NotContractOwner for non-owner", async function () {
      const { contract, owner, univ1, attacker } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.connect(attacker).authorizeIssuer(univ1.address)
      ).to.be.revertedWithCustomError(contract, "NotContractOwner")
        .withArgs(attacker.address, owner.address);
    });

    it("TC-AC-04: reverts with CannotAuthorizeZeroAddress for zero address", async function () {
      const { contract } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.authorizeIssuer(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(contract, "CannotAuthorizeZeroAddress");
    });

    it("TC-AC-05: reverts with CannotAuthorizeOwner if owner tries to authorize themselves", async function () {
      const { contract, owner } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.authorizeIssuer(owner.address)
      ).to.be.revertedWithCustomError(contract, "CannotAuthorizeOwner")
        .withArgs(owner.address);
    });

    it("TC-AC-06: reverts with IssuerAlreadyAuthorized for duplicate authorization", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.authorizeIssuer(univ1.address)
      ).to.be.revertedWithCustomError(contract, "IssuerAlreadyAuthorized")
        .withArgs(univ1.address);
    });

    it("TC-AC-07: emits IssuerAuthorized event with correct parameters", async function () {
      const { contract, owner, univ1 } = await loadFixture(deployRegistryFixture);
      const tx = contract.authorizeIssuer(univ1.address);
      await expect(tx)
        .to.emit(contract, "IssuerAuthorized")
        .withArgs(univ1.address, owner.address, anyValue);
    });

    it("TC-AC-08: isAuthorizedIssuer returns true for authorized address", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.true;
    });

    it("TC-AC-09: isAuthorizedIssuer returns false for unauthorized address", async function () {
      const { contract, attacker } = await loadFixture(deployRegistryFixture);
      expect(await contract.isAuthorizedIssuer(attacker.address)).to.be.false;
    });
  });

  // ── deauthorizeIssuer() ─────────────────────────────────────────────────────
  describe("deauthorizeIssuer()", function () {
    it("TC-AC-10: succeeds when called by owner", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      await contract.deauthorizeIssuer(univ1.address, "accreditation expired");
      expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.false;
    });

    it("TC-AC-11: reverts with NotContractOwner for non-owner", async function () {
      const { contract, owner, univ1, attacker } = await loadFixture(deployAndAuthorizeFixture);
      await expect(
        contract.connect(attacker).deauthorizeIssuer(univ1.address, "reason")
      ).to.be.revertedWithCustomError(contract, "NotContractOwner")
        .withArgs(attacker.address, owner.address);
    });

    it("TC-AC-12: reverts with IssuerNotAuthorized for non-authorized address", async function () {
      const { contract, student } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.deauthorizeIssuer(student.address, "reason")
      ).to.be.revertedWithCustomError(contract, "IssuerNotAuthorized")
        .withArgs(student.address);
    });

    it("TC-AC-13: emits IssuerDeauthorized event with correct parameters", async function () {
      const { contract, owner, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      const reason = "compromised wallet";
      const tx = contract.deauthorizeIssuer(univ1.address, reason);
      await expect(tx)
        .to.emit(contract, "IssuerDeauthorized")
        .withArgs(univ1.address, owner.address, anyValue, reason);
    });

    it("TC-AC-14: isAuthorizedIssuer returns false after deauthorization", async function () {
      const { contract, univ1 } = await loadFixture(deployAndAuthorizeFixture);
      expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.true;
      await contract.deauthorizeIssuer(univ1.address, "test");
      expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.false;
    });
  });

  // ── transferOwnership() ─────────────────────────────────────────────────────
  describe("transferOwnership()", function () {
    it("TC-AC-15: succeeds when called by owner with valid address", async function () {
      const { contract, univ1 } = await loadFixture(deployRegistryFixture);
      await contract.transferOwnership(univ1.address);
      expect(await contract.getOwner()).to.equal(univ1.address);
    });

    it("TC-AC-16: reverts with CannotTransferToZeroAddress for zero address", async function () {
      const { contract } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.transferOwnership(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(contract, "CannotTransferToZeroAddress");
    });

    it("TC-AC-17: reverts with NotContractOwner for non-owner", async function () {
      const { contract, owner, univ1, attacker } = await loadFixture(deployRegistryFixture);
      await expect(
        contract.connect(attacker).transferOwnership(univ1.address)
      ).to.be.revertedWithCustomError(contract, "NotContractOwner")
        .withArgs(attacker.address, owner.address);
    });

    it("TC-AC-18: emits OwnershipTransferred event", async function () {
      const { contract, owner, univ1 } = await loadFixture(deployRegistryFixture);
      const tx = contract.transferOwnership(univ1.address);
      await expect(tx)
        .to.emit(contract, "OwnershipTransferred")
        .withArgs(owner.address, univ1.address, anyValue);
    });

    it("TC-AC-19: new owner can call authorizeIssuer after transfer", async function () {
      const { contract, univ1, univ2 } = await loadFixture(deployRegistryFixture);
      await contract.transferOwnership(univ1.address);
      await contract.connect(univ1).authorizeIssuer(univ2.address);
      expect(await contract.isAuthorizedIssuer(univ2.address)).to.be.true;
    });

    it("TC-AC-20: old owner cannot call authorizeIssuer after transfer", async function () {
      const { contract, owner, univ1, univ2 } = await loadFixture(deployRegistryFixture);
      await contract.transferOwnership(univ1.address);
      await expect(
        contract.connect(owner).authorizeIssuer(univ2.address)
      ).to.be.revertedWithCustomError(contract, "NotContractOwner")
        .withArgs(owner.address, univ1.address);
    });
  });
});
