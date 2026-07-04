#!/usr/bin/env bash
set -euo pipefail

SRC=/app/task_file/src/Main.ts

cat > "$SRC" << 'TS'
import * as fs from "fs";
import * as path from "path";

const FNV_OFFSET = 0xcbf29ce484222325n;
const FNV_PRIME = 0x100000001b3n;
const MASK64 = (1n << 64n) - 1n;

function fnv1a(s: string): bigint {
  let h = FNV_OFFSET;
  const bytes = Buffer.from(s, "utf8");
  for (let i = 0; i < bytes.length; i++) {
    h ^= BigInt(bytes[i]);
    h = (h * FNV_PRIME) & MASK64;
  }
  return h;
}
function groupOf(id: string): number {
  return Number(fnv1a("group|" + id) % 8n);
}
function isForbidden(a: string, b: string): boolean {
  const [x, y] = a <= b ? [a, b] : [b, a];
  return fnv1a("incompat|" + x + "|" + y) % 1000n < 16n;
}

let rngState = 88172645463325252n;
function rnd(): number {
  rngState = (rngState * 6364136223846793005n + 1442695040888963407n) & MASK64;
  return Number((rngState >> 32n) & 0xffffffffn) / 4294967296.0;
}
function rndi(m: number): number {
  return Math.floor(rnd() * m) % m;
}

const argv = process.argv.slice(2);
const inDir = argv.length >= 2 ? argv[0] : "input_data";
const outDir = argv.length >= 2 ? argv[1] : "output_data";

const ids: string[] = [];
const d1: number[] = [];
const d2: number[] = [];
const sraw = fs.readFileSync(path.join(inDir, "segments.jsonl"), "utf8");
for (const line of sraw.split("\n")) {
  if (!line.trim()) continue;
  const o = JSON.parse(line);
  ids.push(o.segment_id);
  d1.push(o.cpu);
  d2.push(o.bitrate);
}
const n = ids.length;

const cfg = JSON.parse(fs.readFileSync(path.join(inDir, "node_config.json"), "utf8"));
const bids: string[] = [];
const cap1: number[] = [];
const cap2: number[] = [];
for (const nd of cfg.nodes) {
  bids.push(nd.node_id);
  cap1.push(nd.cpu_capacity);
  cap2.push(nd.bitrate_capacity);
}
const g = bids.length;

const gid: number[] = ids.map((x) => groupOf(x));
const forb: boolean[][] = Array.from({ length: n }, () => new Array(n).fill(false));
for (let i = 0; i < n; i++) {
  for (let j = i + 1; j < n; j++) {
    if (isForbidden(ids[i], ids[j])) {
      forb[i][j] = true;
      forb[j][i] = true;
    }
  }
}

function score(a: number[]): number {
  const l1 = new Array(g).fill(0);
  const l2 = new Array(g).fill(0);
  const memb: number[][] = Array.from({ length: g }, () => []);
  for (let i = 0; i < n; i++) {
    l1[a[i]] += d1[i];
    l2[a[i]] += d2[i];
    memb[a[i]].push(i);
  }
  for (let j = 0; j < g; j++) if (l1[j] > cap1[j] || l2[j] > cap2[j]) return -1.0;
  let okp = 0;
  let totp = 0;
  let viol = 0;
  for (let j = 0; j < g; j++) {
    const m = memb[j];
    const L = m.length;
    totp += (L * (L - 1)) / 2;
    for (let x = 0; x < L; x++)
      for (let y = x + 1; y < L; y++) {
        if (gid[m[x]] === gid[m[y]]) okp++;
        if (forb[m[x]][m[y]]) viol++;
      }
  }
  const gs = totp > 0 ? okp / totp : 1.0;
  let t1 = 0;
  let t2 = 0;
  let mx1 = l1[0];
  let mn1 = l1[0];
  let mx2 = l2[0];
  let mn2 = l2[0];
  for (let j = 0; j < g; j++) {
    t1 += l1[j];
    t2 += l2[j];
    if (l1[j] > mx1) mx1 = l1[j];
    if (l1[j] < mn1) mn1 = l1[j];
    if (l2[j] > mx2) mx2 = l2[j];
    if (l2[j] < mn2) mn2 = l2[j];
  }
  const b1 = t1 > 0 ? 1.0 - (mx1 - mn1) / t1 : 0.0;
  const b2 = t2 > 0 ? 1.0 - (mx2 - mn2) / t2 : 0.0;
  let base = 0.55 * gs + 0.25 * b1 + 0.2 * b2;
  if (viol > 0) {
    let f = 1.0;
    const k = Math.min(viol, 5);
    for (let t = 0; t < k; t++) f *= 0.55;
    base *= Math.max(f, 0.2);
  }
  return base;
}

const assign: number[] = new Array(n).fill(0);
const a1 = new Array(g).fill(0);
const a2 = new Array(g).fill(0);
const order = Array.from({ length: n }, (_, i) => i);
order.sort((x, y) => d1[y] + d2[y] - (d1[x] + d2[x]));
for (const idx of order) {
  const pref = gid[idx] % g;
  let chosen = pref;
  const cand = [pref];
  for (let j = 0; j < g; j++) if (j !== pref) cand.push(j);
  for (const c of cand) {
    if (a1[c] + d1[idx] <= cap1[c] && a2[c] + d2[idx] <= cap2[c]) {
      chosen = c;
      break;
    }
  }
  assign[idx] = chosen;
  a1[chosen] += d1[idx];
  a2[chosen] += d2[idx];
}

let cur = score(assign);
let best = assign.slice();
let bestsc = cur;
rngState = 0x9e3779b97f4a7c15n;
const iters = 600000;
let T = 0.04;
const cool = Math.pow(0.0006 / 0.04, 1.0 / iters);
for (let it = 0; it < iters; it++) {
  T *= cool;
  const i = rndi(n);
  const old = assign[i];
  const ng = rndi(g);
  if (ng === old) continue;
  if (a1[ng] + d1[i] > cap1[ng] || a2[ng] + d2[i] > cap2[ng]) continue;
  a1[old] -= d1[i];
  a2[old] -= d2[i];
  a1[ng] += d1[i];
  a2[ng] += d2[i];
  assign[i] = ng;
  const ns = score(assign);
  if (ns < 0) {
    a1[ng] -= d1[i];
    a2[ng] -= d2[i];
    a1[old] += d1[i];
    a2[old] += d2[i];
    assign[i] = old;
    continue;
  }
  if (ns >= cur || rnd() < Math.exp((ns - cur) / Math.max(T, 1e-6))) {
    cur = ns;
    if (ns > bestsc) {
      bestsc = ns;
      best = assign.slice();
    }
  } else {
    a1[ng] -= d1[i];
    a2[ng] -= d2[i];
    a1[old] += d1[i];
    a2[old] += d2[i];
    assign[i] = old;
  }
}

let out = "";
for (let i = 0; i < n; i++) {
  out += '{"segment_id": "' + ids[i] + '", "node_id": "' + bids[best[i]] + '"}\n';
}
fs.writeFileSync(path.join(outDir, "assignment.jsonl"), out);
process.stderr.write("oracle best " + bestsc + "\n");
TS

cd /app/task_file/src && npx tsc
node /app/task_file/src/Main.js "${INPUT_DIR:-/app/task_file/input_data}" "${OUTPUT_DIR:-/app/task_file/output_data}"
echo "Oracle complete."
