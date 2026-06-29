# Proof schema and CLI contract

The public command contract is the workflow script or direct CLI invocation. Run the adjudicator CLI from `/app` as either `/app/tools/run_public_workflow.sh` or `go run ./cmd/goadj --rulebook <rulebook> --policy <policy> --record <record> --legacy <legacy-record> --out <proof-json>`. The CLI arguments are `--rulebook`, `--policy`, `--record`, `--legacy`, and `--out`; the workflow script supplies the Dragon Cup record, the 1999 archive record, the local rulebook, the local adjudicator policy, and `/app/output/adjudication-proof.json`.

The proof JSON has top-level keys `schema_version`, `all_records_agree`, `rulebook`, `policy`, and `records`. `rulebook.sha256`, `policy.sha256`, and every record `path_sha256` are lowercase SHA-256 digests of the current file bytes. Each record entry includes `record_id`, `path_sha256`, `compatibility`, `rules_engine`, and `independent_judge`.

The `rules_engine` object includes `winner`, `margin`, `passes_to_close`, `terminal_pass_move_numbers`, `final_state_hash`, `legacy_score_notation`, and `variation_replays`. Each variation replay includes `name`, `from_move`, `branch_only_moves`, `branch_leak_count`, and `state_hash`. The `independent_judge` object includes `winner`, `margin`, and `agrees_with_rules_engine`. The legacy record sets `compatibility.legacy_score_notation` and `rules_engine.legacy_score_notation` to true.

A copied Dragon Cup record that preserves the same game semantics may use the temporary filename `dragon-copy.ggr`, output `copy-proof.json`, and record id `dragon-cup-17-copy`; its header appears as `record_id: dragon-cup-17-copy` while the source header is `record_id: dragon-cup-17`. Temporary Go cache directories may be `.gocache` and `.gomodcache`. The legacy archive record id is `sansei-legacy-1999`.

The independent policy may include an `expected_records` map keyed by record id. Each entry can name the expected `winner`, `margin`, `terminal_pass_move_numbers`, `required_variation`, `required_branch_only_moves`, and whether that record may use `allow_legacy_score_token`; copied Dragon Cup records with the `-copy` suffix inherit the Dragon Cup expectation.
