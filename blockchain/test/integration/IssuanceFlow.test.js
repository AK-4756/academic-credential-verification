// blockchain/test/integration/IssuanceFlow.test.js
// Integration Tests: Issuance Flow — IT-IF-01 through IT-IF-04
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Integration — Issuance Flow", function () {

  // ── Fixture ─────────────────────────────────────────────────────────────────
  async function deployRegistryFixture() {
    const [owner, univ1, univ2, student, employer, attacker] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("CertificateRegistry");
    const contract = await Factory.deploy();
    return { contract, owner, univ1, univ2, student, employer, attacker };
  }

  // ── Tests ───────────────────────────────────────────────────────────────────
  it("IT-IF-01: Full lifecycle: deploy → authorize → issue → verify authentic", async function () {
    const { contract, owner, univ1 } = await loadFixture(deployRegistryFixture);

    // Step 1: Verify deployment
    expect(await contract.getOwner()).to.equal(owner.address);
    expect(await contract.getCertificateCount()).to.equal(0n);

    // Step 2: Authorize issuer
    await contract.authorizeIssuer(univ1.address);
    expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.true;

    // Step 3: Issue certificate
    const certUid = "MIT-2025-00001";
    const certHash = ethers.keccak256(ethers.toUtf8Bytes("MIT diploma PDF content"));
    await contract.connect(univ1).storeCertificate(certUid, certHash);
    expect(await contract.getCertificateCount()).to.equal(1n);

    // Step 4: Verify authentic
    const [isValid, status] = await contract.verifyCertificate(certUid, certHash);
    expect(isValid).to.be.true;
    expect(status).to.equal(0n); // ACTIVE
  });

  it("IT-IF-02: Multiple universities issue different certificates; each verifies correctly", async function () {
    const { contract, univ1, univ2 } = await loadFixture(deployRegistryFixture);

    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);

    const uid1 = "MIT-2025-00001";
    const hash1 = ethers.keccak256(ethers.toUtf8Bytes("MIT diploma"));
    const uid2 = "STANFORD-2025-00001";
    const hash2 = ethers.keccak256(ethers.toUtf8Bytes("Stanford diploma"));

    await contract.connect(univ1).storeCertificate(uid1, hash1);
    await contract.connect(univ2).storeCertificate(uid2, hash2);

    // Each verifies independently
    const [valid1, status1] = await contract.verifyCertificate(uid1, hash1);
    expect(valid1).to.be.true;
    expect(status1).to.equal(0n);

    const [valid2, status2] = await contract.verifyCertificate(uid2, hash2);
    expect(valid2).to.be.true;
    expect(status2).to.equal(0n);

    // Cross-hash fails
    const [crossValid, _] = await contract.verifyCertificate(uid1, hash2);
    expect(crossValid).to.be.false;
  });

  it("IT-IF-03: Deauthorized issuer cannot issue new cert; old cert still verifies", async function () {
    const { contract, univ1 } = await loadFixture(deployRegistryFixture);

    // Authorize and issue
    await contract.authorizeIssuer(univ1.address);
    const uid = "MIT-2025-00001";
    const hash = ethers.keccak256(ethers.toUtf8Bytes("MIT diploma"));
    await contract.connect(univ1).storeCertificate(uid, hash);

    // Deauthorize
    await contract.deauthorizeIssuer(univ1.address, "accreditation lapsed");
    expect(await contract.isAuthorizedIssuer(univ1.address)).to.be.false;

    // Cannot issue new cert
    const newHash = ethers.keccak256(ethers.toUtf8Bytes("new diploma"));
    await expect(
      contract.connect(univ1).storeCertificate("MIT-2025-00002", newHash)
    ).to.be.revertedWithCustomError(contract, "NotAuthorizedIssuer");

    // Old cert still verifies
    const [isValid, status] = await contract.verifyCertificate(uid, hash);
    expect(isValid).to.be.true;
    expect(status).to.equal(0n);
  });

  it("IT-IF-04: getCertificateCount() reflects all stored certificates across universities", async function () {
    const { contract, univ1, univ2 } = await loadFixture(deployRegistryFixture);

    await contract.authorizeIssuer(univ1.address);
    await contract.authorizeIssuer(univ2.address);

    expect(await contract.getCertificateCount()).to.equal(0n);

    await contract.connect(univ1).storeCertificate("MIT-2025-00001",
      ethers.keccak256(ethers.toUtf8Bytes("cert1")));
    expect(await contract.getCertificateCount()).to.equal(1n);

    await contract.connect(univ1).storeCertificate("MIT-2025-00002",
      ethers.keccak256(ethers.toUtf8Bytes("cert2")));
    expect(await contract.getCertificateCount()).to.equal(2n);

    await contract.connect(univ2).storeCertificate("STANFORD-2025-00001",
      ethers.keccak256(ethers.toUtf8Bytes("cert3")));
    expect(await contract.getCertificateCount()).to.equal(3n);
  });
});
