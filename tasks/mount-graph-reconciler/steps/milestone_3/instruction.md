# Mount Graph Reconciler — repeat-cycle matrix

Finish repeat-cycle behavior described in `/app/environment/docs/contract_m4.md`. Repeat arms exercise replay semantics within a single matrix run: each repeat arm must match its paired base or variant arm on the cross-linked digest fields named in the contract.

Across invocations without cleanup, a second matrix run must exit non-zero. After cleanup, two consecutive matrix runs (each preceded by cleanup) must produce identical run tokens.

Rebuild with `/app/environment/scripts/bake_m4.sh`, run cleanup from the contract, and regenerate `/app/output/graph_report.json` via the documented matrix command.

When this part is complete, signal completion before moving on to the next part of the work.
