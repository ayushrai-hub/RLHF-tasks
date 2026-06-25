#!/bin/bash
set -euo pipefail

cd /app

cat > /app/src/index.ts << 'TSEOF'
import { Command } from 'commander';
import * as fs from 'fs';
import * as path from 'path';
import { openDatabase } from './db/connection.js';
import { getStationIds, getReadings } from './db/queries.js';
import { CalibrationParams, EventCatalog, DetectedEvent } from './types.js';
import { PRESSURE_TO_DISPLACEMENT_M_PER_KPA, MAD_CONSISTENCY_CONSTANT } from './config.js';
import { logger } from './logger.js';

// ── Dossier parsing ──────────────────────────────────────────────────────────

function parseDossier(text: string): Map<string, CalibrationParams> {
  const result = new Map<string, CalibrationParams>();
  const stations = ['AXID01', 'AXID02', 'NEMO01', 'JUAN01', 'COAX01'];

  // Strategy 1: Section 29 subsections (Quality Control Event Log: January 2024)
  // Each subsection covers one station's January 2024 calibration status.
  const sec29Idx = text.indexOf('Quality Control Event Log: January 2024');
  const sec30Idx = text.indexOf('\n## 30.');
  if (sec29Idx >= 0) {
    const sec29 = sec30Idx > sec29Idx
      ? text.slice(sec29Idx, sec30Idx)
      : text.slice(sec29Idx, sec29Idx + 20000);

    // Split on subsection headings (### 29.N ...)
    const subsections = sec29.split(/\n###\s+29\.\d+\s+/);
    for (const sub of subsections) {
      for (const sid of stations) {
        if (!result.has(sid) && sub.includes(sid)) {
          const p = parseBlock(sub, sid);
          if (p) result.set(sid, p);
        }
      }
    }
  }

  // Strategy 2: Appendix F structured blocks (if the document version includes them)
  const appendixFIdx = text.indexOf('Appendix F');
  const appendixGIdx = text.indexOf('Appendix G');
  if (appendixFIdx >= 0) {
    const appendixF = appendixGIdx > appendixFIdx
      ? text.slice(appendixFIdx, appendixGIdx)
      : text.slice(appendixFIdx);
    const blocks = appendixF.split(/\n\n(?=\*\*Station )/);
    for (const block of blocks) {
      const m = /\*\*Station ([A-Z0-9]+)/.exec(block);
      if (!m) continue;
      const sid = m[1];
      if (result.has(sid)) continue;
      const p = parseBlock(block, sid);
      if (p) result.set(sid, p);
    }
  }

  // Strategy 3: Main station section headings (## N. Station SID ...)
  for (const sid of stations) {
    if (result.has(sid)) continue;
    const sectionPat = new RegExp(
      `## \\d+\\.\\s+Station ${sid}[\\s\\S]{0,12000}?(?=\\n## \\d+\\.)`,
      'i',
    );
    const m = sectionPat.exec(text);
    if (m) {
      const p = parseBlock(m[0], sid);
      if (p) result.set(sid, p);
    }
  }

  // Strategy 4: Any 800-char slice around each station mention
  for (const sid of stations) {
    if (result.has(sid)) continue;
    const idx = text.indexOf(sid);
    if (idx >= 0) {
      const p = parseBlock(text.slice(Math.max(0, idx - 200), idx + 10000), sid);
      if (p) result.set(sid, p);
    }
  }

  return result;
}

function parseBlock(text: string, sid: string): CalibrationParams | null {
  const gain   = extractGain(text);
  const offset = extractOffset(text);
  const zTh    = extractZThreshold(text);
  const minDur = extractMinDuration(text);

  if (gain === null || offset === null || zTh === null || minDur === null) {
    logger.debug(`Could not extract all params for ${sid}: gain=${gain} offset=${offset} z=${zTh} dur=${minDur}`);
    return null;
  }

  const mw = extractMaintenanceWindows(text);
  logger.info(`  ${sid}: gain=${gain}, offset=${offset}, z=${zTh}, minDur=${minDur}h, maint=${mw.length}`);
  return {
    station_id:          sid,
    pressure_gain:       gain,
    pressure_offset:     offset,
    z_score_threshold:   zTh,
    min_duration_hours:  minDur,
    maintenance_windows: mw,
  };
}

// ── Value extractors ──────────────────────────────────────────────────────────

function extractGain(text: string): number | null {
  const pats = [
    // "Pressure gain: 1.0247"  (structured format)
    /pressure\s+gain\s*[:=]\s*([\d]+\.[\d]+)/i,
    // "gain of 1.0247"  (prose with preposition)
    /\bgain\s+of\s+([\d]+\.[\d]+)/i,
    // "gain correction factor is 1.0247"
    /gain\s+correction\s+(?:factor\s+)?(?:is\s+)?([\d]+\.[\d]+)/i,
    // "calibration parameters of gain 0.9891" or "gain 1.12"
    /\bgain\s+([\d]+\.[\d]+)/i,
    /multiplicative\s+gain\s+correction[^0-9]*([\d]+\.[\d]+)/i,
  ];
  for (const p of pats) {
    const m = p.exec(text);
    if (m) {
      const v = parseFloat(m[1]);
      if (v > 0.5 && v < 2.5) return v;
    }
  }
  return null;
}

function extractOffset(text: string): number | null {
  const pats = [
    // "Pressure offset: −0.183 kPa" or "+0.380 kPa"  (structured)
    /pressure\s+offset\s*[:=]\s*([^\s,\n]{1,12})\s*(?:kPa)?/i,
    // "offset of −0.183 kPa" or "offset +0.072 kPa"  (prose)
    /\boffset\s+(?:of\s+)?([+−\-][\s\d.]+|\d+\.\d+)\s*(?:kPa)?/i,
    // Formula: "raw_value × 1.0247 + (−0.183)"
    /raw_value\s*[×x*]\s*[\d.]+\s*\+\s*\(\s*([−+\-][\d.]+)\s*\)/i,
    // "additive pressure offset is −0.183"
    /additive\s+(?:pressure\s+)?offset(?:\s+is)?\s+([^\s,kK]{1,12})\s*(?:kPa|kilo)?/i,
  ];
  for (const p of pats) {
    const m = p.exec(text);
    if (m) {
      const raw = m[1].replace(/−/g, '-').replace(/\s/g, '');
      const v = parseFloat(raw);
      if (!isNaN(v) && Math.abs(v) < 10) return v;
    }
  }
  return null;
}

function extractZThreshold(text: string): number | null {
  const pats = [
    // "Z-score threshold: 3.5 standard deviations"  (structured)
    /z.score\s+threshold\s*[:=]\s*([\d]+\.[\d]*)\s*(?:standard\s+deviations?|sigma)?/i,
    // "Z-score threshold of 3.5 sigma"  (prose)
    /z.score\s+threshold\s+of\s+([\d]+\.[\d]*)\s*(?:sigma|standard)?/i,
    // "threshold of 3.5 sigma" / "3.5 sigma"
    /threshold\s+(?:of\s+)?([\d]+\.[\d]*)\s+(?:sigma|standard\s+deviation)/i,
    /\b([\d]+\.[\d]*)\s+sigma\b/i,
    /detection\s+threshold[^0-9]*([\d]+\.[\d]*)/i,
  ];
  for (const p of pats) {
    const m = p.exec(text);
    if (m) {
      const v = parseFloat(m[1]);
      if (v > 0.5 && v < 15) return v;
    }
  }
  return null;
}

function extractMinDuration(text: string): number | null {
  const pats = [
    // "Minimum event duration: 2.0 hours"  (structured)
    /minimum\s+event\s+duration\s*[:=]\s*([\d]+\.[\d]*)\s+hours?/i,
    // "minimum duration criterion of 2.0 hours"  (prose)
    /minimum\s+duration\s+criterion\s+(?:of\s+)?([\d]+\.[\d]*)\s+hours?/i,
    // "minimum duration 2.0 hours" / "minimum duration of 2.0 hours"
    /minimum\s+(?:sustained\s+)?duration(?:\s+(?:is|of|required))?\s+(?:is\s+)?([\d]+\.[\d]*)\s+hours?/i,
    /duration\s+criterion[^0-9]*([\d]+\.[\d]*)\s+hours?/i,
    /lasting\s+(?:fewer|less)\s+than\s+([\d]+\.[\d]*)\s+hours?/i,
  ];
  for (const p of pats) {
    const m = p.exec(text);
    if (m) {
      const v = parseFloat(m[1]);
      if (v > 0 && v < 48) return v;
    }
  }
  return null;
}

function extractMaintenanceWindows(
  text: string,
): Array<{ start: Date; end: Date; reason: string }> {
  const windows: Array<{ start: Date; end: Date; reason: string }> = [];

  // "January 8 through January 12, 2024" or "January 8–12, 2024"
  // "2024-01-08T00:00:00Z and 2024-01-12T23:59:59Z"
  const prose = /january\s+(\d{1,2})[^0-9]+(\d{1,2})[^0-9]*2024/gi;
  const iso   = /2024-01-(\d{2})T[^Z]*Z[^0-9]+2024-01-(\d{2})/gi;

  for (const pat of [prose, iso]) {
    let m: RegExpExecArray | null;
    while ((m = pat.exec(text)) !== null) {
      const d1 = parseInt(m[1], 10);
      const d2 = parseInt(m[2], 10);
      if (d1 >= 1 && d1 <= 31 && d2 >= d1 && d2 <= 31) {
        windows.push({
          start:  new Date(`2024-01-${String(d1).padStart(2, '0')}T00:00:00.000Z`),
          end:    new Date(`2024-01-${String(d2).padStart(2, '0')}T23:59:59.999Z`),
          reason: 'Maintenance window per operations dossier',
        });
        break;
      }
    }
    if (windows.length > 0) break;
  }
  return windows;
}

// ── Signal processing ─────────────────────────────────────────────────────────

function applyCalibration(raw: number[], gain: number, offset: number): number[] {
  return raw.map(v => v * gain + offset);
}

function detrend(values: number[]): number[] {
  const n = values.length;
  if (n < 2) return values.slice();
  let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (let i = 0; i < n; i++) { sx += i; sy += values[i]; sxx += i*i; sxy += i*values[i]; }
  const denom = n*sxx - sx*sx;
  if (Math.abs(denom) < 1e-12) return values.map(v => v - sy/n);
  const slope = (n*sxy - sx*sy) / denom;
  const intercept = (sy - slope*sx) / n;
  return values.map((v, i) => v - (slope*i + intercept));
}

function medianOf(sorted: number[]): number {
  const n = sorted.length;
  if (n === 0) return 0;
  const mid = Math.floor(n / 2);
  return n % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function computeMAD(values: number[]): { med: number; mad: number } {
  const sorted = values.slice().sort((a, b) => a - b);
  const med = medianOf(sorted);
  const absDevsSorted = values.map(v => Math.abs(v - med)).sort((a, b) => a - b);
  return { med, mad: medianOf(absDevsSorted) };
}

function robustZScores(values: number[]): number[] {
  const { med, mad } = computeMAD(values);
  const sigma = MAD_CONSISTENCY_CONSTANT * (mad > 1e-12 ? mad : 1e-12);
  return values.map(v => (v - med) / sigma);
}

function bayesianConfidence(window: number[], bgSigma: number): number {
  const n = window.length;
  if (n === 0) return 0;
  const delta = window.reduce((a, b) => a + b, 0) / n;
  const sig2 = bgSigma * bgSigma;
  if (sig2 < 1e-20) return 0;
  const logBF = (n * delta * delta) / (2 * sig2) - 0.5 * Math.log(n);
  return 1 / (1 + Math.exp(-logBF / 2.0));
}

// ── Event detection ───────────────────────────────────────────────────────────

function detectEvents(
  stationId: string,
  timestamps: Date[],
  calibrated: number[],
  params: CalibrationParams,
): DetectedEvent[] {
  const detrended  = detrend(calibrated);
  const zScores    = robustZScores(detrended);
  const { mad }    = computeMAD(detrended);
  const bgSigma    = MAD_CONSISTENCY_CONSTANT * (mad > 1e-12 ? mad : 1e-12);
  const minSamples = Math.ceil(params.min_duration_hours * 6);

  const events: DetectedEvent[] = [];
  let i = 0;
  while (i < zScores.length) {
    if (Math.abs(zScores[i]) >= params.z_score_threshold) {
      let j = i + 1;
      while (j < zScores.length && Math.abs(zScores[j]) >= params.z_score_threshold) j++;

      if (j - i >= minSamples) {
        const win = detrended.slice(i, j);
        const meanAnomaly  = win.reduce((a, b) => a + b, 0) / win.length;
        const displacement = meanAnomaly * PRESSURE_TO_DISPLACEMENT_M_PER_KPA;
        const confidence   = bayesianConfidence(win, bgSigma);
        const startTime    = timestamps[i];
        const endTime      = timestamps[j - 1];
        const durHours     = (endTime.getTime() - startTime.getTime()) / (1000 * 3600);

        let excluded = false;
        let exclusionReason: string | null = null;
        for (const mw of params.maintenance_windows) {
          if (startTime >= mw.start && startTime <= mw.end) {
            excluded = true;
            const s = mw.start.toISOString().slice(0, 10);
            const e = mw.end.toISOString().slice(0, 10);
            exclusionReason = `${mw.reason} (${s} to ${e})`;
            break;
          }
        }

        events.push({
          station_id:            stationId,
          sensor_type:           'pressure',
          start_time:            startTime.toISOString(),
          duration_hours:        Math.round(durHours * 100) / 100,
          displacement_estimate: Math.round(displacement * 10000) / 10000,
          confidence_score:      Math.round(confidence * 10000) / 10000,
          excluded,
          exclusion_reason:      exclusionReason,
        });
        i = j;
        continue;
      }
    }
    i++;
  }
  return events;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const program = new Command();
  program
    .option('--db <path>',      'SQLite database path',    '/app/data/sensors.db')
    .option('--dossier <path>', 'Operations dossier path', '/app/docs/seismology_ops_dossier.md')
    .option('--output <path>',  'Output JSON path',        '/app/output/events.json')
    .parse(process.argv);

  const opts = program.opts<{ db: string; dossier: string; output: string }>();

  const db = openDatabase(opts.db);
  const dossierText = fs.readFileSync(opts.dossier, 'utf-8');

  logger.info('Parsing dossier for calibration parameters...');
  const calibrations = parseDossier(dossierText);
  logger.info(`Extracted calibration for ${calibrations.size} stations`);

  const stationIds = getStationIds(db);
  const allEvents: DetectedEvent[] = [];

  for (const sid of stationIds) {
    const params = calibrations.get(sid);
    if (!params) { logger.warn(`No calibration for ${sid}, skipping`); continue; }

    const rows = getReadings(db, sid, 'pressure');
    if (rows.length === 0) continue;

    const timestamps = rows.map(r => new Date(r.timestamp));
    const calibrated = applyCalibration(
      rows.map(r => r.raw_value),
      params.pressure_gain,
      params.pressure_offset,
    );

    logger.info(`${sid}: ${rows.length} pressure readings`);
    const detected = detectEvents(sid, timestamps, calibrated, params);
    if (detected.length === 0) continue;
    const primary = detected.reduce((best, cur) =>
      cur.confidence_score > best.confidence_score ||
      (cur.confidence_score === best.confidence_score && cur.duration_hours > best.duration_hours)
        ? cur
        : best,
    );
    allEvents.push(primary);
  }

  db.close();

  const excluded = allEvents.filter(e => e.excluded).length;
  const catalog: EventCatalog = {
    generated_at:    new Date().toISOString(),
    total_events:    allEvents.length,
    excluded_events: excluded,
    events:          allEvents,
  };

  const outDir = path.dirname(opts.output);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(opts.output, JSON.stringify(catalog, null, 2));
  logger.info(`Wrote ${allEvents.length} events (${excluded} excluded) to ${opts.output}`);
}

main().catch(err => {
  process.stderr.write(`Fatal: ${err}\n${err.stack ?? ''}\n`);
  process.exit(1);
});
TSEOF

npm run build

mkdir -p /app/output
node dist/src/index.js \
  --db /app/data/sensors.db \
  --dossier /app/docs/seismology_ops_dossier.md \
  --output /app/output/events.json
