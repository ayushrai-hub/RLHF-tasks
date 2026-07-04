Production writes are diverging after a healed network-partition incident. On-call left a note: restore consensus safety — everything you need is on the machine under `/app`.

The recovery workspace is a Node.js Raft forensic replay engine. The public CLI at `/app/consensus_lab/cli.js` delegates to `/app/raft_mesh/`; repair the shared engine modules there and treat `/app/config/` as read-only evidence.

Run:

`node /app/consensus_lab/cli.js --bundle /app/scenarios/partition --output /app/output`

Accepted recovery for the default bundle uses classification `raft_split_brain` with `root_cause` equal to that same token and `primary_node=n1`. After remediation, `after.split_brain_detected` is `false` and `after.commands_lost` is `0`. Misleading election-timeout spikes and snapshot lag notes belong in `rejected_causes`, not `root_cause`.

Write these artifacts under `/app/output`:

- `/app/output/consensus_report.json` — schema version 4 JSON with classification, `root_cause`, `before`/`after` metric objects, and parse summary (`accepted_commands`, `duplicate_commands`).
- `/app/output/term_timeline.csv` — columns `phase,node_id,term,start_tick,end_tick,role,votes_received` with `before` and `after` rows.
- `/app/output/command_trace.json` — schema version 4 object with a `commands` array (not a bare top-level list). Each entry has `key`, `index`, `term`, `value`, and sorted `stages`.
- `/app/output/safety_certificate.json` — `split_brain_detected`, `linearizability_digest`, `simulation_seed`, and `invariants` array with `{name, passed}` entries.
- `/app/output/wal_digest.txt` — sorted `key=value` lines including `cluster_policy_changed=false`, `linearizability_digest=`, and `simulation_seed=`.

Rejected replays exit non-zero, write only `consensus_report.json` with `status=rejected`, and must not create the other output files.

Bundle layout, layered validation priority, rejection behavior, identical-duplicate deduplication, canonicalization, frame ordering, partition rules, election checks, commit safety, deterministic serialization, and full output schemas are in `/app/docs/consensus_contract.md`. Operational context and misleading signals are in `/app/docs/ops_runbook.md`, `/app/docs/cluster_map.md`, and `/app/docs/validation_matrix.md`.

The repaired code must be idempotent, stable under reordered equivalent events, precise about the highest-priority failure reason, efficient on large traces, and must compute outputs by replay rather than checking in canned results.
