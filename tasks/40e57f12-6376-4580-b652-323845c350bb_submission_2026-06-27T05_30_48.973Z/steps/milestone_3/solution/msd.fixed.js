'use strict';

const { execFileSync } = require('child_process');

const DB = '/app/workbook/data/workbook.sqlite';

function query(sql) {
  const out = execFileSync('sqlite3', ['-separator', '|', DB, sql], {
    encoding: 'utf8',
  });
  return out.trim();
}

function queryRows(sql) {
  const raw = query(sql);
  if (!raw) {
    return [];
  }
  return raw.split('\n').map((line) => line.split('|'));
}

function round6(value) {
  return Number(Number(value).toFixed(6));
}

function fitDiffusion(lags, msds, dimension, dt, fitLagMin, fitLagMax) {
  const fitLags = [];
  const fitMsds = [];
  for (let i = 0; i < lags.length; i += 1) {
    if (lags[i] >= fitLagMin && lags[i] <= fitLagMax) {
      fitLags.push(lags[i]);
      fitMsds.push(msds[i]);
    }
  }
  const xs = fitLags.map((k) => 2 * dimension * k * dt);
  let sumXX = 0;
  let sumXY = 0;
  for (let i = 0; i < xs.length; i += 1) {
    sumXX += xs[i] * xs[i];
    sumXY += xs[i] * fitMsds[i];
  }
  const slope = sumXY / sumXX;
  let rss = 0;
  for (let i = 0; i < xs.length; i += 1) {
    const predicted = slope * xs[i];
    const residual = fitMsds[i] - predicted;
    rss += residual * residual;
  }
  return { diffusionCoeff: round6(slope), rss: round6(rss) };
}

module.exports = { query, queryRows, fitDiffusion, round6, DB };
