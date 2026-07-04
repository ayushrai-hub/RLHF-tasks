# Terminus Review Report: reconcile-cargo-inference-configs

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report 100%; local run blocked by Docker sandbox) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are structurally sound: offline env, digest-pinned Node base, regeneration-based tests, spec↔test alignment via dossier appendices, and 38/40 rubric positive points. One real High blocker: platform rubric line uses `Agent's` (possessive apostrophe), which fails the mandatory `Agent …, ±N` format validator (#34). Fix that single line and resubmit. ChatGPT Accept missed this; automated audit #14 (unpinned pip) is a false positive.

**Insights (concise):**

- Non-milestone task with optional `# Rubric 1` header only — **not** wrongly formatted as a multi-milestone rubric (`rubrics.md:66`, `submission-export-format.md:63`).
- Positive rubric total is **38** (not 39 as ChatGPT stated); cap 40 passes.
- Instruction sufficiency FAIL in export is **not** a spec gap: instruction states “latest date wins”; dossier embeds dated prose (e.g. concurrency 12 on 2026-06-18, batch 12 on 2026-06-17, timeout 1200 on 2026-06-20).
- ~349 KB dossier (~87k tokens) satisfies long_context; values require temporal reconciliation, not grep alone.
- Worst-model pass rate 40% (GPT-5.5); tier medium; not too easy (#54 passes).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #34 | One rubric criterion uses `Agent's` possessive; fails `^Agent .+, ±N$` format | `entire-report.txt:371`; `./scripts/terminus rubric-validate` on extracted rubric → `Invalid format: Agent's output files…` | Reword to `Agent ensures output files end with exactly one trailing newline and carry no trailing whitespace on any line, +1` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High severity issues; structurally sound (ChatGPT) | Partially agree | Structure passes; rubric format #34 is High per `reviewer-checklist-full.md:79` |
| 2 | allow_internet=false, timeouts present, tests offline (ChatGPT) | Agree | `task.toml:41`; `[agent] timeout_sec=1500`; `tests/test.sh` no installs |
| 3 | Verifier regenerates artifacts; anti-cheat robust (ChatGPT / test quality) | Agree | `tests/test_outputs.py:37-59` `regenerated_plan` fixture deletes outputs, reruns pipeline |
| 4 | Rubric 39 positive points, within cap (ChatGPT) | Disagree | Sum is **38** via `./scripts/terminus rubric-points entire-report.txt` |
| 5 | Flat non-milestone rubric format OK (ChatGPT) | Agree | `# Rubric 1` only; no `# Rubric 2+`; `number_of_milestones=0` in `task.toml:13` |
| 6 | Non-milestone task wrongly in milestone rubric format (user concern) | Disagree | Single optional `# Rubric 1` is permitted for non-milestone; milestone format requires multiple `# Rubric N` blocks |
| 7 | Node base digest-pinned, justified (ChatGPT / review report) | Agree | `environment/Dockerfile:12` `@sha256:f3a68cf4…`; justification comment lines 1-11 |
| 8 | Optional maintainability: test comments linking dossier dates (ChatGPT Low) | Agree (Low only) | Not a blocker; tests already cite dates in docstrings e.g. `test_serving_limits` L219 |
| 9 | Task Instruction Sufficiency FAIL — prose 2026-06-20 unfair (export) | Disagree | `instruction.md:4` “latest date wins”; dossier L629/L643/L673 dated prose; agent failures are implementation difficulty, not missing spec |
| 10 | Audit #14 unpinned pip | Disagree | `environment/Dockerfile:28-31` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `PyYAML==6.0.2` |
| 11 | Audit #27 phantom numeric asserts | Disagree | Values 8/12/15/25/57/144 trace to dossier appendices referenced in `instruction.md:4` and normative Appendix O/D |
| 12 | Harbor review READY TO USE | Partially agree | Artifacts strong; rubric format line must be fixed first |
| 13 | LLMaJ behavior_in_tests / anti_cheating pass | Agree | Verified against `test_outputs.py`, `.dockerignore:16-17` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 short paragraphs, ~264 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational problem statement, not spec dump | `instruction.md:1-4` |
| 3 | CHECK | No excessive markdown | Plain prose only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States WHAT to build | `instruction.md` |
| 5 | CHECK | No hints/strategies | No solve walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Paths, entrypoint, three outputs, appendices named | `instruction.md:2-4` |
| 8 | CHECK | Interesting | Real ML config reconciliation scenario | task content |
| 9 | CHECK | Unique (manual) | No duplicate found in review scope | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | No task name in instruction | Clean | `instruction.md` |
| 12 | CHECK | No canary string | Clean | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline data shipped | `environment/` |
| 14 | CHECK | Pinned pip deps | All `==` pinned | `environment/Dockerfile:28-31` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:f3a68cf4…` | `environment/Dockerfile:12` |
| 16 | CHECK | Build context in environment/ | `COPY app/` only | `environment/Dockerfile:44` |
| 17 | CHECK | No ground-truth leakage in env | Dossier is input corpus; appendices are schemas | `environment/app/dossier.md` |
| 18 | CHECK | No dangerous Docker ops | Standard RUN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:28-31`, `tests/test.sh:4-5` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3); solution implements full pipeline | `entire-report.txt:33` |
| 22 | CHECK | Oracle offline | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Writes/compiles TS; parses CSV/YAML/TOML; reads dossier run_id | `solution/solve.sh:11-172` |
| 24 | CHECK | reward.txt on pass/fail | Canonical block | `tests/test.sh:19-23` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instruction | All asserts trace to instruction + Appendix O/D | see §5 |
| 28 | CHECK | Tests check correctness | Behavioral values, digests, derivations | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle where flex needed | Exact contract required by appendices | `dossier.md:1081-1112` |
| 31 | CHECK | Informative docstrings | All `test_*` documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 7 negatives | `entire-report.txt:372-378` |
| 33 | CHECK | Valid rubric scores | ±1,2,3,5 only | `entire-report.txt:357-378` |
| 34 | UNCHECK | Rubric one-line format | `Agent's output files…` fails `Agent …, ±N` regex | `entire-report.txt:371`; `rubrics.py:53` |
| 35 | CHECK | Rubric detailed; positive cap | 38 positive pts ≤40 | `./scripts/terminus rubric-points` |
| 36 | CHECK | Positive phrasing on positives | Negatives use `-N` | `entire-report.txt:372-378` |
| 37 | CHECK | No /tests/ in rubric | Clean | platform rubric |
| 38 | CHECK | No instruction.md in rubric | References dossier appendices only | `entire-report.txt:358,367` |
| 39 | CHECK | No oracle/NOP in rubric | Clean | platform rubric |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in submission tree | task folder |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Metadata complete | category, tags, timeouts | `task.toml` |
| 44 | CHECK | Tags/category match | ML + long_context + typescript | `task.toml:8-19` |
| 45 | CHECK | Difficulty field present | `medium`; platform medium; worst-model 40% | `task.toml:8`, `entire-report.txt:23-29` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones=0` | `task.toml:13` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:13` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone-scoped tests | N/A | `task.toml:13` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | `environment/.dockerignore:17` |
| 51 | CHECK | Solution not in image | `.dockerignore` excludes solution | `environment/.dockerignore:16` |
| 52 | CHECK | No trivial input mutation cheat | Regeneration fixture; digests bind bytes | `tests/test_outputs.py:37-59`, `306-324` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:28-29` |
| 55 | CHECK | Fair / not too hard | Dated prose rule stated; oracle passes; agents reach 71–82% partial | `instruction.md:4`, `entire-report.txt:89-96` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 34, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Pipeline `node /app/dist/reconcile.js`, dossier on stdin | `regenerated_plan` | covered | `instruction.md:2`; `test_outputs.py:50-54` |
| `/app/release-plan.yaml` Appendix O contract | `test_top_level_key_order_and_set`, formatting tests | covered | `dossier.md:1081-1112`; `test_outputs.py:106-114` |
| Latest-dated serving limits | `test_serving_limits` | covered | `instruction.md:4`; dossier L629/L643/L673; `test_outputs.py:218-223` |
| `queue_capacity = batch × concurrency` | `test_queue_capacity_derived` | covered | `instruction.md:4`; `test_outputs.py:226-228` |
| Threshold derivations | `test_thresholds_values` | covered | `instruction.md:4`; `test_outputs.py:201-205` |
| RFC-4180 CSV + UTC latest row | `test_model_evaluated_at_utc_selection` | covered | `test_outputs.py:139-147` |
| Feature rules (dynamic-batching, experimental-simd) | `test_dynamic_batching_*`, `test_experimental_simd_*` | covered | dossier feature rules; `test_outputs.py:187-198` |
| Appendix D deploy derivations | `test_deploy_*` | covered | `dossier.md:1120-1138`; `test_outputs.py:250-291` |
| lock.json digests | `test_lock_*` | covered | `dossier.md:1140-1150`; `test_outputs.py:294-324` |

No phantom requirements found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #27, §5 |
| `task.toml` | #45, #46-49 N/A |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/dossier.md` | #27, #55, long_context, §5 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39, #45, #54, §3 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate reconcile-cargo-inference-configs/
Summary: 0 error(s), 1 warning(s), 2 info
(pinned_dependencies warning is false positive — pip uses == in Dockerfile)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Best model |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task name matches folder; regular layout; long_context + typescript |
| 1 Instruction | ☑ | Concise; absolute paths; dossier authority clear |
| 2 Environment | ☑ | tmux/asciinema; digest Node; pip pinned; no tests/solution COPY |
| 3 Oracle | ☑ | Platform 100%; full TS pipeline (local oracle blocked by Docker) |
| 4 Verifiers | ☑ | Regeneration fixture; docstrings; binary reward |
| 5 Metadata | ☑ | Complete; timeouts reasonable |
| 6 Rubric | ☐ | **Blocker:** #34 format fail on `Agent's` line |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL adjudicated as agent error not spec gap |
| 8 Novelty & fairness | ☑ | Multi-step reconciliation; anti-cheat closed |
| 9 Long context | ☑ | ~87k tokens; temporal prose reconciliation required |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task — the long dossier design, regeneration-based tests, and cross-artifact digest checks are all in great shape, and agent pass rates look right for medium difficulty. One small rubric fix before we can accept: the line starting with `Agent's output files…` fails the required format because of the apostrophe right after Agent. Please reword it to something like `Agent ensures output files end with exactly one trailing newline…, +1`. Everything else looks good from my review.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Milestones | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
