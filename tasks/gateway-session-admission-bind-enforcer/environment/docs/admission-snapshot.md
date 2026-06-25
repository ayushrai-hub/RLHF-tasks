# Admission snapshot

After the admit stage completes token refill and any consume, the gateway driver writes `admission-snapshot.json` in the session directory. The enforcement ledger is written immediately afterward with matching fields. Export derives tamper evidence from both staged artifacts per enforcement-ledger.md.

## Path

`<session_dir>/admission-snapshot.json`

## Schema (schema_version = 1)

| Field | Rule |
|-------|------|
| run_id | Echo of the request run_id for this admit |
| accepted | true when consume is omitted; otherwise whether consume succeeded |
| selected_backend | empty when consume is omitted or backend is explicit; round-robin choice when consume.backend is empty |
| tokens_left | zero when consume is omitted; remaining tokens on the consumed backend otherwise |
| config_gen | state.config_gen after admit |
| scope_gen | state.scope_gen after admit |
| route_counter | state.route_counter after admit |
| seq | meta.seq after admit |
| digest_pending_count | Scope-aware pending count for state_digest per state-digest.md |
| bucket_tokens | Alphabetical map of backend id to live token count after admit |

## Stage contract

1. **Admit** mutates enforcement state, writes the snapshot, then seals enforcement-ledger.json.
2. **Export** (`session/export_stage.go`) reads both artifacts and emits the run envelope and checkpoint binding.

The legacy `session/publish.go` helper builds output directly from memory and is **not** the production export hot path.
