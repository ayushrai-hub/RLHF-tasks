# Terminus Review Report: `breast-cancer-cost-calibration-leakage`

**Generated:** 2026-07-07 17:30 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/breast-cancer-cost-calibration-leakage`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed locally (submission export: 100% 3/3) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Rubric, Test Alignment/Coverage Issues

**Decision (concise):** Strong ML task with digest-pinned env, hash-locked deps (including pytest), clear output contract in `/app/contracts/outputs.md`, and well-documented hidden quality gates in both `instruction.md` and the contract. Two real blockers: platform rubric uses forbidden `+4` scores (three lines), and the hidden Brier gate at `≤ 0.028` is empirically too tight—multiple agent runs pass 26/27 tests but miss Brier by `0.00007–0.00019` despite the threshold being stated in the prompt. `author_email = "anonymous"` matches the official `task-requirements.md` example and is not a blocker. Automated audit false-positives on #14 (lockfile pinning) and #20 (pytest in lockfile) are overturned.

**Insights (concise):**

- Non-milestone rubric layout is correct (flat `Agent …, ±N` list; no `# Rubric 2+` blocks); positive total is exactly 40/40.
- Brier `≤ 0.028` is specified in `instruction.md:5` and `contracts/outputs.md:23`, so this is not a phantom/hidden-semantics gap—it's a calibration/fairness tightness issue.
- `test_hidden_eval_brier_quality` pass rate is 5/10 (50%); dominant agent failure mode is near-miss Brier (4 trials at 0.02807–0.02819 vs 0.028 cutoff per `entire-report.txt`).
- Verifier deps (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`) are baked via `requirements.lock` + `--require-hashes` in `environment/Dockerfile:14`.
- Worst-model pass rate 20% → hard tier; within submission policy for Python tasks.
- Local `.pytest_cache/` and `.ruff_cache/` under task dir are dev artifacts—not in zip spec but worth cleaning before submit.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #33 | Platform rubric uses forbidden `+4` scores (allowed set is ±1, ±2, ±3, ±5 only) | `entire-report.txt` lines 363, 365, 368: three `Agent …, +4` lines; `docs/guidelines/rubrics.md:53` forbids `±4` | Replace each `+4` with `+3` or `+5` (adjust block total to stay ≤40) |
| 2 | High | Test Alignment/Coverage Issues | #27, #55 | Hidden Brier gate `≤ 0.028` rejects legitimate calibrated models by microscopic margins; gate appears tuned to reference hyperparameters (`class_weight='balanced'`, sigmoid calibration) not stated in the modeling contract | `instruction.md:5`; `tests/test_outputs.py:560-564` `assert brier <= 0.028`; `entire-report.txt` lines 73-74, 105-107 (misses 0.02807–0.02819); `test_hidden_eval_brier_quality` 5/10 pass; reference model `test_outputs.py:157-167` uses `class_weight="balanced"` | Relax Brier cutoff slightly (e.g. `≤ 0.030`) **or** add minimal modeling guidance in instruction/contract (e.g. class imbalance handling) so stated gate is achievable without oracle-specific tuning |

*No other High/Medium blockers confirmed.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Hidden Brier gate too tight; near-correct calibrated models fail by tiny margins (ChatGPT High) | **Partially agree** | Threshold **is** documented (`instruction.md:5`, `contracts/outputs.md:23`). Unfairness confirmed by agent stats: 4 trials miss by 0.00007–0.00019 (`entire-report.txt:73-107`); 50% pass on `test_hidden_eval_brier_quality`. Not a phantom-requirement gap. |
| 2 | `author_email = "anonymous"` invalid; use `anonymous@anonymous.anonymous` (ChatGPT High) | **Disagree** | Official example in `docs/task-requirements.md:37` is `author_email = "anonymous"`. `task.toml:5` matches. |
| 3 | Output contract well documented in `/app/contracts/outputs.md` (ChatGPT Medium) | **Agree** | `environment/contracts/outputs.md` specifies filenames, schemas, bootstrap seed/replicates, threshold grid, and hidden gates. |
| 4 | Rubric flat and within point range (ChatGPT Medium) | **Partially agree** | Positive total 40/40 PASS. Flat non-milestone format correct. **But** three forbidden `+4` lines fail #33. |
| 5 | Optional timeout on `python3 /app/analysis.py` in test.sh (ChatGPT Low) | **Agree (non-blocking)** | `tests/test.sh:5` runs analysis with no sub-timeout; verifier timeout 1800s is only safeguard. Low severity suggestion only. |
| 6 | Optional: `solve.sh` should run analysis (ChatGPT Low) | **Agree (non-blocking)** | `solution/solve.sh:1-3` only copies; `tests/test.sh:5` runs analysis. Works today; not a blocker. |
| 7 | Dockerfile digest-pinned Python base appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…` |
| 8 | LLMaJ `behavior_in_task_description` FAIL — filenames/schemas only in contracts | **Partially agree** | `instruction.md:5` explicitly defers to `/app/contracts/outputs.md` for full contract. Acceptable Edition 2 pattern when contract is shipped in env and referenced. Not a blocker. |
| 9 | LLMaJ `file_reference_mentioned` FAIL — output filenames not in instruction | **Partially agree** | Same deferral pattern. Contract is normative and in-image. Low concern given explicit pointer. |
| 10 | Instruction sufficiency FAIL — Brier gate unachievable without hidden labels / `class_weight` (entire-report) | **Partially agree** | Aligns with blocker #2 on empirical tightness; threshold itself is not hidden from agents. |
| 11 | Harbor review: solve.sh doesn't execute analysis (entire-report WARNING) | **Agree (non-blocking)** | `solution/solve.sh:3` copy-only; harness runs via `tests/test.sh:5`. |
| 12 | Test quality review: threshold gates appropriate for multiple implementations (entire-report) | **Disagree for Brier** | AUROC/cost gates allow slack vs reference; Brier uses hard `<= 0.028` with no reference slack (`test_outputs.py:564`), and agent near-misses contradict "multiple valid implementations" claim. |
| 13 | Author merged rubric to flat non-milestone list (entire-report comment) | **Agree on format** | `entire-report.txt:356-375` — flat list, no `# Rubric 2+`. Format correct for `number_of_milestones = 0`. |
| 14 | Automated audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:14` uses `requirements.lock` with `--require-hashes`; `docs/guidelines/ci-checks.md:17` allows lockfiles; `pytest==8.4.1` at `requirements.lock:132`. |
| 15 | Automated audit #20 pytest not in Dockerfile | **Disagree** | `requirements.txt:5-6` lists pytest; installed via lockfile in Dockerfile. `tests/test.sh` does not pip install. |
| 16 | Automated audit #11 task name in instruction | **Agree (Low/Medium, not Revise alone)** | `instruction.md:1` path contains `breast-cancer-cost-calibration-leakage.csv` — matches shipped data filename (`environment/data/`). Necessary reference, not gratuitous task-name leak. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~4 short paragraphs, within budget | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads like engineer brief, not spec doc | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goals/constraints, defers schema to contract | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | No oracle walkthrough; contract is normative spec | `instruction.md` |
| 6 | CHECK | No design-doc tables in instruction | None | `instruction.md` |
| 7 | CHECK | Well specified | Clear ML pipeline goal, paths, gates | `instruction.md`, `contracts/outputs.md` |
| 8 | CHECK | Interesting | Realistic ML calibration + leakage + cost-sensitive task | task content |
| 9 | CHECK | Unique | Distinct composite ML benchmark (time split, leakage fields, bootstrap, fairness) | task content |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md:1,5` |
| 11 | UNCHECK | Task name not in instruction | Dataset filename embeds task slug | `instruction.md:1` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local data only | `environment/Dockerfile` |
| 14 | CHECK | Pinned Python deps | `requirements.txt` `==` + hash-locked `requirements.lock` | `environment/Dockerfile:14`, `requirements.lock:132` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:…` present | `environment/Dockerfile:1` |
| 16 | CHECK | Build context scoped to environment/ | COPY only env files | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in environment | Starter `analysis.py` is broken template | `environment/analysis.py` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in lockfile; `test.sh` only runs pytest | `requirements.lock`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally this session | submission export oracle 100% |
| 22 | CHECK | Oracle needs no internet | Copy + compute only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction | Full pipeline in `solution/analysis.py` | `solution/analysis.py` |
| 24 | CHECK | Canonical reward.txt block | Writes 0/1 on pass/fail | `tests/test.sh:7-11` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward only | 0 or 1 | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Brier gate fair but too tight for stated "calibrated classifier" contract | blocker #2 |
| 28 | CHECK | Tests check correctness | Recomputes metrics, hidden eval, anti-cheat | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Integration tests; source scan is anti-cheat only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Numeric tolerances used | `tests/test_outputs.py:94-96` |
| 31 | CHECK | Informative test docstrings | All `test_*` documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:372-375` |
| 33 | UNCHECK | Rubric scores in {±1,±2,±3,±5} | Three `+4` lines | `entire-report.txt:363,365,368` |
| 34 | CHECK | Rubric `Agent …, ±N` format | 20 properly formatted lines | `entire-report.txt:356-375` |
| 35 | CHECK | Rubric detailed/precise | Task-specific trace checks | `entire-report.txt` |
| 36 | CHECK | Rubric positive phrasing | Negatives penalize bad behavior directly | `entire-report.txt:372-375` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt` |
| 38 | CHECK | Rubric no instruction/task.toml refs | None | `entire-report.txt` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt` |
| 40 | CHECK | Required files present | All core files exist | task tree |
| 41 | UNCHECK | No unnecessary parent files | Local `.pytest_cache/`, `.ruff_cache/` present | task dir |
| 42 | CHECK | author_name/email present | Both in `task.toml` | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, tags, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/category applicable | `machine-learning`, python, calibration tags fit | `task.toml` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; worst-model 20% → hard tier | `task.toml:6`, `entire-report.txt:19-21` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone tests scoped | N/A | `task.toml:10` |
| 50 | CHECK | Tests not baked in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore` / no COPY solution | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially rewrite inputs | Data baked at build; hidden labels in `/tests` | `environment/Dockerfile:19`, `tests/eval_labels.csv` |
| 53 | CHECK | Git clones pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Not too hard/unfair | Brier gate rejects near-valid solutions by hair | blocker #2, `entire-report.txt:73-112` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 11, 21, 27, 33, 41, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Time split: fit `<8`, validate `8–9`, historical `<10` | `test_validation_scores_cover_window`, reference recompute | covered | `contracts/outputs.md:3`, `test_outputs.py:107-121` |
| Block leakage columns from features | `test_feature_importance_excludes_blocked_fields` | covered | `instruction.md:1`, `test_outputs.py:37` |
| Sentinel `-999`/`-777` cleaning | reference pipeline + output consistency tests | covered | `contracts/outputs.md:4` |
| Calibrated classifier, mixed types | hidden eval quality gates | covered | `instruction.md:3` |
| Cost-optimal threshold FN=12, FP=1 | `test_cost_curve_*`, `test_metrics_cost_weights_and_primary` | covered | `instruction.md:3`, `test_outputs.py:599-603` |
| Eight output files per contract | `test_all_artifacts_exist`, schema tests | covered | `contracts/outputs.md:7-21` |
| Bootstrap 200 replicates, seed 20260657 | `test_threshold_bootstrap_*` | covered | `contracts/outputs.md:17` |
| Hidden AUROC ≥ 0.988, AP ≥ 0.998 | `test_hidden_eval_discrimination_quality` | covered | `instruction.md:5`, `test_outputs.py:551-557` |
| Hidden Brier ≤ 0.028 | `test_hidden_eval_brier_quality` | covered but tight | `instruction.md:5`, `test_outputs.py:560-564` |
| Hidden cost ≤ ref+0.025, balanced acc ≥ 0.80 | `test_hidden_eval_cost_quality` | covered | `contracts/outputs.md:23`, `test_outputs.py:567-576` |
| >20 distinct eval probabilities | `test_prediction_probability_and_label_shape` | covered | `instruction.md:5`, `test_outputs.py:542` |
| `n_train` = all historical rows `<10` | `test_metrics_match_validation_scores` | covered | `contracts/outputs.md:3` |
| Anti-cheat: no reading `/tests`, labels | `test_analysis_does_not_reference_hidden_or_verifier_artifacts` | covered | `test_outputs.py` |
| 91-row cost curve thresholds 0.05–0.95 | `test_cost_curve_columns` | covered | `contracts/outputs.md:13` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #5, #7, #10, #11, blocker 2, Brier spec |
| `task.toml` | #42, #43, #45, metadata |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `environment/contracts/outputs.md` | #7, spec alignment, bootstrap schema |
| `tests/test_outputs.py` | #27, #28, hidden gates, reference model |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh` | #23 |
| `entire-report.txt` | #33, #45, #54, agent stats, rubric, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate breast-cancer-cost-calibration-leakage/
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures |
| terminus-claude-opus-4-8 | 20.0% (1/5) | 4 failures |
| oracle | 100.0% (3/3) | per submission export |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

**Per-test signal:** `test_hidden_eval_brier_quality` 5/10 — dominant failure mode; others mostly 8–10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise, absolute paths, defers schema to contract |
| 2 Environment | ☑ | Digest-pinned base, tmux/asciinema, hash lockfile, no tests/solution COPY |
| 3 Oracle | ☐ | Not executed locally; static review + export 100% |
| 4 Verifiers | ☑ | Canonical test.sh; 27 tests; hidden gates; anti-cheat |
| 5 Metadata | ☑ | Complete; `author_email = "anonymous"` is valid per docs |
| 6 Rubric | ☑ | Flat non-milestone format OK; **+4 scores fail #33** |
| 7 LLMaJ & agent evidence | ☑ | Brier near-miss pattern confirmed; instruction sufficiency partially valid |
| 8 Novelty & fairness | ☑ | Multi-step ML; Brier tightness is fairness concern |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid ML task — the leakage controls, output contract in `/app/contracts/outputs.md`, hash-locked Dockerfile, and verifier design are in great shape, and difficulty calibration looks right for hard tier. Two things to fix before accept: (1) the platform rubric has three criteria scored at `+4`, which isn't an allowed score — please change those to `+3` or `+5` while keeping the total at or under 40; (2) the hidden Brier gate at `≤ 0.028` is rejecting otherwise correct runs by tiny margins (several agents passed 26/27 tests missing Brier by less than 0.0002). Either relax that cutoff slightly or add minimal guidance on handling class imbalance so a well-built calibrated classifier can hit the stated gate without matching oracle hyperparameters exactly.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2 |
| Metadata Issues | no | — |
| Instruction Styling | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review` + `./scripts/terminus audit`._
