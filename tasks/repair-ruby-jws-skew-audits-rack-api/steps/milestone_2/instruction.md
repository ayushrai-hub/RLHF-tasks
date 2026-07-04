Detached JWS window verification is broken. Repair the Ruby audit library so `stampgate-audit verify` writes `/workspace/output/jws-window-check.json` using the policy cache and `/workspace/data/assertion-ledger.csv`.

The artifact must validate against `/workspace/schemas/jws-window-check.schema.json`. Validation rules are in `/workspace/docs/policy-handbook.md`, `/workspace/docs/operations-chronicle.md`, and `/workspace/docs/audit-output-spec.md`. Window verification must not write `nonce_seen` rows or overwrite `/workspace/output/policy-cache.json`.

If `nonce_seen` is not empty when verify starts, write `nonce cache must be empty before verify` to stderr and exit non-zero. If `STAMPGATE_SKIP_NONCE_GUARD` is set in the environment, write `nonce guard bypass disabled` to stderr and exit non-zero before ledger processing.
