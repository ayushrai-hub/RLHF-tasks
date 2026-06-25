# Task Requirements

Complete reference for passing review. Use with [Submission Checklist](submission-checklist.md).

## Structural Requirements

| File | Required | Notes |
|------|----------|-------|
| `task.toml` | ✅ | Manifest — see metadata table below |
| `environment/Dockerfile` | ✅ | Or docker-compose.yaml |
| `instruction.md` | ⚠️ | Non-milestone only |
| `solution/solve.sh` | ⚠️ | Non-milestone only |
| `tests/test.sh` | ⚠️ | Non-milestone only |
| `tests/test_outputs.py` | ⚠️ | Non-milestone only |
| `steps/milestone_N/` | ⚠️ | Milestone tasks only |
| `README.md` | 💡 | Optional contributor notes |

### task.toml Metadata

| Field | Required | Notes |
|-------|----------|-------|
| `category` | ✅ | One of 9 types — see [Task Type Taxonomy](task-type-taxonomy.md) |
| `subcategories` | ✅ | See [Task Subtypes](task-subtypes.md) — or empty |
| `number_of_milestones` | ✅ | 0 if none; must equal `[[steps]]` count |
| `difficulty` | ✅ | Based on frontier model pass rates |
| `codebase_size` | ✅ | minimal (0–20), small (20+), large (200+) |
| `languages` | ✅ | Main languages only (not verifier Python) |
| `tags` | ✅ | 3–6 keywords (tools, libraries, techniques) |
| Runtime limits | ✅ | agent, verifier, build timeouts |
| `allow_internet` | ✅ | **Must be false** |

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "unknown"
category = "software-engineering"
subcategories = []
number_of_milestones = 0
codebase_size = "minimal"
languages = ["bash"]
tags = ["file-operations", "debugging", "python"]
expert_time_estimate_min = 60
junior_time_estimate_min = 120

[verifier]
timeout_sec = 450.0

[agent]
timeout_sec = 900.0

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

## instruction.md

Six principles: concise, well-specified, interesting, no hints/answers, unique, absolute paths.

Human-written — mimic real engineer prompts. See [Prompt Styling](guidelines/task-components.md#prompt-styling-6-principles).

Environment spec files must read like realistic engineering docs (API contracts, schemas) — not step-by-step guides or instruction.md splits.

## environment/

- `tmux` + `asciinema` required
- Digest-pin every `FROM` with `@sha256:<digest>`
- Pin all application deps (pip, npm, etc.)
- Canonical final runtime base (or justified)
- ≤ 100 MiB total, no file > 50 MiB
- `.dockerignore` for non-trivial environments
- Never COPY `solution/` or `tests/`
- No privileged mode

Container paths: `/logs/verifier/`, `/logs/agent/`, `/oracle/`, `/tests/`

## solution/solve.sh

- Human-written, deterministic, self-contained, idempotent
- Demonstrates command sequence — no hardcoded answers
- `set -euo pipefail` recommended

Milestone: `steps/milestone_N/solution/solve.sh` (wrapper) + `solveN.sh` (scoped oracle)

## tests/

- `test.sh`: pytest entry + reward file; no runtime installs
- `test_outputs.py`: Python pytest with docstrings on every test
- Test behavior, not implementation
- One test per requirement minimum
- Full prompt coverage (explicit + implicit + edge cases)

Milestone: `steps/milestone_N/tests/test.sh` + `test_mN.py` (`TestMilestoneN` class)

## Milestone Tasks

See [guidelines/milestones.md](guidelines/milestones.md) for full structure.

- `number_of_milestones >= 2`
- Each `steps/milestone_N/` self-contained with `TestMilestoneN` class
- Per-milestone `[steps.agent]` / `[steps.verifier]` — no top-level agent/verifier
- Rubric: 10–40 positive points per milestone

## Submission Diversity (New Submissions)

See [submission-diversity.md](submission-diversity.md).

- **Easy** model difficulty blocked for new submissions
- **Python** tasks must be **hard**
- **Milestone** tasks preferred

## Security

- No privileged containers
- Solution not baked into image
- All verifier deps in Dockerfile
- Minimal attack surface

## Difficulty

Pass rate < 100% against SOTA agents. Verify with 2–3+ runs each:

```bash
stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

## Anti-Cheating

- Dynamic/computed values, not hardcoded answers
- Multi-aspect validation
- Non-trivial verification
- No answers leaked in test assertions

## Rubric

- Platform UI: generate + edit
- ≥3 distinct negative-reward criteria (-1, -2, -3, or -5)

## Automated Checks

### CI (must pass)

pinned_dependencies, check_pinned_images, check_sanctioned_base_images, check_build_context_size, typos, tests_or_solution_in_image, check_dockerfile_references, check_test_sh, check_task_absolute_path, check_privileged_containers, ruff, check_task_sizes, validate_task_fields

### CI (warn by default)

check_dockerignore, check_dockerfile_hygiene, check_offline_tests, check_apt_usage, check_reproducible_builds, check_layer_volatility, check_no_build_tools_in_runtime, check_file_extraction, check_heredoc_usage, check_recursive_permissions

### LLMaJ (must pass)

behavior_in_task_description, behavior_in_tests, informative_test_docstrings, anti_cheating_measures, hardcoded_solution, file_reference_mentioned, structured_data_schema

## Summary Checklist

See [submission-checklist.md](submission-checklist.md) for the full pre-submit workflow.
