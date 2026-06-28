# Terminus Review Report: cmake-ninja-depfile-stale-header-repair

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (2 errors, 37 warnings — most warnings are false positives) |
| **Oracle** | not executed locally (submission export: 100% 3/3) |
| **CHECK count** | 54 |
| **UNCHECK count** | 1 |

**Error categories (internal):** Metadata Issues, Milestones

**Decision (concise):** Strong CMake/Ninja milestone task with excellent spec↔test alignment, anti-cheat design, and correctly formatted 3-block platform rubric. One real blocker: `task.toml` retains forbidden top-level `[agent]` / `[verifier]` sections alongside per-milestone timeouts. ChatGPT Accept missed this; automated #14/#31 failures are false positives on manual re-audit.

**Insights (concise):**

- This is a **3-milestone task** (`number_of_milestones = 3`); platform rubric `# Rubric 1/2/3` format is **correct** — not a non-milestone task misusing milestone rubric headers.
- Pip deps are pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); validate warning on #14 is a false positive.
- All 36 `test_*` methods have docstrings; validate regex misses `-> None:` return annotations.
- `reference_audit.py:28` uses `.strip()` while schema says "verbatim" — Low polish only; practically harmless.
- Hidden fixture C (`compile_fence.hpp`) is fair: M1 tests core closure includes it; M2 requires `-MD/-MP`; M3 audit only reports actual Ninja rebuilds.
- Agent rates: Claude 20%, GPT-5.5 60% — defensible `hard` per best-model rule; worst-model 60% ≤80%.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Metadata Issues, Milestones | #43 | Milestone `task.toml` must not have top-level `[agent]` / `[verifier]` — only `[steps.agent]` / `[steps.verifier]` per step | `task.toml:16-20` duplicates per-step timeouts at `task.toml:33-55`; `./scripts/terminus validate` ERROR; `docs/task-requirements.md:107`, `docs/guidelines/milestones.md:99` | Delete lines 16–20 (`[agent]` and `[verifier]` blocks). Per-milestone timeouts already defined under each `[[steps]]`. |

*No other High/Medium blockers found on manual re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept — no High/Medium issues | Partially agree | Agree on spec/test/env quality; **disagree** on Accept — `task.toml` milestone schema violation is a High metadata blocker (`task.toml:16-20`) |
| 2 | ChatGPT: Optional polish — M3 schema says verbatim field 4, reference strips whitespace | Agree (Low only) | `environment/docs/audit_report_schema.md:39` says "Copy field 4 verbatim"; `steps/milestone_3/tests/reference_audit.py:28` uses `parts[3].strip()` |
| 3 | ChatGPT: Optional polish — M3 hint for `compile_fence.hpp` edge | Partially agree (Low only) | `hidden_touch_order_c.json:6` touches `compile_fence.hpp`; not named in M3 instruction, but M1 `test_core_closure_includes_compile_fence` (`test_m1.py:122-125`) and M2 `-MD/-MP` requirement cover the dependency chain fairly |
| 4 | entire-report LLMaJ: behavior_in_task_description PASS | Agree | M1/M2/M3 instructions match contract docs and test assertions |
| 5 | entire-report LLMaJ: behavior_in_tests PASS | Agree | 14+11+11 tests cover stated requirements per milestone |
| 6 | entire-report LLMaJ: anti_cheating PASS | Agree | Hidden fixtures SHA256-pinned (`test_m3.py:27-35`); `.dockerignore` excludes `tests/`, `solution/`, `steps/` |
| 7 | entire-report: Instruction sufficiency PASS | Agree | Agent failures on `test_hidden_fixture_c_fence_touch_matches_log` are implementation gaps (M2 dep wiring), not unstated M3 requirements |
| 8 | Harbor review: non-canonical GCC base image WARNING | Agree (not blocker) | `environment/Dockerfile:1` digest-pinned `gcc:13-bookworm`; justified for C++/CMake toolchain |
| 9 | Harbor review: env stub `build_audit.py` shares solution name | Disagree (not an issue) | `environment/scripts/build_audit.py` exits with "not implemented" — intentional placeholder, no answer leakage |
| 10 | Test quality review: reference `.strip()` oracle drift | Agree (Low) | Same as claim #2 |
| 11 | Auto-review: #14 unpinned pip | Disagree | `environment/Dockerfile:17-18` pins `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` |
| 12 | Auto-review: #31 missing docstrings | Disagree | All `test_*` in `test_m1.py`, `test_m2.py`, `test_m3.py` have docstrings; validator regex `def {fn}\([^)]*\):` fails on `-> None:` annotations (`scripts/validate_task.py:558`) |
| 13 | User: non-milestone task in milestone rubric format | Disagree (N/A) | `task.toml:10` `number_of_milestones = 3`; rubric blocks `# Rubric 1/2/3` per `docs/guidelines/rubrics.md:54-64` are **correct** for this task type |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone instruction ≤3 short paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering problem statements, not LLM spec tone | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no heavy markdown | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes; M1 cmake line is required build outcome not a walkthrough | `steps/milestone_1/instruction.md:3` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Requirements + contract doc refs only | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables in instructions | — |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Paths, targets, schemas named | `steps/milestone_*/instruction.md`, `environment/docs/*.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic CMake/Ninja incremental-build repair | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct depfile-normalization + audit CLI domain | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instructions | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | apt only; no runtime fetch | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Both pip packages use `==` | `environment/Dockerfile:17-18` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY scoped to env | `environment/Dockerfile:24-31` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stub audit script only; broken cmake by design | `environment/scripts/build_audit.py` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged mode | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv in image; test.sh calls pytest only | `environment/Dockerfile:15-18`, `steps/milestone_*/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Submission export oracle 100% (3/3); solve scripts derive fixes | `entire-report.txt:26`, `steps/milestone_*/solution/solveN.sh` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve scripts edit local files only | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rewrites cmake modules and implements audit CLI | `steps/milestone_1/solution/solve1.sh`, `steps/milestone_3/solution/solve3.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block + EXIT trap | `steps/milestone_1/tests/test.sh:3-22` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Writes 0 or 1 only | `steps/milestone_*/tests/test.sh` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Every assertion traces to instruction or referenced contract doc | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Reference closures, mtime rebuilds, ninja log oracle | `reference_depfix.py`, `reference_audit.py`, `test_m2.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Build/ninja/JSON behavior checks | `test_m1.py`, `test_m3.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | `depfix_app=31`, `absolute` stderr specified in docs | `rebuild_expectations.md:17`, `audit_report_schema.md:7` |
| 31 | CHECK | Tests have informative names or docstrings | All 36 tests have docstrings + descriptive names | `test_m1.py:44-125`, `test_m2.py:31+`, `test_m3.py:58+` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 9 negatives across 3 blocks | `entire-report.txt:485-511` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | rubric-validate pass | `entire-report.txt:477-511` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 30 Agent lines, 3 `# Rubric N` headers | `entire-report.txt:477-511` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific cmake/ninja/audit behaviors | `entire-report.txt:477-511` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Negatives use "Agent hardcodes/leaves/breaks…", -N | `entire-report.txt:485-511` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ in rubric lines | `entire-report.txt:477-511` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:477-511` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:477-511` |
| 40 | CHECK | All required files present | `environment/`, `steps/milestone_N/{instruction,tests,solution}`, `task.toml` | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | UNCHECK | All other required metadata fields present | Milestone schema violation: forbidden top-level `[agent]`/`[verifier]` | `task.toml:16-20`, `docs/guidelines/milestones.md:99` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | cpp/cmake, build-and-dependency-management, tool_specific | `task.toml:5-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 20%, worst 60% | `entire-report.txt:16-22`, `task.toml:8` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `steps/milestone_{1,2,3}/` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1.sh, solve2.sh, solve3.sh | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | `TestMilestone1/2/3` classes test only their milestone | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:14` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/tests/steps dockerignored | `environment/.dockerignore:13-15` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Pinned include-tree + hidden fixture SHA256 | `test_m1.py:46-48`, `test_m3.py:27-35` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% | `entire-report.txt:20-22` |
| 55 | CHECK | Task is not too hard or unfair | Requirements in instructions + contract docs; hidden fixtures test fair cross-milestone behavior | §5, `hidden_touch_order_c.json` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 43 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: depfiles in `/app/build/deps/<target>.dep` | `test_depfiles_live_under_build_deps` | covered | `test_m1.py:58-62` |
| M1: per-target include closure | `test_*_depfile_matches_include_closure` (×4) | covered | `test_m1.py:91-115` |
| M1: sorted lines + footer digest | `test_depfile_lines_sorted_lexicographically`, `test_depfile_footer_digest_matches_data` | covered | `test_m1.py:78-89` |
| M1: no stale overlay/publish | `test_stale_overlay_*`, `test_build_ninja_excludes_stale_publish_steps` | covered | `test_m1.py:64-76` |
| M1: core closure includes `compile_fence.hpp` | `test_core_closure_includes_compile_fence` | covered | `test_m1.py:122-125` |
| M2: header sync wired to util/core/app | `test_*_depends_on_header_sync` | covered | `test_m2.py` |
| M2: stamp tracks config + version | `test_stamp_rule_tracks_config_and_version` | covered | `test_m2.py` |
| M2: config/legacy touch rebuilds util; version touch rebuilds core | `test_config_touch_*`, `test_legacy_alias_*`, `test_version_touch_*` | covered | `test_m2.py:31-60` |
| M2: `-MD`/`-MP` on util and app | `test_util_and_app_compile_with_dependency_flags` | covered | `test_m2.py` |
| M2: demo prints `depfix_app=31` | `test_app_binary_still_runs` | covered | `test_m2.py` |
| M3: absolute `--fixture`/`--output` only | `test_relative_fixture_path_rejected`, `test_relative_output_path_rejected` | covered | `test_m3.py:73-101` |
| M3: audit JSON schema + ninja log replay | `test_public_fixture_audit_matches_ninja_log`, hidden fixture tests | covered | `test_m3.py:141-237` |
| M3: hidden fence touch rebuilds core (via M2 wiring) | `test_hidden_fixture_c_fence_touch_matches_log` | covered | `test_m3.py:217-237`, `hidden_touch_order_c.json:6` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker #1, #43, #44, #45, #46 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/audit_report_schema.md` | Claim #2, #27 |
| `environment/docs/ninja_depfile_format.md` | #27, M1 alignment |
| `environment/docs/rebuild_expectations.md` | M2 alignment |
| `steps/milestone_1/instruction.md` | #1-12, #27 |
| `steps/milestone_2/instruction.md` | #27 |
| `steps/milestone_3/instruction.md` | #27 |
| `steps/milestone_1/tests/test_m1.py` | #27, #28, #31 |
| `steps/milestone_2/tests/test_m2.py` | #27, #28, #31 |
| `steps/milestone_3/tests/test_m3.py` | #27, #28, #31, #52 |
| `steps/milestone_3/tests/reference_audit.py` | Claim #2, #10 |
| `steps/milestone_1/tests/reference_depfix.py` | #28 |
| `steps/milestone_3/tests/hidden_touch_order_c.json` | Claim #3, #55 |
| `entire-report.txt` | #32-39, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
WARNING: informative_test_docstrings (36) — FALSE POSITIVE: all tests have docstrings; validator regex misses `-> None:` annotations
WARNING: pinned_dependencies — FALSE POSITIVE: pytest packages are == pinned
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 20.0% (1/5) | Supports `hard` tier |
| terminus-gpt5-5 | 60.0% (3/5) | Medium worst-model |
| oracle | 100.0% (3/3) | From submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium (worst) / hard (best) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model ≤20% rule) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone CMake/Ninja C++ task; report matches folder |
| 1 Instruction | ☑ | Concise per-milestone prompts; contract docs authoritative |
| 2 Environment | ☑ | Digest-pinned gcc, tmux/asciinema, verifier venv, no tests/solution in image |
| 3 Oracle | ☑ | Static review + submission 100%; local harbor oracle not run (CLI error) |
| 4 Verifiers | ☑ | Canonical test.sh, behavior tests, docstrings present |
| 5 Metadata | ☐ | **Blocker:** top-level agent/verifier in milestone task.toml |
| 6 Rubric | ☑ | Correct 3-block milestone format; 9 negatives; 16/15/16 positive pts per block |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; M3 fence failures are agent wiring gaps |
| 8 Novelty & fairness | ☑ | No cheating paths; hidden fixtures fair |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid CMake/Ninja milestone work — the depfile closure verifiers, hidden fixture checksums, and Ninja-log audit oracle are all well thought out, and agent pass rates look right for hard difficulty. One small metadata fix before accept: remove the duplicate top-level `[agent]` and `[verifier]` sections from `task.toml` (lines 16–20). Milestone tasks should only use `[steps.agent]` / `[steps.verifier]` under each `[[steps]]` block, which you already have. Optional polish if you want: align the M3 reference parser with the schema's "verbatim" field-4 wording (`.strip()` vs no strip) — practically harmless today.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1 |
| Milestones | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
