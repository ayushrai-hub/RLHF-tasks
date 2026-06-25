# OTA workflow contract

Binary: /app/bin/ota-chain. Persistent state: /app/state/ota/state.json. Milestone outputs go under /app/output/. Apply history appends to /app/state/ota/apply-journal.jsonl. /app/state/ota/session-epoch is read-only for every milestone.

State carries envelope, workflow_generation (incremented on each successful m1 commit), chunk_map_sha256, payload_coverage_end, chunk_binding_generation (must equal workflow_generation after m2 until the next m1), rollback_index, and apply_runs.

Any validation failure exits non-zero. stderr must contain the substring invalid ota workflow (the CLI may prefix detail after a colon).

## Milestone 1 — envelope

Commands: m1-verify envelope.json epoch-keys.json; m1-commit state.json out.json; m1 envelope.json epoch-keys.json state.json out.json.

m1-verify writes /app/state/ota/verified-envelope.json (see envelope-staging.md). m1-commit reads staging only.

Success report: verified true, device and epoch from envelope.

On commit: store envelope object, increment workflow_generation, clear chunk_map_sha256, payload_coverage_end, chunk_binding_generation, rollback_index, apply_runs, truncate apply-journal.jsonl.

Signature string: version|device|build_id|epoch|payload_sha256|epoch-key (see sig_canon.rs). Reject unknown epoch key or signature mismatch.

## Milestone 2 — chunk map

Commands: m2-validate chunks.json state.json payload.bin; m2-commit state.json out.json; m2 chunks.json state.json payload.bin out.json.

Requires non-null envelope in state. SHA-256 of entire payload.bin must equal envelope.payload_sha256.

m2-validate writes verified-chunk-map.json (see chunk-staging.md). m2-commit reads staging only.

Success report: chunks_verified (count), last_end (final byte offset covered).

On commit: set chunk_map_sha256, payload_coverage_end, chunk_binding_generation to current workflow_generation; clear rollback_index, apply_runs, truncate journal.

Chunk map digest: SHA-256 over UTF-8 lines id:start:end:sha256\n in JSON array order from chunks.json (do not sort by id). Logic in chunk_digest.rs.

Chunks must be contiguous: first start is 0; each next start equals previous end. Reject gaps, overlaps, bad bounds, or per-chunk hash mismatch.

## Milestone 3 — rollback

Commands: m3-validate rollback.json state.json current-index.txt; m3-commit state.json out.json; m3 rollback.json state.json current-index.txt out.json.

Requires envelope, chunk_map_sha256, and chunk_binding_generation equal to workflow_generation.

m3-validate writes verified-rollback.json (see rollback-staging.md). m3-commit reads staging only.

rollback.json device must match envelope.device. Let current be the integer in current-index.txt. Reject rollback index strictly less than current; equal is allowed.

Success report: rollback_ok true, index set to accepted value. State stores same value in rollback_index.

## Milestone 4 — staged apply

Commands: m4-validate stage-plan.json state.json run-id; m4-commit state.json out.json; m4 stage-plan.json state.json run-id out.json.

Requires envelope, chunk_map_sha256, payload_coverage_end, rollback_index, and chunk_binding_generation equal to workflow_generation.

m4-validate writes verified-apply-plan.json (see apply-staging.md), including plan_digest and validate_seq. m4-commit reads staging only and runs the ordered commit checks in apply-staging.md (validate sequence, plan digest, staging generation drift, then coverage and replay) before mutating apply_runs.

rollback_index must be greater than or equal to payload_coverage_end.

Success report: device and build_id from stored envelope, stages array from staged plan, run_id from staged run_id, state_apply_count is len(apply_runs) after this run.

Append run_id to apply_runs (no duplicates). Append one JSON line to apply-journal.jsonl: {"run_id":"...","generation":<workflow_generation>}.

Reject stale binding, missing fields, rollback below coverage, or reused run_id.
