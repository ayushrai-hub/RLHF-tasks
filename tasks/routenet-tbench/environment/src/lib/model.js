"use strict";

const tf = require("@tensorflow/tfjs");

function makeEmbeddings(numNodes, dim, prng) {
  const init = new Float32Array(numNodes * dim);
  for (let i = 0; i < init.length; i++) {
    init[i] = (prng() - 0.5) * 0.1;
  }
  return tf.variable(tf.tensor2d(init, [numNodes, dim]), true, "embeddings");
}

function scorePair(embeddings, u, v) {
  return tf.tidy(() => {
    const eu = embeddings.gather([u]);
    const ev = embeddings.gather([v]);
    return tf.sum(tf.mul(eu, ev), 1);
  });
}

function batchLogits(embeddings, pairs) {
  return tf.tidy(() => {
    const us = pairs.map((p) => p[0]);
    const vs = pairs.map((p) => p[1]);
    const eu = embeddings.gather(us);
    const ev = embeddings.gather(vs);
    return tf.sum(tf.mul(eu, ev), 1);
  });
}

function bceLoss(logits, labels) {
  return tf.tidy(() => {
    const y = tf.tensor1d(labels);
    return tf.losses.sigmoidCrossEntropy(y, logits);
  });
}

module.exports = {
  makeEmbeddings,
  scorePair,
  batchLogits,
  bceLoss,
};
