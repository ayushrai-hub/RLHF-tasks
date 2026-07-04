StampGate policy loading is broken. Repair the Ruby audit library so `stampgate-audit policy` writes `/workspace/output/policy-cache.json` from the live Rack API on port 8966.

The artifact must validate against `/workspace/schemas/policy-cache.schema.json` and follow `/workspace/docs/audit-output-spec.md`. Authoritative policy rules live in `/workspace/docs/api-reference.md`, `/workspace/docs/policy-handbook.md`, and `/workspace/docs/operations-chronicle.md`.

If `STAMPGATE_USE_STATIC_POLICY` is set in the environment, the subcommand must write `static policy bypass disabled` to stderr and exit with a non-zero code before calling the API.
