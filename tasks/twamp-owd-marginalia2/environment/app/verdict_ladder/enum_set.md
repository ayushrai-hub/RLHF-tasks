# Closed verdict enum

The `by_verdict` map MUST contain ALL SEVEN verdict kinds, in lex
order, on every run, including kinds with count zero.

```
JITTER_FLAGGED        (often zero on small fixtures — STILL required)
LOSS_DETECTED
OWD_ANOMALY
QUIET_SUPPRESSED
REFLECTOR_OFFLINE
STALE_MEASUREMENT
WITHIN_BOUNDS
```

A run that omits a kind, even one whose count is zero, is
non-conforming. The emitter's `AllVerdicts` array must enumerate
EXACTLY these seven strings, in this exact order. Drop one and the
produced `by_verdict` is incomplete.

The alt fixture has zero `JITTER_FLAGGED` rows and zero
`STALE_MEASUREMENT` rows; both keys must still appear in its emitted
`by_verdict` map at value `0`.

## Cross-check invariants

* `sum(by_verdict.values()) == summary.total_probes`
* Every entry of the probe ledger maps to exactly one of the seven
  kinds; no kind is reserved or hidden.
* The order in which the emitter writes the seven keys is the lex
  order above. The map keys must appear in that order in the raw
  bytes of the report.

See `zero_emit_invariants.txt` for the common omission patterns and
the byte-level check the verifier uses.
