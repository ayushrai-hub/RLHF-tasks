# Gateway session integrity model

The edge gateway session driver under /app/environment enforces per-backend rate-limit budgets and isolates backend policy changes across session scopes. Each CLI invocation is an audit event: normalize the request, run admit, persist enforcement state, seal an enforcement ledger, then export tamper-evident output.

## Enforcement layers

| Layer | Purpose | Contract doc |
|-------|---------|--------------|
| Request normalize | Scope-bound gating before admit mutates state | deferred-reload.md, run-pipeline.md |
| Rate budget | Token buckets cap upstream admission | routing-and-capacity.md |
| Policy application | Immediate or deferred backend config reload | routing-and-capacity.md, deferred-reload.md |
| Scope boundary | scope_gen and reload_scope block stale queued policy | deferred-reload.md |
| Staging artifacts | admission-snapshot.json and enforcement-ledger.json | admission-snapshot.md, enforcement-ledger.md |
| Bind staging guard | admission-bind.json verified against ledger and snapshot before export | admission-bind.md, run-pipeline.md |
| Tamper evidence | state_digest, checkpoint bucket_fingerprint, checkpoint chain | state-digest.md, session-checkpoint.md, checkpoint-chain.md |

## Milestone scope

Milestone 1 covers live enforcement: refill, consume rejection, hot reload, routing, ledger sealing, and checkpoint binding with scope_gen fixed at zero on fresh_start.

Milestone 2 adds deferred reload queue/replay and scope-scoped digest rules on top of the ledger pipeline.

Run order is in run-pipeline.md. On-disk fields are in persistence-model.md. The legacy session/publish.go helper is not the production export path.
