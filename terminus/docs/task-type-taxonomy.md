# Task Type Taxonomy (Category)

Each task must have exactly one `category` in `task.toml` describing the primary theme or activity. Subtypes use `subcategories` — see [Task Subtypes](task-subtypes.md) (long_context, tool_specific, api_integration, db_interaction, ui_building).

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `system-administration` | OS config, users, packages, processes, services, networks | systemd service, user permissions, Nginx setup |
| `build-and-dependency-management` | Compile, manage deps, build components | Fix broken build, resolve dep conflicts, multi-stage Docker |
| `data-processing` | Transform, parse, filter, aggregate datasets/files | CSV transform, log aggregation, JSON filtering |
| `games` | Game-like/simulated terminal environments, puzzles | VimGolf, terminal puzzle, text adventure |
| `software-engineering` | Feature dev, bug fixes, tests, project maintenance | Caching algorithm, race condition, query optimization |
| `machine-learning` | Train, fine-tune, inference, ML pipelines | Fine-tune model, debug training, optimize inference |
| `debugging` | Find, diagnose, fix errors in code or config | Memory leak, failing tests, production crash |
| `security` | Crypto, auth, permissions, pentest, vulns, RE | SQL injection, TLS config, binary RE |
| `scientific-computing` | Scientific libs, numerical work, simulations | Numerical solver, simulation debug, HPC optimization |

## Choosing a Category

| Primary activity | Category |
|------------------|----------|
| OS/server configuration | `system-administration` |
| Build systems, packages | `build-and-dependency-management` |
| ETL, file processing | `data-processing` |
| Interactive challenges | `games` |
| Code development, testing | `software-engineering` |
| ML model work | `machine-learning` |
| Finding/fixing bugs | `debugging` |
| Security issues | `security` |
| Scientific code | `scientific-computing` |

## Distribution Guidelines

Benchmark diversity targets:

- No single category should exceed **~30%** of total tasks
- At least **four categories** should each represent **≥10%**

Pick the category that best matches the **primary** activity, not incidental steps.

## task.toml Example

```toml
[metadata]
category = "debugging"
subcategories = []
tags = ["python", "pytest", "memory-leak", "profiling"]
```
