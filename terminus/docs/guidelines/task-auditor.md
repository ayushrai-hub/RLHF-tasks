# Task Quality Auditor

Read-only automated evaluation of Terminus Edition 2 tasks against the **55-item reviewer portal checklist**.

## Commands

```bash
# Full checklist audit (writes <task-dir>/audit-report.md)
./scripts/terminus audit <task-dir>

# With submission export for rubric (#32–39) and agent stats (#54)
./scripts/terminus audit <task-dir> --report entire-report.txt

# JSON output
./scripts/terminus audit <task-dir> --json

# Included in pre-submit pipeline
./scripts/terminus check-all <task-dir>
```

## Architecture

The auditor is **modular** and **read-only**:

| Module | Role |
|--------|------|
| `scripts/task_auditor.py` | CLI entry point |
| `scripts/task_audit/auditor.py` | Orchestrator — runs all checks, computes verdict |
| `scripts/task_audit/context.py` | Loads task artifacts once (instruction, Dockerfile, tests, toml, export) |
| `scripts/task_audit/registry.py` | Checklist definitions + `@register` decorator |
| `scripts/task_audit/rules/*.py` | One module per checklist section (#1–12 instruction, #13–20 env, …) |
| `scripts/task_audit/heuristics.py` | Structured heuristics for subjective items |
| `scripts/task_audit/report.py` | Markdown/JSON report generation |
| `scripts/validate_task.py` | Structural CI checks (reused, not duplicated) |
| `scripts/rubric_points.py` | Platform rubric positive-point cap (reused) |

### Adding a new checklist item

1. Add the item to `CHECKBOXES` in `registry.py`.
2. Implement `@register(id, section, label)` in the appropriate `rules/*.py` file.
3. Return a `CheckResult` via helpers in `rules/_helpers.py`.

No changes to the orchestrator or report format are required.

## Status model

Each of the 55 items receives exactly one status:

| Status | Meaning |
|--------|---------|
| **PASS** | Objective evidence shows compliance |
| **FAIL** | Objective or high-confidence heuristic violation |
| **NOT APPLICABLE** | Item does not apply (e.g. milestones #46–49 on regular tasks) |
| **CANNOT DETERMINE** | Requires external data or human judgment |

### Evaluation kinds

| Kind | Examples |
|------|----------|
| `objective` | Digest-pinned FROM, reward.txt path, allow_internet=false |
| `heuristic` | Concise instruction, natural tone, category fit, spec↔test alignment |
| `external` | Oracle flake check (needs harbor run), rubric without export, fairness (#55) |

## Verdicts

| Verdict | When |
|---------|------|
| **APPROVED** | No blocking FAILs; objective checks pass |
| **APPROVED WITH WARNINGS** | Non-blocking heuristic FAILs only |
| **REQUIRES CHANGES** | Any blocking FAIL (e.g. rubric >40, unpinned FROM, tests in image) |
| **REJECTED** | Multiple critical structural failures |

Exit code: `0` for APPROVED / APPROVED WITH WARNINGS; `1` for REQUIRES CHANGES / REJECTED.

## Report sections

`audit-report.md` contains:

1. Executive summary (PASS / FAIL / N/A / CANNOT DETERMINE counts)
2. Detailed checklist table (all 55 items with evidence)
3. Critical issues (blocking failures)
4. Warnings (non-blocking heuristic failures)
5. Suggestions (concrete fixes per failed item)
6. Items requiring manual review
7. `validate_task.py` errors (if any)

## Relationship to other tools

| Tool | Purpose |
|------|---------|
| `terminus validate` | Fast CI structural checks (errors/warnings) |
| `terminus audit` | Full 55-item checklist with verdict |
| `terminus review` | Portal-oriented `review-report.md` + CHECK/UNCHECK lists (uses `review_checklist.py`) |

**Authors:** run `validate` + `audit` before submit.  
**Reviewers:** run `audit --report entire-report.txt`, then enrich `review-report.md` per `prompt.md`.

## Heuristic items (manual follow-up)

These items are evaluated with structured heuristics but still need human confirmation when marked CANNOT DETERMINE or low-confidence FAIL:

- #2 natural tone, #8 interesting, #9 unique
- #17 ground truth in env (comments/docs)
- #21 oracle flakes (run `./scripts/terminus oracle`)
- #27 spec↔test alignment (full matrix in manual review)
- #49 milestone test scope
- #51–#52 anti-cheat fairness
- #55 difficulty fairness

## Rubric checks (#32–39)

Rubrics live on the **submission platform**, not in the task zip. Provide:

- `--report entire-report.txt` (preferred), or
- `--rubric rubric.txt` / `task-dir/rubric.txt`

Without a rubric source, items #32–39 are **CANNOT DETERMINE** (not N/A).

Positive point cap: **>40** on non-milestone tasks is a **blocking FAIL** on #35.

## Recent fixes (vs. prior `review_checklist.py`)

- **AST-based docstrings** (#31) — handles `def test_foo(tmp_path: Path) -> None:` (fixes false positives from regex)
- **reward.txt mkdir** (#24) — mkdir optional; Harbor pre-creates `/logs/verifier`
- **Rubric meta-reference** (#38) — detects `instruction.md`, `task.toml`, “constraint from instructions”
- **Category fit** (#44) — heuristic taxonomy signals, flags sysadmin on code-repair tasks
- **Concise instruction** (#1) — bullet lists excluded from prose-paragraph count
