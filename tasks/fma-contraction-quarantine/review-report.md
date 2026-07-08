# Terminus Review Report: `fma-contraction-quarantine`

**Generated:** 2026-07-07 10:25 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/fma-contraction-quarantine`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (submission export 3/3; not re-run locally — Harbor config error) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** Test Alignment/Coverage Issues, Milestones

**Decision (concise):** Strong 3-milestone floating-point/compiler-flag task with excellent anti-cheat design, held-out grading, and correct milestone rubric layout. One confirmed High blocker: Milestone 2 `inv_holds` evaluates the `recover` / `absorbed_zero` precondition with Python JSON integer arithmetic instead of C `double` semantics, rejecting witnesses such as `[9007199254740992, 1]` that are valid at the kernel level. Prior schema/metadata issues (M2 `invariant` key, M3 bare-filename keys, `docker_flags`/`gpus`/`gpu_types`) are fixed. Automated `#1` (concise) and `#14` (pip pin) failures are false positives on manual re-audit.

**Insights (concise):**

- ChatGPT’s M2 arithmetic mismatch claim is **confirmed** with live simulation and file evidence (`gradelib.py:179-181`).
- Rubric uses correct **milestone** format (`# Rubric 1/2/3`); per-block positives 13/15/16 — all ≤40 (total 44 is allowed for milestone tasks).
- `BUILD_NOTES.md` cited in prior portal feedback **does not exist** in current artifacts; stale claim.
- `task.toml` now includes `gpus`, `gpu_types`, `docker_flags`; M2/M3 output schemas are explicit.
- Agent stats: worst-model 60% (GPT-5.5), best 100% (Opus 4.8); declared `hard` vs platform `medium` is informational only.
- Oracle solution uses `1e16 1.0` (float JSON) for `recover`, sidestepping the integer precondition bug.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Milestones | #27, #55 | M2 witness validation for `recover` / `absorbed_zero` uses Python integer arithmetic on JSON-loaded witness args, not C `double` semantics used by `kerneltest`. Witness `[9007199254740992, 1]` satisfies the invariant precondition as doubles but fails grading because `(a+b)==a` is False for Python `int`. | `steps/milestone_2/tests/gradelib.py:179-181`; `steps/milestone_2/tests/test_m2.py:47-55`; `environment/data/CONTRACTS.md:12`; `entire-report.txt:74-82,88-89`; live sim: int witness → `inv_holds` returns True for both strict and release outputs, failing `not inv_holds(..., ro)` | Coerce witness args to `float` before invariant preconditions in `inv_holds` (at minimum `recover`), **or** document that witness JSON numbers must be IEEE-754 doubles (e.g. `9007199254740992.0` / `1e16`). Prefer coercion in grader to match kernel semantics. |

*No other High or Medium blockers found on manual re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M2 witness validation has C-vs-Python arithmetic mismatch for `recover` / `absorbed_zero` (ChatGPT / `entire-report.txt` agent analysis) | **Agree** | `gradelib.py:179-181` uses `(a+b)==a` on raw JSON values; `json.loads('[9007199254740992,1]')` → `int`; Python `(a+b)==a` is False, float coercion is True; agent trial `7djvyhC` failed M2 on `recover` per `entire-report.txt:68,74,88` |
| 2 | Earlier M2 schema: must name JSON key `invariant` (prior reviewer / `entire-report.txt:12`) | **Disagree (fixed)** | `steps/milestone_2/instruction.md:5` explicitly requires `invariant` key with example |
| 3 | Earlier M3 schema: bare source filename keys undocumented (prior reviewer / `entire-report.txt:13`) | **Disagree (fixed)** | `steps/milestone_3/instruction.md:5` documents `accum` or `accum.c`, never directory paths |
| 4 | `docker_flags`, `gpus`, `gpu_types` missing from `task.toml` (prior reviewer / `entire-report.txt:4`) | **Disagree (fixed)** | `task.toml:22-24` has `gpus = 0`, `gpu_types = []`, `docker_flags = []` |
| 5 | `BUILD_NOTES.md` contains disallowed task-solving spec content (prior reviewer / `entire-report.txt:2`) | **Disagree (stale)** | No `BUILD_NOTES.md` in task tree; env docs are `CONTRACTS.md`, `NUMERICS.md`, `README.md` — schema/contract style only |
| 6 | Missing root-level `[agent]` / `[verifier]` in `task.toml` (Harbor review / ChatGPT Low) | **Disagree (not blocker)** | Per-step `[steps.agent]` / `[steps.verifier]` timeouts present (`task.toml:30-51`); optional fallback, not execution-blocking |
| 7 | Rubric positive total 44 > 40 is a blocker (automated `rubric-points`) | **Disagree** | Milestone task (`number_of_milestones = 3`); cap is **per `# Rubric N` block** per `docs/guidelines/rubrics.md:31-33` — blocks are 13/15/16, all ≤40 |
| 8 | Rubric should use milestone format, not flat non-milestone list (user request) | **Agree (passes)** | `entire-report.txt:385-410` uses `# Rubric 1`, `# Rubric 2`, `# Rubric 3` — correct for milestone task |
| 9 | Instruction too long — blocker #1 (automated audit) | **Disagree** | Each milestone instruction is 1–2 paragraphs (~80–120 words); auditor incorrectly summed all three (~483 words). Milestone instructions evaluated per-step. |
| 10 | Unpinned pip deps — blocker #14 (automated audit) | **Disagree** | `environment/Dockerfile:14-16` pins `pytest==8.4.1` and `pytest-json-ctrf==0.3.5`; multiline `RUN` triggered false positive |
| 11 | M3 minimality sensitive to hidden held-out coverage (agent analysis / `entire-report.txt:84`) | **Partially agree (not blocker)** | Held-out inputs are grading internals by design; one agent over-specified `gain.c` — agent misjudgment, not spec gap |
| 12 | LLMaJ `behavior_in_task_description` PASS | **Agree** | M1/M2/M3 instructions name output paths, keys, and semantics matching verifiers |
| 13 | LLMaJ `structured_data_schema` PASS | **Agree with caveat** | Schemas documented; M2 witness numeric type semantics for `recover` remain implicit — root cause of blocker 1 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone instruction is 1–2 paragraphs; summed-word-count heuristic is N/A for milestone layout | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md`, `steps/milestone_3/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Conversational engineering tone across milestones | milestone instruction files |
| 3 | CHECK | No excessive markdown formatting | Plain prose; M2 has one inline JSON example only | milestone instruction files |
| 4 | CHECK | No step by step instructions | States goals/outputs, not build recipe | milestone instruction files |
| 5 | CHECK | No hints or solving strategies | No bisection/compile walkthrough in instructions | milestone instruction files |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables in instructions | milestone instruction files |
| 7 | CHECK | Instruction is well specified | Output paths, keys, verdicts, flag tokens all named | M1/M2/M3 instruction.md |
| 8 | CHECK | Instruction is interesting | Real compiler FP / build-profile debugging scenario | task content |
| 9 | CHECK | Instruction is unique | Distinct geokern FP-invariant milestone design; no duplicate in repo | task structure |
| 10 | CHECK | All paths in instruction are absolute | `/app/output/result_N.json` | milestone instruction files |
| 11 | CHECK | Task name does not appear in instruction.md | No `fma-contraction-quarantine` string | milestone instruction files |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | milestone instruction files |
| 13 | CHECK | Dockerfile does not grab content from the web | Only apt/pip in build | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:14-16` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | `COPY data/` only | `environment/Dockerfile:18` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs describe contracts/numerics; no hazard partition or manifest literals | `CONTRACTS.md`, `NUMERICS.md`, `README.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:14-16`, `steps/milestone_*/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Submission export: oracle 100% (3/3) | `entire-report.txt:42` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve scripts compile locally | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle is reflective of instruction | solve2.sh builds, probes invariants, emits JSON from runs | `steps/milestone_2/solution/solve2.sh` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical 0/1 reward block | `steps/milestone_1/tests/test.sh:17-21` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | gradelib + test_m*.py |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 in test.sh | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | M2 `recover` precondition uses Python int math, not documented C double semantics | Blocker 1; `gradelib.py:179-181` |
| 28 | CHECK | Tests check for correctness, not just format | Rebuild from `/opt/ref`, run kernels, check invariants | `test_m1.py:27-50`, `test_m2.py:25-61`, `test_m3.py:42-81` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep; runtime execution | test_m*.py |
| 30 | CHECK | No brittle exact string matching | Numeric/bit/invariant checks | gradelib |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` have docstrings | test_m1.py, test_m2.py, test_m3.py |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 negatives across 3 blocks | `entire-report.txt:391-409` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use allowed magnitudes | `entire-report.txt:385-410` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 21 properly formatted lines | `entire-report.txt:385-410` |
| 35 | CHECK | Rubric criteria detailed and precise | Per-block positives 13/15/16 (all ≤40) | `entire-report.txt:385-410` |
| 36 | CHECK | Rubric uses positive language for penalties | Bad-behavior lines use `-N` suffix | `entire-report.txt:391-409` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | `entire-report.txt:385-410` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | References CONTRACTS.md (env doc) only | `entire-report.txt:395` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP lines | `entire-report.txt:385-410` |
| 40 | CHECK | All required files present | Milestone layout complete | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task tree |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | C/build/FP flags match content | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard` present; worst-model 60% → medium tier — informational only | `task.toml:6`, `entire-report.txt:32-38` |
| 46 | CHECK | steps/ layout present | 3 milestones under `steps/` | task tree |
| 47 | CHECK | Each milestone has solveN.sh | solve1.sh, solve2.sh, solve3.sh | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has test_mN.py | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test scoped to that milestone | M1 divergence, M2 hazard partition, M3 manifest | test_m1.py, test_m2.py, test_m3.py |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore` excludes tests/; no COPY tests | `environment/.dockerignore:17`, `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ and tests/ excluded; answers recomputed at grade | `environment/.dockerignore`, gradelib docstring |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Held-out inputs only in gradelib; `/opt/ref` pristine copy | `gradelib.py:54-70`, `environment/Dockerfile:20-21` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 60% ≤ 80% | `entire-report.txt:37-38` |
| 55 | UNCHECK | Task is not too hard or unfair | Valid C-level witnesses can fail M2 grader due to Python int precondition | Blocker 1; `entire-report.txt:74-82` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: JSON object with `diverges` bool + witness for diverging kernels | `test_result_is_object`, `test_all_kernels_present`, `test_divergence_claims_correct` | covered | M1 instruction; `test_m1.py` |
| M1: witness must show real bit divergence | `test_divergence_claims_correct` | covered | `test_m1.py:39-44` |
| M1: non-diverging kernels survive held-out sweep | `test_divergence_claims_correct` | covered | `test_m1.py:46-50` |
| M2: HAZARD/BENIGN verdict per kernel | `test_all_kernels_present` | covered | `test_m2.py:17-23` |
| M2: HAZARD needs `witness` + `invariant` id | `test_partition_and_witnesses` | covered | M2 instruction; `test_m2.py:38-46` |
| M2: witness satisfies invariant under strict, violates under release | `test_partition_and_witnesses` | **gap** | `gradelib.py:179-181` — `recover` precondition uses Python int math on JSON integers |
| M2: partition matches ground truth | `test_partition_and_witnesses` | covered | `test_m2.py:31-37` |
| M3: manifest keyed by bare TU name | `test_sufficiency` via `_manifest()` | covered | M3 instruction; `test_m3.py:15-17` |
| M3: only allowed flag tokens | `_manifest()` | covered | `test_m3.py:21-22` |
| M3: sufficiency on held-out inputs | `test_sufficiency`, `test_held_out_consistency` | covered | `test_m3.py:42-65` |
| M3: minimality (re-adding flag re-breaks) | `test_minimality` | covered | `test_m3.py:67-81` |
| CONTRACTS: `absorbed_zero` when `a+b` rounds to `a` | M2 witness check | **gap** | Contract is double-rounding semantics; grader uses Python `int` addition |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_2/tests/gradelib.py` | Blocker 1, #27, #55, claim 1 |
| `steps/milestone_2/tests/test_m2.py` | Blocker 1, M2 alignment |
| `steps/milestone_2/instruction.md` | M2 schema (fixed), claim 2 |
| `steps/milestone_3/instruction.md` | M3 schema (fixed), claim 3 |
| `steps/milestone_1/instruction.md` | #1, M1 alignment |
| `environment/data/CONTRACTS.md` | `absorbed_zero` contract |
| `environment/Dockerfile` | #14, #15, #20 |
| `task.toml` | #43, #45, claim 4 |
| `entire-report.txt` | Agent stats, rubric, prior claims, agent failure analysis |
| `steps/milestone_2/solution/solve2.sh` | Oracle witness format (`1e16 1.0`) |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: fma-contraction-quarantine/ ===
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: milestone
WARNING: pinned_dependencies — false positive on multiline pip RUN (manual: pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 other failures |
| terminus-claude-opus-4-8 | 100.0% (5/5) | |
| oracle | 100.0% (3/3) | per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

**Per-test:** M2 `test_partition_and_witnesses` 9/10 — single failure consistent with `recover` witness grading bug.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone C/FP compiler-flag task; folder matches export |
| 1 Instruction | ☑ | Per-milestone concise; schemas explicit; no hints |
| 2 Environment | ☑ | Digest-pinned base; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Derives via compile/run; export 100%; local oracle not run |
| 4 Verifiers | ☐ | M2 `inv_holds` recover precondition bug |
| 5 Metadata | ☑ | Complete; docker_flags/gpus/gpu_types present |
| 6 Rubric | ☑ | Milestone `# Rubric N` format; per-block ≤40 |
| 7 LLMaJ & agent evidence | ☑ | Agent analysis confirms M2 spec bug; hack check pass |
| 8 Novelty & fairness | ☐ | Fairness issue on M2 integer witnesses |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the milestone progression, held-out rebuild grading, and anti-cheat design are excellent, and the earlier schema fixes (M2 `invariant` key, M3 bare filename keys, metadata fields) all look good. The rubric is also in the right milestone format with sensible per-milestone point blocks.

One fix needed before accept: in Milestone 2, the grader checks the `recover` / `absorbed_zero` witness precondition using Python integer math on JSON-loaded values, but the kernels run as C doubles. A witness like `[9007199254740992, 1]` can be valid at the binary level yet fail grading. Please coerce witness arguments to floats before evaluating invariant preconditions in `gradelib.inv_holds` (or document required double-form JSON numbers explicitly). Everything else looks ready once that alignment is fixed.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Milestones | yes | 1 |
| Instruction Styling | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Rubric | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |

---

_Generated by `./scripts/terminus review`, enriched after manual audit per `prompt.md`._
