# Terminal Bench Edition 2 — Full Reviewer Checklist

Severity: **High** = must pass (revision if failed) · **Medium** = fail multiple → revision · **Low** = note only

Quick reference: [reviewer-checklist.md](reviewer-checklist.md)

## Severity Rules

| Level | Review action |
|-------|---------------|
| High | Any failure → do not accept |
| Medium | Multiple failures → revision; single → accept with note |
| Low | Accept; mention in revision if already revising |

---

## Instruction Prompt

| Criterion | Severity |
|-----------|----------|
| Concise (1 sentence – 3 paragraphs; human tone; no emoji/heavy markdown) | High |
| Well specified (clear goal; reject edge-case laundry lists) | High |
| Interesting / useful | High |
| No hints or stepwise solve instructions | High |
| Environment has no hidden walkthroughs/hints (README, comments, TODOs) | High |
| Spec/docs realistic; no instruction-length loophole | High |
| Unique vs TB2/TB3/Edition 1 | High |
| Absolute paths only | High |
| No canary string | Medium |
| Task name not in instruction.md | Medium |

## Environment

| Criterion | Severity |
|-----------|----------|
| No web content fetch (except packages) | High |
| Pinned dependency versions (packages) | High |
| Context stays in `environment/` only | High |
| No ground truth / solution answers in env | High |
| No privileged mode / dangerous capabilities | High |
| Compose doesn't conflict with Harbor mounts (`/logs/`, `/tests/`, `/solution/`) | High |
| No AI scaffolding filenames (CLAUDE.md, skills.md) | High |
| Every FROM digest-pinned | High |
| Canonical base OR credible non-canonical justification | High |
| Build context ≤ 100 MiB total, ≤ 50 MiB per file | High |
| Clean apt usage (single transaction, cleanup) | Medium |
| `.dockerignore` for non-trivial env | Medium |
| Avoid Dockerfile heredocs for source | Low |

## Oracle Solution

| Criterion | Severity |
|-----------|----------|
| Passes consistently (no randomness/latency flakes) | High |
| No internet/downloads at runtime | High |
| Solves all instruction requirements (not hardcoded) | High |

## Verifiers

| Criterion | Severity |
|-----------|----------|
| reward.txt always written; canonical end (no trailing exit required) | High |
| Same logic for oracle and agent (no conditional mode) | High |
| test.sh no network installs | High |
| Binary rewards only (0/1) | High |
| Tests aligned with instructions | High |
| Verify correctness, not just format | High |

## Rubrics

**Source:** Platform rubric from the submission export (`entire-report.txt`, Snorkel download, or `--rubric`). Tasks do not ship `rubric.txt`; absence in the task folder is not grounds to skip rubric review.

| Criterion | Severity |
|-----------|----------|
| No references to /tests/ or pytest results | High |
| No references to task.toml or instruction.md | High |
| ≥3 negative penalties | High |
| Scores ±1, 2, 3, 5 only (no 4) | High |
| Format: `Agent …, ±N`; milestone `# Rubric N` headers | High |
| Criteria detailed and precise | High |
| ≥1 negative per milestone rubric block | Medium |
| Score magnitude matches importance (±5 critical) | Medium |
| Positive phrasing with negative scores for bad behavior | Medium |
| No oracle/NOP mentions | Medium |
| 10–40 pts per milestone (or non-milestone total); **>40 = main blocker** | High |

## Task Structure

| Criterion | Severity |
|-----------|----------|
| All required files (regular vs milestone layout) | High |
| Clean parent directory (no jobs/, stray README) | Low |

## Task Metadata

| Criterion | Severity |
|-----------|----------|
| Complete task.toml fields (see [task-requirements.md](task-requirements.md)) | High |
| `custom_docker_compose=true` / `is_multi_container=true` when applicable | High |
| Tags, languages, category, subcategories match content | Medium |

## Milestone Tasks

| Criterion | Severity |
|-----------|----------|
| ≥2 milestones | High |
| `steps/milestone_N/` layout; no root instruction/tests/solution | High |
| One `[[steps]]` per milestone with timeouts | High |
| `solveN.sh` + `solve.sh` wrapper per milestone | High |
| `test_mN.py` (`TestMilestoneN`) + test.sh per milestone | High |
| Per-milestone instruction scoped correctly | Medium |

---

## Review Actions

- **Approve** — all High pass; Medium/Low per severity rules
- **Request Changes** — specific file, line, fix
- **Decline** — too easy, duplicate, fundamental flaw

See [review-guidelines.md](guidelines/review-guidelines.md) · [agent-review.md](guidelines/agent-review.md)
