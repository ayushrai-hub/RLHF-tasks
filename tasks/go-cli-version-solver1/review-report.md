# Terminus Review Report: `go-cli-version-solver1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed (Docker daemon unavailable locally; static review + platform report 100%) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** No High or Medium blockers. Instruction, tests, oracle, environment, metadata, and platform rubric all align. Category `build-and-dependency-management`, CONFLICT first-constraint reporting, and bare `NO_UPGRADE` are correctly specified and tested. Platform rubric is flat (non-milestone) at 39/40 positive points. Worst-model pass rate 60% — appropriately calibrated. Only optional Low polish remains (dense instruction layout, one rubric phrasing line, pre-release inter-identifier ordering not sole test differentiator).

**Insights (concise):**

- Rubric is **not** in milestone format — flat `Agent …, ±N` list with no `# Rubric 2+` headers; correct for `number_of_milestones = 0`.
- ChatGPT Accept decision verified; prior revision items (category, CONFLICT, NO_UPGRADE) are addressed in artifacts.
- 34 parameterized fixtures cover all commands, constraint types, backtracking, diamond deps, yanks, locks, upgrades, pre-releases, and state persistence.
- Automated `terminus review` flagged #36 rubric phrasing — Medium per checklist, not a revision blocker (single Medium → Accept with note).
- GPT-5.5 at 100% does not block; worst model Claude Opus 4.8 at 60% is within medium tier (≤80%).
- `task.toml` declares `hard` vs platform `MEDIUM` — informational only, never blocks.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High severity none; prior issues addressed (ChatGPT) | Agree | `task.toml:7` category; `instruction.md:5` NO_UPGRADE; `instruction.md:5` CONFLICT first constraint; `tests/test_outputs.py:61-63,281-288` |
| 2 | Category now `build-and-dependency-management` (ChatGPT / author comments) | Agree | `task.toml:7`; matches `docs/task-type-taxonomy.md` |
| 3 | NO_UPGRADE documented as bare output (ChatGPT) | Agree | `instruction.md:5` "prints … NO_UPGRADE if already best"; `tests/test_outputs.py:61-63` expects `NO_UPGRADE` alone |
| 4 | CONFLICT reports first constraint added (ChatGPT) | Agree | `instruction.md:5` "FIRST constraint added"; `tests/test_outputs.py:281-288` `conflict_reports_first_constraint` |
| 5 | Rubric correctly scoped for non-milestone task (ChatGPT) | Agree | `entire-report.txt:373-389` flat list, no `# Rubric 2+`; 39 positive pts via `rubric-points` |
| 6 | Tests cover command protocol, constraints, yanks, locks, transitive/diamond/backtracking, pre-releases, remove, persistence (ChatGPT) | Agree | `tests/test_outputs.py:12-289` — 34 fixtures |
| 7 | Medium severity none (ChatGPT) | Agree | No untested instruction requirements or unfair verifiers found |
| 8 | Optional: break dense instruction into sections (ChatGPT / Harbor review) | Agree (Low only) | `instruction.md:1-5` — 3 dense paragraphs; complete but hard to scan |
| 9 | Optional: pre-release inter-identifier ordering test gap (ChatGPT / test quality review) | Agree (Low only) | `tests/test_outputs.py:202-211` — `prerelease_sort_order` resolves to full release `1.0.0`, not beta over alpha |
| 10 | Dockerfile digest-pinned canonical Go base (ChatGPT) | Agree | `environment/Dockerfile:1` `golang:1.24-bookworm@sha256:1a6d4452…` |
| 11 | Decision Accept (ChatGPT) | Agree | Artifacts support Accept; no real blockers |
| 12 | LLMaJ behavior_in_task_description PASS | Agree | All tested behaviors named in `instruction.md` |
| 13 | LLMaJ behavior_in_tests PASS | Agree | All instruction commands/constraints have fixtures |
| 14 | Instruction sufficiency PASS — agent failures are implementation not spec gaps | Agree | `entire-report.txt:74-98`; diamond_conflict failures are solver logic, spec is clear |
| 15 | Harbor review WARNING — dense instruction | Agree (Low) | Stylistic; not a correctness gap |
| 16 | Harbor review — generic test docstrings | Agree (Low) | `tests/test_outputs.py:306-307` single generic docstring on parametrize |
| 17 | Test quality — pre-release lexicographic vs semver-spec ordering | Agree (Low) | `solution/solve.sh:53` lexicographic `v.pre < o.pre`; fixtures use alpha/beta/rc that agree under both schemes |
| 18 | Author: oracle 1.000, feedback addressed | Agree (static) | `solution/solve.sh` full algorithmic implementation; platform `oracle: 100.0%` in `entire-report.txt:31` |
| 19 | Non-milestone task incorrectly using milestone rubric format (user concern) | **Disagree** | `task.toml:9` `number_of_milestones = 0`; rubric has no `# Rubric N` milestone blocks — flat list per `rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 substantive paragraphs (~286 words) | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer-style request; no synthetic LLM patterns | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Protocol spec only; build invocation is required interface | `instruction.md:1` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Commands/outputs specified; no algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Full CLI protocol with constraints and resolution rules | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Package version resolver mirrors real tooling | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Semver backtracking solver with lock/upgrade/yank protocol | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/solver.go`, `/app/solver` | `instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No `go-cli-version-solver` string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | apt/pip only at build time | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1 pytest-json-ctrf==0.3.5` | `environment/Dockerfile:6` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest on FROM line | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | No COPY instructions | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Only Go toolchain + verifier Python | `environment/Dockerfile` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:6`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Platform oracle 100%; solve.sh deterministic algorithm | `entire-report.txt:31`, `solution/solve.sh` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes/compiles Go only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | ~350-line Go resolver with backtracking | `solution/solve.sh:4+` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | mkdir + 0/1 writes present | `tests/test.sh:2-16` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | echo 0/1 only | `tests/test.sh` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Every fixture maps to instruction clause | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Version selection and conflict semantics asserted | `tests/test_outputs.py` fixtures |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | subprocess stdout comparison only | `tests/test_outputs.py:309-318` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | CLI protocol mandates exact output tokens | `instruction.md`, `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | Module docstring + parametrize keys name behaviors | `tests/test_outputs.py:1-4,306-307` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives (-5,-5,-5,-3) | `entire-report.txt:386-389` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:373-389` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 17 Agent lines | `entire-report.txt:373-389` |
| 35 | CHECK | Rubric criteria are detailed and precise | 39/40 positive pts — under cap | `rubric-points` output |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | One line uses "Agent does not persist state…" | `entire-report.txt:389` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ or pytest refs | `entire-report.txt:373-389` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:373-389` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:373-389` |
| 40 | CHECK | All required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh, test_outputs.py | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | go + dependency tags; build-and-dependency-management | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | difficulty present; worst-model 60% medium tier | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — non-milestone task | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Inputs via stdin per run; no fixture files in /app | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% ≤ 80% | `entire-report.txt:26-27` |
| 55 | CHECK | Task is not too hard or unfair | Agent failures are implementation complexity; spec sufficient per LLMaJ | `entire-report.txt:74-98` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 36, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| PUBLISH registers version, prints OK | `publish_single` | covered | `tests/test_outputs.py:13-16` |
| YANK excludes from resolution | `yank_excludes_version`, `yank_forces_backtrack` | covered | `tests/test_outputs.py:37-40,169-180` |
| DEPEND declares dependency | `dependency_resolution`, `diamond_*` | covered | `tests/test_outputs.py:41-44,77-103` |
| ADD top-level constraint | all resolve fixtures | covered | `tests/test_outputs.py` |
| ^ ~ >= exact range constraints | `resolve_*`, `caret_*`, `tilde_*` | covered | `tests/test_outputs.py:17-36,69-76` |
| Pre-release exclusion/inclusion rules | `prerelease_*` fixtures | covered | `tests/test_outputs.py:182-230` |
| Pre-release sort below release | `prerelease_sort_order` | covered | `tests/test_outputs.py:202-211` |
| Pre-release inter-identifier ordering decides outcome | — | gap (Low) | No fixture picks beta over alpha without full release |
| RESOLVE highest compatible, alphabetical output | `multiple_packages_alphabetical` | covered | `tests/test_outputs.py:65-68` |
| Transitive + diamond constraint intersection | `diamond_dependency`, `diamond_conflict` | covered | `tests/test_outputs.py:77-103` |
| Backtracking on conflict | `backtrack_to_lower_version`, `deep_backtrack_with_prerelease` | covered | `tests/test_outputs.py:105-118,255-267` |
| CONFLICT reports FIRST constraint | `conflict_reports_first_constraint`, `diamond_conflict` | covered | `tests/test_outputs.py:92-103,281-288` |
| State persists across RESOLVE | `multi_resolve_state_persists`, `yank_after_resolve_changes_result` | covered | `tests/test_outputs.py:232-253` |
| LOCK / LOCK_ERROR | `lock_basic`, `lock_error_violates_constraint` | covered | `tests/test_outputs.py:49-56` |
| UNLOCK / UNLOCK_ERROR | `unlock_basic`, `unlock_error_not_locked` | covered | `tests/test_outputs.py:120-134` |
| UPGRADE / bare NO_UPGRADE | `upgrade_to_highest`, `upgrade_no_change` | covered | `tests/test_outputs.py:57-63` |
| REMOVE clears lock; keeps transitive dep | `remove_package`, `remove_clears_lock`, `remove_keeps_transitive` | covered | `tests/test_outputs.py:135-154,269-279` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, #46-49 N/A, category |
| `environment/Dockerfile` | #13-18, #20, #50-53 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-cli-version-solver1/ ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst model |
| oracle | 100.0% (3/3) | Platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | MEDIUM (`entire-report.txt:21`) |
| Tier match (#45) | informational only — CHECK #45 for presence |

### Rubric format check (non-milestone)

| Check | Result | Proof |
|-------|--------|-------|
| `number_of_milestones = 0` | pass | `task.toml:9` |
| Flat `Agent …, ±N` list (no `# Rubric 2+`) | pass | `entire-report.txt:373-389` |
| Positive total ≤ 40 | pass (39) | `./scripts/terminus rubric-points entire-report.txt` |
| ≥ 3 negatives | pass (4) | `entire-report.txt:386-389` |
| Milestone rubric format misuse | **not present** | No per-milestone blocks |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `go-cli-version-solver1` matches report; regular layout |
| 1 Instruction | ☑ | Dense but complete; absolute paths; no hints |
| 2 Environment | ☑ | Digest-pinned Go; tmux+asciinema; pinned pytest; no tests/solution COPY |
| 3 Oracle | ☑ | Full Go implementation; not hardcoded (Docker oracle not run locally) |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; 34 fixtures; behavior tests |
| 5 Metadata | ☑ | category/tags/languages match; allow_internet=false |
| 6 Rubric | ☑ | Flat non-milestone format; 39/40 pts; #36 phrasing Low/Medium polish |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; worst model 60%; diamond_conflict hardest test |
| 8 Novelty & fairness | ☑ | Multi-step algorithmic task; cheating paths closed |
| 9 Long context | N/A | No long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Nice work — this is in good shape. The semver resolver spec is complete end to end: commands, constraint types, backtracking, diamond deps, yanks, locks/upgrades, and state persistence all line up with the fixtures. Category, CONFLICT first-constraint reporting, and bare `NO_UPGRADE` look correctly addressed from the prior round. Dockerfile and verifier setup are clean with a pinned Go base and deps baked in the image. Agent rates (60% worst model) feel right for the difficulty.

Only optional polish if you want it: split the dense instruction into headed sections for readability, rephrase the one rubric line that says "Agent does not persist state…" into positive phrasing with a negative score, and optionally add a fixture where pre-release identifier ordering (alpha vs beta) is the deciding factor. None of that blocks acceptance.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no (Low polish only) | — |
| Test Alignment/Coverage Issues | no (Low pre-release ordering gap) | — |
| Rubric | no (#36 phrasing is Medium polish, not >40 cap) | — |
| All others | no | — |

*No blockers — error categories: none*
