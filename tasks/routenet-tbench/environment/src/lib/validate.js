"use strict";

function isFiniteInt(x) {
  return typeof x === "number" && Number.isFinite(x) && Math.floor(x) === x;
}

function validateSeed(seed) {
  if (!isFiniteInt(seed)) {
    throw new Error(`seed must be an integer, got ${seed} (${typeof seed})`);
  }
}

function validateK(k) {
  if (!isFiniteInt(k) || k <= 0) {
    throw new Error(`k must be a positive integer, got ${k}`);
  }
}

function validatePair(pair, nodeIds) {
  if (!Array.isArray(pair) || pair.length !== 2) {
    throw new Error(`pair must be a 2-element array, got ${JSON.stringify(pair)}`);
  }
  const [u, v] = pair;
  if (!isFiniteInt(u) || !isFiniteInt(v)) {
    throw new Error(`pair members must be integers, got [${u}, ${v}]`);
  }
  if (u === v) {
    throw new Error(`pair must have distinct endpoints, got [${u}, ${v}]`);
  }
  if (nodeIds && !(nodeIds.has(u) && nodeIds.has(v))) {
    throw new Error(`pair members must be known node ids, got [${u}, ${v}]`);
  }
}

module.exports = {
  isFiniteInt,
  validateSeed,
  validateK,
  validatePair,
};
