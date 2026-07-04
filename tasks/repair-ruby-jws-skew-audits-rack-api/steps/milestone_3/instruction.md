JTI replay reporting is broken. Repair the Ruby audit library so `stampgate-audit report` writes `/workspace/output/jws-audit-report.json`, clears `nonce_seen` at entry, and records first-use tuples in `/workspace/data/nonce-cache.sqlite`.

The artifact must validate against `/workspace/schemas/jws-audit-report.schema.json`. Replay rules and summary fields are in `/workspace/docs/policy-handbook.md`, `/workspace/docs/operations-chronicle.md`, and `/workspace/docs/audit-output-spec.md`. The `nonce_seen` table shape is defined in `/workspace/sql/nonce-schema.sql` — preserve all columns and the `(issuer, jti, alg)` primary key.

If `STAMPGATE_SKIP_NONCE_CLEAR` is set in the environment, write `nonce clear bypass disabled` to stderr and exit with a non-zero code before touching the nonce database.
