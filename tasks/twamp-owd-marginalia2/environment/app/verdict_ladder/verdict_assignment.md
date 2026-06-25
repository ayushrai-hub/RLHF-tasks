# Per-probe verdict assignment

The auditor assigns a final verdict to every surviving probe in the
following order. Each step short-circuits: a probe whose verdict is
set at step N is not re-evaluated at step N+1.

## Step 1 — terminal status screens

A probe whose `recv_ts_us - send_ts_us` (with `send_ts_us` already
canonicalized) STRICTLY EXCEEDS the configured `stale_max_us` is
`STALE_MEASUREMENT`. The strict `>` matters: a probe exactly at the
ceiling is NOT stale. See `../owd_fieldbook/stale_ceiling.md`.

A probe whose `loss_flag` is the JSON boolean `true` is
`LOSS_DETECTED`. The loss verdict is checked AFTER the staleness
verdict: a probe that is both stale and loss-flagged is
`STALE_MEASUREMENT`.

## Step 2 — anomaly check

A probe whose canonical `owd_us` STRICTLY EXCEEDS the cycle's
effective threshold is `OWD_ANOMALY`. The strict `>` matters: a probe
exactly at the threshold is `WITHIN_BOUNDS`.

The "cycle's effective threshold" comes from the cross-cycle cascade
walk; it is NOT necessarily the default threshold from `config.json`.
See `../cycle_journal/cascade_walk.md`.

Otherwise the probe is provisionally `WITHIN_BOUNDS`.

## Step 3 — quiet-period suppression

A `quiet_period` marker whose seal reconciles and whose scoping
window covers a probe's send_ts mutes exactly ONE `OWD_ANOMALY` for
that `(cycle, reflector)` scope, in send-order. The muted probe's
verdict becomes `QUIET_SUPPRESSED`. See
`../cycle_journal/quiet_period_oneshot.md` for the boundary semantics
and the "exactly one" rule.

A `QUIET_SUPPRESSED` probe does NOT contribute to the cycle's
`anomaly_count` or to the reflector's `anomaly_count`. It DOES count
toward allocator weight.

## Step 4 — jitter upgrade

After the cascade and the marker mute have settled, the auditor
computes the per-cycle WITHIN_BOUNDS owd mean ONCE and upgrades any
WITHIN_BOUNDS probe whose absolute deviation strictly exceeds
`jitter_flag_us` to `JITTER_FLAGGED`. The mean is not recomputed
inside the upgrade pass. Only WITHIN_BOUNDS probes are subject to
jitter upgrade; OWD_ANOMALY / LOSS_DETECTED / QUIET_SUPPRESSED /
STALE_MEASUREMENT are not.

## Step 5 — synthetic offline

For every `(cycle, reflector)` pair with zero real surviving probes,
one synthetic `REFLECTOR_OFFLINE` row is appended to the probe
ledger. See `../reflector_atlas/offline_marking.md`.
