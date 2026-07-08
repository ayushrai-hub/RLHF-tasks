# Terminus Review Report: `ml-eval-api-mlflow.`

**Generated:** 2026-07-04 19:55 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/ml-eval-api-mlflow.`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 3 warnings — pip-pinning heuristic false positives) |
| **Oracle** | pass (100% per submission export; local oracle not executed — Harbor config error) |
| **CHECK count** | 54 |
| **UNCHECK count** | 1 |

**Error categories (internal):** none

**Decision (concise):** Two-milestone ML eval API task is structurally sound, spec-complete, and fairly tested. Prior-cycle blocker (empty `/app/docs`, hidden contract in instructions) is resolved: concise milestone prompts point to shipped contract docs covering every verifier expectation. Dockerfile uses the canonical digest-pinned Node 22 base; rubric uses correct milestone block format with totals under cap. No High or Medium blockers found after manual re-audit.

**Insights (concise):**

- Prior reviewer feedback and Harbor LLMaJ “non-canonical base” claim are **stale/wrong** — `environment/Dockerfile:1` matches `docs/guidelines/dockerfxile.md` canonical `node:22-bookworm-slim` digest exactly.
- Automated audit failures (#14 pip pinning, #22 oracle download, #31 docstrings, #39 rubric oracle) are **false positives** on manual inspection.
- Platform rubric correctly uses `# Rubric 1` / `# Rubric 2` blocks (this **is** a 2-milestone task); per-block positives 18 and 14 (cap 40).
- Agent pass rates (GPT-5.5 20%, Opus 4.8 60%) align with hard/medium calibration; worst-model 20% ≤ 80%.
- Spec↔test alignment is strong: backslash filename rejection, ONNX runtime-usability, MLflow daemonization, and env-port binding are all documented in `/app/docs` and tested.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept; no High/Medium blockers | Agree | Manual artifact audit confirms; see sections 4–5 |
| 2 | ChatGPT: Prior hidden-style instruction concern addressed via `/app/docs` contracts | Agree | `steps/milestone_1/instruction.md:1-3`, `steps/milestone_2/instruction.md:1-3` point to `environment/docs/M1/*.md`, `M2/*.md` copied at `Dockerfile:43` |
| 3 | ChatGPT: Digest-pinned Node 22 base appropriate; no base-image blocker | Agree | `environment/Dockerfile:1` = canonical digest in `docs/guidelines/dockerfxile.md:10` |
| 4 | ChatGPT: Milestone rubrics correctly split, ≤40 pts per block, distinct negatives | Agree | `entire-report.txt:489-508`; `./scripts/terminus rubric-points` → {1:18, 2:14}; 3 negatives per block |
| 5 | ChatGPT: Optional polish — one-line endpoint summary in instructions | Partially agree | Low only; instructions functional as concise dev prompts |
| 6 | ChatGPT: Optional — fold solve1/solve2 into solve.sh | Partially agree | Low only; wrappers work, not blocking |
| 7 | Harbor REVIEW REPORT: Non-canonical Docker base (CRITICAL) | **Disagree** | `environment/Dockerfile:1` uses exact canonical ECR Node 22 digest; LLMaJ references obsolete `ghcr.io/laude-institute/t-bench/node-22` |
| 8 | Harbor REVIEW REPORT: Per-step instructions too terse | Partially agree | Low; docs are normative and shipped; `eval-api-contract.md` covers all tested behavior |
| 9 | Prior portal Reviewer Feedback: `/app/docs` empty; contract hidden in instruction text | **Disagree (stale)** | `environment/docs/M1/eval-api-contract.md`, `server-runtime.md`, `M2/mlflow-runtime.md`, `mlflow-tracking.md` exist and are COPY'd |
| 10 | LLMaJ: behavior_in_task_description PASS | Agree | Docs specify multipart, CSV/ONNX validation, scoring, MLflow schema |
| 11 | LLMaJ: behavior_in_tests PASS | Agree | `test_m1.py` 20 test methods; `test_m2.py` 6 test methods with docstrings |
| 12 | LLMaJ: pinned_dependencies PASS | Agree | `Dockerfile:22-37` all `==`; `package.json:27-49` exact versions + `package-lock.json` |
| 13 | LLMaJ: hardcoded_solution PASS | Agree | `solve1.sh`/`solve2.sh` write full TypeScript implementations via heredoc |
| 14 | Submission: oracle 100% (3/3) | Agree (report evidence) | `entire-report.txt:41`; local `./scripts/terminus oracle` failed (Harbor ValueError — not task fault) |
| 15 | Submission: Instruction sufficiency PASS | Agree | Agent failures attributed to implementation gaps (backslash regex, MLflow daemonization), not missing spec |
| 16 | Test quality: M1/M2 ROBUST | Agree | Dynamic ONNX/CSV generation; independent sklearn reference scores |
| 17 | Author Comments: declined separate `/app/docs` files | Disagree with author premise | Docs **do** exist under `environment/docs/` and are realistic contract files — author response appears to misunderstand prior feedback |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~94 words, 4 short blocks across both milestones | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational dev-style prompts, not spec tables | same |
| 3 | CHECK | No excessive markdown | Plain prose only | same |
| 4 | CHECK | No step-by-step HOW | Points to docs; no numbered solve walkthrough | same |
| 5 | CHECK | No hints/strategies | Describes WHAT via doc references | same |
| 6 | CHECK | No design-doc tables | None in instructions | same |
| 7 | CHECK | Well specified | Absolute paths + clear milestone goals | same |
| 8 | CHECK | Interesting/useful | Realistic Fastify ML eval + MLflow integration | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3 index from artifacts | — |
| 10 | CHECK | Absolute paths only | `/app/docs/M1/...`, `/app/docs/M2/...` | `steps/milestone_1/instruction.md:1-3` |
| 11 | CHECK | Task name not in instruction | No `ml-eval-api-mlflow` string | instruction files |
| 12 | CHECK | No canary strings | None detected | instruction files |
| 13 | CHECK | No runtime web fetch in env | Build-time `curl` for uv only; `allow_internet=false` | `environment/Dockerfile:16-17`, `task.toml:21` |
| 14 | CHECK | Pip deps pinned with == | All pytest/mlflow/sklearn/onnx packages use `==` | `environment/Dockerfile:22-37` |
| 15 | CHECK | FROM digest-pinned | `@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` | `environment/Dockerfile:1` |
| 16 | CHECK | No external build context | COPY limited to `./backend/`, `./docs/` | `environment/Dockerfile:39,43` |
| 17 | CHECK | No ground-truth answers in env | Docs are contracts, not solutions | `environment/docs/M1/eval-api-contract.md` |
| 18 | CHECK | No privileged/docker.sock | Standard RUN instructions only | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no install | pytest/mlflow/sklearn baked; test.sh runs pytest only | `environment/Dockerfile:22-37`, `steps/milestone_1/tests/test.sh:13-16` |
| 21 | CHECK | Oracle passes | 100% (3/3) per submission export | `entire-report.txt:41` |
| 22 | CHECK | Oracle no runtime download | solve scripts write TS via heredoc; no npm/pip install | `steps/milestone_1/solution/solve1.sh:7-724`, `solve2.sh:32-996` |
| 23 | CHECK | Oracle reflects instruction | Full eval plugin + MLflow server startup implemented | `solve1.sh`, `solve2.sh` |
| 24 | CHECK | reward.txt always written | Canonical 0/1 block on pass/fail | `steps/milestone_1/tests/test.sh:18-22` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | test.sh files |
| 26 | CHECK | Binary rewards only | echo 0 or 1 | test.sh files |
| 27 | CHECK | Tests aligned with instructions | All tested behaviors documented in `/app/docs` | section 5 |
| 28 | CHECK | Tests check correctness | Dynamic ONNX + sklearn reference scores | `test_m1.py:506-509`, `test_m2.py:867-900` |
| 29 | CHECK | Behavior not implementation grep | HTTP + MLflow API integration tests | test files |
| 30 | CHECK | No brittle string matching | Score tolerance `1e-4`; MLflow root similarity ≥0.95 | `test_m1.py`, `test_m2.py:843-845` |
| 31 | CHECK | Informative test docstrings | AST: 0 missing docstrings across both files | `test_m1.py`, `test_m2.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 total (3 per milestone block) | `entire-report.txt:489-508` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | same |
| 34 | CHECK | Agent …, ±N format | 17 properly formatted lines | same |
| 35 | CHECK | Rubric detailed; positive cap | 32 total; blocks 18/14 (≤40) | `rubric-points` output |
| 36 | CHECK | Positive language in rubric | No “Agent does not …, +N” patterns | `entire-report.txt:489-508` |
| 37 | CHECK | Rubric no /tests/ refs | None | same |
| 38 | CHECK | Rubric no instruction.md refs | None | same |
| 39 | CHECK | Rubric no oracle/NOP refs | “oracle” only in LLMaJ prose, not rubric lines | `entire-report.txt:489-508` |
| 40 | CHECK | Required files present | Dockerfile, task.toml, steps/* per milestone | task tree |
| 41 | CHECK | No stray parent files | Submission tree clean (reviewer-generated audit files excluded) | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags/languages/category match | TypeScript Fastify ML task | `task.toml:7-13` |
| 45 | CHECK | Difficulty field present | `medium` in task.toml; platform `hard`; worst-model 20% → hard tier — mismatch informational only | `task.toml:6`, `entire-report.txt:31-37` |
| 46 | CHECK | steps/ milestone layout | 2 milestones under `steps/` | `task.toml:29-46` |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh` present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | `test_m1.py`, `test_m2.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | M1: no MLflow refs; M2: MLflow + eval regression | grep: M1 no mlflow; M2 has MLflow tests |
| 50 | CHECK | Tests not in image | No COPY tests/ in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | `steps/` not COPY'd | `environment/Dockerfile:39,43` |
| 52 | CHECK | No trivial input tampering | Runtime-generated ONNX/CSV fixtures | `test_m1.py` artifact helpers |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:36-37` |
| 55 | CHECK | Fair / not too hard | Spec complete; agent failures are narrow implementation gaps | `entire-report.txt:137-193` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| POST /eval multipart with exactly 2 files in `files` | `test_multipart_form_rejects_*` | covered | `eval-api-contract.md:5`, `test_m1.py:734+` |
| Reject path-like filenames incl. `/`, `\`, `..`, null, control chars | `test_path_like_filenames_are_rejected` | covered | `eval-api-contract.md:5`, `test_m1.py:887+` |
| ONNX invalid bytes / runtime inference failure rejected | `test_onnx_validation_rejects_invalid_models` | covered | `eval-api-contract.md:7`, `test_m1.py:969+` |
| Feature count mismatch rejected | `test_onnx_validation_rejects_feature_count_mismatches` | covered | `eval-api-contract.md:7`, `test_m1.py:1004+` |
| CSV row count 2–1000, numeric-only, no NaN/Inf | `test_csv_validation_rejects_empty_or_short_datasets` | covered | `eval-api-contract.md:9-11`, `test_m1.py:1092+` |
| Metrics accuracy/rmse/f1; f1 binary-only | `test_eval_success_*`, `test_f1_rejects_*`, `test_regression_rejects_f1_metric` | covered | `eval-api-contract.md:13`, `test_m1.py:506+` |
| Response `{"score": <number>}`; 200 success / 400 bad | `test_eval_success_returns_expected_score` | covered | `eval-api-contract.md:3`, `test_m1.py:506+` |
| GET /health → 200 | `test_health_returns_200` | covered | `server-runtime.md:3`, `test_m1.py:478+` |
| `npm start`; read `FASTIFY_PORT` | `test_server_starts_with_npm_start` | covered | `server-runtime.md:8`, `test_m1.py:474+` |
| MLflow server background; survives terminal close | `test_mlflow_get_root_content_matches` | covered | `mlflow-runtime.md:4`, `test_m2.py:826+` |
| Experiment `model-evaluation`; one run per success | `test_successful_eval_logs_expected_mlflow_run` | covered | `mlflow-tracking.md:3-5`, `test_m2.py:867+` |
| Params/metric schema; run name `eval-<timestamp>` | same | covered | `mlflow-tracking.md:5`, `test_m2.py:902+` |
| No MLflow run on failed eval | `test_invalid_request_does_not_create_mlflow_run` | covered | implied by tracking contract, `test_m2.py:960+` |
| Read `MLFLOW_PORT` at startup (override) | `test_temporary_mlflow_port_override_is_used` | covered | `mlflow-runtime.md:7`, `test_m2.py:1008+` |
| M1 eval behavior preserved in M2 | `test_submitted_server_matches_reference_response` | covered | `steps/milestone_2/instruction.md:4`, `test_m2.py:977+` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, #46, layout |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/docs/M1/eval-api-contract.md` | #27, spec alignment |
| `environment/docs/M1/server-runtime.md` | #27, spec alignment |
| `environment/docs/M2/mlflow-runtime.md` | #27, spec alignment |
| `environment/docs/M2/mlflow-tracking.md` | #27, spec alignment |
| `steps/milestone_1/instruction.md` | #1-7, #10 |
| `steps/milestone_2/instruction.md` | #1-7, #10 |
| `steps/milestone_1/tests/test_m1.py` | #28-31, #49 |
| `steps/milestone_2/tests/test_m2.py` | #28-31, #49 |
| `steps/milestone_1/tests/test.sh` | #20, #24-26 |
| `steps/milestone_1/solution/solve1.sh` | #22-23 |
| `steps/milestone_2/solution/solve2.sh` | #22-23 |
| `entire-report.txt` | #21, #32-39, #45, #54, adjudication |
| `docs/guidelines/dockerfxile.md` | canonical base verification |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: ml-eval-api-mlflow. ===
WARNING: pinned_dependencies [environment/Dockerfile]: Pin pip packages with == versions (3 lines)
Summary: 0 error(s), 3 warning(s), 2 info
Task type detected: milestone
```

Manual review: all pip packages in `Dockerfile:22-37` use `==`; validator false-positive on multi-line `uv pip install`.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | |
| oracle | 100.0% (3/3) | Submission export |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | medium |
| Platform classified | hard |
| Tier match (#45) | informational only — not a blocker |

### Rubric (platform)

| Field | Value |
|-------|-------|
| Positive total | 32 (cap 40) |
| Per block | #1: 18, #2: 14 |
| Negatives | 6 total (3 per block) |
| Milestone format | Correct `# Rubric 1` / `# Rubric 2` for `number_of_milestones=2` |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 2-milestone TypeScript ML task; folder `ml-eval-api-mlflow.` |
| 1 Instruction | ☑ | Concise prompts + shipped `/app/docs` contracts |
| 2 Environment | ☑ | Canonical digest-pinned Node 22; tmux/asciinema; offline |
| 3 Oracle | ☑ | Heredoc TS implementation; report 100% pass |
| 4 Verifiers | ☑ | Robust dynamic tests; reward block canonical |
| 5 Metadata | ☑ | `allow_internet=false`; milestones=2 |
| 6 Rubric | ☑ | Milestone block format correct; ≤40 per block |
| 7 LLMaJ & agents | ☑ | Failures are agent gaps, not spec gaps |
| 8 Novelty & fairness | ☑ | Multi-step; anti-cheat via dynamic fixtures |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this resubmission — the milestone structure reads much cleaner now. Each step gives a short, natural prompt and points to the contract docs under `/app/docs`, which cover the ONNX runtime checks, CSV rules, server startup assumptions, and MLflow tracking details the verifiers expect. The Dockerfile is digest-pinned on the canonical Node 22 base, verifier deps are baked into the image, and the dynamic ONNX/CSV tests plus MLflow integration checks look solid. Oracle passes and agent rates fit a hard task. I didn’t find any blocking spec, test, environment, or rubric issues. Only note: corpus uniqueness wasn’t verified from artifacts alone.

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

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus validate`, `audit`, and `review`._
