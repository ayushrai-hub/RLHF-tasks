# Terminus Review Report: `stellar-kiosk-ledger`

**Generated:** 2026-06-26  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/stellar-kiosk-ledger`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (local 1/1 reward=1.0; platform 3/3 per `entire-report.txt`) |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong debugging task — canonical digest-pinned Node base, independent Python replay oracle, anti-cheat design, and Hard calibration (GPT-5.5 20%) all hold up. One real blocker: the contract never states that per-row `saved_drain` is always `0` while run-level `saved_drains` records saves; every agent trial set `saved_drain: 1` on the eventual closing row after a prior save, failing the deep-equality and digest tests. Add one explicit contract sentence. External “non-canonical base” and scorecard-case hint claims do not hold on file evidence.

**Insights (concise):**

- `saved_drain` row-field semantics are the sole systematic agent failure (5/5 trials, 8/10 tests, identical root cause per `entire-report.txt`).
- Dockerfile digest `f3a68cf…` matches canonical `node:22-bookworm-slim` in `docs/guidelines/dockerfxile.md:10` — external non-canonical-base claim is incorrect.
- Platform rubric (lines 290–300 of `entire-report.txt`) uses correct **non-milestone** flat format — not milestone `# Rubric N` blocks.
- `scorecard-cases/` restates the four symptom areas already named in `instruction.md`; no numeric answers leaked.
- Oracle solution always emits `saved_drain: 0` on closed rows (`solution/solve.sh:47`); Python oracle matches (`tests/test_outputs.py:79`).
- Optional polish: add `mkdir -p /logs/verifier` to `tests/test.sh`; add module docstring to `tests/test_outputs.py`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Per-row `saved_drain` value unstated; verifier requires `0` on every emitted closed-ball row while run-level `saved_drains` counts saves | `contract.md:5,19` lists field but never defines `0` vs `1`; `tests/test_outputs.py:79` oracle always `saved_drain: 0`; `test_scorecard_ranking_totals_match_cabinet_referee` deep-equals all rows; `entire-report.txt:54–74` — 5/5 agents set closing row `saved_drain: 1` after prior save on aurora ball 1 | Add to `contract.md` (and mirror in `instruction.md` if desired): *"The `saved_drain` field in every emitted row is always `0`; only the run-level `saved_drains` counter records prior saved drains."* |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `saved_drain` row-field semantics under-specified; closing row after prior save must emit `saved_drain: 0` | **Agree** | `contract.md:19` lists `saved_drain` on rows without value rule; `contract.md:5` says save keeps ball open; `tests/test_outputs.py:59–62,79` increments `saved_drains` and returns without row, then emits closing row with `saved_drain: 0`; `entire-report.txt:54–74` unanimous agent misread |
| 2 | ChatGPT: Needs Revision | **Agree** | Blocker 1 above |
| 3 | `entire-report.txt` CRITICAL: Non-canonical base image | **Disagree** | `environment/Dockerfile:1` uses `node:22-bookworm-slim@sha256:f3a68cf…` — exact match to `docs/guidelines/dockerfxile.md:10` |
| 4 | `entire-report.txt` CRITICAL: scorecard-cases leak diagnostic roadmap | **Disagree** | `instruction.md:7` already names all four fix areas (drain, warning, mode, sha256); `scorecard-cases/ranking-…-01.md:3` etc. restate categories without numeric answers |
| 5 | `entire-report.txt` WARNING: `tool_specific` subcategory questionable | **Partially agree** | `task.toml:13` — custom JS codebase, not third-party SDK; metadata polish only, not a blocker |
| 6 | `entire-report.txt` LLMaJ: `task_specification` FAIL (ambiguous) | **Agree** | Same root cause as claim 1 |
| 7 | `entire-report.txt` Quality: all behavior checks PASS | **Agree** | Lines 88–97 — coverage is thorough once `saved_drain` semantics are clarified |
| 8 | `entire-report.txt` Test quality: ACCEPT | **Agree** | Lines 252–288 — independent Python oracle is sound |
| 9 | Automated `terminus review`: #24 missing `mkdir -p /logs/verifier` | **Partially agree** | `tests/test.sh` lacks mkdir; reward block present; Harbor typically pre-creates `/logs/verifier` — polish, not revision driver |
| 10 | Automated `terminus review`: #31 missing docstrings | **Disagree** | All 10 `test_*` functions have docstrings (`tests/test_outputs.py:212–309`); only module-level docstring missing (validation warning) |

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
| 7 | UNCHECK | Well specified | `saved_drain` row value unstated | `contract.md:19`, blocker 1 |
| 8 | CHECK | Interesting | Real arcade state-machine debugging | task content |
| 9 | CHECK | Unique | Custom JS scorer + digest chain | `reference_pattern` in `task.toml:17-18` |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md:3-5` |
| 11 | CHECK | Task name not in instruction | No `stellar-kiosk-ledger` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/` |
| 14 | CHECK | Pinned pip versions | `pytest==8.4.1` etc. | `environment/Dockerfile:14` |
| 15 | CHECK | Digest-pinned FROM | Canonical node digest | `environment/Dockerfile:1`, `dockerfxile.md:10` |
| 16 | CHECK | Context in environment/ | COPY scoped to environment | `environment/Dockerfile:18-23` |
| 17 | CHECK | No ground truth in env | Contract is spec; no answer keys | `sfdata/rules/contract.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't conflict | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh clean | `Dockerfile:14`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | 3/3 per platform report | `entire-report.txt:25` |
| 22 | CHECK | Oracle no internet | `solve.sh` writes local code only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | Builds and runs pipeline | `solution/solve.sh` |
| 24 | UNCHECK | test.sh reward + mkdir | Missing `mkdir -p /logs/verifier` | `tests/test.sh:1-15` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `tests/test.sh:11-14` |
| 27 | UNCHECK | Tests aligned with instruction | Tests enforce `saved_drain: 0` not in contract | `tests/test_outputs.py:79`, blocker 1 |
| 28 | CHECK | Tests check correctness | Deep equality + targeted behavior | `tests/test_outputs.py:224-228` |
| 29 | CHECK | Behavior not implementation | Runs pipeline, compares output | `tests/test_outputs.py:24-34` |
| 30 | CHECK | No brittle exact strings | Schema/values from independent replay | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 10 tests documented | `tests/test_outputs.py:212-309` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives in platform rubric | `entire-report.txt:296-300` |
| 33 | CHECK | Rubric scores in allowed set | ±1,2,3,5 only | `entire-report.txt:290-300` |
| 34 | CHECK | Rubric `Agent …, ±N` format | All lines conform | `entire-report.txt:290-300` |
| 35 | CHECK | Rubric detailed/precise | Task-specific trace checks | `entire-report.txt:290-300` |
| 36 | CHECK | Rubric positive language | Negatives name bad behavior | `entire-report.txt:296-300` |
| 37 | CHECK | Rubric no /tests/ refs | No test-path mentions | `entire-report.txt:290-300` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:290-300` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:290-300` |
| 40 | CHECK | Required files present | All core files exist | task tree |
| 41 | CHECK | No stray parent files | Clean task folder | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | JS arcade scoring task | `task.toml:7-10` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: best-model 20% | `entire-report.txt:19-21`, `difficulty.md` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Input not trivially mutable | Switchlogs are data; verifier rebuilds | `tests/test_outputs.py:24-34` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80% at ≤80% threshold | `entire-report.txt:19-21` |
| 55 | UNCHECK | Not too hard/unfair | Unstated `saved_drain` semantics caused uniform failure | `entire-report.txt:54-74`, blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 24, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Output at `/app/output/audit.json` | `test_cabinet_ranking_schema_and_player_order` | covered | `instruction.md:3`, `tests/test_outputs.py:14` |
| JSON schema per contract | `test_cabinet_ranking_schema_and_player_order` | covered | `tests/test_outputs.py:217-220` |
| Saved drain keeps ball open (≤12s) | `test_saved_drain_ranking_keeps_ball_alive` | covered | `contract.md:5`, `tests/test_outputs.py:244-252` |
| **Per-row `saved_drain` always `0`** | `test_scorecard_ranking_totals_match_cabinet_referee` | **gap** | `contract.md:19` silent; `tests/test_outputs.py:79` |
| Tilt after 2nd warning suppresses scoring | `test_tilt_warning_ranking_suppresses_late_scores` | covered | `contract.md:5-6`, `tests/test_outputs.py:255-263` |
| Mode distinct/repeat/close scoring | `test_mode_ranking_closes_distinct_target_banks` | covered | `contract.md:13`, `tests/test_outputs.py:266-272` |
| Jackpot lit + multiball gate | `test_jackpot_ranking_requires_lit_multiball` | covered | `contract.md:17`, `tests/test_outputs.py:275-286` |
| Lane per-ball reset | `test_lane_scorecard_ranking_resets_per_ball` | covered | `contract.md:12`, `tests/test_outputs.py:231-241` |
| Rollup counters from runs | `test_rollup_ranking_counts_match_score_rows` | covered | `tests/test_outputs.py:289-295` |
| SHA-256 row/run/chain digests | `test_sha256_row_folding_recomputes_chain_digest` | covered | `contract.md:21`, `tests/test_outputs.py:298-305` |
| `SF_AUDIT_STRICT` latch only | `test_strict_latch_preserves_cabinet_scores` | covered | `contract.md:21`, `tests/test_outputs.py:308-317` |
| Pipeline rebuild required | all tests via `_run_export` | covered | `instruction.md:5`, `tests/test_outputs.py:24-34` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-6, #10-11, blocker 1, spec table |
| `environment/sfdata/rules/contract.md` | Blocker 1, #27, spec table |
| `environment/Dockerfile` | #15, #20, claim 3 |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec table |
| `tests/test.sh` | #24 |
| `solution/solve.sh` | #23, saved_drain oracle behavior |
| `task.toml` | #43-46, metadata |
| `entire-report.txt` | Agent stats, rubric, external claims |
| `docs/guidelines/dockerfxile.md` | #15, claim 3 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate stellar-kiosk-ledger
Summary: 0 error(s), 2 warning(s), 1 info
- informative_test_docstrings: module docstring missing
- check_dockerignore: no .dockerignore
- submission-diversity: non-milestone (info only)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Supports `hard` |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Borderline easy on worst model |
| oracle | 100.0% (3/3) | Per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (worst) / hard (best) |
| Declared difficulty | hard |
| Tier match (#45) | yes — best-model ≤20% justifies hard per `difficulty.md` |

**Per-test pass rates** (`entire-report.txt:33-42`): Only `test_scorecard_ranking_totals_match_cabinet_referee` and `test_sha256_row_folding_recomputes_chain_digest` at 5/10 — both cascade from `saved_drain` row mismatch on aurora ball 1.

### Rubric format (non-milestone check)

Platform rubric (`entire-report.txt:290-300`) is a **flat** `Agent …, ±N` list with **no** `# Rubric 2+` milestone blocks — correct for `number_of_milestones = 0` per `docs/guidelines/rubrics.md:60`. Positives sum to 21 (within 10–40); 5 distinct negatives (≥3 required).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches report; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | One spec gap: `saved_drain` row value |
| 2 Environment | ☑ | Canonical digest-pinned Node base; tmux+asciinema; no solution/tests COPY |
| 3 Oracle | ☑ | Derives via code fix; local 1/1 + platform 3/3 |
| 4 Verifiers | ☑ | Sound Python replay oracle; minor test.sh mkdir polish |
| 5 Metadata | ☑ | Fields complete; `tool_specific` debatable |
| 6 Rubric | ☑ | Platform rubric correct non-milestone format |
| 7 LLMaJ & agent evidence | ☑ | Unanimous `saved_drain` misread confirms spec gap |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; cheating closed |
| 9 Long context | — | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the digest-pinned Node setup, independent Python replay oracle, and multi-module debugging depth are all in great shape, and the difficulty calibration looks right for hard tier. One narrow fix before accept: the contract says saved drains keep the ball open and lists a `saved_drain` field on each closed-ball row, but never states that row field is always `0` while only the run-level `saved_drains` counter records saves. Every agent trial set `saved_drain: 1` on the eventual closing row after a prior save, which broke the full row match and digest chain. Please add one explicit sentence to `contract.md` clarifying that.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
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
