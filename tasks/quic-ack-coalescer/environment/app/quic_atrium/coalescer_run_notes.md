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
# Operations

## Sort orders

`events` is sorted by `numeric-suffix(conn_id)` ascending, then `ack_ts_ms`
ascending, then `pn_space` (with the implicit rank `INITIAL < HANDSHAKE <
APP_DATA`), then `packet_number` ascending. Numeric-suffix sort means `C2`
precedes `C10`, which precedes `C11` — a plain lexicographic sort of conn
ids would produce the wrong order on connection ids whose digit length
varies.

`by_conn` is sorted by `numeric-suffix(conn_id)` ascending.

`hamilton` is sorted by `numeric-suffix(conn_id)` ascending.

`by_verdict` keys appear in alphabetical order because the verdict labels
happen to sort alphabetically into a sensible reading order. The closed-enum
guarantee is the inclusion of all seven keys, not the order.

## Cross-cycle cascade walk

Counts per `(conn, day)` are computed AFTER stage-4 window classification and
BEFORE the cascade rewrite. ACCEPTED means the verdict at this stage is one
of `ACK_DELIVERED`, `ACK_COALESCED`, `ACK_REORDERED`. A bucket whose ACCEPTED
count reaches the threshold rewrites the FIRST still-accepted event on the
SAME connection in the NEXT day for which any bucket exists; that event's
verdict becomes `BUDGET_EXCEEDED` and the anchor flag clears. Only one
rewrite per breach; the rewritten event does not propagate further.

When a connection has no day-2 bucket, the breach has no place to land and
the cascade is a no-op for that connection.

## Hamilton walk

Inputs: a registered conn list, a weight per conn equal to the conn's
ACCEPTED count, a boolean flag `any_urgent` computed across registered
connections.

Step 1: pick direction. `any_urgent=true` ⇒ `FORWARD`; otherwise `REVERSE`.

Step 2: floor allocation. `basis_points[c] = floor(weight[c] * 10000 / total)`.
Remainder per conn: `(weight[c] * 10000) mod total`.

Step 3: pick the leftover-many conns by remainder descending. Tiebreak among
equal-remainder conns: FORWARD direction reads conns by numeric-suffix
ascending; REVERSE direction reads conns by numeric-suffix descending. Each
selected conn gets `+1` basis point. Stop when leftover is exhausted.

If total ACCEPTED is zero, every basis_points value is zero and direction is
the default `REVERSE`.

## Run loop

The binary clears `/app/output` before writing. The compiled binary at
`/app/bin/qack` reads `/app/ack_trove` (relative to the working directory) and
writes `/app/output/report.json`. Standard output is empty on success;
standard error carries the failure reason on a nonzero exit. Idempotency is
absolute — running the binary three times in a row produces the same bytes.

## File state

The contents of `/app/ack_trove` are never written to by the binary. The binary
opens shards for read only and closes them before exiting. A read-only check
on `/app/ack_trove` before and after a run produces the same hash.
