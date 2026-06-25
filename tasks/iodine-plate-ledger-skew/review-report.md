# Terminus Review Report: `iodine-plate-ledger-skew`

**Generated:** 2026-06-19 (manual re-audit)  
**Disposition:** Revise  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/iodine-plate-ledger-skew`

---

## 1. Executive summary

- **Recommendation:** Revise
- **Confidence:** High (artifact review); Medium (oracle/agent runs not executed locally)
- **Automated validation:** FAIL — 2 errors, 22 warnings (several warnings are false positives on manual re-check)
- **External report match:** **MISMATCHED** — `entire-report.txt` describes a Java `cronq` cron-parser task, not this Rust PLT5 plate-ledger milestone task
- **ChatGPT findings:** **Invalid for this task** — reviewed the wrong submission entirely
- **Checkboxes to CHECK:** 43 items → `1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 55`
- **Checkboxes to UNCHECK:** 12 items → `4, 21, 32, 33, 34, 35, 36, 37, 38, 39, 45, 54`

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

---

## 2. Main blockers (detailed)

### Blocker 1: `task.toml` milestone layout — top-level `[agent]` / `[verifier]` forbidden

- **Severity:** High
- **Section:** TASK METADATA / MILESTONE TASKS
- **Checkbox:** leave **#43 UNCHECKED** until fixed (fields present but structure invalid); milestone compliance tied to **#46**
- **What failed:** Milestone tasks must use per-step `[steps.agent]` / `[steps.verifier]` only. Top-level `[agent]` and `[verifier]` blocks (lines 16–20) violate `docs/guidelines/milestones.md` and fail `./scripts/terminus validate`.
- **Proof files:** `task.toml:16-20`, `task.toml:30-55`, validation output below
- **Required fix:** Delete top-level `[verifier]` and `[agent]` sections; keep only the three `[[steps]]` blocks with their nested timeout tables.

### Blocker 2 (non-blocking alone): External agent stats unusable for difficulty checkboxes

- **Severity:** Medium (blocks portal #45 / #54 only)
- **Section:** TASK METADATA / TASK DIFFICULTY
- **Checkboxes:** leave **#45** and **#54 UNCHECKED**
- **What failed:** `entire-report.txt` agent performance (`terminus-gpt5-5: 100%`, cron unit tests like `test_daily_midnight_skips_the_start_minute`) belongs to a different Java task. Cannot adjudicate declared `difficulty = "hard"` for this Rust milestone task from that report.
- **Proof files:** `entire-report.txt:19-44` (cron test names), `entire-report.txt:47` (`cronq` Java task summary); contrast `iodine-plate-ledger-skew/steps/milestone_1/instruction.md:1` (PLT5 plate ledger)
- **Required fix:** Run agent evaluation on **this** task folder and attach a matching report before checking #45/#54 in the portal.

### Note (Low — optional polish, not sole blocker): M1 prescriptive rebuild/run line

- **Severity:** Low / borderline Medium
- **Checkbox:** **#4 UNCHECKED** (strict reading)
- **What failed:** `steps/milestone_1/instruction.md:1` contains `Rebuild with ... then run ...`, matching step-hint regex `then,?\s+(run|...)`.
- **Proof files:** `steps/milestone_1/instruction.md:1`, `docs/guidelines/prompt-styling.md:26-27`
- **Suggested fix:** Point to `/app/docs/plate_report_contract.md` for driver invocation instead of inline build-then-run choreography.

---

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise | Each milestone instruction is ~156–165 words, 3 prose paragraphs; automated script wrongly concatenated all three (485 words / 9 blocks) | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md`, `steps/milestone_3/instruction.md` |
| 2 | Natural prompt tone | Engineer debugging brief; no “You are an expert…” synthetic framing | all milestone `instruction.md` |
| 3 | No excessive markdown | Plain prose; no `##` headers or tables in instructions | all milestone `instruction.md` |
| 5 | No hints / solving strategies | States broken behaviors and contracts; does not name source files or patch locations | `steps/milestone_*/instruction.md` |
| 6 | No design-doc I/O tables | No mapping tables in instructions (tables in `/app/docs/` are contract docs, not instruction loophole) | milestone instructions vs `environment/docs/` |
| 7 | Well specified | Clear outputs, paths, field semantics, scenario IDs per milestone | `steps/milestone_*/instruction.md`, `environment/docs/plate_report_contract.md` |
| 8 | Interesting | Realistic multi-stage Rust binary-parsing / pipeline debugging | task content |
| 9 | Unique | PLT5 ledger + trim profiles + cache stamps is distinct from cron/Java tasks in external report | task identity |
| 10 | Absolute paths only | All paths are `/app/...` | milestone instructions |
| 11 | Task name not in instruction | `iodine-plate-ledger-skew` absent from prompts | milestone instructions |
| 12 | No canary string | None detected | milestone instructions |
| 13 | No runtime web fetch | Environment ships local fixtures/docs; `allow_internet = false` | `task.toml:23`, `environment/` |
| 14 | Pinned pip deps | `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` via env-expanded `"${CHECK_RUNNER}==8.4.1"` lines (validator false positive on line wrap) | `environment/Dockerfile:19-21` |
| 15 | Digest-pinned FROM | `rust:1.85-slim@sha256:9f841b...` | `environment/Dockerfile:1` |
| 16 | Environment self-contained | COPY limited to `environment/` subtree | `environment/Dockerfile:38-48` |
| 17 | No ground-truth answers in env | Docs define formats/contracts; buggy code does not label fixes | `environment/m3l/src/scan.rs:42-43` (BE parse bug), `environment/m3l/src/mix.rs:5-7` (sum-not-CRC bug), `environment/r8k/src/lane.rs:5-8` (wrong chain rule) |
| 18 | No dangerous Docker ops | No privileged / docker.sock | `environment/Dockerfile` |
| 19 | Compose mount safety | No `docker-compose.yaml` | task root |
| 20 | Verifier deps in image | pytest pre-installed; `test.sh` does not install packages | `environment/Dockerfile:19-21`, `steps/milestone_1/tests/test.sh:14-15` |
| 22 | Oracle no runtime network | `solveN.sh` patches local Rust sources + `cargo build --release` only | `steps/milestone_1/solution/solve1.sh`, `steps/milestone_3/solution/solve3.sh` |
| 23 | Oracle derives via implementation | Oracle rewrites `scan.rs`, `mix.rs`, `trim.rs`, `gate.rs`, `flow.rs`, `lane.rs`, `slot.rs`, `emit.rs` — not echo of JSON answers | `steps/milestone_*/solution/solve*.sh` |
| 24 | reward.txt canonical block | All milestone `test.sh` write `/logs/verifier/reward.txt` on pass/fail | `steps/milestone_1/tests/test.sh:17-23` |
| 25 | Same verifier logic oracle/agent | No `/oracle` branching | all milestone `test.sh` |
| 26 | Binary rewards | 0 or 1 only | all milestone `test.sh` |
| 27 | Tests aligned with instructions | Independent recompute in `plate_common.py` mirrors instruction rules (digest before trim, lane order, cache stamp formula) | `steps/milestone_1/tests/plate_common.py:147-224`, milestone instructions |
| 28 | Tests check correctness | Full dict equality vs independent byte-level recompute, not format-only | `steps/milestone_1/tests/test_m1.py:18-22` |
| 29 | Behavior not implementation grep | Tests invoke rebuilt binary; no source grepping | `plate_common.py:249-267` |
| 30 | Not brittle string matching | JSON structural equality on computed reports is appropriate | test modules |
| 31 | Informative test docstrings | Every `test_*` method has a docstring; validator missed `-> None:` annotations | `steps/milestone_1/tests/test_m1.py:17-63` (all methods documented) |
| 40 | Required files present | Milestone layout: `environment/Dockerfile`, `steps/milestone_N/{instruction,tests,solution}` | task tree |
| 41 | Clean parent directory | No stray `jobs/`, root README, or dev notes | task root |
| 42 | author fields present | `author_name`, `author_email` in `task.toml` | `task.toml:4-5` |
| 43 | Required metadata fields | Category, difficulty, tags, languages, milestones present (structure error is separate blocker) | `task.toml:3-14` |
| 44 | Tags/languages/category match | `debugging`, `rust`, `tool_specific`, ledger/plate tags fit content | `task.toml:7-12` |
| 46 | Milestone steps layout | `steps/milestone_{1,2,3}/` with per-milestone artifacts | task tree |
| 47 | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` + wrappers | `steps/milestone_*/solution/` |
| 48 | test_mN.py per milestone | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | Milestone-scoped tests | M1 parsing/digest; M2 trim/lane; M3 cache/trace/probes only | test modules |
| 50 | Tests not in image | Dockerfile copies only `environment/` members | `environment/Dockerfile:38-48` |
| 51 | Solution not accessible in env | No `/solution` or test fixtures in image; closed probes installed at test time | `steps/milestone_3/tests/plate_common.py:291-300`, `steps/milestone_3/tests/fixtures/` |
| 52 | Input data not trivially hackable | Verifier rebuilds from source each run; decoy JSON test proves driver overwrite | `test_m1.py:51-63`, `plate_common.py:237-247` |
| 53 | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 55 | Not unfair / too hard | Rules documented in `/app/docs/`; bugs are discoverable via contract + scenarios; probe fixtures closed but rules are specified | `environment/docs/`, milestone instructions |

### UNCHECK these (fail, unverified, or N/A)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 4 | fail | No step-by-step developer steps | M1: `Rebuild with ... then run ...` is prescriptive choreography | `steps/milestone_1/instruction.md:1` |
| 21 | unverified | Oracle passes consistently | Oracle not executed in this review environment | — |
| 32 | na | Rubrics ≥3 negatives | No `rubric.txt` in repo (platform UI rubric expected) | task root |
| 33 | na | Rubric score set | No rubric file | task root |
| 34 | na | Rubric format | No rubric file | task root |
| 35 | na | Rubric detailed | No rubric file | task root |
| 36 | na | Rubric positive language | No rubric file | task root |
| 37 | na | Rubric no /tests/ refs | No rubric file | task root |
| 38 | na | Rubric no metadata refs | No rubric file | task root |
| 39 | na | Rubric no oracle/NOP refs | No rubric file | task root |
| 45 | unverified | Difficulty matches agent pass rates | Supplied report is for wrong task | `entire-report.txt` vs task folder |
| 54 | unverified | Not too easy (>80%) | Same — no valid agent stats for this task | `entire-report.txt` |

### Quick copy-paste

**CHECK:** 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 55

**UNCHECK:** 4, 21, 32, 33, 34, 35, 36, 37, 38, 39, 45, 54

---

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `task.toml` | #43 (structure blocker), #44, #45 |
| `entire-report.txt` | external mismatch (#45, #54 invalid) |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/docs/plate_report_contract.md` | #7, #17, #27 |
| `environment/docs/plt5_plate_format.md` | #7, #27 |
| `environment/m3l/src/{scan.rs,mix.rs,stage.rs,pool.rs,flow.rs}` | #17 (intentional bugs) |
| `environment/r8k/src/lane.rs` | #17 (intentional bugs) |
| `steps/milestone_1/instruction.md` | #1, #4, #10 |
| `steps/milestone_2/instruction.md` | #1, #27 |
| `steps/milestone_3/instruction.md` | #1, #27 |
| `steps/milestone_1/tests/test_m1.py` | #27, #28, #31 |
| `steps/milestone_2/tests/test_m2.py` | #27, #28, #31, #49 |
| `steps/milestone_3/tests/test_m3.py` | #27, #28, #31, #49, #51 |
| `steps/milestone_*/tests/plate_common.py` | #27, #28, #51, #52 |
| `steps/milestone_*/tests/test.sh` | #24, #25, #26 |
| `steps/milestone_*/solution/solve*.sh` | #22, #23, #47 |

---

## 5. Validation output (re-audit)

```
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
WARNING: pinned_dependencies [environment/Dockerfile]: Pin pip packages with == versions (FALSE POSITIVE — see #14)
WARNING: informative_test_docstrings [test_m*.py]: 21 tests missing docstrings (FALSE POSITIVE — type-hint defs; all methods have docstrings)
```

Manual re-audit overrides the two warning classes above.

---

## 6. Agent performance (from report)

**Report invalid for this task.** `entire-report.txt` references:

- Java `cronq` CLI, `PROTOCOL.md`, `Matcher.java`, `NextCalculator.java`
- Unit tests: `test_daily_midnight_skips_the_start_minute`, `test_hour_jump_resets_minute_to_field_floor_offgrid`
- Agent rates: GPT-5.5 100%, Claude Opus 4.8 0%

None of these apply to `iodine-plate-ledger-skew` (Rust `iodine-plate` binary, PLT5 fixtures, milestone pytest files). **Do not use** that report for difficulty adjudication.

---

## External findings adjudication

### Claim: Accept — strong Java cron debugging task with aligned verifiers
- **Source:** ChatGPT RReviewer Assessment (user message)
- **Verdict:** **Disagree**
- **Evidence:** Task folder is Rust milestone PLT5 ledger (`environment/m3l/`, `steps/milestone_*/`); external report lines 47–124 describe Java cronq
- **Severity:** N/A (wrong task)
- **Action:** Discard ChatGPT disposition for this folder

### Claim: Difficulty HARD supported by evaluation spread (GPT 100%, Claude 0%)
- **Source:** `entire-report.txt:1-7`
- **Verdict:** **Disagree** (for this task)
- **Evidence:** Report test names are cron-specific (`entire-report.txt:26-44`); no iodine-plate tests listed
- **Severity:** Medium for portal #45/#54
- **Action:** Re-run agent eval on correct task path

### Claim: Dockerfile digest-pinned; tests/solution not in image
- **Source:** `entire-report.txt:101-106` (cron task)
- **Verdict:** **Agree** (for iodine-plate-ledger-skew on independent inspection)
- **Evidence:** `environment/Dockerfile:1`, `:38-48` — no COPY of tests/solution
- **Severity:** None
- **Action:** none

### Claim: All quality checks pass (behavior_in_task_description, anti_cheating, etc.)
- **Source:** `entire-report.txt:97-107`
- **Verdict:** **Partially agree** for this task on manual audit
- **Evidence:** Milestone instructions + docs cover tested behaviors; closed probe scenarios (`tab_probe`, `tab_probe_v`) in `steps/milestone_3/tests/fixtures/` resist shortcutting; independent recompute in verifier
- **Severity:** None
- **Action:** none (after task.toml fix)

---

## Spec ↔ test alignment matrix

| Requirement (instruction) | Test(s) | Status |
|---------------------------|---------|--------|
| M1: LE PLT5 parse + CRC32 digest + seq sort | `test_m1.py` tab_x/tab_v/tab_t recompute | covered |
| M1: JSON schema fields / digest_chain literals | `expected_for()` + equality asserts | covered |
| M1: Hand-written JSON insufficient | `test_hand_written_output_is_replaced_by_driver` | covered |
| M2: Digest before trim; recount records_applied | `plate_common.expected_for` pipeline + tab_s/tab_w/tab_trim | covered |
| M2: plate_lane before profile lane_mask; trim_sequence | `test_plate_lane_filter_before_trim`, `test_profile_lane_mask_filters_before_trim`, `test_dual_trim_profile_scenario_matches_recompute` | covered |
| M2: modulo_prune manifest + profile | `test_modulo_prune_profile_scenario_matches_recompute` | covered |
| M3: trace sidecar format + pre-trim rows | `test_trace_sidecar_matches_report`, `expected_trace()` | covered |
| M3: cache head/gen stamp rules | cache tests in `test_m3.py:31-70` | covered |
| M3: closed grading probes | `test_verification_scenario_matches_recompute`, `test_verification_profile_scenario_matches_recompute` | covered |

No phantom tests or untested High-severity instruction requirements found.

---

## 7. Audit log

- [x] Phase 0 — Confirmed task identity: Rust milestone `iodine-plate-ledger-skew`; external report mismatched (Java cronq)
- [x] Phase 1 — Read all three milestone `instruction.md` files; checked paths, tone, length per file
- [x] Phase 2 — Read `environment/Dockerfile`, docs, buggy Rust sources; verified no tests/solution COPY
- [x] Phase 3 — Read all `solve1.sh` / `solve2.sh` / `solve3.sh`; oracle patches source deterministically
- [x] Phase 4 — Read all milestone `test.sh`, `test_m*.py`, `plate_common.py`; verified reward block, recompute logic, probe install
- [x] Phase 5 — Read `task.toml`; found top-level `[agent]`/`[verifier]` validation errors
- [x] Phase 6 — No rubric file in repo (#32–39 N/A)
- [x] Phase 7 — Adjudicated `entire-report.txt` and ChatGPT claims against artifacts
- [x] Phase 8 — Anti-cheating: closed probes, rebuild-from-source verifier, decoy overwrite test
- [ ] Oracle Harbor run — **not executed** (#21 unchecked)
- [x] Manual spec↔test alignment (#27, #28) — confirmed
- [x] Subjective fairness (#55) — task is hard but fair given docs

---

## 8. Reviewer note (copy-paste to portal)

Needs revision. The milestone task is well constructed — digest-pinned Rust environment, strong independent recompute verifiers, closed probe scenarios, and clear per-milestone contracts in `/app/docs/` — but `task.toml` still has forbidden top-level `[agent]` and `[verifier]` blocks (validation error; remove and keep only `[steps.*]` timeouts). The supplied `entire-report.txt` and ChatGPT accept note target a different Java cron task and must not be used for difficulty checkboxes until agent stats are rerun on this folder. After the metadata fix, re-run oracle/agent eval and optionally soften the M1 “rebuild then run” line to reference the contract doc instead of inline steps.

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus review iodine-plate-ledger-skew --report entire-report.txt`._
