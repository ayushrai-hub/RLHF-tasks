---
name: terminus-validate
description: Run local CI-aligned validation on Terminus task folders. Use when validating, checking, linting, or pre-submit verifying a Terminus task before submission or during review.
---

# Terminus Validate

## Run Validation

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus check-all <task-dir>
./scripts/terminus ci-check <task-dir>
```

## What Gets Checked

| Check | Severity |
|-------|----------|
| Required files present | Error |
| task.toml version + allow_internet=false | Error |
| Dockerfile digest pins on all FROM | Error |
| tmux + asciinema in Dockerfile | Error |
| No COPY solution/ or tests/ | Error |
| test.sh reward block present | Error |
| No runtime installs in test.sh | Error |
| Test docstrings (module + functions) | Warning |
| instruction.md absolute paths | Warning |
| tags count 3-6 | Warning |
| .dockerignore for large env | Warning |
| Unpinned pip packages | Warning |
| AI scaffolding filenames | Error |
| environment/ size limits | Error |
| Milestone structure consistency | Error |
| Valid category (9 types) | Error |
| Milestone task.toml structure | Error |
| TestMilestoneN class in test_mN.py | Warning |
| Prompt styling anti-patterns | Warning |
| Canonical base image digests | Warning/Info |
| LLMaJ alignment | Warning |
| Rubric format (via rubric-validate) | Error |

## Interpreting Output

- **ERROR** — must fix before submission (CI will block)
- **WARNING** — likely flagged by reviewers; fix if possible
- **INFO** — suggestions for quality

## Fix Loop

1. Run validate
2. Fix all ERRORs
3. Re-run until clean
4. Run oracle: `./scripts/terminus oracle <task-dir>`

## Reference

Validation logic: `scripts/validate_task.py`
