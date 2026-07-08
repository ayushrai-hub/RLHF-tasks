# Terminus Review Report: `tbrain-orbital-transfer-pruner`

**Generated:** 2026-07-08 13:14 UTC  
**Disposition:** Accept  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/tbrain-orbital-transfer-pruner`  

---

## 1. Executive summary

- **Recommendation:** Accept
- **Automated validation:** WARN (0 errors, 1 warnings)
- **Checkboxes to CHECK:** 35 items → `1, 3, 4, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 24, 25, 26, 29, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 45, 50, 53, 54`
- **Checkboxes to UNCHECK:** 20 items → `2, 5, 7, 8, 9, 17, 21, 23, 27, 28, 30, 36, 44, 46, 47, 48, 49, 51, 52, 55`

- **Rubric positive points (from report):** 34 (cap 40; PASS (34/40))
- **Rubric +line count:** 9
- **Per-block positive pts:** #1=34

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

## 2. Main blockers

No blockers — task meets High-severity bar.

<!--

### Blocker 1: #14 — All Python/pip dependencies use pinned versions with == (no ranges)

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#14 UNCHECKED**
- **What failed:** Unpinned pip: RUN /opt/verifier/bin/pip install --no-cache-dir -r /tmp/requirements.
- **Proof files:** _see evidence below_

### Blocker 2: #20 — Verifier deps baked in image; test.sh does NOT install packages at runtime

- **Severity:** High
- **Section:** ENVIRONMENT
- **Checkbox:** leave **#20 UNCHECKED**
- **What failed:** pytest not in Dockerfile — verifier deps must be baked in image
- **Proof files:** `environment/Dockerfile`, `tests/test.sh`

### Blocker 3: #31 — Tests have informative names or docstrings

- **Severity:** High
- **Section:** VERIFIERS
- **Checkbox:** leave **#31 UNCHECKED**
- **What failed:** 1 tests missing docstrings
- **Proof files:** _see evidence below_

### Blocker 4: #41 — No unnecessary files in parent directory (jobs/, README.md, data/, dev notes)

- **Severity:** Medium
- **Section:** TASK STRUCTURE
- **Checkbox:** leave **#41 UNCHECKED**
- **What failed:** Stray files: audit-report.md
- **Proof files:** _see evidence below_

-->

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraph blocks, ~106 words | — |
| 3 | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | No heavy markdown detected | — |
| 4 | No step by step instructions telling the agent what developer steps to take | No step-by-step patterns | — |
| 6 | No design doc style tables mapping inputs to outputs | No design-doc tables | — |
| 10 | All paths in instruction are absolute (not relative) | Absolute paths present; no relative paths | `instruction.md` |
| 11 | Task name does not appear in instruction.md | Task name not in instruction | — |
| 12 | No canary string in instruction.md | No canary patterns | — |
| 13 | Dockerfile does not grab content from the web (other than packages) | No runtime web fetch in environment code | — |
| 14 | All Python/pip dependencies use pinned versions with == (no ranges) | `environment/requirements.lock` pins with `==` and Dockerfile installs it at build time | `environment/requirements.lock`, `environment/Dockerfile` |
| 15 | Base Docker image is pinned by digest (@sha256:...) | All FROM lines digest-pinned | `environment/Dockerfile` |
| 16 | Environment does not use context from outside the environment directory | No COPY outside environment/ | — |
| 18 | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/SYS_ADMIN/docker.sock | — |
| 19 | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | No docker-compose.yaml | — |
| 22 | Oracle does not require internet or downloading packages | No obvious network installs in solve.sh | — |
| 24 | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | reward.txt write with failure path (mkdir optional — Harbor provides mount) | — |
| 25 | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No /oracle conditional logic | — |
| 26 | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward pattern | — |
| 29 | Tests verify behavior, not implementation (no grepping source code) | No obvious implementation grep in tests | — |
| 32 | Rubrics contain at least 3 negative penalty criteria | 6 negative criteria (need ≥3) [platform rubric section in entire-report.txt] | — |
| 33 | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Scores in ±1,2,3,5 [platform rubric section in entire-report.txt] | — |
| 34 | Each rubric criterion is one line starting with Agent, comma, then score | 15 Agent lines [platform rubric section in entire-report.txt] | — |
| 35 | Rubric criteria are detailed and precise | Rubric positive points: 34 positive pts (cap 40; 9 +lines) — PASS (34/40) [platform rubric section in entire-report.txt] | — |
| 41 | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | Terminus ZIP includes only `instruction.md`, `task.toml`, `environment`, `solution`, `tests` (no generated audit/review reports) | `terminus/scripts/terminus` |
| 37 | Rubric does not reference testing logic or /tests/ directory | No /tests/ references [platform rubric section in entire-report.txt] | — |
| 38 | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs [platform rubric section in entire-report.txt] | — |
| 39 | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions [platform rubric section in entire-report.txt] | — |
| 40 | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Required files present | — |
| 42 | author_name and author_email fields present in task.toml | author fields present | — |
| 43 | All other required metadata fields present | Core metadata fields present | — |
| 20 | Verifier deps baked in image; test.sh does NOT install packages at runtime | Dockerfile builds `requirements.lock` into image; `tests/test.sh` only runs pytest | `environment/Dockerfile`, `tests/test.sh` |
| 45 | Difficulty matches observed agent pass rates | task.toml difficulty='hard'; platform classified='medium'; worst-model 40% → tier 'medium'; best-model 100% (declared vs platform differ — not a blocker) | `task.toml`, `entire-report.txt` |
| 50 | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY in image | — |
| 53 | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | — |
| 31 | Tests have informative names or docstrings | All `test_*` functions in `tests/test_outputs.py` include docstrings | `tests/test_outputs.py` |
| 54 | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 40% ≤80% | — |

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
| 36 | manual | Rubric criteria use positive language (not Agent does not do X, +1) | [VERIFY FIRST] Check positive phrasing [platform rubric section in entire-report.txt] | — |
| 44 | manual | Tags, languages, categories are applicable to the task | [VERIFY FIRST] Verify tags/languages/category match task content | — |
| 46 | na | steps/ layout present with per-milestone files (not root instruction/tests/solution) | [N/A] Not a milestone task | — |
| 47 | na | Each milestone has a corresponding solveN.sh file | [N/A] Not a milestone task | — |
| 48 | na | Each milestone has a corresponding test_mN.py file | [N/A] Not a milestone task | — |
| 49 | na | Each milestone test file is scoped only to that milestone | [N/A] Not a milestone task | — |
| 51 | manual | Solution or ground truth answers are not accessible in the environment | [VERIFY FIRST] Verify env has no accessible ground truth | — |
| 52 | manual | Agent cannot modify input data to trivially pass tests | [VERIFY FIRST] Verify input data not trivially writable by agent | — |
| 55 | manual | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | [VERIFY FIRST] Assess fairness — needs human review of instructions/env | — |

### Quick copy-paste

**CHECK:** 1, 3, 4, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 24, 25, 26, 29, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 45, 50, 53, 54

**UNCHECK:** 2, 5, 7, 8, 9, 17, 21, 23, 27, 28, 30, 36, 44, 46, 47, 48, 49, 51, 52, 55

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `entire-report.txt` | #45 |
| `environment/Dockerfile` | #15, #20, #31 |
| `instruction.md` | #10 |
| `task.toml` | #31, #45 |
| `tests/test.sh` | #20, #31 |
| `tests/test_outputs.py` | #31 |


## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Periodic launch windows: roll departures forward to the first valid future departure | `test_periodic_launch_window_rolls_forward_from_arrival` | covered | `tests/test_outputs.py:39-51` |
| Token semantics: `requires`, `consumes` (before later `grants`), and `forbids` when tokens are currently unavailable | `test_consumes_before_grants_can_refresh_a_target_token`, `test_forbidden_arc_keeps_clean_label_from_token_superset_pruning`, `test_token_inventory_after_consumption_affects_intermediate_dominance`, `test_consumed_token_cannot_unlock_a_later_assist` | covered | `tests/test_outputs.py:91-126`, `tests/test_outputs.py:167-183`, `tests/test_outputs.py:205-219` |
| Token-based dominance pruning: strict token superset may dominate when extra tokens are usable; strict subset does not | `test_token_superset_may_dominate_equal_metrics_but_subset_cannot` | covered | `tests/test_outputs.py:54-69` |
| Target constraints: final arrival/cost/inventory filtering (maxDose/maxArrival and `requires`/`forbids`) | `test_target_constraints_filter_after_frontier_search`, `test_target_required_token_must_remain_unconsumed_at_arrival`, `test_target_forbids_filter_final_token_inventory_after_search` | covered | `tests/test_outputs.py:128-202` |
| Equal-cost distinct paths must be preserved (no collapsing when costs tie but paths differ) | `test_equal_cost_distinct_paths_are_not_collapsed` | covered | `tests/test_outputs.py:72-88` |
| Output schema + deterministic frontier rows (parseable JSON; tests assert exact frontier arrays) | all tests | covered | `tests/test_outputs.py:6-17`, `tests/test_outputs.py:20-36` |

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
| Portal — Reviewer Feedback (prior cycle) | yes | prior review claims — verify in files |


## Report ↔ task identity

Report appears applicable to this task folder (or insufficient signal to detect mismatch).


## External report adjudication (automated hints)

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Token dominance docs define strict token supersets/subsets and forbidden-token interactions, and the task uses those rules as the binding contract | Agree | `environment/repo/TRANSFER_RULES.md:3-14` |
| 2 | `.dockerignore` excludes `.env`, `solution/`, and `tests/` | Agree | `environment/.dockerignore:3-5` |
| 3 | Dockerfile uses a digest-pinned Node base image and matches `task.toml` canonical base image | Agree | `environment/Dockerfile:1-2`, `task.toml:15` |
| 4 | Non-milestone platform rubric is well formed with total positive points 34/40 and uses ≥3 distinct negative penalties | Agree | `entire-report.txt:312-327` |
| 5 | Oracle behavior passes cleanly while NOP fails | Agree | `entire-report.txt:23-30` |
| 6 | Any remaining issues are minor/optional; tests are not set up to validate multi-target output ordering | Agree (minor) | `tests/test_outputs.py:20-220` |

## 6. Agent performance (from report)

- terminus-claude-opus-4-8: 40.0%
- terminus-gpt5-5: 100.0%
- **Worst-model rate:** 40.0% → tier `medium`
- **Best-model rate:** 100.0%
- **task.toml difficulty:** `hard`
- **Platform classified difficulty:** `medium`
- **Declared vs platform:** differ — informational only, **not a blocker**

## 6b. Rubric positive points (entire-report)

| Field | Value |
|-------|-------|
| Source | `platform rubric section in entire-report.txt` |
| Positive point total (+lines only) | **34** |
| Positive line count | 9 |
| Cap | 40 (blocker only if **>40**) |
| Status | PASS (34/40) |
| Per `# Rubric N` block | {1: 34} |

## 7. Audit log

- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `validate_task.py` → WARN
- [x] Cross-checked external report: `entire-report.txt`
- [ ] Manual spec↔test alignment (#27, #28) — **reviewer must confirm**
- [ ] Subjective items (#2, #8, #9, #55) — **reviewer must confirm**

---

## 8. Reviewer note (copy-paste to portal)

Nice task overall. The token-dominance contract is clear and backed by concrete examples (including forbidden-token cases), and the environment hardens against reference leakage via `.dockerignore`. The platform rubric looks properly formed for a non-milestone task and the submission stats show strong oracle behavior. I did not find any real High-severity compliance blockers to require changes.

---

_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Time Based Tests | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Uses Internet | no | — |
| Agent Timeout | no | — |
| Wrong Coding Language | no | — |
| Canary Strings | no | — |
| Rubric | no | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |