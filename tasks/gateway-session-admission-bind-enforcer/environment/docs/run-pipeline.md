# Run pipeline

One request is processed per CLI invocation for the gateway session integrity driver. The driver runs normalize, admit (with staging artifacts), persist, then export.

## Stage order

### Normalize stage

1. Apply scope-bound request gating per deferred-reload.md before admit mutates buckets.

### Admit stage

2. If fresh_start is true, apply the fresh_start session reset in persistence-model.md.
3. Set meta.last_run_id from run_id.
4. Increment meta.seq by one (including idle runs with no consume).
5. If queue_reload is present, append that config to meta.pending_reloads.
6. If replay_pending is true, apply deferred reload rules in deferred-reload.md.
7. If reload is present, apply the config to active buckets per routing-and-capacity.md.
8. Apply per-backend token refill before any consume on this run. Refill delta semantics are in refill-anchor.md.
9. If consume is present, route or select the backend and attempt token deduction. If consume is absent, record accepted true, selected_backend empty, and tokens_left zero in the admission snapshot.
10. Write admission-snapshot.json capturing the post-admit view per admission-snapshot.md.
11. Write enforcement-ledger.json with matching fields and admit_seal per enforcement-ledger.md.
12. Write admission-bind.json with scope_epoch and admit_seal_ref per admission-bind.md.

### Persist stage

13. Write state.json and meta.json.

### Export stage

14. Read admission-snapshot.json, enforcement-ledger.json, and admission-bind.json; run staging triple verification (admit_seal_ref, scope_epoch, and snapshot/ledger token alignment) per admission-bind.md; verify the checkpoint chain per checkpoint-chain.md; archive the prior head; emit output.json and checkpoint.json per session-checkpoint.md and state-digest.md.

Idle requests that only carry run_id still execute refill (admit stage 8).

## Refill

For each backend in the active config with a positive refill_rate, add refill_rate multiplied by the elapsed sequence gap since the last refill anchor. Token counts must not exceed backend capacity.

Advance the refill anchor to the current meta.seq after refill on a run. Config transitions on the same run align the refill anchor to the current meta.seq so sequence ticks before that boundary do not accrue refill credit across the transition.
