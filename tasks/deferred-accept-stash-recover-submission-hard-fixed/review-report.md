# Terminus Review Report: deferred-accept-stash-recover-submission-hard-fixed

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (from submission export) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** none

**Decision (concise):** This submission is strong and review-ready. The previously reported blockers around pip pinning, missing test docstrings, and tie-break coverage are not valid on current artifacts. The only real issue found is metadata-category fit (`system-administration` for a Rust code-repair/debug task), which is medium severity and not a blocker by itself.

**Insights (concise):**
- Platform rubric is valid for a non-milestone task: flat `Agent ..., ±N` lines and no `# Rubric 2+` blocks.
- Rubric positive total is 29 (`<=40` cap), with 4 negatives present.
- All seven tests are present and each test function has a docstring.
- Instruction/test/docs alignment is strong for the recovery semantics under test.
- Agent difficulty evidence is hard-tier compatible (worst model 20%, not >80%).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Category mismatch is the main blocker (ChatGPT + Reviewer Feedback) | Partially agree | `task.toml` sets `category = "system-administration"` while task work is Rust debugging in `/app/environment` (`instruction.md`, `tests/test_outputs.py`), but category/tag mismatch is medium severity in checklist and not an automatic revise blocker. |
| 2 | Pick tie-break branch is untested (Reviewer Feedback) | Disagree | `tests/test_outputs.py` contains `test_recovery_g_pick_tie_break_tag_then_wave` asserting tag/wave tie-break order. |
| 3 | Rubric rewards “just reading docs” (Reviewer Feedback) | Disagree | Rubric lines in `entire-report.txt` include no “read docs” reward; lines are implementation/build/behavior oriented. |
| 4 | Missing test docstrings is a blocker (auto review output) | Disagree | Every `test_recovery_*` function in `tests/test_outputs.py` includes a docstring. |
| 5 | Pip dependencies are unpinned (auto review output) | Disagree | `environment/Dockerfile` pins verifier packages as `pytest==8.4.1` and `pytest-json-ctrf==0.3.5`; the flagged `pip install --no-cache-dir` line is a command, not a dependency spec. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Brief, human-readable instruction length and scope | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Reads like an engineering request with compact sections | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks) | Uses light section headers only; no heavy markdown artifacts | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes/constraints, no walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | No algorithmic hint leakage | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No design-spec table dump in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Explicit commands, outputs, and pass condition | `instruction.md` |
| 8 | UNCHECK | Instruction is interesting (useful to some group of developers) | Subjective quality item; not machine-verifiable | — |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Full corpus uniqueness cannot be proven locally | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | Paths are absolute | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Folder/task name not embedded in prompt text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary markers detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | No runtime web fetch logic | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Verifier pip deps are pinned with `==` | `environment/Dockerfile` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Rust base image includes digest pin | `environment/Dockerfile` |
| 16 | CHECK | Environment does not use context from outside the environment directory | Dockerfile copies only task environment artifacts | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No leaked solution material in env files reviewed | `environment/Dockerfile`, `instruction.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/container breakout patterns | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution) | No compose file used for this regular task | task layout |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | All verifier deps preinstalled; `test.sh` runs pytest only | `environment/Dockerfile`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Submission export shows oracle 3/3 pass | `entire-report.txt` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` edits/builds locally only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rewrites/fixes Rust modules and builds from source | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Reward path initialized and failure path writes 0 | `tests/test.sh` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs (no conditional logic) | No oracle branching in test logic | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Reward output is strictly 0/1 | `tests/test.sh` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Tests match documented recovery semantics and outputs | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Assertions validate behavior/state/order, not formatting | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Runtime behavior checks only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Assertions are structured and semantic | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All seven test functions have informative docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negative lines present | `entire-report.txt` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores in allowed set | `entire-report.txt` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | All lines conform `Agent ..., ±N` | `entire-report.txt` |
| 35 | CHECK | Rubric criteria are detailed and precise | Behavior-specific lines tied to this task | `entire-report.txt` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Positive rewards describe desired behavior; negatives use penalties | `entire-report.txt` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No `/tests/` or pytest references | `entire-report.txt` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata/instruction references | `entire-report.txt` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mention in rubric lines | `entire-report.txt` |
| 40 | CHECK | All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml) | Required regular-task files present | task layout |
| 41 | CHECK | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | No task-local stray artifacts identified | task layout |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both fields present | `task.toml` |
| 43 | CHECK | All other required metadata fields present | Required metadata present | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories are applicable to the task | Category is mismatched (`system-administration` vs debugging/software-engineering core activity) | `task.toml`, `instruction.md`, `tests/test_outputs.py`, `docs/task-type-taxonomy.md` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Difficulty field present; hard-tier evidence is consistent | `task.toml`, `entire-report.txt` |
| 46 | UNCHECK | steps/ layout present with per-milestone files (not root instruction/tests/solution) | N/A: non-milestone task | `task.toml` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A: non-milestone task | `task.toml` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A: non-milestone task | `task.toml` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A: non-milestone task | `task.toml` |
| 50 | CHECK | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests copied into image | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution not copied into runtime image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests run behaviors from compiled binary over fresh workspaces | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone/floating commit pulls in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model rate is 20% | `entire-report.txt` |
| 55 | CHECK | Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck) | Docs + tests + oracle evidence indicate fair, solvable task | `instruction.md`, `tests/test_outputs.py`, `entire-report.txt` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 8, 9, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build from `/app/environment/Cargo.toml` and run gatectl commands | all tests via `_build_binary()` and `_run()` | covered | `instruction.md`, `tests/test_outputs.py` |
| Produce `.state/row-obs.jsonl` and `.state/dispatch-obs.jsonl` | all tests read observation products | covered | `instruction.md`, `tests/test_outputs.py` |
| Recovery replay and anchor semantics | `test_recovery_b`, `test_recovery_c`, `test_recovery_d`, `test_recovery_e`, `test_recovery_f` | covered | `tests/test_outputs.py` |
| Duplicate tag/wave identity and ordering semantics | `test_recovery_a`, `test_recovery_g` | covered | `tests/test_outputs.py` |
| “All seven verifier tests must pass” | seven `test_recovery_*` functions | covered | `instruction.md`, `tests/test_outputs.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | metadata checks, milestone applicability, category fit |
| `instruction.md` | prompt quality, path checks, requirement scope |
| `environment/Dockerfile` | pinning/image/test-solution copy checks |
| `tests/test.sh` | reward and runtime-install checks |
| `tests/test_outputs.py` | docstrings, behavior coverage, tie-break coverage |
| `solution/solve.sh` | oracle realism/no-hardcode checks |
| `entire-report.txt` | rubric checks, oracle outcome, agent pass rates, external-claim adjudication |
| `docs/task-type-taxonomy.md` | category applicability standard |
| `docs/guidelines/rubrics.md` | non-milestone rubric format and point-cap rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate deferred-accept-stash-recover-submission-hard-fixed/
./scripts/terminus audit deferred-accept-stash-recover-submission-hard-fixed/ --report entire-report.txt
./scripts/terminus review deferred-accept-stash-recover-submission-hard-fixed/ --report entire-report.txt
./scripts/terminus rubric-points entire-report.txt --milestones 0
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 20.0% (1/5) | Hard-tier compatible |
| terminus-gpt5-5 | 80.0% (4/5) | Near threshold but not >80 worst-model |
| oracle | 100.0% (3/3) | Solvable signal |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Reviewed target folder and report identity |
| 1 Instruction | ☑ | Prompt style/content/path checks completed |
| 2 Environment | ☑ | Dockerfile pinning and copy-scope checks completed |
| 3 Oracle | ☑ | `solve.sh` reviewed; oracle result pulled from export |
| 4 Verifiers | ☑ | `test.sh` and all `test_outputs.py` tests reviewed |
| 5 Metadata | ☑ | Found category mismatch (medium note) |
| 6 Rubric | ☑ | Non-milestone flat format confirmed; +29 points verified |
| 7 External claims | ☑ | Every supplied claim adjudicated with proof |

---

## 9. Reviewer note (copy-paste to portal)

This is a strong task overall: the environment is pinned/offline, the tests are behavior-focused, and the recovery semantics are exercised well. I verified the tie-break behavior is covered in tests and the rubric format is correct for a non-milestone task, with positive points under the cap. The one thing to improve is metadata fit: please switch `category` from `system-administration` to a code-repair category like `debugging` or `software-engineering`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | no | — |