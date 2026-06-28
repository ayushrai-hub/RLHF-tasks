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
# Schema

The on-disk output is one JSON object at `/app/output/report.json`. The keys at
every level appear in the declared order below. Maps inside objects use their
declared semantic order when the order matters (for example `by_conn` is an
ARRAY of per-connection blocks sorted by numeric suffix on the conn id, not a
JSON object).

## Top level

```
version            string
summary            object
by_conn            array
hamilton           array
events             array
report_digest      string
```

## summary

```
total                       integer       # total rows in events
by_verdict                  object        # closed-enum 7 keys → integer count
registered_connections      integer       # count of rows in connections.ndjson
hamilton_direction          string        # "REVERSE" or "FORWARD"
budget_threshold            integer       # mirrors coalescer_anchor_set.json
policy_version              string        # mirrors coalescer_anchor_set.json
```

## by_conn[i]

Ordered ascending by numeric-suffix on `conn_id` (so `C2` precedes `C10`).

```
conn_id        string
tier           string         # canonicalized to one of CRITICAL, STANDARD, BULK
by_verdict     object         # closed-enum 7 keys → integer count
accepted       integer        # COALESCED + DELIVERED + REORDERED count
events_count   integer        # rows of any verdict on this conn
```

Every registered connection from `connections.ndjson` appears even when no
frames carried its id. If a frame carries a `conn_id` that is not registered,
that conn id still surfaces as its own block; tier falls through to
`STANDARD`.

## hamilton[i]

One entry per registered connection, ordered by numeric-suffix on `conn_id`.

```
conn_id        string
weight         integer        # ACCEPTED count per conn (the input to the share)
basis_points   integer        # 0..10000, see ack_anchor_set.md
```

The sum of `basis_points` is exactly 10000 when total weight is positive, and
all zeros when the total weight is zero.

## events[i]

```
conn_id         string
pn_space        string
ack_ts_ms       integer
packet_number   integer
largest_acked   integer
ack_delay_us    integer
ecn_ct0         integer
ecn_ct1         integer
ecn_ce          integer
ack_eliciting   bool
shard_seq       integer
anchor          bool
verdict         string
```

Field declaration order above IS the on-disk key order. Sort key for the array
is described in `coalescer_run_notes.md`. Rows that failed strict-int retain their
`conn_id`, `pn_space`, and `shard_seq` (so the row is still locatable) but
every numeric field is zeroed and `ack_eliciting` is false. Rows whose
`pn_space` is not in the policy enum carry their original numerics; the
verdict alone marks them `BAD_SPACE`.

## report_digest

A 64-character lowercase hex string, the `sha256` of the canonical bytes of
the report with `report_digest` itself blanked to the empty string. The
canonical bytes use two-space indentation, no HTML escaping, no trailing
whitespace, and no trailing newline; the on-disk file appends exactly one
trailing newline AFTER the digest is computed.
