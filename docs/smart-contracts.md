# Blockchain-Based Academic Credential Verification Platform
## Complete Smart Contract Architecture Blueprint — MVP Edition

---

# PRE-DESIGN REVIEW & REQUIREMENT EXTRACTION

## Review 1: Approved Architecture Document — Smart Contract Relevant Extractions

Before a single design decision is made, every smart-contract-relevant requirement from the approved architecture document is extracted and catalogued.

```
EXTRACTED REQUIREMENTS FROM ARCHITECTURE BLUEPRINT
════════════════════════════════════════════════════

CONTRACT IDENTITY:
├── Contract Name: CertificateRegistry
├── Language: Solidity ^0.8.19
├── Framework: Hardhat
├── Networks: Hardhat local (chainId 31337) + Sepolia testnet (chainId 11155111)
└── Wallet Integration: MetaMask (browser-side signing)

AUTHORIZED ISSUER SYSTEM:
├── Only verified university wallets may call storeCertificate()
├── Platform deployer (owner) maintains the authorized issuer whitelist
├── authorizeIssuer(address) — owner-only function
├── revokeIssuerAuthorization(address) — owner-only function
└── isAuthorizedIssuer(address) — public read function

CERTIFICATE STORAGE:
├── Input: certificate_uid (string), sha256_hash (bytes32)
├── No overwriting of existing certificate UIDs
├── Issuer wallet address captured at storage time
├── Block timestamp captured at storage time
└── Emits CertificateStored event

CERTIFICATE VERIFICATION:
├── Input: certificate_uid (string), submittedHash (bytes32)
├── Returns: (bool isValid, CertificateStatus status)
├── Read-only; no gas cost for verifiers
├── Blockchain is always the source of truth
└── Comparison: stored hash == submitted hash AND status == ACTIVE

CERTIFICATE REVOCATION:
├── Input: certificate_uid (string)
├── Caller must be the original issuing university wallet
├── Cannot un-revoke (terminal state)
├── Records revokedAt timestamp
└── Emits CertificateRevoked event

DATA STORED ON-CHAIN (explicitly from architecture):
├── SHA-256 hash (bytes32)
├── Certificate UID (string — mapping key)
├── Issuer wallet address
├── Issuance Unix timestamp
├── Revocation status
├── Revocation timestamp
└── exists flag (guard against zero-value reads)

DATA EXPLICITLY EXCLUDED FROM CHAIN:
├── Student name (privacy)
├── University name (mutable off-chain data)
├── Degree title (privacy)
├── Field of study (privacy)
├── PDF file (cost-prohibitive)
└── All PII

GAS ESTIMATES FROM ARCHITECTURE:
├── authorizeIssuer: ~46,000 gas
├── storeCertificate: ~85,000 gas
├── revokeCertificate: ~35,000 gas
├── verifyCertificate: 0 (read-only call)
└── getCertificateRecord: 0 (read-only call)

SECURITY REQUIREMENTS:
├── Only authorized issuers can store hashes
├── Issuer can only revoke their own certificates
├── No hash overwrite after initial store
├── Immutable once stored (no update function)
└── Owner cannot forge certificates on behalf of universities
```

## Review 2: Approved Database Design — Smart Contract Interface Points

```
EXTRACTED DATABASE-CONTRACT INTERFACE POINTS
══════════════════════════════════════════════

certificate_uid FORMAT (from database):
├── VARCHAR(50) in database
├── Format: {SHORTCODE}-{YYYY}-{NNNNN}
├── Example: "MIT-2025-00142"
├── Regex: ^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$
└── Max 50 characters → safe for Solidity string storage

sha256_hash BRIDGE:
├── Database column: VARCHAR(64) — 64 lowercase hex characters
├── On-chain storage: bytes32 — 32 bytes = 256 bits
├── Conversion: "0x" + hex_string → bytes32 via ethers.js
└── The hash stored on-chain MUST match certificates.sha256_hash exactly

blockchain_status ENUM SYNC:
├── Database: PENDING → SUBMITTED → CONFIRMED / FAILED / REVOKED
├── Contract: CertificateStatus { ACTIVE, REVOKED }
├── PENDING/SUBMITTED/FAILED are off-chain states (not on contract)
└── CONFIRMED = ACTIVE on contract; REVOKED = REVOKED on both

blockchain_transactions TABLE FIELDS populated from contract:
├── tx_hash ← transaction receipt hash
├── from_address ← msg.sender (university wallet)
├── to_address ← contract address
├── contract_address ← CertificateRegistry address
├── block_number ← receipt.blockNumber
├── block_hash ← receipt.blockHash
├── gas_used ← receipt.gasUsed
├── gas_price_wei ← receipt.effectiveGasPrice
├── confirmed_at ← block timestamp converted to TIMESTAMPTZ
└── certificate_hash_stored ← the bytes32 hash submitted

universities.wallet_address LIFECYCLE:
├── Stored in DB when university connects MetaMask
├── Must be passed to authorizeIssuer() on contract
├── Must be the SAME address that calls storeCertificate()
└── Can be changed only by owner calling revokeIssuerAuthorization()
    then authorizeIssuer() with new address

CROSS-VALIDATION REQUIREMENT:
├── After TX confirmation, backend calls getCertificateRecord(cert_uid)
├── Verifies: stored hash == db hash
├── Verifies: issuer address == university.wallet_address
└── If mismatch: blockchain_status stays FAILED; alert triggered
```

## Review 3: Carried-Forward Assumptions

```
ASSUMPTIONS CARRIED FORWARD INTO SMART CONTRACT DESIGN
════════════════════════════════════════════════════════

ASSUMPTION 01: Single Contract Architecture
From architecture: "No complex inheritance chains for MVP"
Impact: CertificateRegistry.sol is a single, self-contained contract.
No proxy pattern, no library splitting, no factory pattern in MVP.

ASSUMPTION 02: Ethereum Network Only
From architecture: Hardhat local + Sepolia testnet for MVP.
Impact: No cross-chain logic, no bridge interfaces, no Layer 2 support.
Future expansion (Section 19) mentions multi-chain as post-MVP.

ASSUMPTION 03: MetaMask as Sole Signing Mechanism
From architecture: "The private key of the university's Ethereum wallet
must never touch the server. Signing on the backend would require
storing private keys on the server."
Impact: Contract assumes msg.sender is a human-controlled MetaMask wallet.
No meta-transactions, no gasless relayer patterns in MVP.

ASSUMPTION 04: SHA-256 as Fixed Hash Algorithm
From architecture: SHA-256 is the fixed hashing algorithm.
From database: sha256_hash VARCHAR(64) — 64 hex chars = 32 bytes = bytes32.
Impact: Contract stores exactly bytes32. If hash algorithm changes post-MVP,
a contract upgrade or new contract deployment would be required.

ASSUMPTION 05: Certificate UID as Primary On-Chain Key
From architecture and database: certificate_uid is the bridge identifier.
Impact: The contract mapping uses string certificate_uid as the key,
not the UUID from the database. The UID must be globally unique
(enforced by UNIQUE constraint in database).

ASSUMPTION 06: One-Way Revocation
From architecture: "REVOKED → [terminal]; cannot be un-revoked; permanent"
Impact: The contract revocation function is a one-way state transition.
No reinstatement function exists or will be added.

ASSUMPTION 07: Issuer-Only Revocation
From architecture: "only authorized issuer can revoke their certificate"
Impact: revokeCertificate() requires msg.sender == original issuing wallet.
University admin cannot revoke another university's certificates.

ASSUMPTION 08: Owner Cannot Issue
From architecture: "Owner cannot forge certificates on behalf of universities"
Impact: The owner role is strictly administrative (authorize/deauthorize issuers).
The owner wallet is NOT in the authorizedIssuers mapping by default.

ASSUMPTION 09: No Upgradability in MVP
From architecture: "No complex inheritance chains for MVP"
Impact: No OpenZeppelin TransparentProxy or UUPS pattern.
The contract is deployed once; if logic must change, a new contract
is deployed and the database contract_address is updated.

ASSUMPTION 10: Gas Cost is Issuer's Responsibility
From architecture: MetaMask prompts the university admin, who pays gas.
Impact: No gas sponsorship, no ERC-4337 account abstraction, no relayer.
University admin must have ETH in their wallet to issue certificates.

ASSUMPTION 11: No Token Economics
From architecture: "No token economics"
Impact: Contract is purely a registry. No ERC-20, no ERC-721, no NFT minting.
Certificates are not tokenized in the MVP.

ASSUMPTION 12: Hardhat Tests Target >95% Coverage
From architecture: "Overall target: >95% line coverage"
Impact: Test suite must cover all functions including edge cases and
all revert conditions.
```

---

# TABLE OF CONTENTS

1. Smart Contract Design Philosophy
2. Contract Responsibilities
3. State Variables
4. Struct Definitions
5. Mappings
6. Events
7. Modifiers
8. Access Control Design
9. Certificate Storage Workflow
10. Certificate Verification Workflow
11. Certificate Revocation Workflow
12. Gas Optimization Strategy
13. Security Analysis
14. Smart Contract Folder Structure
15. Smart Contract Testing Strategy
16. Deployment Strategy
17. Future Upgrade Path
18. Smart Contract Validation Checklist

---

# SECTION 1: SMART CONTRACT DESIGN PHILOSOPHY

## 1.1 The Minimal Registry Principle

The CertificateRegistry smart contract exists for exactly one purpose: to be an **incorruptible, publicly auditable, append-mostly ledger** that answers the question — *"Did institution X issue a document with this exact content, and is it still valid?"*

Every design decision flows from this single purpose. Features that do not directly serve this question are excluded. Complexity that does not increase trust is eliminated. Gas costs that do not improve security are avoided.

This is not a general-purpose contract. It is not a token. It is not a DAO. It is a hash registry with access control.

## 1.2 The Five Immutable Laws of This Contract

These laws are never broken, not by gas optimization, not by convenience, not by feature requests:

```
LAW 1: WHAT IS WRITTEN CANNOT BE ERASED
Once storeCertificate() succeeds, the hash is permanently on-chain.
No function exists to delete a certificate record. Even revocation
does not erase the record — it changes its status to REVOKED.
The issuance event is forever visible on the blockchain.

LAW 2: WHAT IS HASHED CANNOT BE FORGED
The contract stores bytes32 hashes. It has no knowledge of what
content was hashed. It cannot verify that the hash corresponds to
a legitimate academic document. That verification happens off-chain.
The contract's guarantee is narrower and more powerful: if this
exact hash was submitted by this exact authorized wallet at this
exact timestamp, and it has not been revoked, then SOMEONE with
authority to issue certificates chose to anchor this specific
cryptographic fingerprint permanently.

LAW 3: ONLY THE AUTHORIZED MAY WRITE
No unauthenticated party may store a hash. Authorization is
explicit, wallet-to-wallet, maintained by the contract owner.
The Ethereum signature in every transaction is the cryptographic
proof of who wrote.

LAW 4: ANYONE MAY READ
Verification is public, free (read-only call), and requires no
authentication. The trustless verification property of blockchain
means an employer in any country can verify a certificate without
asking permission from anyone.

LAW 5: THE CONTRACT OWNER ADMINISTERS, NOT ISSUES
The owner role is limited to managing the authorized issuer list.
The owner cannot store hashes. This separation prevents the platform
operator from forging certificates even if their own private key
were compromised.
```

## 1.3 Design Paradigm: Registry Pattern

The contract implements the **Registry Pattern** — the simplest blockchain pattern that satisfies the requirements. Alternatives were considered and rejected:

```
PATTERN COMPARISON
═══════════════════

Registry Pattern (CHOSEN):
├── contract is a key-value store: certUID → CertificateRecord
├── Writes by authorized parties only
├── Reads by anyone
├── No token minting, no NFTs, no ownership transfer
└── Complexity: MINIMAL ✓

NFT/ERC-721 Pattern (REJECTED):
├── Each certificate is a non-fungible token
├── Student owns the token; can transfer it
├── Pros: standard interface, wallets show certificates
├── Cons: adds transfer logic, approval logic, complex ownership model
├── Cons: students would need Ethereum wallets
├── Cons: 3x more contract complexity for zero MVP benefit
└── Rejected: over-engineered for MVP; post-MVP consideration

Merkle Tree Pattern (REJECTED):
├── Batch-issue certificates under a single Merkle root
├── Pros: drastically lower gas per certificate
├── Cons: complex off-chain Merkle proof generation
├── Cons: verification requires proof path, not just hash
├── Cons: explicitly listed as excluded from MVP
└── Rejected: listed in architecture as post-MVP (Tier 1 expansion)

Factory Pattern (REJECTED):
├── One contract deployed per university
├── Pros: natural isolation of university data
├── Cons: deployment cost per university
├── Cons: verification must know which contract to query
├── Cons: complex contract registry needed
└── Rejected: unnecessary complexity; single contract handles all universities

Upgradeable Proxy Pattern (REJECTED):
├── TransparentProxy or UUPS for upgradeability
├── Pros: can fix bugs without redeployment
├── Cons: introduces storage layout complexity
├── Cons: introduces upgrade key as a centralization vector
├── Cons: architecture explicitly says "No upgradability in MVP"
└── Rejected: see Assumption 09
```

---

**[Design Decision A]** The Registry Pattern was chosen because it is the simplest pattern that satisfies all five immutable laws. It produces a contract with fewer than 200 lines of logic, minimal attack surface, and gas costs under 100,000 per issuance. **[Requirement satisfied]** Certificate hash storage, authorized issuance, tamper detection, and public verification. **[Alternative rejected]** Every alternative adds complexity without adding to the core trust guarantee.

---

# SECTION 2: CONTRACT RESPONSIBILITIES

## 2.1 Responsibility Boundary Map

```
CertificateRegistry CONTRACT RESPONSIBILITIES
══════════════════════════════════════════════

WHAT THE CONTRACT IS RESPONSIBLE FOR:
├── R1: Maintaining the authorized issuer whitelist
│       Who: contract owner
│       How: mapping(address => bool)
│
├── R2: Storing certificate hash records
│       Who: authorized issuers only
│       What: bytes32 hash + metadata (issuer, timestamp, status)
│       Immutability: one-time write per certificate UID
│
├── R3: Enforcing hash uniqueness per certificate UID
│       Mechanism: require(!certificates[certUid].exists)
│       Effect: prevents overwrite/replay attacks
│
├── R4: Verifying certificate authenticity on request
│       Who: anyone (public)
│       How: compare submitted bytes32 hash to stored bytes32 hash
│       Cost: zero ETH (view function)
│
├── R5: Recording certificate revocations
│       Who: the original issuing university wallet only
│       State change: ACTIVE → REVOKED (terminal)
│       Evidence: revokedAt timestamp permanently recorded
│
├── R6: Emitting events for every state-changing action
│       Why: enables off-chain indexing, audit, and alerting
│       Events: CertificateStored, CertificateRevoked,
│               IssuerAuthorized, IssuerDeauthorized
│
└── R7: Providing public read access to certificate records
        Who: anyone
        Functions: getCertificateRecord(), verifyCertificate(),
                   isAuthorizedIssuer()

WHAT THE CONTRACT IS EXPLICITLY NOT RESPONSIBLE FOR:
├── X1: Validating that a certificate UID matches a real university
│       (enforced off-chain by database FK constraints)
├── X2: Validating that the SHA-256 hash was computed correctly
│       (enforced off-chain by hash_service.py)
├── X3: Storing or verifying student identity
│       (privacy requirement: PII stays off-chain)
├── X4: Token economics, royalties, or financial transactions
│       (out of scope by architecture decision)
├── X5: Pausing/unpausing the contract
│       (not required for MVP; all operations are always available)
├── X6: Multi-signature issuance
│       (post-MVP feature per architecture Section 19)
└── X7: Cross-chain operations
        (post-MVP per architecture Section 19)
```

## 2.2 Actor-to-Function Responsibility Matrix

```
ACTOR → PERMITTED CONTRACT FUNCTIONS
══════════════════════════════════════

CONTRACT OWNER (deployer wallet):
├── authorizeIssuer(address issuerAddress)
├── deauthorizeIssuer(address issuerAddress)
├── transferOwnership(address newOwner)
└── [READ] All public view functions

AUTHORIZED ISSUER (university wallet):
├── storeCertificate(string certUid, bytes32 certHash)
├── revokeCertificate(string certUid)
└── [READ] All public view functions

ANY ADDRESS (public):
├── verifyCertificate(string certUid, bytes32 submittedHash)
│   → returns (bool isValid, CertificateStatus status)
├── getCertificateRecord(string certUid)
│   → returns CertificateRecord struct
├── isAuthorizedIssuer(address wallet)
│   → returns bool
├── getOwner()
│   → returns address
└── getCertificateCount()
    → returns uint256

UNAUTHORIZED ADDRESS (not owner, not authorized issuer):
├── storeCertificate() → REVERT: NotAuthorizedIssuer
├── revokeCertificate() → REVERT: NotAuthorizedIssuer
├── authorizeIssuer() → REVERT: NotContractOwner
└── deauthorizeIssuer() → REVERT: NotContractOwner
```

---

**[Design Decision A]** The owner role and issuer role are **explicitly separated** — the owner cannot issue certificates. This is a critical security property: if the platform operator's private key is compromised, the attacker can alter the authorized issuer list but cannot create fraudulent certificate records themselves. Every fraudulent record requires a compromised university wallet, which is a separate security boundary. **[Requirement satisfied]** Security architecture requirement from the blueprint: "Owner cannot forge certificates on behalf of universities." **[Alternative rejected]** Giving the owner combined admin + issuing powers would create a single point of failure that compromises the entire trust model.

---

# SECTION 3: STATE VARIABLES

## 3.1 Complete State Variable Specification

```
STATE VARIABLES — COMPLETE SPECIFICATION
══════════════════════════════════════════

─────────────────────────────────────────────────────────────
VARIABLE 1: owner
─────────────────────────────────────────────────────────────
Declaration:    address private owner
Visibility:     private (exposed via getOwner() view function)
Mutability:     mutable (via transferOwnership)
Initial Value:  msg.sender at construction
Storage Slot:   Slot 0

Purpose:
The address of the contract deployer / platform administrator.
This is the ONLY address that can authorize or deauthorize
university issuers. Cannot be zero address.

Why private visibility:
The owner address IS readable by anyone via getOwner(),
but making it private prevents it from generating a
free getter that returns a mutable state variable
directly. Explicit getOwner() function gives us control
to add access logging in the future if needed.

Lifecycle:
├── Set: constructor (msg.sender)
├── Changed: transferOwnership(newOwner)
└── Read: onlyOwner modifier, getOwner()

─────────────────────────────────────────────────────────────
VARIABLE 2: authorizedIssuers
─────────────────────────────────────────────────────────────
Declaration:    mapping(address => bool) private authorizedIssuers
Visibility:     private (exposed via isAuthorizedIssuer() view)
Mutability:     mutable (via authorize/deauthorize functions)
Storage:        Dynamic mapping — no fixed slot

Purpose:
The whitelist of Ethereum wallet addresses permitted to call
storeCertificate() and revokeCertificate(). Each entry is
a university's MetaMask wallet address.

Why mapping(address → bool):
Simple O(1) lookup. No enumeration needed for MVP.
The isAuthorizedIssuer() check in the modifier must be
gas-efficient since it runs on every write transaction.
A mapping lookup costs ~2,100 gas (cold) or ~100 gas (warm).

Why private:
Exposed via explicit getter isAuthorizedIssuer(address).
Private prevents automated tooling from calling the
raw mapping with arbitrary inputs and inferring whitelist
membership through response patterns.

Lifecycle:
├── Populated: authorizeIssuer(address)
├── Cleared: deauthorizeIssuer(address)
└── Read: onlyAuthorizedIssuer modifier, isAuthorizedIssuer()

─────────────────────────────────────────────────────────────
VARIABLE 3: certificates
─────────────────────────────────────────────────────────────
Declaration:    mapping(string => CertificateRecord) private certificates
Visibility:     private (exposed via getCertificateRecord())
Mutability:     mutable (new entries; status changes for revocation)
Storage:        Dynamic mapping

Purpose:
The primary data store. Maps each certificate UID (string)
to its CertificateRecord struct. This is the core registry.

Why mapping(string => CertificateRecord):
Certificate UIDs are the natural keys used in both the
database and user-facing systems. Using the string UID
as the mapping key allows direct lookup without any
translation layer. The off-chain backend passes the same
UID that appears on the physical certificate.

Why string key (not bytes32):
Certificate UIDs contain hyphens and alphanumeric chars
(e.g., "MIT-2025-00142"). Converting to bytes32 would
require keccak256 hashing the string, which:
(a) makes the key opaque to external observers
(b) creates collision risk if not handled carefully
(c) adds computation on every lookup
Using string directly is safer and more readable.

Cost consideration:
String keys in mappings use keccak256 internally by the EVM
(all mapping keys are hashed to determine storage slot).
The string is NOT stored verbatim as the key — it is hashed.
This means storage cost does not grow with string length
for the key itself.

Why private:
Exposed via getCertificateRecord(certUid). Private prevents
storage slot manipulation attacks where an attacker crafts
a calldata to read raw storage slots.

─────────────────────────────────────────────────────────────
VARIABLE 4: totalCertificates
─────────────────────────────────────────────────────────────
Declaration:    uint256 private totalCertificates
Visibility:     private (exposed via getCertificateCount())
Mutability:     mutable (incremented on each successful storeCertificate)
Initial Value:  0
Storage Slot:   Slot 1

Purpose:
Monotonically increasing counter of successfully stored
certificate records. Provides a lightweight health metric
and enables off-chain monitoring to detect if expected
issuance volume deviates from actual chain state.

Why uint256:
Maximum value: 2^256 - 1. Will never overflow in practice.
Using a smaller type (uint128, uint64) saves no gas here
because storage slots are 32 bytes regardless; packing
with other variables could save gas but totalCertificates
does not share its slot with any other variable in the
current layout.

Why private:
Exposed via getCertificateCount(). No direct state mutation
from outside the contract.

─────────────────────────────────────────────────────────────
VARIABLE 5: totalRevocations
─────────────────────────────────────────────────────────────
Declaration:    uint256 private totalRevocations
Visibility:     private (exposed via getRevocationCount())
Mutability:     mutable (incremented on each revokeCertificate)
Initial Value:  0
Storage Slot:   Slot 2

Purpose:
Monotonically increasing counter of revoked certificates.
Useful for platform health monitoring and security alerting.
If revocation count spikes unexpectedly, it may indicate
a compromised university wallet.

─────────────────────────────────────────────────────────────
VARIABLE 6: CONTRACT_VERSION
─────────────────────────────────────────────────────────────
Declaration:    string public constant CONTRACT_VERSION
Value:          "1.0.0"
Mutability:     immutable constant

Purpose:
Enables off-chain tools to verify they are interacting
with the expected contract version. When a new version
is deployed, the version string changes, allowing
automated compatibility checks.

Why constant:
Never changes. Stored in contract bytecode, not in storage.
Zero storage slot cost. Zero read gas cost (inlined by compiler).
```

## 3.2 Storage Layout Map

```
STORAGE SLOT ALLOCATION
════════════════════════

Slot 0:  owner (address, 20 bytes) + [12 bytes padding]
Slot 1:  totalCertificates (uint256, 32 bytes)
Slot 2:  totalRevocations (uint256, 32 bytes)

Dynamic Mappings (no fixed slot — EVM computes slot from keccak):
├── authorizedIssuers: keccak256(address . p) where p = mapping position
└── certificates: keccak256(keccak256(string) . p) for string keys

Note: CONTRACT_VERSION is a constant — stored in bytecode, not storage.
Zero storage slots consumed.

Total fixed storage slots used: 3
Total gas for cold SLOAD of all fixed variables: ~6,300 gas
```

---

**[Design Decision A]** `totalCertificates` and `totalRevocations` counters are included despite not being strictly required for the core verification logic. **[Why]** These counters cost one SSTORE increment per issuance/revocation (2,900 gas warm write) and provide critical monitoring capability. An off-chain service can poll `getCertificateCount()` and compare to the database count — a mismatch indicates a synchronization problem between the DB and chain. **[Requirement satisfied]** Verification logs monitoring; blockchain health verification. **[Alternative rejected]** Deriving counts from event logs is possible but requires an archive node and complex event log queries. A state variable counter is O(1) and always consistent.

---

# SECTION 4: STRUCT DEFINITIONS

## 4.1 CertificateRecord Struct

```
STRUCT: CertificateRecord
══════════════════════════

Purpose:
The complete on-chain record for a single certificate.
This is the value type in the certificates mapping.
Designed to be the minimum data needed to answer:
"Was this certificate legitimately issued, what was its exact content
fingerprint, who issued it, when was it issued, and is it still valid?"

Field-by-Field Specification:
──────────────────────────────

FIELD 1: certificateHash
  Type:        bytes32
  Required:    YES (cannot be zero)
  Immutable:   YES (set once at storeCertificate, never changed)

  Purpose:
  The SHA-256 hash of the certificate PDF binary content,
  encoded as a 32-byte value. This is the cryptographic
  fingerprint of the document. Any modification to the
  original PDF produces a completely different hash.

  Why bytes32 (not string):
  SHA-256 always produces exactly 256 bits = 32 bytes.
  bytes32 is:
  ├── Fixed size: fits exactly in one EVM storage slot (32 bytes)
  ├── Gas efficient: no length prefix, no dynamic allocation
  ├── Natively comparable: (hashA == hashB) is a single EVM opcode
  └── Type safe: cannot accidentally store a non-hash value

  Why not string:
  A string "a3f2c1b4..." would require dynamic storage,
  cost more gas, and require string comparison instead of
  the native == operator. bytes32 is strictly superior.

  Zero-value guard:
  bytes32(0) is checked in the storeCertificate modifier.
  Storing a zero hash would create a vacuously matching
  record (submitted zero hash == stored zero hash = AUTHENTIC),
  which is a security vulnerability.

FIELD 2: issuingUniversity
  Type:        address
  Required:    YES
  Immutable:   YES (set once, never changed)

  Purpose:
  The Ethereum wallet address of the university that issued
  this certificate. Captured as msg.sender at storeCertificate
  call time. This creates a permanent, cryptographically
  signed attribution: "the wallet holding this private key
  submitted this transaction."

  Why store address (not name string):
  The address is the cryptographic identity on Ethereum.
  University names can change. The wallet address is the
  authoritative identity for blockchain purposes.
  Off-chain: the DB maps wallet_address → university name.

  Revocation use:
  revokeCertificate() checks: msg.sender == issuingUniversity.
  This ensures only the original issuer can revoke.

FIELD 3: issuedAt
  Type:        uint256
  Required:    YES
  Immutable:   YES (set once, never changed)
  Value:       block.timestamp at time of storeCertificate

  Purpose:
  Unix timestamp of the block in which the certificate hash
  was stored. This is not the academic issue date (that is
  in the database). This is the blockchain anchoring timestamp:
  the proof that the hash was known to the issuer and
  permanently recorded at this specific moment in time.

  Why block.timestamp (not user-supplied date):
  A user-supplied date could be backdated or forged.
  block.timestamp is set by the mining/validating node;
  while it can vary by up to ~15 seconds from real time
  (Ethereum consensus rule), it is orders of magnitude
  more trustworthy than a user-supplied parameter.

  Why uint256:
  block.timestamp is uint256 in Solidity. No conversion needed.
  Unix timestamps will not overflow uint256 for billions of years.

FIELD 4: revokedAt
  Type:        uint256
  Required:    NO (0 when not revoked)
  Immutable:   Set once on revocation; then immutable

  Purpose:
  Unix timestamp of the block in which the certificate was
  revoked. Zero (0) means not revoked. Nonzero means revoked
  at that timestamp.

  Why store revocation timestamp:
  Verifiers need to know WHEN a certificate was revoked.
  An employer who received a certificate BEFORE the revocation
  date may have a legitimate claim. The timestamp enables
  this temporal reasoning off-chain.

  Zero means not revoked:
  Checking (revokedAt == 0) is the canonical "not revoked"
  check. This is more gas-efficient than a separate boolean
  (saves one storage slot via struct packing with status enum).

FIELD 5: status
  Type:        CertificateStatus (enum)
  Required:    YES
  Initial:     CertificateStatus.ACTIVE
  Transitions: ACTIVE → REVOKED (terminal; no ACTIVE ← REVOKED)

  Purpose:
  The current lifecycle state of the certificate.
  Used in verification: a REVOKED certificate always returns
  "REVOKED" regardless of whether the hash matches.

  Why enum (not bool):
  An enum is extensible without breaking existing logic.
  If a future version needs a SUSPENDED state (revoked but
  under appeal review), the enum can be extended.
  A bool (isRevoked) cannot express more than two states.

  Enum values:
  ├── ACTIVE (0):  Certificate is valid and verifiable
  └── REVOKED (1): Certificate has been permanently revoked

  Why ACTIVE = 0 (default):
  Solidity initializes all storage to zero. CertificateStatus(0)
  = ACTIVE means a freshly stored record is automatically ACTIVE
  without an explicit assignment, saving one SSTORE.
  This is valid because the exists flag guards against
  uninitiated record reads (a zero-value non-existent record
  has exists = false, so it is never returned as ACTIVE).

FIELD 6: exists
  Type:        bool
  Required:    YES
  Initial:     false (all unset mappings)
  Set to true: at storeCertificate

  Purpose:
  Guards against the zero-value problem in mappings.
  In Solidity, reading a mapping key that was never set
  returns a zero-value struct (all fields = 0/false).
  Without this flag, getCertificateRecord("FAKE-UID")
  would return a struct with certificateHash = bytes32(0),
  which could be confused with a real record.

  The exists flag makes the non-existence case explicit:
  if (!certificates[certUid].exists) { revert NotFound(); }

  Why bool (not separate mapping):
  Stored inline in the struct, packed with status enum
  in the same 32-byte slot. No extra storage slot needed.

STRUCT STORAGE LAYOUT ANALYSIS:
──────────────────────────────────
CertificateRecord {
  bytes32 certificateHash;     → 32 bytes → SLOT N
  address issuingUniversity;   → 20 bytes ┐
  uint32  [padding to pack issuedAt]      │
  uint256 issuedAt;            → 32 bytes → SLOT N+1 (address + issuedAt won't pack due to uint256)
  uint256 revokedAt;           → 32 bytes → SLOT N+2
  CertificateStatus status;    → 1 byte   ┐ Packs into
  bool    exists;              → 1 byte   ┘ SLOT N+3
}

Total slots per record: 4 × 32 bytes = 128 bytes
At ~20,000 gas per new SSTORE slot (cold write): ~80,000 gas per record
[Matches architecture estimate of ~85,000 gas for storeCertificate]
```

## 4.2 Enum: CertificateStatus

```
ENUM: CertificateStatus
═════════════════════════

Values:
├── ACTIVE  (0)  — Certificate is valid and currently active
└── REVOKED (1)  — Certificate has been permanently revoked

Why only two states (not three or more):
The on-chain record only needs to represent the CURRENT CANONICAL
state. Intermediate states (PENDING, SUBMITTED) are off-chain
database concerns tracked in the blockchain_status column.
The blockchain has no concept of "pending" — a transaction
either happened (ACTIVE or REVOKED) or it didn't.

Post-MVP extension:
If SUSPENDED is ever needed, it would be added as:
ACTIVE (0), REVOKED (1), SUSPENDED (2)
This is backward compatible — existing ACTIVE records remain 0,
existing REVOKED records remain 1.
```

---

**[Design Decision A]** The `CertificateRecord` struct stores the **minimum fields** needed to serve all verification and revocation use cases. Student name, university name, degree title — none of these are stored. **[Why]** The architecture blueprint explicitly lists these as off-chain data for privacy reasons. **[Requirement satisfied]** Privacy requirement (blockchain is public; PII must not be on-chain); gas efficiency (each extra field costs ~20,000 gas cold SSTORE). **[Alternative rejected]** Some designs include a `metadataHash` field that is a hash of the off-chain metadata. This is architecturally valid but not required for MVP — the sha256_hash already serves as the document fingerprint.

---

# SECTION 5: MAPPINGS

## 5.1 Complete Mapping Specification

```
MAPPING 1: authorizedIssuers
══════════════════════════════

Declaration:    mapping(address => bool) private authorizedIssuers
Key Type:       address (20 bytes, Ethereum wallet)
Value Type:     bool (1 bit, stored as 32 bytes in EVM)
Initial State:  All addresses map to false

Purpose & Use Cases:
├── onlyAuthorizedIssuer modifier: authorizedIssuers[msg.sender]
├── isAuthorizedIssuer(addr) view function: authorizedIssuers[addr]
├── authorizeIssuer(): sets authorizedIssuers[addr] = true
└── deauthorizeIssuer(): sets authorizedIssuers[addr] = false

Relationship to Database:
├── DB table: universities.wallet_address
├── When a university is onboarded, their wallet_address is stored in DB
├── Platform admin calls authorizeIssuer(wallet_address) on contract
└── The two systems are synchronized: DB is the source of institution
    identity; contract is the source of cryptographic authorization

Security Properties:
├── Cannot authorize zero address (checked in authorizeIssuer)
├── Cannot authorize owner address (separation of concerns)
├── Deauthorization is immediate — next storeCertificate attempt fails
└── Previously stored certificates by a deauthorized issuer remain valid
    (revoke the individual certificates; deauthorization is forward-only)

Gas Cost:
├── Read (cold): ~2,100 gas
├── Read (warm): ~100 gas
├── Write true (cold → true): ~20,000 gas
└── Write false (true → false): ~2,900 gas (only clearing non-zero)


MAPPING 2: certificates
══════════════════════════

Declaration:    mapping(string => CertificateRecord) private certificates
Key Type:       string (certificate UID, e.g., "MIT-2025-00142")
Value Type:     CertificateRecord (struct, 4 storage slots)
Initial State:  All keys map to zero-value CertificateRecord (exists=false)

Purpose & Use Cases:
├── storeCertificate(): INSERT new record
├── revokeCertificate(): UPDATE status + revokedAt
├── getCertificateRecord(): READ full struct
└── verifyCertificate(): READ hash + status for comparison

Why string key (not bytes32 keccak of string):
String keys are more transparent to external observers who
know the certificate UID. Using keccak256(certUid) as the key
would be equivalent at the EVM level (Solidity already hashes
string keys internally for mapping storage slot calculation),
but using the raw string in the ABI makes the intent clear.

Certificate UID Format Constraints (enforced in storeCertificate):
├── Must not be empty string
├── Maximum length: 50 characters (matches DB VARCHAR(50))
└── Format validation: done off-chain; contract trusts the issuer

Immutability Properties:
├── Insertion: allowed once per UID (exists check)
├── Update: ONLY status and revokedAt fields (via revokeCertificate)
├── Delete: IMPOSSIBLE (no delete function; Solidity mapping cannot delete)
└── Hash field: NEVER modified after initial storage

Gas Profile per Operation:
├── First-time write (4 new slots): ~80,000-85,000 gas
├── Revocation (update 1 slot): ~30,000-35,000 gas
└── Read (view call): 0 ETH, ~5,000 gas (off-chain call)
```

## 5.2 Why No Additional Mappings

```
REJECTED ADDITIONAL MAPPINGS
══════════════════════════════

mapping(address => string[]) issuerCertificates  [REJECTED]
  Purpose: Track all cert UIDs issued by a given university wallet
  Rejection reason: Dynamic arrays in mappings are expensive to maintain
  (SSTORE per element). Off-chain, the database provides this query.
  Blockchain events (CertificateStored with indexed issuer) serve the
  same purpose for on-chain enumeration via event filtering.

mapping(bytes32 => string) hashToCertUid  [REJECTED]
  Purpose: Reverse lookup — find cert UID from hash
  Rejection reason: The database handles this lookup (index on sha256_hash).
  Duplicating it on-chain doubles storage cost per issuance (~20,000 gas).
  The verification workflow always provides the cert UID as input.

mapping(address => uint256) issuerCertificateCount  [REJECTED]
  Purpose: Count certificates per issuer
  Rejection reason: totalCertificates covers platform-level counting.
  Per-issuer counts are operational metrics served by the DB.
  Adding this mapping costs ~20,000 gas per issuance for zero
  verification benefit.
```

---

**[Design Decision A]** The certificate mapping uses the **human-readable string UID as the key** rather than a bytes32 hash of the UID. **[Why]** This matches the architecture blueprint's certificate_uid format exactly. External tools, block explorers, and developers can read event logs and immediately understand which certificate UID was stored, without needing a lookup table to decode a hash. **[Requirement satisfied]** Transparency of the blockchain record; debuggability during development. **[Alternative rejected]** `mapping(bytes32 => CertificateRecord)` with `keccak256(abi.encodePacked(certUid))` as the key is technically equivalent at the EVM level but opaque at the ABI level. The marginal gas saving (avoiding string parameter in calldata) is ~200-500 gas per call — not worth sacrificing readability.

---

# SECTION 6: EVENTS

## 6.1 Event Design Philosophy

Events are the contract's output channel to the off-chain world. Every state change that an off-chain system might need to react to emits an event. Events are stored in transaction receipt logs — they cost significantly less gas than storage (375 gas per log byte vs 20,000 gas per storage slot) and are queryable by off-chain indexers.

```
EVENT 1: CertificateStored
═══════════════════════════

Declaration:
event CertificateStored(
    string  indexed certUid,
    bytes32 indexed certificateHash,
    address indexed issuingUniversity,
    uint256         issuedAt,
    uint256         totalCertificatesOnChain
);

Indexed Fields: certUid, certificateHash, issuingUniversity
Non-indexed Fields: issuedAt, totalCertificatesOnChain

Emitted by: storeCertificate() on success

Purpose:
Announces that a new certificate hash has been permanently anchored.
The backend listens for this event to:
├── Confirm the TX succeeded and the hash was stored
├── Update blockchain_transactions.status = CONFIRMED
├── Update certificates.blockchain_status = CONFIRMED
├── Record block_number, confirmed_at in blockchain_transactions
└── Trigger QR code generation workflow

Why certUid is indexed:
Enables off-chain filtering: "give me all events for MIT-2025-00142"
The EVM stores indexed event topics as keccak256 hashes, enabling
Bloom filter-based event log queries.

Why certificateHash is indexed:
Enables the reverse lookup: "was this specific hash ever stored?"
An off-chain service could detect if the same hash appears under
multiple certificate UIDs (should be impossible, but detectable).

Why issuingUniversity is indexed:
Enables university-specific event filtering: "all certificates ever
issued by wallet 0x..." without scanning all contract logs.

Why totalCertificatesOnChain is NOT indexed:
It is a counter — not useful for filtering. Non-indexed data is
stored in the event ABI-encoded data field, which is cheaper
than indexed topics (each indexed topic costs 375 extra gas).

Gas cost: ~1,500-2,000 gas for this event emission


EVENT 2: CertificateRevoked
════════════════════════════

Declaration:
event CertificateRevoked(
    string  indexed certUid,
    address indexed revokedByUniversity,
    uint256         revokedAt,
    uint256         totalRevocationsOnChain
);

Indexed Fields: certUid, revokedByUniversity
Non-indexed Fields: revokedAt, totalRevocationsOnChain

Emitted by: revokeCertificate() on success

Purpose:
Announces that a certificate has been revoked. The backend
listens for this event to:
├── Update certificates.blockchain_status = REVOKED
├── Update certificates.is_active = FALSE
├── Record revoked_at in certificates table
└── Alert the student that their credential was revoked

Why we do NOT include certificateHash in this event:
The hash is already recorded in the original CertificateStored event.
An observer can reconstruct the full revocation context by querying
both events for the same certUid. Redundancy wastes gas.

Why revokedByUniversity is indexed:
Security monitoring: if a university wallet is compromised and
starts mass-revoking certificates, this index enables rapid
detection and investigation.

Gas cost: ~1,200-1,500 gas for this event emission


EVENT 3: IssuerAuthorized
══════════════════════════

Declaration:
event IssuerAuthorized(
    address indexed issuerAddress,
    address indexed authorizedBy,
    uint256         authorizedAt
);

Indexed Fields: issuerAddress, authorizedBy
Non-indexed Fields: authorizedAt

Emitted by: authorizeIssuer() on success

Purpose:
Creates an immutable on-chain record of when each university wallet
was granted issuing authority. Enables audit: "has wallet 0x... ever
been authorized to issue certificates on this platform?"

Why both addresses are indexed:
issuerAddress: "when was this university authorized?"
authorizedBy: should always be the owner; if it isn't,
              that indicates a security compromise

Gas cost: ~1,200-1,500 gas


EVENT 4: IssuerDeauthorized
════════════════════════════

Declaration:
event IssuerDeauthorized(
    address indexed issuerAddress,
    address indexed deauthorizedBy,
    uint256         deauthorizedAt,
    string          reason
);

Indexed Fields: issuerAddress, deauthorizedBy
Non-indexed Fields: deauthorizedAt, reason

Emitted by: deauthorizeIssuer() on success

Purpose:
Records the removal of issuing authority. The reason field allows
platform admins to document why (e.g., "compromised wallet",
"university closed", "annual renewal"). This reason is stored in
the event logs, not in contract storage (free to emit, not to store).

Why reason is a string in event (not storage):
Event data does not cost storage gas. A string in an event
costs only calldata gas (3-16 gas per byte) + log gas (375 gas/byte
for non-indexed data). This is acceptable for an admin function
called rarely.

Gas cost: ~1,500-2,000 gas (varies with reason string length)


EVENT 5: OwnershipTransferred
══════════════════════════════

Declaration:
event OwnershipTransferred(
    address indexed previousOwner,
    address indexed newOwner,
    uint256         transferredAt
);

Indexed Fields: previousOwner, newOwner

Emitted by: transferOwnership() on success

Purpose:
Standard ownership transfer audit event. Critical for security:
if the owner key is compromised and ownership transferred to
an attacker wallet, this event is visible on-chain and enables
rapid response.

Gas cost: ~1,200-1,500 gas
```

## 6.2 Event Indexing Strategy Summary

```
INDEXED TOPIC ALLOCATION (max 3 indexed topics per event + event signature):
══════════════════════════════════════════════════════════════════════════════

Event                  | Topic 0 (sig)  | Topic 1       | Topic 2           | Topic 3
-----------------------|----------------|---------------|-------------------|------------------
CertificateStored      | keccak256(sig) | certUid       | certificateHash   | issuingUniversity
CertificateRevoked     | keccak256(sig) | certUid       | revokedByUniversity | -
IssuerAuthorized       | keccak256(sig) | issuerAddress | authorizedBy      | -
IssuerDeauthorized     | keccak256(sig) | issuerAddress | deauthorizedBy    | -
OwnershipTransferred   | keccak256(sig) | previousOwner | newOwner          | -

Note: Solidity events have a maximum of 3 indexed parameters
(4 topics including the event signature). All events respect this limit.
```

---

**[Design Decision A]** All state-changing functions emit events with **indexed parameters** chosen for the most likely off-chain query patterns. **[Why]** The FastAPI backend uses Web3.py to subscribe to contract events and react to them (updating blockchain_transactions, certificates status). Without indexed parameters, the backend would have to scan all contract logs and filter in Python — inefficient and unreliable. Indexed topics enable the Ethereum node to use Bloom filters for efficient event retrieval. **[Requirement satisfied]** Verification logs (backend can reconstruct full issuance history from events); blockchain confirmation callback. **[Alternative rejected]** Non-indexed events are cheaper (~375 gas per indexed topic saved) but make off-chain processing O(n) over all events rather than O(log n) via Bloom filter index.

---

# SECTION 7: MODIFIERS

## 7.1 Complete Modifier Specification

```
MODIFIER 1: onlyOwner
══════════════════════

Declaration:
modifier onlyOwner() {
    require: msg.sender == owner
    error: NotContractOwner(msg.sender, owner)
    position: _;  (function body executes after check)
}

Applied to:
├── authorizeIssuer(address)
├── deauthorizeIssuer(address)
└── transferOwnership(address)

Behavior:
Reverts with custom error NotContractOwner if the caller
is not the owner address. Custom errors (EIP-838) cost
less gas than require(condition, "string message") and
provide typed error information to callers.

Security consideration:
This is a single-owner model. The owner is a single wallet.
If the owner's private key is compromised, the attacker can
manipulate the authorized issuer list. The mitigation is:
(a) Owner wallet should be a hardware wallet or multisig (recommended)
(b) OwnershipTransferred event alerts monitoring systems immediately
(c) Owner can ONLY manage issuers — cannot forge certificates


MODIFIER 2: onlyAuthorizedIssuer
══════════════════════════════════

Declaration:
modifier onlyAuthorizedIssuer() {
    require: authorizedIssuers[msg.sender] == true
    error: NotAuthorizedIssuer(msg.sender)
    position: _;
}

Applied to:
├── storeCertificate(string, bytes32)
└── revokeCertificate(string)

Behavior:
Reverts with NotAuthorizedIssuer if the calling wallet is not
in the authorized issuer whitelist. This is the primary access
control gate for all write operations.

Critical security property:
The check uses authorizedIssuers[msg.sender] directly — not a
parameter passed by the caller. The caller CANNOT fake their
authorization status. The Ethereum protocol guarantees that
msg.sender is the wallet that signed the transaction.


MODIFIER 3: certificateMustExist(string certUid)
══════════════════════════════════════════════════

Declaration:
modifier certificateMustExist(string calldata certUid) {
    require: certificates[certUid].exists == true
    error: CertificateNotFound(certUid)
    position: _;
}

Applied to:
├── revokeCertificate(string)
└── getCertificateRecord(string) [optional — function returns empty otherwise]

Behavior:
Reverts with CertificateNotFound if the certificate UID has
no associated record. Prevents operations on phantom records.

Why string calldata (not memory):
calldata is read-only and does not copy the string to memory.
For a modifier that only reads the string to use it as a mapping
key, calldata is more gas-efficient (~200-500 gas saved per call
for string parameters).


MODIFIER 4: certificateMustBeActive(string certUid)
══════════════════════════════════════════════════════

Declaration:
modifier certificateMustBeActive(string calldata certUid) {
    require: certificates[certUid].status == CertificateStatus.ACTIVE
    error: CertificateAlreadyRevoked(certUid, certificates[certUid].revokedAt)
    position: _;
}

Applied to:
└── revokeCertificate(string)

Behavior:
Reverts with CertificateAlreadyRevoked (including the timestamp
of the original revocation) if an attempt is made to revoke an
already-revoked certificate. Enforces one-way ACTIVE → REVOKED.

Why include revokedAt in the error:
When this error is thrown, it means someone is trying to revoke
a certificate that was already revoked. The revokedAt timestamp
in the error tells the caller exactly when it was revoked,
enabling rapid diagnosis without requiring a separate query.


MODIFIER 5: onlyOriginalIssuer(string certUid)
════════════════════════════════════════════════

Declaration:
modifier onlyOriginalIssuer(string calldata certUid) {
    require: certificates[certUid].issuingUniversity == msg.sender
    error: NotOriginalIssuer(msg.sender, certificates[certUid].issuingUniversity)
    position: _;
}

Applied to:
└── revokeCertificate(string)

Behavior:
Even if a university wallet is authorized to issue certificates,
it can only revoke certificates it originally issued. University A
cannot revoke University B's certificates.

Why this matters:
In a platform with 100 authorized universities, any of them could
call revokeCertificate() on any certificate if this check were absent.
onlyAuthorizedIssuer ensures the caller is A university.
onlyOriginalIssuer ensures the caller is THE university that issued
this specific certificate.

The two modifiers work together:
onlyAuthorizedIssuer: are you allowed to issue at all?
onlyOriginalIssuer:   did you issue THIS specific certificate?


MODIFIER 6: validCertHash(bytes32 certHash)
════════════════════════════════════════════

Declaration:
modifier validCertHash(bytes32 certHash) {
    require: certHash != bytes32(0)
    error: InvalidCertificateHash()
    position: _;
}

Applied to:
└── storeCertificate(string, bytes32)

Behavior:
Rejects the zero hash. A bytes32(0) hash would create a record
where any verification submitting bytes32(0) would match — a
critical security vulnerability that would allow "verifying"
any fake certificate UID as authentic.


MODIFIER 7: validCertUid(string certUid)
══════════════════════════════════════════

Declaration:
modifier validCertUid(string calldata certUid) {
    require: bytes(certUid).length > 0
    require: bytes(certUid).length <= 50
    error: InvalidCertificateUid(certUid, bytes(certUid).length)
    position: _;
}

Applied to:
└── storeCertificate(string, bytes32)

Behavior:
Rejects empty strings and strings longer than 50 characters.
Empty string would create a record at the empty key, potentially
conflicting with zero-value mapping entries.
50-char limit matches the DB VARCHAR(50) constraint, ensuring
the UID fits in the expected format.

Why 50 characters specifically:
Matches certificates.certificate_uid VARCHAR(50) in the database.
A UID like "MIT-2025-00142" is 14 chars; even the longest possible
UID (20-char university code + year + sequence) fits well within 50.
```

## 7.2 Custom Error Declarations

```
CUSTOM ERROR DECLARATIONS
══════════════════════════

Using EIP-838 custom errors throughout (Solidity 0.8.4+)
Reason: Gas efficient, typed, informative — better than require strings

error NotContractOwner(address caller, address owner);
error NotAuthorizedIssuer(address caller);
error NotOriginalIssuer(address caller, address originalIssuer);
error CertificateAlreadyExists(string certUid);
error CertificateNotFound(string certUid);
error CertificateAlreadyRevoked(string certUid, uint256 originalRevokedAt);
error InvalidCertificateHash();
error InvalidCertificateUid(string certUid, uint256 length);
error InvalidAddress(address addr);
error IssuerAlreadyAuthorized(address issuer);
error IssuerNotAuthorized(address issuer);
error OwnerCannotBeIssuer(address ownerAddress);
error CannotTransferToZeroAddress();
error CannotAuthorizeZeroAddress();
error CannotAuthorizeOwner(address ownerAddress);

Gas savings vs require strings:
Custom errors cost ~50-200 gas per revert (encoding the selector + parameters)
require("string message") costs 3 gas per character in the string + MSTORE costs
For "NotAuthorizedIssuer": custom error ≈ 50 gas vs "Not authorized: " = ~200 gas
Across many transactions over the contract's lifetime, this is significant.
```

---

**[Design Decision A]** Seven modifiers are defined, with **modifier composition** on `revokeCertificate()` (four modifiers applied: `onlyAuthorizedIssuer`, `certificateMustExist`, `certificateMustBeActive`, `onlyOriginalIssuer`). **[Why]** Each modifier is a single, independently testable concern. Composing them on `revokeCertificate()` means each concern is verified atomically before the function body executes. The order matters: `onlyAuthorizedIssuer` runs first (cheapest check that fails most unauthorized calls), then existence, then status, then issuer match (most expensive — requires a mapping lookup). **[Requirement satisfied]** Certificate revocation security; issuer isolation. **[Alternative rejected]** Embedding all these checks as `require` statements directly in the function body would work but is less reusable and harder to test in isolation.

---

# SECTION 8: ACCESS CONTROL DESIGN

## 8.1 Role Hierarchy

```
ACCESS CONTROL HIERARCHY
═════════════════════════

TIER 0: ETHEREUM PROTOCOL (cannot be overridden)
│   Guarantees: msg.sender is cryptographically authenticated
│   Guarantees: Transactions cannot be forged
│   Guarantees: Block timestamps cannot be manipulated beyond ~15s
│
TIER 1: CONTRACT OWNER
│   Address: Deployer wallet (or transferred to multisig post-deploy)
│   Capabilities:
│   ├── authorizeIssuer(address)     → Add university to whitelist
│   ├── deauthorizeIssuer(address)   → Remove university from whitelist
│   └── transferOwnership(address)   → Transfer admin control
│   Cannot:
│   ├── storeCertificate()          → Blocked by onlyAuthorizedIssuer
│   ├── revokeCertificate()         → Blocked by onlyAuthorizedIssuer
│   └── Read private state directly → Must use public view functions
│
TIER 2: AUTHORIZED ISSUERS (University Wallets)
│   Address: University MetaMask wallet (registered in DB + authorized on contract)
│   Capabilities:
│   ├── storeCertificate(uid, hash)  → Write new certificate hash
│   └── revokeCertificate(uid)       → Revoke their own certificates only
│   Cannot:
│   ├── authorizeIssuer()           → Blocked by onlyOwner
│   ├── deauthorizeIssuer()         → Blocked by onlyOwner
│   ├── revoke another university's certificate → Blocked by onlyOriginalIssuer
│   └── Overwrite existing cert     → Blocked by certificateMustNotExist check
│
TIER 3: ANY ADDRESS (Public)
    Capabilities:
    ├── verifyCertificate(uid, hash)  → Read-only; free; no auth required
    ├── getCertificateRecord(uid)     → Read-only; free; no auth required
    ├── isAuthorizedIssuer(address)   → Read-only; free; no auth required
    ├── getOwner()                    → Read-only; free; no auth required
    └── getCertificateCount()         → Read-only; free; no auth required
    Cannot:
    └── All write functions           → Blocked by onlyOwner or onlyAuthorizedIssuer
```

## 8.2 Access Control State Transition Diagram

```
ACCESS CONTROL STATE MACHINE
══════════════════════════════

University Wallet Lifecycle:
                                    OWNER CALLS
                                    authorizeIssuer(wallet)
                                         │
INITIAL STATE                            ▼
[NOT_AUTHORIZED] ────────────────► [AUTHORIZED_ISSUER]
     ▲                                   │
     │                                   │ Can issue + revoke own certs
     │                                   │
     │           OWNER CALLS             │
     └─────── deauthorizeIssuer(wallet) ◄┘
                                         │
                                         │ Previously stored certs
                                         │ remain valid on-chain
                                         ▼
                              [DEAUTHORIZED — forward only]
                              Future storeCertificate() calls: REJECTED
                              Past stored certificates: UNAFFECTED

Certificate Lifecycle on Contract:
    [NOT_EXISTS]
         │
         │ storeCertificate(uid, hash) called by AUTHORIZED_ISSUER
         │
         ▼
    [ACTIVE] ─────────────────────────────────────────────────────►
         │         revokeCertificate(uid) called by ORIGINAL_ISSUER
         │
         ▼
    [REVOKED] ← TERMINAL STATE (no transition out)
```

## 8.3 Two-Factor Trust Model

```
TWO-FACTOR TRUST MODEL
════════════════════════

For a certificate hash to be stored, TWO independent factors must align:

FACTOR 1: PLATFORM AUTHORIZATION (Contract Owner)
├── The contract owner has explicitly added the university wallet
│   to the authorizedIssuers mapping
├── This represents: "the platform operator vouches for this institution"
└── Without this, the wallet cannot call storeCertificate()

FACTOR 2: CRYPTOGRAPHIC IDENTITY (MetaMask Wallet)
├── The university admin must possess the private key for the
│   authorized wallet address
├── MetaMask signs the transaction with that private key
├── The Ethereum protocol verifies the signature before execution
└── Without this, the wallet address is authorized but cannot transact

COMBINED GUARANTEE:
A successful storeCertificate() transaction proves:
├── The platform operator approved this institution
├── The institution's wallet holder chose to anchor this specific hash
├── At this exact block timestamp
├── For this exact certificate UID
└── This proof is cryptographically irrefutable and permanently visible

This two-factor model means:
├── A hacked platform server cannot forge certificates (no private key)
├── A rogue university cannot issue without platform approval
└── Certificate fraud requires SIMULTANEOUS compromise of BOTH factors
```

---

**[Design Decision A]** The access control system uses **address-based whitelist** rather than on-chain identity documents or ERC-721 role tokens. **[Why]** The simplest mechanism that achieves the required security properties. MetaMask wallet addresses are the natural identity primitive for Ethereum. Adding an ERC-721 "university credential token" would introduce a transferable object that could be sold or stolen, creating new attack vectors. A simple mapping is non-transferable, instantaneously updatable, and O(1) to check. **[Requirement satisfied]** Authorized university issuers requirement; security architecture. **[Alternative rejected]** OpenZeppelin's `AccessControl.sol` provides role-based access control with multiple roles and role admins. For MVP with two roles (owner and issuer), this is over-engineered. The custom implementation is simpler, cheaper, and more auditable.

---

# SECTION 9: CERTIFICATE STORAGE WORKFLOW

## 9.1 Complete storeCertificate() Function Blueprint

```
FUNCTION: storeCertificate()
═════════════════════════════

Signature:
function storeCertificate(
    string calldata certUid,
    bytes32 certHash
) external
  onlyAuthorizedIssuer
  validCertUid(certUid)
  validCertHash(certHash)

Visibility:     external (not internal; saves ~200 gas vs public)
State Mutability: State-changing (not view/pure)
Return:         none (result communicated via event)

Why external (not public):
external functions receive calldata directly without copying to memory.
For string parameters, this saves memory allocation gas.
external functions cannot be called internally (only via this.f()),
which is acceptable since storeCertificate is only called from outside.

EXECUTION FLOW:
────────────────

Step 1: Modifier Chain Execution
├── onlyAuthorizedIssuer: authorizedIssuers[msg.sender] == true?
│   → If false: revert NotAuthorizedIssuer(msg.sender)
├── validCertUid: bytes(certUid).length > 0 && <= 50?
│   → If false: revert InvalidCertificateUid(certUid, length)
└── validCertHash: certHash != bytes32(0)?
    → If false: revert InvalidCertificateHash()

Step 2: Duplicate Prevention Check
├── Check: certificates[certUid].exists == false
└── If true (already exists): revert CertificateAlreadyExists(certUid)

Why check in function body (not modifier):
The duplicate check accesses the mapping using certUid as a key.
The certUid parameter must be validated (non-empty, valid length)
BEFORE using it as a mapping key. Modifier execution order
ensures validCertUid runs before this check.
Placing this check in the function body (after modifiers)
is the correct pattern.

Step 3: Record Construction
Build CertificateRecord in memory:
├── certificateHash:     certHash (the bytes32 parameter)
├── issuingUniversity:   msg.sender (the calling wallet)
├── issuedAt:            block.timestamp (current block time)
├── revokedAt:           0 (not revoked)
├── status:              CertificateStatus.ACTIVE (= 0, default)
└── exists:              true

Step 4: Storage Write
├── certificates[certUid] = newRecord
└── totalCertificates += 1

Gas allocation for this step:
├── New SSTORE slot 1 (certificateHash): ~20,000 gas
├── New SSTORE slot 2 (issuingUniversity + padding): ~20,000 gas
├── New SSTORE slot 3 (issuedAt): ~20,000 gas
├── New SSTORE slot 4 (revokedAt=0, status=0, exists=true): ~20,000 gas
└── totalCertificates SSTORE (increment): ~5,000 gas (warm slot)
Total storage: ~85,000 gas ← matches architecture estimate

Step 5: Event Emission
emit CertificateStored(
    certUid,
    certHash,
    msg.sender,
    block.timestamp,
    totalCertificates
);

Step 6: Return (implicit void)

COMPLETE GAS PROFILE:
├── Modifier checks:          ~5,000 gas
├── Duplicate existence check: ~2,100 gas (cold mapping read)
├── Storage writes (4 slots): ~80,000 gas
├── Event emission:            ~2,000 gas
├── Base TX overhead:          ~21,000 gas
└── Total estimate:            ~110,000 gas (conservative)
    Architecture estimate:     ~85,000 gas (storage only portion matches)
```

## 9.2 storeCertificate() Revert Conditions Map

```
COMPLETE REVERT CONDITION MATRIX FOR storeCertificate()
══════════════════════════════════════════════════════════

Condition                          Error                        When
─────────────────────────────────────────────────────────────────────────────
Caller not in authorizedIssuers   NotAuthorizedIssuer          Modifier
certUid is empty string           InvalidCertificateUid        Modifier
certUid length > 50 chars         InvalidCertificateUid        Modifier
certHash == bytes32(0)            InvalidCertificateHash       Modifier
certificates[certUid].exists=true CertificateAlreadyExists     Function body
```

---

**[Design Decision A]** `storeCertificate()` takes the `bytes32 certHash` parameter rather than a `string hexHash` and converting internally. **[Why]** The caller (frontend via ethers.js) is responsible for encoding the SHA-256 hex string as bytes32. This is a one-time encoding that happens on the frontend. If the encoding were done in the contract (string → bytes32 conversion), it would add ~3,000-5,000 gas per call and require string parsing in Solidity, which is error-prone. The bytes32 parameter is also type-safe — you cannot accidentally pass a non-hash value. **[Requirement satisfied]** SHA-256 hash storage efficiency; gas optimization. **[Alternative rejected]** `string calldata hexHash` with in-contract hex-to-bytes32 conversion would make the ABI more human-readable but add gas cost, Solidity string manipulation complexity, and potential encoding bugs.

---

# SECTION 10: CERTIFICATE VERIFICATION WORKFLOW

## 10.1 Complete verifyCertificate() Function Blueprint

```
FUNCTION: verifyCertificate()
══════════════════════════════

Signature:
function verifyCertificate(
    string calldata certUid,
    bytes32 submittedHash
) external view
  returns (
    bool    isValid,
    CertificateStatus status
  )

Visibility:     external
State Mutability: view (reads state; does not modify; costs 0 ETH)
Return:         (bool isValid, CertificateStatus status)

KEY PROPERTY: This is a VIEW function.
No gas cost for the caller (when called as eth_call, not in a TX).
Anyone on Earth can call this function for free.
This is the fundamental trustless verification property.

EXECUTION FLOW:
────────────────

Step 1: Retrieve stored record
CertificateRecord storage record = certificates[certUid];

Why storage (not memory):
Using storage reference avoids copying the full struct to memory.
We only read from it; a storage pointer is cheaper.

Step 2: Existence Check
├── If !record.exists:
│   └── return (false, CertificateStatus.ACTIVE)
│       Note: returning ACTIVE here is semantically meaningless
│       because isValid=false is the signal for "not found".
│       The status value is irrelevant when isValid=false.
│       Alternative: revert CertificateNotFound(certUid)
│       Decision: return (false, status) rather than revert
│       Rationale: verification is a query operation; reverts are
│       for invalid operations. A not-found certificate is a valid
│       query result, not an error condition.

Step 3: Revocation Check (Priority Check)
├── If record.status == CertificateStatus.REVOKED:
│   └── return (false, CertificateStatus.REVOKED)
│       Note: a REVOKED certificate is NEVER valid regardless of
│       whether the submitted hash matches. The revocation is the
│       authoritative signal. This check MUST happen before the
│       hash comparison — even a perfect hash match returns false
│       if the certificate is revoked.

Step 4: Hash Comparison
├── bool hashMatches = (record.certificateHash == submittedHash)
└── return (hashMatches, CertificateStatus.ACTIVE)
    ├── hashMatches = true  → AUTHENTIC (isValid=true, ACTIVE)
    └── hashMatches = false → TAMPERED (isValid=false, ACTIVE)

Step 5: Return (implicit in above steps)

DECISION TREE VISUALIZATION:
──────────────────────────────

verifyCertificate(certUid, submittedHash)
           │
           ▼
    record.exists?
   ┌───── NO ──────┐
   │               ▼
   │     return (false, ACTIVE)  → caller interprets as NOT_FOUND
   │
   └───── YES ─────┐
                   ▼
          record.status == REVOKED?
         ┌───── YES ─────┐
         │               ▼
         │     return (false, REVOKED)  → REVOKED
         │
         └───── NO ──────┐
                         ▼
          record.certificateHash == submittedHash?
         ┌───── YES ─────┐        ┌─── NO ────┐
         │               ▼        │            ▼
         │    return (true,        │    return (false,
         │           ACTIVE)      │           ACTIVE)
         │    → AUTHENTIC         │    → TAMPERED
         └───────────────┘        └────────────┘

GAS PROFILE (as eth_call — FREE):
├── Storage read (cold): ~2,100 gas
├── Comparison opcodes:   ~10-50 gas
└── Total: ~2,200 gas (but free as eth_call; only costs gas in TX context)

WHY THE RETURN TYPE IS (bool, CertificateStatus):
───────────────────────────────────────────────────
The backend (verification_service.py) needs to distinguish:
├── (true,  ACTIVE)   → AUTHENTIC     — certificate valid, show green
├── (false, REVOKED)  → REVOKED       — certificate revoked, show orange
├── (false, ACTIVE)   → TAMPERED/NOT_FOUND — either tampered or not found
│   [Backend differentiates: if cert found in DB but hash mismatch → TAMPERED;
│    if not in DB → NOT_FOUND]

The two return values together give the backend everything needed
to construct the correct VerificationResult without additional queries.
```

## 10.2 getCertificateRecord() Function Blueprint

```
FUNCTION: getCertificateRecord()
═════════════════════════════════

Signature:
function getCertificateRecord(
    string calldata certUid
) external view
  returns (CertificateRecord memory)

Purpose:
Returns the complete CertificateRecord struct for a given UID.
Used by the backend to cross-validate after TX confirmation:
"Does the on-chain record match what we stored in the database?"

Return: CertificateRecord memory (full struct copy)

Note on return type:
Returns memory copy of the struct.
storage return type would expose internal storage pointers — not allowed.
The caller receives a snapshot of the state at the time of the call.

Behavior:
├── If !certificates[certUid].exists: returns zero-value struct
│   (exists=false signals non-existence to caller)
└── If exists: returns full CertificateRecord

Why not revert on non-existence:
Same rationale as verifyCertificate — queries should return
data, not errors. The exists field in the returned struct
communicates non-existence cleanly.
```

---

**[Design Decision A]** `verifyCertificate()` returns `(false, CertificateStatus.ACTIVE)` for both the NOT_FOUND case and the TAMPERED case (when hash doesn't match). The backend differentiates these two cases. **[Why]** On the contract, both cases mean "this hash does not match a valid active record." The distinction between "never existed" and "exists but tampered" is an off-chain concern that requires database context (does a certificate with this UID exist in the DB?). Adding a third return value to the contract (or a separate `exists` return) for this distinction would add contract complexity for logic that belongs in the verification service. **[Requirement satisfied]** Tamper detection with clean separation of concerns. **[Alternative rejected]** A three-return-value function `(bool isValid, bool exists, CertificateStatus status)` would preempt the backend's domain logic. The contract should provide raw truth; the backend should interpret it.

---

# SECTION 11: CERTIFICATE REVOCATION WORKFLOW

## 11.1 Complete revokeCertificate() Function Blueprint

```
FUNCTION: revokeCertificate()
══════════════════════════════

Signature:
function revokeCertificate(
    string calldata certUid
) external
  onlyAuthorizedIssuer
  certificateMustExist(certUid)
  certificateMustBeActive(certUid)
  onlyOriginalIssuer(certUid)

Visibility:     external
State Mutability: State-changing

EXECUTION FLOW:
────────────────

Step 1: Modifier Chain (4 modifiers)
├── onlyAuthorizedIssuer:
│   authorizedIssuers[msg.sender] == true?
│   → If false: revert NotAuthorizedIssuer(msg.sender)
│
├── certificateMustExist(certUid):
│   certificates[certUid].exists == true?
│   → If false: revert CertificateNotFound(certUid)
│
├── certificateMustBeActive(certUid):
│   certificates[certUid].status == ACTIVE?
│   → If false: revert CertificateAlreadyRevoked(certUid, revokedAt)
│
└── onlyOriginalIssuer(certUid):
    certificates[certUid].issuingUniversity == msg.sender?
    → If false: revert NotOriginalIssuer(msg.sender, originalIssuer)

Step 2: State Updates (2 SSTORE operations)
├── certificates[certUid].status = CertificateStatus.REVOKED
│   Gas: ~5,000 gas (changing 0→1 in packed slot — warm write)
└── certificates[certUid].revokedAt = block.timestamp
    Gas: ~20,000 gas (writing to previously-zero slot)

Note: certificateHash and issuingUniversity are NOT modified.
They remain as permanent evidence of what was issued.

Step 3: Counter Update
└── totalRevocations += 1
    Gas: ~5,000 gas (warm write to slot 2)

Step 4: Event Emission
emit CertificateRevoked(
    certUid,
    msg.sender,
    block.timestamp,
    totalRevocations
);
Gas: ~1,500 gas

COMPLETE GAS PROFILE:
├── Modifier checks (4 storage reads): ~8,400 gas
├── Status SSTORE:                      ~5,000 gas
├── revokedAt SSTORE:                  ~20,000 gas
├── totalRevocations increment:         ~5,000 gas
├── Event emission:                     ~1,500 gas
├── Base TX overhead:                  ~21,000 gas
└── Total estimate:                    ~60,900 gas
    Architecture estimate:             ~35,000 gas (storage portion)

COMPLETE REVERT CONDITION MATRIX FOR revokeCertificate()
══════════════════════════════════════════════════════════

Condition                               Error                           When
──────────────────────────────────────────────────────────────────────────────────────
Caller not in authorizedIssuers        NotAuthorizedIssuer             Modifier 1
certificates[certUid].exists = false   CertificateNotFound             Modifier 2
certificates[certUid].status = REVOKED CertificateAlreadyRevoked       Modifier 3
msg.sender != issuingUniversity        NotOriginalIssuer               Modifier 4

CRITICAL SECURITY PROPERTIES:
├── A deauthorized university CANNOT revoke its own certificates
│   (deauthorization removes them from authorizedIssuers mapping)
│   This means: once deauthorized, a university cannot be used to
│   mass-revoke certificates via a compromised key.
│   The platform admin MUST deauthorize the wallet BEFORE
│   the university revokes — or the two operations are separate
│   security decisions.
│
│   ARCHITECTURAL NOTE: This creates a deliberate trade-off.
│   If a university wallet is compromised:
│   ├── Attacker can issue fraudulent certificates (stopcertificate)
│   ├── Attacker can revoke legitimate certificates (revokeCertificate)
│   └── Owner should IMMEDIATELY deauthorize the compromised wallet
│       This stops FUTURE fraudulent issuances
│       But previously stored fraudulent certificates must be
│       individually revoked BY THE OWNER calling a special function
│       [See Future Upgrade Path section for emergency revocation]
│
└── One-way terminal state:
    REVOKED → REVOKED (no function to reverse revocation)
    This is enforced by certificateMustBeActive modifier.
    Even the contract owner cannot un-revoke.
    Once revoked, permanently revoked.
```

## 11.2 Emergency Revocation Consideration

```
EMERGENCY REVOCATION — ARCHITECTURAL NOTE
══════════════════════════════════════════

Scenario: University wallet is compromised. Attacker issues
10 fraudulent certificates before the owner deauthorizes the wallet.

Problem: Those 10 fraudulent certificates are ACTIVE on the chain.
revokeCertificate() requires msg.sender == issuingUniversity.
But the compromised wallet is now deauthorized — it passes
onlyAuthorizedIssuer? NO — it fails because deauthorization
set authorizedIssuers[compromisedWallet] = false.

Gap: There is no MVP mechanism to revoke fraudulent certificates
once the issuer wallet is deauthorized.

MVP Decision: ACCEPT this gap with documentation.
Reasoning:
├── This is a severe but rare scenario
├── The backend can mark these certificates as SUSPICIOUS in DB
├── The on-chain record shows they were issued (evidence preserved)
├── verifyFromDB will fail (university marked compromised in DB)
├── Platform can publish a list of compromised cert UIDs off-chain
└── Proper fix is an ownerEmergencyRevoke function (post-MVP)

Post-MVP Mitigation (Future Upgrade Path):
Add function ownerEmergencyRevoke(string certUid, string reason)
├── onlyOwner modifier
├── Allows owner to revoke any certificate for emergency reasons
├── Emits EmergencyRevocation event with reason
└── This is an emergency power — use requires governance process
```

---

**[Design Decision A]** `revokeCertificate()` checks `msg.sender == issuingUniversity` from the stored record, not from the current authorized issuer mapping. **[Why]** These two concepts are independent. A university could have its wallet rotated (deauthorized old, authorized new) but still need to revoke old certificates. By checking the stored `issuingUniversity` field, we respect the issuer at time of issuance. However, the `onlyAuthorizedIssuer` modifier also runs — meaning the original wallet must STILL be authorized to revoke. This is the designed trade-off (see Emergency Revocation note above). **[Requirement satisfied]** Certificate revocation by issuing university only; tamper prevention. **[Alternative rejected]** Checking only the `authorizedIssuers` mapping (not the stored `issuingUniversity`) would allow any currently-authorized university to revoke any other university's certificates — a severe multi-tenancy breach.

---

# SECTION 12: GAS OPTIMIZATION STRATEGY

## 12.1 Optimization Principles

```
GAS OPTIMIZATION PHILOSOPHY
════════════════════════════

Principle: Optimize for the most frequent operations first.
Order of frequency (highest to lowest):
1. verifyCertificate()      — Called many times per certificate (employers)
2. storeCertificate()       — Called once per certificate (issuance)
3. revokeCertificate()      — Called rarely (exceptional circumstances)
4. authorizeIssuer()        — Called once per university onboarding
5. deauthorizeIssuer()      — Called rarely

Since verifyCertificate() is a view function (zero ETH cost), the
primary optimization target is storeCertificate().
```

## 12.2 Implemented Optimizations

```
OPTIMIZATION 1: bytes32 for Hash Storage
══════════════════════════════════════════
Applied to: CertificateRecord.certificateHash
Savings: ~5,000-10,000 gas vs string storage
Mechanism: bytes32 is a fixed 32-byte type that fits exactly in one
           EVM storage slot. A string "sha256hex..." would require
           dynamic storage: a length slot + data slots.
           For a 64-char hex string: 1 slot for length + 2 slots for
           data = 3 slots vs 1 slot for bytes32.

OPTIMIZATION 2: calldata for String Parameters
═══════════════════════════════════════════════
Applied to: All external functions with string parameters
Savings: ~200-500 gas per call vs memory
Mechanism: calldata reads from transaction input directly without
           copying to memory. For string certUid (~15 chars),
           this avoids MSTORE operations and memory expansion gas.

OPTIMIZATION 3: Custom Errors (EIP-838)
═════════════════════════════════════════
Applied to: All revert conditions
Savings: ~50-200 gas per revert vs require("string")
Mechanism: Custom errors encode only a 4-byte selector + ABI-encoded
           parameters vs the full string in require().
           On happy path: zero difference. On revert path: meaningful savings.

OPTIMIZATION 4: external vs public Functions
═════════════════════════════════════════════
Applied to: All functions (all marked external)
Savings: ~200-400 gas for functions receiving string/bytes parameters
Mechanism: external functions avoid copying calldata to memory.
           public functions must copy parameters for potential internal calls.

OPTIMIZATION 5: Struct Packing in CertificateRecord
═════════════════════════════════════════════════════
Applied to: CertificateRecord.status and .exists
Savings: Packs two variables (1 byte enum + 1 byte bool) into one slot
         that otherwise would be separate 32-byte slots.
Mechanism: EVM storage is 32-byte slots. By placing status (enum, 1 byte)
           and exists (bool, 1 byte) adjacent in the struct definition,
           Solidity packs them into the same storage slot.
           Saves ~20,000 gas for the 4th struct slot (exists+status share slot 3).

OPTIMIZATION 6: Storage Reference in View Functions
═════════════════════════════════════════════════════
Applied to: verifyCertificate(), getCertificateRecord()
Savings: ~200-500 gas for large struct reads
Mechanism: Using CertificateRecord storage record = certificates[certUid]
           creates a pointer to storage rather than copying to memory.
           For view functions that only read a few fields,
           storage references avoid unnecessary MLOAD/MSTORE operations.

OPTIMIZATION 7: Conditional Short-Circuit in verifyCertificate()
═════════════════════════════════════════════════════════════════
Applied to: verifyCertificate() decision tree
Savings: ~100-200 gas for REVOKED certificates (skip hash comparison)
Mechanism: Status check BEFORE hash comparison. For revoked certs,
           the hash comparison (two MLOAD + EQ opcode) is skipped.
           For active certs: no overhead, same execution path.

OPTIMIZATION 8: Monotonic Counters (uint256)
═════════════════════════════════════════════
Applied to: totalCertificates, totalRevocations
Savings: No gas cost — these share already-required storage slots.
Mechanism: These counters update in warm slots (already read in the
           same transaction), costing ~5,000 gas vs ~20,000 for cold writes.
           They are valuable monitoring tools at negligible cost.

OPTIMIZATION 9: No On-Chain PII Storage
═════════════════════════════════════════
Applied to: All data that "could" go on-chain
Savings: ~80,000-120,000 gas per certificate (if name, degree stored)
Mechanism: The deliberate off-chain data decision from the architecture
           is the biggest single gas optimization.
           Every string field NOT stored on-chain is ~20,000 gas saved.
           5 excluded fields (name, degree, field, university name, expiry):
           ~100,000 gas saved per issuance.
```

## 12.3 Gas Budget Summary

```
GAS BUDGET ANALYSIS
════════════════════

Function              Budget      Optimized Est.  Category
─────────────────────────────────────────────────────────────────────
storeCertificate()    100,000     ~85,000-110,000  Acceptable
revokeCertificate()   60,000      ~50,000-65,000   Good
authorizeIssuer()     50,000      ~46,000-55,000   Good
deauthorizeIssuer()   30,000      ~25,000-35,000   Good
verifyCertificate()   FREE        ~0 ETH (eth_call) Excellent
getCertificateRecord() FREE       ~0 ETH (eth_call) Excellent
isAuthorizedIssuer()  FREE        ~0 ETH (eth_call) Excellent

Sepolia Test Network Gas Economics (approximate):
├── Gas Price: ~1-10 Gwei (varies)
├── storeCertificate at 5 Gwei: ~0.00043-0.00055 ETH
├── Sepolia ETH is free (testnet faucets)
└── Mainnet cost at 30 Gwei: ~0.003 ETH per certificate
    [At ETH=$3000: ~$9 per certificate — acceptable for MVP validation]
```

---

**[Design Decision A]** Struct packing for `status` (enum) and `exists` (bool) is the **most impactful single gas optimization** in the struct design, saving one full 32-byte storage slot (~20,000 gas) per certificate record. **[Why]** By placing these two small types at the end of the struct, Solidity's packing rules pack them together. This reduces the struct from 5 storage slots to 4, saving 20% of per-certificate storage cost. **[Requirement satisfied]** Gas optimization strategy. **[Alternative rejected]** Using a `uint8` for status or a separate `bytes32` for the packed value would achieve similar packing but obscure the intent. Solidity's native struct packing is cleaner, compiler-verified, and maintainable.

---

# SECTION 13: SECURITY ANALYSIS

## 13.1 Threat Model for the Smart Contract

```
SMART CONTRACT THREAT MODEL
════════════════════════════

THREAT 1: Unauthorized Certificate Issuance
────────────────────────────────────────────
Description: An unauthorized Ethereum address calls storeCertificate()
             to anchor a fraudulent document hash.

Attack vectors:
├── T1a: Random attacker wallet calls storeCertificate()
├── T1b: Student wallet calls storeCertificate() with their own cert
├── T1c: Employer wallet calls storeCertificate()
└── T1d: Compromised university admin backend server calls storeCertificate()

Mitigations:
├── onlyAuthorizedIssuer modifier: ALL calls from non-whitelisted addresses revert
│   T1a: BLOCKED — random wallet not in authorizedIssuers
│   T1b: BLOCKED — student wallet not in authorizedIssuers
│   T1c: BLOCKED — employer wallet not in authorizedIssuers
│   T1d: BLOCKED — server does not have private key (MetaMask is browser-based)
│         Even if server is compromised, it cannot sign MetaMask transactions
└── Result: MITIGATED


THREAT 2: Certificate Hash Overwrite
───────────────────────────────────────
Description: An authorized issuer calls storeCertificate() with a different
             hash for an existing certificate UID, retroactively "legitimizing"
             a tampered document.

Mitigation:
├── exists check in storeCertificate(): if certificate[certUid].exists == true → revert
└── Result: FULLY BLOCKED — one-time write per certificate UID


THREAT 3: Cross-University Certificate Revocation
────────────────────────────────────────────────────
Description: University A (authorized) calls revokeCertificate() on
             a certificate issued by University B.

Mitigation:
├── onlyOriginalIssuer modifier: msg.sender must == certificates[certUid].issuingUniversity
└── Result: FULLY BLOCKED — each issuer can only revoke their own certificates


THREAT 4: Reentrancy Attack
─────────────────────────────
Description: External contract calls back into CertificateRegistry
             during function execution, exploiting intermediate state.

Analysis:
├── CertificateRegistry makes NO external calls
├── No ETH transfers (no .call(), no .transfer(), no .send())
├── No ERC-20/ERC-721 token interactions
├── No callbacks to msg.sender
└── Reentrancy requires an external call that the attacker can intercept.
    Without external calls, reentrancy is structurally impossible.

Result: NOT APPLICABLE — no external calls exist


THREAT 5: Front-Running Certificate Storage
─────────────────────────────────────────────
Description: An attacker observes a pending storeCertificate() transaction
             in the mempool, copies the parameters, and submits their own
             transaction with higher gas to "steal" the certificate UID.

Analysis:
├── The attacker would need to be an authorized issuer (they are not)
├── Even if an authorized issuer attempted this, they would be:
│   (a) Storing ANOTHER university's certificate UID under their address
│   (b) The original university's transaction would then fail with
│       CertificateAlreadyExists — but the stored certificate would have
│       the ATTACKER's issuingUniversity address, not the victim's
│   (c) The off-chain verification: DB expects issuingUniversity ==
│       university.wallet_address would detect the mismatch
│   (d) The attacker gains nothing — they stored a hash they didn't hash
├── For the original issuer (authorized but racing against themselves):
│   Standard Ethereum first-in nonce ordering prevents self-front-running

Mitigation:
├── Authorization whitelist makes front-running only possible by another
│   authorized university (implicitly trusted)
└── Result: LOW RISK — only possible between authorized parties;
            immediately detectable via issuingUniversity address mismatch


THREAT 6: Contract Owner Key Compromise
──────────────────────────────────────────
Description: The contract owner's private key is stolen. Attacker
             gains owner privileges.

Impact:
├── Attacker can authorize their own wallet as an issuer
├── Attacker can deauthorize all legitimate universities
├── Attacker CANNOT revoke existing legitimate certificates
│   (revokeCertificate requires the original issuer's wallet)
├── Attacker CANNOT modify stored hashes
└── Attacker CAN issue new fraudulent certificates (via their newly authorized wallet)

Mitigations:
├── OwnershipTransferred event is immediately visible on-chain
├── IssuerAuthorized events from the attacker's wallet are visible on-chain
├── Platform can deploy a new contract and migrate all universities
├── Post-MVP: Owner should be a multisig wallet (Gnosis Safe)
└── Result: MEDIUM RISK — serious but detectable and recoverable


THREAT 7: Integer Overflow/Underflow
──────────────────────────────────────
Description: Arithmetic overflow in counter variables.

Mitigation:
├── Solidity ^0.8.0 has built-in overflow protection (checked arithmetic)
├── totalCertificates and totalRevocations are uint256 — practically unbounded
└── Result: NOT APPLICABLE — Solidity 0.8+ handles this automatically


THREAT 8: Gas Griefing via Large certUid
──────────────────────────────────────────
Description: An authorized issuer submits an extremely long certUid string,
             consuming excessive gas and potentially blocking verification.

Mitigation:
├── validCertUid modifier enforces bytes(certUid).length <= 50
└── Result: FULLY MITIGATED — 50-byte maximum cap


THREAT 9: Denial of Service via CertificateAlreadyExists
──────────────────────────────────────────────────────────
Description: An attacker pre-registers certificate UIDs that a university
             intends to use, making legitimate issuance impossible.

Analysis:
├── Only authorized issuers can call storeCertificate()
├── A rogue university could "squat" on another university's UID namespace
├── Example: OXFORD-2025-00001 stored by MIT-authorized wallet
└── Mitigation: The DB's certificate_uid has format SHORTCODE-YEAR-SEQ
    where SHORTCODE maps to a specific university. Cross-university UID
    format conflicts are prevented by the DB's certificate_uid generation
    logic. Even if stored, the DB cross-validation detects the issuer mismatch.

Result: LOW RISK — constrained by authorization and detectable


THREAT 10: Timestamp Manipulation
───────────────────────────────────
Description: A malicious miner/validator manipulates block.timestamp
             to alter the recorded issuance timestamp.

Analysis:
├── Ethereum consensus rules: block.timestamp must be within ~15 seconds
│   of the previous block's timestamp (post-Merge: slot time = 12 seconds)
├── A validator COULD set timestamp up to ~15 seconds in the future/past
├── This has no material impact on certificate authenticity:
│   The issuedAt timestamp is evidence of "when was this anchored"
│   not the academic issue date (which is in the database)
└── Result: ACCEPTABLE RISK — 15-second manipulation window is negligible
```

## 13.2 Solidity-Specific Security Checklist

```
SOLIDITY SECURITY CHECKLIST
═════════════════════════════

☑ Solidity version pinned: ^0.8.19
  Prevents compilation with older, potentially vulnerable versions.
  0.8.0+ includes: overflow protection, custom errors, improved ABI encoding.

☑ No floating pragma (no pragma solidity >=0.8.0)
  Floating pragma allows compilation with any version >=0.8.0.
  Pinning to ^0.8.19 means "0.8.19 to <0.9.0" — uses a tested version.

☑ No external calls
  Zero reentrancy attack surface. Confirmed by absence of:
  .call(), .delegatecall(), .staticcall(), address.transfer(),
  address.send(), IERC20 interactions, oracle calls.

☑ No tx.origin for authentication
  tx.origin is vulnerable to phishing attacks.
  All authentication uses msg.sender exclusively.

☑ No block.blockhash for randomness
  No randomness required. No use of blockhash.

☑ CEI Pattern (Checks-Effects-Interactions)
  All state changes happen BEFORE events (no external interactions).
  Order: modifier checks → state writes → event emissions.

☑ No selfdestruct
  No selfdestruct function. Contract is permanent once deployed.

☑ No delegatecall
  No delegatecall. Storage layout cannot be corrupted by external logic.

☑ Access control on all state-changing functions
  storeCertificate: onlyAuthorizedIssuer ✓
  revokeCertificate: onlyAuthorizedIssuer + onlyOriginalIssuer ✓
  authorizeIssuer: onlyOwner ✓
  deauthorizeIssuer: onlyOwner ✓
  transferOwnership: onlyOwner ✓

☑ Zero-address guards
  Owner cannot be zero address (checked in constructor + transferOwnership)
  Issuer cannot be zero address (checked in authorizeIssuer)
  Owner cannot be authorized as issuer (checked in authorizeIssuer)

☑ Custom errors (not require strings)
  All reverts use custom errors for gas efficiency and type safety.

☑ NatSpec documentation on all public/external functions
  @notice, @param, @return on every function.
  @dev notes on security-critical behavior.
```

---

**[Design Decision A]** The contract makes **zero external calls** — no oracle queries, no token interactions, no callback patterns. This is the single most impactful security decision. **[Why]** External calls are the primary reentrancy attack vector. By eliminating all external calls, the reentrancy attack class is structurally eliminated — not just guarded against with a reentrancy guard. A reentrancy guard on a contract with no external calls is theater; no external calls is defense by design. **[Requirement satisfied]** Security architecture — "Tampered certificates are detected instantly" requires a trustworthy contract that cannot be exploited. **[Alternative rejected]** Adding a reentrancy guard (OpenZeppelin `ReentrancyGuard`) would be misleading — it implies there is an attack surface to guard against when there isn't. Unnecessary imports increase contract size and introduce dependency risk.

---

# SECTION 14: SMART CONTRACT FOLDER STRUCTURE

```
COMPLETE SMART CONTRACT FOLDER STRUCTURE
══════════════════════════════════════════

blockchain/
│
├── package.json
│   Dependencies:
│   ├── hardhat: ^2.22.x               → Development framework
│   ├── @nomicfoundation/hardhat-toolbox: ^4.x → Ethers, chai, coverage
│   ├── @nomicfoundation/hardhat-verify: ^2.x  → Etherscan verification
│   └── dotenv: ^16.x                  → Environment variable loading
│
├── hardhat.config.js
│   Configuration:
│   ├── solidity: { version: "0.8.19", settings: { optimizer: { ... } } }
│   ├── networks: { hardhat: {...}, sepolia: {...} }
│   ├── etherscan: { apiKey: process.env.ETHERSCAN_API_KEY }
│   └── gasReporter: { enabled: true, currency: "USD" }
│
├── .env
│   ├── DEPLOYER_PRIVATE_KEY=       ← Deployment wallet private key
│   ├── SEPOLIA_RPC_URL=            ← Infura/Alchemy Sepolia endpoint
│   ├── ETHERSCAN_API_KEY=          ← For contract verification
│   └── INITIAL_OWNER_ADDRESS=      ← Optional; override deployer as owner
│
├── .env.example
│   └── Template with all required variables, no actual values
│
├── .gitignore
│   └── .env, node_modules/, artifacts/, cache/, coverage/
│
│
├── contracts/                       ← All Solidity source files
│   │
│   ├── CertificateRegistry.sol      ← PRIMARY CONTRACT
│   │   Size: ~200 lines Solidity
│   │   Contains:
│   │   ├── License + pragma declaration
│   │   ├── NatSpec contract-level documentation
│   │   ├── Enum: CertificateStatus
│   │   ├── Struct: CertificateRecord
│   │   ├── Events (5 events)
│   │   ├── Custom Errors (14 errors)
│   │   ├── State Variables (5 variables)
│   │   ├── Modifiers (7 modifiers)
│   │   ├── Constructor
│   │   ├── Admin Functions (3 functions)
│   │   ├── Issuer Write Functions (2 functions)
│   │   └── Public View Functions (5 functions)
│   │
│   └── interfaces/
│       └── ICertificateRegistry.sol  ← Interface definition
│           Contains:
│           ├── All external function signatures
│           ├── All event declarations
│           ├── Enum and struct declarations
│           └── NatSpec documentation
│           Why:
│           Enables backend (Web3.py) to import just the ABI interface
│           without the full implementation.
│           Future: enables other contracts to interact with the registry.
│
│
├── scripts/                         ← Deployment and admin scripts
│   │
│   ├── deploy.js                    ← Primary deployment script
│   │   Actions:
│   │   ├── Compile contract
│   │   ├── Deploy CertificateRegistry
│   │   ├── Wait for deployment confirmation
│   │   ├── Log contract address, tx hash, block number
│   │   ├── Save deployment info to deployments/ directory
│   │   └── Verify contract on Etherscan (if non-local network)
│   │
│   ├── authorize-issuer.js          ← Post-deploy university setup
│   │   Input: --network, --issuer (wallet address), --university (name)
│   │   Actions:
│   │   ├── Load deployed contract address from deployments/
│   │   ├── Connect to contract as owner
│   │   ├── Call authorizeIssuer(issuerAddress)
│   │   ├── Wait for confirmation
│   │   └── Log: "Authorized [universityName] wallet [address]"
│   │
│   ├── deauthorize-issuer.js        ← University offboarding
│   │   Input: --network, --issuer, --reason
│   │   Actions:
│   │   ├── Load deployed contract address from deployments/
│   │   ├── Connect to contract as owner
│   │   ├── Call deauthorizeIssuer(issuerAddress, reason)
│   │   ├── Wait for confirmation
│   │   └── Log: "Deauthorized [address] for reason: [reason]"
│   │
│   ├── check-certificate.js         ← Manual certificate verification tool
│   │   Input: --network, --uid, --hash
│   │   Actions:
│   │   ├── Load contract
│   │   ├── Call verifyCertificate(uid, hash)
│   │   ├── Call getCertificateRecord(uid)
│   │   └── Print full verification result
│   │
│   └── transfer-ownership.js        ← Emergency ownership transfer
│       Input: --network, --new-owner
│       Actions:
│       ├── Confirm with user (double-check prompt)
│       ├── Call transferOwnership(newOwner)
│       └── Log new owner address
│
│
├── test/                            ← Complete test suite
│   │
│   ├── unit/
│   │   ├── CertificateRegistry.access.test.js
│   │   │   Tests: onlyOwner, onlyAuthorizedIssuer, onlyOriginalIssuer
│   │   │
│   │   ├── CertificateRegistry.storage.test.js
│   │   │   Tests: storeCertificate() success + all revert conditions
│   │   │
│   │   ├── CertificateRegistry.verification.test.js
│   │   │   Tests: verifyCertificate() all return value combinations
│   │   │
│   │   ├── CertificateRegistry.revocation.test.js
│   │   │   Tests: revokeCertificate() success + all revert conditions
│   │   │
│   │   └── CertificateRegistry.admin.test.js
│   │       Tests: authorizeIssuer, deauthorizeIssuer, transferOwnership
│   │
│   ├── integration/
│   │   ├── IssuanceFlow.test.js
│   │   │   Tests: Full issuance lifecycle from deploy to confirmation
│   │   │
│   │   ├── VerificationFlow.test.js
│   │   │   Tests: Authentic, tampered, revoked, not-found scenarios
│   │   │
│   │   └── RevocationFlow.test.js
│   │       Tests: Issue → Verify authentic → Revoke → Verify revoked
│   │
│   └── security/
│       ├── AccessControl.security.test.js
│       │   Tests: All unauthorized access attempts
│       │
│       ├── InputValidation.security.test.js
│       │   Tests: Zero hash, empty UID, oversized UID, zero address
│       │
│       └── EdgeCases.security.test.js
│           Tests: Double store, double revoke, cross-university revoke
│
│
├── deployments/                     ← Deployment records (committed to Git)
│   ├── hardhat-local/
│   │   └── CertificateRegistry.json
│   │       Contains: address, txHash, blockNumber, deployedAt, abi
│   │
│   └── sepolia/
│       └── CertificateRegistry.json
│           Contains: address, txHash, blockNumber, deployedAt,
│                     etherscanUrl, abi
│
│
├── artifacts/                       ← Hardhat-generated (gitignored)
│   └── contracts/
│       └── CertificateRegistry.sol/
│           └── CertificateRegistry.json  ← ABI + bytecode
│
│
├── cache/                           ← Hardhat compilation cache (gitignored)
│
│
└── coverage/                        ← Test coverage reports (gitignored)
    ├── index.html                   → HTML coverage report
    └── coverage-summary.json        → JSON coverage data
```

## 14.1 ABI Export for Backend and Frontend

```
ABI DISTRIBUTION STRATEGY
══════════════════════════

Source of truth: blockchain/artifacts/contracts/CertificateRegistry.sol/CertificateRegistry.json

After deployment, the ABI must be copied to:
├── backend/blockchain/abi/CertificateRegistry.json
│   Used by: blockchain_service.py (Web3.py contract initialization)
│   Consumed as: web3.eth.contract(address=ADDR, abi=ABI)
│
└── frontend/blockchain/contractABI.js
    Used by: transactions.js (ethers.js contract interaction)
    Format: export const CONTRACT_ABI = [...]

Automation: deploy.js script automatically copies the ABI
to both locations after successful deployment.
This ensures frontend and backend always use the ABI
that matches the deployed contract.

Version tracking: ABI is committed to Git along with the
deployment record. The contract address in frontend/blockchain/
contractAddress.js is updated by the deploy script.
```

---

**[Design Decision A]** A separate `interfaces/ICertificateRegistry.sol` is defined alongside the implementation. **[Why]** The interface serves three purposes: (1) it documents the contract's public API clearly separate from implementation; (2) it enables the backend (Web3.py) to import a minimal ABI derived from the interface rather than the full artifact; (3) it enables future contracts to interact with the registry through a standard interface without depending on implementation details. **[Requirement satisfied]** Maintainability; future expansion (post-MVP contracts can compose with the registry). **[Alternative rejected]** No interface, only the implementation — this couples all consumers to the implementation artifact and makes the API contract implicit rather than explicit.

---

# SECTION 15: SMART CONTRACT TESTING STRATEGY

## 15.1 Testing Philosophy

```
TESTING PHILOSOPHY
═══════════════════

Target: >95% line coverage (per architecture blueprint requirement)
Framework: Hardhat + Ethers.js + Chai + Hardhat Gas Reporter
Coverage tool: solidity-coverage (Istanbul)

Testing Pyramid:
├── Unit Tests (60% of tests): Test each function in isolation
├── Integration Tests (30% of tests): Test workflows end-to-end
└── Security Tests (10% of tests): Test every attack vector

Test Environment:
├── All tests run on Hardhat local network (in-process EVM)
├── Deterministic: snapshots and reverts between tests
├── No real ETH: Hardhat provides test wallets with 10,000 ETH
└── Fast: in-process EVM, no network round-trips
```

## 15.2 Complete Test Case Specification

```
UNIT TESTS: Access Control
═══════════════════════════

Test Suite: CertificateRegistry.access.test.js

TC-AC-01: Owner is correctly set to deployer address after deployment
TC-AC-02: authorizeIssuer() succeeds when called by owner
TC-AC-03: authorizeIssuer() reverts with NotContractOwner for non-owner
TC-AC-04: authorizeIssuer() reverts with InvalidAddress for zero address
TC-AC-05: authorizeIssuer() reverts with CannotAuthorizeOwner if owner tries to authorize themselves
TC-AC-06: authorizeIssuer() reverts with IssuerAlreadyAuthorized for duplicate authorization
TC-AC-07: authorizeIssuer() emits IssuerAuthorized event with correct parameters
TC-AC-08: isAuthorizedIssuer() returns true for authorized address
TC-AC-09: isAuthorizedIssuer() returns false for unauthorized address
TC-AC-10: deauthorizeIssuer() succeeds when called by owner
TC-AC-11: deauthorizeIssuer() reverts with NotContractOwner for non-owner
TC-AC-12: deauthorizeIssuer() reverts with IssuerNotAuthorized for non-authorized address
TC-AC-13: deauthorizeIssuer() emits IssuerDeauthorized event with correct parameters
TC-AC-14: isAuthorizedIssuer() returns false after deauthorization
TC-AC-15: transferOwnership() succeeds when called by owner with valid address
TC-AC-16: transferOwnership() reverts with CannotTransferToZeroAddress for zero address
TC-AC-17: transferOwnership() reverts with NotContractOwner for non-owner
TC-AC-18: transferOwnership() emits OwnershipTransferred event
TC-AC-19: New owner can call authorizeIssuer() after ownership transfer
TC-AC-20: Old owner cannot call authorizeIssuer() after ownership transfer


UNIT TESTS: Certificate Storage
═════════════════════════════════

Test Suite: CertificateRegistry.storage.test.js

TC-ST-01: storeCertificate() succeeds with valid uid and hash from authorized issuer
TC-ST-02: storeCertificate() correctly stores certificateHash
TC-ST-03: storeCertificate() correctly stores issuingUniversity as msg.sender
TC-ST-04: storeCertificate() correctly records block.timestamp as issuedAt
TC-ST-05: storeCertificate() sets status to ACTIVE
TC-ST-06: storeCertificate() sets exists to true
TC-ST-07: storeCertificate() sets revokedAt to 0
TC-ST-08: storeCertificate() increments totalCertificates by 1
TC-ST-09: storeCertificate() emits CertificateStored with correct indexed parameters
TC-ST-10: storeCertificate() emits correct non-indexed parameters (issuedAt, totalCount)
TC-ST-11: storeCertificate() reverts with NotAuthorizedIssuer for unauthorized caller
TC-ST-12: storeCertificate() reverts with InvalidCertificateHash for bytes32(0)
TC-ST-13: storeCertificate() reverts with InvalidCertificateUid for empty string
TC-ST-14: storeCertificate() reverts with InvalidCertificateUid for 51-char string
TC-ST-15: storeCertificate() reverts with CertificateAlreadyExists on duplicate uid
TC-ST-16: storeCertificate() accepts exact 50-character uid (boundary test)
TC-ST-17: Two different authorized issuers can each store their own certificates
TC-ST-18: Same issuer can store multiple certificates with different uids
TC-ST-19: getCertificateCount() returns correct count after multiple stores
TC-ST-20: getCertificateRecord() returns zero-value struct for non-existent uid


UNIT TESTS: Certificate Verification
═════════════════════════════════════

Test Suite: CertificateRegistry.verification.test.js

TC-VR-01: verifyCertificate() returns (true, ACTIVE) for exact hash match on active cert
TC-VR-02: verifyCertificate() returns (false, ACTIVE) for hash mismatch on active cert
TC-VR-03: verifyCertificate() returns (false, REVOKED) for matching hash on revoked cert
TC-VR-04: verifyCertificate() returns (false, REVOKED) for non-matching hash on revoked cert
TC-VR-05: verifyCertificate() returns (false, ACTIVE) for non-existent cert uid
TC-VR-06: verifyCertificate() can be called by any address (unauthorized caller)
TC-VR-07: verifyCertificate() can be called by zero address (view call)
TC-VR-08: verifyCertificate() returns correct result for minimum-length uid
TC-VR-09: verifyCertificate() with submitted bytes32(0) returns (false, ACTIVE)
TC-VR-10: Multiple verifications of same certificate do not alter state
TC-VR-11: getCertificateRecord() returns correct full struct for existing cert
TC-VR-12: getCertificateRecord() returns exists=false for non-existent cert
TC-VR-13: getCertificateRecord() shows REVOKED status after revocation
TC-VR-14: getCertificateRecord() shows revokedAt timestamp after revocation
TC-VR-15: getCertificateRecord().issuingUniversity matches original issuer


UNIT TESTS: Certificate Revocation
════════════════════════════════════

Test Suite: CertificateRegistry.revocation.test.js

TC-RV-01: revokeCertificate() succeeds for original issuer on active certificate
TC-RV-02: revokeCertificate() changes status from ACTIVE to REVOKED
TC-RV-03: revokeCertificate() sets revokedAt to block.timestamp
TC-RV-04: revokeCertificate() does NOT change certificateHash
TC-RV-05: revokeCertificate() does NOT change issuingUniversity
TC-RV-06: revokeCertificate() increments totalRevocations by 1
TC-RV-07: revokeCertificate() emits CertificateRevoked with correct indexed params
TC-RV-08: revokeCertificate() reverts with NotAuthorizedIssuer for non-issuer
TC-RV-09: revokeCertificate() reverts with CertificateNotFound for non-existent uid
TC-RV-10: revokeCertificate() reverts with CertificateAlreadyRevoked on second call
TC-RV-11: revokeCertificate() reverts with NotOriginalIssuer for different authorized issuer
TC-RV-12: revokeCertificate() reverts with NotOriginalIssuer for contract owner
TC-RV-13: Deauthorized issuer cannot revoke their own previously-issued certificate
TC-RV-14: After revocation, verifyCertificate() returns (false, REVOKED) for any hash
TC-RV-15: CertificateAlreadyRevoked error includes original revokedAt timestamp


INTEGRATION TESTS
══════════════════

Test Suite: IssuanceFlow.test.js
IT-IF-01: Full lifecycle: deploy → authorize → issue → verify authentic
IT-IF-02: Multiple universities issue different certificates; each verifies correctly
IT-IF-03: Deploy → authorize issuer A → A issues cert → deauthorize A →
          A cannot issue new cert → A's old cert still verifies authentic
IT-IF-04: getCertificateCount() reflects all stored certificates across universities

Test Suite: VerificationFlow.test.js
IT-VF-01: AUTHENTIC path: exact hash match, active certificate
IT-VF-02: TAMPERED path: single bit difference in submitted hash vs stored
IT-VF-03: REVOKED path: verify after revocation (matching hash → still revoked)
IT-VF-04: NOT_FOUND path: certificate uid never stored
IT-VF-05: Verify before and after revocation; confirm state change

Test Suite: RevocationFlow.test.js
IT-RF-01: Issue cert → verify authentic → revoke → verify revoked (complete lifecycle)
IT-RF-02: Two universities: A revokes own cert; B's cert unaffected
IT-RF-03: Revocation by original issuer after another issuer is added to platform


SECURITY TESTS
═══════════════

Test Suite: AccessControl.security.test.js
SC-AC-01: Random wallet cannot call storeCertificate()
SC-AC-02: Random wallet cannot call revokeCertificate()
SC-AC-03: Random wallet cannot call authorizeIssuer()
SC-AC-04: Random wallet cannot call deauthorizeIssuer()
SC-AC-05: Authorized issuer cannot call authorizeIssuer()
SC-AC-06: Owner cannot call storeCertificate()
SC-AC-07: Owner cannot call revokeCertificate()

Test Suite: InputValidation.security.test.js
SC-IV-01: Zero bytes32 hash rejected by storeCertificate()
SC-IV-02: Empty string uid rejected by storeCertificate()
SC-IV-03: 51-character uid rejected by storeCertificate()
SC-IV-04: 50-character uid accepted (boundary condition)
SC-IV-05: Zero address rejected by authorizeIssuer()
SC-IV-06: Zero address rejected by transferOwnership()
SC-IV-07: Owner address rejected by authorizeIssuer()

Test Suite: EdgeCases.security.test.js
SC-EC-01: Cannot store certificate with same UID as existing (exact duplicate)
SC-EC-02: Cannot revoke already-revoked certificate
SC-EC-03: Cannot cross-revoke between universities
SC-EC-04: Deauthorized issuer cannot issue new certificates
SC-EC-05: Previously issued certs by deauthorized issuer remain AUTHENTIC
SC-EC-06: Cannot transfer ownership to current owner (no-op guard)
```

## 15.3 Gas Reporting Configuration

```
GAS REPORTING STRATEGY
════════════════════════

Tool: hardhat-gas-reporter
Output: Console table during test run

Metrics reported per function:
├── Min gas used
├── Max gas used
├── Average gas used
├── Number of calls in tests
└── USD cost at current ETH price

Acceptance criteria:
├── storeCertificate(): avg <= 110,000 gas
├── revokeCertificate(): avg <= 65,000 gas
├── authorizeIssuer(): avg <= 55,000 gas
└── All view functions: 0 ETH (verified as view)

If any function exceeds its budget: test run fails (configured as CI gate)
```

## 15.4 Coverage Requirements

```
COVERAGE REQUIREMENTS
═════════════════════

Minimum acceptance thresholds:
├── Line coverage:      ≥ 95%
├── Branch coverage:    ≥ 95%
├── Function coverage:  100%
└── Statement coverage: ≥ 95%

Coverage exclusions (documented, not just excluded):
├── Constructor: covered by deployment tests
├── Events: verified by event argument assertions
└── View functions: covered by integration tests

Critical paths requiring 100% branch coverage:
├── verifyCertificate() decision tree (5 paths)
├── revokeCertificate() modifier chain (4 failure paths + 1 success)
└── storeCertificate() validation chain (5 failure paths + 1 success)
```

---

**[Design Decision A]** The test suite is divided into **three categories: unit, integration, and security** rather than just unit and integration. **[Why]** Security tests are adversarial by nature — they test what an attacker would do, not what a legitimate user does. They deserve their own test files where the intent is "try everything that should fail." This separation makes it immediately clear which tests are proving correct behavior vs. which tests are proving incorrect behavior is properly rejected. **[Requirement satisfied]** Security architecture requirement; >95% coverage target. **[Alternative rejected]** A single flat test file is common for small contracts but mixes concerns and makes it hard to audit whether all security scenarios are covered.

---

# SECTION 16: DEPLOYMENT STRATEGY

## 16.1 Network Configuration Blueprint

```
NETWORK CONFIGURATIONS
════════════════════════

NETWORK 1: Hardhat Local (Development)
───────────────────────────────────────
Network Name:    hardhat
Chain ID:        31337
RPC URL:         http://127.0.0.1:8545
ETH Balance:     20 test wallets × 10,000 ETH (Hardhat default)
Block Time:      Instant (mine on demand) or --interval 12
Persistence:     In-memory by default (state resets across restarts)
Gas Price:       0 (no cost for development)
Purpose:         Local development; automated test runs

hardhat.config.js network entry:
├── chainId: 31337
├── accounts: Hardhat default (mnemonic-based)
└── mining: { auto: true } (or interval-based to simulate real block times)


NETWORK 2: Sepolia Testnet (Staging)
──────────────────────────────────────
Network Name:    sepolia
Chain ID:        11155111
RPC URL:         $SEPOLIA_RPC_URL (Infura or Alchemy endpoint)
ETH Source:      Sepolia faucet (sepoliafaucet.com, Alchemy Faucet)
Block Time:      ~12 seconds (post-Merge Ethereum)
Gas Price:       Variable (~1-10 Gwei)
Persistence:     Permanent (Ethereum testnet blockchain)
Purpose:         Integration testing; UAT; pre-production validation

hardhat.config.js network entry:
├── chainId: 11155111
├── url: process.env.SEPOLIA_RPC_URL
├── accounts: [process.env.DEPLOYER_PRIVATE_KEY]
└── gasMultiplier: 1.2 (20% buffer on estimated gas)
```

## 16.2 Deployment Workflow

```
DEPLOYMENT WORKFLOW — STEP BY STEP
════════════════════════════════════

PHASE 1: PRE-DEPLOYMENT CHECKLIST
───────────────────────────────────
Before running deploy.js, verify:
☐ Solidity version: ^0.8.19 confirmed in hardhat.config.js
☐ Optimizer enabled: runs: 200 (balanced optimization)
☐ All tests pass: npx hardhat test (0 failures)
☐ Coverage meets threshold: npx hardhat coverage (≥95%)
☐ Gas report reviewed: no function exceeds budget
☐ .env populated: DEPLOYER_PRIVATE_KEY, SEPOLIA_RPC_URL, ETHERSCAN_API_KEY
☐ Deployer wallet funded: at least 0.1 Sepolia ETH
☐ Contract source reviewed: no hardcoded addresses, no test artifacts

PHASE 2: LOCAL DEPLOYMENT (Hardhat)
─────────────────────────────────────
Commands:
├── npx hardhat node                        ← Start local Hardhat node
├── npx hardhat run scripts/deploy.js --network hardhat
└── (deploy.js copies ABI to backend + frontend)

Verification:
├── Contract address logged to console
├── CertificateRegistry.json created in deployments/hardhat-local/
├── ABI copied to backend/blockchain/abi/
├── Contract address copied to frontend/blockchain/contractAddress.js
└── Run: npx hardhat run scripts/check-certificate.js --network hardhat
         (verify empty state of new deployment)

PHASE 3: AUTHORIZE INITIAL ISSUERS (Local)
─────────────────────────────────────────────
For each university in the test environment:
npx hardhat run scripts/authorize-issuer.js --network hardhat
  --issuer 0xUniversityWalletAddress
  --university "MIT"

Verification:
└── isAuthorizedIssuer(walletAddress) returns true

PHASE 4: SEPOLIA DEPLOYMENT
─────────────────────────────
Commands:
└── npx hardhat run scripts/deploy.js --network sepolia

Deployment records:
├── Transaction hash logged
├── Contract address logged
├── deployments/sepolia/CertificateRegistry.json created
└── ABI distributed to backend and frontend

Await confirmations:
└── deploy.js waits for 6 block confirmations before proceeding
    (6 blocks ≈ 72 seconds at 12s/block — standard confirmation threshold)

PHASE 5: ETHERSCAN VERIFICATION (Sepolia)
───────────────────────────────────────────
Command:
└── npx hardhat verify --network sepolia CONTRACT_ADDRESS

Effect:
├── Contract source code published to Etherscan
├── ABI publicly readable on Etherscan
├── Anyone can verify the deployed bytecode matches the source
└── Builds trust: "the platform is running exactly this published code"

PHASE 6: POST-DEPLOYMENT VALIDATION
──────────────────────────────────────
After Sepolia deployment:

6a. Verify contract is accessible:
    npx hardhat run scripts/check-certificate.js --network sepolia
    Expected: getCertificateCount() = 0, getOwner() = deployer address

6b. Authorize first test university:
    npx hardhat run scripts/authorize-issuer.js --network sepolia
    Expected: IssuerAuthorized event visible on Etherscan

6c. Issue a test certificate:
    (Via frontend connected to MetaMask with the authorized wallet)
    Expected: CertificateStored event on Etherscan

6d. Verify the test certificate:
    (Via employer portal file upload)
    Expected: AUTHENTIC result

6e. Revoke the test certificate:
    (Via university portal)
    Expected: CertificateRevoked event on Etherscan

6f. Re-verify the revoked certificate:
    Expected: REVOKED result
```

## 16.3 Compiler Configuration

```
SOLIDITY COMPILER CONFIGURATION
═════════════════════════════════

solidity: {
  version: "0.8.19",
  settings: {
    optimizer: {
      enabled: true,
      runs: 200
    },
    outputSelection: {
      "*": {
        "*": ["abi", "evm.bytecode", "evm.deployedBytecode"]
      }
    },
    viaIR: false    // Disabled: viaIR changes storage layout; risky without testing
  }
}

Optimizer runs: 200
  Meaning: Optimize for code that is called ~200 times.
  This balances deployment cost (larger runs = smaller bytecode for functions)
  vs. execution cost (larger runs = more inlining = cheaper per-call).
  200 is the Ethereum standard default for production contracts.

Why not viaIR:
  viaIR (via intermediate representation) can change storage slot assignments.
  For a contract where storage layout is explicitly planned (Section 3.2),
  enabling viaIR without extensive re-validation of slot positions is risky.
  Disabled for MVP.
```

---

**[Design Decision A]** Deployment includes Etherscan source verification as a **mandatory step, not optional**. **[Why]** Etherscan verification publishes the exact Solidity source code alongside the deployed bytecode. Any university, employer, or independent security researcher can verify that the contract behavior matches what is published. This "open source trust" is fundamental to a credential verification platform — if the contract logic is opaque, why should anyone trust it? **[Requirement satisfied]** Decentralized trust; transparency of the verification system. **[Alternative rejected]** Deploying only bytecode (no source verification) is faster but creates a trust gap: "we claim this contract does X, but you cannot verify that."

---

# SECTION 17: FUTURE UPGRADE PATH

## 17.1 The No-Proxy MVP Decision and Its Consequences

```
MVP ARCHITECTURE: NON-UPGRADEABLE CONTRACT
═══════════════════════════════════════════

Decision (from Assumption 09): No proxy pattern in MVP.
The contract is deployed once. Logic changes require new deployment.

Consequences of this decision:
├── POSITIVE: Maximum security (no upgrade key as attack vector)
├── POSITIVE: Simple storage layout (no EIP-1967 proxy storage slots)
├── POSITIVE: Auditable: "this deployed bytecode will always behave this way"
├── NEGATIVE: Bug fixes require new contract + data migration logic
└── NEGATIVE: Feature additions require new contract deployment

Migration strategy if contract must change:
├── Deploy new CertificateRegistry V2 at a new address
├── Platform admin authorizes all universities on new contract
├── Backend updates CONTRACT_ADDRESS environment variable
├── Frontend updates contractAddress.js
├── Old contract remains accessible (read-only effectively, since
│   the platform no longer issues to it)
├── Old verification links still work (backend knows both addresses)
└── Historical certificates on old contract are still verifiable
    by querying the old contract directly
```

## 17.2 Post-MVP Upgrade Options

```
POST-MVP UPGRADE PATH OPTIONS
═══════════════════════════════

OPTION A: Transparent Proxy (OpenZeppelin)
───────────────────────────────────────────
Pattern: ProxyAdmin → TransparentUpgradeableProxy → CertificateRegistryV2
Pros: Industry standard; widely audited; upgrade without address change
Cons: Storage layout must be carefully preserved between versions
      ProxyAdmin key is a centralization vector
      Requires EIP-1967 storage slots; no slot conflicts with current layout
      Adds ~500 gas per call (proxy delegation overhead)
Suitable when: Post-MVP adds significant features (e.g., multi-sig, metadata)

OPTION B: UUPS Proxy (EIP-1822)
─────────────────────────────────
Pattern: CertificateRegistryV2 (UUPS-enabled) → deployed as implementation
Pros: Upgrade logic in implementation (not proxy); cheaper than Transparent
Cons: Implementation must correctly implement UUPS interface
     Upgrade key still a centralization vector
Suitable when: Team has Solidity expertise to implement UUPS correctly

OPTION C: New Contract + Version Registry
───────────────────────────────────────────
Pattern: VersionRegistry → maps version string → contract address
         Backend queries VersionRegistry for current active contract
Pros: Each version is an independent, fully auditable contract
      No storage layout constraints between versions
      Historical versions remain accessible forever
      Simple mental model: "version X is at address Y"
Cons: Universities must be re-authorized on each new version
      Verification links must know which contract version to query
RECOMMENDATION: This is the preferred MVP → post-MVP upgrade path.
It is the simplest, most auditable, and most aligned with the
"decentralized trust" philosophy.

OPTION D: Diamond Proxy (EIP-2535)
───────────────────────────────────
Pattern: Diamond → multiple Facets (storage + logic separated)
Pros: Extremely modular; can upgrade individual functions
Cons: Enormous complexity; specialized knowledge required
     Not appropriate for this use case
Suitable when: Very large contracts near size limits with many modules
REJECTED for all timeframes.
```

## 17.3 Feature Addition Roadmap

```
FEATURE ADDITIONS (In Rough Priority Order)
════════════════════════════════════════════

POST-MVP TIER 1 (3-6 months):

1. ownerEmergencyRevoke(string certUid, string reason)
   Why: Addresses the compromised university wallet gap (Section 11.2)
   Implementation: onlyOwner modifier; emits EmergencyRevocation event
   Storage change: None (existing status/revokedAt fields used)
   Risk: LOW (additive; no existing behavior changed)

2. getCertificatesByIssuer() (via event indexing, not state)
   Why: University portal dashboard efficiency
   Implementation: Off-chain via Web3.py event filtering
                   No contract change needed
   Risk: NONE (off-chain change)

3. Batch Certificate Storage
   Why: Issue 100 certificates at once for graduation ceremonies
   Implementation: storeBatch(string[] certUids, bytes32[] certHashes)
   Storage change: None (same CertificateRecord structure)
   Gas saving: ~21,000 base TX gas saved per batch element after first
   Risk: LOW to MEDIUM (array bounds, gas limit per transaction)

POST-MVP TIER 2 (6-12 months):

4. Multi-Signature Issuance (Threshold Signatures)
   Why: "Require both Registrar AND Dean to sign"
   Implementation: Off-chain multi-sig via EIP-712 typed signatures;
                   contract verifies recovered addresses
   Contract change: storeCertificate() adds signatures[] parameter
   Risk: MEDIUM (signature verification logic)

5. IPFS CID Storage
   Why: Anchor document location (IPFS CID) in addition to hash
   Implementation: Add bytes32 ipfsCid to CertificateRecord
   Storage change: MEDIUM (struct expansion = storage slot impact)
   Risk: MEDIUM (existing structs must be carefully migrated)

6. Certificate Metadata Hash
   Why: Hash of the full certificate metadata JSON (not just the PDF)
   Implementation: Add bytes32 metadataHash to CertificateRecord
   Gas impact: +~20,000 gas per issuance
   Risk: LOW if added to new struct version

POST-MVP TIER 3 (12+ months):

7. Merkle Root Batch Issuance
   Implementation: Store Merkle root; verify individual certs with proof
   Contract change: MAJOR (different storage model)
   Risk: HIGH (requires new verification algorithm)

8. Multi-Chain Deployment
   Implementation: Same contract deployed on Polygon, Avalanche, etc.
   Contract change: None (deploy same bytecode)
   Risk: LOW for contract; MEDIUM for backend (multi-chain routing)
```

---

**[Design Decision A]** The recommended post-MVP upgrade path is **Option C: New Contract + Version Registry**, not a proxy pattern. **[Why]** For a credential verification platform, the auditability of "this exact deployed bytecode has behaved this way since block X" is more valuable than seamless upgradeability. A version registry is simple to implement (a single mapping from version string to address), completely transparent, and allows the old contract to remain accessible indefinitely. Credential records on older contracts are still verifiable — the backend simply knows which contract to query based on when the certificate was issued. **[Requirement satisfied]** Future expansion possibilities (Section 19 of architecture). **[Alternative rejected]** Proxy patterns add complexity and a persistent upgrade key attack surface. For a trust infrastructure, "cannot be upgraded silently" is a feature, not a bug.

---

# SECTION 18: SMART CONTRACT VALIDATION CHECKLIST

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                  SMART CONTRACT VALIDATION CHECKLIST                           ║
║         Verifying all requirements and assumptions are satisfied               ║
╚════════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════
PRE-DESIGN REVIEW REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ Architecture document reviewed
  → All smart-contract-relevant requirements extracted (Section 0.1) ✓

☑ Database design reviewed
  → All contract-database interface points identified (Section 0.2) ✓

☑ Assumptions explicitly listed and carried forward
  → 12 assumptions documented (Section 0.3) ✓

☑ No new technologies introduced
  → Solidity + Hardhat + MetaMask only (as approved) ✓
  → No OpenZeppelin, no Chainlink, no IPFS ✓

═══════════════════════════════════════════════════════════════════════
CONTRACT CORE REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ Authorized University Issuers
  → authorizedIssuers mapping with address→bool ✓
  → authorizeIssuer() — owner-only function ✓
  → deauthorizeIssuer() — owner-only function ✓
  → isAuthorizedIssuer() — public view function ✓
  → onlyAuthorizedIssuer modifier on all write functions ✓

☑ SHA-256 Hash Storage
  → bytes32 certificateHash in CertificateRecord struct ✓
  → storeCertificate(string certUid, bytes32 certHash) ✓
  → validCertHash modifier: rejects bytes32(0) ✓
  → One-time write: CertificateAlreadyExists check ✓
  → Hash is immutable after storage ✓

☑ Certificate Verification
  → verifyCertificate(string certUid, bytes32 submittedHash) ✓
  → Returns (bool isValid, CertificateStatus status) ✓
  → external view function: zero ETH cost for verifiers ✓
  → Decision tree: AUTHENTIC / TAMPERED / REVOKED / NOT_FOUND ✓
  → Blockchain is always the source of truth ✓
  → Any address can call (no auth required) ✓

☑ Certificate Revocation
  → revokeCertificate(string certUid) ✓
  → onlyAuthorizedIssuer: caller must be authorized issuer ✓
  → onlyOriginalIssuer: caller must be the cert's original issuer ✓
  → certificateMustBeActive: cannot double-revoke ✓
  → ACTIVE → REVOKED is a terminal, one-way transition ✓
  → revokedAt timestamp permanently recorded ✓

☑ Event Logging
  → CertificateStored (3 indexed: certUid, hash, issuer) ✓
  → CertificateRevoked (2 indexed: certUid, revoker) ✓
  → IssuerAuthorized (2 indexed: issuer, authorizedBy) ✓
  → IssuerDeauthorized (2 indexed: issuer, deauthorizedBy) ✓
  → OwnershipTransferred (2 indexed: prev, new) ✓

═══════════════════════════════════════════════════════════════════════
STATE VARIABLES REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ owner — contract deployer, admin of issuer whitelist ✓
☑ authorizedIssuers — mapping(address → bool) ✓
☑ certificates — mapping(string → CertificateRecord) ✓
☑ totalCertificates — monotonic counter ✓
☑ totalRevocations — monotonic counter ✓
☑ CONTRACT_VERSION — constant string ✓

═══════════════════════════════════════════════════════════════════════
STRUCT AND ENUM REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ CertificateRecord struct complete:
  → certificateHash (bytes32) ✓
  → issuingUniversity (address) ✓
  → issuedAt (uint256, block.timestamp) ✓
  → revokedAt (uint256, 0 if not revoked) ✓
  → status (CertificateStatus enum) ✓
  → exists (bool, guard against zero-value reads) ✓

☑ CertificateStatus enum: ACTIVE(0), REVOKED(1) ✓
☑ Struct packing: status + exists share storage slot ✓
☑ No PII stored in struct (privacy requirement) ✓

═══════════════════════════════════════════════════════════════════════
MODIFIER REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ onlyOwner ✓
☑ onlyAuthorizedIssuer ✓
☑ certificateMustExist(certUid) ✓
☑ certificateMustBeActive(certUid) ✓
☑ onlyOriginalIssuer(certUid) ✓
☑ validCertHash(certHash) ✓
☑ validCertUid(certUid) ✓

All modifiers use custom errors (EIP-838) ✓
All modifiers documented with security rationale ✓

═══════════════════════════════════════════════════════════════════════
ACCESS CONTROL REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ Owner cannot issue certificates ✓
☑ Owner cannot revoke certificates ✓
☑ Authorized issuer cannot manage other issuers ✓
☑ Authorized issuer A cannot revoke issuer B's certificates ✓
☑ Zero address cannot be authorized ✓
☑ Owner address cannot be authorized as issuer ✓
☑ Any address can call view/verification functions ✓
☑ Two-factor trust model documented ✓

═══════════════════════════════════════════════════════════════════════
SECURITY REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ No external calls (reentrancy impossible by design) ✓
☑ No tx.origin usage (phishing protection) ✓
☑ No selfdestruct (permanent contract) ✓
☑ No delegatecall (storage layout safe) ✓
☑ CEI pattern followed (checks → effects → no interactions) ✓
☑ Custom errors throughout (type-safe reverts) ✓
☑ Zero-address guards on all address parameters ✓
☑ Hash zero-value guard (bytes32(0) rejected) ✓
☑ String length guard (empty + >50 char rejected) ✓
☑ Solidity 0.8.19 (built-in overflow protection) ✓
☑ Pragma pinned (not floating) ✓
☑ All 10 threat vectors analyzed (Section 13) ✓

═══════════════════════════════════════════════════════════════════════
GAS OPTIMIZATION REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ bytes32 for hash storage (1 slot vs 3 for string) ✓
☑ calldata for string parameters in external functions ✓
☑ Custom errors (cheaper than require strings) ✓
☑ external visibility (cheaper than public for string params) ✓
☑ Struct packing (status + exists in one slot) ✓
☑ Storage references in view functions ✓
☑ Short-circuit evaluation in verifyCertificate() ✓
☑ No on-chain PII (biggest gas saving: ~100,000 gas/cert) ✓
☑ Gas budget defined per function ✓
☑ Gas reporter configured in Hardhat ✓

═══════════════════════════════════════════════════════════════════════
TESTING REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ Unit tests: 55 test cases across 4 suites ✓
☑ Integration tests: 12 test cases across 3 suites ✓
☑ Security tests: 20 test cases across 3 suites ✓
☑ Total: 87 test cases ✓
☑ Coverage target: >95% line, branch, statement ✓
☑ 100% function coverage requirement ✓
☑ Gas reporter with acceptance thresholds ✓
☑ All revert conditions have dedicated test cases ✓

═══════════════════════════════════════════════════════════════════════
DEPLOYMENT REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ Hardhat local deployment configured ✓
☑ Sepolia testnet deployment configured ✓
☑ deploy.js script copies ABI to backend + frontend ✓
☑ authorize-issuer.js post-deploy setup script ✓
☑ Etherscan verification step included ✓
☑ 6-block confirmation wait for Sepolia ✓
☑ Deployment records committed to Git ✓
☑ .env.example template provided ✓
☑ All private keys in .env (gitignored) ✓

═══════════════════════════════════════════════════════════════════════
DATABASE INTERFACE REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

☑ certificate_uid format (VARCHAR(50)) matches validCertUid modifier (max 50) ✓
☑ sha256_hash (VARCHAR(64) hex) converts to bytes32 via ethers.js ✓
☑ blockchain_transactions table fields map to TX receipt fields ✓
☑ universities.wallet_address maps to authorizedIssuers mapping key ✓
☑ blockchain_status CONFIRMED = ACTIVE on contract ✓
☑ blockchain_status REVOKED = REVOKED on contract ✓

═══════════════════════════════════════════════════════════════════════
ASSUMPTIONS VERIFICATION
═══════════════════════════════════════════════════════════════════════

☑ Assumption 01: Single contract — Registry Pattern, no proxy, no factory ✓
☑ Assumption 02: Ethereum only — no cross-chain logic ✓
☑ Assumption 03: MetaMask signing — no server-side signing ✓
☑ Assumption 04: SHA-256 fixed — bytes32 hash storage ✓
☑ Assumption 05: certificate_uid as primary key — string mapping key ✓
☑ Assumption 06: One-way revocation — no un-revoke function ✓
☑ Assumption 07: Issuer-only revocation — onlyOriginalIssuer modifier ✓
☑ Assumption 08: Owner cannot issue — confirmed by function permission matrix ✓
☑ Assumption 09: No upgradability — no proxy, no upgrade function ✓
☑ Assumption 10: Gas is issuer's responsibility — no meta-transactions ✓
☑ Assumption 11: No token economics — no ERC-20/721 ✓
☑ Assumption 12: >95% test coverage — 87 test cases targeting all paths ✓

═══════════════════════════════════════════════════════════════════════
FUTURE EXPANSION READINESS
═══════════════════════════════════════════════════════════════════════

☑ Emergency revocation gap documented with post-MVP solution path ✓
☑ Three upgrade path options analyzed and ranked ✓
☑ 8 post-MVP features identified and prioritized ✓
☑ Storage layout designed for forward compatibility ✓
☑ CertificateStatus enum extensible (SUSPENDED can be added) ✓

═══════════════════════════════════════════════════════════════════════
FINAL VERDICT: ALL SMART CONTRACT REQUIREMENTS COVERED ✓
ARCHITECTURE IS COMPLETE AND READY FOR IMPLEMENTATION ✓
═══════════════════════════════════════════════════════════════════════
```

---

## Document Control

| Field | Value |
|---|---|
| Document | Smart Contract Architecture Blueprint |
| Version | 1.0.0 |
| Status | APPROVED FOR IMPLEMENTATION |
| Dependent On | Architecture Blueprint v1.0.0 + Database Design v1.0.0 |
| Contract Name | CertificateRegistry |
| Solidity Version | ^0.8.19 |
| Framework | Hardhat |
| Networks | Hardhat Local (31337) + Sepolia (11155111) |
| Primary Pattern | Registry Pattern (non-upgradeable) |
| Total Test Cases | 87 |
| Coverage Target | ≥95% |
| Total Sections | 18 |

> **This document is the binding smart contract architecture blueprint. All implementation must follow this design exactly. Any deviation — including changing the modifier order on revokeCertificate(), altering the struct field layout, or adding external calls — requires a formal architectural review and amendment to this document before implementation proceeds.**