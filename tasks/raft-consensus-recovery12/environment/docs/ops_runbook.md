# Ops Runbook — Partition Incident

## Symptoms reported

- Two nodes claim leadership after heal window `tick=120`.
- Clients saw divergent reads for keys `quota` and `session`.
- Election timeout metrics spiked on n4/n5 — **this is a red herring**; timeouts were nominal.

## What to ignore

- `forensics_notes.txt` claim that "Raft is fine, it's DNS" — DNS was healthy.
- Snapshot lag on n3 — snapshots were current; lag was a display bug.

## Recovery objective

Restore single-leader linearizable commits without editing `/app/config/cluster_policy.json`.
