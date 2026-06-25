# Deferred reload and scope isolation

Queued backend policy must not apply across a scope boundary. scope_gen marks the active enforcement scope; reload_scope tags the pending queue.

## fresh_start

Always clear meta.pending_reloads, reset buckets and routing counters, reset config_gen to 0, anchor the refill sequence without applying refill accumulation from seq ticks that belonged to the prior session state, and delete checkpoint.json plus the checkpoints/ archive per checkpoint-chain.md.

Scope generation has two phases:

- Milestone 1 (immediate reload only): fresh_start must not change scope_gen; it stays 0.
- Milestone 2 (deferred reload enabled): fresh_start increments state.scope_gen, sets meta.reload_scope to the new scope_gen, and blocks cross-scope refill accrual as described below.

The milestone 2 scope rule replaces the milestone 1 unchanged-scope_gen rule. Session artifacts from milestone 1 workflows may still show scope_gen 0 after fresh_start; those files illustrate the older phase and must not override the milestone 2 contract.

## queue_reload

queue_reload appends a config to meta.pending_reloads and sets meta.reload_scope to the current state.scope_gen.

## replay_pending

replay_pending applies queued configs in enqueue order only when meta.reload_scope equals state.scope_gen. Queued configs tagged with an older reload_scope are stale and must not change active buckets.

Always clear meta.pending_reloads after replay_pending finishes, whether or not any config applied.

## Output pending_count

pending_count in output is always the live length of meta.pending_reloads after the run completes.
