# Offline marking and synthetic ledger rows

A reflector is marked `offline_observed = true` for the run when, in
at least one cycle of the run, it had ZERO surviving real probes
(after dedup, canonicalization, and strict-int gating). The mark is a
metadata signal — it does not change any single probe's verdict — but
it has two downstream consequences:

1. The allocator tiebreak direction flips to descending (see
   `../allocator_pages/tiebreak_direction.md`).
2. The probe ledger gains one synthetic `REFLECTOR_OFFLINE` row per
   `(cycle, reflector)` pair that had zero probes.

## Synthetic REFLECTOR_OFFLINE rows

For every `(cycle, reflector)` pair where the reflector contributed
zero real probes in that cycle, the auditor emits ONE synthetic probe
ledger row:

| field          | value |
|----------------|-------|
| `probe_id`     | `"OFFLINE-<reflector_id>-<cycle_id>"` (e.g. `"OFFLINE-R10-2"`) |
| `session_id`   | `"-"` |
| `cycle_id`     | the cycle in which the reflector was missing |
| `reflector_id` | the reflector |
| `owd_us`       | `0` |
| `verdict`      | `REFLECTOR_OFFLINE` |

These synthetic rows ARE emitted in the probe ledger and DO contribute
to the `by_verdict["REFLECTOR_OFFLINE"]` count. They do NOT contribute
to allocator weight, anomaly_count, loss_count, jitter computations,
or any cycle row's probe_count.

## Per-cycle probe_count and contributors

A cycle row's `probe_count` is the count of REAL probes in that cycle
(synthetic OFFLINE rows excluded). The cycle's `contributors` array
is the set of `reflector_id` values that actually contributed at
least one real probe to that cycle, sorted by numeric suffix.
