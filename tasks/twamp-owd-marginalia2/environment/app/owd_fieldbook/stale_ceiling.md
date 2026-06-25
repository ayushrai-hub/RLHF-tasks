# Staleness ceiling

A probe is `STALE_MEASUREMENT` iff its measured arrival latency
STRICTLY EXCEEDS the configured `stale_max_us`. The strict `>`
matters:

    is_stale = (recv_ts_us - send_ts_us) > stale_max_us

A probe whose arrival latency equals exactly `stale_max_us` is NOT
stale. A probe whose arrival latency is one microsecond above is
stale.

`send_ts_us` here is the CANONICALIZED value (microseconds after the
magnitude routing). Using the raw picosecond value or skipping the
routing would push every legacy-firmware probe into staleness
incorrectly.

## Contribution accounting

A `STALE_MEASUREMENT` probe:

* Appears in the probe ledger with its canonical `owd_us` value (the
  computed `recv - send - tx`, NOT zero).
* Does NOT contribute to allocator weight.
* Does NOT contribute to the cycle's `loss_count` (it is not a loss).
* Does NOT contribute to the cycle's `anomaly_count`.
* DOES contribute to the cycle's `probe_count` and the reflector's
  `probe_count` (it was a real probe; the staleness is a quality
  signal, not a structural exclusion).
* DOES count toward `summary.total_probes`.

## Common misimplementations

* Using `>=` in place of `>` — a probe exactly at the ceiling is
  wrongly flagged stale.
* Computing staleness on the raw send_ts (before canonicalization) —
  every picosecond-firmware probe is wrongly flagged stale because
  `recv - raw_send` is a giant negative number.
* Treating a stale probe as a loss for `loss_ratio` accounting —
  triggers a wrong cascade trip on the next cycle.
