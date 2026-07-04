#!/usr/bin/env node
"use strict";

const path = require("path");

const { parseArgv, writeJson } = require(path.join(__dirname, "..", "lib", "util"));
const { sampleHardNegatives } = require(path.join(__dirname, "..", "lib", "sampler"));

async function main() {
  const args = parseArgv(process.argv.slice(2));

  if (args.seed === undefined || args.k === undefined || args.output === undefined) {
    process.stderr.write(
      "Usage: node src/cli/sample.js --seed=<int> --k=<int> --output=<path>\n",
    );
    process.exit(2);
  }

  const seed = parseInt(args.seed, 10);
  const k = parseInt(args.k, 10);
  if (!Number.isFinite(seed) || !Number.isFinite(k) || k <= 0) {
    process.stderr.write("seed and k must be integers; k must be positive\n");
    process.exit(2);
  }

  const result = await sampleHardNegatives({ seed, k });
  writeJson(args.output, result);

  process.stdout.write(
    `wrote ${result.negatives.length} negatives to ${args.output} (source=${result.source})\n`,
  );
}

main().catch((err) => {
  process.stderr.write(`sample failed: ${err.stack || err.message || err}\n`);
  process.exit(1);
});
