# Terminus Review Report: `span-moment-area12`

**Generated:** 2026-07-08 14:51 UTC  
**Disposition:** Revise  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/span-moment-area12`  

---

## 1. Executive summary

- **Recommendation:** Revise
- **Automated validation:** WARN (0 errors, 1 warnings)
- **Checkboxes to CHECK:** 50 items → `1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54`
- **Checkboxes to UNCHECK:** 5 items → `9, 46, 47, 48, 49`

- **Rubric positive points (from report):** 30 (cap 40; PASS (30/40))
- **Rubric +line count:** 9
- **Per-block positive pts:** #0=30

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

## 2. Main blockers (detailed)

### Blocker 1: #9 — Instruction is not unique (duplicate across existing tasks)

- **Severity:** High
- **Error category:** Instruction Styling
- **Finding:** `span-moment-area12/instruction.md` is identical to other tasks’ `instruction.md` text in this repository (example matches: `tasks/span-moment-area/instruction.md`, `span-moment-area1/instruction.md`, `span-moment-area1 copy/instruction.md`).
- **Proof:** `span-moment-area12/instruction.md:1-5` == `tasks/span-moment-area/instruction.md:1-5` (same 5-line instruction block).
- **Required fix:** Make `span-moment-area12/instruction.md` unique before resubmission (or explicitly justify shared text if it is an intentional variant and update the instruction to distinguish this task).

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraph blocks, ~134 words | — |
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
| 24 | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | reward.txt write with failure path (mkdir optional — Harbor provides mount) | — |
| 25 | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No /oracle conditional logic | — |
| 26 | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward pattern | — |
| 29 | Tests verify behavior, not implementation (no grepping source code) | No obvious implementation grep in tests | — |
| 31 | Tests have informative names or docstrings | Test docstrings present | — |
| 32 | Rubrics contain at least 3 negative penalty criteria | 5 negative criteria (need ≥3) [platform rubric section in entire-report.txt] | — |
| 33 | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Scores in ±1,2,3,5 [platform rubric section in entire-report.txt] | — |
| 34 | Each rubric criterion is one line starting with Agent, comma, then score | 14 Agent lines [platform rubric section in entire-report.txt] | — |
| 35 | Rubric criteria are detailed and precise | Rubric positive points: 30 positive pts (cap 40; 9 +lines) — PASS (30/40) [platform rubric section in entire-report.txt] | — |
| 37 | Rubric does not reference testing logic or /tests/ directory | No /tests/ references [platform rubric section in entire-report.txt] | — |
| 38 | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs [platform rubric section in entire-report.txt] | — |
| 39 | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions [platform rubric section in entire-report.txt] | — |
| 40 | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Required files present | — |
| 41 | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | No obvious stray parent files | — |
| 42 | author_name and author_email fields present in task.toml | author fields present | — |
| 43 | All other required metadata fields present | Core metadata fields present | — |
| 45 | Difficulty matches observed agent pass rates | task.toml difficulty='hard'; platform classified='hard'; worst-model 0% → tier 'hard'; best-model 0% | `task.toml`, `entire-report.txt` |
| 50 | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 53 | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 54 | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% ≤80% | — |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 9 | manual | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Duplicated 5-line instruction block found in multiple other tasks in this repo | `span-moment-area12/instruction.md:1-5` vs `tasks/span-moment-area/instruction.md:1-5` |
| 46 | na | steps/ layout present with per-milestone files (not root instruction/tests/solution) | [N/A] Not a milestone task | — |
| 47 | na | Each milestone has a corresponding solveN.sh file | [N/A] Not a milestone task | — |
| 48 | na | Each milestone has a corresponding test_mN.py file | [N/A] Not a milestone task | — |
| 49 | na | Each milestone test file is scoped only to that milestone | [N/A] Not a milestone task | — |

### Quick copy-paste

**CHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54

**UNCHECK:** 9, 46, 47, 48, 49

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `entire-report.txt` | #45 |
| `environment/Dockerfile` | #15, #20 |
| `instruction.md` | #10 |
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
- terminus-gpt5-5: 0.0%
- **Worst-model rate:** 0.0% → tier `hard`
- **Best-model rate:** 0.0%
- **task.toml difficulty:** `hard`
- **Platform classified difficulty:** `hard`

## 6b. Rubric positive points (entire-report)

| Field | Value |
|-------|-------|
| Source | `platform rubric section in entire-report.txt` |
| Positive point total (+lines only) | **30** |
| Positive line count | 9 |
| Cap | 40 (blocker only if **>40**) |
| Status | PASS (30/40) |
| Per `# Rubric N` block | {0: 30} |

## 7. Audit log

- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `validate_task.py` → WARN
- [x] Cross-checked external report: `entire-report.txt`
- [x] Instruction uniqueness (#9) — **fails due to duplication**
- [x] Other manual items — **verified pass**

---

## 8. Reviewer note (copy-paste to portal)

Good foundation on span-moment-area12 — most of the structure looks solid. See the detailed blocker section in this report for specifics.

---

_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._