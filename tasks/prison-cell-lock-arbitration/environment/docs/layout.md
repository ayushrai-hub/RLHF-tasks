# Subsystem layout

The facility stack under `/app/environment` is a Rust workspace plus a linked C library. Four cooperating crates handle node promotion, interval journal replay, movement-plan evaluation, and batched actuator pulses; a separate chain crate produces arithmetically valid summaries. Read-only seeds live under `fixtures/` (do not modify).

## Trace contract

Regenerate `/app/output/failover_trace.json` with:

```bash
bash /app/environment/scripts/run_sim_driver.sh
```

The driver builds the workspace and runs `facility_sim --output /app/output/failover_trace.json`.

Each trace contains top-level `audit_chain_head` (hex string) and `runs[]` rows with:

- `run_id` — scenario label (`epoch_convergence`, `load_pulse`, `lane_span`, `shadow_drop`, `divergent_recovery`, `trace_continuity`, `delayed_commit`)
- `events[]` — rows with `t_ms`, `cell_id`, `observed_controller`, `ownership_epoch`, `override_generation`, `corridor_slice`, `actuator_digest`
- `outcome` — derived reconciliation label

Outcome labels include `converged`, `divergent`, `stale_override`, `partial_isolation`, and `delayed_skew`.

## Derived invariants

- **Epoch unity:** after promotion, the distinct `ownership_epoch` count per converged run must equal 1 across all events in that run.
- **Generation monotonicity:** `override_generation` never decreases within a run.
- **Plan coverage:** coverage ratio is `|seen_slices ∩ plan_slices| / |plan_slices|` where `seen_slices` comes from event `corridor_slice` values and `plan_slices` from the active movement plan fixture (`north-wing`, `east-link`, `yard-cross`, `south-gate`). Converged runs require ratio `1.0`.
- **Baseline generation:** emergency journal entries must carry `override_generation` strictly greater than the topology baseline (`3` in the bundled fixture) or the run ends `stale_override`.
- **Audit continuity:** `audit_chain_head` must equal `5b58a1b91f119798254073d43b5a8ddc9d39717e16136ec9205e1528c9abe531` across regenerated traces.
- **Delayed settle:** after corrupt-then-valid recovery spanning at least three work intervals, converged runs must not end `delayed_skew` once actuator digests settle within two simulator ticks.
- **Multi-scenario trace:** a full simulator pass emits seven scenario runs; the converged run count must be at least 5 once sources are repaired.

## Actuator digest

Each event's `actuator_digest` is the lowercase hex SHA-256 over the concatenation of every `(cell_id bytes || ownership_epoch as little-endian u64)` pair from the registry table at commit time, using the pulse layer's last committed epoch value.
