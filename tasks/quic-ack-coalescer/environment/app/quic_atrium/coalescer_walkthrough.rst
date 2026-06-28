# CRITICAL — Key contract (read first)

These seven rules cover the failure modes that surface most often. They
appear verbatim at the top of every spec doc so the agent never has to
scroll past a truncated paragraph to find them.

1. The output file is `/app/output/report.json`. Top-level keys appear in
   this order: `version`, `summary`, `by_conn`, `hamilton`, `events`,
   `report_digest`.

2. Closed verdict set of SEVEN: `ACK_DELIVERED`, `ACK_COALESCED`,
   `ACK_REORDERED`, `BUDGET_EXCEEDED`, `TYPE_INVALID`, `BAD_SPACE`,
   `RESET_VOID`. Every map carrying verdict counts holds ALL seven keys
   including zero counts.

3. Strict-int rejection covers SEVEN numeric fields: `ack_ts_ms`,
   `packet_number`, `largest_acked`, `ack_delay_us`, `ecn_ct0`, `ecn_ct1`,
   `ecn_ce`. A JSON float (e.g. `42.0`), a decimal string (e.g. `"42.5"`),
   a boolean, or null on ANY one of them flips the entire row to
   `TYPE_INVALID`. On rejection: every numeric is zeroed AND `ack_eliciting`
   is set to `false`; the string fields `conn_id` / `pn_space` / `shard_seq`
   are preserved verbatim. `ack_eliciting` itself requires a real JSON
   boolean — the integers `1` and `0` BOTH trip the same rejection.

4. Coalesce window `[0, coalesce_ms]` is RIGHT-INCLUSIVE. Reorder window
   `(coalesce_ms, reorder_ms]` is LEFT-EXCLUSIVE. The two windows share the
   boundary value at `coalesce_ms`; the coalesce window owns the boundary.
   An event whose delta is exactly `coalesce_ms` is `ACK_COALESCED`, NOT
   `ACK_REORDERED`. An event whose delta exceeds `reorder_ms` is
   `ACK_DELIVERED`. The `CRITICAL` tier multiplies the base coalesce_ms by
   `500/1000` (i.e. halves it from 200ms to 100ms). The `BULK` and
   `STANDARD` tiers retain the base value. The reorder window does NOT
   scale by tier in this edition.

5. Bucket anchor is the earliest `ack_ts_ms` row in the bucket. Ties resolve
   to the LARGER `packet_number`; then to the larger `shard_seq`. The
   anchor verdict is always `ACK_DELIVERED`. Picking the most-recent row,
   or breaking the tie by the SMALLER packet number, is wrong.

6. Hamilton remainder-tiebreak direction is `REVERSE` by DEFAULT, which
   orders connections by their numeric suffix DESCENDING (so `C11` before
   `C10` before `C9` before `C2`). The direction FLIPS to `FORWARD` (numeric
   suffix ASCENDING) when ANY registered connection carries `urgent=true`.
   `urgent` must be a real JSON boolean — the integer `1` does NOT flip
   direction. Floor allocation happens first; then the leftover (10000 minus
   floor sum) is distributed one basis point per conn picked by remainder
   DESCENDING, with the tier-determined direction breaking remainder ties.

7. `by_conn`, `hamilton`, and `events` ALL sort by numeric-suffix on
   `conn_id` (`C2` < `C10` < `C11`). Plain lexicographic order on conn ids
   places `C10` before `C2`, which is wrong. The `report_digest` is the
   lowercase hex `sha256` over the canonical bytes of the report with the
   `report_digest` field itself blanked to the empty string. The on-disk
   file ends in exactly one trailing newline AFTER the digest is computed.

---
# Examples

## Sample harness — per-row outcome map

The shipped sample fixture in `/app/quic_atrium/ack_workshop/coalescer_seed` carries seven
frames across three registered connections. Running `/app/bin/qack` against
the sample directory should byte-match `/app/quic_atrium/ack_workshop/golden_run.json`.
This is the cheapest way to validate the four most-missed behaviors locally
before running against the real fixture.

| shard_seq | conn | pn  | delta_ms | verdict        | what it tests                              |
|-----------|------|-----|----------|----------------|---------------------------------------------|
| 1         | S2   | 10  | 0        | ACK_DELIVERED  | bucket anchor                               |
| 2         | S2   | 11  | 200      | ACK_COALESCED  | coalesce boundary right-inclusive (200=200) |
| 3         | S2   | 12  | n/a      | TYPE_INVALID   | float ack_ts_ms (1717459201500.5) rejected  |
| 4         | S5   | 50  | 0        | ACK_DELIVERED  | bucket anchor (CRITICAL tier)               |
| 5         | S5   | 51  | 100      | ACK_COALESCED  | CRITICAL halved coalesce: 100=100 boundary  |
| 6         | S10  | 100 | 0        | ACK_DELIVERED  | bucket anchor (BULK tier)                   |
| 7         | S10  | 101 | 500      | ACK_REORDERED  | reorder boundary right-inclusive (500=500)  |

Sample Hamilton: each registered conn has 2 ACCEPTED rows, total weight 6.
Floor allocation is `floor(2*10000/6) = 3333` per conn, leftover `1`. All
three remainders tie at `2`. Direction is `REVERSE` (no urgent), so the
numeric-suffix DESCENDING tiebreak gives the `+1` to `S10` first:

  S2: 3333, S5: 3333, S10: 3334.

A `FORWARD`-default bug would instead award `+1` to `S2`, producing
`S2: 3334, S5: 3333, S10: 3333` — a clean byte-level discriminator.

## Worked smoking-gun — Hamilton direction

The same input scored under both directions:

```
weights:    {S2: 2, S5: 2, S10: 2}, total = 6
floor:      {S2: 3333, S5: 3333, S10: 3333}   sum = 9999, leftover = 1
remainders: {S2: 2,    S5: 2,    S10: 2}      (all tied at 2)
```

CORRECT (REVERSE — no urgent flag in fixture):
```
tiebreak order:  S10, S5, S2   (numeric-suffix DESCENDING)
+1 awarded to:   S10
final basis:     {S2: 3333, S5: 3333, S10: 3334}
```

WRONG (FORWARD-default bug):
```
tiebreak order:  S2, S5, S10   (numeric-suffix ASCENDING)
+1 awarded to:   S2
final basis:     {S2: 3334, S5: 3333, S10: 3333}
```

The byte diff lands on `basis_points` and on `report_digest`. The `summary.
hamilton_direction` field also flips from `REVERSE` to `FORWARD`. Three
fields move from one bug.

## Worked smoking-gun — coalesce boundary inclusivity

A non-anchor frame at delta exactly equal to `coalesce_ms`:

CORRECT (right-inclusive coalesce):
```
delta_ms = coalesce_ms = 200  → ACK_COALESCED
delta_ms = coalesce_ms + 1     → ACK_REORDERED
```

WRONG (right-exclusive coalesce — the obvious read):
```
delta_ms = coalesce_ms = 200  → ACK_REORDERED    (off-by-one)
delta_ms = coalesce_ms + 1     → ACK_REORDERED
```

The wrong reading inflates `ACK_REORDERED` and deflates `ACK_COALESCED` in
both `summary.by_verdict` and each affected `by_conn[i].by_verdict`. The
`events[i].verdict` for the boundary row flips too. Four-plus tests catch it.

## Worked smoking-gun — CRITICAL tier coalesce halving

A `CRITICAL` connection with `coalesce_us_base = 200` resolves to
`effective_coalesce_ms = 200 * 500 / 1000 = 100`. A non-anchor frame at
delta `100ms`:

CORRECT (CRITICAL halves, boundary right-inclusive):
```
effective_coalesce_ms = 100
delta_ms = 100   → ACK_COALESCED   (delta == boundary, right-inclusive)
delta_ms = 101   → ACK_REORDERED   (delta > 100)
```

WRONG (factor falls through to 1000 — agent forgot the per-tier map):
```
effective_coalesce_ms = 200  (CRITICAL not special-cased)
delta_ms = 100   → ACK_COALESCED   (still in window, but for the wrong reason)
delta_ms = 101   → ACK_COALESCED   (also wrong — should be REORDERED)
```

The wrong reading collapses the CRITICAL-tier `ACK_REORDERED` bucket to
zero, inflates the CRITICAL-tier `ACK_COALESCED` bucket, and shifts the
report digest.

## Window classification

Connection `C0` is `STANDARD` (coalesce_ms = 200, reorder_ms = 500). Frames
arrive at the following `ack_ts_ms` deltas relative to the bucket anchor:

| delta_ms | verdict        | reason                                  |
|----------|----------------|------------------------------------------|
| 0        | ACK_DELIVERED  | anchor row                               |
| 50       | ACK_COALESCED  | 50 in `[0, 200]`                         |
| 200      | ACK_COALESCED  | 200 IS the boundary; window is right-incl|
| 201      | ACK_REORDERED  | 201 in `(200, 500]`                      |
| 500      | ACK_REORDERED  | 500 IS the boundary; reorder is right-incl|
| 501      | ACK_DELIVERED  | beyond reorder window                    |

Connection `C0` flipped to `CRITICAL` would shrink the coalesce window to 100,
so a delta of 150 (which was COALESCED under STANDARD) becomes REORDERED.

## Anchor tiebreak

Two frames share the same `ack_ts_ms` inside the bucket:

| ack_ts_ms | packet_number | role            |
|-----------|---------------|-----------------|
| 1000      | 50            | non-anchor      |
| 1000      | 51            | anchor          |

The row with the LARGER packet_number wins the anchor — packet_number 50
becomes a non-anchor at delta 0 and is classified `ACK_COALESCED`.

## Cross-cycle cascade

`C7` has eight ACCEPTED frames on UTC day D. `budget_threshold` is `8`. On
day D+1, the earliest still-accepted event of `C7` (regardless of pn_space)
is rewritten to `BUDGET_EXCEEDED` and loses any anchor flag it had. Subsequent
day-D+1 events on `C7` keep the verdicts they already received from window
classification. The cascade fires once per breach.

## Type rejection

A row with `ack_ts_ms = 1717459207000.5` is `TYPE_INVALID` even though all
other fields look correct, because the floating point literal trips strict-int
rejection on `ack_ts_ms`. The same row's `conn_id`, `pn_space`, and `shard_seq`
remain visible in the report; the seven numerics and `ack_eliciting` are
zeroed.

A row with `ack_eliciting: 1` (integer) is `TYPE_INVALID`. The boolean check
requires the JSON literal `true` or `false`.

## Marker validation

A row in `markers.ndjson` is accepted only when its `source` equals
`control_plane`, its `kind` is in `marker_kinds`, and its `hmac8` matches the
prefix of `sha256("qack-marker-2026|RESET_RANGE|<conn>|<low>|<high>|<ts>")`.
Mismatch in any field drops the marker silently. The downstream pipeline
behaves as if the marker had never existed.

