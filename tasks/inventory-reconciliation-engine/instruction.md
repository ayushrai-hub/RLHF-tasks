# Quota Ledger Restart Skew

The local quota ledger under `/app` ingests event batches, persists an append-only journal, rebuilds a materialized projection, and emits quota and audit reports. After interrupted imports, duplicate retries, reservation expirations, cross-replica corrections, and compensating reversals, the rebuilt balances and digests no longer match operator expectations.

Repair the Go implementation so the documented workflow produces correct persistent state and reports. Static, canned, precomputed, or hand-authored JSON is insufficient.

## Workflow

Run from a clean `/app/state` (verifier resets state before each scenario):

```bash
/app/bin/ledgerctl import --batch seed --events /app/data/batches/seed.jsonl
/app/bin/ledgerctl rebuild
/app/bin/ledgerctl report --out /app/output/quota_report.json
/app/bin/ledgerctl audit --out /app/output/audit_trail.json
```

Re-importing the same batch name must be a no-op. Running `rebuild` twice on unchanged journal data must not change semantic report fields.

## Event batches

Each non-blank line of a batch file is one JSON object. Allowed keys only: `event_id`, `account_id`, `operation`, `amount`, `logical_time`, `source_replica`, `seq`, `epoch`, `target_event_id`, `expires_at`.

Field formats, bounds, and validation errors are defined in `/app/internal/domain/domain.go`. Amount bounds: `RESERVE`/`CONSUME`/`RELEASE` require integers `>= 1`; `CORRECTION` requires an integer `>= 0`. Unparseable lines inside the durable import prefix increment `malformed_line_count` only.

## Processing

After import, `rebuild` folds all durable journal rows in ascending `(logical_time, event_id, source_line_index)` order — not file or batch import order.

Operational semantics (validation gate order, apply rules, journal durability, legacy merge, and expiration) are defined in `/app/docs/ledger_rules.md` and `/app/docs/quota_policy.md`. Reason strings and `priority_rank` values must match `/app/internal/domain/domain.go`. When starter code or draft docs disagree with those files or this instruction, this instruction wins.

High-signal rules:

- New accounts use `limit=1000`, `available=0`, `held=0`, and inherit `epoch` from the first event that materializes the account row during apply (not `0`). `CORRECTION` sets `available`, not `limit`.
- Per `(account_id, source_replica)`, `seq` must strictly increase across every applied mutating event, including `REVERSAL`.
- `CONSUME` requires `available + held >= amount` and debits `held` before `available`.
- `REVERSAL` inverts the target operation (`RESERVE`, `CONSUME`, `RELEASE`, or `CORRECTION`) from the same replica on the same account; see ledger rules for per-type inversion. For `CONSUME`, restoration uses the account's **current** `held` at reversal time (not the split recorded when the consume originally applied).
- Concurrent `CORRECTION` at the same `logical_time` for the same account is first-writer-wins in replay order; later different replicas fail with `replica_conflict`.
- Only the replica that applied `SUSPEND` may `RESUME` that account.
- Import records a durable byte prefix per batch ending at the last complete newline; truncated tail bytes are excluded from all replay counters.
- Legacy snapshot `/app/data/legacy/snapshot_v0.json` merges at rebuild start for accounts without journal-derived state, using `last_event_id="LEGACY-IMPORT"` and `last_logical_time="1970-01-01T00:00:00Z"` until a live event applies.
- Reservation expiration runs at rebuild completion using current UTC time; see quota policy.

## Report schema

`/app/output/quota_report.json`:

```json
{
  "generated_from": "quota-ledger-v2",
  "event_line_count": 0,
  "parsed_count": 0,
  "malformed_line_count": 0,
  "processed_count": 0,
  "applied_count": 0,
  "rejected_count": 0,
  "skipped_idempotent_count": 0,
  "rejections": [],
  "accounts": [],
  "snapshot_digest": "..."
}
```

- `processed_count` equals `applied_count + rejected_count`.
- `rejections`: sorted by `(priority_rank, event_id)`.
- `accounts`: active (non-suspended) accounts with materialized state, sorted by `account_id`. Include journal-applied accounts and legacy-imported accounts (`last_event_id="LEGACY-IMPORT"`). Exclude accounts that were never seeded and never touched by a live event. Each row has `account_id`, `available`, `held`, `limit`, `epoch`, `last_event_id`, `last_logical_time`.
- `snapshot_digest`: lowercase SHA-256 hex of canonical JSON excluding `snapshot_digest`, with `sort_keys=True` and separators `(",", ":")`.

`/app/output/audit_trail.json` exposes `generated_from`, `batch_count`, `journal_digest`, `projection_digest`, `batches`, and `audit_digest` (same digest rules excluding `audit_digest`). Its `projection_digest` must match the report's `snapshot_digest` after rebuild.

The verifier command is `/tests/test.sh`.
