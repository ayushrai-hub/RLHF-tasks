# Airdawgs-review-Terminus2 — OpenMemory Guide

## Overview

Automation toolkit for **Project Terminus Edition 2** (Snorkel Expert Platform). Helps coding experts create, validate, test, and review Terminal-Bench-style benchmark tasks for AI coding agents.

## Architecture

```
tasks/                   # All task folders (index: tasks/README.md)
terminus/                # Terminus hub (docs, scripts, archives, reviews)
  ├── docs/              # Guidelines, checklists (symlinked at repo root)
  ├── scripts/terminus   # CLI (wrapper at scripts/terminus)
  ├── reviews/           # Platform reports (entire-report.txt)
  ├── _incoming/zips/    # Submission ZIP archives
  ├── _backup/copies/    # Archived duplicate task folders
  └── _misc/personal/    # Unrelated local files
Cursor Integration
  ├── .cursor/rules/     # Auto-context per file type
  ├── .cursor/skills/    # Workflows: create, review, validate, test
  └── .cursor/hooks/     # Post-edit validation
```

## User Defined Namespaces

- (Leave blank - user populates)

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Terminus CLI | `scripts/terminus` → `terminus/scripts/terminus` | validate, audit, checklist, ci-check, oracle, agent, zip |
| Validator | `terminus/scripts/validate_task.py` | Local CI + docstring/path/tag checks |
| Task Auditor | `terminus/scripts/task_audit/` | Read-only 55-item checklist audit |
| Submission Checklist | `terminus/docs/submission-checklist.md` | Pre-submit verification |
| Task Requirements | `docs/task-requirements.md` | Full structural requirements |
| Create Skill | `.cursor/skills/terminus-create-task/` | New task workflow |
| Review Skill | `.cursor/skills/terminus-review-task/` | Review workflow |

## Patterns

- **Doc hub:** `docs/guidelines/INDEX.md`
- **Validate before submit**: `./scripts/terminus check-all <task-dir>` now runs validate + audit + checklist
- **Accuracy review commands**: `prompt.md` requires running user-provided exact commands first, then baseline `validate`, `audit`, and `review`; static simulation is only a fallback when commands/tooling are unavailable.
- **Rubric lint**: `./scripts/terminus rubric-validate rubric.txt --milestones N`
- **LLMaJ guide:** `docs/guidelines/llmaj-checks.md`
- **Full reviewer checklist:** `docs/reviewer-checklist-full.md`
- **Canonical images**: `docs/guidelines/dockerfile.md` (exact digests)
- **Difficulty models**: GPT-5.5 + Claude Opus 4.8; reject if >80% worst-model pass rate
- **allow_internet = false**: all deps in Dockerfile
- **Digest-pin all FROM images** with @sha256:
- **Rubric**: platform UI only; ≥3 negative rewards
- **Tags**: 3-6 keywords in task.toml
- **Test docstrings**: required on module and each test function

## External Tools

- `stb` (snorkelai-stb) — submissions, reviews, harbor wrapper
- `harbor` — oracle/agent runs, CI checks, container env
- Docker Desktop v24+
