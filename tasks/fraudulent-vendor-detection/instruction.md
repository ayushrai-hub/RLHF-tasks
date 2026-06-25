# Fraudulent vendor detection

Finance suspects coordinated invoice fraud across the vendor master. Per-invoice approval queues stay green, three-way match rates look normal, and aggregate spend dashboards remain flat — yet accounts-payable analysts see unexplained phantom spend when they reconcile **vendor_graph** attribution against **line_item** attribution after enabling multi-stage invoice routing.

A Go accounts-payable attribution simulator writes `/app/output/vendor_audit.json`. Per-vendor spend caps look enforced under **line_item** view, but **vendor_graph** runs on the same seed, panel, stage geometry, and flags sometimes bind invoice rows whose cumulative `weight_pts` exceed the vendor cap. **line_item** stays within cap while **vendor_graph** reports positive phantom spend totals and mismatched invoice rows.

Fix the Go sources under `/app/environment` (required — not output-only) so the normal pipeline regenerates the vendor audit. Rebuild via `/app/environment/tools/runner.sh` after source edits. Hand-written JSON is insufficient—the verifier deletes prior output and reruns the runner.

Invoice rows in `lines` must keep the short keys `period` and `stage`. Period snapshots in `ticks` use `period_index`. Do not rename invoice-row keys to `period_index` or `stage_index` when editing report emission.

```bash
bash /app/environment/tools/runner.sh /app/environment/profiles/burst.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/steady.json /app/output/vendor_audit.json
```

## Requirements

The verifier reruns the runner against every bundled profile in `/app/environment/docs/operations.md`. With the same config and seed, **line_item** and **vendor_graph** must agree on every invoice row, all period snapshots, and every summary tally documented in `/app/environment/docs/report_schema.md`. On a correct run, phantom tallies are zero. Rejected rows use bind slot `-1` with no over-cap weight on the row (see `/app/environment/docs/report_schema.md`).

North-panel period-zero triple behavior, burst rejection sets, stage-width filtering, warm checkpoints, period failover, related-vendor rails, and view-mode rules are documented in `/app/environment/docs/fixture_layout.md` and `/app/environment/docs/report_schema.md`.

The divergence appears only on profiles that combine multi-stage geometry with **vendor_graph** period scheduling and deferred rollout flags.

A **line_item** smoke on `steady.json` can look healthy while **vendor_graph** burst still shows phantom spend. Fixing only the visibility path is not enough: mid-run **period_failover** restore/replay and warm-checkpoint continuation must reproduce the same audit as one uninterrupted **vendor_graph** run (same invoice rows, period snapshots, and summary tallies). When restore trims staged rows or resumes replay from the wrong period cursor, fingerprints drift even if per-invoice caps look enforced on the latest period. Failover counter semantics for the bundled `period_failover.json` profile are documented in `/app/environment/docs/fixture_layout.md` and `/app/environment/docs/report_schema.md`.

Do not change the verifier. The harness runs `python3 -m pytest` and writes `/logs/verifier/ctrf.json`.
