export const PRIORITY = {
  node_id_invalid: 0,
  term_overflow: 1,
  log_index_gap: 2,
  duplicate_entry: 3,
  bad_encoding: 4,
  rpc_term_stale: 5,
  rpc_order_violation: 6,
  wal_frame_oversize: 7,
  wal_order_violation: 8,
  snapshot_conflict: 9,
  cluster_homoglyph: 10,
  partition_overlap: 11,
  config_quorum_invalid: 12,
  commit_regression: 13,
  env_conflict: 14,
  bad_binary_frame: 15,
  bundle_incomplete: 16,
  env_not_production: 17,
  clock_regression: 18,
  no_valid_commands: 19,
};

export class ParseIssue {
  constructor(code, message, line = 0) {
    this.code = code;
    this.message = message;
    this.line = line;
  }
}

export function chooseIssue(issues) {
  if (!issues.length) {
    return null;
  }
  return [...issues].sort((a, b) => {
    const pa = PRIORITY[a.code] ?? 99;
    const pb = PRIORITY[b.code] ?? 99;
    if (pa !== pb) {
      return pa - pb;
    }
    if (a.line !== b.line) {
      return a.line - b.line;
    }
    return a.message.localeCompare(b.message);
  })[0];
}
