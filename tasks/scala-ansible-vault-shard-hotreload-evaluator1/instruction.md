The vault shard hot-reload evaluator under `/app` ingests framed vshard rotation bundles into `/app/data/vault.db` and must export `/app/output/vault-hotreload-audit.json` for a tenant. Operators see wrong active secret versions after reload, missing leak rows for unredacted log lines, and reported_at_unix that does not track the latest applied shard sequence.

Normative contracts (required): `/app/docs/vshard-frame-format.md`, `/app/docs/material-precedence.md`, `/app/docs/hotreload-policy.md`, `/app/docs/audit-report-schema.md`, `/app/docs/db-schema.md`, `/app/docs/cli-contract.md`.

Use `/app/bin/vaultshard-ingest` and `/app/bin/vaultshard-export` per the CLI contract doc above. Rebuild with `/app/scripts/build.sh` when you change Scala sources under `/app/src/main/scala/vaultshard/`.
