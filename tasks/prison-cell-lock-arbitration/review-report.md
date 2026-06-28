# Terminus Review Report: `prison-cell-lock-arbitration`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 9 warnings) |
| **Oracle** | not executed locally (platform report: 100% 3/3) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Rust/C split-brain debugging task with solid anti-cheat design and appropriate hard difficulty (Claude 0%, GPT 5/5). Two High blockers drive Revise: `layout.md` tells agents stale emergency overrides should end runs in `stale_override`, while verifiers require `filter_w2` to drop stale rows so `load_pulse` and `shadow_drop` converge; and the platform rubric references `/app/tests/test.sh`. ChatGPT’s `test_delayed_commit` and fixture-integrity findings are real gaps but Medium at most—not standalone blockers. Docker base uses canonical `ubuntu:24.04` digest; rubric format is correctly flat (not milestone-style).

**Insights (concise):**

- All 5 Claude Opus 4.8 runs failed identically on `test_load_pulse` + `test_shadow_drop` because agents followed `layout.md:28` and left `filter_w2` as passthrough.
- Solution requires five coordinated fixes (`p4`, `w2`, `run_loop`, `r6`, `t8`); patch applies via `solution/patch.diff`—not hardcoded output.
- `ubuntu:24.04@sha256:0d39fcc…` matches canonical list in `docs/guidelines/dockerfxile.md`; Harbor “non-canonical base” claim in export is wrong.
- Platform rubric is flat `Agent …, ±N` (correct for `number_of_milestones = 0`); not milestone `# Rubric N` format.
- Automated review false-positives: #14 (pip `==` on continuation lines), #54 (used GPT 100% instead of Claude 0% worst-model), #31 (all test functions have docstrings).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `layout.md` describes stale emergency overrides as producing `stale_override` outcome; tests require filtering stale rows so `load_pulse` and `shadow_drop` converge | `environment/docs/layout.md:28`; `tests/test_outputs.py:73-77,87-93`; `environment/fac_b2/src/run_loop.rs:213-216`; `solution/patch.diff:6-13`; export lines 64-87 | Reword baseline-generation invariant: stale emergency rows are **dropped before replay**; `load_pulse` and `shadow_drop` must end `converged` after filtering. Align wording with instruction “rejects stale emergency overrides.” |
| 2 | High | Rubric | #37 | Platform rubric references `/app/tests/test.sh` | `entire-report.txt:421` — `Agent runs bash /app/tests/test.sh or run_sim_driver.sh…` | Remove `/tests/` reference; e.g. “Agent runs the verifier command from instruction.md” or “Agent runs run_sim_driver.sh and confirms trace output.” |

*No other High-severity blockers verified.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `layout.md` misleads about stale overrides; tests require filter-and-converge (ChatGPT High) | **Agree** | `layout.md:28` “or the run ends `stale_override`”; `test_load_pulse`/`test_shadow_drop` call `assert_converged()`; broken `filter_w2` passthrough at `q3_v9/src/w2.rs:18-20`; 5/5 Claude failures per export lines 49-54 |
| 2 | `test_delayed_commit` tautological / weak digest checks (ChatGPT High; test-quality export Major) | **Partially agree** | `test_outputs.py:112-115`: line 113 redundant after `assert_converged`; line 115 `len(set(digests)) >= 1` is trivial. **However** `assert_converged` on `delayed_commit` still requires `flush_t8` fix (`run_loop.rs:221-222` sets `delayed_skew` when commit epoch wrong). Medium coverage gap, not Revise driver alone. |
| 3 | No fixture-integrity checks despite instruction ban (ChatGPT Medium) | **Partially agree** | `instruction.md:3` bans fixture edits; no hash assertions in `test_outputs.py`. Cheat path exists but requires multi-file fixture edits; audit head + dynamic regen partially mitigate. Single Medium—note, not blocker. |
| 4 | Unpinned Rust deps in Cargo.toml (export warning; ChatGPT Low) | **Disagree as blocker** | `Cargo.lock` present; Dockerfile builds with `cargo build --locked`; Low optional `=` prefix only |
| 5 | Non-canonical Docker base (Harbor export Critical) | **Disagree** | `Dockerfile:1` digest `0d39fcc…` matches canonical `ubuntu:24.04` in `docs/guidelines/dockerfxile.md:23-24`; validate emits no `check_sanctioned_base_images` warning |
| 6 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `task.toml:12` `number_of_milestones = 0`; export rubric lines 414-424 are flat `Agent …, ±N` with no `# Rubric 2+` headers—correct per `docs/guidelines/rubrics.md:64` |
| 7 | Task too easy / #54 fail (automated review) | **Disagree** | Export: Claude 0/5 (0%), GPT 5/5 (100%); worst-model 0% ≤20% hard tier; #54 passes |
| 8 | Pip unpinned / #14 fail (automated review) | **Disagree** | `Dockerfile:25-27` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; false positive from multiline `pip install` |
| 9 | Missing test docstrings / #31 fail (automated review) | **Disagree** | All seven `test_*` functions have docstrings (`test_outputs.py:64-110`); only module-level docstring absent (validate warning only) |
| 10 | Instruction sufficiency FAIL—all Claude agents misread spec (export LLMaJ) | **Agree** | Root cause is `layout.md:28` contradiction, not missing instruction paths |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~170 words, 2 paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering incident narrative, not spec template | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Single fenced command block only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No file-level patch walkthrough | `instruction.md` |
| 5 | CHECK | No solving hints | Points to layout.md for schema, not bug locations | `instruction.md:11` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | UNCHECK | Well specified | Stale-override handling ambiguous/contradictory vs tests | `layout.md:28`, `test_outputs.py:73-93` |
| 8 | CHECK | Interesting | Realistic Rust/C FFI split-brain debugging | task content |
| 9 | CHECK | Unique | Prison failover theme; multi-crate workspace | task content |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/tests/test.sh`, etc. | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No “prison-cell-lock-arbitration” string | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch | No curl/wget in env code | `environment/` |
| 14 | CHECK | Pip pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `Dockerfile:25-27` |
| 15 | CHECK | FROM digest-pinned | `@sha256:0d39fcc…` | `Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only env subdirs | `Dockerfile:29-39` |
| 17 | CHECK | No ground truth in env | Audit head is normative spec constant in layout guide | `layout.md:29` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose mount conflicts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:24-27`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally; platform 3/3 | export lines 25-26 |
| 22 | CHECK | Oracle no internet | patch + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Multi-file source patch, not static JSON | `solution/patch.diff`, `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir, write 0, pytest, write 0/1 | `tests/test.sh:6-19` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:16-19` |
| 27 | UNCHECK | Tests aligned with instructions | layout.md stale_override vs converged tests | blocker 1 |
| 28 | UNCHECK | Tests check correctness | `test_delayed_commit` digest settling barely asserted | `test_outputs.py:109-115` |
| 29 | CHECK | Behavior not implementation | Regenerates trace via simulator | `test_outputs.py:15-22` |
| 30 | CHECK | No brittle string matching | Outcome/audit constants are spec-defined | `test_outputs.py:9-12` |
| 31 | CHECK | Informative test docstrings | All seven tests documented | `test_outputs.py:64-110` |
| 32 | CHECK | ≥3 negative rubric criteria | -5, -3, -2 | export lines 422-424 |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines valid | export lines 414-424 |
| 34 | CHECK | Agent …, ±N format | 10 Agent lines | export lines 414-424 |
| 35 | CHECK | Rubric detailed/precise | Per-crate patch criteria | export lines 414-424 |
| 36 | CHECK | Positive phrasing | Bad behaviors as actions with negative scores | export lines 422-424 |
| 37 | UNCHECK | Rubric no /tests/ reference | References `/app/tests/test.sh` | export line 421 |
| 38 | CHECK | Rubric no metadata/instruction refs | None | export lines 414-424 |
| 39 | CHECK | Rubric no oracle/NOP | None | export lines 414-424 |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust+c, system-administration, tool_specific | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches rates | hard; worst-model Claude 0% | export lines 16-22 |
| 46 | UNCHECK | Milestone steps/ layout | N/A — regular task | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone-scoped tests | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile` |
| 51 | CHECK | Solution not in environment | solution/ outside image | `Dockerfile` |
| 52 | UNCHECK | Agent cannot trivially modify inputs | Fixtures writable; no integrity hash test | `instruction.md:3`, `test_outputs.py` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% (Claude), not >80% | export lines 20-22 |
| 55 | UNCHECK | Not unfair | layout.md systematically misled all Claude agents | export lines 49-87 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 29, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 53, 54 |
| **UNCHECK** | 7, 21, 27, 28, 37, 46, 47, 48, 49, 52, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Coherent lock ownership (single epoch after promotion) | `test_epoch_convergence` | covered | `test_outputs.py:64-70`, `layout.md:25` |
| Reject stale emergency overrides | `test_load_pulse`, `test_shadow_drop` | **gap** | Tests require converge + no stale replay; `layout.md:28` implies `stale_override` outcome |
| Full corridor isolation | `test_lane_span`, `test_divergent_recovery` | covered | `test_outputs.py:80-100`, `layout.md:27` |
| Audit chain continuity | `test_trace_continuity` | covered | `test_outputs.py:103-106`, `layout.md:29` |
| ≥5 converged runs | `test_trace_continuity` | covered | `test_outputs.py:106` |
| Actuator digest settling (2 ticks) | `test_delayed_commit` | partial | Convergence catches `delayed_skew`; digest format/settling weakly checked `test_outputs.py:115` |
| Do not edit fixtures | — | untested | `instruction.md:3`; no fixture hash test |
| Regenerate trace via simulator | all tests (fixture) | covered | `test_outputs.py:15-22` |
| Override generation monotonicity | `test_epoch_convergence`, `test_load_pulse` | covered | `test_outputs.py:50-53,69,77` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blocker 1, spec alignment |
| `environment/docs/layout.md` | Blocker 1, #27, #55, adjudication #1 |
| `tests/test_outputs.py` | Blocker 1, #27, #28, #31, spec alignment |
| `environment/q3_v9/src/w2.rs` | Blocker 1, adjudication #1 |
| `environment/fac_b2/src/run_loop.rs` | Blocker 1, scenario journals, outcome logic |
| `solution/patch.diff` | #23, adjudication #1 |
| `environment/Dockerfile` | #14, #15, #20, adjudication #5 |
| `task.toml` | #44, #45, #46-49 N/A |
| `entire-report.txt` | Blocker 2, #37, section 7 agent stats |
| `docs/guidelines/dockerfxile.md` | Adjudication #5 canonical base |
| `docs/guidelines/rubrics.md` | Adjudication #6 rubric format |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: prison-cell-lock-arbitration/ ===
Summary: 0 error(s), 9 warning(s), 2 info
Task type detected: regular
```

Warnings: multiline pip false-positive, missing module-level test docstring, non-milestone info.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | All runs pass |
| terminus-claude-opus-4-8 | 0% (0/5) | All fail on load_pulse + shadow_drop |
| oracle | 100% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (Claude) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test (from export): `test_load_pulse` 5/10, `test_shadow_drop` 5/10—both split exactly on stale-filter fix.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular Rust/C task; matches export |
| 1 Instruction | ☑ | Stale-override ambiguity in layout.md |
| 2 Environment | ☑ | Canonical ubuntu digest; tmux+asciinema; allow_internet=false |
| 3 Oracle | ☐ | Not executed locally; static review of patch.diff passes |
| 4 Verifiers | ☑ | Dynamic regen; delayed_commit weak; layout-test gap |
| 5 Metadata | ☑ | hard, system-administration, number_of_milestones=0 |
| 6 Rubric | ☑ | Flat format OK; /tests/ reference fails #37 |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency fail confirmed; root cause layout.md |
| 8 Novelty & fairness | ☑ | Five-bug coordination; unfair until layout fixed |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust/C failover debugging task—the multi-crate workspace, dynamic trace regeneration, and scenario invariants are well thought out, and the difficulty calibration looks right (GPT passes, Claude struggles). Two things before acceptance: please reword the baseline-generation bullet in `layout.md` so it’s clear stale emergency overrides are **filtered out before replay** and that `load_pulse`/`shadow_drop` should still end `converged`—right now that section reads like `stale_override` is the intended outcome, which is what sank every Claude run. Also drop the `/app/tests/test.sh` reference from the platform rubric (use the instruction verification command or `run_sim_driver.sh` instead). Optional follow-ups: strengthen `test_delayed_commit` digest settling checks and add fixture hash guards.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
| Oracle Solution Issues | no | — |
| Exposing Hints/Answers | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review prison-cell-lock-arbitration/ --report entire-report.txt`._
