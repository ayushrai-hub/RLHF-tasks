# Mount Graph Reconciler — baseline cluster

A local TypeScript reconciliation lab under `/app/environment` exposes `/app/bin/mgr_run`. After dry-run then apply on a bind migration ladder, generated unit snapshots and live edge tables look aligned for the first matrix column, but later arms disagree about whether retired bind nodes should remain attached under the prior cluster id.

Rebuild with `/app/environment/scripts/bake_m4.sh`. Run cleanup from `/app/environment/docs/contract_m4.md`, then regenerate `/app/output/graph_report.json` using the documented matrix command from that contract.

Partial observability: text tails under `/app/environment/fixtures/logs/` omit rows; authoritative slices live in `/app/environment/fixtures/edge_slice/*.grf`. Stage stub summaries under `/app/environment/fixtures/stage_stub/m3_stub.json` expose per-cluster alive counts that can disagree with graded node list cardinality after rebuild. Graded arms require distributed consistency between the tab fragment layout (`/app/environment/fixtures/tab_frag/fs0.tab`) and authoritative edge slices per cluster.

The graded artifact is terminal `/app/output/graph_report.json`. Infer and implement sources under `/app/environment` so the normal pipeline regenerates it. Hardcoding the output file, single-surface edits without rebuild coordination, or test modifications are insufficient.

For this phase, baseline cluster c0 must converge after cleanup plus matrix run: retired edge key a002 must not appear in graded node lists, and list cardinality must fall below the stage stub alive count for c0 (documented in the contract). Field-level digest rules and baseline arm requirements are defined in `/app/environment/docs/contract_m4.md`.

When this part is complete, signal completion before moving on to the next part of the work.
