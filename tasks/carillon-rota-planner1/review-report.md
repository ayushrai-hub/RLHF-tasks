# Terminus Review Report: carillon-rota-planner1

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report 100% 3/3; local run blocked by Docker sandbox) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are strong: digest-pinned Ruby base, offline verifier setup, thorough instruction↔test alignment via reference solver, and difficulty calibration (worst-model 40%). One real High blocker: the platform rubric has two inverted negative criteria that penalize desirable agent behavior (verification and single-pass delivery), leaving only one correctly framed penalty. Positive total is 36 (under cap). Prior reviewer feedback citing 42 points is stale. `# Rubric 1` alone on a non-milestone task is permitted.

**Insights (concise):**

- Non-milestone task (`number_of_milestones = 0`) with optional single `# Rubric 1` header — **not** wrongly formatted as multi-milestone rubric (`rubrics.md:66`).
- Positive rubric total is **36** (cap 40 passes); ChatGPT and current export agree; stale portal note citing 42 is outdated.
- Automated audit #14 (unpinned pip) and #37 (pytest in rubric) are **false positives** — multiline `pytest==` pins in Dockerfile; pytest mention is in appended reviewer-feedback text, not rubric criteria lines.
- Instruction is dense (~571 words) but normative for a constraint-optimization contract; LLMaJ behavior_in_tests/description PASS; not elevated to blocker.
- Worst-model pass rate 40% (Claude Opus 4.8); GPT-5.5 100%; tier medium; not too easy (#54 passes).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32, #36 | Two of three negative rubric lines penalize **good** behavior (verification, single-pass delivery); only one line correctly penalizes bad behavior (non-executable / missing shebang). Need ≥3 distinct, correctly framed penalties. | `entire-report.txt:283-285`; `rubrics.md:37-41` ("Penalize bad behavior") | Reframe negatives, e.g. `Agent completes without running the planner on sample input or inspecting output, -2`; `Agent leaves multiple broken planner versions or inconsistent partial implementations, -2`; keep/fix executable/shebang penalty as action-style `Agent leaves the planner non-executable or missing a shebang, -3`; add at least one more distinct bad-behavior penalty if replacing rather than reframing. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Two rubric negatives describe desirable behavior; only one valid penalty; need ≥3 correct negatives (ChatGPT High) | **Agree** | `entire-report.txt:283-285` — lines 283–284 assign `-2` to "verifies" and "single pass" (good actions); line 285 is the only inverted-framing-correct negative |
| 2 | Positive total ~36, no 42-point cap issue (ChatGPT) | **Agree** | `./scripts/terminus rubric-points entire-report.txt` → 36/40 PASS |
| 3 | Trim positive total from 42 to ≤40 (prior Reviewer Feedback) | **Disagree (stale)** | Current rubric sums to 36; feedback predates rubric trim |
| 4 | Add one more negative because only two exist (prior Reviewer Feedback) | **Partially agree** | Three `-N` lines exist by count, but two are semantically invalid; author needs ≥3 **correctly framed** negatives, not just more lines |
| 5 | Task instructions, verifier, offline setup otherwise sound (ChatGPT Medium none) | **Agree** | `instruction.md`, `tests/test_outputs.py`, `environment/Dockerfile`, `task.toml:23` `allow_internet=false` |
| 6 | Optional: clarify bell rule as floor(N/2) (ChatGPT Low / Harbor review) | **Agree (Low only)** | `instruction.md:7` uses `N/2`; `test_outputs.py:96` uses `tower["bells"] // 2`; consistent but could add example — not a blocker |
| 7 | Optional: rephrase executable negative to action-style (ChatGPT Low) | **Agree (Low only)** | `entire-report.txt:285` "Agent fails to make…" works but action-style wording preferred |
| 8 | Docker FROM digest-pinned Ruby base appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:e76733e9…`; non-canonical Ruby justified (Harbor review L125-146) |
| 9 | Non-milestone task in milestone rubric format (user concern) | **Disagree** | Only `# Rubric 1` present, no `# Rubric 2+`; `task.toml:10` `number_of_milestones=0`; `rubrics.md:66` permits optional `# Rubric 1` on flat rubrics |
| 10 | Audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:13-15` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` on continuation lines |
| 11 | Audit #37 rubric references pytest | **Disagree** | Rubric criteria `entire-report.txt:270-285` contain no pytest; false hit from reviewer-feedback chunk (`L290`) bundled in export parse |
| 12 | Audit #1 instruction too long | **Partially agree (not blocker)** | ~571 words / 7 prose blocks exceeds concise heuristic; acceptable for optimization contract with exact reason strings and tie-breaks |
| 13 | LLMaJ behavior_in_tests / anti_cheating / pinned_deps pass | **Agree** | `entire-report.txt:86-93`; verified against artifacts |
| 14 | Harbor review READY TO USE | **Partially agree** | Artifacts strong; rubric negative framing must be fixed first |
| 15 | test_large_rota 8/10 pass rate = performance not spec gap | **Agree** | `entire-report.txt:48,61-62`; `test_outputs.py:355-408` 10s timeout; instruction L13 warns up to 45 proposals |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction concise | Dense spec ~571 words / 7 prose blocks exceeds 3-paragraph heuristic; intentional for optimization contract — borderline, not a separate blocker | `instruction.md`; audit #1 |
| 2 | CHECK | Natural prompt tone | Opens as engineer request, not "You are an expert…" | `instruction.md:1` |
| 3 | CHECK | No excessive markdown | Plain prose, no tables/headers | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States WHAT (CLI contract, rules), not dev steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | No solve walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, schemas, reason strings, tie-breaks, output contract | `instruction.md:1-13` |
| 8 | CHECK | Interesting | Real scheduling/constraint scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify vs full TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | Absolute paths | `/app/carillon-planner`, `/app/input/…` | `instruction.md:1-3` |
| 11 | CHECK | No task name in instruction | Clean | `instruction.md` |
| 12 | CHECK | No canary string | Clean | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline input shipped | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:13-15` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:e76733e9…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | `COPY task_file/input` only | `environment/Dockerfile:19` |
| 17 | CHECK | No ground-truth leakage in env | Public input only; expected output not in image | `environment/.dockerignore:13-14` |
| 18 | CHECK | No dangerous Docker ops | Standard RUN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest venv in Dockerfile; test.sh no installs | `environment/Dockerfile:12-15`, `tests/test.sh:12` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle offline | solve.sh writes Ruby implementation locally | `solution/solve.sh:4+` |
| 23 | CHECK | Oracle reflective | Full branch-and-bound planner derived at runtime | `solution/solve.sh` |
| 24 | CHECK | reward.txt on pass/fail | Canonical block | `tests/test.sh:15-19` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instruction | All 11 tests trace to documented rules | see §5 |
| 28 | CHECK | Tests check correctness | Reference `expected_plan()` comparison | `tests/test_outputs.py:132-185,248-250` |
| 29 | CHECK | Behavior not implementation grep | Runs CLI, compares JSON output | `tests/test_outputs.py:188-202` |
| 30 | CHECK | Not brittle where flex needed | Exact strings required by spec (reason codes) | `instruction.md:6,10` |
| 31 | CHECK | Informative docstrings | All `test_*` documented | `tests/test_outputs.py` |
| 32 | UNCHECK | ≥3 negative rubric criteria | 3 `-N` lines exist but only 1 correctly penalizes bad behavior | `entire-report.txt:283-285` |
| 33 | CHECK | Valid rubric scores | ±1,2,3,5 only | `entire-report.txt:270-285` |
| 34 | CHECK | Rubric one-line format | 16 `Agent …, ±N` lines | `entire-report.txt:270-285` |
| 35 | CHECK | Rubric detailed; positive cap | 36 positive pts ≤40 | `./scripts/terminus rubric-points` |
| 36 | UNCHECK | Positive phrasing on positives / negatives penalize bad behavior | Lines 283–284 penalize good actions with `-2` | `entire-report.txt:283-284` |
| 37 | CHECK | No /tests/ in rubric | Criteria lines clean (export parse false positive) | `entire-report.txt:270-285` |
| 38 | CHECK | No instruction.md in rubric | Clean | `entire-report.txt:270-285` |
| 39 | CHECK | No oracle/NOP in rubric | Clean | `entire-report.txt:270-285` |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in submission tree | task folder |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Metadata complete | Timeouts, verifier/agent blocks | `task.toml` |
| 44 | CHECK | Tags/languages/category | Ruby CLI optimization; `data-processing` reasonable | `task.toml:7-11` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; platform `medium`; worst-model 40% — informational only | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps layout | N/A — non-milestone | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | `environment/.dockerignore:14` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution | `environment/.dockerignore:13` |
| 52 | CHECK | Input not trivially tamperable | SHA256 integrity check on public input | `tests/test_outputs.py:17,258-259` |
| 53 | CHECK | Git clones pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:26-27` |
| 55 | CHECK | Not too hard/unfair | Instruction sufficiency PASS; failures algorithmic | `entire-report.txt:52-69` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 9, 32, 36, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Executable at `/app/carillon-planner` with two path args | `test_executable_and_sample_rota_integrity` | covered | `instruction.md:1-3`; `test_outputs.py:253-259` |
| Validation order + exact reason strings | `test_rejection_reasons_follow_rota_policy_order` | covered | `instruction.md:6`; `test_outputs.py:271-293` |
| Bell tier rules (N/2, competent, experienced) | `test_rejection_reasons_follow_rota_policy_order` (tier case) | covered | `instruction.md:7`; `test_outputs.py:96-99,287` |
| Half-open intervals | `test_rejection_reasons…`, variations | covered | `instruction.md:5`; `test_outputs.py:26-27` |
| Mandatory inclusion + infeasibility | `test_conflicting_mandatory_sessions_make_rota_infeasible`, `test_mandatory_sessions_can_exceed_the_tower_cap` | covered | `instruction.md:8-9,10`; `test_outputs.py:311-322,411-423` |
| 30-minute rest gap | `test_rest_gap_blocks_back_to_back_shared_ringers` | covered | `instruction.md:8`; `test_outputs.py:324-332` |
| Minute caps on selected proposals | `test_minute_caps_can_outweigh…`, `test_large_rota_respects_minute_caps_exactly` | covered | `instruction.md:8`; `test_outputs.py:335-408` |
| Tie-breaks (score, count, minutes, lex ids) | `test_tie_breaks_compare_the_complete_rota` | covered | `instruction.md:9`; `test_outputs.py:296-308` |
| Output JSON schema + rejection reasons | `test_sample_rota_requires_global_choice`, reference tests | covered | `instruction.md:10-11`; `test_outputs.py:262-268` |
| Empty arrays valid | `test_empty_input_arrays_are_valid` | covered | `instruction.md:11`; `test_outputs.py:427-442` |
| Scale up to 45 proposals | `test_large_rota_respects_minute_caps_exactly` (34 proposals, 10s limit) | covered | `instruction.md:13`; `test_outputs.py:355-408` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, spec alignment §5 |
| `task.toml` | #44, #45, milestone N/A |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32, #36, #45, #54, rubric adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: carillon-rota-planner1/ ===
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | 2 timeouts |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | medium |
| Tier match (#45) | informational only — never blocks |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular layout; Ruby optimization task |
| 1 Instruction | ☑ | Dense but complete; no hints; absolute paths |
| 2 Environment | ☑ | Digest-pinned Ruby; tmux/asciinema; pytest venv; allow_internet=false |
| 3 Oracle | ☑ | Platform 100%; solve.sh writes full Ruby planner |
| 4 Verifiers | ☑ | Reference solver; 11 tests; reward block canonical |
| 5 Metadata | ☑ | Complete; non-milestone |
| 6 Rubric | ☐ | **Blocker:** inverted negatives #283-284 |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; worst-model 40% |
| 8 Novelty & fairness | ☑ | Multi-rule optimization; anti-cheat via SHA256 + synthetic variants |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong work on this one — the rota planner spec is thorough, the Ruby CLI contract is clear, and the pytest suite with a reference solver gives solid end-to-end coverage of validation order, mandatory sessions, rest gaps, minute caps, and tie-breaks. Dockerfile and offline verifier setup look good too, and difficulty calibration feels reasonable.

One thing to fix before we can accept: two rubric negative lines currently penalize good behavior (`Agent verifies the planner runs successfully… -2` and `Agent writes the planner in a single pass… -2`). Please reframe those as penalties for skipping verification or leaving broken partial implementations, and make sure you have at least three distinct negatives that all penalize bad actions. The positive total is already 36, so no trim needed there. Optional polish: clarify the bell rule as `floor(N/2)` and use action-style wording for the executable/shebang negative.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
