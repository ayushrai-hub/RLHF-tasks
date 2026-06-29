'use strict';

const { queryRows, fitDiffusion } = require('../lib/msd');
const { execFileSync } = require('child_process');

const DB = '/app/workbook/data/workbook.sqlite';

function runSql(sql) {
  execFileSync('sqlite3', [DB], { input: sql, encoding: 'utf8' });
}

function sqlString(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function up() {
  runSql('DELETE FROM diffusion_summary;');
  const sweeps = queryRows(
    'SELECT sweep_id, kernel_revision, dt, dimension, fit_lag_min, fit_lag_max FROM sweeps'
  );
  for (const row of sweeps) {
    const [sweepId, kernelRevision, dtRaw, dimensionRaw, fitLagMinRaw, fitLagMaxRaw] = row;
    const dt = Number(dtRaw);
    const dimension = Number(dimensionRaw);
    const fitLagMin = Number(fitLagMinRaw);
    const fitLagMax = Number(fitLagMaxRaw);
    const points = queryRows(
      `SELECT lag_step, msd FROM msd_points WHERE sweep_id = ${sqlString(sweepId)} ORDER BY lag_step ASC`
    );
    const lags = points.map((point) => Number(point[0]));
    const msds = points.map((point) => Number(point[1]));
    const { diffusionCoeff, rss } = fitDiffusion(
      lags,
      msds,
      dimension,
      dt,
      fitLagMin,
      fitLagMax
    );
    runSql(
      `INSERT OR REPLACE INTO diffusion_summary (sweep_id, kernel_revision, diffusion_coeff, rss) VALUES (${sqlString(sweepId)}, ${sqlString(kernelRevision)}, ${diffusionCoeff}, ${rss});`
    );
  }
}

module.exports = { up };
