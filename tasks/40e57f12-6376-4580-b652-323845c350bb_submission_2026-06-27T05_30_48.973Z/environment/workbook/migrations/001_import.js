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

function up() {
  const files = fs.readdirSync(FIXTURES).filter((name) => name.endsWith('.json'));
  for (const name of files) {
    const payload = JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf8'));
    const sweepId = payload.id || name.replace('.json', '');
    const kernel = payload.meta?.run?.kernel || payload.kernel || 'unknown';
    const dt = Number(payload.params?.dt || payload.dt || 0.01);
    const dimension = Number(payload.params?.dimension || payload.dimension || 2);
    runSql(
      `INSERT OR REPLACE INTO sweeps (sweep_id, kernel_revision, dt, dimension) VALUES ('${sweepId}', '${kernel}', ${dt}, ${dimension});`
    );
    const points = payload.msd || payload.series?.msd || [];
    for (const point of points) {
      const lag = Number(point.lag || point.step || 0);
      const msd = Number(point.msd || point.value || 0);
      runSql(
        `INSERT OR REPLACE INTO msd_points (sweep_id, lag_step, msd) VALUES ('${sweepId}', ${lag}, ${msd});`
      );
    }
  }
}

module.exports = { up };
