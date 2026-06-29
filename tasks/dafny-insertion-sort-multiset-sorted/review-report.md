# Terminus Review Report: dafny-insertion-sort-multiset-sorted

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (false-positive Dockerfile regex on `COPY solution.dfy`) |
| **Oracle** | pass (1/1, reward 1.0) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Strong formal-verification task: frozen spec hash, Dafny verifier oracle, escape-hatch bans, and behavioral harnesses are well designed. Oracle passes. The sole High blocker is `test_no_ghost_copy`: it rejects any file containing both `ghost var` and `new int`, but the shipped `Main()` scaffold already allocates with `new int`, so standard `ghost var pre := a[..]` snapshot proofs fail despite satisfying `instruction.md`. Narrow the heuristic or document/ban the pattern in the spec.

**Insights (concise):**

- ChatGPT / instruction-sufficiency analysis is correct: 5/5 GPT runs failed with 6/7 tests passing; only `test_no_ghost_copy` failed at 5/10 aggregate.
- Oracle `solution_correct.dfy` avoids `ghost var` (uses `var s := a[..]` in a lemma), so oracle passes while legitimate agent proofs can fail.
- Automated `#54` blocker in baseline report is wrong: worst benchmark model is GPT-5.5 at 0%, not Claude at 100% (`scripts/review_checklist.py` uses `max()` for “worst”).
- Platform rubric uses optional `# Rubric 1` header only — acceptable for `number_of_milestones = 0` per `docs/guidelines/rubrics.md`.
- Dockerfile `COPY solution.dfy` is correct starter packaging; validate script regex is overbroad (`\bsolution\b` matches filename).
- Rubric has two positive lines with “Agent does not …” phrasing (#36 Medium note, not a Revise driver alone).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #55 | `test_no_ghost_copy` enforces an unstated requirement and false-positives on valid proofs using `ghost var` sequence snapshots while `Main()` already contains `new int` | `tests/test_outputs.py:212-218`; `environment/solution.dfy:38,44`; `instruction.md:5` (bans only assume/axiom/verify-false/extern); `entire-report.txt:37` (5/10 on `test_no_ghost_copy`) | Narrow check to the actual cheat pattern (e.g. `ghost var … := new int[…]` and/or exclude `method Main`), **or** explicitly ban `ghost var` in `instruction.md` if that constraint is intended |

*No other High/Medium revision drivers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `test_no_ghost_copy` is overbroad; flags `ghost var` + starter `new int` in `Main()` (ChatGPT) | **Agree** | `test_outputs.py:213-215` regex on full stripped file; `solution.dfy:38,44` pre-existing `new int`; instruction silent on `ghost var` |
| 2 | Legitimate proofs use `ghost var pre := a[..]` idiom (ChatGPT / entire-report) | **Agree** | Standard Dafny snapshot pattern; co-occurrence heuristic does not distinguish from `ghost var … := new int[…]` hack described in docstring `test_outputs.py:207-210` |
| 3 | All 5 GPT agents failed only on `test_no_ghost_copy` after local verify success (entire-report) | **Agree** | `entire-report.txt:31-37,44-55`; GPT 0/5 overall, `test_no_ghost_copy` 5/10 |
| 4 | Instruction sufficiency FAIL due to hidden ghost-var constraint (entire-report LLMaJ) | **Agree** | `instruction.md:5` vs `test_no_ghost_copy` assertion; no mention of ghost-copy ban in instruction |
| 5 | Optional WORKDIR guard missing in `test.sh` (Harbor review / ChatGPT Low) | **Disagree** (not a blocker) | `tests/test.sh:6` explicit `cd /app`; Low severity per checklist |
| 6 | Generic directory name `tbench-task` (Harbor review) | **Disagree** (stale) | Task folder is `dafny-insertion-sort-multiset-sorted`; report references old path |
| 7 | Dockerfile Dafny wget availability risk (Harbor review) | **Partially agree** (informational) | `environment/Dockerfile:19-21` build-time fetch with sha256 check; allowed per build-time policy; not a blocker |
| 8 | LLMaJ `behavior_in_tests` PASS — all instruction behaviors covered | **Partially agree** | Core behaviors covered; `test_no_ghost_copy` tests behavior **not** stated in instruction |
| 9 | Test quality review ACCEPT (entire-report) | **Partially agree** | Suite is strong overall; `test_no_ghost_copy` heuristic undermines fairness |
| 10 | Task too easy — worst model 100% (#54 in baseline report) | **Disagree** | `entire-report.txt:20-21`: GPT 0%, Claude 100%; per `difficulty.md` worst model = lowest rate (0%); #54 should CHECK |
| 11 | Rubric negative phrasing (#36 in baseline report) | **Agree** (Medium note only) | `entire-report.txt:297-298`: “Agent does not use assume…” +5, “Agent does not modify…” +3; single Medium ≠ Revise per severity rules |
| 12 | Non-milestone task uses milestone rubric format | **Disagree** | `task.toml:10` `number_of_milestones = 0`; rubric has only `# Rubric 1` (optional per `rubrics.md:64`); no `# Rubric 2+` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs, ~155 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Direct task framing, no spec-doc boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown | Single `#` header, no tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | States goal and constraints only | `instruction.md` |
| 5 | CHECK | No hints / HOW-not-WHAT | Docs explain concepts, not proof annotations | `environment/docs/` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | CHECK | Well specified | Clear verifier goal, frozen spec, forbidden escape hatches | `instruction.md:3-5` |
| 8 | CHECK | Interesting / useful | Real Dafny proof task for developers | — |
| 9 | CHECK | Unique | No duplicate found in review scope | — |
| 10 | CHECK | Absolute paths | `/app/solution.dfy`, `/app/verify.sh`, `/app/run.sh` | `instruction.md:3,7` |
| 11 | CHECK | Task name not in instruction | Name absent | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | wget only at Docker build for Dafny zip | `environment/Dockerfile:19-21` |
| 14 | CHECK | Pinned pip deps | `pytest==8.2.0`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:25` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY limited to env files | `environment/Dockerfile:29-32` |
| 17 | CHECK | No ground-truth answers in env | Starter skeleton + educational docs only | `environment/solution.dfy` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image; test.sh clean | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:25`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Harbor oracle 1.0 reward | oracle run 2026-06-28 |
| 22 | CHECK | Oracle no runtime network | `cp` + `verify.sh` only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction | Full annotated Dafny proof, not hardcoded output | `solution/solution_correct.dfy` |
| 24 | CHECK | reward.txt canonical block | mkdir, trap, 0/1 write | `tests/test.sh:1-13` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:9-12` |
| 27 | UNCHECK | Tests aligned with instructions | `test_no_ghost_copy` bans unstated `ghost var` + `new int` co-occurrence | Blocker 1 |
| 28 | CHECK | Tests check correctness | `dafny verify`, behavioral sort cases | `tests/test_outputs.py` |
| 29 | CHECK | Behavior-focused verification | Primary oracle is `dafny verify` + runtime harness; source grep limited to explicit anti-cheat | `test_verifies`, `test_behavioral` |
| 30 | CHECK | No brittle long-string asserts | Hash + regex checks are appropriate | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All seven `test_*` documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives (-5,-5,-3,-1) | `entire-report.txt:299-301` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines comply | `entire-report.txt:288-301` |
| 34 | CHECK | `Agent …, ±N` format | 15 Agent lines | `entire-report.txt:288-301` |
| 35 | CHECK | Rubric detailed / precise | Task-specific Dafny proof steps | `entire-report.txt:288-301` |
| 36 | UNCHECK | Positive rubric phrasing | Two positives use “Agent does not …” | `entire-report.txt:297-298` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:288-301` |
| 38 | CHECK | Rubric no instruction.md refs | Clean | `entire-report.txt:288-301` |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | `entire-report.txt:288-301` |
| 40 | CHECK | Required files present | All standard layout files | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, difficulty, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Dafny formal-verification task | `task.toml:6-12` |
| 45 | CHECK | Difficulty defensible | `hard`: best model 0% ≤20% per `difficulty.md` | `entire-report.txt:20-21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | Only starter `solution.dfy` | `environment/Dockerfile:29` |
| 52 | CHECK | Input not trivially mutable | Spec region SHA-256 locked | `tests/test_spec_frozen` |
| 53 | CHECK | Git repos pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model GPT 0% (not >80%) | `entire-report.txt:20-21`, `difficulty.md` |
| 55 | UNCHECK | Not unfair | Hidden ghost-copy heuristic disqualifies standard proofs | Blocker 1; `entire-report.txt:40-78` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 36, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `dafny verify /app/solution.dfy` exits 0 | `test_verifies` | covered | `instruction.md:3`; `test_outputs.py:106-114` |
| Frozen spec (predicates, signature, requires/ensures) | `test_spec_frozen` | covered | `instruction.md:5`; `test_outputs.py:117-125` |
| No `assume`, `{:axiom}`, `{:verify false}`, `{:extern}` | `test_no_escape_hatch` | covered | `instruction.md:5`; `test_outputs.py:128-142` |
| Sorted + multiset postconditions (via verifier) | `test_verifies`, `test_behavioral` | covered | `instruction.md:3`; `test_outputs.py` |
| Empty array completes | `test_empty_array` | covered | implied by general correctness; `test_outputs.py:167-201` |
| Real termination measures (not `decreases *` in sort body) | `test_no_decreases_star` | covered | `instruction.md:5` “termination measures”; `test_outputs.py:221-231` |
| No ghost-copy reward hack | `test_no_ghost_copy` | **phantom / unfair** | Not in `instruction.md`; flags `ghost var` + scaffold `new int` |
| No vacuous `ensures true` | `test_no_escape_hatch` | covered (implicit quality) | `test_outputs.py:140-142` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #27, spec alignment, blocker 1 |
| `tests/test_outputs.py` | Blocker 1, #27, #55, spec alignment |
| `environment/solution.dfy` | Blocker 1 (`new int` in Main) |
| `solution/solution_correct.dfy` | #23, oracle path (no `ghost var`) |
| `tests/test.sh` | #20, #24 |
| `environment/Dockerfile` | #15, #20, validation note |
| `task.toml` | #45, #46-49 N/A, metadata |
| `entire-report.txt` | Agent stats, rubric, external adjudication |
| `solution/solve.sh` | #21-23 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: dafny-insertion-sort-multiset-sorted/ ===
ERROR: dockerfile [environment/Dockerfile]: Must not COPY solution/ into image
```

False positive: `COPY solution.dfy` matches `\bsolution\b` in `validate_task.py:407-408`. Copying the starter file from `environment/` is required and correct.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0% (0/5) | All runs 6/7 tests; `test_no_ghost_copy` only failure per export |
| terminus-claude-opus-4-8 | 100% (5/5) | Likely avoided `ghost var` or used oracle-style lemma pattern |
| oracle | 100% (3/3 export; 1/1 local) | Passes all tests including `test_no_ghost_copy` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (GPT-5.5) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `dafny-insertion-sort-multiset-sorted`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Clear, concise; gap only on unstated ghost-copy rule |
| 2 Environment | ☑ | Pinned base, tmux/asciinema, Dafny 4.9.0 sha256, offline runtime |
| 3 Oracle | ☑ | Passes Harbor oracle locally |
| 4 Verifiers | ☑ | Blocker: `test_no_ghost_copy` unfair heuristic |
| 5 Metadata | ☑ | category/tags/languages consistent |
| 6 Rubric | ☑ | Platform rubric valid; `# Rubric 1` optional for non-milestone; #36 phrasing note |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency fail confirmed; difficulty stats reconciled |
| 8 Novelty & fairness | ☑ | Strong anti-cheat except ghost-copy false positive |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid formal-verification task — the frozen spec hash, Dafny verifier as oracle, escape-hatch checks, and behavioral harnesses are all well thought out, and the reference proof passes cleanly.

One fix before we can accept: `test_no_ghost_copy` currently fails any solution that contains both `ghost var` and `new int` anywhere in the file. The starter `Main()` already uses `new int`, so agents writing a standard `ghost var pre := a[..]` snapshot proof get rejected even though the instructions never ban that pattern. Please narrow the check to the actual cheat (e.g. `ghost var … := new int[…]`, or exclude `Main()`), or document the constraint explicitly in the instructions.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | no | — |
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
| Rubric | no (Medium #36 note only) | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
