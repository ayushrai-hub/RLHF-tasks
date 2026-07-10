# Terminus Review Report: `subtyping-transitivity-checker-go`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3); not executed locally (Docker unavailable) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Solid debugging task with good agent calibration (0–40% pass) and a compliant rubric/Dockerfile, but two High gaps block acceptance: (1) no verifier dataset exercises unprovable obligations, non-empty `breaking_rules`, or `transitivity_holds=false`; (2) direct-rule obligation suppression is tested in four tests but never stated in `instruction.md`, which drove systematic agent failures. AutoEval build failure and non-canonical-base claims in the export are not substantiated blockers.

**Insights (concise):**

- Platform oracle 100% (3/3) and all 38 unit tests ran on agent trials — AutoEval `Build status: FAILED` is likely infra/stale, not reproduced in task artifacts.
- `environment/Dockerfile:1` uses the **canonical** `golang:1.24-bookworm` digest listed in `docs/guidelines/dockerfile.md:11` — Harbor review report’s `ghcr.io/laude-institute/t-bench/...` recommendation is outdated.
- Rubric is correct **non-milestone flat format** (no `# Rubric 2+`); positive sum = 23 (≤40); 3 distinct negatives.
- `breaking_rules` empty-array tests catch the unfixed “all obligations” bug indirectly, but an agent can hardcode `return []` and never prove the unprovable-only filter.
- Agent instruction-sufficiency analysis (7/8 trials at 32/38) pinpoints direct-rule suppression as the sole systematic miss — aligns with spec↔test gap.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #55 | No dataset tests failure-reporting path: all four rule files yield `unprovable_count=0`, `transitivity_holds=true`, `breaking_rules=[]`, and every obligation has `is_provable=true`. Core bugs (breaking_rules filter, `transitivity_holds` inversion, `is_provable=false`) are untested on the negative path. | `tests/test_outputs.py:10-12,57-72,99-106,207-208,250-253,365-368`; all of `tests/{alt,edge,stress}_rules.json` produce fully provable graphs | Add a hidden test dataset (e.g. `broken_rules.json`) with genuinely unprovable obligations; assert `unprovable_count>0`, `transitivity_holds=false`, specific `is_provable=false` rows, and non-empty sorted `breaking_rules`. |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Direct-rule obligation suppression is enforced by tests but absent from `instruction.md`. Instruction only says “identify all transitive proof obligations” without stating that an existing direct rule A<:C suppresses generation for pair (A,C). | `instruction.md:3` (no suppression rule); `tests/test_outputs.py:159-166,220-225,311-316`; `entire-report.txt:92-124` (7/8 agent trials failed `test_no_obligation_for_direct_rules`); env code comment `environment/pkg/checker/checker.go:45-46` describes behavior but instruction warns docs may contain errors | Add explicit requirement: when a direct rule A<:C exists, do **not** generate a transitive obligation for (A,C) via any intermediate B. |

*Secondary (not disposition-driving alone):* `#10` — `instruction.md:1` uses `./cmd/transitivity-checker` (relative) in build command; should be `/app/cmd/transitivity-checker`.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | AutoEval/build failure unresolved (ChatGPT High; `entire-report.txt:2`) | **Partially agree** | `entire-report.txt:2` reports `Build status: FAILED`; but `entire-report.txt:36` oracle 100% (3/3), lines 43–81 show all 38 tests executed on agent runs. No reproducible build error in task artifacts. Treat as platform infra noise unless re-run fails — **not a standalone blocker** given oracle pass on platform. |
| 2 | No negative/unprovable-path test coverage (ChatGPT High; test-quality review `entire-report.txt:317-389`) | **Agree** | `tests/test_outputs.py:10-12,57-72,99-106,207-208,250-253,365-368` — every dataset expects all provable, empty breaking_rules, transitivity holds. |
| 3 | Direct-rule suppression not in instruction (ChatGPT High) | **Agree** | `instruction.md:3` lacks rule; tests at `test_outputs.py:159-166,220-225,311-316` enforce it; `entire-report.txt:109-124` documents systematic agent failure. |
| 4 | `test.sh` exits non-zero on Go build failure (ChatGPT Medium; `entire-report.txt:218-249`) | **Agree (non-blocking)** | `tests/test.sh:7-9` `exit $BUILD_RC`; line 3 pre-writes `reward.txt=0`. Single Medium per severity rules — note only. |
| 5 | Category data-processing vs debugging (ChatGPT Low; `entire-report.txt:198-215`) | **Disagree as blocker** | `task.toml:6` `category = "data-processing"`; author rebuttal `entire-report.txt:5-6` notes legacy acceptance. Per `prompt.md` difficulty/category metadata mismatch is not a revision driver. |
| 6 | Non-canonical Docker base image (Harbor review `entire-report.txt:167-191`) | **Disagree** | `environment/Dockerfile:1` digest matches canonical table `docs/guidelines/dockerfile.md:11`. Harbor suggestion references obsolete `ghcr.io/laude-institute/t-bench/...` image. |
| 7 | Rubric positive total within cap (ChatGPT Low) | **Agree** | `entire-report.txt:467-476`: positives 5+5+3+3+3+2+2=23 ≤ 40; negatives -5,-3,-3 (3 distinct). |
| 8 | Non-milestone task in milestone rubric format (user query) | **Disagree** | `entire-report.txt:467-476` is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct non-milestone format per `docs/guidelines/rubrics.md:55-66`. |
| 9 | LLMaJ `behavior_in_tests` PASS (`entire-report.txt:130`) | **Partially agree** | Tests cover instruction-described schema/CLI/config; but negative-path and direct-suppression instruction gaps mean LLMaJ overstates alignment. |
| 10 | Instruction sufficiency FAIL (`entire-report.txt:84-124`) | **Agree** | Direct contradiction between tested suppression behavior and instruction text; 7/8 trials failed same tests. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 short paragraphs, ~223 words | `instruction.md` |
| 2 | CHECK | Natural tone | Conversational debugging prompt | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal, not fix steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | No walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | UNCHECK | Well specified | Direct-rule suppression tested but not specified | `instruction.md:3`, `tests/test_outputs.py:159-166` |
| 8 | CHECK | Interesting | Realistic Go debugging / type-theory scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify vs corpus | — |
| 10 | UNCHECK | Absolute paths only | `./cmd/transitivity-checker` relative in build cmd | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | Absent | `instruction.md` |
| 12 | CHECK | No canary string | Absent | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/` |
| 14 | CHECK | Pinned pip versions | `pytest==8.4.1` | `environment/Dockerfile:7-8` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only env files | `environment/Dockerfile:11-17` |
| 17 | CHECK | No ground-truth answers | Misleading docs intentional; instruction warns | `instruction.md:1`, `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged mode | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:7-8`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:36` |
| 22 | CHECK | Oracle no internet | solve.sh patches local files only | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Patches checker.go, rebuilds | `solution/solve.sh:20-86` |
| 24 | CHECK | reward.txt + failure path | Pre-writes 0; final 0/1 block | `tests/test.sh:2-3,17-20` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:17-20` |
| 27 | UNCHECK | Tests aligned with instruction | Phantom direct-suppression req; no negative-path coverage | §2 blockers 1–2 |
| 28 | CHECK | Tests check correctness | Behavioral JSON assertions across 4 datasets | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | No source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Structured JSON checks | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives (-5,-3,-3) | `entire-report.txt:474-476` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All criteria valid | `entire-report.txt:467-476` |
| 34 | CHECK | Rubric `Agent …, ±N` format | Flat non-milestone list | `entire-report.txt:467-476` |
| 35 | CHECK | Rubric detailed | Task-specific bug-fix criteria | `entire-report.txt:467-473` |
| 36 | CHECK | Positive phrasing | Penalties use negative scores | `entire-report.txt:474-476` |
| 37 | CHECK | Rubric no /tests/ refs | No test references | `entire-report.txt:467-476` |
| 38 | CHECK | Rubric no instruction.md refs | No metadata refs | `entire-report.txt:467-476` |
| 39 | CHECK | Rubric no oracle/NOP refs | Absent | `entire-report.txt:467-476` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages applicable | go/bash tags match | `task.toml:11-12` |
| 45 | CHECK | Difficulty field present | `hard` in toml; worst-model 0% | `task.toml:8`, `entire-report.txt:26-32` |
| 46 | UNCHECK | steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | .dockerignore excludes tests | `environment/.dockerignore` |
| 51 | CHECK | Solution not in image | .dockerignore excludes solution | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot trivially cheat | Hidden `/tests/*.json` datasets not in image | `tests/test_outputs.py:181-189` |
| 53 | CHECK | Git repos pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:31-32` |
| 55 | UNCHECK | Not unfair | Spec gap on direct suppression caused systematic near-misses | `entire-report.txt:84-124` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 10, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build/run CLI paths | `test_output_file_exists`, `test_binary_no_args_exits_nonzero` | covered | `instruction.md:1`, `tests/test_outputs.py:31-33,283-289` |
| Output JSON schema | `test_output_valid_json`, `test_obligation_schema` | covered | `instruction.md:3`, `tests/test_outputs.py:36-42,85-96` |
| `settings.toml` authoritative | `test_config_settings_authoritative` | covered | `instruction.md:1`, `tests/test_outputs.py:256-261` |
| Deterministic sorted obligations | `test_obligations_sorted`, `test_repeated_runs_deterministic` | covered | `instruction.md:3`, `tests/test_outputs.py:75-82,264-280` |
| `breaking_rules` when transitivity holds | `test_breaking_rules_empty`, `test_edge_breaking_rules_empty` | covered (positive path only) | `instruction.md:3`, `tests/test_outputs.py:69-72,250-253` |
| `breaking_rules` for unprovable obligations | — | **gap** | No dataset with non-empty expected `breaking_rules` |
| `transitivity_holds=false` path | — | **gap** | All tests expect `True` |
| `is_provable=false` obligations | — | **gap** | `test_all_obligations_provable` only asserts true |
| Direct A<:C suppresses obligation | `test_no_obligation_for_direct_rules`, alt/edge/stress variants | **phantom** (tested, not in instruction) | `tests/test_outputs.py:159-166`; absent from `instruction.md` |
| Exact obligation counts (7, 11, etc.) | `test_obligation_count`, stress/alt counts | covered (implicit from algorithm) | `tests/test_outputs.py:51-54,198-201,305-308` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blockers 1–2, spec alignment |
| `tests/test_outputs.py` | #27, #31, blocker 1, adjudication rows 2–3 |
| `tests/test.sh` | #24, adjudication row 4 |
| `environment/Dockerfile` | #15, adjudication row 6 |
| `environment/pkg/checker/checker.go` | direct-suppression code comment, bug patterns |
| `solution/solve.sh` | #22, #23 |
| `task.toml` | #45, #46–49 N/A |
| `entire-report.txt` | #21, #32–39 rubric, agent stats, prior feedback |
| `docs/guidelines/dockerfile.md` | canonical base adjudication |
| `docs/guidelines/rubrics.md` | rubric format adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate subtyping-transitivity-checker-go/
Summary: 0 error(s), 1 warning(s), 3 info
WARNING: instruction.md may use relative paths (./cmd/transitivity-checker)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Hard tier |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Hard tier |
| oracle | 100.0% (3/3) | Platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Lowest per-test pass rates on obligation-count/suppression tests: 2/10 (`test_obligation_count`, `test_no_obligation_for_direct_rules`, alt/stress variants) — aligns with spec gap, not random agent noise.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches export; regular layout; `number_of_milestones=0` |
| 1 Instruction | ☑ | Gaps on direct suppression and `./` path |
| 2 Environment | ☑ | Canonical digest-pinned Go image; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | solve.sh patches 4 bugs; platform oracle 100% |
| 4 Verifiers | ☑ | Missing negative-path coverage; reward block OK |
| 5 Metadata | ☑ | Category debatable but not blocking |
| 6 Rubric | ☑ | Flat non-milestone format; 23 pts; 3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL corroborated |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; spec gap unfair near-miss |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really nice debugging task — the multi-bug Go pipeline, hidden alt/edge/stress datasets, and difficulty calibration all look strong, and the rubric/Docker setup are in good shape. Two things to fix before acceptance: please add a hidden test dataset where some obligations are genuinely unprovable and assert non-empty `breaking_rules`, `transitivity_holds=false`, and specific `is_provable=false` rows — right now every fixture expects the happy path, so the failure-reporting logic isn’t really verified. Also, the tests require that a direct rule A<:C suppresses generating a transitive obligation for that pair, but `instruction.md` never says that — agents consistently got stuck on exactly those tests. Please spell out that suppression rule in the instruction (and use `/app/cmd/transitivity-checker` instead of `./cmd/transitivity-checker` in the build line while you’re there).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Instruction Styling | yes | 2 |
| Test Build Issues | no | — |
| Rubric | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
