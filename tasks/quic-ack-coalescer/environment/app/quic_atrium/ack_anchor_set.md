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
# Policies

`coalescer_anchor_set.json` carries the runtime configuration. The fields in detail:

## Coalesce and reorder windows

`coalesce_us_base` and `reorder_us_base` are the base window lengths in
milliseconds. Despite the name suffix, both are integer milliseconds in this
codebase — the suffix is a historical artifact retained for compatibility with
upstream packet traces. Each tier scales the base via
`tier_coalesce_factor_permille` and `tier_reorder_factor_permille`.

Effective window for a connection of tier T is
`base * tier_factor_permille[T] / 1000` rounded toward zero. The `CRITICAL`
tier halves `coalesce_ms` (factor 500), shrinking the coalesce window from
200ms to 100ms. The `BULK` and `STANDARD` tiers retain the base. Reorder
factors are 1000 for every tier in this edition.

## Window inclusivity

The coalesce window is left-inclusive and right-inclusive: a non-anchor row
with delta in `[0, coalesce_ms]` is COALESCED. The reorder window is
left-exclusive and right-inclusive: a non-anchor row with delta in
`(coalesce_ms, reorder_ms]` is REORDERED. The two windows share the boundary
value `coalesce_ms`. A row whose delta is exactly that boundary is COALESCED,
because the coalesce window carries the boundary while the reorder window
does not. A row whose delta exceeds `reorder_ms` is `ACK_DELIVERED`.

## Anchor selection

Inside a `(conn, pn_space, utc_day)` bucket the anchor is the row with the
smallest `ack_ts_ms`. On a tie, the LARGER `packet_number` wins. On a further
tie, the larger `shard_seq` wins. The anchor's own verdict is `ACK_DELIVERED`.
The anchor itself is always the FIRST occurrence on its bucket — picking the
most recent instead is wrong.

## Tier synonyms

`tier_synonyms` maps lower-case input labels onto the canonical upper-case
enum. A raw tier label is lower-cased and trimmed before lookup. An unmapped
value falls through to `STANDARD`.

## Cross-cycle budget

`budget_threshold` is the count at which a `(conn, day)` bucket triggers a
single rewrite on the NEXT day's first still-accepted event in the same
connection. The count is taken AT the moment of evaluation — before the
rewrite. The rewrite uses verdict `BUDGET_EXCEEDED` and removes the anchor
flag from the rewritten row. The rewritten row stops contributing to the
Hamilton weight.

## Hamilton direction

The default distribution direction is `REVERSE`. When ANY registered
connection carries `urgent=true` (real boolean only — the integer 1 does NOT
count), the direction FLIPS to `FORWARD`. The direction influences only the
remainder-tiebreak ordering, not the floor allocation; see `coalescer_run_notes.md`.

## Marker enums

`pn_spaces` is the closed enum for valid `pn_space` values. Any other value
on a frame surfaces as `BAD_SPACE`. `marker_kinds` is the closed enum for
recognized marker kinds; any other value silently drops the marker.

## Marker seal

The eight-hex seal is the prefix of `sha256` over the pipe-joined preimage
`secret_label|kind|conn|target_low|target_high|issued_ts`. A non-matching
seal drops the marker silently. A non-`control_plane` source drops the
marker silently. A marker kind not in `marker_kinds` drops silently.
