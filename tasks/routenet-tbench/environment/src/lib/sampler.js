"use strict";

const fs = require("fs");
const path = require("path");

const SNAPSHOT = path.join(__dirname, "../../data/snapshot.json");

async function sampleHardNegatives({ seed, k }) {
  const blob = JSON.parse(fs.readFileSync(SNAPSHOT, "utf8"));
  const ids = blob.nodes.map((n) => n.id);
  const edges = new Set();
  for (const e of blob.edges) {
    const lo = Math.min(e.u, e.v);
    const hi = Math.max(e.u, e.v);
    edges.add(`${lo},${hi}`);
  }

  const negatives = [];
  let attempts = 0;
  while (negatives.length < k && attempts < k * 500) {
    attempts += 1;
    const i = Math.floor(Math.random() * ids.length);
    let j = Math.floor(Math.random() * ids.length);
    if (i === j) continue;
    const u = ids[i];
    const v = ids[j];
    const key = `${Math.min(u, v)},${Math.max(u, v)}`;
    if (edges.has(key)) continue;
    negatives.push([u, v]);
  }

  if (negatives.length < k && ids.length >= 2) {
    negatives.push([ids[0], ids[1]]);
  }

  return {
    seed: seed | 0,
    k: k | 0,
    source: "snapshot",
    negatives: negatives.slice(0, k),
  };
}

module.exports = { sampleHardNegatives };
