# Terminus 2nd Edition — Frequently Asked Questions

*Last updated: April 27, 2026*

Sections follow the task lifecycle: onboarding → building → testing → submitting → payment.

## Quick navigation

1. [Getting Started & Onboarding](#1-getting-started--onboarding)
2. [CLI Setup & API Keys](#2-cli-setup--api-keys)
3. [Task Structure: Milestones & File Layout](#3-task-structure-milestones--file-layout)
4. [Difficulty, Language & Codebase Size](#4-difficulty-language--codebase-size)
5. [Testing & Docker Troubleshooting](#5-testing--docker-troubleshooting)
6. [Submissions & Reviews](#6-submissions--reviews)
7. [Rubrics & Quality Checks](#7-rubrics--quality-checks)
8. [Compensation & Payment](#8-compensation--payment)
9. [Project Scope & Support](#9-project-scope--support)
10. [Known Issues & Workarounds](#10-known-issues--workarounds)

---

## 1. Getting Started & Onboarding

**How do I get started?** Review the project website, pinned posts in `#terminus-2nd-edition-submission` and `#terminus-2nd-edition-announcements`. Complete **Terminus-2nd-Edition-Assessment** on your Snorkel dashboard (80%+ to advance).

**Where is the assessment?** Dashboard → My Projects → Terminus-2nd-Edition-Assessment → Submissions node.

**Deadlines?** No — but the assessment has a **90-minute limit** once started.

**After passing?** Team contacts you next business day. $25 for completion + $25 bonus for 80%+.

**Training videos?** Three by Brady Nguyen: Understanding Terminus, Understanding Submissions, Understanding Revisions.

**Task gallery vs portal?** Gallery = browse tasks (docs site). Portal = upload (Snorkel Experts). Build locally from gallery, submit via portal.

**Wait for first review before another task?** No — submit multiple in parallel.

**Initialize a task:** `stb init my-task-name -p "terminus-2nd-edition" -t base`

---

## 2. CLI Setup & API Keys

**"Your account is not assigned to any Terminal-Bench project."** Complete assessment and wait for assignment.

**Key refresh limit (10)?** Ask admin in `#terminus-2nd-edition-submission` to reset.

**stb login works, keys refresh fails?** Regenerate API key in browser → `stb login` → retry. Escalate in Slack if persistent.

**API key for agent testing?** Project provides credentials via CLI — `stb keys refresh`. See CLI User Guide.

**Key exhausted mid-work?** `stb keys refresh`. Concurrent agent tests exhaust faster.

**stb upgrade 403?** Download link may be rotated — retry later. Verify with `stb --version`.

---

## 3. Task Structure: Milestones & File Layout

⚠️ **Most common revision source.** Harbor "milestones" = our "multi-step tasks."

### Milestone task (N milestones) — required zip contents

| Path | Requirement |
|------|-------------|
| `task.toml` | One `[[steps]]` per milestone (`name = "milestone_N"`), `[steps.agent].timeout_sec`, `[steps.verifier].timeout_sec`; `number_of_milestones` = step count |
| `environment/Dockerfile` | Shared environment |
| `steps/milestone_N/instruction.md` | Per-milestone prompt; M1 includes overall context |
| `steps/milestone_N/tests/test_mN.py` | `TestMilestoneN` class, scoped to that milestone |
| `steps/milestone_N/tests/test.sh` | Writes `/logs/verifier/reward.txt` |
| `steps/milestone_N/solution/solveN.sh` | Oracle for that milestone only |
| `steps/milestone_N/solution/solve.sh` | Thin wrapper → `solveN.sh` |
| Rubrics (UI) | One per milestone; ≥1 negative; 10–40 pts |

**No** root-level `instruction.md`, `tests/`, `solution/`, or `milestone_x.md`.

**Non-milestone:** `number_of_milestones = 0` (not 1).

**Old flat layout** (`milestone_x.md`, root `solve1.sh`) is replaced — use `steps/` layout.

**Older revisions:** New guidelines apply to **new submissions only**. If cached checks block revision, trivial change + resubmit or report in Slack.

See [milestones.md](guidelines/milestones.md).

---

## 4. Difficulty, Language & Codebase Size

### Difficulty

| Rule | Detail |
|------|--------|
| Python tasks | Must be **HARD** |
| Non-Python | **MEDIUM** or **HARD** |
| TRIVIAL | Pass rate too high — make harder |

**HARD** = ≤20% on **best OR worst** model (GPT-5.5, Claude Opus 4.8). See [difficulty.md](guidelines/difficulty.md).

**TRIVIAL tasks:** Single-bug, template-based — add complexity, edge cases, multi-file discovery.

**"Python requires HARD" on Go task:** Remove `python` from `languages` if only used for pytest infrastructure.

### Codebase size

Counted in `environment/` (excl. Dockerfile, docker-compose):

| Value | Files |
|-------|-------|
| `minimal` | 0–19 |
| `small` | 20+ |
| `large` | 200+ |

Case-sensitive: `"small"` not `"Small"`.

### Timeouts

- Agent timeout max: **1800s** (30 min)
- Concurrent agent tests: allowed; faster key exhaustion

---

## 5. Testing & Docker Troubleshooting

### Solvable vs passing a run

| Term | Meaning |
|------|---------|
| **Passing a run** | One run where **all** unit tests pass |
| **Solvable** | Across 10 runs, **each** unit test passes at least once (not necessarily same run) |

```bash
stb harbor run -m @openai/gpt-5.5 -p ./task -k 10
stb harbor run -m @anthropic/claude-opus-4-8 -p ./task -k 10
```

### Model strings

| Model | Correct | Wrong |
|-------|---------|-------|
| GPT | `@openai/gpt-5.5` | `gpt-5-5`, `@openai-tbench/gpt-5-5` |
| Claude | `@anthropic/claude-opus-4-8` | `claude-opus-4.8` |

### Tests

All verifiers = **Python pytest**. `test.sh` is bash wrapper only — no Java/Go test frameworks in test.sh.

### reward.txt not found

1. **Blocking entrypoint** — use `nginx` then `exec "$@"`, not `exec nginx -g 'daemon off;'`
2. **`set -e` early exit** — use `set -uo pipefail`, capture pytest rc, always write reward
3. **Missing** `mkdir -p /logs/verifier`

### verifier_did_not_run (all runs)

Missing **tmux** and/or **asciinema** in Dockerfile.

### Other

- `source "$HOME/.local/bin/env"` flagged as typo → **ignore** (false positive)
- Harbor build context = `environment/` only — move files into `environment/`
- `docker network prune` after many harbor runs

---

## 6. Submissions & Reviews

```bash
stb submissions list -p PROJECT_ID --show-folder-names
stb submissions view SUBMISSION_ID
stb submissions feedback SUBMISSION_ID
stb submissions download SUBMISSION_ID
```

| Status | Meaning | Can revise? |
|--------|---------|-------------|
| EVALUATION_PENDING | Automated checks | No |
| NEEDS_REVISION | Reviewer requested changes | Yes |
| REVIEW_PENDING | Awaiting human | No |
| ACCEPTED | Accepted | No |

**Daily limits:** 2 new/day (before 2 accepted); 5 new/day (2+ accepted). Revisions don't count. Resets midnight UTC.

**AutoEval reject despite local pass?** Resubmit; report IDs if persistent.

**"READY TO USE" but reviewer revises?** Automated review ≠ human approval.

**Review time:** Assessment ~24h; tasks 1–7 business days.

**Wrong/stale reviewer feedback?** Dispute with screenshots; escalate in Slack.

**New guidelines on old revisions?** Should not apply — flag if enforced.

---

## 7. Rubrics & Quality Checks

- ≥1 negative per milestone rubric (hard requirement)
- 10–40 pts per milestone / non-milestone total — **>40 is a main blocker (Revise)**, not optional polish
- Generate via "Generate Rubric(s)" without "Send to Reviewer" — appears during CI, edit in portal UI

---

## 8. Compensation & Payment

See Rate Schedule. Base + bonuses (codebase size, milestones, non-Python).

**Paid:** Friday-to-Thursday acceptance window → paid following Friday. **Accepted** only.

Terminus 1st Edition (deprecated Dec 2025): no payment for non-accepted tasks.

---

## 9. Project Scope & Support

- Project duration: at least ~1 month from mid-April 2026, possible extension
- No deadlines
- Office hours: pinned in `#terminus-2nd-edition-announcements`

| Channel | Use |
|---------|-----|
| `#terminus-2nd-edition-submission` | Questions, tech, submissions |
| `#terminus-2nd-edition-announcements` | Guideline updates |

---

## 10. Known Issues & Workarounds

| Issue | Workaround |
|-------|------------|
| AutoEval intermittent fail | Resubmit; report IDs |
| Rubrics disappear on revision | Report UUID |
| EVALUATION_PENDING stuck | Report UUID |
| Wrong task in reviewer feedback | Dispute + escalate |
| New rules on old revision | Trivial change + resubmit |
| Rubric `# Rubric N` parse fail | Manual review |
| Keys refresh limit | Admin reset |
| Non-Python flagged as Python | Remove python from languages |
| `source "$HOME/.local/bin/env"` flag | Ignore |
| Agent logs missing | Report UUID |
| Docker network limit | `docker network prune` |

---

## Local automation

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus review <task-dir> [--report entire-report.txt]
```

See [prompt.md](../prompt.md) for full accuracy review with UI checkbox output.
