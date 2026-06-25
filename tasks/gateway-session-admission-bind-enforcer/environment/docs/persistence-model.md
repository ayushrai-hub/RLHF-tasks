# Session persistence model

Gateway enforcement state lives in each session directory: state.json, meta.json, admission-snapshot.json, checkpoint.json, checkpoints/<seq>.json archives, and per-run output.json. The CLI reads one request JSON per invocation, runs admit then export, and persists state files before exit. See gateway-session-integrity.md for the enforcement model overview. Checkpoint chain layout is in checkpoint-chain.md.

## state.json

| Field | Type | Description |
|-------|------|-------------|
| buckets | map | Per-backend token bucket: tokens and capacity |
| config_gen | int | Count of applied backend configs |
| route_counter | int | Weighted round-robin cursor |
| scope_gen | int | Session scope generation |
| last_refill_seq | int | Last meta.seq value used for refill accumulation |
| active_config | object | Current backend table from the last applied config |

## meta.json

| Field | Type | Description |
|-------|------|-------------|
| pending_reloads | array | Queued backend configs not yet applied |
| reload_scope | int | Scope generation tag for the pending queue |
| last_run_id | string | run_id from the most recent request |
| seq | int | Monotonic run counter incremented once per invocation |

## Request JSON

| Field | Type | Description |
|-------|------|-------------|
| run_id | string | Required identifier for the run |
| fresh_start | bool | Optional scope reset |
| reload | object | Optional immediate backend config |
| queue_reload | object | Optional config to enqueue without applying |
| replay_pending | bool | Optional apply queued configs |
| consume | object | Optional token deduction (backend, cost) |

## Output JSON

| Field | Type | Description |
|-------|------|-------------|
| accepted | bool | true when consume is omitted; otherwise whether consume succeeded |
| selected_backend | string | empty when consume is omitted or backend is explicit; round-robin choice when consume.backend is empty |
| tokens_left | int | zero when consume is omitted; remaining tokens on the consumed backend otherwise |
| pending_count | int | Length of meta.pending_reloads after the run |
| last_run_id | string | Echo of request run_id |
| config_gen | int | state.config_gen after the run |
| scope_gen | int | state.scope_gen after the run |
| state_digest | string | Hex SHA-256 fingerprint; see state-digest.md |

## fresh_start (session reset)

When fresh_start is true at the beginning of a run:

- Clear buckets and active_config-derived bucket state
- Set config_gen to 0 and reset route_counter to 0
- Clear meta.pending_reloads
- Delete checkpoint.json and the checkpoints/ archive directory per checkpoint-chain.md
- Leave scope_gen unchanged in milestone 1 (starts at 0 and stays 0). Milestone 2 scope rules are in deferred-reload.md and gateway-session-integrity.md.
- After meta.seq increments for this run, set last_refill_seq to the new seq without applying refill credit accumulated from seq gaps before the reset

If reload is present on the same request, apply it after the reset; config_gen becomes 1 after that single applied config.
