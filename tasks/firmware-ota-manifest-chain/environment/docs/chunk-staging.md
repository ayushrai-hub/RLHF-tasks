# Verified chunk-map staging

Milestone 2 splits validate and commit. m2-validate checks layout and payload binding, then writes staging; m2-commit updates state from staging only; m2 runs both.

## Staging path

/app/state/ota/verified-chunk-map.json — pretty-printed JSON, sorted keys, trailing newline.

Fields: chunk_map_sha256, chunks_verified, payload_coverage_end, payload_sha256 (copy of envelope.payload_sha256 from validate), workflow_generation (copy of state.workflow_generation at validate time).

m2-validate must not mutate state.json or clear apply history. Only m2-commit and m2 set chunk_map_sha256, payload_coverage_end, chunk_binding_generation, clear rollback_index and apply_runs, and truncate the apply journal.

If staging is absent at commit time, stderr must include the phrase missing verified chunk map staging.
