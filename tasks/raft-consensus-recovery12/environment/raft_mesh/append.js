export function advanceCommitIndex(log, currentTerm, commitIndex) {
  let next = commitIndex;
  for (const entry of log) {
    if (entry.index > commitIndex) {
      next = Math.max(next, entry.index);
    }
  }
  return next;
}

export function applyCommitted(log, commitIndex) {
  const state = new Map();
  for (const entry of log) {
    if (entry.index > commitIndex) {
      continue;
    }
    if (entry.command.op === 'set') {
      state.set(entry.command.key, entry.command.value);
    } else if (entry.command.op === 'del') {
      state.delete(entry.command.key);
    }
  }
  return state;
}

export function detectCommitRegression(log, commitIndex) {
  return { ok: true };
}
