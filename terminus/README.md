# Terminus Hub

Central directory for Terminus Edition 2 automation, documentation, review artifacts, and archives. The **repo root** stays clean — all tasks live in [`tasks/`](../tasks/).

## Directory Map

```
terminus/
├── AGENTS.md              # Agent instructions (symlinked at repo root)
├── prompt.md              # Accuracy review prompt → review-report.md
├── docs/                  # Guidelines, checklists, taxonomy (symlinked at root)
├── templates/             # review-report.template.md
├── scripts/
│   ├── terminus           # Main CLI (validate, audit, review, oracle, agent, zip)
│   ├── reorganize-tasks.sh
│   ├── rename-tasks.py    # UUID → canonical slug renaming
│   ├── generate-tasks-index.py
│   ├── validate_task.py
│   ├── task_audit/        # 55-item read-only auditor
│   └── rubric_points.py   # Sum platform rubric positive points
├── jobs/                  # Harbor job run history (additional to root jobs/)
├── reviews/               # Platform submission exports
│   └── entire-report.txt  # Symlinked at repo root
├── _incoming/
│   ├── zips/              # Archived submission ZIPs (extracted into tasks/)
│   └── submissions/       # Unpacked submission log folders
├── _backup/copies/        # Duplicate task folders (gitignored)
├── _misc/personal/        # Unrelated local files (gitignored)
└── _other/                # Misc review artifacts (gitignored)
```

## Repo Root Layout

```
.
├── tasks/                 # 21 curated task folders — canonical library
├── jobs/                  # Harbor run outputs at repo root
├── terminus/              # This hub
├── scripts/terminus       # Wrapper → terminus/scripts/terminus
├── docs → terminus/docs
├── prompt.md → terminus/prompt.md
├── AGENTS.md → terminus/AGENTS.md
├── templates → terminus/templates
└── .cursor/               # Rules, skills, hooks
```

## Common Commands

Run from repo root:

```bash
# Validate and pre-submit
./scripts/terminus validate tasks/<name>
./scripts/terminus check-all tasks/<name>

# Review pipeline
./scripts/terminus audit tasks/<name> --report terminus/reviews/entire-report.txt
./scripts/terminus review tasks/<name> --report terminus/reviews/entire-report.txt

# Testing
./scripts/terminus oracle tasks/<name>
./scripts/terminus agent tasks/<name> --model gpt-5.5 --runs 3

# Housekeeping
./scripts/reorganize-tasks.sh
```

## Reorganize Script

[`scripts/reorganize-tasks.sh`](scripts/reorganize-tasks.sh) is the main housekeeping tool. It:

1. **Archives personal clutter** — moves `assignment-tirios/`, `new/`, `sddnew/`, docs, media to `_misc/personal/`
2. **Consolidates tasks** — moves loose task folders from repo root into `tasks/`
3. **Dedupes** — drops root copies when `tasks/<name>` already exists
4. **Extracts ZIPs** — unpacks submission archives from root and `_incoming/zips/`
5. **Renames UUID folders** — shortens `*_submission_*` names via `rename-tasks.py`
6. **Regenerates index** — updates `tasks/README.md`

Edit `ROOT_TASKS` in the script to pin specific tasks at repo root during active work.

## Review Artifacts

| File | Purpose |
|------|---------|
| `reviews/entire-report.txt` | Snorkel submission export — agent stats, LLMaJ, platform rubric |
| `tasks/<name>/review-report.md` | Portal review output (CHECK/UNCHECK, blockers, portal note) |
| `tasks/<name>/audit-report.md` | 55-item automated audit |

Parse `entire-report.txt` sections per [submission-export-format.md](docs/guidelines/submission-export-format.md) before adjudicating.

## Documentation Index

Full reference: [docs/guidelines/INDEX.md](docs/guidelines/INDEX.md)

Key entry points:

- [submission-checklist.md](docs/submission-checklist.md) — pre-submit
- [reviewer-checklist-ui.md](docs/reviewer-checklist-ui.md) — 55 portal checkboxes
- [prompt.md](prompt.md) — accuracy review procedure
- [rubrics.md](docs/guidelines/rubrics.md) — platform rubric rules
- [task-auditor.md](docs/guidelines/task-auditor.md) — automated audit reference

## Gitignored Paths

These stay local and are not pushed to GitHub:

- `_backup/`, `_incoming/`, `_misc/`, `_other/`
- `AGENTS.md` symlink at root (real file is here)
- `entire-report.txt` symlink at root (real file in `reviews/`)
