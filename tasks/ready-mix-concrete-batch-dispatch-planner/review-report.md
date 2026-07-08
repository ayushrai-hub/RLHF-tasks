# Terminus Review Report: ready-mix-concrete-batch-dispatch-planner

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (from `entire-report.txt`) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** The task is strong overall: pinned/offline environment, solid optimizer/verifier structure, valid rubric format for a non-milestone task, and worst-model pass rate below the easy-tier blocker threshold. One real blocker remains: the verifier enforces deterministic byte-stable reruns, but `instruction.md` does not explicitly require determinism/reproducibility on unchanged inputs. Add that requirement explicitly, then this should be ready.

**Insights (concise):**
- Non-milestone rubric format is correct (flat `Agent ..., ±N` list; no milestone blocks required).
- Rubric positive total is exactly 40, which passes the `>40` blocker rule.
- Docker image is digest-pinned and includes verifier deps via `requirements.lock`.
- Go solver requirement is real and tested (source exists, compile, rerun, perturbed-input replanning).
- Main fairness gap is specification clarity around deterministic replay.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Tests require byte-identical deterministic reruns, but instruction only says compute from current inputs/not fixed plan and does not explicitly require deterministic reproducibility for unchanged inputs. | `tests/test_outputs.py` (`test_go_binary_reproduces_main_plan` compares canonical plan and summary for exact equality); `instruction.md` (no explicit determinism/reproducibility requirement). | Add explicit requirement in `instruction.md`: same unchanged inputs must reproduce identical plan and summary across reruns. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Deterministic rerun requirement is tested but not clearly stated (ChatGPT finding) | Agree | `tests/test_outputs.py` deterministic equality checks vs `instruction.md` missing explicit reproducibility text. |
| 2 | No medium-severity issues (ChatGPT finding) | Agree | Remaining reviewed issues are low/non-blocking except determinism gap above. |
| 3 | Optional instruction restructuring for readability (ChatGPT finding) | Agree | `instruction.md` is dense single-paragraph style; still complete but can be clearer. |
| 4 | Optional `test.sh` simplification (ChatGPT finding) | Agree | `tests/test.sh` trap/subshell reward pattern works but can be simplified. |
| 5 | Dockerfile digest pinning present (ChatGPT finding) | Agree | `environment/Dockerfile` uses digest-pinned Go base image. |
| 6 | Non-canonical Go base warning (external report warning) | Disagree | Terminus non-negotiable is digest pinning; `environment/Dockerfile` satisfies this and no canonical-base blocker is documented here. |
| 7 | "pytest not in Dockerfile" blocker from auto audit | Disagree | `environment/Dockerfile` installs `requirements.lock`; `environment/requirements.lock` includes `pytest` and `pytest-json-report`; `tests/test.sh` does not install at runtime. |
| 8 | Non-milestone task should use milestone rubric format | Disagree | `task.toml` has `number_of_milestones = 0`; rubric is correctly flat `Agent ..., ±N` lines in `entire-report.txt` (no `# Rubric N` blocks required). |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Concise 3-paragraph instruction. | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Direct task prompt style. | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No heavy headers/tables/codeblocks in instruction. | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No procedural walkthrough. | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Constraints are requirements, not solve script hints. | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No design-doc tables. | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | Deterministic replay requirement enforced by tests is not explicit in instruction. | `instruction.md`, `tests/test_outputs.py` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic multi-constraint dispatch optimization task. | `instruction.md`, `tests/test_outputs.py` |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Uniqueness cannot be proven from local artifacts alone. | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | Uses absolute `/app/...` paths. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Task name absent. | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary text found. | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Only package-manager installs. | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `requirements.lock` fully pinned and hash-locked. | `environment/requirements.lock`, `environment/Dockerfile` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned Go base image. | `environment/Dockerfile` |
| 16 | CHECK | Environment does not use context from outside the environment directory | Copies local `task_file/` only. | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | `.dockerignore` excludes `solution/` and `tests/` from image. | `environment/.dockerignore`, `environment/Dockerfile` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock/sysadmin patterns. | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file used. | Task layout |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | Deps installed in image; `test.sh` only validates/imports and runs pytest. | `environment/Dockerfile`, `environment/requirements.lock`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report shows oracle 3/3 pass and solvable status. | `entire-report.txt` |
| 22 | CHECK | Oracle does not require internet or downloading packages | No runtime network installs in oracle. | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Builds/runs Go solver from inputs and self-validates with model. | `solution/solve.sh`, `solution/solve.go` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Initializes reward, updates to 1 only on success path, otherwise 0. | `tests/test.sh` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No conditional branching on oracle/agent mode. | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Writes only 0/1 reward. | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Deterministic exact replay is tested but not explicitly stated in instruction. | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Behavioral scoring/constraint assertions across full plan. | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Runtime behavior checks dominate; no source grep. | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Assertions target structured values and constraints. | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | Test names are informative and grouped by class intent. | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | Three negative rubric lines present. | `entire-report.txt` |
| 33 | CHECK | Rubric scores are from allowed set | Uses ±1/2/3/5 only. | `entire-report.txt` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | All rubric lines follow required pattern. | `entire-report.txt` |
| 35 | CHECK | Rubric criteria are detailed and precise | Criteria are concrete, task-specific. | `entire-report.txt` |
| 36 | CHECK | Rubric criteria use positive language | Positive criteria are affirmative statements. | `entire-report.txt` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No `/tests/` or pytest references. | `entire-report.txt` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata/instruction references. | `entire-report.txt` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions in rubric lines. | `entire-report.txt` |
| 40 | CHECK | All required files present | Required regular-task files exist. | Task tree |
| 41 | CHECK | No unnecessary files in parent directory | No structural blocker in submission artifacts. | Task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present. | `task.toml` |
| 43 | CHECK | All other required metadata fields present | Required metadata fields present. | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | Data-processing + Go tags align with task behavior. | `task.toml`, artifacts |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty` present in `task.toml`; mismatch is non-blocking by policy anyway. | `task.toml`, `entire-report.txt` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A: non-milestone (`number_of_milestones = 0`). | `task.toml` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A: non-milestone task. | `task.toml` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A: non-milestone task. | `task.toml` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A: non-milestone task. | `task.toml` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests and Dockerfile does not copy tests. | `environment/.dockerignore`, `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution excluded from image context. | `environment/.dockerignore`, `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Input/model hash checks plus perturbed-input replanning test. | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone usage. | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model pass rate is 0%, far below >80% blocker threshold. | `entire-report.txt` |
| 55 | UNCHECK | Task is not too hard or unfair | Unfairness from unstated deterministic output requirement. | `instruction.md`, `tests/test_outputs.py` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Produce required plan and summary outputs with defined schema/fields | `TestOutputExists`, `TestSchema`, `test_summary_matches_plan` | covered | `instruction.md`, `tests/test_outputs.py` |
| Respect hard constraints, mandatory pours, prep precedence, score thresholds and floors | `TestHardConstraints`, `TestScoreThresholds` | covered | `instruction.md`, `tests/test_outputs.py` |
| Anti-shortcut distribution/diversity/quality guards | `TestAntiShortcut` suite | covered | `instruction.md`, `tests/test_outputs.py` |
| Go-language solver requirement with dynamic recomputation | `TestGoLanguageRequirement` suite | covered | `instruction.md`, `tests/test_outputs.py` |
| Deterministic exact reproducibility on unchanged inputs | `test_go_binary_reproduces_main_plan` | gap (unstated in instruction) | `instruction.md`, `tests/test_outputs.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker evidence (#7/#27/#55), path/clarity checks |
| `tests/test_outputs.py` | Determinism requirement evidence, test coverage checks |
| `tests/test.sh` | Reward/dependency behavior checks |
| `environment/Dockerfile` | Pinning/env dependency checks |
| `environment/requirements.lock` | Runtime dependency pinning proof |
| `environment/.dockerignore` | Anti-cheating image exclusion proof |
| `solution/solve.sh` | Oracle behavior proof |
| `solution/solve.go` | Dynamic planner implementation proof |
| `task.toml` | Metadata and non-milestone format proof |
| `entire-report.txt` | Agent stats, oracle status, and platform rubric proof |

---

## 7. Validation & agent performance

### Validation

`./scripts/terminus validate ready-mix-concrete-batch-dispatch-planner.`  
Pass (0 errors, 0 warnings, informational notes only).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Mostly Go delivery/runtime failures per report |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Solved full task in report |
| oracle | 100.0% (3/3) | Solvable and oracle passes |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational; mismatch would not block) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Reviewed actual task folder `ready-mix-concrete-batch-dispatch-planner.` |
| 1 Instruction | ☑ | Found determinism clarity gap only |
| 2 Environment | ☑ | Digest pinning/deps/no internet constraints pass |
| 3 Oracle | ☑ | Reflective/dynamic oracle and pass evidence from report |
| 4 Verifiers | ☑ | Strong tests; deterministic replay requirement found unstated |
| 5 Metadata | ☑ | Metadata complete; non-milestone |
| 6 Rubric | ☑ | Non-milestone format correct; positive cap = 40 (pass) |
| 7 Report adjudication | ☑ | Challenged ChatGPT + external report claims with file evidence |
| 8 Final disposition | ☑ | Revise due to one high-severity blocker |

---

## 9. Reviewer note (copy-paste to portal)

Strong task overall: the environment setup is clean and pinned, the optimization/verifier design is robust, and the anti-cheat + perturbed-input checks are thoughtful. One fix is needed before acceptance: the tests require deterministic byte-identical reruns on unchanged inputs, but the instruction currently does not explicitly state that reproducibility requirement. Please add a clear deterministic-output requirement (same inputs must reproduce the same plan and summary), and this should be ready.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |