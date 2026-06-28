# Terminus Review Report: `meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260624`

**Generated:** 2026-06-25 (manual audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260624`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; local oracle CLI unavailable) |
| **CHECK count** | 52 |
| **UNCHECK count** | 3 |

**Error categories (internal):** Task Difficulty, Rubric

**Decision (concise):** The task is structurally sound: digest-pinned Node Dockerfile, offline verifier venv, milestone layout, spec-to-test alignment, anti-cheat hash checks, and oracle 100% (3/3) all check out. Claude worst-model pass rate is 40% (Medium tier) while `task.toml` declares `hard` — that metadata mismatch is the primary blocker. Submitted rubrics in `entire-report.txt` also fail CI format (#34): lines omit the required `Agent` prefix. No instruction, environment, oracle, or verifier blockers found on re-audit.

**Insights (concise):**

- Automated `review_checklist.py` miscomputed worst-model rate as 100% (`max` of model rates); actual worst model is Claude at 40%.
- `#54` passes: worst model 40% is not >80% too-easy; only `#45` fails for tier mismatch.
- `environment/requirements.txt` pins `pytest==8.4.1`; validate warning on Dockerfile `pip install -r` is a false positive.
- LLMaJ quality checks (behavior_in_task_description, behavior_in_tests, anti_cheating) all pass; agent M4 `by_district` failure is agent error — M2 specifies `districts` key.
- Rubrics have ≥3 negatives and valid score magnitudes but need `Agent …, ±N` prefix on every line.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | `task.toml` declares `difficulty = "hard"` but worst-model pass rate is 40% (Medium tier: 20–60%) | `task.toml:6`; `entire-report.txt:1-7` | Set `difficulty = "medium"` in `task.toml`, or rebalance task until worst model ≤20% |
| 2 | High | Rubric | #34 | Rubric lines do not start with `Agent` as required by `docs/guidelines/rubrics.md` | `entire-report.txt:446-494` (e.g. line 446: `Output file /app/output/...`) | Rewrite each rubric line as `Agent <behavior>, ±N` before portal accept |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: difficulty `hard` but evaluation is Medium (Claude 40%, GPT 100%) | **Agree** | `task.toml:6` = `hard`; `entire-report.txt:1-7` Claude 40%, GPT 100%; `docs/guidelines/difficulty.md` worst-model floor → Medium |
| 2 | ChatGPT: only blocker is difficulty metadata | **Partially agree** | Difficulty is primary blocker; rubric format (#34) is an additional High blocker in submitted rubrics |
| 3 | `entire-report.txt`: Task Instruction Sufficiency FAIL | **Disagree** (not a task blocker) | Agent-analysis artifact (`entire-report.txt:35-36`); LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:103`); M2 names `districts` (`steps/milestone_2/instruction.md:3`) |
| 4 | Agent analysis: cross-milestone schema gap M4 (`by_district` vs `districts`) | **Disagree** | `steps/milestone_2/instruction.md:3` specifies `districts` array; `solve4.sh:51` uses `summary.districts`; agent implementation error |
| 5 | Agent analysis: external doc dependency for bucket rules is unfair | **Disagree** | `steps/milestone_4/instruction.md:9` explicitly points to `/app/docs/district-review-format.md`; file ships in image (`environment/Dockerfile:27`) |
| 6 | Harbor review: non-canonical Node base image | **Disagree** (not a blocker) | `environment/Dockerfile:1` digest-pinned; no canonical Node image mandated in repo docs; warning only (`entire-report.txt:139-162`) |
| 7 | Harbor review: JS epsilon rounding vs Python Decimal | **Disagree** (not a blocker) | `solve1.sh:20-22` uses epsilon hack; oracle 100% (`entire-report.txt:11`); test data avoids edge cases |
| 8 | Harbor review: redundant solve.sh wrappers | **Disagree** (not a blocker) | Style suggestion only (`entire-report.txt:192-213`); both wrapper and solveN.sh work |
| 9 | LLMaJ: all 10 quality checks pass | **Agree** | `entire-report.txt:102-112` |
| 10 | Test quality: all 4 milestones ROBUST | **Agree** | `entire-report.txt:248-440` |
| 11 | Automated review: #1 instruction too long (798 words aggregate) | **Disagree** | Milestone layout: M1 116w, M2 109w (`wc -w`); per-milestone instructions are schema contracts, not aggregate bloat |
| 12 | Automated review: #14 unpinned pip | **Disagree** | `environment/requirements.txt:1` = `pytest==8.4.1`; installed via pinned requirements file |
| 13 | Automated review: #54 worst model 100% too easy | **Disagree** | Script bug: uses `max()` not `min()` for worst model; Claude 40% (`entire-report.txt:6`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Per-milestone: M1/M2 short; M3/M4 are dense schema specs (277–296w), acceptable for data-processing | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering tone (“We need a clean settlement feed…”) | `steps/milestone_1/instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions | Requirements only, no dev walkthrough | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes outputs/rules, not implementation | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables | No input→output tables in instructions | — |
| 7 | CHECK | Instruction is well specified | All output paths, fields, rounding, sort orders specified | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic meter-settlement pipeline | — |
| 9 | UNCHECK | Instruction is unique | Cannot verify against full TB2/TB3 corpus in this audit | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instructions | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY local data only | `environment/Dockerfile:24-27` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `pytest==8.4.1` in requirements.txt | `environment/requirements.txt:1` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:f3a68cf4…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context outside environment/ | All COPY from env subdirs | `environment/Dockerfile:24-27` |
| 17 | CHECK | Environment does not contain solution or ground truth | Docs are format contracts; catalog is input data | `environment/docs/*.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:14-18`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet | Node + sqlite3 local | `steps/milestone_1/solution/solve1.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Derives from raw events + catalog queries | `steps/milestone_1/solution/solve1.sh:15-40` |
| 24 | CHECK | test.sh writes reward.txt with failure path | mkdir + echo 0/1 pattern | `steps/milestone_1/tests/test.sh:11-20` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 only | `steps/milestone_1/tests/test.sh:16-19` |
| 27 | CHECK | All tests aligned with instructions | Full recomputation reference oracles mirror specs | `test_m1.py`–`test_m4.py`; LLMaJ pass `entire-report.txt:104` |
| 28 | CHECK | Tests check correctness, not just format | Deep equality on computed outputs | `test_m1.py:expected_rows()` etc. |
| 29 | CHECK | Tests verify behavior, not implementation | No source-code grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching | Numeric/structural equality on outputs | `test_m*.py` |
| 31 | CHECK | Tests have informative names or docstrings | Module + method docstrings present | `steps/milestone_*/tests/test_m*.py:1` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negative lines across rubric blocks | `entire-report.txt:454-494` |
| 33 | CHECK | Rubric scores from set {1,2,3,5,-1,-2,-3,-5} | All scores ±1,2,3,5 | `entire-report.txt:446-494` |
| 34 | UNCHECK | Each rubric criterion starts with Agent, comma, then score | Lines start with “Output file…” not “Agent …” | `entire-report.txt:446` |
| 35 | CHECK | Rubric criteria are detailed and precise | Field-level behavioral checks | `entire-report.txt:446-494` |
| 36 | CHECK | Rubric criteria use positive language | Penalties use negative scores, not “does not” positives | `entire-report.txt:454-494` |
| 37 | CHECK | Rubric does not reference /tests/ | No pytest/test path refs | `entire-report.txt:446-494` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:446-494` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:446-494` |
| 40 | CHECK | All required files present | Milestone layout with Dockerfile, solve, test, instruction, task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, subcategories, milestones, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | javascript/sql/bash data-processing with db_interaction | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`, observed Medium (worst 40%) | `task.toml:6`, `entire-report.txt:6` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/` | `task.toml:9`, `steps/` |
| 47 | CHECK | Each milestone has solveN.sh | solve1–solve4.sh present | `steps/milestone_*/solution/solve*.sh` |
| 48 | CHECK | Each milestone has test_mN.py | test_m1–test_m4.py present | `steps/milestone_*/tests/test_m*.py` |
| 49 | CHECK | Each milestone test scoped to that milestone | M1 tests normalization only; preservation tests in later milestones | `test_m1.py`–`test_m4.py` |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore` excludes tests/; no COPY tests | `environment/.dockerignore:17`, `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ and tests/ in .dockerignore | `environment/.dockerignore:16-17` |
| 52 | CHECK | Agent cannot trivially modify inputs | SHA-256 raw hash check in tests | `test_m1.py:12,98` |
| 53 | CHECK | Git repos pinned (no unpinned clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model Claude 40% | `entire-report.txt:6` |
| 55 | CHECK | Task is not too hard or unfair | Format docs in `/app/docs/`; failures are implementation not missing info | `environment/Dockerfile:27`, agent analysis `entire-report.txt:72-78` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 34, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: dedupe, filter, multiply, half-up 3dp, sort | `test_normalized_feed_matches_catalog_rules` | covered | `test_m1.py:53-90` |
| M1: exact schema types | `test_normalized_schema_is_exact` | covered | `test_m1.py` |
| M1: raw files unchanged | `test_source_event_files_are_unchanged` | covered | `test_m1.py:98` |
| M2: account_months rows + summary JSON | `test_settlement_database_rows_are_correct`, `test_summary_json_matches_database_totals` | covered | `test_m2.py` |
| M3: reconciliation union, statuses, nulls, adjustments | `test_reconciliation_report_matches_prior_ledger_union` | covered | `test_m3.py` |
| M3: all four statuses exercised | `test_reconciliation_report_exercises_all_statuses` | covered | `test_m3.py` |
| M4: district review rollups + buckets | `test_district_review_matches_expected_rollups` | covered | `test_m4.py` |
| M4: exception bucket priority rules | `test_exception_buckets_exercise_priority_rules` | covered | `test_m4.py` |
| M4: zero-count keys for all buckets/statuses | `test_district_counts_include_all_zero_count_keys` | covered | `test_m4.py` |
| Cross-milestone output preservation | `test_*_preserved` / `test_previous_outputs_are_preserved` | covered | `test_m2.py`–`test_m4.py` |

No spec↔test gaps found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, blocker 1 |
| `entire-report.txt` | #21, #45, #54, agent stats, rubrics, adjudication |
| `environment/Dockerfile` | #13–#20, #50 |
| `environment/requirements.txt` | #14 |
| `environment/.dockerignore` | #50, #51 |
| `steps/milestone_*/instruction.md` | #1–#12, #27 |
| `steps/milestone_*/tests/test_m*.py` | #27–#31, spec alignment |
| `steps/milestone_*/tests/test.sh` | #20, #24–#26 |
| `steps/milestone_*/solution/solve*.sh` | #22, #23 |
| `environment/docs/district-review-format.md` | adjudication claim 5 |
| `docs/guidelines/difficulty.md` | blocker 1 tier rules |
| `docs/guidelines/rubrics.md` | blocker 2 format rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260624/
Summary: 0 error(s), 1 warning(s), 4 info
WARNING: pinned_dependencies — false positive; requirements.txt pins pytest==8.4.1
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 40.0% (2/5) | Worst model — sets tier floor |
| terminus-gpt5-5 | 100.0% (5/5) | Above floor; does not make task “too easy” alone |
| oracle | 100.0% (3/3) | Consistent pass |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone Node/SQL data-processing task; report matches folder |
| 1 Instruction | ☑ | Per-milestone instructions + `/app/docs/` format contracts |
| 2 Environment | ☑ | Digest-pinned, tmux+asciinema, offline, no tests/solution in image |
| 3 Oracle | ☑ | Derives outputs; 100% per report |
| 4 Verifiers | ☑ | Canonical reward block; pytest reference oracles |
| 5 Metadata | ☑ | Blocker: difficulty mismatch only |
| 6 Rubric | ☑ | Blocker: missing `Agent` prefix on lines |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; agent failures are implementation not spec |
| 8 Novelty & fairness | ☑ | Multi-step pipeline; hash anti-cheat |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Milestone structure, digest-pinned Dockerfile, verifier setup, spec-to-test alignment, oracle pass rate, and anti-cheat measures all look solid. Two fixes before accept: (1) update `task.toml` `difficulty` from `hard` to `medium` — Claude worst-model pass rate is 40% (Medium tier, not Hard); (2) rewrite rubric lines to the required `Agent <behavior>, ±N` format (currently missing `Agent` prefix). No instruction, environment, or verifier blockers found.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Rubric | yes | 2 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
