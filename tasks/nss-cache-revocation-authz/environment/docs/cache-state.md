# Cache and derived state

The simulator keeps durable local surfaces under the state directory:

1. `cache_entries.json` — cache entries keyed by username. Each entry records username, subject id, generation, groups, directory revision, proof revision, proof age, refreshed-at tick, expiry tick, the refresh epoch that last wrote the row, and whether the subject is revoked.
2. `group_index.json` — derived group membership used by the authorization path and reported in the trace as `group_index`.
3. `run_manifest.json` — resume cursor with `completed_step`, `head_revision`, `refresh_epoch`, `last_refresh_accepted`, and `case_digest`.
4. `refresh_journal.jsonl` — append-only refresh attempts for audit reconstruction.

## Refresh epoch counter

The simulator keeps a monotonic `refresh_epoch` counter for the run (including steps completed before a resume boundary).

- The counter starts at `0` before any accepted refresh.
- Each **accepted** refresh increments the counter **before** writing cache rows. The first accepted refresh stamps entries with epoch `1`, the second with `2`, and so on.
- **Rejected** refreshes do not increment the counter and do not re-stamp cache rows from the rejected snapshot.
- `run_manifest.json` `refresh_epoch` is the counter value after the last persisted step.
- Each `cache_entries` row's `refresh_epoch` records the counter value from the accepted refresh that last wrote that row.

Those surfaces must agree after every step that persists them, including after resume. An accepted refresh updates `cache_entries.json` and rebuilds `group_index.json` from the authoritative snapshot. A rejected refresh must not adopt the rejected snapshot into the cache, but the persisted `group_index.json` must still fail closed: it must not retain username-keyed membership that would grant authority from an earlier accepted refresh when the current refresh attempt is rejected (for example `proof-revision-mismatch`). The in-memory `group_index` reported in the trace must follow the same rule. If a user loses a group, is revoked, or is re-added under the same username with a new subject id, the derived group index must not retain the old subject's group membership. If the active snapshot proof is stale, proves a different revision, or is too old at the authorize tick, the refresh or authorization path must fail closed.

On resume, the runner reloads `run_manifest.json` and persisted cache surfaces. If the manifest `refresh_epoch` is lower than the highest `refresh_epoch` stamped on any cache entry, the counter must be reconciled to that maximum before executing further steps. The trace `provenance.resume.epoch_start` field records the refresh-epoch counter at the resume boundary, not the counter value after the resumed segment finishes.

Revoked principals remain represented in `cache_entries` with `revoked` true and cleared group membership. A principal absent from the active snapshot after refresh must still appear in `cache_entries` with revoked state rather than disappearing from the trace. Authorization against such a revoked row must deny with the canonical reason `revoked-principal`. Empty collections in JSON output — including `groups` on cache entries and member lists in `group_index` — must serialize as `[]`, not `null`. In Go, slice fields that should appear empty in JSON must be initialized (for example `[]string{}`), not left as nil slices.

Allowed users who remain active and still belong to an allowed group must continue to be authorized after a valid refresh. The fix must preserve that behavior while removing revoked rights within the freshness bound and keeping resumed runs equivalent to monolithic runs.
