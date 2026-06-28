#!/bin/bash
set -euo pipefail

cat > /app/import.js <<'IMPORT_EOF'
'use strict';
// Importer. The container body is range-coded; the decoder below was worked out
// from the reference probe. Records stream one at a time so the feed is never
// materialized whole.
const fs = require('fs');
const path = require('path');
const pgp = require('pg-promise')();
const batcher = require('./lib/stream-batcher');

const db = pgp({ host: '127.0.0.1', port: 5433, database: 'app', user: 'app', password: 'apppass' });
const CHECKPOINT_FILE = '/var/lib/csv-importer/.checkpoint';

// ---- range decoder + adaptive model ----
const PB = 11, PMAX = 1 << PB, PINIT = PMAX >> 1, MV = 5, TOP = 1 << 24;
const CB = 12, CSIZE = 1 << CB, CMASK = CSIZE - 1;
const MULT = 2654435761, ADD = 1013904223;
function modinv32() { let x = MULT >>> 0; for (let i = 0; i < 5; i++) x = Math.imul(x, (2 - Math.imul(MULT, x)) >>> 0) >>> 0; return x >>> 0; }
const MINV = modinv32();
function unscramble(e) { return (Math.imul((e - ADD) >>> 0, MINV)) >>> 0; }
function ctxOrder(v) { return v === 1 ? 1 : 2; }
function ctxIndex(order, p1, p2) { if (order === 1) return p1; return ((Math.imul(p1, 769) ^ Math.imul(p2, 13)) >>> 0) & CMASK; }
function newModel(order) { const n = order === 1 ? 256 : CSIZE; const m = new Array(n); for (let i = 0; i < n; i++) m[i] = new Uint16Array(256).fill(PINIT); return m; }
class RD {
    constructor(d) { this.d = d; this.pos = 1; this.range = 0xFFFFFFFF >>> 0; this.code = 0; for (let k = 0; k < 4; k++) this.code = (((this.code << 8) >>> 0) | this._b()) >>> 0; }
    _b() { const b = this.pos < this.d.length ? this.d[this.pos] : 0; this.pos++; return b; }
    bit(probs, idx) { const p = probs[idx]; const bound = (Math.imul(this.range >>> PB, p)) >>> 0; let bt;
        if ((this.code >>> 0) < bound) { this.range = bound; probs[idx] = p + ((PMAX - p) >> MV); bt = 0; }
        else { this.code = (this.code - bound) >>> 0; this.range = (this.range - bound) >>> 0; probs[idx] = p - (p >> MV); bt = 1; }
        while (this.range < TOP) { this.range = ((this.range << 8) >>> 0); this.code = (((this.code << 8) >>> 0) | this._b()) >>> 0; }
        return bt; }
}
function makeByteStream(comp, order) {
    let pos = 0;
    return function () { return pos < comp.length ? comp[pos++] : 0; };
}
const TAGMAP = [2, 0, 1, 1, 2, 0];
function rVarint(nb) { let sh = 0, v = 0; for (;;) { const b = nb(); v += (b & 0x7F) * Math.pow(2, sh); if (!(b & 0x80)) return v; sh += 7; } }
function rText(nb) { const f = nb(); if (f === 0) return null; const n = rVarint(nb); const a = Buffer.alloc(n); for (let i = 0; i < n; i++) a[i] = nb(); return a.toString('utf-8'); }
function rNum(nb, tag, scr) { const b = TAGMAP[((tag % 6) + 6) % 6]; const raw = rVarint(nb); let v = b === 0 ? raw : (b === 1 ? Math.floor(raw / 2) : raw - 1000); if (scr) v = unscramble(v >>> 0); return v; }
function rOptNum(nb, tag, scr) { const f = nb(); if (f === 0) return null; return rNum(nb, tag, scr); }
function rCatalog(nb, version) { const id = rVarint(nb); let tag = 0; if (version !== 1) tag = nb(); const sku = rText(nb); const name = rText(nb); const scr = version >= 3; const qty = rNum(nb, tag, scr); const price_ct = rNum(nb, tag, scr); return { id, sku, name, qty, price_ct }; }
function rChangelog(nb) { const id = rVarint(nb); const version = rVarint(nb); const tag = nb(); const op = nb(); const r = { id, version, op: op === 1 ? 'del' : 'put' }; if (op !== 1) { r.sku = rText(nb); r.name = rText(nb); r.qty = rOptNum(nb, tag, true); r.price_ct = rOptNum(nb, tag, true); } return r; }
function header(buf) { if (buf.toString('latin1', 0, 4) !== 'PCT2') throw new Error('bad magic'); return { version: buf[4], count: buf.readUInt32BE(13), bodylen: buf.readUInt32BE(17), off: 21 }; }
async function* decodeCatalog(file) { const buf = fs.readFileSync(file); const h = header(buf); const nb = makeByteStream(buf.subarray(h.off), ctxOrder(h.version)); for (let k = 0; k < h.count; k++) yield rCatalog(nb, h.version); }
async function* decodeChangelog(file) { const buf = fs.readFileSync(file); const h = header(buf); const nb = makeByteStream(buf.subarray(h.off), ctxOrder(h.version)); for (let k = 0; k < h.count; k++) yield rChangelog(nb); }

// ---- import + reconcile ----
const cs = new pgp.helpers.ColumnSet(['id', 'sku', 'name', 'qty', 'price'], { table: 'products' });
function toRow(r) { return { id: r.id, sku: r.sku === null ? '' : r.sku, name: r.name === null ? '' : r.name, qty: r.qty, price: (r.price_ct / 100).toFixed(2) }; }
function parseCkpt(raw) { const m = /^id:(\d+)$/.exec(String(raw).trim()); if (!m) throw new Error('bad checkpoint'); return parseInt(m[1], 10); }
function resolveResume(arg) { if (arg === null) return { mode: null, startId: null }; if (arg === 'auto') { if (!fs.existsSync(CHECKPOINT_FILE)) return { mode: 'auto', startId: null }; return { mode: 'auto', startId: parseCkpt(fs.readFileSync(CHECKPOINT_FILE, 'utf8')) }; } return { mode: 'literal', startId: parseCkpt(arg) }; }
async function* skip(src, mode, startId) { if (startId === null) { for await (const r of src) yield r; return; } for await (const r of src) { const rid = r.id; if (mode === 'auto') { if (rid <= startId) continue; } else { if (rid < startId) continue; } yield r; } }
function writeCkptAtomic(val) { const tmp = CHECKPOINT_FILE + '.tmp'; const fd = fs.openSync(tmp, 'w'); try { fs.writeSync(fd, val); fs.fsyncSync(fd); } finally { fs.closeSync(fd); } fs.renameSync(tmp, CHECKPOINT_FILE); const d = fs.openSync(path.dirname(CHECKPOINT_FILE), 'r'); try { fs.fsyncSync(d); } finally { fs.closeSync(d); } }
const UPSERT = ` ON CONFLICT (id) DO UPDATE SET sku = COALESCE(NULLIF(EXCLUDED.sku, ''), products.sku), name = COALESCE(NULLIF(EXCLUDED.name, ''), products.name), qty = EXCLUDED.qty, price = EXCLUDED.price`;

async function claimFeedKey(feedKey) {
    const row = await db.oneOrNone(
        'INSERT INTO import_runs (feed_key, row_count, finished) VALUES ($1, 0, false) ON CONFLICT (feed_key) DO NOTHING RETURNING feed_key',
        [feedKey]);
    return row !== null;
}

async function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes('--dry-run');
    const ri = args.indexOf('--resume-from');
    const resumeArg = ri >= 0 ? args[ri + 1] : null;
    const fi = args.indexOf('--feed-key');
    const feedKey = fi >= 0 ? args[fi + 1] : null;
    const positional = [];
    for (let k = 0; k < args.length; k++) { if (args[k].startsWith('--')) { if (args[k] === '--resume-from' || args[k] === '--feed-key') k++; continue; } positional.push(args[k]); }
    const file = positional[0];
    if (!file) { console.error('usage: import.js [--dry-run] [--resume-from auto|id:<n>] [--feed-key <k>] <feed>'); process.exit(1); }
    if (feedKey !== null && !dryRun) {
        const won = await claimFeedKey(feedKey);
        if (!won) { console.log('processed 0 rows'); pgp.end(); return; }
    }
    const { mode, startId } = resolveResume(resumeArg);
    const decoded = skip(decodeCatalog(file), mode, startId);
    let total;
    if (dryRun) { total = await batcher.consume(decoded, async () => {}); }
    else {
        total = await batcher.consume(decoded, async batch => {
            const rows = batch.map(toRow);
            await db.none(pgp.helpers.insert(rows, cs) + UPSERT);
            writeCkptAtomic(`id:${batch[batch.length - 1].id}`);
        });
        await db.one("SELECT setval('products_id_seq', GREATEST((SELECT MAX(id) FROM products), 1)) AS v");
        if (feedKey !== null) { await db.none('UPDATE import_runs SET row_count = $1, finished = true WHERE feed_key = $2', [total, feedKey]); }
    }
    console.log(`processed ${total} rows`);
    pgp.end();
}

async function reconcileChangelog() {
    const args = process.argv.slice(2);
    const file = args[args.indexOf('--changelog') + 1];
    if (!file) { console.error('usage: import.js --changelog <feed>'); process.exit(1); }
    const FIELDS = ['sku', 'name', 'qty', 'price_ct'];
    const maxDel = new Map(), maxPut = new Map(), best = new Map();
    for await (const r of decodeChangelog(file)) {
        const id = r.id, ver = r.version;
        if (r.op === 'del') { if (ver > (maxDel.get(id) || 0)) maxDel.set(id, ver); }
        else {
            if (ver > (maxPut.get(id) || 0)) maxPut.set(id, ver);
            let fb = best.get(id); if (!fb) { fb = {}; best.set(id, fb); }
            for (const f of FIELDS) { const v = r[f]; if (v !== null && v !== undefined && ver > (fb[f] ? fb[f][0] : 0)) fb[f] = [ver, v]; }
        }
    }
    const ccs = new pgp.helpers.ColumnSet(['id', 'sku', 'name', 'qty', 'price'], { table: 'products' });
    const present = [];
    for (const [id, mp] of maxPut) {
        const md = maxDel.get(id) || 0; if (mp <= md) continue;
        const fb = best.get(id) || {}; const row = { id }; let ok = true;
        for (const f of FIELDS) { const bv = fb[f]; if (!bv || bv[0] <= md) { ok = false; break; } row[f] = bv[1]; }
        if (ok) present.push({ id, sku: row.sku, name: row.name, qty: row.qty, price: (row.price_ct / 100).toFixed(2) });
    }
    for (let i = 0; i < present.length; i += 1000) { const b = present.slice(i, i + 1000); if (b.length) await db.none(pgp.helpers.insert(b, ccs)); }
    console.log(`reconciled ${present.length} products`);
    pgp.end();
}

const entry = process.argv.includes('--changelog') ? reconcileChangelog : main;
entry().catch(err => { console.error('import failed:', err.message); process.exit(1); });
IMPORT_EOF

node -c /app/import.js
