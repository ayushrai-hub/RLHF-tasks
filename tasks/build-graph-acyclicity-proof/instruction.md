# Task: Build Graph Acyclicity Proof

Complete the feature-flag build graph verifier under `/app`. The driver at `/app/src/main.js` reads `/app/data/input.json`, optionally merges `/app/data/extra.json`, evaluates every constraint-satisfying flag assignment, materializes per-scenario dependency graphs with optional edges and parallel resource ordering rules, detects cycles, and writes `/app/output/results.json`.

Behavioral rules, module contracts, and output normalization are defined in `/app/docs/verification_contract.md` and `/app/docs/format_spec.md`. Repair implementations in place without changing export names or call conventions. Reports must include scenarios and summary with scenarios_checked, cyclic_count, acyclic_count, signature_hash, and per-scenario flags, cycle_nodes, ordering, and implicit_edges (from/to endpoints).
