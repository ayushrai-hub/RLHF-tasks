# Ledger rules

Rejection `reason` strings and `priority_rank` integers are defined in `/app/internal/domain/domain.go`. When starter code or draft docs disagree with that file or `/app/instruction.md`, the instruction wins.

## Replay order

Fold durable journal rows in ascending `(logical_time, event_id, source_line_index)` order. Batch import order does not define replay order.

## Validation gates

Walk each event through the gates below in this order (first failure wins):

1. Field and type validation (`missing_required` through `invalid_target`)
2. Duplicate `event_id` with conflicting payload (`duplicate_event_id`)
3. Idempotent duplicate skip (same payload → `skipped_idempotent_count`, no re-apply)
4. `account_suspended` for `RESERVE`, `CONSUME`, `RELEASE`, `CORRECTION` on suspended accounts
5. `RESUME` / `account_not_suspended` / `resume_replica_mismatch`
6. `stale_seq` per `(account_id, source_replica)` including `REVERSAL`
7. `replica_conflict` for concurrent `CORRECTION` at the same `(account_id, logical_time)`
8. `REVERSAL` target guards (`reversal_*`)
9. `insufficient_quota` for `RESERVE`, `CONSUME`, and `RELEASE`

## Apply semantics

- `CORRECTION`: remember prior `available`, then set `available` to the event amount.
- `RESERVE`: `available -= amount`, `held += amount`; optional `expires_at` tracked for rebuild expiration.
- `CONSUME`: require `available + held >= amount`; subtract from `held` first, then `available`.
- `RELEASE`: `held -= amount`, `available += amount`.
- `SUSPEND` / `RESUME`: suspend lock owned by the applying replica until a matching `RESUME`.
- `CARRY_FORWARD`: double `available`, clear `held`, set `epoch`.
- `REVERSAL` inverts the target event on the same account and replica:
  - target `RESERVE`: `held -= amount`, `available += amount`
  - target `CONSUME`: let `need` be the target consume `amount` and `h = min(need, held)` using the account's **current** `held` at reversal time (not the held debit from when the consume originally applied). Then `held += h` and `available += (need - h)`.
  - target `RELEASE`: `held += amount`, `available -= amount`
  - target `CORRECTION`: restore the `available` value stored when that correction applied

### Worked example: `CONSUME` reversal with partial held debit

Seed batch `ACC-WIDGET` (replay in `(logical_time, event_id)` order):

1. `CORRECTION` amount `2` at `09:00` → `available=2`
2. `CORRECTION` amount `10` at `10:00` → `available=10`
3. `RESERVE` amount `5` → `available=5`, `held=5`
4. `CONSUME` amount `3` → debit held first: `held=2`, `available=5`
5. `SUSPEND` (account suspended; a reversal while suspended is rejected)
6. `RESUME` by the suspending replica → account active again, still `held=2`, `available=5`
7. `REVERSAL` of the step-4 consume (`need=3`, current `held=2`): `h=min(3,2)=2` → `held=4`, `available=6`
8. `CORRECTION` amount `8` → `available=8`, `held=4`

Final `ACC-WIDGET` row: `available=8`, `held=4`. Restoring the full consume amount to `held` (for example `held += 3` when `held` was `2`) is incorrect.

## Journal durability

Import stores each batch file plus a `durable_bytes` prefix ending at the last complete newline.

Rebuild reads only that prefix. Bytes after the prefix are invisible: they do not affect `event_line_count`, `parsed_count`, or `malformed_line_count`.

Unparseable lines inside the durable prefix increment `malformed_line_count` only.

## Idempotency

Re-importing the same batch name is a no-op. Identical `event_id` payloads increment `skipped_idempotent_count`.

`processed_count` equals `applied_count + rejected_count` (excludes malformed lines and idempotent skips).
