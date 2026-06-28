# Terminus Review Report: `go-deployment-health-window-reconciler-hardfreeze`

**Generated:** 2026-06-28 05:34 UTC  
**Disposition:** Revise  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/go-deployment-health-window-reconciler-hardfreeze`  

---

## 1. Executive summary

- **Recommendation:** Revise
- **Automated validation:** WARN (0 errors, 8 warnings)
- **Checkboxes to CHECK:** 32 items → `1, 3, 4, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 24, 25, 26, 29, 32, 33, 34, 37, 38, 39, 40, 41, 42, 43, 50, 53, 54`
- **Checkboxes to UNCHECK:** 23 items → `2, 5, 7, 8, 9, 17, 21, 23, 27, 28, 30, 31, 35, 36, 44, 45, 46, 47, 48, 49, 51, 52, 55`

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

## 2. Main blockers (detailed)

### Blocker 1: #31 — Tests have informative names or docstrings

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#31 UNCHECKED**
- **What failed:** 8 tests missing docstrings
- **Proof files:** _see evidence below_

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise (1 sentence to 3 paragraphs max) | 2 paragraph blocks, ~88 words | — |
| 3 | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | No heavy markdown detected | — |
| 4 | No step by step instructions telling the agent what developer steps to take | No step-by-step patterns | — |
| 6 | No design doc style tables mapping inputs to outputs | No design-doc tables | — |
| 10 | All paths in instruction are absolute (not relative) | Absolute paths present; no relative paths | `instruction.md` |
| 11 | Task name does not appear in instruction.md | Task name not in instruction | — |
| 12 | No canary string in instruction.md | No canary patterns | — |
| 13 | Dockerfile does not grab content from the web (other than packages) | No runtime web fetch in environment code | — |
| 14 | All Python/pip dependencies use pinned versions with == (no ranges) | No pip install in Dockerfile | — |
| 15 | Base Docker image is pinned by digest (@sha256:...) | All FROM lines digest-pinned | `environment/Dockerfile` |
| 16 | Environment does not use context from outside the environment directory | No COPY outside environment/ | — |
| 18 | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/SYS_ADMIN/docker.sock | — |
| 19 | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | No docker-compose.yaml | — |
| 20 | Verifier deps baked in image; test.sh does NOT install packages at runtime | Verifier deps in image; no runtime installs in test.sh | `environment/Dockerfile`, `tests/test.sh` |
| 22 | Oracle does not require internet or downloading packages | No obvious network installs in solve.sh | — |
| 24 | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | reward.txt write pattern present | — |
| 25 | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No /oracle conditional logic | — |
| 26 | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward pattern | — |
| 29 | Tests verify behavior, not implementation (no grepping source code) | No obvious implementation grep in tests | — |
| 32 | Rubrics contain at least 3 negative penalty criteria | 5 negative criteria (need ≥3) [platform rubric section in entire-report.txt] | — |
| 33 | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Scores in ±1,2,3,5 [platform rubric section in entire-report.txt] | — |
| 34 | Each rubric criterion is one line starting with Agent, comma, then score | 16 Agent lines [platform rubric section in entire-report.txt] | — |
| 37 | Rubric does not reference testing logic or /tests/ directory | No /tests/ references [platform rubric section in entire-report.txt] | — |
| 38 | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs [platform rubric section in entire-report.txt] | — |
| 39 | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions [platform rubric section in entire-report.txt] | — |
| 40 | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Required files present | — |
| 41 | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | No obvious stray parent files | — |
| 42 | author_name and author_email fields present in task.toml | author fields present | — |
| 43 | All other required metadata fields present | Core metadata fields present | — |
| 50 | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 53 | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 54 | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% ≤80% | — |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 2 | manual | Instruction reads like a natural prompt, not a spec document | [VERIFY FIRST] No automated LLM-pattern hits — confirm natural tone | — |
| 5 | manual | No hints or solving strategies (describes WHAT to build, not HOW) | [VERIFY FIRST] Review for implicit HOW-not-WHAT guidance | — |
| 7 | manual | Instruction is well specified (goal is clear and obvious) | [VERIFY FIRST] Has paths — verify all requirements testable | — |
| 8 | manual | Instruction is interesting (useful to some group of developers) | [VERIFY FIRST] Subjective — confirm task is useful/interesting | — |
| 9 | manual | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | [VERIFY FIRST] Verify uniqueness vs TB2/TB3/Edition 1 corpus | — |
| 17 | manual | Environment does not contain solution or ground truth answers | [VERIFY FIRST] Verify no answer leakage in comments/docs | — |
| 21 | manual | Oracle passes consistently (no flaky behavior) | [VERIFY FIRST] Run ./scripts/terminus oracle — confirm no flakes | — |
| 23 | manual | Oracle is reflective of instruction (real implementation, not hardcoded) | [VERIFY FIRST] Verify oracle derives results from implementation | — |
| 27 | manual | All tests are aligned with instructions (do not test unstated requirements) | [VERIFY FIRST] Cross-check instruction vs each test assertion (use prompt.md) | — |
| 28 | manual | Tests check for correctness, not just format | [VERIFY FIRST] Confirm tests assert correctness not format-only | — |
| 30 | manual | No brittle exact string matching where flexible checks would work | [VERIFY FIRST] Review assert style | — |
| 31 | fail | Tests have informative names or docstrings | 8 tests missing docstrings | — |
| 35 | manual | Rubric criteria are detailed and precise | [VERIFY FIRST] Review criterion precision [platform rubric section in entire-report.txt] | — |
| 36 | manual | Rubric criteria use positive language (not Agent does not do X, +1) | [VERIFY FIRST] Check positive phrasing [platform rubric section in entire-report.txt] | — |
| 44 | manual | Tags, languages, categories are applicable to the task | [VERIFY FIRST] Verify tags/languages/category match task content | — |
| 45 | manual | Difficulty matches observed agent pass rates | [VERIFY FIRST] task.toml difficulty='hard' vs worst-model 60% → 'medium'; report classified 'medium' — not a revision blocker per review policy | `task.toml`, `entire-report.txt` |
| 46 | na | steps/ layout present with per-milestone files (not root instruction/tests/solution) | [N/A] Not a milestone task | — |
| 47 | na | Each milestone has a corresponding solveN.sh file | [N/A] Not a milestone task | — |
| 48 | na | Each milestone has a corresponding test_mN.py file | [N/A] Not a milestone task | — |
| 49 | na | Each milestone test file is scoped only to that milestone | [N/A] Not a milestone task | — |
| 51 | manual | Solution or ground truth answers are not accessible in the environment | [VERIFY FIRST] Verify env has no accessible ground truth | — |
| 52 | manual | Agent cannot modify input data to trivially pass tests | [VERIFY FIRST] Verify input data not trivially writable by agent | — |
| 55 | manual | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | [VERIFY FIRST] Assess fairness — needs human review of instructions/env | — |

### Quick copy-paste

**CHECK:** 1, 3, 4, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 24, 25, 26, 29, 32, 33, 34, 37, 38, 39, 40, 41, 42, 43, 50, 53, 54

**UNCHECK:** 2, 5, 7, 8, 9, 17, 21, 23, 27, 28, 30, 31, 35, 36, 44, 45, 46, 47, 48, 49, 51, 52, 55

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `entire-report.txt` | #45 |
| `environment/Dockerfile` | #15, #20 |
| `instruction.md` | #10 |
| `task.toml` | #31, #45 |
| `tests/test.sh` | #20, #31 |
| `tests/test_outputs.py` | #31 |


## Submission export sections

| Section | Present | Use for |
|---------|---------|---------|
| Author — Difficulty Explanation | yes | context only |
| Author — Solution Explanation | yes | context only — not oracle |
| Author — Verification Explanation | yes | context only |
| System — difficulty check / agent stats / unit tests | yes | #45, #54, section 7 |
| System — instruction sufficiency analysis | yes | #27, #55 adjudication |
| System — LLMaJ quality checks | yes | LLMaJ hints — verify in files |
| System — Harbor review report | yes | warnings — verify in files |
| System — test quality review | yes | verifier quality |
| Platform — agent-generated rubric (#32–39) | yes | rubrics #32–39 |
| System — agent review narrative | no | advisory |


## Report ↔ task identity

Report appears applicable to this task folder (or insufficient signal to detect mismatch).


## External report adjudication (automated hints)

## 6. Agent performance (from report)

- terminus-claude-opus-4-8: 60.0%
- terminus-gpt5-5: 60.0%
- **Worst-model rate:** 60.0% → tier `medium`
- **Report classified difficulty:** medium

## 7. Audit log

- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `validate_task.py` → WARN
- [x] Cross-checked external report: `entire-report.txt`
- [ ] Manual spec↔test alignment (#27, #28) — **reviewer must confirm**
- [ ] Subjective items (#2, #8, #9, #55) — **reviewer must confirm**

---

## 8. Reviewer note (copy-paste to portal)

Good foundation on go-deployment-health-window-reconciler-hardfreeze — most of the structure looks solid. Main items to address: #31. See the detailed blocker section in this report for specifics.

---

_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._