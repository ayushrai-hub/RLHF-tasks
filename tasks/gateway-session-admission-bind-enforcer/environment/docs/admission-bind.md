# Admission bind staging

Between ledger sealing and export, the admit stage writes `admission-bind.json` as a scope-bound staging artifact. Export must read and verify this file against `enforcement-ledger.json` before checkpoint chain work — not via `session/publish.go`.

## Path

`<session_dir>/admission-bind.json`

## Schema (schema_version = 1)

| Field | Rule |
|-------|------|
| scope_epoch | Lowercase hex SHA-256 of the compact scope payload below |
| admit_seal_ref | Must equal enforcement-ledger.json admit_seal for this run |
| seq | Must equal enforcement-ledger.json seq |

## Scope epoch payload

Compact JSON (no spaces) with keys sorted alphabetically at the top level:

```json
{
  "admit_seal": "<ledger admit_seal>",
  "bucket_tokens": {"api": 475, "web": 300},
  "config_gen": 1,
  "scope_gen": 0,
  "seq": 4
}
```

`bucket_tokens` keys must be sorted alphabetically. Values come from ledger.bucket_tokens.

Any change to ledger bucket token values, admit_seal, config_gen, scope_gen, or seq must produce a new scope_epoch. Bucket count alone is not sufficient.

## Stage contract

1. Admit writes admission-snapshot.json, then enforcement-ledger.json, then admission-bind.json with scope_epoch derived from the ledger fields above.
2. Export reads snapshot + ledger + bind, verifies admit_seal_ref and scope_epoch against the ledger, then proceeds to checkpoint-chain.md work.
3. fresh_start deletes admission-bind.json along with checkpoint history per checkpoint-chain.md.

Export must fail when admission-bind.json is missing or when scope_epoch does not match the ledger-derived value.
