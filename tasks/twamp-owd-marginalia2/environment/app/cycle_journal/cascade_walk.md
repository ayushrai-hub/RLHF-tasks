# Cross-cycle cascade walk

The cascade walks cycles in ascending `cycle_id` order. Each cycle's
EFFECTIVE anomaly threshold derives from the IMMEDIATELY PRIOR
cycle's already-classified `loss_ratio`. The walk is naturally
single-pass: by the time the auditor processes cycle N, cycle N-1's
verdicts and loss_ratio are final.

## Loss ratio definition

For a cycle C with `probe_count(C)` real surviving probes:

    loss_ratio(C) = (LOSS_DETECTED(C) + OWD_ANOMALY(C)) / probe_count(C)

QUIET_SUPPRESSED probes do NOT contribute to `loss_ratio`. A muted
anomaly is treated as a non-anomaly for cascade accounting.

## Effective threshold

The default threshold comes from `config.json` field
`owd_anomaly_threshold_us`. The cascade rule:

    threshold[0]   = default
    for n = 1, 2, 3, ...:
        if loss_ratio(n-1) >= 0.02:
            threshold[n] = threshold[n-1] / 2     (integer division)
        else:
            threshold[n] = default

The key point: when cycle N-1 trips, the next halving is RELATIVE to
the prior EFFECTIVE threshold, not the default. Consecutive trips
compound:

* 1 consecutive trip: default, default/2
* 2 consecutive trips: default, default/2, default/4
* 3 consecutive trips: default, default/2, default/4, default/8
* 4 consecutive trips: default, default/2, default/4, default/8, default/16
* ...

There is no floor; the threshold halves as many times as consecutive
trips persist. A clean cycle (loss_ratio == 0.0) resets the next
cycle's threshold to the default.

## Coupling with downstream aggregation

The cascade module must update BOTH:

1. The per-probe verdicts (so the cycle row's `anomaly_count` and the
   probe-ledger row's `verdict` field agree with the cascade).
2. The per-cycle effective threshold map (so the cycle row's
   `threshold_owd_us` field reflects the cascade, not the default).

Updating verdicts but leaving the threshold map at the default for
non-zero cycles is a common partial fix that fails the threshold
test on cycles[].threshold_owd_us. Updating thresholds without
re-classifying is the opposite failure. The two updates must happen
together.

## Common misimplementation

Implementing `threshold[n] = default / 2` whenever the prior cycle
tripped gives the wrong ladder for consecutive trips. With default
800, two consecutive trips correctly produce 800, 400, 200; the
mistake produces 800, 400, 400. See `threshold_ladder.json` for the
data-form expected ladder, and `../digest_workshop/worked_example.md`
for the ladder's effect on the final digest.
