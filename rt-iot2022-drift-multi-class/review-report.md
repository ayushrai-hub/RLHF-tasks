# Terminus Review Report: `rt-iot2022-drift-multi-class`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report 100%; not re-run locally) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Strong RT-IoT2022 multiclass ML task with digest-pinned Python base, pinned `requirements.txt`, independent reference recomputation, and correct flat (non-milestone) rubric format. One substantive blocker: numeric PSI proportion denominator is tested exactly via `reference_outputs.py` but instruction wording (“that split total”) reasonably reads as row count, while the verifier uses `max(histogram_count_sum, 1.0)`. Automated script false-positives on #14/#20 were overturned after manual audit. Harbor “test.sh re-runs analysis.py” and split-iteration-order claims are not blockers.

**Insights (concise):**

- PSI exact-value tests (`test_drift_values_match[psi]`, `test_float_metrics_match[drift_psi_*]`) fail at 3/10 runs — systematic spec gap, not agent noise.
- `+1e-9` scope is already explicit (fallback linspace only); vMV3B27 misread is agent error, not a spec gap.
- Per-class split is order-independent after ascending concat; `groupby(sort=False)` is reference detail, not a tested unstated requirement.
- `test.sh` re-running `/app/analysis.py` is intentional reproducibility; `wall_clock_sec` is not exact-tested.
- Rubric is flat `Agent …, ±N` (correct for `number_of_milestones = 0`); not milestone-header format.
- `#14`/`#20` automated fails are false: `environment/requirements.txt` pins all packages including `pytest==8.4.2`, installed in Dockerfile.
- Instruction is long (~772 words) but schema depth is justified; length is a note, not a revision driver here.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #55 | Numeric PSI proportion denominator underspecified vs exact verifier | `instruction.md:15` says “convert counts to proportions using **that split total** or 1.0”; `tests/reference_outputs.py:122-123` uses `ac / max(ac.sum(), 1.0)` and `bc / max(bc.sum(), 1.0)` (histogram count sums, not `len(train)`/`len(test)`). Values outside quantile edges are excluded from `np.histogram` bins, so sums differ. Agent report: nxQqUeb 49/67 on denominator; vMV3B27 63/67 on PSI only; `test_drift_values_match[psi]` 3/10 passes. | Clarify: normalize each side by `max(sum of histogram bin counts for that side, 1.0)` (not raw split row count). Optionally note out-of-range values are excluded from bin counts. |

*No other High/Medium blockers after manual audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | PSI denominator ambiguous: split total vs `max(histogram_sum, 1.0)` (ChatGPT High) | **Agree** | `instruction.md:15` vs `tests/reference_outputs.py:120-123`; `entire-report.txt` Pattern B / nxQqUeb |
| 2 | `+1e-9` only on fallback path not explicit enough (ChatGPT / agent report) | **Disagree** | `instruction.md:15` ties `+1e-9` to “if fewer than 3 edges remain, use 11 evenly spaced edges … plus 1e-9”; `reference_outputs.py:118-119` matches; main quantile path has no `+1e-9` |
| 3 | Split iteration order (`groupby(sort=False)`) unstated (entire-report Pattern A) | **Disagree** | `reference_outputs.py:59-70` concatenates per-class indices then `np.sort`; class iteration order cannot change final `train_idx`/`test_idx` sets |
| 4 | `test.sh` re-running `/app/analysis.py` is a blocker (Harbor REVIEW REPORT Critical) | **Disagree** | `tests/test.sh:8-11` wipes outputs and re-runs script; task requires working `/app/analysis.py` (`instruction.md:3`); pipeline is deterministic (`random_state=7002`); `wall_clock_sec` not exact-tested (`tests/test_outputs.py` schema only); canonical pattern deviation is acceptable here |
| 5 | Agent timeout 1500s < verifier 1800s (ChatGPT Low / Harbor Warning) | **Disagree** (not a blocker) | `task.toml:17-20`; 2/10 agent timeouts, under gate; informational only |
| 6 | Rubric should add positives for metrics.json / predictions.csv / drift_report.csv (ChatGPT Low) | **Disagree** (not a blocker) | Platform rubric 17 positive pts, 3 negatives — within 10–40; optional enrichment only |
| 7 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; platform rubric is flat `Agent …, ±N` with no `# Rubric 2+` headers — correct per `docs/guidelines/rubrics.md:64` |
| 8 | `#14` unpinned pip / `#20` pytest not in image (automated review) | **Disagree** | `environment/requirements.txt:1-6` all `==`; Dockerfile `COPY` + `pip install -r`; pytest baked in image |
| 9 | `#11` task name in instruction (automated review) | **Partially agree** (portal only) | `instruction.md:3` requires `task_name` literal `rt-iot2022-drift-multi-class` — required output field, not canary; single Medium, not revision driver |
| 10 | Instruction too long `#1` (automated review) | **Partially agree** (note only) | ~772 words, 9 blank-line blocks; exceeds concise guideline but necessary for six-artifact ML schema; not listed as blocker |
| 11 | LLMaJ `behavior_in_task_description` PASS | **Agree** with caveat | Broad pass holds except PSI denominator nuance |
| 12 | Test quality ROBUST / ACCEPT | **Agree** | Independent `reference_outputs.py` recomputation; fair given PSI spec fix |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~772 words, 9 blocks — exceeds concise guideline | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer handoff tone, no LLM boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no ##/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Specifies outputs/algorithms, not terminal steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Hyperparameters are normative spec for exact-value grading | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Six artifacts, paths, schemas, model/split defined | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Real IoT intrusion multiclass + drift pipeline | `instruction.md` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | RT-IoT2022 drift multiclass combination is distinctive | task content |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md` |
| 11 | UNCHECK | Task name does not appear in instruction.md | Folder name appears as required `task_name` output value | `instruction.md:3` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `requirements.txt` pins all packages with `==` | `environment/requirements.txt`, `environment/Dockerfile:8-9` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned `python:3.13-slim-bookworm` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only under environment/ | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Starter `analysis.py` is intentionally broken; contracts are structural metadata | `environment/analysis.py`, `environment/.dockerignore` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in `requirements.txt`; no pip in `test.sh` | `environment/requirements.txt:5`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Platform oracle 100% (3/3) | `entire-report.txt` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` copies and runs local script | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full pipeline in `solution/analysis.py` | `solution/analysis.py` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:2-16` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 0` / `echo 1` only | `tests/test.sh:12-15` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | PSI denominator semantics tested but not fully specified | `instruction.md:15`, `tests/reference_outputs.py:122-123` |
| 28 | CHECK | Tests check for correctness, not just format | Reference recomputation + exact value compares | `tests/test_outputs.py`, `tests/reference_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Output-file comparisons only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact compares appropriate for deterministic ML outputs | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | Docstrings on all tests | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives at -5 | `entire-report.txt` platform rubric |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 9 Agent lines, flat format | `entire-report.txt` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific artifact/process checks | `entire-report.txt` |
| 36 | CHECK | Rubric criteria use positive language | Positives describe good behavior; negatives penalize bad | `entire-report.txt` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | Complete metadata | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | python / machine-learning / ML tags match | `task.toml` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best model 0%, worst 60% | `entire-report.txt`, `task.toml:6` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not milestone | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not milestone | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not milestone | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:17` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ excluded from image | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Independent reference recomputation from same CSV | `tests/reference_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 60% | `entire-report.txt` |
| 55 | UNCHECK | Task is not too hard or unfair | PSI denominator hidden semantics cause systematic near-miss failures | `entire-report.txt`, blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 11, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Per-class 70/30 split by `Unnamed: 0` order | `test_integer_metrics_match[n_train/n_test]`, predictions identity | covered | `instruction.md:3`, `tests/reference_outputs.py:59-70` |
| PSI numeric: quantile edges + fallback linspace `+1e-9` | `test_drift_values_match[psi]` | covered | `instruction.md:15`, `reference_outputs.py:117-119` |
| PSI numeric: proportion denominator | `test_drift_values_match[psi]`, `test_float_metrics_match[drift_psi_*]` | **gap** | `instruction.md:15` “split total” vs `reference_outputs.py:122-123` `max(ac.sum(), 1.0)` |
| PSI clip 1e-6–1.0 and log formula | drift value tests | covered | `instruction.md:15`, `reference_outputs.py:122-124` |
| Categorical PSI renormalize | drift tests | covered | `instruction.md:15`, `reference_outputs.py:126-135` |
| RandomForest hyperparameters | prediction/metric exact tests | covered | `instruction.md:3`, `reference_outputs.py:106-112` |
| Six output artifacts under `/app/outputs` | `test_all_artifacts_exist` | covered | `instruction.md:7-17`, `tests/test_outputs.py:56-66` |
| `wall_clock_sec` present | `test_metrics_top_level_schema` | covered (not exact-valued) | `tests/test_outputs.py:91` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker 1, #1, #7, #10, #11, spec alignment |
| `tests/reference_outputs.py` | Blocker 1 PSI proof, oracle logic |
| `tests/test_outputs.py` | #27, #28, #31, drift PSI test rates |
| `tests/test.sh` | Re-run adjudication, #24–26 |
| `environment/Dockerfile` | #14–#16, #20 |
| `environment/requirements.txt` | #14, #20 |
| `task.toml` | #45, milestone N/A, timeouts |
| `entire-report.txt` | Agent stats, rubric, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate rt-iot2022-drift-multi-class/
Summary: 0 error(s), 1 warning(s), 3 info
WARNING: pinned_dependencies — Dockerfile pip line lacks inline == (packages pinned in requirements.txt)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Execution/other failures |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 timeouts |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% supports hard) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `machine-learning`; matches report |
| 1 Instruction | ☑ | PSI denominator gap; length note only |
| 2 Environment | ☑ | Digest-pinned; deps pinned; tmux/asciinema present |
| 3 Oracle | ☑ | Real pipeline; platform 100% pass |
| 4 Verifiers | ☑ | Re-run design acceptable; reference recomputation |
| 5 Metadata | ☑ | Complete; agent timeout note only |
| 6 Rubric | ☑ | Flat non-milestone format correct |
| 7 LLMaJ & agent evidence | ☑ | PSI gap confirmed; split-order claim rejected |
| 8 Novelty & fairness | ☑ | PSI underspec = fairness concern (#55) |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid RT-IoT2022 task overall — pinned environment, independent reference verification, and the six-artifact consistency checks are well thought out. The rubric format is correct for a non-milestone task. One fix before accept: the numeric PSI instruction says to normalize histogram counts using “that split total,” which reads like the train/test row count, but the verifier normalizes by the sum of histogram bin counts (`max(bin_count_sum, 1.0)`). That matters when values fall outside quantile edges and is driving systematic PSI failures (including a 63/67 near-miss). Please spell out the histogram-count-sum denominator explicitly in `instruction.md`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Agent Timeout | no | — |
