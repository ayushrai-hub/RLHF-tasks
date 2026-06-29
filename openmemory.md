# Airdawgs-review-Terminus2 — OpenMemory Guide

## Overview

Automation toolkit for **Project Terminus Edition 2** (Snorkel Expert Platform). Helps coding experts create, validate, test, and review Terminal-Bench-style benchmark tasks for AI coding agents.

## Architecture

```
tasks/                   # All active task folders (index: tasks/README.md)
stats-plan-resume-skew/  # Pinned at repo root (excluded from tasks/ by reorganize script)
reviews/                 # External platform reports (entire-report.txt)
_incoming/zips/          # Submission ZIP archives
_backup/copies/          # Archived duplicate task folders
_misc/personal/          # Unrelated local files
CLI (scripts/terminus)
  ├── validate_task.py   # CI-aligned local checks
  ├── reorganize-tasks.sh # Consolidate root clutter into tasks/
  ├── checklist/ci-check # Pre-submit workflow
  ├── oracle/agent/zip   # Harbor + stb wrappers
Cursor Integration
  ├── .cursor/rules/     # Auto-context per file type
  ├── .cursor/skills/    # Workflows: create, review, validate, test
  └── .cursor/hooks/     # Post-edit validation
docs/
  ├── submission-checklist.md
  ├── task-type-taxonomy.md
  └── ...
```

## User Defined Namespaces

- (Leave blank - user populates)

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Terminus CLI | `scripts/terminus` | validate, checklist, ci-check, oracle, agent, zip |
| Validator | `scripts/validate_task.py` | Local CI + docstring/path/tag checks |
| Submission Checklist | `docs/submission-checklist.md` | Pre-submit verification |
| Task Requirements | `docs/task-requirements.md` | Full structural requirements |
| Create Skill | `.cursor/skills/terminus-create-task/` | New task workflow |
| Review Skill | `.cursor/skills/terminus-review-task/` | Review workflow |

## Patterns

- **Doc hub:** `docs/guidelines/INDEX.md`
- **Validate before submit**: `./scripts/terminus check-all <task-dir>`
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
