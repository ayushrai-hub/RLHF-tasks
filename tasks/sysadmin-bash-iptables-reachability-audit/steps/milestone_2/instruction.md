Fix `/app/lib/persist.sh` so the four tables in `/app/data/iptables_audit.db` (`chains`, `rules`, `chain_graph`, `rule_audit`) reflect the audit shaped by `/app/db/schema.sql`. `/app/docs/SCHEMA.md` specifies each table's contract:

- The per-chain columns `effective_default_policy` and `is_dead_chain` are documented under the `chains` section, including how unconditional targets interact with the declared default and how dead-chain scope is defined against `chain_graph` inbound coverage.
- The `chain_graph` construction rule — one edge per jump/goto rule, with source and destination scoped to the rule's own table — is documented under the `chain_graph` section.
- Per-chain reachability semantics and the `blocked_by_rule_id` reference are documented under the `rule_audit` section, including how each `target_type` affects fall-through within a chain.
- The `is_effectively_dead_chain` signal — its distinction from the structural `is_dead_chain`, the live-edge definition, and the iteration semantics — is documented in its own section.

After editing, run `bash /app/scripts/start_api.sh && bash /app/bin/ipaudit.sh all` to regenerate `/app/data/iptables_audit.db`. Do not modify anything under `/app/api/` or `/app/db/schema.sql`.
