# Snapshot contract

Path: `/app/state/rtcmctl-snapshot.json`

```json
{
  "db_path": "/path/to/db",
  "as_of": "2024-01-01T00:00:00Z",
  "db_fingerprint": "<sha256 db bytes>",
  "station_chain_digest": "<ledger chain_digest>",
  "mutation_seal_digest": "<sha256 compact json of seal fields>",
  "station_count": 2,
  "total_gaps": 1,
  "observable_sum_total": 456.78
}
```

## Counters

- `station_count`: `COUNT(*)` from `stations`
- `total_gaps`: `SUM(gap_count)` from `stations`
- `observable_sum_total`: `SUM(observable_sum)` from `stations`

## mutation_seal_digest

SHA-256 hex of compact JSON:

```json
{"db_fingerprint":"...","db_path":"...","event_count":N,"ledger_chain_digest":"...","tail_created_at":"..."}
```

`refresh-snapshot` validates live seal and ledger digests before writing.

Compact JSON keys for `mutation_seal_digest` must appear in **alphabetical** order: `db_fingerprint`, `db_path`, `event_count`, `ledger_chain_digest`, `tail_created_at`.

## export

`export` must read this snapshot file, validate `station_chain_digest`, `mutation_seal_digest`, and `as_of`, then emit counters from the snapshot — **not** live SQLite queries. `export` does **not** re-hash the database file; the snapshot counters are authoritative for the published `as_of`.

For `mutation_seal_digest`, load `/app/state/rtcmctl-mutation-seal.json`, recompute the digest with the same compact JSON field order as above, and reject when the snapshot value does not equal the recomputed digest. Checking only that the snapshot field is lowercase hex is insufficient.

## Gap detection (persist)

When applying a staged row with `sequence` newer than the stored `last_sequence` for the same `station_key`, add to `gap_count`:

When `next <= last`, compute forward u32 distance as `next.wrapping_sub(last.wrapping_add(1)) + 1`; otherwise `next - last`. Then:

```
delta = 0 if diff <= 1 else diff - 1
```

A single-step advance (`sequence == last_sequence + 1` or wrap `4294967295 → 0`) yields `delta = 0`.

Persist must wrap station upserts and audit inserts in **one** SQLite transaction per batch; rollback all station changes if audit insert fails.
