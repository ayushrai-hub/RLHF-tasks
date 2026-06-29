# Event bundles

- `events.jsonl` — primary supplier stream for the default reconcile run.
- `archive_lane_b.jsonl` — historical lane retained for audit comparisons only.

The CLI reads whichever path is passed to `--events`.
