import fs from 'node:fs';
import path from 'node:path';
import { APP_DIR } from './paths.js';

const INVISIBLE = /[\u200B-\u200D\uFEFF\u2060]/g;

export function loadEnvDir(bundlePath) {
  const envDir = path.join(bundlePath, 'env.d');
  const map = new Map();
  let filesMerged = 0;
  if (!fs.existsSync(envDir)) {
    return { map, filesMerged, issue: null };
  }
  const names = fs.readdirSync(envDir).filter((n) => n.endsWith('.env')).sort();
  for (const name of names) {
    filesMerged += 1;
    const text = fs.readFileSync(path.join(envDir, name), 'utf8');
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }
      const eq = trimmed.indexOf('=');
      if (eq <= 0) {
        continue;
      }
      const key = trimmed.slice(0, eq);
      const canon = key.normalize('NFKC').replace(INVISIBLE, '');
      if (map.has(canon) && map.get(canon).raw !== key) {
        return { map, filesMerged, issue: { code: 'env_conflict', message: `conflict on ${canon}` } };
      }
      map.set(canon, { raw: key, value: trimmed.slice(eq + 1) });
    }
  }
  return { map, filesMerged, issue: null };
}

export function ensureProduction(envMap) {
  const env = envMap.get('RAFT_ENV')?.value ?? '';
  if (env !== 'production') {
    return { ok: false, code: 'env_not_production', message: 'RAFT_ENV must be production' };
  }
  return { ok: true };
}

export function simulationSeed(envMap) {
  const raw = envMap.get('SIMULATION_SEED')?.value ?? '42';
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? 42 : parsed;
}

export function goldenPolicyPath() {
  return path.join(APP_DIR, 'config', 'cluster_policy.json');
}
