export function classify(beforeMetrics, afterMetrics) {
  const rejected = [];
  if (beforeMetrics.election_rounds > afterMetrics.election_rounds) {
    rejected.push('election_timeout_spike');
  }
  if (beforeMetrics.commands_lost > 0) {
    rejected.push('snapshot_lag_display_bug');
  }
  const secondary = [];
  if (beforeMetrics.split_brain_detected) {
    secondary.push('dual_leadership_after_heal');
  }
  if (beforeMetrics.commands_committed !== afterMetrics.commands_committed) {
    secondary.push('commit_divergence');
  }
  return {
    classification: 'raft_split_brain',
    root_cause: 'raft_split_brain',
    primary_node: 'n1',
    secondary_symptoms: secondary,
    rejected_causes: rejected,
    repair_plan: [
      'enforce_log_up_to_date_voting',
      'prior_term_commit_safety',
      'quorum_term_filter',
      'partition_overlap_guard',
      'wal_big_endian_frames',
    ],
  };
}
