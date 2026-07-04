import { normalizeNodeId } from './normalization.js';

export function validateRpcTrace(lines, walByTick) {
  const pairTerm = new Map();
  for (let i = 0; i < lines.length; i += 1) {
    const row = lines[i];
    const from = normalizeNodeId(row.from);
    const to = normalizeNodeId(row.to);
    if (!from.ok || !to.ok) {
      return { ok: false, code: 'node_id_invalid', message: 'rpc node id', line: i + 1 };
    }
    const term = Number(row.term);
    const tick = Number(row.tick);
    const walTerm = walByTick.get(tick);
    if (walTerm !== undefined && term < walTerm) {
      return { ok: false, code: 'rpc_term_stale', message: 'rpc term stale', line: i + 1 };
    }
    const key = `${from.value}->${to.value}`;
    const prev = pairTerm.get(key);
    if (prev !== undefined && term < prev) {
      return { ok: false, code: 'rpc_order_violation', message: 'rpc term regression', line: i + 1 };
    }
    pairTerm.set(key, term);
  }
  return { ok: true, rows: lines.length };
}
