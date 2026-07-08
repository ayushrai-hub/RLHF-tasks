# RLHF-tasks — Terminus Edition 2

[![GitHub](https://img.shields.io/github/repo-size/ayushrai-hub/RLHF-tasks)](https://github.com/ayushrai-hub/RLHF-tasks)
**21** curated benchmark tasks · **79** Harbor job runs · automation for authoring, validation, and peer review

This repository is a working library and toolchain for [**Project Terminus Edition 2**](https://snorkel.ai) — Docker-container engineering tasks that benchmark AI coding agents (GPT-5.5, Claude Opus 4.8).

| What | Where |
|------|-------|
| **Task library** | [`tasks/`](tasks/) — all task folders with `instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/` |
| **Task index** | [`tasks/README.md`](tasks/README.md) — auto-generated table with difficulty, category, review status |
| **Harbor run logs** | [`jobs/`](jobs/) — local oracle/agent job outputs |
| **Terminus hub** | [`terminus/`](terminus/) — docs, scripts, review exports, archives |
| **CLI** | [`scripts/terminus`](scripts/terminus) — validate, audit, review, oracle, agent, zip |

---

## Quick Start

### Prerequisites (once)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install snorkelai-stb --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html --python ">=3.12"
uv tool install "harbor @ https://snorkel-public.s3.us-west-2.amazonaws.com/harbor/harbor-0.5.0%2Bpromptfix5-py3-none-any.whl" --python 3.13

stb login
export OPENAI_API_KEY=<your-portkey-api-key>
export OPENAI_BASE_URL=https://api.portkey.ai/v1
```

### Work on an existing task

```bash
# Validate structure and CI rules
./scripts/terminus validate tasks/<task-name>
./scripts/terminus check-all tasks/<task-name>

# Run oracle solution
./scripts/terminus oracle tasks/<task-name>

# Agent difficulty test (both reference models)
./scripts/terminus agent tasks/<task-name> --model gpt-5.5 --runs 3
./scripts/terminus agent tasks/<task-name> --model claude-opus-4-8 --runs 3
```

### Create a new task

```bash
stb init my-task -p "Terminus-2nd-Edition" -t base
# develop in my-task/, then:
./scripts/terminus check-all ./my-task
./scripts/terminus zip ./my-task
stb submissions create ./my-task -p "Terminus-2nd-Edition" --time 120
```

### After downloading tasks or ZIPs

```bash
./scripts/reorganize-tasks.sh   # moves loose folders → tasks/, archives clutter, regenerates index
```

---

## Workflows

### Authors

1. Scaffold with `stb init` or copy a skeleton from `tasks/Default_Task_Skeleton`
2. Develop `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/`
3. Run `./scripts/terminus check-all <task-dir>` before every submit
4. Calibrate difficulty with agent runs on **both** reference models
5. Author rubric on the platform (≥3 negatives; ≤40 positive points total)
6. Package with `./scripts/terminus zip <task-dir>`

### Reviewers

1. Download submission → save export as `terminus/reviews/entire-report.txt`
2. Run accuracy review:

```bash
./scripts/terminus validate tasks/<task-name>
./scripts/terminus audit tasks/<task-name> --report terminus/reviews/entire-report.txt
./scripts/terminus review tasks/<task-name> --report terminus/reviews/entire-report.txt
```

3. Enrich `tasks/<task-name>/review-report.md` (blockers, CHECK/UNCHECK #s, portal note)
4. Use skill `@terminus-accuracy-review` or follow [`prompt.md`](prompt.md)

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `validate` | Structure, paths, Dockerfile, test.sh reward block |
| `audit` | 55-item read-only checklist → `audit-report.md` |
| `review` | Portal review report → `review-report.md` |
| `check-all` | validate + audit + submission checklist |
| `checklist` | Submission checklist only |
| `ci-check` | CI-aligned checks |
| `llmaj-check` | LLM-as-Judge alignment hints |
| `oracle` | Run oracle agent via Harbor |
| `agent` | Run GPT-5.5 or Claude Opus 4.8 |
| `zip` | Create submission ZIP |
| `rubric-points` | Sum positive rubric points from export |

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus audit <task-dir> [--report entire-report.txt]
./scripts/terminus review <task-dir> --report entire-report.txt
./scripts/terminus check-all <task-dir>
./scripts/terminus oracle <task-dir>
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 3
./scripts/terminus zip <task-dir>
```

---

## Difficulty Calibration

| Tier | Worst-model pass rate | Action |
|------|----------------------|--------|
| **Hard** | ≤20% | Target for new Python tasks |
| **Medium** | 20–60% | Acceptable |
| **Easy** | 60–80% | Note in review |
| **Rejected** | >80% | Too easy — do not submit |

Benchmark models: **GPT-5.5** (worst-model gate) and **Claude Opus 4.8**.

---

## Repository Layout

```
.
├── tasks/                  # 21 curated Terminus task folders
│   └── README.md           # Auto-generated index
├── jobs/                   # Harbor job run outputs (oracle/agent)
├── terminus/               # Hub: docs, scripts, reviews, archives
│   ├── docs/               # Guidelines & checklists (symlinked at root)
│   ├── scripts/            # terminus CLI, audit, reorganize
│   ├── reviews/            # Platform exports (entire-report.txt)
│   ├── jobs/               # Additional Harbor job history
│   ├── _incoming/zips/     # Archived submission ZIPs
│   ├── _backup/copies/     # Duplicate task folders (gitignored)
│   └── _misc/personal/     # Local clutter (gitignored)
├── scripts/terminus        # Wrapper → terminus/scripts/terminus
├── docs → terminus/docs    # Symlink
├── prompt.md → terminus/prompt.md
├── AGENTS.md → terminus/AGENTS.md
├── templates → terminus/templates
└── .cursor/                # Rules, skills, hooks for Cursor
```

**Clean root policy:** all tasks live under `tasks/`. Run `./scripts/reorganize-tasks.sh` after imports. Personal files are archived to `terminus/_misc/personal/` (not pushed to GitHub).

---

## Cursor Integration

Rules auto-apply when editing task files. Invoke skills explicitly:

| Skill | Use when |
|-------|----------|
| `@terminus-create-task` | Scaffold and author a new task |
| `@terminus-review-task` | Peer review workflow |
| `@terminus-accuracy-review` | Deep review with `review-report.md` output |
| `@terminus-validate` | Run validation and interpret results |
| `@terminus-agent-test` | Oracle + agent difficulty testing |

---

## Documentation

**Start here:** [Documentation Index](docs/guidelines/INDEX.md)

| Topic | Doc |
|-------|-----|
| Pre-submit | [submission-checklist.md](docs/submission-checklist.md) |
| Creating tasks | [creating-task.md](docs/guidelines/creating-task.md) |
| Review process | [review-guidelines.md](docs/guidelines/review-guidelines.md) |
| Accuracy review | [prompt.md](prompt.md) → `review-report.md` |
| 55 portal checkboxes | [reviewer-checklist-ui.md](docs/reviewer-checklist-ui.md) |
| Rubrics | [rubrics.md](docs/guidelines/rubrics.md) |
| Dockerfile / images | [dockerfile.md](docs/guidelines/dockerfile.md) |
| Common errors | [common-errors.md](docs/guidelines/common-errors.md) |
| Milestones | [milestones.md](docs/guidelines/milestones.md) |
| Difficulty | [difficulty.md](docs/guidelines/difficulty.md) |
| FAQ | [faq.md](docs/faq.md) |

---

## Non-Negotiables (Edition 2)

- `allow_internet = false` in `task.toml`
- Digest-pin every `FROM` with `@sha256:<digest>`
- `tmux` + `asciinema` in Dockerfile
- Verifier deps baked in image — **no** runtime installs in `test.sh`
- No `solution/` or `tests/` copied into the Docker image
- Canonical `test.sh` reward block (always writes `reward.txt`)
- Rubric via platform UI: ≥3 negatives, ≤40 positive points (non-milestone)

See [terminus/AGENTS.md](terminus/AGENTS.md) for agent instructions.
