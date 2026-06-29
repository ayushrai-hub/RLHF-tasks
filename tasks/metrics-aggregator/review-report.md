# Terminus Review Report: metrics-aggregator

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Rust multi-bug debugging task — digest-pinned offline environment, comprehensive statistical spec, 34 behavioral verifiers, misleading-code trap design, and oracle all pass cleanly. Worst-model pass rate is **60%** (Claude), matching declared `medium` difficulty. The sole **High** blocker is the platform rubric: only **1** negative criterion (needs ≥3). Category `system-administration` should be `debugging` (Medium metadata note). Non-milestone rubric uses optional single `# Rubric 1` header only — **not** milestone-format violation.

**Insights (concise):**

- ChatGPT/Harbor category mismatch claim is **valid** but **Medium** severity per checklist — not a Revise driver alone.
- Automated baseline `#54` fail is **wrong**: `review_checklist.py` uses `max()` for “worst model” → reports GPT 100%; actual worst model = Claude **60%** (`entire-report.txt:67-68`).
- Platform rubric has 20 Agent lines, 49 positive points, **1** negative — `# Rubric 1` only (acceptable for `number_of_milestones = 0`).
- All 34 `test_*` functions have docstrings; validate’s module-level docstring warning is not a #31 fail.
- Instruction is 10 paragraph blocks (~424 words) — exceeds 3-paragraph guideline (#1 UNCHECK) but spec density is appropriate for tested statistical semantics; not a fairness blocker.
- `metrics-aggregator` appears in instruction as the **binary path** (#11 UNCHECK, Medium) — incidental to CLI contract, not a canary.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32 | Platform rubric has only **1** negative penalty; Terminus requires **≥3** distinct negatives | `entire-report.txt:374-394` (20 Agent lines; sole negative at line 394: `…applypatch…, -2`); `docs/guidelines/rubrics.md:37` (“Minimum 3 distinct negative criteria”); `docs/reviewer-checklist-full.md:77` (High) | On the submission platform, add at least **two** more distinct negative criteria (e.g. `-2` for editing test files, `-3` for leaving build.rs compile-time offsets, `-2` for only patching one source file without rebuilding). Keep scores in ±1,2,3,5. |

*No other High-severity revision drivers found in task artifacts.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Category should be `debugging`, not `system-administration` (ChatGPT / Harbor `entire-report.txt:242-263`) | **Agree** | `task.toml:6` `category = "system-administration"`; `instruction.md:1-2` (“Fix all bugs… Rebuild with cargo build”); `docs/task-type-taxonomy.md:15,29` (`debugging` = find/diagnose/fix errors); no OS/service/network admin work |
| 2 | Category mismatch is **High** severity blocker (ChatGPT) | **Disagree** (severity) | `docs/reviewer-checklist-full.md:100` — tags/category mismatch is **Medium**; single Medium ≠ Revise per severity rules |
| 3 | Replace `config-trap` tag with neutral tag (ChatGPT / Harbor `entire-report.txt:216-239`) | **Agree** (Low only) | `task.toml:12` `config-trap`; advisory discoverability — not a blocker |
| 4 | Task needs revision for category only; otherwise production-ready (Harbor `entire-report.txt:327-330`) | **Partially agree** | Category fix warranted; rubric negative count is the stronger High blocker |
| 5 | Test quality ACCEPT — comprehensive coverage (Harbor test quality `entire-report.txt:344-370`) | **Agree** | 34 behavioral tests with hand-computed expected values; synthetic fixtures isolate individual bugs |
| 6 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` PASS | **Agree** | `entire-report.txt:180-181`; spot-checked config path, env isolation, dedup, stats formulas |
| 7 | Instruction sufficiency PASS — failures are implementation errors (entire-report analysis) | **Agree** | `entire-report.txt:154-158`; agents hit partial fixes (7/34 tests), not spec gaps |
| 8 | Worst-model 100% → too easy (#54 in automated baseline) | **Disagree** | `entire-report.txt:67-68` — GPT 100%, Claude **60%**; worst model = **60%** (Medium tier); automated script bug uses `max()` at `scripts/review_checklist.py:320-322` |
| 9 | Instruction too long → #1 fail (automated baseline) | **Partially agree** | `instruction.md` — 10 paragraph blocks, 424 words vs 3-paragraph guideline; dense but maps 1:1 to tested behaviors; UNCHECK #1, not a Revise driver |
| 10 | Task name in instruction → #11 fail (automated baseline) | **Partially agree** | `instruction.md:1,3` — `/app/target/release/metrics-aggregator` is the shipped binary path; Medium per checklist; UNCHECK #11 |
| 11 | Missing test docstrings → #31 fail (automated baseline) | **Disagree** | All 34 `def test_*` have docstrings (`tests/test_outputs.py:29-860`); validate module-level warning is separate |
| 12 | Rubric negative phrasing → #36 fail (automated baseline) | **Disagree** (not a blocker) | `entire-report.txt:394` — “Agent fails to identify…, **-2**” is a valid negative penalty; Medium phrasing note at most |
| 13 | Non-milestone task uses milestone rubric format (`# Rubric 1` header) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; `entire-report.txt:374` single `# Rubric 1` only; `docs/guidelines/rubrics.md:64` (“`# Rubric 1` optional; no `# Rubric 2+`”) |
| 14 | Rubric positive total 49 pts exceeds 10–40 non-milestone cap | **Agree** (Low only) | Sum of `+N` in `entire-report.txt:375-393` = 49; `docs/reviewer-checklist-full.md:85-86` — Low severity |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 10 paragraph blocks, ~424 words | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense statistical/JSON contract prose | `instruction.md:7-19` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT (correct behavior), not edit order | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No “look for” / repair walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Exact formulas, paths, schema, config rules | `instruction.md:7-19` |
| 8 | CHECK | Instruction is interesting | Real Rust debugging / stats pipeline task | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md:1-17` |
| 11 | UNCHECK | Task name does not appear in instruction.md | Binary path contains `metrics-aggregator` | `instruction.md:1,3` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies pinned with == | `pytest==8.4.1 pytest-json-ctrf==0.3.5` | `environment/Dockerfile:9` |
| 15 | CHECK | Base Docker image pinned by digest | `@sha256:9f841bbe…` | `environment/Dockerfile:2` |
| 16 | CHECK | Environment does not use context outside environment/ | COPY limited to env paths | `environment/Dockerfile:13-30` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Misleading docs; instruction warns they may be wrong | `instruction.md:19`; `environment/docs/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:9`, `tests/test.sh:24` |
| 21 | CHECK | Oracle passes consistently | Mean reward 1.000 (1/1) | Harbor oracle run 2026-06-28 |
| 22 | CHECK | Oracle does not require internet | Local patches + `cargo build --release` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Patches each buggy source file, rebuilds, smoke-runs | `solution/solve.sh:1-528` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical 0/1 block | `tests/test.sh:13-30` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | Writes 0 or 1 | `tests/test.sh:27-29` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to instruction requirement | §5 below; `entire-report.txt:180-181` |
| 28 | CHECK | Tests check correctness, not just format | Hand-computed numeric expected values | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs binary on fixtures; no source grep | `tests/test_outputs.py:18-26` |
| 30 | CHECK | No brittle exact string matching | Numeric tolerances (`abs(...) < 0.00001`) | `tests/test_outputs.py:890-894` |
| 31 | CHECK | Tests have informative names or docstrings | All 34 tests documented | `tests/test_outputs.py:29-860` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Only 1 negative in platform rubric | `entire-report.txt:394` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use ±1,2,3,5 | `entire-report.txt:375-394` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 20 Agent lines | `entire-report.txt:375-394` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific trace checks per bug class | `entire-report.txt:375-393` |
| 36 | CHECK | Rubric criteria use positive language | Negative line uses `-2` for bad behavior | `entire-report.txt:394` |
| 37 | CHECK | Rubric does not reference /tests/ or pytest | No test refs | `entire-report.txt:374-394` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:374-394` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:374-394` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean layout | task root |
| 42 | CHECK | author_name and author_email present | `anonymous` fields | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | Complete `[metadata]` / env / agent / verifier | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories applicable | `category = "system-administration"` mismatches debugging content | `task.toml:6` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `medium`; worst model 60% → Medium tier | `task.toml:8`, `entire-report.txt:67-68` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone tests scoped to milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | tests/ and solution/ outside build context | `environment/Dockerfile:13-30` |
| 52 | CHECK | Agent cannot trivially pass by modifying input data | Must fix Rust source + rebuild; tests use /tmp fixtures | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model 60% ≤ 80% | `entire-report.txt:67-68` |
| 55 | CHECK | Task is not too hard or unfair | Detailed spec; all tested behaviors stated | `instruction.md`; agent analysis `entire-report.txt:154-158` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 2, 9, 11, 32, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Binary at `/app/target/release/metrics-aggregator`; exit 0 on success | `test_binary_compiles`, `test_tool_runs_successfully` | covered | `instruction.md:1-5`; `tests/test_outputs.py:29-40` |
| Output `aggregation_report.json` in output dir | all tests via `REPORT_FILE` | covered | `instruction.md:5`; `tests/test_outputs.py:9` |
| Config from fixed `/app/config/` paths; threshold 1.5 | `test_config_loads_from_fixed_path`, `test_no_env_var_override` | covered | `instruction.md:9`; `tests/test_outputs.py:416-701` |
| No deduplication across files | `test_no_deduplication_across_files`, `test_count_field_with_cross_file_combine` | covered | `instruction.md:11`; `tests/test_outputs.py:673-821` |
| Mean unrounded; true sum/count | `test_mean_is_float_computed`, `test_mean_not_normalized` | covered | `instruction.md:13`; `tests/test_outputs.py:42-748` |
| Sample stddev N-1 from true mean | `test_stddev_sample_formula`, `test_stddev_uses_correct_mean`, `test_single_point_stddev_zero` | covered | `instruction.md:13`; `tests/test_outputs.py:204-414` |
| Median ascending; odd/even rules | `test_median_ascending_order`, `test_median_odd_length_correct_index`, `test_even_length_median` | covered | `instruction.md:13`; `tests/test_outputs.py:70-479` |
| Percentile ceiling nearest-rank, unrounded | `test_percentile_ceiling_method`, `test_percentile_not_rounded`, `test_p99_percentile` | covered | `instruction.md:13`; `tests/test_outputs.py:128-845` |
| Min/max over all values | `test_min_not_zero`, `test_max_value_correct`, `test_max_includes_first_element` | covered | `instruction.md:13`; `tests/test_outputs.py:52-809` |
| Outliers when z-score >= threshold | `test_outlier_detection_threshold`, `test_outlier_boundary_zscore_equals_threshold` | covered | `instruction.md:15`; `tests/test_outputs.py:280-339` |
| Z-score rounded to `percentile_rounding` places | `test_outlier_zscore_rounded`, `test_outlier_zscore_exact_value` | covered | `instruction.md:15`; `tests/test_outputs.py:481-671` |
| Exact `total_outliers` sum | `test_total_outliers_count` | covered | `instruction.md:15`; `tests/test_outputs.py:341-351` |
| Alphabetical metric ordering | `test_metric_order_alphabetical` | covered | `instruction.md:17`; `tests/test_outputs.py:366-373` |
| No trailing slash in error paths | `test_error_message_no_trailing_slash` | covered | `instruction.md:17`; `tests/test_outputs.py:353-364` |
| Deterministic output | `test_rerun_deterministic` | covered | `instruction.md:17`; `tests/test_outputs.py:375-384` |
| No transform when calibration=1, windowing=false | `test_no_transformation_when_calibration_one` | covered | `instruction.md:19`; `tests/test_outputs.py:859-894` |
| `total_metric_points` = sum of all point counts | `test_total_metric_points_accurate`, `test_multi_file_total_points` | covered | `instruction.md:11`; `tests/test_outputs.py:544-760` |
| `count` = data points in group | `test_count_field_is_total_points` | covered | `instruction.md:11`; `tests/test_outputs.py:557-611` |
| Don't change types.rs field names/types | — | gap (untested) | `instruction.md:17`; no structural assertion — Low only; agents can pass without touching types.rs |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #11, §5 alignment |
| `task.toml` | #44, #45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50, #53 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39, #45, #54, §3 adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate metrics-aggregator/
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: informative_test_docstrings — module-level docstring missing (not #31)
INFO: submission-diversity — non-milestone (not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst model |
| oracle | 100.0% (3/3) | Reference |
| nop | 0.0% (0/1) | Reference |

| Metric | Value |
|--------|-------|
| Worst-model rate | **60%** (Claude) |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `metrics-aggregator`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Dense spec; aligned with tests; #1/#2 UNCHECK for length/tone |
| 2 Environment | ☑ | Digest-pinned Rust base; tmux+asciinema; pytest in image; no tests/solution COPY |
| 3 Oracle | ☑ | Pass 1.0; patches source + rebuild |
| 4 Verifiers | ☑ | 34 tests; reward block canonical; no runtime installs |
| 5 Metadata | ☑ | Category mismatch Medium; tags OK count |
| 6 Rubric | ☑ | **Blocker:** 1 negative; format OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; 60% worst model |
| 8 Novelty & fairness | ☑ | Multi-file Rust debugging; anti-cheat sound |
| 9 Long context | ☐ | N/A — no `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust debugging task — the pinned offline environment, detailed statistical spec, misleading-code trap across build.rs/config/aggregator/reporter, and broad verifier suite are all in great shape. Oracle passes cleanly and agent rates (60% worst model) fit medium difficulty well.

Two things before accept: (1) the platform rubric only has one negative penalty — please add at least two more distinct negatives (e.g. tampering with graded tests, leaving build.rs offsets, or patching without rebuilding). (2) Change `category` in `task.toml` from `system-administration` to `debugging` — this is a code-bug repair task, not OS admin. Optional: rename the `config-trap` tag to something neutral like `configuration`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Metadata Issues | yes (Medium only) | — |
| Instruction Styling | no (UNCHECK #1/#2; not Revise driver) | — |
| Test Alignment/Coverage Issues | no | — |
| Task Difficulty | no (#54 passes at 60%) | — |
| Milestones | no (N/A; rubric format OK) | — |
