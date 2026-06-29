'use strict';

const crypto = require('crypto');
const fs = require('fs');
const { queryRows } = require('./msd');

const OUT = '/app/workbook/out/summary.checksum';

function formatNumber(value) {
  return Number(value).toFixed(3);
}

function formatRow(row) {
  const [sweepId, kernelRevision, diffusionCoeff, rss] = row;
  return (
    `{"sweep_id":"${sweepId}","kernel_revision":"${kernelRevision}",` +
    `"diffusion_coeff":${formatNumber(diffusionCoeff)},"rss":${formatNumber(rss)}}`
  );
}

function canonicalBody() {
  const rows = queryRows(
    'SELECT sweep_id, kernel_revision, diffusion_coeff, rss FROM diffusion_summary ORDER BY kernel_revision DESC'
  );
  return rows.map(formatRow).join('\n');
}

function writeChecksum() {
  const body = canonicalBody();
  const digest = crypto.createHash('sha256').update(body, 'utf8').digest('hex');
  fs.mkdirSync('/app/workbook/out', { recursive: true });
  fs.writeFileSync(OUT, `${digest}\n`, 'utf8');
  return digest;
}

module.exports = { writeChecksum, canonicalBody };
