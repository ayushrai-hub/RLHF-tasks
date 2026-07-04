const INVISIBLE = /[\u200B-\u200D\uFEFF\u2060]/g;
const KEY_RE = /^[a-zA-Z0-9_.-]{1,64}$/;
const NODE_RE = /^[a-z0-9-]{1,32}$/;

export function normalizeKey(raw) {
  if (raw === undefined || raw === null) {
    return { ok: false, code: 'node_id_invalid', message: 'missing key' };
  }
  const text = String(raw).normalize('NFKC').replace(INVISIBLE, '').trim();
  if (!KEY_RE.test(text)) {
    return { ok: false, code: 'node_id_invalid', message: `invalid key ${text}` };
  }
  return { ok: true, value: text };
}

export function normalizeNodeId(raw) {
  if (raw === undefined || raw === null) {
    return { ok: false, code: 'node_id_invalid', message: 'missing node_id' };
  }
  const text = String(raw).normalize('NFKC').replace(INVISIBLE, '').trim().toLowerCase();
  if (!NODE_RE.test(text)) {
    return { ok: false, code: 'node_id_invalid', message: `invalid node_id ${text}` };
  }
  return { ok: true, value: text };
}

export function canonicalCommand(entry) {
  return JSON.stringify([
    entry.index,
    entry.term,
    entry.tick,
    entry.nodeId,
    entry.command.op,
    entry.command.key,
    entry.command.value ?? '',
  ]);
}
