'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { resolveKernelRevision } = require('../lib/go-resolve');

const DB = '/app/workbook/data/workbook.sqlite';
const FIXTURES = '/app/workbook/fixtures/sweeps';

function runSql(sql) {
  execFileSync('sqlite3', [DB], { input: sql, encoding: 'utf8' });
}

function sqlString(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function up() {
  const files = fs
    .readdirSync(FIXTURES)
    .filter((name) => name.endsWith('.json'))
    .sort();
  for (const name of files) {
    const payload = JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf8'));
    const sweepId = payload.meta?.run?.id;
    if (!sweepId) {
      continue;
    }
    const kernel = payload.meta.run.kernel;
    const kernelRevision = resolveKernelRevision(kernel);
    const dt = Number(payload.params.dt);
    const dimension = Number(payload.params.dimension);
    const fitLagMin = Number(payload.params.fit_lag_min ?? 2);
    const fitLagMax = Number(payload.params.fit_lag_max ?? 5);
    runSql(
      `INSERT OR REPLACE INTO sweeps (sweep_id, kernel_revision, dt, dimension, fit_lag_min, fit_lag_max) VALUES (${sqlString(sweepId)}, ${sqlString(kernelRevision)}, ${dt}, ${dimension}, ${fitLagMin}, ${fitLagMax});`
    );
    const points = payload.series?.msd || [];
    for (const point of points) {
      const lag = Number(point.step);
      const msd = Number(point.msd);
      runSql(
        `INSERT OR REPLACE INTO msd_points (sweep_id, lag_step, msd) VALUES (${sqlString(sweepId)}, ${lag}, ${msd});`
      );
    }
  }
}

module.exports = { up };
