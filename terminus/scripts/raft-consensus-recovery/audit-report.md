# Task Quality Audit: `raft-consensus-recovery`

**Generated:** 2026-07-03 09:41 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/scripts/raft-consensus-recovery`  
**Layout:** regular  
**Verdict:** **REJECTED**

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| PASS | 15 |
| FAIL | 20 |
| NOT APPLICABLE | 4 |
| CANNOT DETERMINE | 16 |

**Validator:** 1 error(s), 0 warning(s)

---

## 2. Detailed Checklist Report

| # | Status | Kind | Description | Explanation | Evidence |
|---|--------|------|-------------|-------------|----------|
| 1 | FAIL | objective | Instruction is concise (1 sentence to 3 paragraphs max) | Missing instruction.md | instruction.md |
| 2 | FAIL | objective | Instruction reads like a natural prompt, not a spec document | Missing instruction.md | — |
| 3 | FAIL | objective | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | Missing instruction | — |
| 4 | PASS | objective | No step by step instructions telling the agent what developer steps to take | No step-by-step walkthrough patterns | — |
| 5 | PASS | heuristic | No hints or solving strategies (describes WHAT to build, not HOW) | No explicit hint language; limited HOW directives. | — |
| 6 | PASS | objective | No design doc style tables mapping inputs to outputs | No design-doc tables | — |
| 7 | FAIL | objective | Instruction is well specified (goal is clear and obvious) | Missing instruction | — |
| 8 | CANNOT DETERMINE | external | Instruction is interesting (useful to some group of developers) | Subjective quality — requires human reviewer judgment. | — |
| 9 | CANNOT DETERMINE | external | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Corpus uniqueness cannot be verified from task artifacts alone. | — |
| 10 | FAIL | objective | All paths in instruction are absolute (not relative) | No absolute paths detected | — |
| 11 | PASS | objective | Task name does not appear in instruction.md | Task name not in instruction | — |
| 12 | PASS | objective | No canary string in instruction.md | No canary patterns | — |
| 13 | FAIL | objective | Dockerfile does not grab content from the web (other than packages) | Missing environment/ | environment/ |
| 14 | FAIL | objective | All Python/pip dependencies use pinned versions with == (no ranges) | Missing Dockerfile | — |
| 15 | FAIL | objective | Base Docker image is pinned by digest (@sha256:...) | No FROM statements | environment/Dockerfile |
| 16 | PASS | objective | Environment does not use context from outside the environment directory | No COPY outside environment/ | — |
| 17 | CANNOT DETERMINE | external | Environment does not contain solution or ground truth answers | No obvious solution files; manual review needed for comment/doc leakage. | — |
| 18 | PASS | objective | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/SYS_ADMIN/docker.sock | — |
| 19 | PASS | objective | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | No docker-compose.yaml | — |
| 20 | FAIL | objective | Verifier deps baked in image; test.sh does NOT install packages at runtime | Dockerfile missing agent runtime tools (also missing: tmux, asciinema) | — |
| 21 | FAIL | objective | Oracle passes consistently (no flaky behavior) | Missing oracle solution | — |
| 22 | FAIL | objective | Oracle does not require internet or downloading packages | Missing solve.sh | — |
| 23 | FAIL | objective | Oracle is reflective of instruction (real implementation, not hardcoded) | Missing solve.sh | — |
| 24 | FAIL | objective | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing test.sh | — |
| 25 | PASS | objective | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No /oracle conditional logic | — |
| 26 | PASS | objective | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward pattern | — |
| 27 | CANNOT DETERMINE | external | All tests are aligned with instructions (do not test unstated requirements) | Missing instruction or test files for alignment check. | — |
| 28 | FAIL | objective | Tests check for correctness, not just format | Missing test_outputs.py | — |
| 29 | PASS | objective | Tests verify behavior, not implementation (no grepping source code) | No obvious implementation grep in tests | — |
| 30 | PASS | heuristic | No brittle exact string matching where flexible checks would work | No long brittle string equality patterns detected. | — |
| 31 | FAIL | objective | Tests have informative names or docstrings | Missing test_outputs.py | — |
| 32 | CANNOT DETERMINE | external | Rubrics contain at least 3 negative penalty criteria | No rubric in task folder or --report export. | — |
| 33 | CANNOT DETERMINE | external | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | No rubric available. | — |
| 34 | CANNOT DETERMINE | external | Each rubric criterion is one line starting with Agent, comma, then score | No rubric available. | — |
| 35 | CANNOT DETERMINE | external | Rubric criteria are detailed and precise | No rubric available. | — |
| 36 | CANNOT DETERMINE | external | Rubric criteria use positive language (not Agent does not do X, +1) | No rubric available. | — |
| 37 | CANNOT DETERMINE | external | Rubric does not reference testing logic or /tests/ directory | No rubric available. | — |
| 38 | CANNOT DETERMINE | external | Rubric does not reference metadata (task.toml) or instruction.md | No rubric available. | — |
| 39 | CANNOT DETERMINE | external | Rubric does not mention oracle or NOP runs | No rubric available. | — |
| 40 | FAIL | objective | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/scripts/raft-consensus-recovery | task.toml |
| 41 | PASS | objective | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | No obvious stray parent files | — |
| 42 | FAIL | objective | author_name and author_email fields present in task.toml | Missing task.toml | — |
| 43 | FAIL | objective | All other required metadata fields present | Missing task.toml | — |
| 44 | FAIL | objective | Tags, languages, categories are applicable to the task | Missing task.toml | — |
| 45 | FAIL | objective | Difficulty matches observed agent pass rates | Missing difficulty in task.toml | — |
| 46 | NOT APPLICABLE | objective | steps/ layout present with per-milestone files (not root instruction/tests/solution) | Not a milestone task (number_of_milestones = 0) | — |
| 47 | NOT APPLICABLE | objective | Each milestone has a corresponding solveN.sh file | Not a milestone task | — |
| 48 | NOT APPLICABLE | objective | Each milestone has a corresponding test_mN.py file | Not a milestone task | — |
| 49 | NOT APPLICABLE | objective | Each milestone test file is scoped only to that milestone | Not a milestone task | — |
| 50 | PASS | objective | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 51 | CANNOT DETERMINE | external | Solution or ground truth answers are not accessible in the environment | Manual review needed for ground-truth leakage in env docs/comments. | — |
| 52 | CANNOT DETERMINE | external | Agent cannot modify input data to trivially pass tests | Requires reviewing whether test inputs are writable/immutable in the container. | — |
| 53 | PASS | objective | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 54 | CANNOT DETERMINE | external | Task is not too easy (not >80% combined pass rate consistently) | Agent pass rates require --report submission export. | — |
| 55 | CANNOT DETERMINE | external | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | Fairness assessment requires human judgment of instructions, environment, and agent trajectories. | — |

---

## 3. Critical Issues

- **#1** — Missing instruction.md (instruction.md)
- **#2** — Missing instruction.md (—)
- **#3** — Missing instruction (—)
- **#7** — Missing instruction (—)
- **#10** — No absolute paths detected (—)
- **#13** — Missing environment/ (environment/)
- **#14** — Missing Dockerfile (—)
- **#15** — No FROM statements (environment/Dockerfile)
- **#20** — Dockerfile missing agent runtime tools (also missing: tmux, asciinema) (—)
- **#21** — Missing oracle solution (—)
- **#22** — Missing solve.sh (—)
- **#23** — Missing solve.sh (—)
- **#24** — Missing test.sh (—)
- **#28** — Missing test_outputs.py (—)
- **#31** — Missing test_outputs.py (—)
- **#40** — Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/scripts/raft-consensus-recovery (task.toml)
- **#42** — Missing task.toml (—)
- **#43** — Missing task.toml (—)
- **#44** — Missing task.toml (—)
- **#45** — Missing difficulty in task.toml (—)

---

## 4. Warnings

_No non-blocking warnings._

---

## 5. Suggestions

- **#8** — Confirm the scenario is realistic and useful to a developer audience.
- **#9** — Compare against TB2/TB3/Edition 1 task index before submission.
- **#17** — Scan environment docs and comments for walkthroughs or golden answers.
- **#32** — Provide --report or --rubric for rubric checks.
- **#52** — Confirm golden inputs are read-only or tests use ephemeral fixtures.
- **#54** — Run agent tests and attach entire-report.txt for #54 evaluation.

---

## 6. Items Requiring Manual Review

- **#8** — Subjective quality — requires human reviewer judgment.
- **#9** — Corpus uniqueness cannot be verified from task artifacts alone.
- **#17** — No obvious solution files; manual review needed for comment/doc leakage.
- **#27** — Missing instruction or test files for alignment check.
- **#32** — No rubric in task folder or --report export.
- **#33** — No rubric available.
- **#34** — No rubric available.
- **#35** — No rubric available.
- **#36** — No rubric available.
- **#37** — No rubric available.
- **#38** — No rubric available.
- **#39** — No rubric available.
- **#51** — Manual review needed for ground-truth leakage in env docs/comments.
- **#52** — Requires reviewing whether test inputs are writable/immutable in the container.
- **#54** — Agent pass rates require --report submission export.
- **#55** — Fairness assessment requires human judgment of instructions, environment, and agent trajectories.

---

## 7. validate_task.py Errors

```
ERROR: structure: Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/scripts/raft-consensus-recovery
```

---

_Generated by `./scripts/terminus audit` (read-only). See `docs/guidelines/task-auditor.md`._