'use strict';

const { queryRows, round6 } = require('../lib/msd');
const { execFileSync } = require('child_process');

const DB = '/app/workbook/data/workbook.sqlite';

function runSql(sql) {
  execFileSync('sqlite3', [DB], { input: sql, encoding: 'utf8' });
}

function up() {
  runSql('DELETE FROM diffusion_summary;');
  const sweeps = queryRows('SELECT sweep_id, kernel_revision, dt, dimension FROM sweeps');
  for (const row of sweeps) {
    const [sweepId, kernelRevision, dtRaw, dimensionRaw] = row;
    const dt = Number(dtRaw);
    const dimension = Number(dimensionRaw);
    const points = queryRows(
      `SELECT lag_step, msd FROM msd_points WHERE sweep_id = '${sweepId}' ORDER BY lag_step ASC`
    );
    const last = points[points.length - 1];
    const lastLag = Number(last[0]);
    const lastMsd = Number(last[1]);
    const diffusionCoeff = round6(lastMsd / (2 * lastLag));
    let rss = 0;
    for (const point of points) {
      rss += Number(point[1]);
    }
    runSql(
      `INSERT OR REPLACE INTO diffusion_summary (sweep_id, kernel_revision, diffusion_coeff, rss) VALUES ('${sweepId}', '${kernelRevision}', ${diffusionCoeff}, ${round6(rss)});`
    );
  }
}

module.exports = { up };
