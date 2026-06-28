Finish the Clinicflow workflow with `python -m clinicflow audit`. It should reconcile `/app/output/m1_clean.json`, `/app/output/m2_plan.json`, and `/app/output/m3_actions.json`, apply `/app/data/review_policy.json`, and write `/app/output/m4_audit.json` by default. The command must also accept `--clean`, `--plan`, `--actions`, `--rules`, `--policy`, and `--output`; missing output parents are created and repeated runs replace the file.

Keep `normalize`, `plan`, and `actions` working with their existing flags. The audit output has `review_items`, `owner_summary`, and `meta` sections covering cross-stage mismatch detection, expected action/channel recomputation, stateful owner review-cap allocation, deferrals, batch keys, and the audit digest.

The exact schema, ordering, allocation rules, mismatch codes, digest input, and fallback behavior are in `/app/docs/clinicflow_contract.md` under "Milestone 4: audit".
