# Metrics report schema

Written to uncertainty-graph.dot sibling file metrics-report.json in the output directory.

| Field | Type | Meaning |
|-------|------|---------|
| bundle_id | string | From bundle root |
| stable | boolean | false when any unstable loop exists |
| stage_order | array of strings | Stage ids in pipeline.stages array order |
| stage_variances | object | Map stage id to propagated variance (6 decimal places in JSON) |
| unstable_loops | array | Each entry: nodes (array of stage ids in cycle order), gain (number) |

When stable is true, unstable_loops is an empty array.

Variance values are computed per /app/docs/validation-memo/cryogrid-thermal-review.md SECTION 37,
with frozen soil handling in SECTION 58.

DOT annotations per SECTION 72.

Loop detection per SECTION 91.
