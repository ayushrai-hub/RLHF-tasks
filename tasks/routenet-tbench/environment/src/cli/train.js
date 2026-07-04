#!/usr/bin/env node
"use strict";

const path = require("path");
const tf = require("@tensorflow/tfjs");

const { parseArgv, readJson, makePrng } = require(path.join(__dirname, "..", "lib", "util"));
const { connect, disconnect, fetchEdges, fetchNodeIds } = require(path.join(__dirname, "..", "lib", "db"));
const { sampleHardNegatives } = require(path.join(__dirname, "..", "lib", "sampler"));
const { makeEmbeddings, batchLogits, bceLoss } = require(path.join(__dirname, "..", "lib", "model"));
const { auc } = require(path.join(__dirname, "..", "lib", "metrics"));

async function trainOnce(client, cfg) {
  const nodeIds = await fetchNodeIds(client);
  const trainPos = await fetchEdges(client, "train");
  const valPos = await fetchEdges(client, "val");

  const numNodes = nodeIds.length;
  const prng = makePrng(cfg.seed);
  const embeddings = makeEmbeddings(numNodes, cfg.embedding_dim, prng);
  const optimizer = tf.train.adam(cfg.learning_rate);

  for (let epoch = 0; epoch < cfg.epochs; epoch++) {
    const negResult = await sampleHardNegatives({
      seed: cfg.seed + epoch,
      k: cfg.negatives_per_epoch,
    });
    const posPairs = trainPos.map((e) => [e.u, e.v]);
    const negPairs = negResult.negatives;

    const pairs = posPairs.concat(negPairs);
    const labels = posPairs.map(() => 1).concat(negPairs.map(() => 0));

    optimizer.minimize(() => {
      const logits = batchLogits(embeddings, pairs);
      return bceLoss(logits, labels);
    });
  }

  const valPairs = valPos.map((e) => [e.u, e.v]);
  const valNegResult = await sampleHardNegatives({
    seed: cfg.seed + 9999,
    k: valPairs.length,
  });
  const evalPairs = valPairs.concat(valNegResult.negatives);
  const evalLabels = valPairs.map(() => 1).concat(valNegResult.negatives.map(() => 0));

  const logits = batchLogits(embeddings, evalPairs).arraySync();
  const score = auc(logits, evalLabels);

  return { auc: score, source: valNegResult.source };
}

async function main() {
  const args = parseArgv(process.argv.slice(2));
  const cfgPath = args.config || "/app/config/trainer.json";
  const cfg = readJson(cfgPath);

  const client = await connect();
  try {
    const out = await trainOnce(client, cfg);
    process.stdout.write(`validation auc = ${out.auc.toFixed(4)} (negatives source=${out.source})\n`);
    if (out.auc < cfg.validation.target) {
      process.exitCode = 3;
    }
  } finally {
    await disconnect(client);
  }
}

main().catch((err) => {
  process.stderr.write(`train failed: ${err.stack || err.message || err}\n`);
  process.exit(1);
});
