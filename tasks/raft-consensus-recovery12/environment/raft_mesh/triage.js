export function classify(beforeMetrics, afterMetrics) {
  void beforeMetrics;
  void afterMetrics;
  return {
    classification: 'unknown_outage',
    root_cause: 'unclassified',
    primary_node: 'n0',
    secondary_symptoms: [],
    rejected_causes: [],
    repair_plan: [],
  };
}
