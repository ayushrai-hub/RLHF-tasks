# Terminus Automation System

Automation toolkit for **Project Terminus (Edition 2)** — task authoring, local validation, agent testing, and peer review.

## Quick Start

```bash
# 1. Install prerequisites (once)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install snorkelai-stb --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html --python ">=3.12"
uv tool install "harbor @ https://snorkel-public.s3.us-west-2.amazonaws.com/harbor/harbor-0.5.0%2Bpromptfix5-py3-none-any.whl" --python 3.13

# 2. Authenticate
stb login
export OPENAI_API_KEY=<your-portkey-api-key>
export OPENAI_BASE_URL=https://api.portkey.ai/v1

# 3. Initialize a task
stb init my-task -p "Terminus-2nd-Edition" -t base

# 4. Validate locally before submit
./scripts/terminus validate ./tasks/my-task
./scripts/terminus check-all ./tasks/my-task

# Reorganize after downloading tasks or ZIPs
./scripts/reorganize-tasks.sh
```

## What's Included

| Component | Path | Purpose |
|-----------|------|---------|
| **CLI** | `scripts/terminus` | Validate, test oracle, run agents, package ZIP |
| **Validator** | `scripts/validate_task.py` | CI-aligned local checks |
| **Cursor Rules** | `.cursor/rules/terminus-*.mdc` | Auto-context for authoring & review |
| **Cursor Skills** | `.cursor/skills/terminus-*/` | Workflows: create, review, validate, test |
| **Hooks** | `.cursor/hooks.json` | Post-edit validation on task files |
| **Docs** | `docs/` | Condensed guidelines, checklist, rubric template |

## Common Commands

```bash
# Validate task structure & CI rules
./scripts/terminus validate <task-dir>

# Full pre-submit pipeline
./scripts/terminus check-all <task-dir>
./scripts/terminus review <task-dir> --report entire-report.txt  # writes review-report.md
./scripts/terminus checklist <task-dir>
./scripts/terminus ci-check <task-dir>
./scripts/terminus llmaj-check <task-dir>

# Oracle solution test
./scripts/terminus oracle <task-dir>

# Agent difficulty testing
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 3
./scripts/terminus agent <task-dir> --model claude-opus-4-8 --runs 3

# Create submission ZIP (files inside folder, not the folder itself)
./scripts/terminus zip <task-dir>

# Submit via CLI
stb submissions create <task-dir> -p "Terminus-2nd-Edition" --time 120
```

## Difficulty Targets

| Tier | Criteria |
|------|----------|
| **Hard** | ≤20% on best OR worst model |
| **Medium** | 20–60% on worst model |
| **Easy** | 60–80% on worst model |
| **Rejected** | >80% on worst model |

Benchmark models: **GPT-5.5** and **Claude Opus 4.8**.

## Cursor Integration

Open this repo alongside your task folder in Cursor. Rules auto-apply when editing `instruction.md`, `task.toml`, `environment/`, or `tests/`. Invoke skills explicitly:

- `@terminus-create-task` — scaffold and author a new task
- `@terminus-review-task` — peer review workflow
- [@terminus-accuracy-review](prompt.md) — writes `review-report.md` (blockers, proof, CHECK/UNCHECK #s, portal note)
- `@terminus-validate` — run validation and interpret results
- `@terminus-agent-test` — oracle + agent difficulty testing

## Project Structure

```
.
├── tasks/              # All active Terminus task folders (see tasks/README.md)
├── reviews/            # External reports (entire-report.txt copies per review)
├── _incoming/zips/     # Submission ZIP archives
├── _backup/copies/     # Duplicate task folders kept for safety
├── _misc/personal/     # Unrelated local files (not Terminus tasks)
├── .cursor/
│   ├── rules/          # Authoring & review rules
│   ├── skills/         # Agent workflows
│   └── hooks/          # Post-edit validation
├── docs/
│   ├── guidelines/INDEX.md       # Full doc hub
│   ├── submission-checklist.md
│   ├── task-requirements.md
│   └── ...
├── prompt.md                     # Review prompt → outputs review-report.md
├── templates/review-report.template.md
├── scripts/
│   ├── terminus                  # Main CLI
│   ├── reorganize-tasks.sh       # Consolidate loose tasks/files
│   └── validate_task.py
└── templates/          # Reference skeletons
```

**Reorganize** after downloading or extracting tasks:

```bash
./scripts/reorganize-tasks.sh
```

Task paths in commands use `tasks/<name>/`, e.g. `./scripts/terminus validate tasks/stellar-kiosk-ledger11.`

## References

**Start here:** [Documentation Index](docs/guidelines/INDEX.md)

- [Submission Checklist](docs/submission-checklist.md)
- [Creating a Task](docs/guidelines/creating-task.md)
- [CI Checks](docs/guidelines/ci-checks.md)
- [Rubrics](docs/guidelines/rubrics.md)
- [Prompt Styling](docs/guidelines/prompt-styling.md)
- [Milestones](docs/guidelines/milestones.md)
- [Dockerfile / Canonical Images](docs/guidelines/dockerfile.md)
- [Task Type Taxonomy](docs/task-type-taxonomy.md)
- [Task Subtypes](docs/task-subtypes.md)
- [Difficulty](docs/guidelines/difficulty.md)
- [LLMaJ Checks](docs/guidelines/llmaj-checks.md)
- [Review Guidelines](docs/guidelines/review-guidelines.md)
- [Full Reviewer Checklist](docs/reviewer-checklist-full.md)
- [**Task Accuracy Review**](prompt.md) — generates `review-report.md`
- [Review Report Template](templates/review-report.template.md)
- [Quality Guidelines](docs/guidelines/quality-guidelines.md)
- [Common Errors](docs/guidelines/common-errors.md)
- [Long Context Checklist](docs/guidelines/long-context-checklist.md)
- [Agent Review](docs/guidelines/agent-review.md)
- [Oracle Agent](docs/guidelines/oracle-agent.md)
- [Agent Testing](docs/guidelines/agent-testing.md)
