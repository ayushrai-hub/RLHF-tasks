// Decoy Two
// Logs simplified representation of boolean flag attributes.

function logFlagsInfo(flags) {
  console.log("Active flags configuration context:");
  for (const [key, value] of Object.entries(flags)) {
    console.log(`  Flag: ${key} = ${value}`);
  }
}

module.exports = { logFlagsInfo };
