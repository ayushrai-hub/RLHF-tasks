"use strict";

const fs = require("fs");
const path = require("path");

function parseArgv(argv) {
  const out = {};
  for (const arg of argv) {
    if (!arg.startsWith("--")) continue;
    const eq = arg.indexOf("=");
    if (eq === -1) {
      out[arg.slice(2)] = true;
    } else {
      const key = arg.slice(2, eq);
      const val = arg.slice(eq + 1);
      out[key] = val;
    }
  }
  return out;
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function writeJson(p, obj) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(obj, null, 2) + "\n", "utf8");
}

function canonicalPair(a, b) {
  return a < b ? [a, b] : [b, a];
}

function pairKey(a, b) {
  const [x, y] = canonicalPair(a, b);
  return `${x},${y}`;
}

module.exports = {
  parseArgv,
  readJson,
  writeJson,
  canonicalPair,
  pairKey,
};
