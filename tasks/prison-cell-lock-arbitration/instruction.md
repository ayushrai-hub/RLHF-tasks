A maximum-security correctional facility runs an autonomous access-control stack governing electronic cell locks, inmate movement schedules, guard authorization tokens, and emergency lockdown controllers. After primary controller failover, operators observe lock ownership diverging between redundant controllers, emergency overrides replaying with stale authorization, corridor isolation succeeding only on some segments, while audit ledgers remain internally consistent.

Repair the Rust and C source code under `/app/environment` so failover recovery restores coherent lock ownership, rejects stale emergency overrides, and applies corridor isolation across the full movement plan. Do not edit read-only fixtures under `/app/environment/fixtures/` or write static output by hand.

Run verification with:

```bash
bash /app/tests/test.sh
```

The verifier regenerates `/app/output/failover_trace.json` through the normal facility simulator described in `/app/environment/docs/layout.md`. Trace rows include audit_chain_head, runs, run_id, events with t_ms, cell_id, observed_controller, ownership_epoch, override_generation, corridor_slice, actuator_digest, and outcome labels converged, divergent, stale_override, partial_isolation, and delayed_skew. Scenario identifiers, derived invariants, coverage ratio formula, actuator digest derivation, and audit baseline constants are defined in the layout guide. Static trace writes, blanket service restarts, and chain-only edits are insufficient.
