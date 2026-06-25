// blockchain/.solcover.js
// Coverage configuration for solidity-coverage
// Target: >95% statements, >95% branches, 100% functions, >95% lines
module.exports = {
  skipFiles: [
    'contracts/interfaces/',  // Interfaces have no executable code
  ],
  configureYulOptimizer: false,
  // false: Consistent with viaIR: false in hardhat.config.js
  // Changing this would affect coverage measurement accuracy

  // Note: These are the MINIMUM files to skip
  // Do not skip any implementation files — all must be covered
};
