#!/usr/bin/env node
"use strict";

const args = process.argv.slice(2);
if (args.length < 2) {
  process.stderr.write("usage: calibrate.js <temperature> <logit>...\n");
  process.exit(2);
}
const temperature = Number(args[0]);
if (!Number.isFinite(temperature) || temperature <= 0) {
  process.stderr.write("invalid temperature\n");
  process.exit(2);
}
const logits = args.slice(1).map(Number);
if (logits.some((v) => !Number.isFinite(v))) {
  process.stderr.write("invalid logits\n");
  process.exit(2);
}
const scaled = logits.map((l) => l / temperature);
const max = Math.max(...scaled);
const exps = scaled.map((l) => Math.exp(l - max));
const sum = exps.reduce((a, b) => a + b, 0);
const probs = exps.map((e) => e / sum);
process.stdout.write(JSON.stringify(probs));
