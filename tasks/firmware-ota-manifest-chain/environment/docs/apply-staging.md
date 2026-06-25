# Verified apply-plan staging

Milestone 4 splits validate and commit. m4-validate checks prerequisites, coverage, replay, and binding, then writes staging; m4-commit records apply_runs and journal from staging only; m4 runs both.

## Staging path

/app/state/ota/verified-apply-plan.json — pretty-printed JSON, trailing newline.

Fields: stages (array copied from the plan file at validate time), run_id (CLI argument at validate time), workflow_generation, payload_coverage_end, rollback_index (snapshots from state at validate time), plan_digest (lowercase hex SHA-256 of UTF-8 bytes formed by joining each stage string with a single newline, in plan file order — do not sort stage names), validate_seq (value of apply-validate-seq.json seq field at validate time, before increment).

## Validate sequence ledger

Path: /app/state/ota/apply-validate-seq.json — {"seq": 0} when absent.

m4-validate reads seq, stores it as validate_seq on staging, then increments seq by one.

## m4-commit check order (mandatory)

After loading verified-apply-plan.json, m4-commit must evaluate failures in this order (do not reorder — tests match stderr verbatim):

1. **Validate sequence** — current seq in apply-validate-seq.json must equal validate_seq on staging plus exactly one. On failure stderr must include the exact contiguous substring **stale apply validate sequence** (verbatim spelling and spacing).
2. **Plan digest** — plan_digest on staging must equal apply_staging::compute_plan_digest of staged stages. On failure: **apply plan digest mismatch**.
3. **Staging generation drift** — workflow_generation in state.json must equal workflow_generation on staging. On failure: **stale apply plan staging generation**. This check must run before any chunk_binding_generation versus workflow_generation comparison on commit (when only workflow_generation drifted, commit must not report stale chunk binding generation first).
4. **Coverage versus rollback** — rollback_index on staging must be greater than or equal to payload_coverage_end on staging.
5. **Run-id replay** — run_id on staging must not already appear in apply_runs.

Only after all checks pass may commit append apply_runs and the journal line.

m4-validate must not append to apply_runs or the apply journal. Only m4-commit and m4 mutate those.

Decoy module apply_plan_digest.rs sorts stages and joins with commas — not used on the validate hot path. m4-validate must call apply_staging::compute_plan_digest only; that helper must newline-join stages in plan file order without sorting names.

If staging is absent at commit time, stderr must include the phrase missing verified apply plan staging.
