# Enforcement ledger

The admit stage seals post-admit enforcement evidence into `enforcement-ledger.json` immediately after `admission-snapshot.json`. Export reads **both** artifacts and binds checkpoint and digest output to the ledger seal — not to in-memory store fields and not via `session/publish.go`.

## Path

`<session_dir>/enforcement-ledger.json`

## Schema (schema_version = 1)

| Field | Rule |
|-------|------|
| run_id | Same run_id as admission-snapshot.json for this invocation |
| bucket_tokens | Alphabetical map of backend id to token count; must equal snapshot.bucket_tokens |
| config_gen | state.config_gen after admit |
| scope_gen | state.scope_gen after admit |
| route_counter | state.route_counter after admit |
| seq | meta.seq after admit |
| digest_pending_count | Scope-aware pending count (same rule as admission-snapshot.md) |
| admit_seal | Lowercase hex SHA-256 of the compact JSON seal payload below |

## Seal payload

Compact JSON (no spaces) with keys sorted alphabetically at the top level:

```json
{
  "bucket_tokens": {"api": 475, "web": 300},
  "config_gen": 1,
  "digest_pending_count": 0,
  "route_counter": 2,
  "run_id": "take",
  "scope_gen": 0,
  "seq": 4
}
```

`bucket_tokens` keys must be sorted alphabetically. Token values come from the post-admit bucket state (after refill and any consume on the same run).

## Stage contract

1. Admit finishes snapshot write, then writes the ledger with matching fields and a correct admit_seal.
2. Export reads snapshot + ledger, verifies run_id alignment and bucket_tokens equality, recomputes admit_seal from ledger fields, and derives checkpoint.bucket_fingerprint from ledger.bucket_tokens (token counts, not capacities).
3. state_digest uses ledger bucket_tokens plus ledger config_gen, route_counter, scope_gen, seq, and digest_pending_count.

When meta.reload_scope trails state.scope_gen, digest_pending_count in both snapshot and ledger is zero even if meta.pending_reloads is non-empty.
