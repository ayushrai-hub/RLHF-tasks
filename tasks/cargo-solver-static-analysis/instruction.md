The `wavebench` Cargo workspace is at `/app/wavebench`. There's a static-analysis script at `/app/scripts/audit.awk` that's supposed to map every feature gate in the workspace, extract CFL stability constraints from the validation dossier at `/app/docs/validation_dossier.md`, compute the effective CFL ceiling each feature inherits, and flag any feature combinations that violate the stability rules. Right now it's broken — the Cargo parser mishandles `dep:` prefixes and the `crate?/feature` optional-dependency syntax and chokes on feature arrays that span multiple lines or carry trailing commas and inline comments, it only picks up stability rules from section headings and misses the ones buried in reviewer comment threads, method notes, and the errata appendix, the violation check only looks at each feature's direct dependencies instead of resolving the full feature graph, it never computes the CFL ceilings at all, and the output columns are wrong.

Fix the script so that running it against the four workspace `Cargo.toml` files and the dossier writes four deterministic TSV reports under `/app/reports/`. The dossier is the authoritative source for every stability constraint, and only annotations marked `status=active` count — superseded, withdrawn, rejected, draft, and example annotations must be ignored. Feature combinations, missing guards, and inherited CFL ceilings must all be decided from a feature's full transitive set of enabled features across the workspace, and Cargo's weak `crate?/feature` enables only take effect when that optional crate dependency is itself activated within the same manifest.

The four reports use tab-separated columns with these exact headers:

`/app/reports/feature_gates.tsv` — one row per feature across all four crates:
`crate	feature_name	feature_deps	external_deps`
`feature_deps` is a comma-separated, lexicographically sorted list of the feature's same-crate and cross-crate enables (keep `crate/feature` and `crate?/feature` tokens verbatim); `external_deps` is the comma-separated sorted list of `dep:`-prefixed external crates with the `dep:` prefix stripped. Empty lists are the empty string. Rows are sorted by `(crate, feature_name)`.

`/app/reports/cfl_rules.tsv` — one row per active rule:
`rule_id	affected_features	constraint_type	bound_value	source`
For rules taken from the errata table, `source` is `errata-<errata id>` (for example `errata-E-007`). Rows are sorted by `rule_id`.

`/app/reports/audit_violations.tsv` — one row per violating feature:
`crate	feature_name	violation_type	severity	rule_id`
`violation_type` is `PROHIBITED_COMBINATION` for a prohibited feature combination and `MISSING_GUARD` for a required-but-absent guard feature (uppercase). `severity` is `CRITICAL` or `WARNING` as given by the dossier. Rows are sorted by `(crate, feature_name)`.

`/app/reports/cfl_margins.tsv` — one row per feature across all four crates:
`crate	feature_name	effective_cfl_max	binding_rule`
`effective_cfl_max` is the smallest `max_cfl` bound among every `max_cfl` rule whose affected feature appears in that feature's transitive closure, formatted to exactly four decimal places; `binding_rule` is the `rule_id` of that smallest bound, with ties broken by the smallest `rule_id`. When no `max_cfl` rule applies to a feature, `effective_cfl_max` is the empty string and `binding_rule` is `none`. Rows are sorted by `(crate, feature_name)`.
