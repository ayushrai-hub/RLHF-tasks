# Terminus Review Report: `contfrac_20260627_232952.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report 3/3; not re-run locally — Harbor milestone path error) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Milestone structure, Dockerfile, oracle design, and anti-cheat are solid. Two real blockers: Milestone 2 never states the `p` or `p/q` (omit `/1`) output rule that Milestone 1 gives for VALUE and that tests enforce for CONVERGENT/CONVERGENTS — causing systematic agent failures on integer convergents (`4` vs `4/1`). Second: documented `ERROR: divzero` for VALUE has no test coverage. Fix those before accept.

**Insights (concise):**

- ChatGPT High-severity M2 format claim is **confirmed** with file evidence; agent runs failed `test_m2_convergent` / `test_m2_more` at 7/10 (30% failure rate on those tests).
- ChatGPT Medium divzero gap is **confirmed**; `m1_errors.txt` has no VALUE divzero input.
- Automated `./scripts/terminus review` falsely flagged #1 (combined 3 milestone instructions) and #54 (used 100% best-model instead of 40% worst-model) — overridden.
- Docstrings missing on all 24 test functions — Low only; not a revision driver alone.
- `entire-report.txt` contains **no platform rubric** — #32–39 N/A here; author must supply milestone-format rubric (`# Rubric 1` … `# Rubric 3`) on platform, not flat non-milestone list.
- Declared `difficulty = "hard"` vs 40% worst-model (medium tier) is informational, not a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Milestone 2 omits integer rational print rule (`p` or `p/q`, omit `/1`) that tests require for CONVERGENT/CONVERGENTS | M1: `steps/milestone_1/instruction.md:5` — `printed in lowest terms as p or p/q`. M2: `steps/milestone_2/instruction.md:3-4` — only `as a reduced fraction`. Expected: `steps/milestone_2/tests/cases/exp/m2_convergent.txt:1,6` → `4`, `7`; `m2_more.txt:4` → `0` (not `4/1`, `7/1`, `0/1`). Agent evidence: `entire-report.txt:24-25` — `test_m2_convergent` 7/10, `test_m2_more` 7/10 | Add to M2 instruction (CONVERGENT and CONVERGENTS): print each convergent as `p` or `p/q`, omitting denominator when 1 — same convention as M1 VALUE |
| 2 | Medium | Test Alignment/Coverage Issues | #27 | `ERROR: divzero` documented for VALUE but never tested | `steps/milestone_1/instruction.md:7` — `a VALUE that divides by zero prints ERROR: divzero`. `steps/milestone_1/tests/cases/in/m1_errors.txt:1-7` — no VALUE divzero case (only CF/LEN/NOPE errors) | Add at least one VALUE input triggering divzero (e.g. `VALUE 1 0`) with expected `ERROR: divzero` to `m1_errors` case files (replicate in M2/M3 regression copies) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M2 convergent output format under-specified; tests expect `4` not `4/1` (ChatGPT High) | **Agree** | `steps/milestone_2/instruction.md:3-4` vs `steps/milestone_2/tests/cases/exp/m2_convergent.txt:1,6` and `m2_more.txt:4`; `entire-report.txt:24-25,57-62` |
| 2 | No VALUE divzero test despite documented error (ChatGPT Medium; test-quality review) | **Agree** | `steps/milestone_1/instruction.md:7`; `steps/milestone_1/tests/cases/in/m1_errors.txt` — no VALUE line |
| 3 | Test methods lack docstrings (ChatGPT Low; LLMaJ informative_test_structure fail) | **Agree** (Low only) | `steps/milestone_1/tests/test_m1.py:5-10` — bare `check()` calls; validate: 24 warnings |
| 4 | LLMaJ `behavior_in_task_description` PASS | **Disagree** | LLMaJ missed M2 format gap; M2 does not repeat M1 `p` or `p/q` rule |
| 5 | LLMaJ `behavior_in_tests` PASS | **Partially agree** | Most behaviors covered; divzero gap remains |
| 6 | Harbor review "READY TO USE" | **Disagree** on M2 fairness | Same divzero/docstring warnings valid; missed M2 integer-format spec gap that caused 30% agent failures |
| 7 | Instruction sufficiency analysis: spec defect on M2 format (entire-report) | **Agree** | Consistent with artifact proof above |
| 8 | Automated review #1 "instruction too long" | **Disagree** | Each milestone instruction is 2 short paragraphs (~80–120 words); combined-count heuristic inappropriate for milestone layout per `docs/guidelines/milestones.md` |
| 9 | Automated review #54 "worst-model 100% too easy" | **Disagree** | `entire-report.txt:7-8` — worst model `terminus-gpt5-5` 40% (2/5), not 100% |
| 10 | Non-canonical `gcc:13-bookworm` base (Harbor review warning) | **Partially agree** (not blocking) | `environment/Dockerfile:1` — digest-pinned; credible C++ toolchain justification |
| 11 | AutoEval build FAILED (entire-report footer) | **Unverified** | Platform AutoEval only; local Dockerfile structure passes static review |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction ≤3 paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads like engineer request, not spec dump | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no heavy headers/tables | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step-by-step dev steps | States commands/behavior, not dev workflow | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints/solving strategies | Recurrence formulas are domain spec, not solve walkthrough | `steps/milestone_2/instruction.md:1` |
| 6 | CHECK | No design-doc I/O tables | None present | — |
| 7 | UNCHECK | Well specified | M2 missing `p`/`p/q` print convention | Blocker 1 |
| 8 | CHECK | Interesting | Non-trivial number-theory CLI in C++ | task content |
| 9 | CHECK | Unique | Continued-fraction + Pell milestone progression appears distinct | — |
| 10 | CHECK | Absolute paths | `/app/contfrac.cpp`, `/app/contfrac` | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No `contfrac` task name string | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:6-7` |
| 15 | CHECK | FROM digest-pinned | `@sha256:930f2e…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | No external COPY | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in env | No answer leakage in env files | `environment/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts safe | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:6-7`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform: oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle no internet | solve copies/compiles local C++ | `steps/milestone_1/solution/solve1.sh` |
| 23 | CHECK | Oracle real implementation | `rstr()` omits `/1` for integers | `steps/milestone_3/solution/contfrac.cpp:12` |
| 24 | CHECK | reward.txt canonical | Writes 0 on fail, 1 on pass | `steps/milestone_1/tests/test.sh:3-11` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Binary rewards | 0/1 only | `steps/milestone_1/tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M2 tests enforce unstated integer format; divzero untested | Blockers 1–2 |
| 28 | CHECK | Tests check correctness | I/O diff against computed CF/Pell outputs | `steps/milestone_*/tests/conftest.py` |
| 29 | CHECK | Behavior not implementation | Runs compiled binary, no source grep | `steps/milestone_1/tests/conftest.py` |
| 30 | CHECK | Exact matching appropriate | Line-oriented CLI protocol | case file design |
| 31 | UNCHECK | Informative docstrings | 24 test functions lack docstrings | `steps/milestone_1/tests/test_m1.py:5-10`; validate warnings |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric in submission export | `entire-report.txt` — no rubric section |
| 33 | UNCHECK | Rubric valid scores | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle mentions | N/A | — |
| 40 | CHECK | Required files present | milestone layout complete | `task.toml`, `steps/`, `environment/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author fields | present | `task.toml:4-5` |
| 43 | CHECK | metadata complete | version, category, milestones, timeouts | `task.toml` |
| 44 | CHECK | tags/languages match | `cpp`, `scientific-computing` | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 40% → medium tier | `task.toml:6`, `entire-report.txt:7-8` |
| 46 | CHECK | steps/ layout | 3 milestones under `steps/` | `task.toml:9,24-43` |
| 47 | CHECK | solveN.sh per milestone | solve1/2/3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/m2/m3.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | `TestMilestoneN` classes test only milestone N features | `steps/milestone_2/tests/test_m2.py:4-10` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests/ | `environment/.dockerignore:17` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/ | `environment/.dockerignore:16` |
| 52 | CHECK | Input not trivially mutable | Cases mounted at runtime under /tests | Harbor pattern |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% < 80% | `entire-report.txt:7-8` |
| 55 | UNCHECK | Not too hard/unfair | M2 format ambiguity caused systematic 30% test failures | `entire-report.txt:24-25,57-62` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| M1: CF/LEN/VALUE commands | `test_m1_cf`, `test_m1_value` | covered | case files `m1_cf`, `m1_value` |
| M1: ERROR range/parse/usage/unknown | `test_m1_errors` | covered | `m1_errors.txt` |
| M1: ERROR divzero for VALUE | `test_m1_errors` | **gap** | `instruction.md:7`; no VALUE divzero in `m1_errors.txt` |
| M1: VALUE output `p` or `p/q` | `test_m1_value` | covered | `m1_value.txt` expected `7`, `1/7`, etc. |
| M2: CONVERGENT/CONVERGENTS | `test_m2_convergent`, `test_m2_more` | covered | case files |
| M2: integer convergent as `p` (omit `/1`) | `test_m2_convergent`, `test_m2_more` | **gap in spec** | expected `4`, `0`; instruction only says "reduced fraction" |
| M2: ERROR range for bad k | `test_m2_errors` | covered | `m2_errors.txt` |
| M3: SQRTCF/PERIOD/PELL | `test_m3_sqrt`, `test_m3_pell`, `test_m3_errors` | covered | case files |
| M3: perfect-square edge cases | `test_m3_pell`, `test_m3_sqrt` | covered | PELL `none`, PERIOD `0` in expected files |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/instruction.md` | M1 VALUE format, divzero spec |
| `steps/milestone_2/instruction.md` | M2 format gap (blocker 1) |
| `steps/milestone_2/tests/cases/exp/m2_convergent.txt` | Integer convergent expected output |
| `steps/milestone_2/tests/cases/exp/m2_more.txt` | `CONVERGENT 1 7 0` → `0` |
| `steps/milestone_1/tests/cases/in/m1_errors.txt` | divzero gap |
| `steps/milestone_3/solution/contfrac.cpp:12` | Oracle `rstr()` format |
| `environment/Dockerfile` | #15, #20 |
| `task.toml` | metadata, milestones |
| `entire-report.txt` | agent stats, LLMaJ, sufficiency analysis |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate contfrac_20260627_232952.
Summary: 0 error(s), 24 warning(s) — all informative_test_docstrings
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | best model |
| oracle | 100.0% (3/3) | platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

Per-test failures concentrated on M2 convergent cases: `test_m2_convergent` 7/10, `test_m2_more` 7/10 (`entire-report.txt:24-25`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `contfrac_20260627_232952.`; 3-milestone C++ scientific-computing task; report matches |
| 1 Instruction | ☑ | M2 format gap confirmed; per-milestone instructions concise |
| 2 Environment | ☑ | Digest-pinned gcc image; tmux/asciinema; pytest pinned; no tests/solution in image |
| 3 Oracle | ☑ | Real C++ implementation; `rstr` omits `/1`; platform oracle 100% |
| 4 Verifiers | ☑ | Canonical reward block; no runtime installs; divzero + docstrings gaps |
| 5 Metadata | ☑ | `number_of_milestones=3` matches `[[steps]]`; category/tags OK |
| 6 Rubric | ☑ | **No rubric in export** — #32–39 N/A; task is milestone — author must use `# Rubric 1/2/3` blocks on platform, not flat non-milestone list |
| 7 LLMaJ & agents | ☑ | Sufficiency analysis agrees on M2 format; LLMaJ behavior_in_task_description overstated |
| 8 Novelty & fairness | ☑ | Genuine multi-milestone number theory; M2 format unfair until fixed |
| 9 Long context | — | N/A (not tagged) |

---

## 9. Reviewer note (copy-paste to portal)

Really nice work on this one — the three-milestone progression, digest-pinned GCC environment, and I/O-diff verifier design are all in good shape, and agents clearly understood the math (Milestone 3 logic passed even when M2 formatting failed). Two fixes before we can accept: (1) Milestone 2’s instruction should explicitly say convergents print as `p` or `p/q`, omitting the denominator when it’s 1 — the same rule Milestone 1 already gives for VALUE. Right now tests expect `4` and `0` but the spec only says “reduced fraction,” which is why multiple agents reasonably printed `4/1` and `0/1`. (2) Add at least one test case for `VALUE` division-by-zero (`ERROR: divzero`) since it’s documented in Milestone 1 but never exercised. Optional polish: short docstrings on the pytest methods would make failure reports easier to read.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Milestones | no | — |
| Rubric | no (not in export) | — |
| Task Difficulty | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
