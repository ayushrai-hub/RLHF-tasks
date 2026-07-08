# Operator contract

The simulator is operated with:

```text
authzctl run-case --case <scenario.json> --state <state-dir> --out <trace.json> [--resume] [--stop-after-step N]
```

`make build` must create `/app/environment/bin/authzctl`. `run-case` reads the scenario, executes every step in order, persists cache/index state and a run manifest under the supplied state directory, and writes one JSON authorization trace to the supplied output path. The state directory is intentionally separate from the output trace so restart/replay and regeneration behavior can be tested by deleting the trace and re-running the same source pipeline.

With `--resume`, the command continues from `run_manifest.json` and the persisted cache surfaces when the manifest's `case_digest` matches the scenario file. A resumed run records only the steps it executes in the trace, but the final cache entries, group index, and on-disk state must match a single uninterrupted run of the same scenario. `--stop-after-step` executes through the numbered step and persists state without requiring a separate scenario file.

Each scenario step has an integer `tick`. The program uses scenario ticks only; it must not use wall-clock time. The public workflow is directory publish, cache refresh, and authorization. A refresh is authoritative only when the active directory snapshot has a proof whose `revision` equals the snapshot `revision` and whose `issued_at` is no more than `freshness_bound` ticks behind the refresh tick. Authorization re-checks proof age at the authorize tick, not only at the last refresh tick.

A rejected refresh is recorded with `accepted: false` in the trace and `refresh_journal.jsonl`. It must not update cache entries from the rejected snapshot, but persisted `group_index.json` under the state directory must not retain username-keyed membership that would still grant authority from a prior accepted refresh. Resume and regeneration checks read those on-disk surfaces directly; leaving stale index rows after a rejected refresh is not a valid fail-closed outcome.

A valid repair updates the Go source that maintains cache entries, derived group index entries, authorization decisions, audit rows, persisted manifest/journal surfaces, and trace provenance. Purging the state directory or writing static output traces is not a valid implementation of the workflow.
