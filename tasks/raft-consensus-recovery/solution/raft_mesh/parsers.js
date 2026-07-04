import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { ParseIssue, chooseIssue } from './errors.js';
import { normalizeKey, normalizeNodeId, canonicalCommand } from './normalization.js';
import { readFrames, validateFrameOrder } from './wal.js';
import { validateRpcTrace } from './rpc.js';
import { loadCluster } from './cluster.js';
import { loadPartitions } from './partition.js';
import { loadEnvDir, ensureProduction } from './envmerge.js';

import { gunzipSync, brotliDecompressSync } from 'node:zlib';

const MAX_TERM = 2147483647;
const REQUIRED = [
  'cluster.json',
  'wal_entries.jsonl',
  'wal_frames.bin',
  'rpc_trace.jsonl',
  'partition_events.jsonl',
  'election_timeouts.json',
  'snapshots.csv',
];

function decodeWrapped(parsed, lineNo) {
  if (!parsed.encoding || !parsed.payload) {
    return { ok: true, value: parsed };
  }
  try {
    let buf = Buffer.from(String(parsed.payload), 'base64');
    if (parsed.encoding === 'base64+gzip+json') {
      buf = gunzipSync(buf);
    } else if (parsed.encoding === 'base64+brotli+json') {
      buf = brotliDecompressSync(buf);
    } else if (parsed.encoding !== 'base64+json') {
      return { ok: false, code: 'bad_encoding', message: 'unknown encoding', line: lineNo };
    }
    return { ok: true, value: JSON.parse(buf.toString('utf8')) };
  } catch {
    return { ok: false, code: 'bad_encoding', message: 'failed to decode wrapped line', line: lineNo };
  }
}

function parseWalLines(text) {
  const issues = [];
  const commands = [];
  const seen = new Map();
  let duplicateSkipped = 0;
  let stripped = text;
  if (stripped.charCodeAt(0) === 0xfeff) {
    stripped = stripped.slice(1);
  }
  const lines = stripped.split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i].trim();
    if (!raw) {
      continue;
    }
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      issues.push(new ParseIssue('bad_encoding', 'invalid json', i + 1));
      continue;
    }
    const decoded = decodeWrapped(parsed, i + 1);
    if (!decoded.ok) {
      issues.push(new ParseIssue(decoded.code, decoded.message, decoded.line));
      continue;
    }
    parsed = decoded.value;
    const index = Number(parsed.index);
    const term = Number(parsed.term);
    const tick = Number(parsed.tick);
    if (!Number.isInteger(term) || term <= 0 || term > MAX_TERM) {
      issues.push(new ParseIssue('term_overflow', 'term out of range', i + 1));
      continue;
    }
    const nodeNorm = normalizeNodeId(parsed.node_id);
    if (!nodeNorm.ok) {
      issues.push(new ParseIssue(nodeNorm.code, nodeNorm.message, i + 1));
      continue;
    }
    const op = parsed.command?.op;
    const keyNorm = normalizeKey(parsed.command?.key);
    if (!keyNorm.ok || !['set', 'del'].includes(op)) {
      issues.push(new ParseIssue('node_id_invalid', 'invalid command', i + 1));
      continue;
    }
    const entry = {
      index,
      term,
      tick,
      nodeId: nodeNorm.value,
      command: { op, key: keyNorm.value, value: String(parsed.command?.value ?? '') },
    };
    const canon = canonicalCommand(entry);
    const dupKey = `${term}:${index}`;
    if (seen.has(dupKey)) {
      if (seen.get(dupKey) !== canon) {
        issues.push(new ParseIssue('duplicate_entry', 'conflicting duplicate', i + 1));
      } else {
        duplicateSkipped += 1;
      }
      continue;
    }
    seen.set(dupKey, canon);
    commands.push(entry);
  }
  if (commands.length) {
    const indexes = new Set(commands.map((entry) => entry.index));
    const maxIndex = Math.max(...indexes);
    for (let index = 1; index <= maxIndex; index += 1) {
      if (!indexes.has(index)) {
        issues.push(new ParseIssue('log_index_gap', 'index gap in WAL', 0));
        break;
      }
    }
  }
  if (!commands.length && !issues.length) {
    issues.push(new ParseIssue('no_valid_commands', 'empty wal', 0));
  }
  return { commands, issues, duplicateSkipped };
}

function loadSnapshots(bundlePath) {
  const text = fs.readFileSync(path.join(bundlePath, 'snapshots.csv'), 'utf8');
  const rows = text.trim().split('\n');
  const seen = new Map();
  for (let i = 1; i < rows.length; i += 1) {
    const [nodeRaw, indexRaw, termRaw, checksum] = rows[i].split(',');
    const node = normalizeNodeId(nodeRaw);
    if (!node.ok) {
      return { ok: false, code: node.code, message: node.message, line: i + 1 };
    }
    const key = `${node.value}:${indexRaw}`;
    const payload = `${termRaw}:${checksum}`;
    if (seen.has(key) && seen.get(key) !== payload) {
      return { ok: false, code: 'snapshot_conflict', message: 'snapshot conflict', line: i + 1 };
    }
    seen.set(key, payload);
  }
  return { ok: true, count: rows.length - 1 };
}

function loadJsonl(bundlePath, name) {
  const text = fs.readFileSync(path.join(bundlePath, name), 'utf8');
  return text
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

export function loadBundle(bundlePath) {
  const issues = [];
  for (const name of REQUIRED) {
    if (!fs.existsSync(path.join(bundlePath, name))) {
      issues.push(new ParseIssue('bundle_incomplete', `missing ${name}`, 0));
    }
  }
  if (issues.length) {
    return { issue: chooseIssue(issues) };
  }

  const envLoad = loadEnvDir(bundlePath);
  if (envLoad.issue) {
    return { issue: new ParseIssue(envLoad.issue.code, envLoad.issue.message) };
  }
  const prod = ensureProduction(envLoad.map);
  if (!prod.ok) {
    return { issue: new ParseIssue(prod.code, prod.message) };
  }

  const clusterRaw = JSON.parse(fs.readFileSync(path.join(bundlePath, 'cluster.json'), 'utf8'));
  const cluster = loadCluster(clusterRaw);
  if (!cluster.ok) {
    return { issue: new ParseIssue(cluster.code, cluster.message) };
  }

  const walText = fs.readFileSync(path.join(bundlePath, 'wal_entries.jsonl'), 'utf8');
  const wal = parseWalLines(walText);
  issues.push(...wal.issues);

  const frameBuf = fs.readFileSync(path.join(bundlePath, 'wal_frames.bin'));
  const frames = readFrames(frameBuf, { littleEndian: false });
  if (!frames.ok) {
    issues.push(new ParseIssue(frames.code, frames.message, frames.line ?? 0));
  } else {
    const order = validateFrameOrder(frames.frames);
    if (!order.ok) {
      issues.push(new ParseIssue(order.code, order.message, order.line ?? 0));
    }
  }

  const snapshots = loadSnapshots(bundlePath);
  if (!snapshots.ok) {
    issues.push(new ParseIssue(snapshots.code, snapshots.message, snapshots.line ?? 0));
  }

  const rpcLines = loadJsonl(bundlePath, 'rpc_trace.jsonl');
  const walByTick = new Map(wal.commands.map((c) => [c.tick, c.term]));
  const rpc = validateRpcTrace(rpcLines, walByTick);
  if (!rpc.ok) {
    issues.push(new ParseIssue(rpc.code, rpc.message, rpc.line ?? 0));
  }

  const partLines = loadJsonl(bundlePath, 'partition_events.jsonl');
  const partitions = loadPartitions(partLines);
  if (!partitions.ok) {
    issues.push(new ParseIssue(partitions.code, partitions.message, partitions.line ?? 0));
  }

  const issue = chooseIssue(issues);
  if (issue) {
    return { issue };
  }

  return {
    commands: wal.commands,
    partitions: partitions.events,
    rpcTrace: rpcLines,
    cluster,
    envMap: envLoad.map,
    envFilesMerged: envLoad.filesMerged,
    frameCount: frames.frames.length,
    snapshotCount: snapshots.count,
    duplicateCommands: wal.duplicateSkipped,
  };
}
