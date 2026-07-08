Cross-layer arrival gap

A file-driven intake service polls a spool directory for new arrivals. Steady single-file drops record correctly. Producer traffic through the published bind-layer path drops sporadic ledger entries; a direct touch probe on the watched layered path still reports the bytes. Rename-heavy batches show higher miss tallies in audit excerpts; manual probes keep succeeding.

Widening the host-side allowance alone reduces ENOSPC bursts in trace excerpts; the service keeps under-counting cross-layer arrivals. After observer pauses, generation markers on the host view can advance while the work-view authority lags — a skew that survives byte-length alignment until marker recycle runs.

Repair the Go sources under /app/environment so the arrival-audit driver reproduces correct cross-layer arrival evidence. Rebuild and audit commands are documented in /app/environment/README.md. The verifier deletes /app/output/arrival_trace.json and reruns the build-and-audit pipeline; hand-written JSON is insufficient.

Success criteria, digest formulas, scenario matrix, and idempotency rules are in /app/environment/docs/audit_contract.md. That contract defines the arrival trace at /app/output/arrival_trace.json including runs, report_digest, replay_token, and per-row scenario, wave_gen, edge_fp_host, edge_fp_work, miss_gap, gen_skew, retention_stamp, row_seal. Fan-out bootstrap uses /app/environment/scripts/setup_fanout.sh.

To grade locally inside the container, run bash /tests/test.sh.
