# Critical pins (truncation-proof short form)

The seven pins agents miss most often. Each is restated in detail
elsewhere; this file is the truncation-proof short form for shells
that drop the tail of long stdout.

1. **OWD = recv_ts_us - send_ts_us - tx_ts_us** (canonical), NOT
   `recv_minus_send`. The shortcut field on the probe row exists
   only for legacy dashboards and ignores reflector turnaround. See
   `../owd_fieldbook/formula.md`.

2. **send_ts magnitude routing**: raw `send_ts < 2e12` is
   microseconds (use as-is); raw `>= 2e12` is picoseconds (divide
   by 1e6 to get microseconds). Apply BEFORE any window check. See
   `../probe_intake/canonicalize.txt`.

3. **Strict-int gating**: `cycle_id`, `send_ts`, `recv_ts`, `tx_ts`,
   `seq_no` accept only bare integers or quoted integer strings. A
   floating-point fallback (`ParseFloat`, etc.) is INCORRECT and
   silently admits `42.0`, `42.5`, scientific notation. See
   `../probe_intake/strict_int_table.md`.

4. **Cascade COMPOUNDS** while consecutive cycles trip: cycle N+2's
   threshold is HALF of cycle N+1's effective threshold (one
   quarter of the default), when both N and N+1 had
   `loss_ratio >= 0.02`. A clean cycle resets to default. The
   coupling: the cascade module must update BOTH the per-probe
   verdicts AND the per-cycle effective threshold map. See
   `../cycle_journal/cascade_walk.md` and
   `../cycle_journal/threshold_ladder.json`.

5. **Quiet-period one-shot**: a valid `quiet_period` marker mutes
   EXACTLY ONE OWD_ANOMALY emission within its scope, not all of
   them. The marker scoping window is `(open, close]` —
   LEFT-EXCLUSIVE, RIGHT-INCLUSIVE — OPPOSITE the probe validity
   window. See `../cycle_journal/quiet_period_oneshot.md`.

6. **Allocator descending tiebreak**: the largest-remainder
   tiebreak uses ASCENDING numeric suffix when NO reflector was
   observed offline, and FLIPS to DESCENDING numeric suffix when
   ANY reflector was observed offline. An unconditional ascending
   tiebreak is incorrect on the alt fixture. See
   `../allocator_pages/tiebreak_direction.md`.

7. **Digest separator**: the bytes that feed the SHA-256 of
   `report_digest` join the probe ledger, the reflector ledger,
   and the summary tail with the LITERAL three-byte sequence
   `\n##\n`. Not `\n--\n`, not `\n==\n`, not blank line. See
   `../digest_workshop/canonical_bytes.md` and
   `../digest_workshop/worked_example.md`.

## Closed enum and output exclusivity

The `by_verdict` map contains ALL SEVEN verdict kinds, in lex
order, even at count zero — including `JITTER_FLAGGED` on small
fixtures where the count is zero. See
`../verdict_ladder/enum_set.md`.

`/app/output` must contain exactly `report.json` after every run —
no leftover files, no leftover subdirectories. See
`output_exclusivity.md`.
