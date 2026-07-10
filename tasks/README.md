# Terminus Tasks Library

**41 tasks** in this directory — Harbor benchmark tasks for Project Terminus Edition 2.

_Index auto-generated 2026-07-10 23:25_ · refresh with `./scripts/reorganize-tasks.sh`

## At a glance

| Metric | Count |
|--------|------:|
| Total tasks | 41 |
| Regular layout | 34 |
| Milestone layout | 7 |
| Review: Accept | 23 |
| Review: Revise | 8 |
| Review: not yet reviewed | 10 |

**Difficulty:** hard 34, medium 7

**Top categories:** data-processing (13), security (7), machine-learning (6), system-administration (6), build-and-dependency-management (4), scientific-computing (3)

## Finding a task

- Browse the table below (sorted alphabetically)
- Search by folder name: `ls tasks | rg stellar`
- UUID-stub names (e.g. `00af3d22-15f-task`) need `metadata.name` in `task.toml` for canonical renaming

## Per-task structure

```
tasks/<name>/
├── instruction.md      # Agent prompt
├── task.toml           # Metadata, timeouts, category
├── environment/        # Dockerfile + app code (no solution/tests)
├── solution/solve.sh   # Oracle (not visible to agent)
├── tests/              # Verifiers (not in Docker image)
├── review-report.md    # Portal review (if reviewed)
└── audit-report.md     # 55-item audit (if run)
```

## Commands

```bash
./scripts/terminus validate tasks/<name>
./scripts/terminus check-all tasks/<name>
./scripts/terminus review tasks/<name> --report terminus/reviews/entire-report.txt
./scripts/terminus oracle tasks/<name>
./scripts/terminus agent tasks/<name> --model gpt-5.5 --runs 3
```

## Full index

| Task | Difficulty | Category | Layout | Review |
|------|------------|----------|--------|--------|
| `16-fleet-risk-calibrator` | medium | machine-learning | regular | Accept |
| `TimeSeries-Downsampler` | hard | data-processing | milestone | Accept |
| `_go-cookie-scope-auditor` | hard | security | regular | — |
| `_tide-harmonic-forecaster` | hard | scientific-computing | regular | — |
| `bplustree-index` | hard | data-processing | milestone | Accept |
| `breach-ledger-recovery` | hard | security | regular | Revise |
| `breach-ledger-recovery ` | hard | security | regular | — |
| `breast-cancer-cost-calibration-leakage` | hard | machine-learning | regular | — |
| `build-graph-acyclicity-proof` | hard | build-and-dependency-management | regular | Accept |
| `build-pcap-flow-reassembly-gap-classifier-cpp-csv-json` | hard | data-processing | regular | Accept |
| `c-safe-format-spec` | hard | security | regular | Accept |
| `cdn-pop-coassigner` | medium | system-administration | regular | Accept |
| `columnar-encoding-correctness-validator` | hard | data-processing | regular | Accept |
| `cpp-polars-inference-endpoint-harden` | hard | machine-learning | regular | — |
| `cpp-polars-inference-endpoint-harden111` | hard | machine-learning | regular | — |
| `deferred-accept-stash-recover-submission-hard-fixed` | hard | system-administration | regular | Accept |
| `edge-device-drift-classification-auditor` | hard | machine-learning | regular | Accept |
| `edge-trace-log-reconciler-go` | hard | data-processing | regular | Revise |
| `game-replay-chronicle-normalizer` | hard | data-processing | regular | Accept |
| `go-cookie-scope-auditor` | hard | security | regular | Revise |
| `graphviz-risk-snapshot` | medium | software-engineering | milestone | Revise |
| `huffman-container` | hard | data-processing | regular | Accept |
| `ml-eval-api-mlflow` | medium | machine-learning | milestone | Accept |
| `mount-propagation` | medium | system-administration | regular | Accept |
| `offline-service-reconciler` | hard | system-administration | regular | Accept |
| `pubsub-delivery-validator-go` | hard | system-administration | regular | Accept |
| `rbac-temporal-rust` | hard | security | regular | Accept |
| `ready-mix-concrete-batch-dispatch-planner` | hard | data-processing | regular | — |
| `repair-python-oci-build-graph-analysis-with-graphviz-1783502772` | hard | build-and-dependency-management | regular | — |
| `repair-ruby-jws-skew-audits-rack-api` | hard | security | milestone | Accept |
| `scala-abac-attribute-constraint-framed-wire-auditor` | hard | data-processing | regular | Accept |
| `scala-sbt-schema-consumer-regeneration` | hard | build-and-dependency-management | regular | Revise |
| `subtyping-transitivity-checker-go` | hard | data-processing | regular | Revise |
| `sysadmin-bash-iptables-reachability-audit` | medium | system-administration | milestone | Revise |
| `tbrain-orbital-transfer-pruner` | hard | scientific-computing | regular | Accept |
| `tcl-interval-tree-calendar` | medium | data-processing | regular | — |
| `terraform-bazel-lockfile-gen` | hard | build-and-dependency-management | regular | Accept |
| `tide-harmonic-forecaster` | hard | scientific-computing | regular | Revise |
| `tournament-appeal-record-dual-cause-authoring` | hard | games | regular | Accept |
| `warmcache-perl-2` | hard | data-processing | milestone | — |
| `x12-837-claim-loop-weaver` | hard | data-processing | regular | Accept |

## Related paths

| Path | Contents |
|------|----------|
| [`jobs/`](../jobs/) | Harbor oracle/agent run logs |
| [`terminus/reviews/`](../terminus/reviews/) | Platform submission exports |
| [`terminus/_incoming/zips/`](../terminus/_incoming/zips/) | Archived submission ZIPs |
| [`terminus/_backup/copies/`](../terminus/_backup/copies/) | Duplicate task folders |
