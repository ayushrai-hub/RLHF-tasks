# Terminus Review Report: meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260626

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; local harbor run failed — config error) |
| **CHECK count** | 52 |
| **UNCHECK count** | 3 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are solid: five-milestone Node/SQLite pipeline, digest-pinned environment, offline pytest verifiers, spec-to-test alignment, and declared `medium` difficulty match worst-model Claude at 60%. The sole High blocker is the portal rubric (lines 476–528 of `entire-report.txt`): 45 criteria lines, zero `Agent` prefixes, zero negative penalties — both violate `docs/guidelines/rubrics.md` and reviewer-checklist High rules. Automated script false-positives on instruction length (aggregated all milestones), pip pinning (`requirements.txt` is pinned), and difficulty (used GPT-5.5 100% instead of worst-model 60%) were rejected.

**Insights (concise):**

- ChatGPT rubric finding is correct and is the only real blocker; task structure, tests, and env need no revision.
- Per-milestone instructions are 167–316 words each (not 1344 aggregate); appropriate for milestone data-pipeline specs.
- `environment/requirements.txt` pins `pytest==8.4.1`; Dockerfile `-r` install is correctly pinned via file.
- Worst-model pass rate is Claude 60% (medium tier); GPT-5.5 at 100% does not override tier rules.
- Oracle scripts derive outputs computationally (Node + sqlite3); `entire-report.txt` reports 3/3 oracle pass.
- Non-canonical Node base is digest-pinned and justified; warning only, not a numbered checkbox failure.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32, #34, #36 | Portal rubric has 0 `Agent`-prefixed lines and 0 negative penalties (needs ≥3) | `entire-report.txt:476-528`; `docs/guidelines/rubrics.md:37-47,71-77` | Rewrite every criterion as `Agent <trace behavior>, ±N`; add ≥3 negatives (e.g. corrupting prior outputs, skipping catalog join, using relative paths) |

*No other High blockers — automated failures on #1, #14, #45, #54 were disproven (see section 3).*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Rubric criteria need `Agent <behavior>, ±N` format, not bare outcomes (ChatGPT High) | **Agree** | `entire-report.txt:477` `Output file /app/output/normalized-events.jsonl exists...` — 0/45 lines start with `Agent` |
| 2 | Milestone structure, digest-pinned Node env, offline verifier, medium difficulty, oracle, spec-to-test alignment solid (ChatGPT) | **Agree** | `task.toml:6-12,21`; `environment/Dockerfile:1,14-18`; `steps/milestone_*/tests/test.sh`; `entire-report.txt:18-108` |
| 3 | Instruction length blocker — 1344 words (automated review) | **Disagree** | Per-milestone: M1 275w, M2 167w, M3 277w, M4 316w, M5 309w (`wc -w steps/milestone_*/instruction.md`); milestone layout evaluates per-step prompts per `docs/guidelines/milestones.md:35-39` |
| 4 | Unpinned pip dependencies (automated review #14) | **Disagree** | `environment/requirements.txt:1` `pytest==8.4.1`; Dockerfile installs from pinned requirements file |
| 5 | Difficulty mismatch — worst-model 100% (automated review #45/#54) | **Disagree** | `entire-report.txt:23-24` Claude 60% is worst model; `task.toml:6` `difficulty = "medium"` matches `docs/guidelines/difficulty.md:10` (20–60% worst) |
| 6 | Non-canonical base image warning (`entire-report.txt`) | **Partially agree** | `environment/Dockerfile:1` uses `public.ecr.aws/.../node:22-bookworm-slim@sha256:...` not ghcr.io canonical; digest-pinned and Node-specific — acceptable per `docs/reviewer-checklist-full.md:44` |
| 7 | Oracle float epsilon rounding fragile (`entire-report.txt` warning) | **Agree (non-blocking)** | `steps/milestone_1/solution/solve1.sh:20-22` `round3` uses `1e-12` hack; tests pass; oracle robustness note only |
| 8 | All LLMaJ quality checks pass (`entire-report.txt:99-108`) | **Agree** | Spot-checked M1–M5 instructions vs `test_m1.py`–`test_m5.py` reference oracles; behavior_in_task_description and behavior_in_tests hold |
| 9 | Agent failures operational, not spec gaps (`entire-report.txt:78-80`) | **Agree** | Failures at M2 (`settlement.db` empty/missing columns) from terminal/state issues, not missing spec for `event_count` (`steps/milestone_2/instruction.md:3`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Per-milestone prompts 167–316 words; aggregate 1344w is invalid for milestone layout | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering tone ("We need a clean settlement feed…"); no LLM scaffolding | `steps/milestone_1/instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no ##/tables/code blocks | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No "first run ls" patterns | — |
| 5 | CHECK | No hints or solving strategies | Specifies outputs/rules, not implementation walkthrough | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instructions | — |
| 7 | CHECK | Instruction is well specified | All output paths, fields, rounding, sort orders named per milestone | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting | Real meter-settlement pipeline domain | — |
| 9 | CHECK | Instruction is unique | Multi-milestone Node/SQLite settlement pipeline; not a trivial duplicate pattern | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instructions | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY local dirs only | `environment/Dockerfile:24-27` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1` in requirements file | `environment/requirements.txt:1` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | FROM digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY within environment/ | `environment/Dockerfile:24-27` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Catalog/seed is input fixture; no solution COPY | `environment/.dockerignore:16-17` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv+pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:14-18`, `steps/milestone_1/tests/test.sh:13` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:28` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solveN.sh uses local node/sqlite3 | `steps/milestone_1/solution/solve1.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Computational Node pipelines, not echo | `steps/milestone_*/solution/solveN.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `steps/milestone_1/tests/test.sh:11-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward.txt | `steps/milestone_1/tests/test.sh:16-19` |
| 27 | CHECK | All tests are aligned with instructions | Reference oracles mirror instruction rules per milestone | `steps/milestone_2/tests/test_m2.py:276`, `steps/milestone_2/instruction.md:3` |
| 28 | CHECK | Tests check for correctness, not just format | Full equality vs reference computation | `steps/milestone_1/tests/test_m1.py:178-179` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Numeric/schema equality appropriate for settlement outputs | `steps/milestone_3/tests/test_m3.py:350` |
| 31 | CHECK | Tests have informative names or docstrings | All test_* have docstrings | `steps/milestone_1/tests/test_m1.py:175-208` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | 0 negative lines in portal rubric | `entire-report.txt:476-528` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Only +1,+2,+3,+5 used; no ±4 | `entire-report.txt:476-528` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | 0/45 lines start with `Agent` | `entire-report.txt:477` |
| 35 | CHECK | Rubric criteria are detailed and precise | Outcome descriptions are specific (field names, rules) | `entire-report.txt:477-528` |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | No negative criteria exist to satisfy phrasing rules | `entire-report.txt:476-528` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ or pytest refs | `entire-report.txt:476-528` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:476-528` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP refs | `entire-report.txt:476-528` |
| 40 | CHECK | All required files present | steps/ milestone layout + Dockerfile + task.toml | `task.toml`, `steps/milestone_1/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, milestones, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable | javascript/sql/bash, data-processing, db_interaction | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | medium declared; worst-model Claude 60% → medium | `task.toml:6`, `entire-report.txt:23-24` |
| 46 | CHECK | steps/ layout present with per-milestone files | 5 milestones under steps/ | `task.toml:9,24-67` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1.sh–solve5.sh present | `steps/milestone_*/solution/solveN.sh` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1.py–test_m5.py present | `steps/milestone_*/tests/test_mN.py` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | TestMilestoneN classes score one step | `steps/milestone_*/tests/test_mN.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | .dockerignore excludes tests/ | `environment/.dockerignore:17` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ excluded; tests mounted at runtime | `environment/.dockerignore:16-17` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | SHA-256 integrity on raw events | `steps/milestone_1/tests/test_m1.py:174` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% ≤ 80% | `entire-report.txt:23-24` |
| 55 | CHECK | Task is not too hard or unfair | Spec complete; agent failures operational per report | `entire-report.txt:78-80` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 34, 36 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: dedup by revision/priority/received_at | `test_normalized_feed_matches_catalog_rules` | covered | `steps/milestone_1/instruction.md:3`, `steps/milestone_1/tests/test_m1.py:178` |
| M1: quality/active-meter filter | `test_filtered_and_duplicate_events_do_not_leak` | covered | `steps/milestone_1/instruction.md:3`, `steps/milestone_1/tests/test_m1.py:207` |
| M1: service_month cutover + billing_band peak rules | `test_normalized_feed_matches_catalog_rules` | covered | `steps/milestone_1/instruction.md:5`, `steps/milestone_1/tests/test_m1.py:178` |
| M2: account_months 8 columns incl. event_count | `test_settlement_database_schema_is_usable` | covered | `steps/milestone_2/instruction.md:3`, `steps/milestone_2/tests/test_m2.py:296` |
| M2: half-up rounding kWh/cents + rate lookup | `test_settlement_database_rows_are_correct` | covered | `steps/milestone_2/instruction.md:3`, `steps/milestone_2/tests/test_m2.py:276` |
| M3: four statuses + null handling + union keys | `test_reconciliation_report_matches_prior_ledger_union` | covered | `steps/milestone_3/instruction.md:3-9`, `steps/milestone_3/tests/test_m3.py:350` |
| M4: review_bucket priority + null preservation | `test_exception_buckets_exercise_priority_rules` | covered | `steps/milestone_4/instruction.md:9-11`, `steps/milestone_4/tests/test_m4.py:472` |
| M5: bucket→action mapping + posting_direction | `test_posting_actions_match_exception_handoff_rules` | covered | `steps/milestone_5/instruction.md:5-7`, `steps/milestone_5/tests/test_m5.py:611` |
| M5: action_counts/posting_direction_counts key order | `test_action_counts_mapping_and_null_preservation` | covered | `steps/milestone_5/instruction.md:7`, `steps/milestone_5/tests/test_m5.py:616` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `entire-report.txt` | #21, #32-39, #45, #54, adjudication rows 1-2, 8-9 |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/requirements.txt` | #14 |
| `environment/.dockerignore` | #17, #50-51 |
| `task.toml` | #42-46, #45 |
| `steps/milestone_*/instruction.md` | #1-12, #27, spec alignment |
| `steps/milestone_*/tests/test_m*.py` | #27-31, #49, #52 |
| `steps/milestone_*/tests/test.sh` | #20, #24-26 |
| `steps/milestone_*/solution/solveN.sh` | #22-23 |
| `docs/guidelines/rubrics.md` | Blocker 1, #32-36 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260626
Summary: 0 error(s), 1 warning(s), 5 info
WARNING: pinned_dependencies — pip install -r (false positive; requirements.txt pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | `entire-report.txt:24` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model |
| oracle | 100.0% (3/3) | `entire-report.txt:28` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; 5-milestone Node/SQLite task |
| 1 Instruction | ☑ | Per-milestone prompts well-specified; no hints/canary |
| 2 Environment | ☑ | Digest-pinned Node image; tmux/asciinema; offline pytest venv |
| 3 Oracle | ☑ | Computational solveN.sh; 3/3 pass per report |
| 4 Verifiers | ☑ | Binary reward; reference oracles; docstrings present |
| 5 Metadata | ☑ | medium difficulty matches worst-model 60% |
| 6 Rubric | ☐ | Portal rubric fails Agent format + negatives |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; failures operational |
| 8 Novelty & fairness | ☑ | Multi-step pipeline; cheating paths closed |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The five-milestone structure, digest-pinned Node environment, offline verifier setup, spec-to-test alignment, oracle pass rate, and medium difficulty calibration all look solid. The remaining blocker is rubric formatting in the portal submission: all 45 criteria are bare outcomes (e.g. "Output file … exists") with no `Agent` prefix and no negative penalties. Rewrite each line as `Agent <behavior>, ±N` per rubrics.md and add at least three negative trace-evidenced penalties before resubmitting.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
