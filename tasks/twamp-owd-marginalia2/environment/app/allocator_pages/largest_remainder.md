# Largest-remainder allocation

`summary.jitter_share_permille` distributes 1000 parts per thousand
across the registered reflectors. The unweighted input is the
per-reflector count of probes whose FINAL verdict is one of:

* `WITHIN_BOUNDS`
* `OWD_ANOMALY`
* `JITTER_FLAGGED`
* `QUIET_SUPPRESSED`

`LOSS_DETECTED`, `STALE_MEASUREMENT`, and `REFLECTOR_OFFLINE` rows
do NOT contribute to allocator weight. Synthetic OFFLINE rows do
not contribute either.

## Allocation procedure

For total weight T across all reflectors:

1. For each reflector R, compute `floor(count(R) * 1000 / T)`.
   That is reflector R's floor allocation.
2. Sum the floors. The remainder `leftover = 1000 - sum_floors` is
   distributed one unit at a time.
3. Sort reflectors by descending fractional remainder
   (`count(R)*1000 - floor(R)*T`). Hand out one leftover unit to the
   reflector at the head of the sorted list, then continue down
   until the leftover is exhausted.

A reflector with zero qualifying probes receives 0 — that row is
still emitted in the report (with all zero counts and
`offline_observed = true` if no real probes appeared in any cycle).

## Tiebreak

When two reflectors have the EQUAL fractional remainder, the
allocator falls through to a tiebreak. The direction of that
tiebreak is conditional on whether ANY reflector was observed
offline this run. See `tiebreak_direction.md`.

## Edge cases

* Total weight T == 0: every reflector receives 0, and the sum is
  0 (not 1000). This is the only run where the sum is allowed to
  be anything other than 1000.
* T > 0: the sum MUST be exactly 1000. A correct implementation
  produces this by construction.
