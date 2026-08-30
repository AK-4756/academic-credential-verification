// blockchain/test/helpers/utils.js
// Shared test utility functions
const { ethers } = require("hardhat");

/**
 * Generate a unique certificate UID for testing
 * @param {string} prefix - University prefix (e.g., "MIT")
 * @param {number} seq - Sequence number
 * @returns {string} Formatted UID
 */
function generateTestUid(prefix = "TEST", seq = 1) {
  return `${prefix}-2025-${String(seq).padStart(5, "0")}`;
}

/**
 * Create a SHA-256-like hash from a content string
 * Uses keccak256 (available in ethers) as test-compatible hash
 * @param {string} content - Content to hash
 * @returns {string} bytes32 hex string
 */
function generateTestHash(content) {
  return ethers.keccak256(ethers.toUtf8Bytes(content));
}

module.exports = {
  generateTestUid,
  generateTestHash,
};
