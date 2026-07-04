"use strict";

function auc(scores, labels) {
  const n = scores.length;
  const idx = scores.map((_, i) => i).sort((a, b) => scores[a] - scores[b]);
  let pos = 0;
  let neg = 0;
  for (const l of labels) {
    if (l > 0.5) pos++; else neg++;
  }
  if (pos === 0 || neg === 0) return 0.5;

  let rankSum = 0;
  let i = 0;
  let rank = 1;
  while (i < n) {
    let j = i;
    while (j < n && scores[idx[j]] === scores[idx[i]]) j++;
    const avgRank = (rank + (j - i + rank - 1)) / 2;
    for (let m = i; m < j; m++) {
      if (labels[idx[m]] > 0.5) rankSum += avgRank;
    }
    rank += j - i;
    i = j;
  }
  return (rankSum - (pos * (pos + 1)) / 2) / (pos * neg);
}

function hitsAtK(scores, labels, k) {
  const idx = scores.map((_, i) => i).sort((a, b) => scores[b] - scores[a]);
  let hits = 0;
  for (let i = 0; i < Math.min(k, idx.length); i++) {
    if (labels[idx[i]] > 0.5) hits++;
  }
  return hits / k;
}

module.exports = { auc, hitsAtK };
