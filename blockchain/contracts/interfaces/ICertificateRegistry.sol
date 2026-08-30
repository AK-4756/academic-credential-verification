// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title ICertificateRegistry
/// @author Academic Credential Verification Platform
/// @notice Interface for the on-chain academic credential registry.
///         Defines the public API for certificate storage, verification,
///         revocation, and issuer management.
/// @dev Enables backend (Web3.py) to import a minimal ABI without the
///      full implementation. Future contracts can interact with the
///      registry through this standard interface.
interface ICertificateRegistry {

    // ═══════════════════════════════════════════════════════════════════════════
    //                                  ENUMS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Certificate lifecycle states
    enum CertificateStatus {
        ACTIVE,   // 0 — Certificate is valid and currently active
        REVOKED   // 1 — Certificate has been permanently revoked
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                                 STRUCTS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice On-chain certificate record
    struct CertificateRecord {
        bytes32           certificateHash;    // SHA-256 hash of the certificate PDF binary
        address           issuingUniversity;  // University wallet that stored the hash
        CertificateStatus status;             // ACTIVE or REVOKED
        bool              exists;             // Guard against zero-value struct reads
        uint256           issuedAt;           // block.timestamp when hash was stored
        uint256           revokedAt;          // 0 if active; block.timestamp when revoked
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                                 EVENTS
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Emitted when a new certificate hash is stored on-chain
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
    //                          ADMIN FUNCTIONS (onlyOwner)
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Adds a university wallet to the authorized issuers whitelist
    /// @param issuerAddress The university wallet address to authorize
    function authorizeIssuer(address issuerAddress) external;

    /// @notice Removes a university wallet from the authorized issuers whitelist
    /// @param issuerAddress The university wallet address to deauthorize
    /// @param reason Human-readable reason for deauthorization
    function deauthorizeIssuer(address issuerAddress, string calldata reason) external;

    /// @notice Transfers contract ownership to a new address
    /// @param newOwner The address of the new contract owner
    function transferOwnership(address newOwner) external;

    // ═══════════════════════════════════════════════════════════════════════════
    //                     WRITE FUNCTIONS (onlyAuthorizedIssuer)
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Stores a new certificate hash on-chain
    /// @param certUid The unique certificate identifier (1–50 characters)
    /// @param certHash The SHA-256 hash of the certificate PDF binary (bytes32)
    function storeCertificate(string calldata certUid, bytes32 certHash) external;

    /// @notice Permanently revokes a certificate — terminal state, cannot be undone
    /// @param certUid The certificate UID to revoke
    function revokeCertificate(string calldata certUid) external;

    // ═══════════════════════════════════════════════════════════════════════════
    //                          VIEW FUNCTIONS (public, no gas)
    // ═══════════════════════════════════════════════════════════════════════════

    /// @notice Returns the contract version string
    /// @return The version string (e.g., "1.0.0")
    function CONTRACT_VERSION() external view returns (string memory);

    /// @notice Verifies a certificate hash against the on-chain record
    /// @param certUid The certificate UID to verify
    /// @param submittedHash The SHA-256 hash to compare against the stored hash
    /// @return isValid True only if the certificate is ACTIVE and hashes match
    /// @return status The current CertificateStatus (ACTIVE or REVOKED)
    function verifyCertificate(
        string calldata certUid,
        bytes32 submittedHash
    ) external view returns (bool isValid, CertificateStatus status);

    /// @notice Returns the complete on-chain record for a certificate UID
    /// @param certUid The certificate UID to look up
    /// @return The full CertificateRecord struct (memory copy)
    function getCertificateRecord(
        string calldata certUid
    ) external view returns (CertificateRecord memory);

    /// @notice Checks whether a wallet address is an authorized certificate issuer
    /// @param wallet The address to check
    /// @return True if the wallet is authorized to issue certificates
    function isAuthorizedIssuer(address wallet) external view returns (bool);

    /// @notice Returns the current contract owner address
    /// @return The owner address
    function getOwner() external view returns (address);

    /// @notice Returns the total number of certificates stored on-chain
    /// @return The monotonic certificate counter value
    function getCertificateCount() external view returns (uint256);

    /// @notice Returns the total number of certificates that have been revoked
    /// @return The monotonic revocation counter value
    function getRevocationCount() external view returns (uint256);
}
