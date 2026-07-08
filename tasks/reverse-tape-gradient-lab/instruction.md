  Graph fixtures under `/app/environment/data/graphs` describe small reverse-mode
  autodiff programs: leaf variables, elementwise add/mul, batched matmul, broadcast
  add, axis reductions, shared subexpressions, and optional second-order passes. The
  unfinished Rust computation kernel and Go orchestration packages must be completed and rebuilt per
  `/app/environment/docs/toolchain.md`. Install CLIs at `/app/environment/build/gradctl-run`,
  `gradctl-probe`, `gradctl-audit`, and `gradctl-inspect`. Every public surface must
  agree with `/app/environment/docs/grad_contract.txt`.

  `gradctl-run` evaluates the active graph set and writes `/app/output/gradient_report.json`,
  `/app/output/node_trace.csv`, `/app/output/pass_journal.jsonl`, plus persisted state under
  `/app/var/grad/` including session counters, gradient pool, pass epoch state, and run
  checkpoint. A reset clears persisted state before evaluation. Alternate graph
  directories and policy files are selectable via environment variables documented in
  the contract. Probe, audit, and inspect outputs must match the report and persisted
  state on every run.

  Build with Go and Rust only — not Python — per `/app/environment/docs/toolchain.md`.
  Rust implements forward evaluation and reverse-mode Jacobian-vector products on the
  computational graph. Go implements graph ingestion, feasibility validation, tolerance
  policy resolution, gradient-pool lifecycle, epoch invalidation, finite-difference
  cross-check metadata, artifact export, and CLI wiring. Op semantics, broadcast rules,
  reduction gradient expansion, shared-node gradient accumulation, second-order pool
  clearing, digest binding, CSV columns, probe literals, negative invalid-graph paths,
  checkpoint waterlines, and cross-surface invariants are specified in the contract.
  `/app/environment/scripts/rebuild.sh` installs a fresh toolchain without hand-written
  JSON or CSV. The verifier reinstalls via that script, mutates graphs and policies,
  sequences multiple runs, and checks every interface against live CLI output and
  independent finite-difference cross-checks.
