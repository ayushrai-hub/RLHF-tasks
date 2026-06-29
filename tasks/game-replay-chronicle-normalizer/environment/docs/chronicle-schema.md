# Chronicle JSON schema (version 1)

UTF-8 JSON written by `replay-chronicle normalize`. Keys are sorted lexicographically in output (Go `encoding/json` default struct order is acceptable when fields are emitted in this order):

```json
{
  "events": [ ... ],
  "integrity": "<hex>",
  "shards": [ ... ],
  "version": 1
}
```

### `shards` array

One object per input `.grsh` file (sorted by `shard_id` ascending):

```json
{"drift_ms": <int>, "shard_id": <uint>}
```

### `events` array

After parsing all shards, apply drift correction (`tick = raw_tick - drift_ms` per originating shard), then:

1. Sort by `(tick asc, seq asc)`.
2. Deduplicate on `(tick, seq)` — keep the **first** occurrence in the pre-sort file read order when ticks and seqs collide.

Each event object:

```json
{"payload_hex": "<lowercase hex>", "seq": <uint>, "tick": <uint>, "type": <uint>}
```

`payload_hex` is lowercase hex encoding of raw payload bytes (empty string when length zero).

### `integrity`

SHA-256 hex digest (lowercase) of the canonical string built by concatenating, for each event in final order:

```
{seq}:{tick}:{type}:{payload_hex};
```

Example for one event: `1:100:3:ff;`

`replay-chronicle validate` recomputes this digest and compares to `integrity`. Exit 0 on match, non-zero otherwise.
