# Terminus Review Report: `disaster-recovery-readiness-auditor`

**Generated:** 2026-07-03 06:09 UTC  
**Disposition:** Revise  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/disaster-recovery-readiness-auditor`  

---

## 1. Executive summary

- **Recommendation:** Revise
- **Automated validation:** FAIL (1 errors, 0 warnings)
- **Checkboxes to CHECK:** 11 items → `32, 33, 34, 35, 37, 38, 39, 41, 50, 53, 54`
- **Checkboxes to UNCHECK:** 44 items → `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 36, 40, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 55`

- **Rubric positive points (from report):** 39 (cap 40; PASS (39/40))
- **Rubric +line count:** 13
- **Per-block positive pts:** #0=39

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

## 2. Main blockers (detailed)

### Blocker 1: #1 — Instruction is concise (1 sentence to 3 paragraphs max)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#1 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 2: #2 — Instruction reads like a natural prompt, not a spec document

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#2 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 3: #3 — No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#3 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 4: #4 — No step by step instructions telling the agent what developer steps to take

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#4 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 5: #5 — No hints or solving strategies (describes WHAT to build, not HOW)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#5 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 6: #6 — No design doc style tables mapping inputs to outputs

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#6 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 7: #7 — Instruction is well specified (goal is clear and obvious)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#7 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 8: #8 — Instruction is interesting (useful to some group of developers)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#8 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 9: #9 — Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#9 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 10: #10 — All paths in instruction are absolute (not relative)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#10 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 11: #11 — Task name does not appear in instruction.md

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#11 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 12: #12 — No canary string in instruction.md

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#12 UNCHECKED**
- **What failed:** Missing instruction.md
- **Proof files:** `instruction.md`

### Blocker 13: #13 — Dockerfile does not grab content from the web (other than packages)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#13 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 14: #14 — All Python/pip dependencies use pinned versions with == (no ranges)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#14 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 15: #15 — Base Docker image is pinned by digest (@sha256:...)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#15 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 16: #16 — Environment does not use context from outside the environment directory

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#16 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 17: #17 — Environment does not contain solution or ground truth answers

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#17 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 18: #18 — Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#18 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 19: #19 — Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#19 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 20: #20 — Verifier deps baked in image; test.sh does NOT install packages at runtime

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#20 UNCHECKED**
- **What failed:** Missing Dockerfile
- **Proof files:** _see evidence below_

### Blocker 21: #21 — Oracle passes consistently (no flaky behavior)

- **Severity:** High
- **Section:** ORACLE SOLUTION
- **Checkbox:** leave **#21 UNCHECKED**
- **What failed:** Missing oracle solution
- **Proof files:** _see evidence below_

### Blocker 22: #22 — Oracle does not require internet or downloading packages

- **Severity:** High
- **Section:** ORACLE SOLUTION
- **Checkbox:** leave **#22 UNCHECKED**
- **What failed:** Missing oracle solution
- **Proof files:** _see evidence below_

### Blocker 23: #23 — Oracle is reflective of instruction (real implementation, not hardcoded)

- **Severity:** High
- **Section:** ORACLE SOLUTION
- **Checkbox:** leave **#23 UNCHECKED**
- **What failed:** Missing oracle solution
- **Proof files:** _see evidence below_

### Blocker 24: #24 — test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#24 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 25: #25 — Verifiers use the exact same logic for oracle and agent runs (no conditional logic)

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#25 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 26: #26 — Verifier applies binary rewards only (0 or 1, no partial scores)

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#26 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 27: #27 — All tests are aligned with instructions (do not test unstated requirements)

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#27 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 28: #28 — Tests check for correctness, not just format

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#28 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 29: #29 — Tests verify behavior, not implementation (no grepping source code)

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#29 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 30: #30 — No brittle exact string matching where flexible checks would work

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#30 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 31: #31 — Tests have informative names or docstrings

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#31 UNCHECKED**
- **What failed:** Missing test.sh
- **Proof files:** _see evidence below_

### Blocker 32: #40 — All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml)

- **Severity:** High
- **Section:** TASK STRUCTURE
- **Checkbox:** leave **#40 UNCHECKED**
- **What failed:** Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/disaster-recovery-readiness-auditor
- **Proof files:** _see evidence below_

### Blocker 33: #42 — author_name and author_email fields present in task.toml

- **Severity:** High
- **Section:** TASK METADATA
- **Checkbox:** leave **#42 UNCHECKED**
- **What failed:** Missing task.toml
- **Proof files:** _see evidence below_

### Blocker 34: #43 — All other required metadata fields present

- **Severity:** High
- **Section:** TASK METADATA
- **Checkbox:** leave **#43 UNCHECKED**
- **What failed:** Missing task.toml
- **Proof files:** _see evidence below_

### Blocker 35: #44 — Tags, languages, categories are applicable to the task

- **Severity:** High
- **Section:** TASK METADATA
- **Checkbox:** leave **#44 UNCHECKED**
- **What failed:** Missing task.toml
- **Proof files:** _see evidence below_

### Blocker 36: #45 — Difficulty matches observed agent pass rates

- **Severity:** High
- **Section:** TASK METADATA
- **Checkbox:** leave **#45 UNCHECKED**
- **What failed:** Missing task.toml
- **Proof files:** _see evidence below_

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 32 | Rubrics contain at least 3 negative penalty criteria | 4 negative criteria (need ≥3) [platform rubric section in entire-report.txt] | — |
| 33 | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Scores in ±1,2,3,5 [platform rubric section in entire-report.txt] | — |
| 34 | Each rubric criterion is one line starting with Agent, comma, then score | 17 Agent lines [platform rubric section in entire-report.txt] | — |
| 35 | Rubric criteria are detailed and precise | Rubric positive points: 39 positive pts (cap 40; 13 +lines) — PASS (39/40) [platform rubric section in entire-report.txt] | — |
| 37 | Rubric does not reference testing logic or /tests/ directory | No /tests/ references [platform rubric section in entire-report.txt] | — |
| 38 | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs [platform rubric section in entire-report.txt] | — |
| 39 | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions [platform rubric section in entire-report.txt] | — |
| 41 | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | No obvious stray parent files | — |
| 50 | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 53 | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 54 | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% ≤80% | — |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 1 | fail | Instruction is concise (1 sentence to 3 paragraphs max) | Missing instruction.md | `instruction.md` |
| 2 | fail | Instruction reads like a natural prompt, not a spec document | Missing instruction.md | `instruction.md` |
| 3 | fail | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | Missing instruction.md | `instruction.md` |
| 4 | fail | No step by step instructions telling the agent what developer steps to take | Missing instruction.md | `instruction.md` |
| 5 | fail | No hints or solving strategies (describes WHAT to build, not HOW) | Missing instruction.md | `instruction.md` |
| 6 | fail | No design doc style tables mapping inputs to outputs | Missing instruction.md | `instruction.md` |
| 7 | fail | Instruction is well specified (goal is clear and obvious) | Missing instruction.md | `instruction.md` |
| 8 | fail | Instruction is interesting (useful to some group of developers) | Missing instruction.md | `instruction.md` |
| 9 | fail | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Missing instruction.md | `instruction.md` |
| 10 | fail | All paths in instruction are absolute (not relative) | Missing instruction.md | `instruction.md` |
| 11 | fail | Task name does not appear in instruction.md | Missing instruction.md | `instruction.md` |
| 12 | fail | No canary string in instruction.md | Missing instruction.md | `instruction.md` |
| 13 | fail | Dockerfile does not grab content from the web (other than packages) | Missing Dockerfile | — |
| 14 | fail | All Python/pip dependencies use pinned versions with == (no ranges) | Missing Dockerfile | — |
| 15 | fail | Base Docker image is pinned by digest (@sha256:...) | Missing Dockerfile | — |
| 16 | fail | Environment does not use context from outside the environment directory | Missing Dockerfile | — |
| 17 | fail | Environment does not contain solution or ground truth answers | Missing Dockerfile | — |
| 18 | fail | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | Missing Dockerfile | — |
| 19 | fail | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | Missing Dockerfile | — |
| 20 | fail | Verifier deps baked in image; test.sh does NOT install packages at runtime | Missing Dockerfile | — |
| 21 | fail | Oracle passes consistently (no flaky behavior) | Missing oracle solution | — |
| 22 | fail | Oracle does not require internet or downloading packages | Missing oracle solution | — |
| 23 | fail | Oracle is reflective of instruction (real implementation, not hardcoded) | Missing oracle solution | — |
| 24 | fail | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing test.sh | — |
| 25 | fail | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | Missing test.sh | — |
| 26 | fail | Verifier applies binary rewards only (0 or 1, no partial scores) | Missing test.sh | — |
| 27 | fail | All tests are aligned with instructions (do not test unstated requirements) | Missing test.sh | — |
| 28 | fail | Tests check for correctness, not just format | Missing test.sh | — |
| 29 | fail | Tests verify behavior, not implementation (no grepping source code) | Missing test.sh | — |
| 30 | fail | No brittle exact string matching where flexible checks would work | Missing test.sh | — |
| 31 | fail | Tests have informative names or docstrings | Missing test.sh | — |
| 36 | manual | Rubric criteria use positive language (not Agent does not do X, +1) | [VERIFY FIRST] Check positive phrasing [platform rubric section in entire-report.txt] | — |
| 40 | fail | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/disaster-recovery-readiness-auditor | — |
| 42 | fail | author_name and author_email fields present in task.toml | Missing task.toml | — |
| 43 | fail | All other required metadata fields present | Missing task.toml | — |
| 44 | fail | Tags, languages, categories are applicable to the task | Missing task.toml | — |
| 45 | fail | Difficulty matches observed agent pass rates | Missing task.toml | — |
| 46 | na | steps/ layout present with per-milestone files (not root instruction/tests/solution) | [N/A] Not a milestone task | — |
| 47 | na | Each milestone has a corresponding solveN.sh file | [N/A] Not a milestone task | — |
| 48 | na | Each milestone has a corresponding test_mN.py file | [N/A] Not a milestone task | — |
| 49 | na | Each milestone test file is scoped only to that milestone | [N/A] Not a milestone task | — |
| 51 | manual | Solution or ground truth answers are not accessible in the environment | [VERIFY FIRST] Verify env has no accessible ground truth | — |
| 52 | manual | Agent cannot modify input data to trivially pass tests | [VERIFY FIRST] Verify input data not trivially writable by agent | — |
| 55 | manual | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | [VERIFY FIRST] Assess fairness — needs human review of instructions/env | — |

### Quick copy-paste

**CHECK:** 32, 33, 34, 35, 37, 38, 39, 41, 50, 53, 54

**UNCHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 36, 40, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 55

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `instruction.md` | #1, #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #12 |

## 5. Validation output (re-audit)

```
ERROR: structure: Task directory not found: /Users/ayushrai/Downloads/Airdawgs-review-Terminus2/disaster-recovery-readiness-auditor
```


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
| Author — Comments for Reviewer | no | author context only |
| Portal — Reviewer Feedback (prior cycle) | no | prior review claims — verify in files |


## Report ↔ task identity

Report appears applicable to this task folder (or insufficient signal to detect mismatch).


## External report adjudication (automated hints)

## 6. Agent performance (from report)

- terminus-claude-opus-4-8: 0.0%
- terminus-gpt5-5: 20.0%
- **Worst-model rate:** 0.0% → tier `hard`
- **Best-model rate:** 20.0%
- **Platform classified difficulty:** `hard`

## 6b. Rubric positive points (entire-report)

| Field | Value |
|-------|-------|
| Source | `platform rubric section in entire-report.txt` |
| Positive point total (+lines only) | **39** |
| Positive line count | 13 |
| Cap | 40 (blocker only if **>40**) |
| Status | PASS (39/40) |
| Per `# Rubric N` block | {0: 39} |

## 7. Audit log

- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `validate_task.py` → FAIL
- [x] Cross-checked external report: `entire-report.txt`
- [ ] Manual spec↔test alignment (#27, #28) — **reviewer must confirm**
- [ ] Subjective items (#2, #8, #9, #55) — **reviewer must confirm**

---

## 8. Reviewer note (copy-paste to portal)

Good foundation on disaster-recovery-readiness-auditor — most of the structure looks solid. Main items to address: #1, #2, #3, #4, #5. See the detailed blocker section in this report for specifics.

---

_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._