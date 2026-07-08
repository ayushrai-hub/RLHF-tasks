# Terminus Review Report: `warmcache-perl`

**Generated:** 2026-07-07 06:34 UTC  
**Disposition:** Revise  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/warmcache-perl`  

---

## 1. Executive summary

- **Recommendation:** Revise
- **Automated validation:** WARN (0 errors, 14 warnings)
- **Checkboxes to CHECK:** 30 items → `3, 4, 6, 10, 11, 12, 13, 15, 16, 18, 19, 22, 24, 25, 26, 29, 32, 34, 35, 37, 38, 39, 40, 42, 43, 45, 46, 50, 53, 54`
- **Checkboxes to UNCHECK:** 25 items → `1, 2, 5, 7, 8, 9, 14, 17, 20, 21, 23, 27, 28, 30, 31, 33, 36, 41, 44, 47, 48, 49, 51, 52, 55`

- **Rubric positive points (from report):** 37 (cap 40; PASS (37/40))
- **Rubric +line count:** 11
- **Per-block positive pts:** #1=37

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

## 2. Main blockers (detailed)

### Blocker 1: #1 — Instruction is concise (1 sentence to 3 paragraphs max)

- **Severity:** High
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** leave **#1 UNCHECKED**
- **What failed:** Very long instruction (14 blocks, ~714 words)
- **Proof files:** `steps/milestone_1/instruction.md, steps/milestone_2/instruction.md, steps/milestone_3/instruction.md`

### Blocker 2: #14 — All Python/pip dependencies use pinned versions with == (no ranges)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#14 UNCHECKED**
- **What failed:** Unpinned pip: RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requ
- **Proof files:** _see evidence below_

### Blocker 3: #20 — Verifier deps baked in image; test.sh does NOT install packages at runtime

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#20 UNCHECKED**
- **What failed:** pytest not in Dockerfile — verifier deps must be baked in image
- **Proof files:** `environment/Dockerfile`, `tests/test.sh`

### Blocker 4: #31 — Tests have informative names or docstrings

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#31 UNCHECKED**
- **What failed:** 10 tests missing docstrings
- **Proof files:** _see evidence below_

### Blocker 5: #33 — Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5}

- **Severity:** Medium
- **Section:** RUBRICS
- **Checkbox:** leave **#33 UNCHECKED**
- **What failed:** Invalid scores: ['+4'] [platform rubric section in entire-report.txt]
- **Proof files:** _see evidence below_

### Blocker 6: #36 — Rubric criteria use positive language (not Agent does not do X, +1)

- **Severity:** Medium
- **Section:** RUBRICS
- **Checkbox:** leave **#36 UNCHECKED**
- **What failed:** Negative phrasing in rubric [platform rubric section in entire-report.txt]
- **Proof files:** _see evidence below_

### Blocker 7: #41 — No unnecessary files in parent directory (jobs/, README.md, data/, dev notes)

- **Severity:** Medium
- **Section:** TASK STRUCTURE
- **Checkbox:** leave **#41 UNCHECKED**
- **What failed:** Stray files: audit-report.md
- **Proof files:** _see evidence below_

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 3 | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | No heavy markdown detected | — |
| 4 | No step by step instructions telling the agent what developer steps to take | No step-by-step patterns | — |
| 6 | No design doc style tables mapping inputs to outputs | No design-doc tables | — |
| 10 | All paths in instruction are absolute (not relative) | Absolute paths present; no relative paths | `steps/milestone_1/instruction.md, steps/milestone_2/instruction.md, steps/milestone_3/instruction.md` |
| 11 | Task name does not appear in instruction.md | Task name not in instruction | — |
| 12 | No canary string in instruction.md | No canary patterns | — |
| 13 | Dockerfile does not grab content from the web (other than packages) | No runtime web fetch in environment code | — |
| 15 | Base Docker image is pinned by digest (@sha256:...) | All FROM lines digest-pinned | `environment/Dockerfile` |
| 16 | Environment does not use context from outside the environment directory | No COPY outside environment/ | — |
| 18 | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/SYS_ADMIN/docker.sock | — |
| 19 | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | No docker-compose.yaml | — |
| 22 | Oracle does not require internet or downloading packages | No obvious network installs in solve.sh | — |
| 24 | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | reward.txt write with failure path (mkdir optional — Harbor provides mount) | — |
| 25 | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No /oracle conditional logic | — |
| 26 | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward pattern | — |
| 29 | Tests verify behavior, not implementation (no grepping source code) | No obvious implementation grep in tests | — |
| 32 | Rubrics contain at least 3 negative penalty criteria | 4 negative criteria (need ≥3) [platform rubric section in entire-report.txt] | — |
| 34 | Each rubric criterion is one line starting with Agent, comma, then score | 15 Agent lines [platform rubric section in entire-report.txt] | — |
| 35 | Rubric criteria are detailed and precise | Rubric positive points: 37 positive pts (cap 40; 11 +lines) — PASS (37/40) [platform rubric section in entire-report.txt] | — |
| 37 | Rubric does not reference testing logic or /tests/ directory | No /tests/ references [platform rubric section in entire-report.txt] | — |
| 38 | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs [platform rubric section in entire-report.txt] | — |
| 39 | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions [platform rubric section in entire-report.txt] | — |
| 40 | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Required files present | — |
| 42 | author_name and author_email fields present in task.toml | author fields present | — |
| 43 | All other required metadata fields present | Core metadata fields present | — |
| 45 | Difficulty matches observed agent pass rates | task.toml difficulty='hard'; platform classified='hard'; worst-model 20% → tier 'hard'; best-model 100% | `task.toml`, `entire-report.txt` |
| 46 | steps/ layout present with per-milestone files (not root instruction/tests/solution) | steps/ milestone layout OK | — |
| 50 | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 53 | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 54 | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% ≤80% | — |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 1 | fail | Instruction is concise (1 sentence to 3 paragraphs max) | Very long instruction (14 blocks, ~714 words) | `steps/milestone_1/instruction.md, steps/milestone_2/instruction.md, steps/milestone_3/instruction.md` |
| 2 | manual | Instruction reads like a natural prompt, not a spec document | [VERIFY FIRST] No automated LLM-pattern hits — confirm natural tone | — |
| 5 | manual | No hints or solving strategies (describes WHAT to build, not HOW) | [VERIFY FIRST] Review for implicit HOW-not-WHAT guidance | — |
| 7 | manual | Instruction is well specified (goal is clear and obvious) | [VERIFY FIRST] Has paths — verify all requirements testable | — |
| 8 | manual | Instruction is interesting (useful to some group of developers) | [VERIFY FIRST] Subjective — confirm task is useful/interesting | — |
| 9 | manual | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | [VERIFY FIRST] Verify uniqueness vs TB2/TB3/Edition 1 corpus | — |
| 14 | fail | All Python/pip dependencies use pinned versions with == (no ranges) | Unpinned pip: RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requ | — |
| 17 | manual | Environment does not contain solution or ground truth answers | [VERIFY FIRST] Verify no answer leakage in comments/docs | — |
| 20 | fail | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest not in Dockerfile — verifier deps must be baked in image | `environment/Dockerfile`, `tests/test.sh` |
| 21 | manual | Oracle passes consistently (no flaky behavior) | [VERIFY FIRST] Run ./scripts/terminus oracle — confirm no flakes | — |
| 23 | manual | Oracle is reflective of instruction (real implementation, not hardcoded) | [VERIFY FIRST] Verify oracle derives results from implementation | — |
| 27 | manual | All tests are aligned with instructions (do not test unstated requirements) | [VERIFY FIRST] Cross-check instruction vs each test assertion (use prompt.md) | — |
| 28 | manual | Tests check for correctness, not just format | [VERIFY FIRST] Confirm tests assert correctness not format-only | — |
| 30 | manual | No brittle exact string matching where flexible checks would work | [VERIFY FIRST] Review assert style | — |
| 31 | fail | Tests have informative names or docstrings | 10 tests missing docstrings | — |
| 33 | fail | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Invalid scores: ['+4'] [platform rubric section in entire-report.txt] | — |
| 36 | fail | Rubric criteria use positive language (not Agent does not do X, +1) | Negative phrasing in rubric [platform rubric section in entire-report.txt] | — |
| 41 | fail | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | Stray files: audit-report.md | — |
| 44 | manual | Tags, languages, categories are applicable to the task | [VERIFY FIRST] Verify tags/languages/category match task content | — |
| 47 | manual | Each milestone has a corresponding solveN.sh file | [VERIFY FIRST] Verify solveN.sh per milestone | — |
| 48 | manual | Each milestone has a corresponding test_mN.py file | [VERIFY FIRST] Verify test_mN.py per milestone | — |
| 49 | manual | Each milestone test file is scoped only to that milestone | [VERIFY FIRST] Verify milestone scope per milestone | — |
| 51 | manual | Solution or ground truth answers are not accessible in the environment | [VERIFY FIRST] Verify env has no accessible ground truth | — |
| 52 | manual | Agent cannot modify input data to trivially pass tests | [VERIFY FIRST] Verify input data not trivially writable by agent | — |
| 55 | manual | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | [VERIFY FIRST] Assess fairness — needs human review of instructions/env | — |

### Quick copy-paste

**CHECK:** 3, 4, 6, 10, 11, 12, 13, 15, 16, 18, 19, 22, 24, 25, 26, 29, 32, 34, 35, 37, 38, 39, 40, 42, 43, 45, 46, 50, 53, 54

**UNCHECK:** 1, 2, 5, 7, 8, 9, 14, 17, 20, 21, 23, 27, 28, 30, 31, 33, 36, 41, 44, 47, 48, 49, 51, 52, 55

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `entire-report.txt` | #45 |
| `environment/Dockerfile` | #15, #20, #31 |
| `steps/milestone_1/instruction.md, steps/milestone_2/instruction.md, steps/milestone_3/instruction.md` | #1, #10 |
| `steps/milestone_1/tests/test.sh` | #31 |
| `steps/milestone_1/tests/test_m1.py` | #31 |
| `steps/milestone_2/tests/test.sh` | #31 |
| `steps/milestone_2/tests/test_m2.py` | #31 |
| `steps/milestone_3/tests/test.sh` | #31 |
| `steps/milestone_3/tests/test_m3.py` | #31 |
| `task.toml` | #45 |
| `tests/test.sh` | #20 |


## Submission export sections

| Section | Present | Use for |
|---------|---------|---------|
| Author — Difficulty Explanation | yes | context only |
| Author — Solution Explanation | yes | context only — not oracle |
| Author — Verification Explanation | yes | context only |
| System — difficulty check / agent stats / unit tests | yes | #45, #54, section 7 |
| System — instruction sufficiency analysis | yes | #27, #55 adjudication |
| System — LLMaJ quality checks | yes | LLMaJ hints — verify in files |
| System — Harbor review report | no | warnings — verify in files |
| System — test quality review | yes | verifier quality |
| Platform — agent-generated rubric (#32–39) | yes | rubrics #32–39 |
| System — agent review narrative | no | advisory |
| Author — Comments for Reviewer | no | author context only |
| Portal — Reviewer Feedback (prior cycle) | no | prior review claims — verify in files |


## Report ↔ task identity

Report appears applicable to this task folder (or insufficient signal to detect mismatch).


## External report adjudication (automated hints)

## 6. Agent performance (from report)

- terminus-claude-opus-4-8: 20.0%
- terminus-gpt5-5: 100.0%
- **Worst-model rate:** 20.0% → tier `hard`
- **Best-model rate:** 100.0%
- **task.toml difficulty:** `hard`
- **Platform classified difficulty:** `hard`

## 6b. Rubric positive points (entire-report)

| Field | Value |
|-------|-------|
| Source | `platform rubric section in entire-report.txt` |
| Positive point total (+lines only) | **37** |
| Positive line count | 11 |
| Cap | 40 (blocker only if **>40**) |
| Status | PASS (37/40) |
| Per `# Rubric N` block | {1: 37} |

## 7. Audit log

- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `validate_task.py` → WARN
- [x] Cross-checked external report: `entire-report.txt`
- [ ] Manual spec↔test alignment (#27, #28) — **reviewer must confirm**
- [ ] Subjective items (#2, #8, #9, #55) — **reviewer must confirm**

---

## 8. Reviewer note (copy-paste to portal)

Good foundation on warmcache-perl — most of the structure looks solid. Main items to address: #1, #14, #20, #31. See the detailed blocker section in this report for specifics.

---

_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._