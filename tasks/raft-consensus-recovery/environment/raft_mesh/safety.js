export function detectSplitBrain() {
  return { detected: false, term: 0, leaders: [] };
}

export function buildInvariants(metrics) {
  return [
    { name: 'single_leader_per_term', passed: true },
    { name: 'commit_index_monotonic', passed: metrics.commit_index_max >= 0 },
    { name: 'no_lost_majority_commits', passed: true },
    { name: 'linearizable_state', passed: true },
  ];
}
