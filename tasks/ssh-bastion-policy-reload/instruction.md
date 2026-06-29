Repair the TypeScript sources under `/app/src` so the ssh bastion policy reload driver writes deterministic artifacts under `/app/output` when run from `/app`:

```bash
node --experimental-strip-types src/reload.ts --input fixtures --output output
```

The driver must derive its outputs from the local artifacts in `/app/fixtures`. Static or manually hard-coded output JSON is not sufficient. The verifier reruns the driver for idempotence and also exercises a variant fixture state.

Write these artifacts:

`policy_plan.json`

```json
{
  "generation": "gen-8",
  "entries": [
    {
      "user": "alice",
      "role": "admin",
      "seq": 3,
      "action": "allow-user"
    }
  ]
}
```

Entries must be sorted lexicographically by `user`. Use `allow-user` for active policy entries.

`revoke_manifest.json`

```json
{
  "generation": "gen-8",
  "revoked": [
    {
      "user": "dan",
      "seq": 7
    }
  ]
}
```

`reload_report.json`

```json
{
  "summary": {
    "unit": "ssh-bastion.service",
    "generation": "gen-8",
    "entries_total": 3,
    "revoked_total": 1,
    "reload_status": "settled",
    "plan_digest": "8 lowercase hex characters"
  },
  "checks": {
    "user_map_complete": true,
    "audit_trail_aligned": true,
    "revokes_respected": true,
    "idempotent_plan": true
  }
}
```

`plan_digest` is the low eight lowercase hex digits of a SHA-256 hash over the canonical plan payload. The canonical payload is one line per policy entry, sorted by user and joined with `\n`. Each line uses `user|role|seq|action`.

## Hints

The reload state in `/app/fixtures/reload-state.env` names the active generation and checkpoint sequence. Session audit records are ordered by `seq`. Revoke records describe users that should not be treated as active policy entries for the current generation. See `/app/docs/reload_contract.md` for the same schema notes and `/app/docs/build_hints.txt` for the verifier command shape.
