# Pipeline order

The orchestrator in `cmd/auditor/main.go` runs these stages strictly
in order. Any reorder silently produces wrong but plausible output.

1. **load** — read `/app/data/{config.json, reflectors.json,
   probes_shard_a.ndjson, probes_shard_b.ndjson, markers.ndjson}`.
   Strict-int gating is applied here; a row that fails is silently
   discarded.
2. **canonicalize** — for every probe, route the raw `send_ts` by
   magnitude to microseconds. See `../probe_intake/canonicalize.txt`.
3. **validity** — drop probes whose canonicalized `send_ts_us` falls
   outside the validity window. See
   `../owd_fieldbook/window_boundaries.md`.
4. **dedup** — when the same `probe_id` appears in both shards, the
   EARLIEST `send_ts_us` survivor is authoritative. Ties on
   `send_ts_us` are broken by ascending `reflector_id` (lex). Loser
   is silently discarded.
5. **classify** — assign tentative verdict from the canonical OWD,
   the staleness ceiling, and the loss flag. See
   `../verdict_ladder/verdict_assignment.md` for the step ordering.
6. **cascade** — walk cycles in ascending `cycle_id` order and
   reclassify probes against the cycle's effective threshold. See
   `../cycle_journal/cascade_walk.md`.
7. **markers** — apply valid `quiet_period` markers, muting EXACTLY
   ONE OWD_ANOMALY per `(cycle, reflector)` scope. See
   `../cycle_journal/quiet_period_oneshot.md`.
8. **jitter** — upgrade WITHIN_BOUNDS probes whose absolute cycle
   jitter strictly exceeds the configured ceiling.
9. **synthetic offline** — append one `REFLECTOR_OFFLINE` row per
   `(cycle, reflector)` pair with zero real probes. See
   `../reflector_atlas/offline_marking.md`.
10. **aggregate** — group probes by cycle and by reflector; compute
    counts.
11. **allocate** — distribute `jitter_share_permille` across
    reflectors with largest-remainder allocation. See
    `../allocator_pages/largest_remainder.md`.
12. **digest** — compute the self-binding `report_digest` over the
    final canonical bytes. See `../digest_workshop/canonical_bytes.md`.
13. **emit** — clear `/app/output` of all entries (files AND
    subdirectories), write `/app/output/report.json` with pinned key
    order and a single trailing newline. See `output_exclusivity.md`.

## Coupling notes

* Classify depends on canonicalize (uses canonical send_ts_us).
* Cascade depends on classify (uses initial verdicts).
* Markers depend on cascade (mute fires on post-cascade
  OWD_ANOMALY).
* Jitter depends on markers (only post-mute WITHIN_BOUNDS are
  candidates).
* Synthetic offline depends on all preceding stages.
* Allocate depends on the FINAL verdicts.
* Digest depends on FINAL ordered ledger and FINAL shares.
* Emit depends on the complete report.

The classify→cascade→markers→jitter chain is the easiest place to
get a partial fix that produces a partially-correct report.
