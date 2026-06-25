# Canonical one-way-delay formula

For a probe record the canonical one-way delay in microseconds is:

    owd_us = recv_ts_us - send_ts_us - tx_ts_us

where every term is in microseconds AFTER the magnitude routing of
`send_ts` has happened (see `../probe_intake/canonicalize.txt`).

The field labelled `recv_minus_send` on the probe row is a convenience
aggregate some upstream collectors record. It does NOT account for the
reflector turnaround `tx_ts` and is therefore NOT the policy key. The
auditor uses the canonical formula above, not the upstream-supplied
shortcut.

## Why the shortcut is wrong

For older reflectors the queue-tick was effectively zero and
`recv_minus_send` happened to match the canonical `recv_ts - send_ts -
tx_ts`. Two of the newer reflectors (per `../revision_notes.md`)
record non-trivial `tx_ts` values for queue-tick behavior. The
shortcut admits the queue-tick latency into the reported OWD and the
report disagrees with what the agent expects.

## Anomaly check

A surviving probe whose canonical `owd_us` STRICTLY EXCEEDS the
cycle's effective threshold is `OWD_ANOMALY`. The strict `>` matters:
a probe exactly at the threshold is `WITHIN_BOUNDS`. See
`../cycle_journal/cascade_walk.md` for how the per-cycle effective
threshold is derived.

## Jitter

After cascade and marker mute, the per-cycle WITHIN_BOUNDS owd_us
mean is computed ONCE (integer truncation), and any WITHIN_BOUNDS
probe whose absolute deviation strictly exceeds `jitter_flag_us` is
upgraded to `JITTER_FLAGGED`. The upgrade pass does NOT recompute the
mean.

Only WITHIN_BOUNDS probes are subject to jitter upgrade.
OWD_ANOMALY / LOSS_DETECTED / QUIET_SUPPRESSED / STALE_MEASUREMENT
probes are never upgraded.
