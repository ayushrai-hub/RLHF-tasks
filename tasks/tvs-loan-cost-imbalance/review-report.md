# Terminus Review Report: `tvs-loan-cost-imbalance`

**Generated:** 2026-06-29  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/tvs-loan-cost-imbalance`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong cost-sensitive R/ML task with precise output contracts, digest-pinned offline environment, and robust metric/cost re-estimation verifiers. One main blocker: platform rubric positive total is **43** (cap **40**). Task uses correct **flat** non-milestone rubric format (no `# Rubric N` headers). Trim or merge at least three positive points before accept.

**Insights (concise):**

- Contracts under `/app/contracts/` fully specify output schemas; instruction directs agents to read them (`instruction.md:6`).
- Verifiers recompute ROC-AUC, PR-AUC, Brier, costs, and threshold optimality from submitted predictions (`tests/test_outputs.py:178–311`).
- `requirements.lock` pins pip packages with `==` and SHA256 hashes; Dockerfile installs via `--require-hashes` (`environment/Dockerfile:28-29`, `environment/requirements.lock:4+`).
- Worst-model pass rate 40% (Claude Opus 4.8) → medium tier; not too easy (`entire-report.txt:20-22`).
- Agent failures were contract-schema mismatches and file-management errors, not spec gaps (`entire-report.txt:78-127`).
- `TestSource` greps `/app/analysis.R` for keywords — supplementary to output-based tests (`tests/test_outputs.py:98-381`); portal #29 fails but is not a disposition driver alone.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric positive total **43** exceeds **40** cap for non-milestone tasks | `entire-report.txt:363-382` — 17 positive lines summing to 43 (+3×7, +2×10); `task.toml:12` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:29-35` | Trim or merge positive criteria until total ≤40 (e.g. drop one +3 and one +2, or merge related +2 items) |

*No other High-severity blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High/Medium blockers; Accept (ChatGPT) | **Partially agree** | Agree on spec/env/verifier quality; **disagree on Accept** — rubric 43 > 40 is a mandatory Revise blocker per `docs/guidelines/rubrics.md:35` |
| 2 | Rubric positive total 43, slightly above ≤40; Low only (ChatGPT) | **Disagree on severity** | 43 > 40 is **High** main blocker, not Low (`prompt.md:377-378`, `rubrics.md:35`) |
| 3 | Dockerfile digest-pinned; canonical Python + apt R justified (ChatGPT) | **Agree** | `environment/Dockerfile:1-4` `@sha256:01f42367…`; comment justifies R via apt |
| 4 | Contract files sufficient; agent failures from skipping contracts (ChatGPT / entire-report) | **Agree** | `instruction.md:6` mandates reading `/app/contracts`; failures used invented key names (`entire-report.txt:88-89`) — agent error, not spec gap |
| 5 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` pass | **Agree** | `entire-report.txt:130-131`; verified key behaviors have matching tests |
| 6 | LLMaJ `structured_data_schema` pass via contracts | **Agree** | `environment/contracts/metrics.md`, `predictions.md`, `cost_report.md` |
| 7 | Instruction sufficiency FAIL (agents skipped contracts) | **Partially agree** | Instruction is sufficient when contracts are read; brittle without contract read is agent failure mode, not untestable spec — not a Revise driver |
| 8 | Harbor review READY TO USE | **Partially agree** | Task artifacts are strong; rubric cap violation blocks accept |
| 9 | Test quality ACCEPT; source keyword checks gameable | **Agree** | `entire-report.txt:267-329`; metric-quality gates dominate over `TestSource` |
| 10 | Non-milestone task in milestone rubric format (user query) | **Disagree** | Rubric is flat `Agent …, ±N` list with **no** `# Rubric N` headers (`entire-report.txt:363-386`); correct for `number_of_milestones = 0` (`task.toml:12`, `rubrics.md:66`) |
| 11 | Automated `terminus review` #14 pip unpinned fail | **Disagree** | `requirements.lock` uses `==` + hashes; `Dockerfile:29` `--require-hashes -r requirements.lock` |
| 12 | Automated `terminus review` #36 rubric negative phrasing fail | **Disagree** | `Agent does not run…, -5` is valid bad-behavior penalty; anti-pattern is `does not …, +1` (`entire-report.txt:385`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 4 prose paragraphs, ~569 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Human lending-problem narrative | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | Requirements without implementation steps | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Describes WHAT (classifier, outputs, cost rule) | `instruction.md:2-8` |
| 6 | CHECK | No design-doc tables | No input→output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, paths, cost model, contracts | `instruction.md:2-8` |
| 8 | CHECK | Interesting/useful | Real cost-sensitive credit-risk ML | `instruction.md:1-4` |
| 9 | CHECK | Unique | Distinctive contracts + asymmetric cost + R pipeline | task content |
| 10 | CHECK | Absolute paths only | All paths `/app/...` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No `tvs-loan-cost-imbalance` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web fetch in env code | Data/contracts copied locally | `environment/Dockerfile:34-35` |
| 14 | CHECK | Pip deps pinned with == | `requirements.lock` uses `==` + SHA256 hashes | `environment/requirements.lock:4+`, `Dockerfile:29` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:4` |
| 16 | CHECK | Context in environment/ only | COPY `data/`, `contracts/` only | `environment/Dockerfile:34-35` |
| 17 | CHECK | No ground truth in env | Contracts are schemas; no answer leakage | `environment/contracts/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter harbor mounts | No docker-compose.yaml | task root |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest/sklearn in image; test.sh runs pytest only | `Dockerfile:26-29`, `tests/test.sh:9` |
| 21 | UNCHECK | Oracle passes consistently | Docker unavailable locally; static review only | oracle run failed |
| 22 | CHECK | Oracle no internet | `solve.sh` copies R script and runs locally | `solution/solve.sh:4-6` |
| 23 | CHECK | Oracle derives results | Full ML pipeline in `solution/analysis.R` | `solution/analysis.R:17-80+` |
| 24 | CHECK | test.sh writes reward.txt | Canonical 0/1 block | `tests/test.sh:9-14` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | Writes 0 or 1 | `tests/test.sh:10-13` |
| 27 | CHECK | Tests aligned with instructions | All instruction reqs traced to tests/contracts | §5 below |
| 28 | CHECK | Tests check correctness | Recomputes metrics/costs from predictions | `tests/test_outputs.py:178-311` |
| 29 | UNCHECK | Tests verify behavior not implementation | `TestSource` reads/greps `analysis.R` | `tests/test_outputs.py:98-103,314-381` |
| 30 | CHECK | No brittle exact-string matching | Numeric tolerances on metrics/costs | `tests/test_outputs.py:182-280` |
| 31 | CHECK | Informative test docstrings | Every `test_*` has docstring | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 negatives (-3×3, -5×2, -2×1) | `entire-report.txt:369-386` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | All lines use allowed magnitudes | `entire-report.txt:363-386` |
| 34 | CHECK | Rubric format `Agent …, ±N` | Flat non-milestone list; note `Agent's` on L376 may confuse parsers | `entire-report.txt:363-386` |
| 35 | UNCHECK | Rubric detailed; 10–40 positive pts | **43 positive points** exceeds cap | `entire-report.txt:363-382` |
| 36 | CHECK | Rubric positive language | Negatives use `-N` for bad behavior; no `does not …, +1` | `entire-report.txt:385` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:363-386` |
| 38 | CHECK | Rubric no task.toml/instruction.md refs | Says "the instructions" but not `instruction.md` filename | `entire-report.txt:372,376` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:363-386` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author_name/email present | `anonymous` fields | `task.toml:8-9` |
| 43 | CHECK | Other metadata fields present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category match | `machine-learning`, `languages=["r"]`, finance tags | `task.toml:5-21` |
| 45 | CHECK | Difficulty field present | `difficulty=hard`; platform=medium; not a blocker | `task.toml:4`, `entire-report.txt:16` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:14` |
| 51 | CHECK | Solution not in environment | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Instruction forbids modifying data; tests use fixed split | `instruction.md:8` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤ 80% | `entire-report.txt:20-22` |
| 55 | CHECK | Not too hard/unfair | Contracts + reference data provided; failures were agent errors | `entire-report.txt:78-127` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 21, 29, 35, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contracts) | Test(s) | Status | Proof |
|---------------------------------------|---------|--------|-------|
| Write metrics.json, predictions.csv, cost_report.json to /app/outputs/ | `test_all_artifacts_exist` | covered | `instruction.md:6`, `test_outputs.py:122-129` |
| Read /app/contracts for exact schemas | `test_metrics_top_level_schema`, `test_predictions_columns` | covered | `instruction.md:6`, `test_outputs.py:131-159` |
| Fixed split from split.csv | `test_n_test_matches_split`, `test_row_id_set_matches_test_split` | covered | `instruction.md:2`, `test_outputs.py:149-163` |
| Cost FN=20, FP=1 | `test_cost_matrix_values` | covered | `instruction.md:4`, `test_outputs.py:238-241` |
| Threshold sweep; minimize cost | `test_sweep_argmin_is_chosen` | covered | `instruction.md:4`, `test_outputs.py:282-288` |
| Chosen cost beats 0.5 and approve-all | `test_policy_beats_half`, `test_policy_beats_predict_all_negative` | covered | `instruction.md:4`, `test_outputs.py:301-311` |
| Class-imbalance handling | `test_imbalance_handling_present`, `test_minority_recall_above_floor` | covered | `instruction.md:2`, `test_outputs.py:229-335` |
| Informative missingness (bureau cols) | `test_missing_handling_present` | covered | `instruction.md:1`, `test_outputs.py:337-349` |
| Categorical encoding | `test_encoding_present` | covered | `instruction.md:1-2`, `test_outputs.py:351-356` |
| Exclude V1; V16 redundant | `test_identifier_referenced`, `test_top_feature_is_real_column` | covered | `instruction.md:1`, `test_outputs.py:213-217,378-380` |
| Metrics recomputed from predictions | `test_reported_*_matches_*` | covered | `instruction.md:6`, `test_outputs.py:178-211` |
| ROC/PR vs reference model | `test_roc_auc_not_far_below_reference`, `test_pr_auc_not_far_below_reference` | covered | `instruction.md:6`, `test_outputs.py:221-227` |
| Create /app/analysis.R | `TestSource` fixtures read `ANALYSIS` | covered | `instruction.md:8`, `test_outputs.py:24,98-103` |
| Sort predictions by row_id | `test_row_id_sorted` | covered | `instruction.md:6` (via contracts), `test_outputs.py:165-167` |
| Threshold well below 0.5 | — | gap (minor) | Instruction `instruction.md:4`; only cost/recall indirectly tested |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, #55, spec alignment |
| `task.toml` | #42-45, #46-49 N/A, milestone format |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/requirements.lock` | #14 |
| `environment/contracts/*.md` | #17, #27, spec alignment |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #29 UNCHECK |
| `solution/solve.sh`, `solution/analysis.R` | #22-23 |
| `entire-report.txt` | #32-39, #45, #54, rubric blocker, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tvs-loan-cost-imbalance/
Summary: 0 error(s), 1 warning(s), 1 info
Task type detected: regular
WARNING: pinned_dependencies — pip install line lacks inline == (false positive; requirements.lock has == + hashes)
INFO: non-milestone task (milestones preferred, not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | `entire-report.txt:22` |
| terminus-claude-opus-4-8 | 40% (2/5) | `entire-report.txt:21` |
| oracle | 100% (3/3) | `entire-report.txt:26` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml:4`) |
| Platform classified | medium (`entire-report.txt:16`) |
| Tier match (#45) | informational only — CHECK |

### Rubric positive points

| Field | Value |
|-------|-------|
| Source | `entire-report.txt:363-382` |
| Positive point total | **43** |
| Positive line count | 17 |
| Cap | 40 |
| Status | **FAIL (>40)** |
| Milestone format | **No** — flat list, no `# Rubric N` headers (correct for non-milestone) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular R/ML task; report matches folder |
| 1 Instruction | ☑ | Concise, absolute paths, contracts referenced |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Static review: full pipeline; docker oracle not run |
| 4 Verifiers | ☑ | reward.txt OK; TestSource is implementation grep (#29) |
| 5 Metadata | ☑ | `number_of_milestones=0`, `languages=["r"]`, `allow_internet=false` |
| 6 Rubric | ☑ | **43 > 40 blocker**; flat format OK (not milestone headers) |
| 7 Agent evidence | ☑ | 40% worst-model; contract-read failures = agent error |
| 8 Novelty & fairness | ☑ | Multi-step ML; anti-cheat via metric recomputation |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task — the cost-sensitive framing, output contracts, and verifier design that recomputes metrics and costs from predictions are all excellent, and the offline pinned environment looks solid. One fix before we can accept: the platform rubric has **43** positive points and needs to be trimmed to **40 or fewer** (merge or drop a few of the +2/+3 items). The rubric format itself is fine as a flat non-milestone list. Optional polish: rephrase the `Agent's chosen threshold…` line to start with `Agent` (not `Agent's`) so automated parsers count it reliably.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review tvs-loan-cost-imbalance/ --report entire-report.txt`._
