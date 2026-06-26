# Terminus Review Report: `brfss-adult-cost-groupcv-imbalance-svywt`

**Generated:** 2026-06-25 (manual re-audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/brfss-adult-cost-groupcv-imbalance-svywt`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; not re-run — Docker unavailable locally) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** Structure, environment pinning, anti-cheat, oracle evidence, spec↔test alignment, and verifier design are solid. Prior human-revision notes on Dockerfile base image, instruction length, and `n_train`/`n_test` checks are **not** valid blockers on current artifacts. The **only real blocker** is metadata: `task.toml` declares `difficulty = "hard"` while agent evaluation places the task in the **Medium** tier (worst model Claude 60%). Update `difficulty` to `"medium"` or rebalance until Hard criteria are met.

**Insights (concise):**

- Canonical digest-pinned `public.ecr.aws` Python base with R + pytest baked at build time; `test.sh` has no runtime installs.
- `instruction.md` is exactly 3 paragraphs and delegates schema semantics to `/home/SCHEMA.md`; paragraph 3 lists required JSON keys but does not duplicate full nested contracts.
- `schema_metrics_counts_match_data` asserts `n_train`/`n_test` equal actual row counts — human claim #3 is false.
- Automated `terminus review` falsely flagged #14, #20, #31 and miscomputed worst-model rate as 80% (script uses `max()` not `min()`).
- Agent failures are execution/model-tuning errors, not systematic spec gaps; 60% Claude / 80% GPT-5.5 with 1/10 timeouts.
- Rubric criteria appear only in external report text; no `rubric.txt` in task folder (portal rubric items N/A).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared difficulty `hard` does not match observed Medium tier | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:36-37` Claude 60%, GPT-5.5 80%; `docs/guidelines/difficulty.md:9-12` worst-model 60% → Medium (20–60%) | Set `difficulty = "medium"` in `task.toml`, **or** harden task until worst-model ≤20% |

*No other High/Medium blockers found on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Dockerfile must switch to approved canonical ECR image (human reviewer #1) | **Disagree** | `environment/Dockerfile:1` already `FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367…` |
| 2 | `instruction.md` too long / schema-heavy; shorten to ≤3 paragraphs (human reviewer #2) | **Disagree** | `instruction.md` is 3 paragraphs; line 5 references `/home/SCHEMA.md` for full contract; detailed semantics live in `environment/SCHEMA.md` |
| 3 | Tests only check `n_train`/`n_test` key existence, not values (human reviewer #3) | **Disagree** | `tests/test_outputs.py:105-111` R check `schema_metrics_counts_match_data` asserts `nt == nrow(raw_train) && ns == nrow(raw_test)`; pytest wrapper `test_r_schema_metrics_counts_match_data` line 535-537 |
| 4 | Submitter rebuttals 1–3 are correct (entire-report lines 29) | **Agree** | Same proofs as rows 1–3 |
| 5 | Difficulty mismatch: declared Hard, evaluation Medium (ChatGPT) | **Agree** | `task.toml:6`; `entire-report.txt:31,36-37`; worst model = min(60%, 80%) = 60% → Medium per `difficulty.md` |
| 6 | Digest-pinned env, verifier setup, anti-cheat, oracle, schema, metric recomputation solid (ChatGPT) | **Agree** | `environment/Dockerfile`, `tests/test_outputs.py` CHECKS list, `entire-report.txt:158-168` LLMaJ all pass |
| 7 | Non-canonical Docker base / Python base for R task (LLMaJ warning) | **Disagree** (not a blocker) | Digest-pinned canonical ECR Python base; R via apt for agent toolchain; pytest venv for verifier — pragmatic dual-runtime pattern |
| 8 | `WORKDIR /home` non-standard (LLMaJ warning) | **Disagree** (not a blocker) | `task.toml:23` `workdir = "/home"`; all paths consistent across instruction/solution/tests |
| 9 | Agent timeout 900s may be tight (LLMaJ suggestion) | **Partially agree** (not a blocker) | `task.toml:20`; `entire-report.txt:45-48` only 1/10 agent timeouts; 60–80% pass rates show solvability |
| 10 | LLMaJ quality checks all pass (behavior_in_task_description, behavior_in_tests, anti_cheat, etc.) | **Agree** | `entire-report.txt:158-168` |
| 11 | Test quality review: ACCEPT, no material weaknesses | **Agree** | `entire-report.txt:306-315` |
| 12 | Automated review blockers #14, #20, #31 | **Disagree** | #14: `requirements.lock` uses `==` + hashes, installed via `--require-hashes`; #20: `pytest==8.4.1` in lock, installed Dockerfile:25, `test.sh` has no installs; #31: all 54 `test_*` functions have docstrings (module-level docstring absent = validator info only) |
| 13 | Automated review worst-model 80% → easy | **Disagree** | `scripts/review_checklist.py:167-169` uses `max(agent_rates)`; correct worst = Claude **60%** |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Exactly 3 paragraphs | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Opens "Hey, quick one"; engineer tone | `instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal/outputs, not dev steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (WHAT not HOW) | Challenge context only; no solve script | `instruction.md:3` |
| 6 | CHECK | No design doc style tables | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear outputs, paths, metrics, SCHEMA pointer | `instruction.md`, `SCHEMA.md` |
| 8 | CHECK | Instruction is interesting | Real survey-weighted ML with geographic shift | — |
| 9 | CHECK | Instruction is unique | BRFSS cost-sensitive group-CV task; no duplicate found in audit | — |
| 10 | CHECK | All paths absolute | `/home/data`, `/home/output`, `/home/SCHEMA.md` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No folder name string | `instruction.md` |
| 12 | CHECK | No canary string | None present | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content (except packages) | Build-time apt/R/pip only | `environment/Dockerfile` |
| 14 | CHECK | Python/pip deps pinned with == | `requirements.lock` hash-pinned `pytest==8.4.1`, etc. | `environment/requirements.lock:141` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | COPY only env artifacts | `environment/Dockerfile:27-30` |
| 17 | CHECK | No ground truth in environment | Test CSV lacks HAVEDIAB; labels in `/tests/eval` only | `environment/data/brfss_adult_test.csv` header |
| 18 | CHECK | No dangerous Docker operations | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | task layout |
| 20 | CHECK | Verifier deps baked in image; test.sh no runtime installs | pytest in image; `test.sh` only runs pytest | `Dockerfile:25`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:41` |
| 22 | CHECK | Oracle needs no internet | `solve.sh` runs local `analysis.R` | `solution/solve.sh` |
| 23 | CHECK | Oracle is real implementation | glmnet pipeline with CV, threshold tuning | `solution/analysis.R` |
| 24 | CHECK | test.sh reward.txt pattern | mkdir + 0/1 write | `tests/test.sh:11-19` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:15-18` |
| 27 | CHECK | Tests aligned with instructions | All instruction/SCHEMA reqs tested; data_* checks are env integrity | `tests/test_outputs.py`, `SCHEMA.md` |
| 28 | CHECK | Tests check correctness | Quality floors + metric recomputation | `tests/test_outputs.py:164-435` |
| 29 | CHECK | Behavior not implementation grep | R verifier on outputs, no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Literal `_STATE`/`_LLCPWT` required by contract | `SCHEMA.md:48-54` |
| 31 | CHECK | Informative test names/docstrings | 54/54 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics ≥3 negatives | N/A — no rubric file in task dir | — |
| 33 | UNCHECK | Rubric scores ∈ {±1,2,3,5} | N/A | — |
| 34 | UNCHECK | Rubric format Agent …, ±N | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no task.toml/instruction refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP mentions | N/A | — |
| 40 | CHECK | Required files present | All present | task layout |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task layout |
| 42 | CHECK | author_name/email present | Set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | version, timeouts, env fields | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | `languages=["r"]`, `category="machine-learning"` | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed pass rates | Declared `hard`, observed Medium (60% worst) | `task.toml:6`, `entire-report.txt:36-37` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | — |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | — |
| 49 | UNCHECK | Milestone tests scoped | N/A | — |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Ground truth not accessible in env | Eval labels verifier-only | `environment/Dockerfile`, `tests/eval/` |
| 52 | CHECK | Agent cannot trivially pass via input tampering | Quality floors require real cross-state classifier | `tests/test_outputs.py` quality checks |
| 53 | CHECK | Git repos pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 60% | `entire-report.txt:36-37` |
| 55 | CHECK | Not too hard/unfair | Solvable; failures are agent execution/tuning | `entire-report.txt:106-155` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / SCHEMA) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Write `/home/output/predictions.csv` with required columns, sorted, full coverage | `test_predictions_file_has_rows`, `test_r_schema_*` | covered | `instruction.md:5`, `tests/test_outputs.py:473-557` |
| Write `/home/output/metrics.json` with all top-level keys | `test_r_schema_metrics_keys_present` | covered | `instruction.md:5`, `SCHEMA.md:19-54` |
| `n_train`/`n_test` match actual row counts | `test_r_schema_metrics_counts_match_data` | covered | `tests/test_outputs.py:105-111` |
| CV-reported metrics within tolerance of held-out recomputation | `test_r_anticheat_*_matches_recomputed` | covered | `SCHEMA.md:28-34`, `tests/test_outputs.py:154-395` |
| Quality floors (BA, AUROC, Brier, cost, subgroup BA, minority recall/precision) | `test_r_quality_*` | covered | `SCHEMA.md:60-62`, `tests/test_outputs.py:164-435` |
| Cost matrix FN > FP; threshold in (0,1); survey design field literals | `test_r_anticheat_cost_matrix_*`, `test_r_anticheat_weight_psu_strata_fields_named` | covered | `instruction.md:3,5`, `tests/test_outputs.py:212-263` |
| Geographic split by `_STATE`; zero overlap | `test_r_anticheat_group_field_is_state`, `test_r_anticheat_n_overlap_states_is_zero` | covered | `instruction.md:3`, `tests/test_outputs.py:230-241` |
| Anti-cheat: variance, no train leakage, no perfect BA | `test_r_anticheat_predictions_have_variance`, `test_r_anticheat_no_train_rows_in_predictions`, `test_r_anticheat_balanced_accuracy_not_suspiciously_perfect` | covered | `tests/test_outputs.py:133-172` |
| Reference data integrity (codebook, weights, rotation) | `test_r_data_*` | covered (env sanity) | Bundled data consistency; not agent-output reqs |

No spec gaps or phantom agent requirements identified.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #44, #45, blocker 1 |
| `instruction.md` | #1-12, #27 |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/SCHEMA.md` | #27, spec alignment |
| `environment/requirements.lock` | #14, #20 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, spec alignment, blocker adjudication row 3 |
| `solution/analysis.R` | #23 |
| `entire-report.txt` | #21, #45, #54, agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate brfss-adult-cost-groupcv-imbalance-svywt/
Summary: 0 error(s), 2 warning(s), 2 info
- WARN pinned_dependencies: false positive (hash-locked requirements.lock)
- WARN informative_test_docstrings: module-level docstring missing (all test functions documented)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% | 4/5 runs |
| terminus-claude-opus-4-8 | 60.0% | 3/5 runs; **worst model** |
| oracle | 100.0% | 3/3 runs |
| nop | 0.0% | 0/1 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; R ML task |
| 1 Instruction | ☑ | 3 paragraphs; SCHEMA delegation valid |
| 2 Environment | ☑ | Canonical digest base; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Real R pipeline; 100% per report |
| 4 Verifiers | ☑ | Canonical reward; 54 pytest + R CHECKS; no runtime installs |
| 5 Metadata | ☐ | **Blocker:** difficulty mismatch |
| 6 Rubric | ☑ | N/A — rubric in portal only |
| 7 Agent evidence | ☑ | Medium tier; solvable; 1 timeout |
| 8 Novelty & fairness | ☑ | Multi-step ML; anti-cheat strong |
| 9 Long context | ☑ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The digest-pinned Python/R environment, verifier setup, anti-cheat design, oracle pass rate, output schema, and metric recomputation checks look solid. The earlier Dockerfile, instruction-length, and n_train/n_test concerns are not valid blockers in the current files. The remaining issue is the difficulty mismatch: the task is labeled Hard while live evaluation supports Medium (Claude 60%, GPT-5.5 80%). Update `difficulty` to `medium` in `task.toml` or rebalance until the task qualifies as Hard.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Test Dependency Location | no | — |
| Oracle Solution Issues | no | — |
| Agent Timeout | no | — |
