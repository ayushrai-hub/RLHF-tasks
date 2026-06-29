# Quota ledger policy

## Account defaults

New accounts materialize with `limit=1000`, `available=0`, and `held=0` unless legacy import supplies an opening balance.

When an account row is first created during event application, set `epoch` from that event's `epoch` field (do not default to `0`).

`CORRECTION` sets `available` to the event amount. It does not change `limit`.

## Balance semantics

`CONSUME` requires `available + held >= amount`. Debit `held` first, then `available`.

`RESERVE` moves quantity from `available` to `held`.

`RELEASE` moves quantity from `held` back to `available`.

## Reservation expiration

Expiration runs during `rebuild`, after all durable journal events are applied.

For each applied `RESERVE` with `expires_at`, if the rebuild evaluation instant is on or after `expires_at`, release the held quantity back to `available`. The rebuild evaluation instant is the container's current UTC time at rebuild completion (not the latest journal `logical_time`).

Expiration does not append journal rows.

## Legacy import

`/app/data/legacy/snapshot_v0.json` (`format: quota-v0`) seeds accounts that have no journal-derived state yet.

For each legacy row, set `available` and `epoch` from the snapshot, keep `limit=1000`, and record:

- `last_event_id`: `LEGACY-IMPORT`
- `last_logical_time`: `1970-01-01T00:00:00Z`

Legacy merge runs at the start of every rebuild, before folding journal events. Once a live journal event applies to the account, later rebuilds keep the live `last_event_id` / `last_logical_time`.

Legacy-imported accounts (`last_event_id="LEGACY-IMPORT"`) are included in report `accounts` output when active (non-suspended), even if no journal event has applied yet.
