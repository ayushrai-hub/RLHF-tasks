import crypto from 'node:crypto';
import { buildInvariants } from './safety.js';

export function linearizabilityDigest(commands, applied) {
  const seen = new Set();
  const payload = [];
  for (const c of commands) {
    const row = [c.index, c.term, c.nodeId, c.command.key, c.command.value];
    const key = JSON.stringify(row);
    if (!seen.has(key)) {
      seen.add(key);
      payload.push(row);
    }
  }
  payload.sort((a, b) => (
    String(a[3]).localeCompare(String(b[3]))
    || Number(a[0]) - Number(b[0])
    || Number(a[1]) - Number(b[1])
    || String(a[2]).localeCompare(String(b[2]))
    || String(a[4]).localeCompare(String(b[4]))
  ));
  const state = [...applied.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  return crypto.createHash('sha256').update(JSON.stringify({ payload, state })).digest('hex');
}

export function buildTermTimeline(beforeTimeline, afterTimeline) {
  const rows = [];
  for (const row of beforeTimeline) {
    rows.push({ ...row, phase: 'before' });
  }
  for (const row of afterTimeline) {
    rows.push({ ...row, phase: 'after' });
  }
  rows.sort((a, b) => {
    const phase = a.phase.localeCompare(b.phase);
    if (phase !== 0) {
      return phase;
    }
    const node = a.node_id.localeCompare(b.node_id);
    if (node !== 0) {
      return node;
    }
    return a.start_tick - b.start_tick;
  });
  return rows;
}

export function buildCommandTrace(commands, applied) {
  const byKey = new Map();
  for (const cmd of commands) {
    if (!applied.has(cmd.command.key)) {
      continue;
    }
    const value = applied.get(cmd.command.key);
    byKey.set(cmd.command.key, {
      key: cmd.command.key,
      index: cmd.index,
      term: cmd.term,
      value,
      stages: ['append', 'apply', 'election', 'quorum'].sort(),
    });
  }
  return [...byKey.values()].sort((a, b) => a.key.localeCompare(b.key));
}

export function buildSafetyCertificate(metrics, digest, seed) {
  return {
    schema_version: 4,
    split_brain_detected: metrics.split_brain_detected,
    commit_index_aligned: metrics.commit_index_max >= metrics.commands_committed,
    linearizability_digest: digest,
    simulation_seed: seed,
    invariants: buildInvariants(metrics),
  };
}

export function snapshotMetrics(metrics) {
  return {
    leaders_observed: metrics.leaders_observed,
    split_brain_detected: metrics.split_brain_detected,
    commands_committed: metrics.commands_committed,
    commands_lost: metrics.commands_lost,
    election_rounds: metrics.election_rounds,
    commit_index_max: metrics.commit_index_max,
    linearizable_keys: metrics.linearizable_keys,
  };
}
