# Terminus Review Report: `scala-course-scheduler`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (automated `pip install` hit is a comment false-positive) |
| **Oracle** | not executed (harbor run did not complete in review window) |
| **CHECK count** | 33 |
| **UNCHECK count** | 22 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling, Rubric

**Decision (concise):** Strong adversarial Scala scheduler — digest-pinned hybrid image, oracle design, daemon anti-cheat, and broad verifier coverage are excellent. Two real acceptance blockers: (1) `test_source_soft_scorer_real_impl` enforces literal `weights.roomUtil`/`weights.facultySat` tokens not listed in the instruction’s source-audit contract, so functionally correct schedules can fail (confirmed by agent trial XeQLMZC at 93/94); (2) platform rubric uses four `# Rubric N` milestone blocks and 83 total positive points on a `number_of_milestones = 0` task. Fix SoftScorer documentation (or relax the test) and flatten/re-point the rubric first.

**Insights (concise):**

- ChatGPT’s High-severity SoftScorer claim is **confirmed** with file evidence; `preferredSlots` is partially inferable, `weights.roomUtil`/`weights.facultySat` are not.
- Automated validate/review `#14`/`#20` failures are **false positives** — `pip install` appears only in comments; Dockerfile line 16 pins `pytest==8.4.1 pytest-json-ctrf==0.3.5`.
- Platform rubric (`entire-report.txt` lines 434–484) violates non-milestone rubric rules: four milestone headers, 83 positive points (cap 10–40 total).
- Worst-model pass rate is exactly 80.0% (Claude Opus 4.8) — at the easy-tier ceiling but not >80%; not a rejection blocker.
- `conf-poisoner.sh` stale “ten tiers” comment is real but Low only; does not affect behavior.
- Instruction length/markdown/step-prescription fail formal styling checkboxes but are intentional for this adversarial design — not listed as revision blockers here.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | `SoftScorer.scala` source-audit requires literal `weights.roomUtil` or `weights.facultySat` in live code, but instruction source-audit section documents DataLoader, ConstraintChecker, and Scheduler tokens only — not SoftScorer field names | `tests/test_outputs.py:1246-1251`; `instruction.md:21-37` (no SoftScorer bullets); `instruction.md:244` (stub listed without token contract); agent trial XeQLMZC 93/94 in `entire-report.txt:206-210` | Add SoftScorer to the source-audit contract with required tokens (`weights.roomUtil`/`weights.facultySat` and `preferredSlots`), mirroring ConstraintChecker/Scheduler bullets — **or** relax `test_source_soft_scorer_real_impl` to accept semantically equivalent weight access |
| 2 | High | Rubric, Milestones | #34 | Non-milestone task (`number_of_milestones = 0`) but platform rubric uses milestone layout `# Rubric 1` … `# Rubric 4` | `task.toml:9`; `entire-report.txt:434-484`; `docs/guidelines/rubrics.md:60` (“Non-milestone: flat list; `# Rubric 1` optional; no `# Rubric 2+`”) | Flatten to a single rubric block (optional `# Rubric 1` header only) on the platform rubric |
| 3 | Medium | Rubric | #34 | Non-milestone rubric sums **83** positive points; Edition 2 cap is **10–40 total** for non-milestone tasks | `entire-report.txt:434-484` (sum +3…+2 lines = 83); `docs/guidelines/rubrics.md:25-28` | Trim/re-point criteria so total positives are 10–40 |

*Low-severity only (not blockers):* `conf-poisoner.sh:4` stale “ten tiers” comment; four daemon `pgrep` tests missing docstrings (`test_outputs.py:119-120,454-456,459-461,464-466`).

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | SoftScorer has undocumented `weights.roomUtil`/`weights.facultySat` source-token requirement; semantically correct code can fail (ChatGPT High) | **Agree** | `test_outputs.py:1250` asserts `"weights.roomUtil" in src or "weights.facultySat" in src`; `instruction.md:25-35` lists DataLoader/ConstraintChecker/Scheduler tokens only; `instruction.md:244` lists SoftScorer without token contract; XeQLMZC 93/94 in `entire-report.txt:206-210` |
| 2 | `preferredSlots` also required but undocumented | **Partially agree** | Test requires `preferredSlots` (`test_outputs.py:1251`); Bug B fix and `Instructor` model mention the field (`instruction.md:71-77`) but source-audit section does not list SoftScorer — secondary to the weight-field gap |
| 3 | conf-poisoner comment still says “ten tiers” (ChatGPT Low / LLMaJ typos fail) | **Agree** | `environment/scripts/daemons/conf-poisoner.sh:4` references `test_policy_d_has_ten_tiers`; actual test is `test_policy_d_has_sixteen_tiers` (`test_outputs.py:1017-1018`) |
| 4 | Non-canonical base image without justification (automated review warning) | **Disagree** | `environment/Dockerfile:1-7` digest-pins `python:3.13-slim-bookworm` and documents Python 3.13 + JDK + gcc need; author justification in `entire-report.txt:486-495` |
| 5 | Instruction too long / prescriptive (automated review suggestion) | **Partially agree** | `instruction.md` is ~255 lines with prescribed kill sequence (`instruction.md:233`); intentional for adversarial solvability — design note, not a spec-test blocker |
| 6 | Binary reward too punishing (agent analysis) | **Agree (informational)** | All-or-nothing `test.sh` reward; XeQLMZC 93/94 → 0.0 (`entire-report.txt:210`); not a Terminus acceptance blocker |
| 7 | `behavior_in_tests` / `behavior_in_task_description` LLMaJ pass | **Partially agree** | Broad alignment holds; SoftScorer weight-field tokens are the one material exception |
| 8 | test.sh runtime `pip install` (automated validate error) | **Disagree** | `tests/test.sh:6-7` mentions `pip install` only in a comment; runtime command is `python3 -m pytest` (`test.sh:17-18`); deps pinned in `Dockerfile:16` |
| 9 | Platform rubric acceptable as-is (implicit in submission) | **Disagree** | Milestone-format rubric on `number_of_milestones = 0` task; 83 positive points vs 10–40 cap (`entire-report.txt:434-484`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise | ~255 lines / ~4.4k words | `instruction.md` |
| 2 | UNCHECK | Natural prompt, not spec | Dense adversarial runbook tone | `instruction.md:233` |
| 3 | UNCHECK | No excessive markdown | Multiple `##` sections, code blocks | `instruction.md` |
| 4 | UNCHECK | No step-by-step HOW | Prescribed 11-step kill/neutralise sequence | `instruction.md:233` |
| 5 | UNCHECK | No hints/solving strategies | Extensive daemon-order and bypass HOW | `instruction.md:193-233` |
| 6 | CHECK | No design-doc I/O tables | No input→output mapping tables | `instruction.md` |
| 7 | UNCHECK | Well specified | SoftScorer weight-field tokens untested in prose | `instruction.md:21-37` vs `test_outputs.py:1250` |
| 8 | CHECK | Interesting | Realistic adversarial Scala scheduling | — |
| 9 | CHECK | Unique | Novel daemon + crypto + CSP combo | — |
| 10 | CHECK | Absolute paths | `/app/`, `/opt/scheduler/`, `/etc/scheduler/` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No `scala-course-scheduler` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web content fetch | Pre-bundled sbt tarball | `Dockerfile:25-28` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1 pytest-json-ctrf==0.3.5` | `Dockerfile:16` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367…` | `Dockerfile:7` |
| 16 | CHECK | Context in environment/ | `COPY . /app/` from environment only | `Dockerfile:31` |
| 17 | CHECK | No ground truth in env | Stubs throw `NotImplementedError`; random audit key at build | `Dockerfile:54-55`, stub files |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `Dockerfile` |
| 19 | CHECK | Compose mounts OK | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh runs pytest only | `Dockerfile:16`, `test.sh:17-18` |
| 21 | UNCHECK | Oracle passes | Not executed in this review window | — |
| 22 | CHECK | Oracle no internet | solve.sh uses local toolchain | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Implements stubs, fixes bugs, builds JAR | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical | mkdir + pytest + 0/1 write | `test.sh:9-23` |
| 25 | CHECK | Same logic oracle/agent | No `/oracle` branching | `test.sh`, `test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `test.sh:19-22` |
| 27 | UNCHECK | Tests aligned with instructions | SoftScorer weight-field token gap | `test_outputs.py:1250`, `instruction.md:21-37` |
| 28 | CHECK | Tests check correctness | Recomputes crypto, constraints, model.py score | `test_outputs.py` |
| 29 | UNCHECK | Behavior not implementation | Extensive source-token grep suite | `test_outputs.py:744+` |
| 30 | UNCHECK | No brittle string matching | Literal Scala token checks | `test_outputs.py:1250,1287-1288` |
| 31 | UNCHECK | Informative docstrings | 4 pgrep tests lack docstrings | `test_outputs.py:119,454,459,464` |
| 32 | CHECK | ≥3 negative rubric criteria | Five negatives in platform rubric | `entire-report.txt:445-446,458,483-484` |
| 33 | CHECK | Valid rubric scores | Only ±1,2,3,5 used | `entire-report.txt:434-484` |
| 34 | UNCHECK | Rubric line format | Milestone headers on non-milestone task; 83 pts > 40 cap | `task.toml:9`, `entire-report.txt:434-484` |
| 35 | CHECK | Rubric detailed | Task-specific daemon/bug/stub criteria | `entire-report.txt:434-484` |
| 36 | CHECK | Positive rubric phrasing | Bad behavior uses negative scores | `entire-report.txt:445-446` |
| 37 | CHECK | Rubric no /tests/ refs | No pytest or `/tests/` mentions | `entire-report.txt:434-484` |
| 38 | CHECK | Rubric no instruction.md refs | No instruction.md mentions | `entire-report.txt:434-484` |
| 39 | CHECK | Rubric no oracle/NOP | No oracle/NOP mentions | `entire-report.txt:434-484` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | version, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags/languages/category | Scala optimization/scheduling task | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 80% → easy tier | `task.toml:6`, `entire-report.txt:82-83` — informational, not a revision blocker |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile` |
| 51 | CHECK | No accessible solution in env | solution/ bind-mounted at runtime only | `Dockerfile`, `entrypoint.sh` |
| 52 | CHECK | Input not trivially mutable | SHA-256 pins + live policy recompute | `test_outputs.py` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80.0% — not >80% | `entire-report.txt:82-83` |
| 55 | UNCHECK | Not too hard/unfair | Undocumented SoftScorer tokens can fail correct schedules | `entire-report.txt:206-210` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 2, 3, 4, 5, 7, 21, 27, 29, 30, 31, 34, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Source-audit: DataLoader fixture filenames | `test_source_dataloader_real_impl` | covered | `instruction.md:25`; `test_outputs.py:823+` |
| Source-audit: ConstraintChecker tokens | `test_source_constraint_checker_real_impl` | covered | `instruction.md:26-33`; `test_outputs.py:1254+` |
| Source-audit: Scheduler tokens + Assignment ctor | `test_source_scheduler_uses_second_layer_constraints`, `test_source_assignment_ctor_not_copy` | covered | `instruction.md:34-35`; `test_outputs.py:959+,1283+` |
| Source-audit: PolicyLoader sort + TOML strings | `test_source_policy_loader_real_impl` | covered | `instruction.md:153,236`; `test_outputs.py:1171+` |
| SoftScorer uses `weights.roomUtil`/`weights.facultySat` | `test_source_soft_scorer_real_impl` | **gap** | Test at `test_outputs.py:1250`; not in `instruction.md:21-37` |
| SoftScorer references `preferredSlots` | `test_source_soft_scorer_real_impl` | partial | Test at `test_outputs.py:1251`; Bug B mentions field but no SoftScorer audit bullet |
| 14 hard constraints + score threshold | constraint tests + `test_score_meets_threshold` | covered | `instruction.md:5`; `test_outputs.py` |
| 28 daemon neutralisation | `test_no_*_running` + archive/cron tests | covered | `instruction.md` daemon section; `test_outputs.py:454+` |
| JSON field order + crypto outputs | `test_output_field_order`, audit/manifest tests | covered | `instruction.md:39-45`; `test_outputs.py` |
| sixteen conf.d tiers | `test_policy_d_has_sixteen_tiers` | covered | `instruction.md:5`; `test_outputs.py:1017` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-5, #7, #27, blocker 1, spec table |
| `tests/test_outputs.py` | #27-31, #55, blocker 1, spec table |
| `tests/test.sh` | #20, #24 |
| `environment/Dockerfile` | #14-17, #20, #50 |
| `task.toml` | #34, #45-49, blocker 2 |
| `entire-report.txt` | agent stats, rubric, XeQLMZC, adjudication |
| `environment/scripts/daemons/conf-poisoner.sh` | adjudication claim 3 |
| `solution/solve.sh` | #22-23, SoftScorer oracle tokens `828-829` |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate scala-course-scheduler/
Summary: 1 error(s), 6 warnings, 2 info
ERROR: test.sh — Runtime network install not allowed: pip\s+install
  → FALSE POSITIVE: comment-only mention in tests/test.sh:6-7
WARNING: unpinned pip in Dockerfile comment — FALSE POSITIVE; line 16 pins pytest
WARNING: 4 tests missing docstrings — LOW
INFO: non-milestone task (milestones preferred, not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | `entire-report.txt:83` |
| terminus-claude-opus-4-8 | 80.0% (4/5) | `entire-report.txt:82` |
| oracle | 100.0% (3/3) | `entire-report.txt:87` |
| nop | 0.0% (0/1) | `entire-report.txt:86` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (60–80% band) |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only per review policy |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `scala-course-scheduler`; regular layout; Scala/data-processing |
| 1 Instruction | ☑ | Long adversarial prompt; source-audit gap on SoftScorer weight fields |
| 2 Environment | ☑ | Digest-pinned hybrid image justified; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☐ | Harbor oracle started but did not complete in review window |
| 4 Verifiers | ☑ | 94 tests; reward block OK; source-audit suite documented except SoftScorer weights |
| 5 Metadata | ☑ | `number_of_milestones = 0`; timeouts plausible |
| 6 Rubric | ☑ | Platform rubric in report — milestone format + point cap fail |
| 7 LLMaJ & agent evidence | ☑ | XeQLMZC confirms spec gap; hack check clean |
| 8 Novelty & fairness | ☑ | Multi-phase adversarial; unfair only on undocumented SoftScorer tokens |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really impressive work on this one — the adversarial environment, crypto verification, constraint coverage, and anti-cheat design are among the strongest I’ve seen. The Dockerfile justification for the hybrid Python/JDK image is solid, and agent runs show the task is genuinely hard without being unsolvable. Two things to fix before accept: please add `SoftScorer.scala` to the source-audit contract with the exact live-code tokens the verifier expects (`weights.roomUtil` or `weights.facultySat`, plus `preferredSlots`) — right now an agent can pass 93/94 checks with a valid above-threshold schedule and still fail on that one undocumented grep. Also, since this is a non-milestone task, flatten the platform rubric to a single block (no `# Rubric 2`–`4`) and bring total positive points into the 10–40 range.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
| Rubric | yes | 2, 3 |
| Milestones | yes | 2 |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review scala-course-scheduler/ --report entire-report.txt`._
