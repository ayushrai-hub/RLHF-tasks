import { normalizeNodeId } from './normalization.js';

export function loadPartitions(lines) {
  const events = [];
  const active = new Set();
  for (let i = 0; i < lines.length; i += 1) {
    const row = lines[i];
    const tick = Number(row.tick);
    if (row.kind === 'partition') {
      const isolated = (row.isolated ?? []).map((n) => normalizeNodeId(n));
      const majority = (row.majority ?? []).map((n) => normalizeNodeId(n));
      for (const n of [...isolated, ...majority]) {
        if (!n.ok) {
          return { ok: false, code: n.code, message: n.message, line: i + 1 };
        }
      }
      const isoSet = isolated.map((n) => n.value).sort();
      for (const node of isoSet) {
        if (active.has(node)) {
          return { ok: false, code: 'partition_overlap', message: `overlap on ${node}`, line: i + 1 };
        }
        active.add(node);
      }
      events.push({ tick, kind: 'partition', isolated: isoSet, majority: majority.map((n) => n.value).sort() });
    } else if (row.kind === 'heal') {
      active.clear();
      events.push({ tick, kind: 'heal' });
    }
  }
  return { ok: true, events };
}

export function majorityAt(events, tick) {
  let majority = null;
  for (const event of events) {
    if (event.tick > tick) {
      break;
    }
    if (event.kind === 'partition') {
      majority = new Set(event.majority);
    } else {
      majority = null;
    }
  }
  return majority;
}

export function isIsolated(events, tick, nodeId) {
  for (const event of events) {
    if (event.tick > tick) {
      break;
    }
    if (event.kind === 'partition' && event.isolated.includes(nodeId)) {
      return true;
    }
    if (event.kind === 'heal') {
      return false;
    }
  }
  return false;
}
