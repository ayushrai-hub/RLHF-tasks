# Scenario format

A scenario JSON object contains:

- `name`: trace case name.
- `freshness_bound`: maximum allowed proof age in scenario ticks.
- `resources`: resources and actions. Each resource has an `id` string and an `actions` object mapping action names to arrays of allowed group names (for example `"actions": {"read": ["ops"]}`). A user may perform an action when at least one required group is present in the authoritative cache entry for the user's current subject.
- `snapshots`: directory revisions. Each snapshot has `revision`, `proof`, and `principals`.
- `steps`: ordered operations.

Step operations are:

- `publish`: make the snapshot with the given `revision` the active directory snapshot.
- `refresh`: attempt to refresh local cache and derived group index from the active snapshot. Accepted refreshes update both in-memory and persisted cache/index surfaces. Rejected refreshes must still leave persisted `group_index.json` fail-closed so stale username-keyed membership cannot survive on disk.
- `authorize`: evaluate one `username` against a `resource` and `action`.

Principal objects have `username`, `subject_id`, `generation`, `groups`, and `active`. A username can be revoked and later re-added with a different `subject_id` and `generation`; the current subject and current proof govern authorization, not a stale username-keyed membership from an older generation. Bundled fixtures illustrate common principal names and subject ids such as `sana`/`subj-sana`, `ren`/`subj-ren-old`, `subj-ren-new`, and `subj-ren-third`.

Proof objects have `revision`, `issued_at`, and `nonce`. The proof must prove the same directory revision being refreshed and must be fresh according to the scenario's `freshness_bound` at both the refresh tick and any later authorize tick.

Resume runs use the same scenario file. The persisted `case_digest` in `run_manifest.json` must match the scenario bytes before `--resume` continues from `completed_step`.
