import { normalizeNodeId } from './normalization.js';

export function loadCluster(raw) {
  const nodes = [];
  const seen = new Map();
  for (const item of raw.nodes ?? []) {
    const norm = normalizeNodeId(item);
    if (!norm.ok) {
      return { ok: false, code: norm.code, message: norm.message };
    }
    const canon = norm.value;
    const key = canon.normalize('NFKC').replace(/[\u200B-\u200D\uFEFF\u2060]/g, '').toLowerCase();
    if (seen.has(key)) {
      return { ok: false, code: 'cluster_homoglyph', message: `homoglyph node ${item}` };
    }
    seen.set(key, canon);
    nodes.push(canon);
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
