# SSH Bastion Policy Reload Contract

The driver consumes only local evidence under `/app/fixtures`.

Inputs:

- `reload-state.env` defines the service unit, active generation, and checkpoint sequence.
- `user-map.json` contains visible user rows.
- `includes/bastion.conf` is an include observation.
- `session-audit.jsonl` records ordered grant and revoke events.

Output policy entries must be sorted by user. Active entries come from audit records that match the active generation, do not exceed the checkpoint sequence, and are not revoked for that generation. Revoke records for the active generation must appear in `revoke_manifest.json`.

The report `plan_digest` is the low eight lowercase hex digits of a SHA-256 hash over the canonical plan payload:

`user|role|seq|action`

Lines are sorted by user and joined with `\n` before hashing.
