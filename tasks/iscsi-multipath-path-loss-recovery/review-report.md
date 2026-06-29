# Terminus Review Report: `iscsi-multipath-path-loss-recovery`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 16 warnings — all false positives on manual audit) |
| **Oracle** | pass (platform: 3/3; local Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Accept. Strong multipath/iSCSI failback debugging task with 16 independent-verifier tests, injected scenarios, rebuild-from-source checks, and clear output validation. Manual audit found **no real blockers**: the Ubuntu 24.04 digest is canonical per policy, `operations.md` documents `flush_bump` highest-`registration_order` semantics, tests all have docstrings, worst-model pass rate is 40% (not >80%), and the platform rubric is correctly formatted as a flat non-milestone list. ChatGPT/Harbor “non-canonical base” and instruction-sufficiency claims are disproven by artifacts.

**Insights (concise):**

- `ubuntu:24.04@sha256:0d39fcc8…` is listed in `docs/guidelines/dockerfxile.md:22-23` and `scripts/validate_task.py` `CANONICAL_BASE_IMAGES` — Harbor “switch to golang base” warning is incorrect.
- `operations.md:39` states *“effective depth follows highest registration order”*; `instruction.md:22` points agents there — LLMaJ instruction-sufficiency FAIL and ChatGPT spec-gap claims are stale.
- Worst-model rate is **40%** (GPT-5.5), not 100%; automated `terminus review` misread Claude’s 100% as worst-model.
- All 16 `test_pf*` functions have one-line docstrings; `validate_task.py` regex misses type-hinted `def` lines — false #31 failures.
- Platform rubric (`entire-report.txt:326-341`) is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct for `number_of_milestones = 0`.
- Optional polish: declared `difficulty = "hard"` vs observed medium tier (40% worst); rubric positive sum is 43 pts (slightly above 10–40 guidance).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT High: non-canonical Ubuntu base; need golang image or stronger exemption | **Disagree** | `environment/Dockerfile:1` digest `0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` matches canonical `ubuntu:24.04` in `docs/guidelines/dockerfxile.md:22-23` and `scripts/validate_task.py:74` |
| 2 | ChatGPT Medium: `flush_bump` / `registration_order` spec gap | **Disagree** | `environment/docs/operations.md:39` — *“effective depth follows highest registration order, not filename sort”*; `instruction.md:22` references operations.md |
| 3 | ChatGPT Low: `difficulty = "hard"` vs platform Medium | **Partially agree** | `task.toml:6` hard; `entire-report.txt:31,37` Medium / 40% worst — informational only per review policy; not a blocker |
| 4 | ChatGPT Low: dense instruction | **Partially agree** | `instruction.md` is terse but complete; reconciliation rules + `operations.md` cover all tested semantics; Low not blocker |
| 5 | ChatGPT Decision: Needs Revision (base image) | **Disagree** | Canonical Ubuntu digest; no Environment blocker |
| 6 | Harbor REVIEW REPORT: non-canonical base image (CRITICAL) | **Disagree** | Same digest proof as claim 1; golang base is optional alternative, not required |
| 7 | Harbor WARNING: `epoch/loader.go` discoverability risk | **Partially agree** | Intentional bug (`environment/epoch/loader.go:49` uses `order < bestOrder`); semantics documented in `operations.md:39`; fair for hard debugging task |
| 8 | Harbor WARNING: instruction brevity | **Partially agree** | Dense but complete; `operations.md` supplements; Low not blocker |
| 9 | LLMaJ: instruction sufficiency FAIL (`flush_bump` selection undocumented) | **Disagree** | `operations.md:39`; `test_pf15_flush_bump_from_flag_registration` docstring at `tests/test_outputs.py:387` |
| 10 | LLMaJ: all other quality checks pass | **Agree** | Verified against artifacts |
| 11 | Test quality review: ACCEPT | **Agree** | Independent Python simulation + rebuild + injected s07 |
| 12 | Agent stats: Claude 100%, GPT 40%, oracle 100% | **Agree** | `entire-report.txt:36-41` |
| 13 | Automated `terminus review`: #31 missing docstrings | **Disagree** | Docstrings at `tests/test_outputs.py:270,276,282,…,402`; validator regex `def {fn}\([^)]*\):` misses type hints |
| 14 | Automated `terminus review`: #54 too easy (100% worst) | **Disagree** | Worst model is GPT-5.5 at 40% (`entire-report.txt:37`); 40% is not >80% |
| 15 | Automated `terminus review`: #36 rubric negative phrasing | **Disagree** | Rubric uses negative **scores** for bad behaviors (`-3`, `-2`); anti-pattern is “does not …, **+1**” — not present |
| 16 | User concern: non-milestone task in milestone rubric format | **Disagree (no issue)** | `entire-report.txt:326-341` — flat `Agent …, ±N` lines, no `# Rubric 1/2/…` milestone blocks; correct per `docs/guidelines/rubrics.md:64` and `submission-export-format.md:63` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Problem + requirements in ~23 lines; bullets carry reconciliation contract | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer incident brief tone | `instruction.md:1-4` |
| 3 | CHECK | No excessive markdown formatting | Plain prose + bullet list; no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States build/run commands as contract, not debug walkthrough | `instruction.md:5-7` |
| 5 | CHECK | No hints or solving strategies | Reconciliation rules are WHAT to satisfy, not which files to patch | `instruction.md:10-20` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Output path, schema, build commands, reconciliation rules clear | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Real multipath/iSCSI failback debugging scenario | — |
| 9 | CHECK | Instruction is unique | Distinct pathfb-sweep pipeline with replay/retain/route/queue/ALUA stages | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY environment only | `environment/Dockerfile:30` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:27` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:0d39fcc8…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | `COPY . /app/environment` only | `environment/Dockerfile:30` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Intentional bugs to fix; no expected JSON output | `environment/epoch/loader.go:49` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv+pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:26-27`, `tests/test.sh:11` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:41` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `go build` + file copies only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Copies corrected Go sources, rebuilds, runs sweep | `solution/solve.sh:19-33` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Writes 0 on start and 0/1 after pytest | `tests/test.sh:3-16` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` | `tests/test.sh:4,14-15` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to instruction rules or `operations.md` | `instruction.md:10-22`, `operations.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Independent `_simulate_row` cross-check per field | `tests/test_outputs.py:78-160,275-278` |
| 29 | CHECK | Tests verify behavior, not implementation | Rebuilds binary, runs sweep, compares output | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Field-by-field simulation vs emitted rows | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 16 tests named `test_pfNN_*` with docstrings | `tests/test_outputs.py:269-414` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 5 negatives (-3×4, -2×1) | `entire-report.txt:338-341` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores valid | `entire-report.txt:326-341` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 16 Agent lines | `entire-report.txt:326-341` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific subsystem trace checks | `entire-report.txt:326-341` |
| 36 | CHECK | Rubric criteria use positive language | Bad behaviors with negative scores; no “does not …, +1” | `entire-report.txt:338-341` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ | No /tests/ refs | `entire-report.txt:326-341` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No task.toml/instruction refs | `entire-report.txt:326-341` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:326-341` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go/bash storage debugging; system-administration | `task.toml:7-10` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 40% = Medium tier; best 100% | `task.toml:6`, `entire-report.txt:31,37` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:14` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:14` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:14` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ in `.dockerignore`; not COPY’d | `environment/.dockerignore:15` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Verifier injects s07, rebuilds from source, simulates expected rows | `tests/test_outputs.py:248-266,299-310` |
| 53 | CHECK | Git repos pinned (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 40% (GPT-5.5) | `entire-report.txt:37` |
| 55 | CHECK | Task is not too hard or unfair | `operations.md` documents all tested semantics including flush_bump | `operations.md:39`, agent analysis |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Six bundled scenarios s01–s06 in output | `test_pf01_six_scenario_envelope` | covered | `instruction.md:10`, `tests/test_outputs.py:269-272` |
| Each row matches stage pipeline simulation | `test_pf02_stage_pipeline_match` | covered | `instruction.md:10-20`, `tests/test_outputs.py:275-278` |
| crash_mid → replay_epoch=2 | `test_pf03_crash_fragment_epoch` | covered | `instruction.md:13`, `operations.md:28`, `tests/test_outputs.py:281-286` |
| retain_seq transform + subset overlap | `test_pf04_retain_partial_overlap` | covered | `instruction.md:18`, `operations.md:31`, `tests/test_outputs.py:289-292` |
| gate_hold live spread from final masks | `test_pf05_gate_hold_live_spread` | covered | `operations.md:35`, `tests/test_outputs.py:294-296` |
| failback_early penalty uses pre_spread | `test_pf06_failback_early_penalty_spread` | covered | `instruction.md:19`, `operations.md:35`, `tests/test_outputs.py:299-310` |
| Three consecutive sweeps stable digest | `test_pf07_triple_sweep_stable` | covered | `instruction.md:20`, `tests/test_outputs.py:313-318` |
| segment_seq_crc crash kinds | `test_pf08_segment_crc_crash_kinds` | covered | `instruction.md:14`, `tests/test_outputs.py:321-326` |
| Shuffled filenames invariant | `test_pf09_changed_input_order_invariant` | covered | `tests/test_outputs.py:329-339` |
| session_token_hex derivation | `test_pf10_session_token_distinct`, `test_pf02` | covered | `operations.md:36`, `tests/test_outputs.py:342-345` |
| standby subset + path_overlap_index | `test_pf11_cross_pack_subset_invariant` | covered | `instruction.md:11-12`, `tests/test_outputs.py:348-354` |
| crash_mid target path mask convergence | `test_pf12_crash_mid_target_path_mask` | covered | `tests/test_outputs.py:357-359` |
| stale tail ignored | `test_pf13_stale_tail_ignored` | covered | `instruction.md:15`, `operations.md:24`, `tests/test_outputs.py:362-374` |
| rebuild idempotent | `test_pf14_rebuild_idempotent_after_source_touch` | covered | `tests/test_outputs.py:377-383` |
| flush_bump=0 → highest registration_order depth | `test_pf15_flush_bump_from_flag_registration` | covered | `operations.md:16,39`, `tests/test_outputs.py:386-398` |
| digest_hex recompute from row fields | `test_pf16_digest_recompute_consistency` | covered | `instruction.md:8`, `emit/digest.go`, `tests/test_outputs.py:401-414` |
| Injected additional scenarios (e.g. s07) | `test_pf06`, `test_pf09`, `test_pf15` | covered | `instruction.md:10`, `tests/test_outputs.py:248-266` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27, spec alignment |
| `environment/Dockerfile` | #15, #20, canonical base adjudication |
| `environment/docs/operations.md` | #27, flush_bump adjudication, #55 |
| `environment/epoch/loader.go` | intentional bug context |
| `task.toml` | #45, metadata |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | agent stats, rubric, external claims |
| `docs/guidelines/dockerfxile.md` | canonical base policy |
| `docs/guidelines/rubrics.md` | rubric format (#32-39) |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate iscsi-multipath-path-loss-recovery/
Summary: 0 error(s), 16 warning(s), 2 info
```

16 warnings are false-positive missing-docstring hits (type-hinted `def` lines). No canonical-base warning (Ubuntu digest matches).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| terminus-gpt5-5 | 40.0% (2/5) | Worst model |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone Go task; report matches folder |
| 1 Instruction | ☑ | Dense but complete; references operations.md |
| 2 Environment | ☑ | Canonical Ubuntu digest; tmux/asciinema; pinned deps; offline |
| 3 Oracle | ☑ | Platform 3/3; solve.sh derives via patched Go build |
| 4 Verifiers | ☑ | 16 tests; independent simulation; reward block; no runtime installs |
| 5 Metadata | ☑ | allow_internet=false; category/tags fit |
| 6 Rubric | ☑ | Flat non-milestone format; ≥3 negatives; no /tests/ refs |
| 7 LLMaJ & agent evidence | ☑ | Instruction-sufficiency FAIL disproven; agent stats reconciled |
| 8 Novelty & fairness | ☑ | Multi-package debugging; anti-cheat via inject + rebuild |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid multipath failback task — the independent Python verifier, injected s07 scenario, and rebuild-from-source checks are exactly the kind of anti-cheat design we want. I didn’t find any blockers on re-audit. The Ubuntu 24.04 base is digest-pinned and on the approved canonical list, `operations.md` already documents highest-`registration_order` for `flush_bump`, and all 16 tests have docstrings (the automated validator misses type-hinted defs). The platform rubric is correctly a flat non-milestone list, not milestone blocks. Optional polish: consider setting `difficulty` to medium to match the 40% worst-model rate, and trim rubric positives from 43 to ≤40 if you want to match the scoring band exactly.

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
