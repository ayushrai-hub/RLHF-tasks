# Terminus Review Report: `tbrain-minimum-version-setting`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Rust feature-addition task with pinned offline env, real cargo rebuilds, and solid semver/literal enforcement coverage. One real blocker: `test_dump_and_other_settings_remain_compatible` asserts exact double-quoted `--dump` output (`set minimum-version := "0.0.1"`) but `instruction.md` only says to preserve `--dump` behavior and never documents the required dumped string form. A near-pass agent failed solely on single-quote dump output despite correct feature logic. Non-milestone rubric uses the correct flat format (not milestone headers); rubric +41 is low-severity polish only.

**Insights (concise):**

- ChatGPT High finding on `--dump` quote style is **confirmed** with file evidence; automated script blockers on #14, #31, #54 were **false positives**.
- Worst-model pass rate is **60%** (GPT-5.5), not 100%; task is medium-tier, not rejected (>80%).
- Platform rubric is a **flat** non-milestone list (no `# Rubric 2+`); format is correct.
- All four `test_*` functions have docstrings; only module-level docstring is missing (validate warning, not portal #31 fail).
- Pip deps in Dockerfile are pinned (`pytest==8.4.2`, `pytest-json-ctrf==0.3.5`); `rustup` pins 1.89.0.
- Oracle not run locally (Docker socket unavailable); static review of `solve.sh` + `fix.patch` shows patch-and-build approach aligned with instruction.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `--dump` test requires exact double-quoted rendering for `minimum-version`, but instruction never states dumped string form | `instruction.md:3` says preserve `--dump`; `tests/test_outputs.py:151` asserts `'set minimum-version := "0.0.1"'`; `entire-report.txt:51` documents agent failure on single vs double quotes (9/10 on that test) | Add explicit instruction that `--dump` must render `minimum-version` in normal justfile syntax using double-quoted string form (e.g. `set minimum-version := "0.0.1"`), consistent with other string-expression settings |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier requires `--dump` to print `set minimum-version := "0.0.1"` with double quotes but instruction does not state quote style (ChatGPT High) | **Agree** | `instruction.md:3`; `tests/test_outputs.py:151`; `entire-report.txt:51,61` |
| 2 | Core feature behavior well covered (compatible/equal run, future stops, invalid rejected, existing settings work) (ChatGPT Medium none) | **Agree** | `tests/test_outputs.py:49-156`; all four tests map to `instruction.md:1-3` |
| 3 | Rubric positive total 41, slightly above ≤40 target (ChatGPT Low) | **Agree** (Low only) | `entire-report.txt:243-256` sums to +41; `docs/guidelines/rubrics.md:29-31` target 10–40 |
| 4 | Dockerfile FROM digest-pinned (ChatGPT) | **Agree** | `environment/Dockerfile:1,3` both `FROM ...@sha256:...` |
| 5 | Instruction sufficiency FAIL on dump quote style (entire-report.txt) | **Agree** | `entire-report.txt:46,59-61` matches artifact gap |
| 6 | LLMaJ `behavior_in_task_description` PASS (entire-report.txt:80) | **Partially agree** | Dump preservation claimed covered by `instruction.md:3`, but exact double-quote dump form is unstated — gap remains |
| 7 | Harbor review READY TO USE / terse instruction acceptable (entire-report.txt:192-196) | **Partially agree** | Task structure sound; terse style OK for hard Rust task, but dump rendering gap is separate from brevity |
| 8 | Test quality: no `--version` test though instruction mentions version reporting (entire-report.txt:222-224) | **Agree** (not a blocker) | No `test_*` asserts `--version`; regression risk low; not listed in section 2 |
| 9 | Automated review #14 pip unpinned | **Disagree** | `environment/Dockerfile:33-35` uses `pytest==8.4.2`, `pytest-json-ctrf==0.3.5` |
| 10 | Automated review #31 missing docstrings | **Disagree** | `tests/test_outputs.py:50,85,107,135` all have function docstrings; validate warning is module-level only |
| 11 | Automated review #54 worst-model 100% too easy | **Disagree** | `entire-report.txt:26-27` GPT-5.5 60%, Claude 100%; worst = 60% (<80% threshold) |
| 12 | Automated review #36 rubric negative phrasing | **Disagree** | `entire-report.txt:257` uses "does not" with **-5** score (valid negative criterion); #36 targets positive-score negative phrasing |
| 13 | Non-milestone task uses milestone rubric format | **Disagree** | `entire-report.txt:243-262` is flat `Agent …, ±N` list with no `# Rubric 2+` headers; `task.toml:9` `number_of_milestones = 0`; matches `docs/guidelines/rubrics.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Single paragraph, ~155 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads like engineer request, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only, no dev walkthrough | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Describes feature behavior, not file edits | `instruction.md` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | UNCHECK | Well specified | `--dump` rendering form for new setting unstated | `instruction.md:3`, `tests/test_outputs.py:151` |
| 8 | CHECK | Interesting | Realistic Rust CLI feature work | `instruction.md`, env repo |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app` used | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline env; cargo fetch at build only | `task.toml:23`, `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned with == | Both pytest packages pinned | `environment/Dockerfile:33-35` |
| 15 | CHECK | FROM digest-pinned | Both stages pinned | `environment/Dockerfile:1,3` |
| 16 | CHECK | Context in environment/ only | COPY repo/ only | `environment/Dockerfile:40` |
| 17 | CHECK | No ground truth in env | No solution/tests COPY; `Resolution::` false-positive on "solution:" scan | `environment/Dockerfile`, grep |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts safe | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:33-35`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed (Docker unavailable) | oracle run failed: socket permission |
| 22 | CHECK | Oracle no internet | patch + offline cargo build | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Applies multi-file patch, builds binary | `solution/solve.sh`, `solution/fix.patch` |
| 24 | CHECK | reward.txt canonical | Writes 0/1 on failure path | `tests/test.sh:16-20` |
| 25 | CHECK | Same verifier for oracle/agent | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Dump exact double-quote assertion unstated in instruction | `tests/test_outputs.py:151`, `instruction.md:3` |
| 28 | CHECK | Tests check correctness | Builds binary, runs recipes, checks side effects | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact matching | Error substrings specified in instruction | `instruction.md:1-3`, `tests/test_outputs.py:100-130` |
| 31 | CHECK | Informative test names/docstrings | Four named tests, each with docstring | `tests/test_outputs.py:49-135` |
| 32 | CHECK | ≥3 negative rubric criteria | 7 negatives | `entire-report.txt:257-262` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All valid | `entire-report.txt:243-262` |
| 34 | CHECK | Agent-line format | 21 Agent lines | `entire-report.txt:243-262` |
| 35 | CHECK | Rubric detailed/precise | Task-specific semver/dump/side-effect criteria | `entire-report.txt:243-262` |
| 36 | CHECK | Positive rubric phrasing | "does not" only on negative-score lines (-5) | `entire-report.txt:257` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:243-262` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:243-262` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:243-262` |
| 40 | CHECK | Required files present | All standard layout files | task dir |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task dir |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | version, timeouts, env block present | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Rust CLI parser task | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 60% → medium tier | `task.toml:6`, `entire-report.txt:26-27` — not a revision blocker per policy |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially cheat | Must compile/run modified Rust binary | `tests/test_outputs.py:12-21` |
| 53 | CHECK | Git pinned at build | git init + commit in Dockerfile, no unpinned clone | `environment/Dockerfile:46-50` |
| 54 | CHECK | Not too easy | Worst model 60% (<80%) | `entire-report.txt:26-27` |
| 55 | UNCHECK | Not too hard/unfair | Dump quote expectation tested but not specified; caused documented near-miss failure | `entire-report.txt:51,61`, `tests/test_outputs.py:151` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| `minimum-version` accepts plain `MAJOR.MINOR.PATCH` literal | `test_satisfied_and_equal_requirements_run_recipes` | covered | `instruction.md:1`, `tests/test_outputs.py:56` |
| Older/equal requirement runs recipes normally | `test_satisfied_and_equal_requirements_run_recipes` | covered | `instruction.md:3`, `tests/test_outputs.py:66-81` |
| Newer requirement stops before recipes; diagnostic with version fragments | `test_future_requirement_fails_before_recipe_side_effects` | covered | `instruction.md:1-2`, `tests/test_outputs.py:98-103` |
| Invalid semver diagnostic | `test_invalid_and_non_literal_values_are_rejected` | covered | `instruction.md:3`, `tests/test_outputs.py:110` |
| Non-plain string diagnostic | `test_invalid_and_non_literal_values_are_rejected` | covered | `instruction.md:3`, `tests/test_outputs.py:111-113` |
| Preserve existing settings + recipe execution | `test_dump_and_other_settings_remain_compatible` | covered | `instruction.md:3`, `tests/test_outputs.py:154-156` |
| Preserve `--dump` including new setting format | `test_dump_and_other_settings_remain_compatible` | **gap** | `instruction.md:3` generic; `tests/test_outputs.py:151` exact double-quote |
| Preserve version reporting (`--version`) | — | gap (low) | `instruction.md:3`; no dedicated test |
| Indented strings rejected | `test_invalid_and_non_literal_values_are_rejected` | partial | `instruction.md:3`; triple-single tested, not `"""` variant |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #27, blocker 1, spec alignment |
| `tests/test_outputs.py` | #27, #30, #31, blocker 1 |
| `tests/test.sh` | #20, #24 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `task.toml` | #44, #45, #46-49 N/A |
| `solution/solve.sh` | #22, #23 |
| `solution/fix.patch` | #23, dump Display pattern |
| `entire-report.txt` | #45, #54, adjudication, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: tbrain-minimum-version-setting/ ===
Summary: 0 error(s), 8 warning(s), 2 info
Task type detected: regular
```

Warnings include module-level docstring, `solution:` false-positive hints in Rust `Resolution::` code, and validate script pip line heuristic (actual pins present).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 1 timeout, 1 other |
| terminus-claude-opus-4-8 | 100.0% (5/5) | |
| oracle | 100.0% (3/3) | platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no — worst 60% is medium; declared hard not defensible on rates alone (informational) |

Per-test: `test_dump_and_other_settings_remain_compatible` 9/10 — sole systematic spec-friction point.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `tbrain-minimum-version-setting`; regular layout; Rust build task |
| 1 Instruction | ☑ | Terse but clear; dump form gap |
| 2 Environment | ☑ | Digest-pinned, offline, tmux+asciinema, deps baked |
| 3 Oracle | ☑ | Static pass; Docker oracle not run |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; one spec gap |
| 5 Metadata | ☑ | `number_of_milestones = 0`; category/tags fit |
| 6 Rubric | ☑ | Flat non-milestone format correct; +41 low polish |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed for dump quotes |
| 8 Novelty & fairness | ☑ | Multi-file Rust feature; dump quote unfair without spec |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust task — pinned offline build, real cargo verification, and the semver/literal enforcement tests are well thought out. The one fix before accept: `test_dump_and_other_settings_remain_compatible` expects `--dump` to emit `set minimum-version := "0.0.1"` with double quotes, but the instructions only say to preserve `--dump` and never spell out that dumped string form. One agent got everything else right and failed on single-quote dump output. Please add a line documenting that `--dump` should render the new setting in normal justfile syntax with double-quoted strings. Optional polish: trim rubric positives from 41 to ≤40 (e.g. merge the `--version` +1 into the compatibility line).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no (Low +41 only) | — |
| Task Difficulty | no (#54 passes at 60%) | — |
| Pinning Issues | no | — |
| Milestones | no (correct non-milestone layout) | — |
| Metadata Issues | no (#45 mismatch informational only) | — |
| Environment | no | — |
| Oracle Solution Issues | no (not executed; static OK) | — |
