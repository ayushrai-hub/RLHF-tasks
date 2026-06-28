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
# API Reference (critical rules summary)

This is the cheat sheet. It names the traps; it does NOT list every numeric
threshold. The detail lives across the other docs.

## Closed enums

* Verdicts: `ACK_DELIVERED`, `ACK_COALESCED`, `ACK_REORDERED`,
  `BUDGET_EXCEEDED`, `TYPE_INVALID`, `BAD_SPACE`, `RESET_VOID`. Every map
  carrying verdict counts MUST include every key.
* `pn_space`: `INITIAL`, `HANDSHAKE`, `APP_DATA`. Any other value routes to
  `BAD_SPACE`.
* `marker_kinds`: see `coalescer_anchor_set.json`. Any other value silently drops the
  marker.
* `tier`: `CRITICAL`, `STANDARD`, `BULK` after canonicalization through the
  synonym map.

## Strict-int rejection

Seven numeric fields require a JSON integer literal or a quoted-integer
string. Floats, decimal strings, booleans, and null are rejected for ALL
seven, and rejection ZEROES every numeric on the row plus zeros
`ack_eliciting`. String fields are preserved.

## Real-bool `ack_eliciting`

`ack_eliciting` must be a real JSON boolean. The integers `1` and `0` are NOT
accepted in its place; either trips strict rejection on the entire row.

## Anchor selection

Per `(conn, pn_space, utc_day)` bucket, anchor is the row with the smallest
`ack_ts_ms`; ties resolve to the LARGER `packet_number`, then to the larger
`shard_seq`. Anchor verdict is `ACK_DELIVERED`. Picking the most-recent row
or breaking ties by the smaller packet number produces a wrong reading at
multiple downstream layers.

## Window inclusivity

Coalesce window `[0, coalesce_ms]` is right-inclusive. Reorder window
`(coalesce_ms, reorder_ms]` is left-exclusive. The two windows share the
boundary value at `coalesce_ms`; the coalesce window owns the boundary.

## Tier scaling on coalesce_ms

`CRITICAL` tier halves the base. `BULK` and `STANDARD` tiers retain the base.
The reorder window in this edition does not scale by tier.

## Markers

A marker is processed only if `source=="control_plane"`, `kind` is in the
closed marker enum, and `hmac8` matches the recomputed seal. Every failure
mode is a silent drop with no audit trail.

## Cross-cycle budget cascade

A `(conn, day)` ACCEPTED count that reaches `budget_threshold` triggers a
single `BUDGET_EXCEEDED` rewrite on the SAME connection's first still-accepted
event in the NEXT day. The count is the value BEFORE the rewrite.

## Hamilton direction

`REVERSE` by default. Flips to `FORWARD` whenever ANY registered connection
carries `urgent=true` (real boolean only).

## Sort orders

`events` sorts by numeric-suffix conn_id, then `ack_ts_ms`, then pn_space
rank (INITIAL < HANDSHAKE < APP_DATA), then `packet_number`. `by_conn` and
`hamilton` sort by numeric-suffix conn_id.

## Self-binding digest

`report_digest` is the lowercase hex `sha256` over the canonical bytes of the
report with `report_digest` itself blanked. The on-disk file ends in exactly
one trailing newline AFTER the digest is computed.
