import { normalizeNodeId } from './normalization.js';

export function loadCluster(raw) {
  const nodes = [];
  for (const item of raw.nodes ?? []) {
    const norm = normalizeNodeId(item);
    if (!norm.ok) {
      return { ok: false, code: norm.code, message: norm.message };
    }
    nodes.push(norm.value);
  }
  nodes.sort((a, b) => a.localeCompare(b));
  const quorum = Number(raw.quorum_size);
  const minQ = Math.floor(nodes.length / 2) + 1;
  if (!Number.isInteger(quorum) || quorum < minQ || quorum > nodes.length) {
    return { ok: false, code: 'config_quorum_invalid', message: 'invalid quorum_size' };
  }
  return {
    ok: true,
    nodes,
    quorumSize: quorum,
    electionTimeoutMs: Number(raw.election_timeout_ms ?? 150),
  };
}
