# Terminus Hub

All Terminus automation, docs, archives, and review artifacts live here. The **repo root** stays clean for active task work.

## Layout

```
terminus/
├── AGENTS.md              # Agent instructions (symlinked at repo root)
├── prompt.md              # Accuracy review prompt (symlinked at repo root)
├── docs/                  # Guidelines, checklists, taxonomy (symlinked at repo root)
├── templates/             # Review report templates (symlinked at repo root)
├── scripts/
│   ├── terminus           # Main CLI
│   ├── reorganize-tasks.sh
│   ├── validate_task.py
│   ├── task_audit/        # 55-item read-only auditor
│   └── ...
├── jobs/                  # CI / batch job configs
├── reviews/               # Platform reports (entire-report.txt, etc.)
├── _incoming/
│   ├── zips/              # Submission ZIP archives
│   └── submissions/       # Unpacked submission logs
├── _backup/copies/        # Duplicate task folders
├── _misc/personal/        # Unrelated local files
└── _other/                # Misc review artifacts
```

## Repo root (workspace)

```
.
├── tasks/                 # Archived / bulk task library (see tasks/README.md)
├── <active-task>/         # Current review or authoring work (moved here by reorganize)
├── terminus/              # This hub
├── scripts/terminus       # Wrapper → terminus/scripts/terminus
├── docs → terminus/docs   # Symlink
├── prompt.md → …          # Symlink
└── .cursor/               # Rules, skills, hooks
```

## Commands

From repo root (wrappers keep old paths working):

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus check-all <task-dir>
./scripts/terminus audit <task-dir>
./scripts/terminus review <task-dir> --report entire-report.txt
./scripts/reorganize-tasks.sh
```

Task paths: `tasks/<name>/` for archived tasks, or a folder at repo root while actively working.

## Reorganize

`./scripts/reorganize-tasks.sh` moves loose task folders into `tasks/`, archives ZIPs to `terminus/_incoming/zips/`, and syncs personal clutter into `terminus/_misc/`. Edit `ROOT_TASKS` in the script to pin specific tasks at repo root.
