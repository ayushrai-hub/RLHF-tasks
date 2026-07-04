# Quality Guidelines (TBench Edition 2)

High-level quality bar. All tasks must comply.

## Core Tenets

| Tenet | Requirement |
|-------|-------------|
| **Prompt styling** | Human-written, 1–2 paragraphs problem + ≤2 paragraphs requirements (~20 bullets max) |
| **Multi-step** | ≥5 terminal commands, intermediate states, reasoning (not one-shot) |
| **Testable** | Fully specified; deterministic tests measure final state |
| **Novel** | Not duplicate of TB2/TB3/Edition 1 |
| **No privileged ops** | No `--privileged`, unsafe caps |
| **Standalone** | Completes without human input; Harbor-validated |

## Scenarios to Avoid

### 1. No latency-based tests
Performance thresholds vary by hardware — test correctness only.

### 2. Identical oracle/agent testing
No conditional logic on `/oracle` presence. Same permissions and conditions.

### 3. Tag docker-compose / multi-container
```toml
custom_docker_compose = true   # if docker-compose.yaml
is_multi_container = true      # if multiple containers
```

### 4. No web fetching at runtime
Pre-download into `environment/`. Package installs OK at **build** time only.

### 5. Don't create /tests or /solution in Dockerfile
Harbor reserves these paths.

### 6. Always write reward file
Canonical reward block — never `exit` before writing `reward.txt`.

### 7. Default env vars in test.sh
```bash
TEST_DIR="${TEST_DIR:-/tests}"
```

### 8. No oracle-replication thresholds
Thresholds must allow diverse valid solutions, not ~5% of oracle performance.

## Quick Reference

| Rule | Do |
|------|-----|
| Latency | Don't test timing |
| Testing | Same for oracle & agent |
| Compose | Tag metadata |
| Web | Local data only |
| Reserved dirs | Don't touch /tests, /solution |
| Reward | Write 0 on failure |
| Env vars | `${VAR:-default}` |

See [common-errors.md](common-errors.md) for examples.
