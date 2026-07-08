# Terminus Review Report: `16-fleet-risk-calibrator`

**Generated:** 2026-07-08 18:30 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/16-fleet-risk-calibrator`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass (0 errors, 2 warnings) |
| **Oracle** | pass (submission report 3/3; local run blocked — Docker daemon unavailable) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** No blocking issues found after manual re-audit. The task is offline, digest-pinned on the canonical Go base, verifier deps are baked into the image via hash-locked `requirements.lock`, oracle passes in submission runs, and the verifier reimplements the full scoring/planning pipeline with counterexample probes. Automated audit `#10`, `#14`, `#20` are false positives or de-minimis; platform rubric is correctly formatted for a non-milestone task (flat list, 21 positive pts, 6 negatives).

**Insights (concise):**

- Dockerfile uses the **canonical** `golang:1.24-bookworm` digest from `docs/guidelines/dockerfxile.md` — Harbor “non-canonical base” warning is incorrect.
- `pytest==8.4.1` and deps are pinned in `environment/requirements.lock` and installed in the Dockerfile; auditor `#14`/`#20` false positives.
- Rubric is a **flat** non-milestone list (no `# Rubric N` blocks) — not milestone format; 21 positive pts ≤ 40 cap.
- `scored_calls.csv` input-order rule is in `output-contract.md:21`; instruction references that contract — optional polish only.
- Worst-model pass rate 40% (GPT-5.5) fits medium tier; Claude Opus 4.8 at 100% does not make the task too easy.
- LLMaJ “instruction sufficiency FAIL” reflects agent ordering mistakes, not a missing spec requirement.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High severity issues | Agree | `task.toml:27` `allow_internet=false`; `Dockerfile:1` digest-pinned canonical Go base; `tests/test.sh:11-15` no runtime installs |
| 2 | ChatGPT: No Medium severity issues | Agree | `instruction.md` + `environment/app/docs/{model-card,output-contract}.md` specify schemas, metrics, planner rules; 16 `test_*` functions with reference recompute |
| 3 | ChatGPT Low: Add scored_calls order callout to `instruction.md` | Partially agree | `output-contract.md:21` “preserve the original service_calls.csv input order”; `instruction.md:16` references output-contract; agents missed ordering per export — polish only, not blocker |
| 4 | ChatGPT Low: Rubric says “four” artifacts, should be “six” | Agree | `entire-report.txt:275` “four /app/out artifacts”; `instruction.md:16` lists six files |
| 5 | ChatGPT: Accept | Agree | No real blockers after manual audit |
| 6 | Harbor review: Non-canonical Docker base | Disagree | `Dockerfile:1` matches `docs/guidelines/dockerfxile.md:11` canonical `golang:1.24-bookworm@sha256:1a6d4452…` |
| 7 | Harbor review: Tags array 6 entries / golang redundant | Partially agree | `task.toml:12` six tags including `golang` duplicating `languages=["go"]` — Low metadata polish only |
| 8 | LLMaJ: `behavior_in_task_description` pass | Agree | Instruction + referenced docs cover tested behaviors |
| 9 | LLMaJ: `behavior_in_tests` pass | Agree | 16 tests cover scoring, planning, manifest, metrics, counterexamples |
| 10 | Instruction sufficiency analysis FAIL (ordering) | Partially agree | Ordering specified in `output-contract.md:21`; failure is agent implementation, not missing requirement |
| 11 | Test quality review: ACCEPT | Agree | Reference Python recompute + 4 counterexample tests |
| 12 | Automated audit REJECTED (#10, #14, #20) | Disagree | See checkbox #10, #14, #20 adjudication below — false positives or de-minimis |
| 13 | User concern: non-milestone task in milestone rubric format | Disagree (no issue) | `task.toml:9` `number_of_milestones=0`; platform rubric is flat `Agent …, ±N` list with no `# Rubric 2+` headers (`entire-report.txt:271-283`) — correct non-milestone format per `docs/guidelines/rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~24 lines, one problem paragraph + bullets | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Incident-style maintenance brief, not spec headers | `instruction.md:1-2` |
| 3 | CHECK | No excessive markdown | No ##/tables/code fences | `instruction.md` |
| 4 | CHECK | No step-by-step dev walkthrough | Outcome bullets only | `instruction.md:7-21` |
| 5 | CHECK | No hints/solving strategies | WHAT + normative doc refs, no solve script | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | No markdown tables | `instruction.md` |
| 7 | CHECK | Well specified | Absolute I/O paths, six outputs, metrics named | `instruction.md:3-21` |
| 8 | CHECK | Interesting/useful | Realistic offline fleet risk + dispatch planning | task content |
| 9 | CHECK | Unique | Multi-contract Go ML + optimizer task; no duplicate verified | subjective — distinctive scope |
| 10 | CHECK | Absolute paths only | All data/config/output paths absolute; `go run ./cmd/fleetrisk` co-listed with `/app/cmd/fleetrisk` (Go idiom from WORKDIR `/app`) | `instruction.md:5`, `Dockerfile:22` |
| 11 | CHECK | Task name not in instruction | No “fleet-risk-calibrator” string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch in env | No runtime fetch in app code | `environment/` |
| 14 | CHECK | Pinned pip dependencies | `requirements.lock` uses `==` + sha256 hashes; Dockerfile `--require-hashes` | `environment/requirements.lock:1-12`, `Dockerfile:15-16` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452…` on FROM | `Dockerfile:1` |
| 16 | CHECK | Env context only | COPY `app/` only | `Dockerfile:24` |
| 17 | CHECK | No ground-truth leakage | `model-card.md` / `output-contract.md` are normative agent-facing specs, not oracle answers | `environment/app/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose Harbor mounts | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest baked via `requirements.lock`; `test.sh` only runs pytest | `Dockerfile:13-17`, `tests/test.sh:11-15`, `reviewer-checklist-ui.md` item-20 note |
| 21 | CHECK | Oracle passes consistently | Submission: oracle 100% (3/3); local `./scripts/terminus oracle` errored (Docker daemon not running) | `entire-report.txt:23` |
| 22 | CHECK | Oracle no internet | `solve.sh` copies Go files, `go test`, `go run` locally | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Implements features/score/run via Go computation | `solution/solve.sh:4-19` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail | `tests/test.sh:17-22` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:18-21` |
| 27 | CHECK | Tests aligned with instructions | Every instruction bullet traced to tests or referenced docs | §5 below |
| 28 | CHECK | Tests check correctness | Full reference recompute, not format-only | `tests/test_outputs.py:913-929` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Numeric tolerance via reference math | `tests/test_outputs.py` |
| 31 | CHECK | Informative docstrings | All 16 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 negatives | `entire-report.txt:278-283` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines valid | `entire-report.txt:271-283` |
| 34 | CHECK | Agent line format | 13 `Agent …, ±N` lines | `entire-report.txt:271-283` |
| 35 | CHECK | Rubric detailed; positive cap | 21 positive pts ≤ 40 | `./scripts/terminus rubric-points entire-report.txt` |
| 36 | CHECK | Positive phrasing | No `Agent does not…, +N` patterns | `entire-report.txt:271-283` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:271-283` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:271-283` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:271-283` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/category match | `machine-learning` + Go offline inference fit; `golang` tag redundant but harmless | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `difficulty=medium`; platform medium; worst-model 40% → medium tier | `task.toml:6`, `entire-report.txt:13-19` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones=0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:16`, `Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:15` |
| 52 | CHECK | Agent cannot trivially mutate inputs | `test_shipped_inputs_were_not_changed` SHA-256 checks | `tests/test_outputs.py:907-910` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤ 80% | `entire-report.txt:17-19` |
| 55 | CHECK | Not unfair/too hard | Spec complete in instruction + docs; agent near-misses are implementation errors | `entire-report.txt:47-92`, artifacts |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Latest sensor window at/before `opened_at`; fail if none | `test_missing_sensor_window_fails_with_clear_error` | covered | `tests/test_outputs.py:1811-1847` |
| stderr `ERROR:` prefix on fatal input errors | `test_missing_sensor_window_fails_with_clear_error` | covered | `tests/test_outputs.py:1846` |
| Feature vector per model-card (imputation, clipping, trend, history) | `test_scored_calls_match_model_contract` | covered | `tests/test_outputs.py:913-929` |
| Dual heads, calibration knots, asset blend, PAVA post-calibration | `test_scored_calls_match_model_contract` | covered | `tests/test_outputs.py:913-929` |
| Missing feature weights → zero contribution | `test_scored_calls_match_model_contract` | covered | reference `score_call` in `test_outputs.py` |
| Calibrated integrated-gradient `top_factor` | `test_top_factor_uses_calibrated_integrated_attribution`, `test_scored_calls_match_model_contract` | covered | `tests/test_outputs.py:1118`, `929` |
| Global capacity optimizer + crew/parts scheduler | `test_decisions_are_sorted_and_actionable`, `test_crew_schedule_matches_exact_roster_plan`, `test_parts_allocation_matches_exact_inventory_plan`, counterexample tests | covered | `tests/test_outputs.py:932-974`, `1248`, `1460`, `1641` |
| Six output files in `/app/out` | `test_agent_left_required_reports_in_app_out` | covered | `tests/test_outputs.py:881` |
| `scored_calls.csv` preserves `service_calls.csv` order | `test_scored_calls_match_model_contract` | covered | `expected_scores()` iterates `calls` in file order; `output-contract.md:21` |
| Decisions sorted by `calibrated_risk` desc, `request_id` asc | `test_decisions_are_sorted_and_actionable` | covered | `tests/test_outputs.py:932-936` |
| Six evaluation metrics + JSON field names | `test_evaluation_*` trio | covered | `tests/test_outputs.py:1050-1074` |
| `roc_auc` Mann-Whitney; `average_precision` sort rules | `test_evaluation_ranking_metrics_match_labels` | covered | `tests/test_outputs.py:1064` |
| Do not modify input CSV/JSON | `test_shipped_inputs_were_not_changed` | covered | `tests/test_outputs.py:907-910` |
| Manifest input/output hashes | `test_manifest_records_inputs_and_outputs` | covered | `tests/test_outputs.py:977` |
| Fully offline | env `GOPROXY=off`, `allow_internet=false` | covered | `Dockerfile:19-20`, `task.toml:27` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, §5 |
| `task.toml` | #42-45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #13-16, #20, canonical base |
| `environment/requirements.lock` | #14, #20 |
| `environment/.dockerignore` | #50-51 |
| `environment/app/docs/output-contract.md` | scored_calls ordering, schemas |
| `environment/app/docs/model-card.md` | feature/scoring/attribution spec |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39, #45, #54, agent stats |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `docs/guidelines/rubrics.md` | rubric format/cap |
| `docs/reviewer-checklist-ui.md` | #20 interpretation |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate 16-fleet-risk-calibrator/
Summary: 0 error(s), 2 warning(s), 2 info
Task type detected: regular
```

Warnings: `pinned_dependencies` heuristic on Dockerfile pip line (false positive — uses hash-locked lockfile); `check_task_absolute_path` on `go run ./cmd/fleetrisk` (de-minimis).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Submission runs |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | medium |
| Platform classified | medium |
| Tier match (#45) | yes (informational) |

Common agent failures: `test_scored_calls_match_model_contract` (ordering/precision), `test_decisions_are_sorted_and_actionable` (top_factor), scheduler break edge case — implementation errors, not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular layout; `number_of_milestones=0`; report matches task |
| 1 Instruction | ☑ | Concise, absolute I/O paths; `./cmd/fleetrisk` de-minimis |
| 2 Environment | ☑ | Canonical digest-pinned Go base; tmux+asciinema; hash-locked pytest venv |
| 3 Oracle | ☑ | Derives via Go; submission 3/3 pass |
| 4 Verifiers | ☑ | 16 behavior tests; reward block; no runtime installs |
| 5 Metadata | ☑ | category/tags appropriate |
| 6 Rubric | ☑ | Flat non-milestone format; 21/+ cap OK; 6 negatives; wording nit “four” artifacts |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL is agent ordering, not missing spec |
| 8 Novelty & fairness | ☑ | Multi-step ML+optimizer; anti-cheat via hashes + counterexamples |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall — this is a strong offline Go implementation challenge with clear normative docs (`model-card.md`, `output-contract.md`), a digest-pinned canonical base, and verifier deps properly baked into the image. The test suite reimplements the full scoring and planning pipeline and adds targeted counterexamples for attribution, regional capacity, crew breaks, and part-transfer delays. Oracle passes cleanly and agent pass rates look right for medium difficulty (GPT-5.5 at 40%, Opus higher). I didn’t find any blocking spec-test gaps or cheating paths. Optional polish: mention in `instruction.md` that `scored_calls.csv` must keep `service_calls.csv` row order (already in output-contract), and update the rubric line that says “four” output artifacts to “six.”

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

_Manual accuracy review per `prompt.md`. Baseline from `./scripts/terminus validate`, `./scripts/terminus audit`, `./scripts/terminus review`._
