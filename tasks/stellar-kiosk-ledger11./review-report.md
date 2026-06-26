# Terminus Review Report: `stellar-kiosk-ledger11.`

**Generated:** 2026-06-26  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/stellar-kiosk-ledger11.`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed locally; LLMaJ `hardcoded_solution` pass per `entire-report.txt:27-28` |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** Accept. The prior `saved_drain` contract ambiguity is resolved in `contract.md:5`: run-level `saved_drains` counts saves and every emitted closed-ball row keeps `saved_drain` at `0`. Digest-pinned canonical Node base, offline verifier, independent Python replay oracle, anti-cheat design, output schema, and platform rubric format (flat non-milestone) all comply. No High-severity blockers remain. Optional polish: add `mkdir -p /logs/verifier` to `tests/test.sh`; add module docstring to `tests/test_outputs.py`.

**Insights (concise):**

- `contract.md:5` explicitly states row `saved_drain` is always `0` including after prior saves — fixes the unanimous agent failure described in `entire-report.txt:222`.
- Platform rubric (`entire-report.txt:207-218`) uses correct **flat** non-milestone format — no `# Rubric N` milestone blocks.
- Dockerfile digest `f3a68cf…` matches canonical `node:22-bookworm-slim` in `docs/guidelines/dockerfxile.md:10`.
- All 10 `test_*` functions have docstrings; only module-level docstring missing (validation warning, not blocker).
- `tests/test.sh` lacks canonical `mkdir -p /logs/verifier` but writes binary reward on both paths; Harbor pre-creates mount.
- Instruction claims verifier runs `npm run build` (`instruction.md:5`); tests invoke `/app/ops/sfdesk` only — `build` is `selfcheck.cjs` syntax check; `.cjs` sources load at runtime so no practical gap.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept; prior contract ambiguity resolved | **Agree** | `contract.md:5` — *"Saved drains are counted only in the run-level `saved_drains` counter; each emitted closed-ball row keeps `saved_drain` at `0`"* |
| 2 | ChatGPT: digest-pinned Node, offline verifier, Python replay oracle, anti-cheat, Hard calibration solid | **Agree** | `environment/Dockerfile:1,14`; `allow_internet = false` (`task.toml:27`); `tests/test_outputs.py:42-186` independent replay; `.dockerignore:3-4`; `difficulty = "hard"` (`task.toml:6`) |
| 3 | `entire-report.txt:222`: needs contract clarification for `saved_drain` | **Disagree** | Fixed in this revision at `contract.md:5`; stale relative to `stellar-kiosk-ledger11.` |
| 4 | `entire-report.txt:56-77`: non-canonical base image WARNING | **Disagree** | `environment/Dockerfile:1` digest matches `docs/guidelines/dockerfxile.md:10` exactly |
| 5 | `entire-report.txt:21`: `informative_test_structure` FAIL (obfuscated `_expected_for` vars) | **Partially agree** | `tests/test_outputs.py:47-50` uses `x3`/`x8` etc.; maintainability note only — all tests have clear docstrings |
| 6 | `entire-report.txt:104-126`: missing shebang in test.sh | **Disagree** | `tests/test.sh:1` has `#!/bin/bash` |
| 7 | `entire-report.txt:181-184`: `_run_export()` skips `npm run build` | **Partially agree** | `tests/test_outputs.py:24-34` calls `/app/ops/sfdesk` only; `package.json:7` `build` is syntax selfcheck; no compile step — no correctness impact |
| 8 | `entire-report.txt:19-28`: LLMaJ behavior_in_task_description / behavior_in_tests PASS | **Agree** | Coverage spans schema, drain, tilt, mode, jackpot, digests, latch (`tests/test_outputs.py:211-317`) |
| 9 | Automated `terminus review`: #24 missing mkdir | **Partially agree** | `tests/test.sh` lacks mkdir; reward block present (`tests/test.sh:11-14`); polish only |
| 10 | Automated `terminus review`: #31 missing docstrings | **Disagree** | All 10 `test_*` have docstrings (`tests/test_outputs.py:212-309`); module docstring only |
| 11 | User: non-milestone task in milestone rubric format? | **Disagree** (no issue) | Platform rubric is flat `Agent …, ±N` list with no `# Rubric 2+` blocks (`entire-report.txt:207-218`); correct per `docs/guidelines/rubrics.md:60` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 4 short paragraphs, ~190 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Debugging brief, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | No heavy headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States symptoms and contract path only | `instruction.md:7` |
| 5 | CHECK | No hints/solving strategies | Lists WHAT is wrong, not fix steps | `instruction.md:7` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | CHECK | Well specified | Contract now defines `saved_drain` row semantics | `contract.md:5,19` |
| 8 | CHECK | Interesting | Real arcade state-machine debugging | task content |
| 9 | CHECK | Unique | Custom JS scorer + digest chain | `task.toml:17-18` |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md:3-5` |
| 11 | CHECK | Task name not in instruction | No `stellar-kiosk-ledger` in instruction | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/` |
| 14 | CHECK | Pinned pip versions | `pytest==8.4.1` etc. | `environment/Dockerfile:14` |
| 15 | CHECK | Digest-pinned FROM | Canonical node digest | `environment/Dockerfile:1`, `dockerfxile.md:10` |
| 16 | CHECK | Context in environment/ | COPY scoped to environment | `environment/Dockerfile:18-23` |
| 17 | CHECK | No ground truth in env | Contract is spec; scorecard cases are vague notes | `sfdata/rules/contract.md`, `scorecard-cases/ranking-drain-warning-mode-sha256-scorecard-01.md:3` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't conflict | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh clean | `Dockerfile:14`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | LLMaJ hardcoded_solution pass; solve derives via pipeline | `entire-report.txt:27-28`, `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | `solve.sh` writes local code only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | Replaces buggy modules, runs build + sfdesk | `solution/solve.sh:4-47` |
| 24 | UNCHECK | test.sh reward + mkdir | Missing `mkdir -p /logs/verifier` | `tests/test.sh:1-15` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `tests/test.sh:11-14` |
| 27 | CHECK | Tests aligned with instruction | All instructed behaviors tested; `saved_drain` now in contract | `contract.md:5`, `tests/test_outputs.py:79,244-252` |
| 28 | CHECK | Tests check correctness | Deep equality + targeted behavior | `tests/test_outputs.py:224-228` |
| 29 | CHECK | Behavior not implementation | Runs pipeline, compares output | `tests/test_outputs.py:24-34` |
| 30 | CHECK | No brittle exact strings | Values from independent replay | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 10 tests documented | `tests/test_outputs.py:212-309` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives in platform rubric | `entire-report.txt:214-218` |
| 33 | CHECK | Rubric scores in allowed set | ±1,2,3,5 only | `entire-report.txt:207-218` |
| 34 | CHECK | Rubric `Agent …, ±N` format | All lines conform | `entire-report.txt:207-218` |
| 35 | CHECK | Rubric detailed/precise | Task-specific trace checks | `entire-report.txt:207-218` |
| 36 | CHECK | Rubric positive language | Negatives name bad behavior | `entire-report.txt:214-218` |
| 37 | CHECK | Rubric no /tests/ refs | No test-path mentions | `entire-report.txt:207-218` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:207-218` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:207-218` |
| 40 | CHECK | Required files present | All core files exist | task tree |
| 41 | CHECK | No stray parent files | Clean task folder | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | JS arcade scoring task | `task.toml:7-10` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: multi-bug debugging; prior trials failed on now-fixed spec gap | `task.toml:6`, `entire-report.txt:222`, `difficulty.md` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:4` |
| 51 | CHECK | Solution not in env | No solution COPY | `environment/Dockerfile`, `.dockerignore:3` |
| 52 | CHECK | Input not trivially mutable | Verifier deletes output and reruns pipeline | `tests/test_outputs.py:25-26` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Multi-module debugging; contract fix removes unfair systematic failure | task design |
| 55 | CHECK | Not too hard/unfair | Contract now states `saved_drain` row rule | `contract.md:5` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 24, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Output at `/app/output/audit.json` | `test_cabinet_ranking_schema_and_player_order` | covered | `instruction.md:3`, `tests/test_outputs.py:14` |
| JSON schema per contract | `test_cabinet_ranking_schema_and_player_order` | covered | `tests/test_outputs.py:217-220` |
| Saved drain keeps ball open (≤12s) | `test_saved_drain_ranking_keeps_ball_alive` | covered | `contract.md:5`, `tests/test_outputs.py:244-252` |
| Per-row `saved_drain` always `0` | `test_scorecard_ranking_totals_match_cabinet_referee` | covered | `contract.md:5`, `tests/test_outputs.py:79` |
| Tilt after 2nd warning suppresses scoring | `test_tilt_warning_ranking_suppresses_late_scores` | covered | `contract.md:5-6`, `tests/test_outputs.py:255-263` |
| Mode distinct/repeat/close scoring | `test_mode_ranking_closes_distinct_target_banks` | covered | `contract.md:13`, `tests/test_outputs.py:266-272` |
| Jackpot lit + multiball gate | `test_jackpot_ranking_requires_lit_multiball` | covered | `contract.md:17`, `tests/test_outputs.py:275-286` |
| Lane per-ball reset | `test_lane_scorecard_ranking_resets_per_ball` | covered | `contract.md:12`, `tests/test_outputs.py:231-241` |
| Rollup counters from runs | `test_rollup_ranking_counts_match_score_rows` | covered | `tests/test_outputs.py:289-295` |
| SHA-256 row/run/chain digests | `test_sha256_row_folding_recomputes_chain_digest` | covered | `contract.md:21`, `tests/test_outputs.py:298-305` |
| `SF_AUDIT_STRICT` latch only | `test_strict_latch_preserves_cabinet_scores` | covered | `contract.md:21`, `tests/test_outputs.py:308-317` |
| Fix source; pipeline regenerates output | all tests via `_run_export` | covered | `instruction.md:5`, `tests/test_outputs.py:24-34` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-6, #10-11, spec table |
| `environment/sfdata/rules/contract.md` | #7, #27, #55, spec table, claim 1 |
| `environment/Dockerfile` | #15, #20, claim 4 |
| `tests/test_outputs.py` | #27-31, spec table |
| `tests/test.sh` | #24, #26 |
| `solution/solve.sh` | #21-23 |
| `task.toml` | #43-46, metadata |
| `entire-report.txt` | External claims, rubric, LLMaJ |
| `docs/guidelines/dockerfxile.md` | #15, claim 4 |
| `docs/guidelines/rubrics.md` | Rubric format, claim 11 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate stellar-kiosk-ledger11.
Summary: 0 error(s), 1 warning(s), 1 info
- informative_test_docstrings: module docstring missing
- submission-diversity: non-milestone (info only)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | not in provided report | Prior revision: systematic `saved_drain` misread (now fixed in contract) |
| terminus-claude-opus-4-8 | not in provided report | — |
| oracle | LLMaJ pass | `entire-report.txt:27-28`; local oracle not completed |

| Metric | Value |
|--------|-------|
| Worst-model rate | not in `entire-report.txt` |
| Observed tier | hard (design + prior agent failures on fixed spec gap) |
| Declared difficulty | hard |
| Tier match (#45) | yes |

### Rubric format (non-milestone check)

Platform rubric (`entire-report.txt:207-218`) is a **flat** `Agent …, ±N` list with **no** `# Rubric 2+` milestone blocks — correct for `number_of_milestones = 0` per `docs/guidelines/rubrics.md:60`. Positive sum = 23 (within 10–40); 5 distinct negatives (≥3 required). **Not** in milestone rubric format.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `stellar-kiosk-ledger11.`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Contract fix resolves prior `saved_drain` gap |
| 2 Environment | ☑ | Canonical digest-pinned Node; tmux+asciinema; no solution/tests COPY |
| 3 Oracle | ☑ | Derives via code fix; LLMaJ pass |
| 4 Verifiers | ☑ | Sound Python replay oracle; minor test.sh mkdir polish |
| 5 Metadata | ☑ | Fields complete |
| 6 Rubric | ☑ | Platform rubric correct flat non-milestone format |
| 7 LLMaJ & agent evidence | ☑ | Prior revision note at line 222 superseded by contract fix |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; cheating closed |
| 9 Long context | — | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The digest-pinned Node setup, independent Python replay oracle, and multi-module debugging depth are all in great shape, and the contract clarification on `saved_drain` — saves count only in run-level `saved_drains`, closed-ball rows always emit `0` — closes the gap that tripped every prior agent trial. Verifiers, anti-cheat design, and rubric format all look good. Optional polish: add `mkdir -p /logs/verifier` to `test.sh` to match the canonical template.

---

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
