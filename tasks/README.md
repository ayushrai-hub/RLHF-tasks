# Terminus Tasks Library

**21 tasks** in this directory — Harbor benchmark tasks for Project Terminus Edition 2.

_Index auto-generated 2026-07-09 02:33_ · refresh with `./scripts/reorganize-tasks.sh`

## At a glance

| Metric | Count |
|--------|------:|
| Total tasks | 21 |
| Regular layout | 17 |
| Milestone layout | 4 |
| Review: Accept | 21 |
| Review: Revise | 0 |
| Review: not yet reviewed | 0 |

**Difficulty:** hard 17, medium 4

**Top categories:** data-processing (8), system-administration (4), machine-learning (3), security (3), build-and-dependency-management (2), scientific-computing (1)

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
| `bplustree-index` | hard | data-processing | milestone | Accept |
| `build-graph-acyclicity-proof` | hard | build-and-dependency-management | regular | Accept |
| `build-pcap-flow-reassembly-gap-classifier-cpp-csv-json` | hard | data-processing | regular | Accept |
| `c-safe-format-spec` | hard | security | regular | Accept |
| `cdn-pop-coassigner` | medium | system-administration | regular | Accept |
| `columnar-encoding-correctness-validator` | hard | data-processing | regular | Accept |
| `deferred-accept-stash-recover-submission-hard-fixed` | hard | system-administration | regular | Accept |
| `edge-device-drift-classification-auditor` | hard | machine-learning | regular | Accept |
| `game-replay-chronicle-normalizer` | hard | data-processing | regular | Accept |
| `huffman-container` | hard | data-processing | regular | Accept |
| `ml-eval-api-mlflow` | medium | machine-learning | milestone | Accept |
| `mount-propagation` | medium | system-administration | regular | Accept |
| `offline-service-reconciler` | hard | system-administration | regular | Accept |
| `rbac-temporal-rust` | hard | security | regular | Accept |
| `repair-ruby-jws-skew-audits-rack-api` | hard | security | milestone | Accept |
| `scala-abac-attribute-constraint-framed-wire-auditor` | hard | data-processing | regular | Accept |
| `tbrain-orbital-transfer-pruner` | hard | scientific-computing | regular | Accept |
| `terraform-bazel-lockfile-gen` | hard | build-and-dependency-management | regular | Accept |
| `x12-837-claim-loop-weaver` | hard | data-processing | regular | Accept |

## Related paths

| Path | Contents |
|------|----------|
| [`jobs/`](../jobs/) | Harbor oracle/agent run logs |
| [`terminus/reviews/`](../terminus/reviews/) | Platform submission exports |
| [`terminus/_incoming/zips/`](../terminus/_incoming/zips/) | Archived submission ZIPs |
| [`terminus/_backup/copies/`](../terminus/_backup/copies/) | Duplicate task folders |
