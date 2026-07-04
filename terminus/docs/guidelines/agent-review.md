# Agent Review Reference

Automated static review via **Claude Code** (does not block submission — advisory).

## What It Does

Static analysis of task files — no container build or execution. Produces structured report by severity.

## Review Steps

1. **File structure** — required files for regular vs milestone vs multi-container
2. **task.toml** — version 2.0, metadata, timeouts, `[[steps]]` for milestones
3. **instruction.md** — clarity, success criteria, output format
4. **Dockerfile** — WORKDIR, deps, no solution/tests in image
5. **solve.sh** — shebang, `set -euo pipefail`, completeness
6. **test_outputs.py** — pytest, assertions, edge cases, docstrings
7. **test.sh** — pytest, reward.txt, no runtime installs
8. **Quality** — behavior coverage, anti-cheating, schema, pinning, typos

## Quality Control (Critical)

| Rule | Detail |
|------|--------|
| No latency-based tests | Hardware-dependent thresholds banned |
| Identical oracle/agent testing | No conditional verifier logic by mode |
| Multi-container tagging | `is_multi_container=true`, `custom_docker_compose=true` |
| No web data fetching | Pre-download into `environment/` |
| Reserved directories | Don't create `/tests`, `/solution`, `/oracle` in Dockerfile |
| Reward file required | Always write `/logs/verifier/reward.txt` |
| Env var defaults | `$TEST_DIR` needs default if used |

## Severity

| Level | Action |
|-------|--------|
| ❌ Critical | Must fix — invalid/unfair task |
| ⚠️ Warning | Should fix — best practices |
| 💡 Suggestion | Optional improvement |

## Report Format

```
### Review Report: [task-name]
**Status:** ✅ PASS | ⚠️ WARNING | ❌ FAIL

#### Critical Issues ❌
#### Warnings ⚠️
#### Suggestions 💡
**Recommendation:** READY TO USE | NEEDS FIXES | REQUIRES REVISION
```

## Common Critical: Reward File

**Bad** — exit before reward block:
```bash
python -m pytest /tests/test_outputs.py -rA
exit $rc   # reward.txt never written
```

**Good** — canonical reward block as script end:
```bash
python -m pytest /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
```

## Acting on Feedback

1. Fix **Critical** first
2. Then **Warnings**
3. Consider **Suggestions**

Cross-check with [reviewer-checklist-full.md](../reviewer-checklist-full.md).
