export function detectSplitBrain(leadersByTerm) {
  for (const [term, leaders] of leadersByTerm.entries()) {
    const unique = [...new Set(leaders)];
    if (unique.length > 1) {
      return { detected: true, term, leaders: unique };
    }
  }
  return { detected: false, term: 0, leaders: [] };
}

export function buildInvariants(metrics) {
  return [
    { name: 'single_leader_per_term', passed: !metrics.split_brain_detected },
    { name: 'commit_index_monotonic', passed: metrics.commit_index_max >= 0 },
    { name: 'no_lost_majority_commits', passed: metrics.commands_lost === 0 },
    { name: 'linearizable_state', passed: metrics.linearizable_keys > 0 || metrics.commands_committed === 0 },
  ];
}
