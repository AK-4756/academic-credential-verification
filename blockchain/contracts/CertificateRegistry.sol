// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title CertificateRegistry
/// @author Academic Credential Verification Platform
/// @notice On-chain registry for academic credential SHA-256 hashes.
///         Universities store certificate hashes; employers verify authenticity.
/// @dev Single-contract, non-upgradeable registry pattern.
///      Stores only SHA-256 hashes — never PDFs or PII on-chain.
///      Custom access control (no OpenZeppelin dependency).
///      Fixed storage layout: 3 slots + 2 dynamic mappings.
///      ~200 lines target. Gas budgets: store ≤110k, revoke ≤65k, authorize ≤55k.
contract CertificateRegistry {

    // ═══════════════════════════════════════════════════════════════════════════
    //                                  ENUMS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Certificate lifecycle states
    /// @dev ACTIVE(0) is the Solidity default for uninitialized storage,
    ///      which saves one SSTORE when creating a new CertificateRecord.
    ///      REVOKED(1) is a terminal state — no transition back to ACTIVE.
    ///      Post-MVP: SUSPENDED(2) can be appended backward-compatibly.
    enum CertificateStatus {
        ACTIVE,   // 0 — Certificate is valid and currently active
        REVOKED   // 1 — Certificate has been permanently revoked
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                                 STRUCTS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice On-chain certificate record
    /// @dev Fields are ordered for optimal storage packing (4 slots / 128 bytes):
    ///
    ///      Slot N  : certificateHash    (bytes32, 32 bytes — full slot)
    ///      Slot N+1: issuingUniversity  (address, 20 bytes) ┐
    ///               status             (uint8,    1 byte)  │ packed: 22 bytes
    ///               exists             (bool,     1 byte)  ┘
    ///      Slot N+2: issuedAt           (uint256, 32 bytes — full slot)
    ///      Slot N+3: revokedAt          (uint256, 32 bytes — full slot)
    ///
    ///      Gas cost: ~80,000 gas per new record (4 cold SSTORE × ~20,000 each)
    struct CertificateRecord {
        bytes32           certificateHash;    // SHA-256 hash of the certificate PDF binary
        address           issuingUniversity;  // University wallet (msg.sender) that stored the hash
        CertificateStatus status;             // ACTIVE or REVOKED (1-byte enum)
        bool              exists;             // Guard against zero-value struct reads
        uint256           issuedAt;           // block.timestamp when hash was stored
        uint256           revokedAt;          // 0 if active; block.timestamp when revoked
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                              CUSTOM ERRORS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @dev Caller is not the contract owner
    error NotContractOwner(address caller, address owner);

    /// @dev Caller is not in the authorized issuers whitelist
    error NotAuthorizedIssuer(address caller);

    /// @dev Caller is not the university that originally issued the certificate
    error NotOriginalIssuer(address caller, address originalIssuer);

    /// @dev A certificate record with this UID already exists on-chain
    error CertificateAlreadyExists(string certUid);

    /// @dev No certificate record found for the given UID
    error CertificateNotFound(string certUid);

    /// @dev Certificate has already been permanently revoked
    error CertificateAlreadyRevoked(string certUid, uint256 originalRevokedAt);

    /// @dev Certificate hash is bytes32(0) — rejected
    error InvalidCertificateHash();

    /// @dev Certificate UID is empty or exceeds 50 characters
    error InvalidCertificateUid(string certUid, uint256 length);

    /// @dev Address parameter is the zero address
    error InvalidAddress(address addr);

    /// @dev Issuer is already in the authorized whitelist
    error IssuerAlreadyAuthorized(address issuer);

    /// @dev Issuer is not in the authorized whitelist (for deauthorization)
    error IssuerNotAuthorized(address issuer);

    /// @dev Owner cannot also serve as an issuer (separation of concerns)
    error OwnerCannotBeIssuer(address ownerAddress);

    /// @dev Cannot transfer ownership to the zero address
    error CannotTransferToZeroAddress();

    /// @dev Cannot authorize the zero address as an issuer
    error CannotAuthorizeZeroAddress();

    /// @dev Cannot authorize the current owner as an issuer
    error CannotAuthorizeOwner(address ownerAddress);

    // ═══════════════════════════════════════════════════════════════════════════
    //                                 EVENTS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Emitted when a new certificate hash is stored on-chain
    /// @dev 3 indexed topics. string indexed is stored as keccak256(certUid).
    event CertificateStored(
        string  indexed certUid,
        bytes32 indexed certificateHash,
        address indexed issuingUniversity,
        uint256         issuedAt,
        uint256         totalCertificatesOnChain
    );

    /// @notice Emitted when a certificate is permanently revoked
    event CertificateRevoked(
        string  indexed certUid,
        address indexed revokedByUniversity,
        uint256         revokedAt,
        uint256         totalRevocationsOnChain
    );

    /// @notice Emitted when a new university wallet is authorized to issue certificates
    event IssuerAuthorized(
        address indexed issuerAddress,
        address indexed authorizedBy,
        uint256         authorizedAt
    );

    /// @notice Emitted when a university wallet is removed from the authorized issuers
    event IssuerDeauthorized(
        address indexed issuerAddress,
        address indexed deauthorizedBy,
        uint256         deauthorizedAt,
        string          reason
    );

    /// @notice Emitted when contract ownership is transferred
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner,
        uint256         transferredAt
    );

    // ═══════════════════════════════════════════════════════════════════════════
    //                             STATE VARIABLES
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Contract version identifier
    /// @dev Stored in bytecode as a constant — does not occupy a storage slot.
    string public constant CONTRACT_VERSION = "1.0.0";

    /// @dev Contract owner/admin — manages the issuer whitelist (Slot 0, 20 bytes)
    address private owner;

    /// @dev Monotonic certificate counter — incremented on each storeCertificate (Slot 1)
    uint256 private totalCertificates;

    /// @dev Monotonic revocation counter — incremented on each revokeCertificate (Slot 2)
    uint256 private totalRevocations;

    /// @dev University wallet authorization whitelist (dynamic storage)
    mapping(address => bool) private authorizedIssuers;

    /// @dev Primary certificate registry: certificate UID → CertificateRecord (dynamic storage)
    mapping(string => CertificateRecord) private certificates;

    // ═══════════════════════════════════════════════════════════════════════════
    //                               MODIFIERS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @dev Restricts function access to the contract owner
    modifier onlyOwner() {
        if (msg.sender != owner) {
            revert NotContractOwner(msg.sender, owner);
        }
        _;
    }

    /// @dev Restricts function access to authorized university issuers
    modifier onlyAuthorizedIssuer() {
        if (!authorizedIssuers[msg.sender]) {
            revert NotAuthorizedIssuer(msg.sender);
        }
        _;
    }

    /// @dev Requires that a certificate record exists for the given UID
    /// @param certUid The certificate unique identifier to check
    modifier certificateMustExist(string calldata certUid) {
        if (!certificates[certUid].exists) {
            revert CertificateNotFound(certUid);
        }
        _;
    }

    /// @dev Requires that the certificate has not been revoked
    /// @param certUid The certificate unique identifier to check
    modifier certificateMustBeActive(string calldata certUid) {
        if (certificates[certUid].status != CertificateStatus.ACTIVE) {
            revert CertificateAlreadyRevoked(certUid, certificates[certUid].revokedAt);
        }
        _;
    }

    /// @dev Restricts revocation to the university that originally issued the certificate
    /// @param certUid The certificate unique identifier to check ownership of
    modifier onlyOriginalIssuer(string calldata certUid) {
        if (certificates[certUid].issuingUniversity != msg.sender) {
            revert NotOriginalIssuer(msg.sender, certificates[certUid].issuingUniversity);
        }
        _;
    }

    /// @dev Validates that the certificate hash is not the zero value
    /// @param certHash The SHA-256 hash to validate
    modifier validCertHash(bytes32 certHash) {
        if (certHash == bytes32(0)) {
            revert InvalidCertificateHash();
        }
        _;
    }

    /// @dev Validates certificate UID length: must be 1–50 characters (bytes)
    /// @param certUid The certificate UID string to validate
    modifier validCertUid(string calldata certUid) {
        uint256 len = bytes(certUid).length;
        if (len == 0 || len > 50) {
            revert InvalidCertificateUid(certUid, len);
        }
        _;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                              CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Initializes the contract with the deployer as the owner
    /// @dev Owner is NOT added to authorizedIssuers — separation of concerns.
    ///      The owner manages the issuer whitelist but cannot issue certificates.
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender, block.timestamp);
    }
}
