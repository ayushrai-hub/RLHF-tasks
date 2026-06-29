# Terminus Review Report: payroll-garnishment

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (report: 100% 3/3) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Environment

**Decision (concise):** Strong three-milestone Go payroll/garnishment task with excellent integer-arithmetic verifiers, coupled bisection discriminators, and correct milestone rubric layout (three `# Rubric N` blocks, each ≤40 positive pts). Two real High blockers: (1) `project` final-period arrears compounding is tested but ambiguous in the instruction — systematic agent failures on three project tests; (2) starter scaffold references undefined `Period` type and will not compile. Rubric format, pip pinning, and per-milestone timeouts are not blockers.

**Insights (concise):**

- Milestone rubric format is correct: `# Rubric 1/2/3` with +19/+26/+29 pts per block (all ≤40 cap); not a flat non-milestone list.
- ChatGPT arrears-compounding claim verified: reference engine and oracle compound after every period including the last; instruction says "before the next period opens."
- ChatGPT `Period` type claim verified: `employees.go:42` returns `[]Period`; no `Period` in `model.go`; dead code not in CLI or tests.
- Automated `#14` pip-unpinned flag is a false positive — `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are `==`-pinned in `environment/Dockerfile:14-15`.
- Missing root `[agent]`/`[verifier]` in `task.toml` is expected for milestone tasks per `docs/task-requirements.md:107`.
- Agent stats: GPT-5.5 0%, Claude Opus 4.8 60% — appropriately hard; not too easy.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | `project` final-period arrears compounding ambiguous: instruction says compounding happens "before the next period opens," but tests/oracle compound unmet arrears after the final simulated period before reporting `final_arrears`. Multiple agents independently skipped final-period compounding (`3602` expected vs `3558` actual). | `steps/milestone_2/instruction.md:25` ("before the next period opens"); `steps/milestone_2/tests/test_m2.py:295-302` (compounds inside loop every iteration, returns `arr[k]`); `steps/milestone_2/tests/test_m2.py:771-774` (pinned `final_arrears=3602`); `steps/milestone_2/solution/solve2.sh:423-437`; `entire-report.txt:86-88,114-124,140-144` | Add one explicit sentence, e.g.: "Arrears from the final simulated period are also compounded by 125 bps (round half to even) before being reported as `final_arrears`." |
| 2 | High | Environment | #55 | Starter scaffold does not compile: `ListPeriods` returns `[]Period` but `Period` is undefined anywhere in the package. Dead `AddPeriod`/`ListPeriods` stubs are not referenced by CLI, instructions, or tests. | `environment/pay-app/employees.go:34-45`; `environment/pay-app/model.go:1-39` (no `Period`); grep shows no CLI wiring in `main.go`/`cli.go` | Add a minimal `Period` struct stub to `model.go`, or remove the unused `AddPeriod`/`ListPeriods` functions from `employees.go`. |

*No other High/Medium blockers found after re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Final-period arrears must compound before `final_arrears` is printed; instruction ambiguous (ChatGPT High) | **Agree** | `instruction.md:25` vs `test_m2.py:295-302,771-774`; agent failure pattern in `entire-report.txt:114-124` |
| 2 | Starter scaffold fails compile due to undefined `Period` type (ChatGPT High / Harbor WARNING) | **Agree** | `employees.go:42`; `model.go` lacks `Period`; functions unused by spec |
| 3 | Missing root `[agent]`/`[verifier]` in task.toml (Harbor WARNING) | **Disagree** (not a blocker) | `task.toml:24-49` has per-step timeouts; `docs/task-requirements.md:107` says milestone tasks use per-milestone sections, no top-level agent/verifier |
| 4 | Optional M1 tests for empty `--kind` and fractional `--mandatory` (ChatGPT Low / test quality) | **Agree** (Low only) | `steps/milestone_1/instruction.md:7`; no matching tests in `test_m1.py` — minor gap, not revision-blocking |
| 5 | Optional M3 audit test with second employee (ChatGPT Low) | **Agree** (Low only) | `entire-report.txt:538-569`; all M3 audit tests use employee id 1 — theoretical hardcode path, not blocking |
| 6 | Rubric positive total 74 exceeds 40 (automated review) | **Disagree** (not a blocker) | Milestone task: cap is **per `# Rubric N` block** — `#1=19`, `#2=26`, `#3=29`, all ≤40 (`entire-report.txt:576-614`; `docs/guidelines/rubrics.md:31-33`) |
| 7 | Milestone rubric format check (user query) | **Pass** | Three `# Rubric N` headers with scoped criteria; correct milestone format, not a flat non-milestone list |
| 8 | Instruction sufficiency FAIL on project compounding (entire-report LLMaJ) | **Partially agree** | Spec gap is real and drives Revise; other M2 behaviors are well-specified and tested |
| 9 | `#14` unpinned pip (automated review) | **Disagree** | `environment/Dockerfile:14-15` uses `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` |
| 10 | `#36` rubric negative phrasing (automated review) | **Disagree** | `"fails to verify"` appears only on a `-5` penalty line (`entire-report.txt:611`); acceptable per rubric negative-penalty convention |
| 11 | `#1` instruction too long — 2396 words combined (automated review) | **Partially agree** (not main blocker) | M2 alone is dense spec prose; warranted for financial precision; M1/M3 are concise; not revision-driving vs the two High blockers |
| 12 | `#31` 60 tests missing docstrings (automated review) | **Disagree** (not a blocker) | Checkbox allows informative names **or** docstrings; names like `test_project_floor_arrears_and_split` are descriptive; M2 KEY tests have docstrings |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | M2 instruction alone is ~7 dense paragraphs (~1700 words); exceeds 3-paragraph cap even though complexity warrants detail | `steps/milestone_2/instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | M2 reads as algorithmic spec (brackets, bisection bounds, allocation rules) rather than conversational prompt | `steps/milestone_2/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no heavy markdown | all `instruction.md` files |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No dev workflow steps (edit file X, run Y) | all `instruction.md` files |
| 5 | CHECK | No hints or solving strategies | Specifies required behavior/algorithms, not oracle walkthrough | all `instruction.md` files |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables | all `instruction.md` files |
| 7 | CHECK | Instruction is well specified | Every tested behavior has explicit numeric rules and output formats | all `instruction.md` files |
| 8 | CHECK | Instruction is interesting | Real payroll/garnishment domain with non-trivial algorithms | task content |
| 9 | UNCHECK | Instruction is unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/pay`, `/app/data/pay.db` | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No "payroll-garnishment" string | all `instruction.md` files |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | all `instruction.md` files |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch; `GOPROXY=off` | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Both pip packages `==`-pinned | `environment/Dockerfile:14-15` |
| 15 | CHECK | Base Docker image is pinned by digest | `FROM ...@sha256:1a6d4452...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | Only `COPY pay-app /app` | `environment/Dockerfile:17` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No answer leakage in env files | `environment/pay-app/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:13-15`, `steps/milestone_*/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3); not re-run locally | `entire-report.txt:24` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `GOPROXY=off`; solve scripts write Go source locally | `environment/Dockerfile:29`, `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle is reflective of instruction | solveN.sh builds full Go implementations via computation | `steps/milestone_2/solution/solve2.sh` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block in all milestone test.sh | `steps/milestone_1/tests/test.sh:1-11` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only | 0/1 reward pattern | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | Phantom requirement: final-period compounding tested but not clearly specified | Blocker #1 |
| 28 | CHECK | Tests check for correctness, not just format | Reference engines pin exact cent values | `steps/milestone_2/tests/test_m2.py` |
| 29 | CHECK | Tests verify behavior, not implementation | CLI stdout/exit-code assertions, no source grep | all `test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact cent pins required for financial correctness | `test_m2.py:771-774` |
| 31 | CHECK | Tests have informative names or docstrings | Descriptive test names throughout; KEY tests have docstrings | `test_m1.py`, `test_m2.py:760-766` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 12 negative lines across 3 blocks | `entire-report.txt:584-613` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores in allowed set | `entire-report.txt:576-613` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 34 Agent lines | `entire-report.txt:576-613` |
| 35 | CHECK | Rubric criteria detailed and precise | Domain-specific payroll/garnishment behaviors | `entire-report.txt:576-613` |
| 36 | CHECK | Rubric criteria use positive language | "fails to verify" only on `-5` penalty line | `entire-report.txt:611` |
| 37 | CHECK | Rubric does not reference /tests/ or pytest | No test path references | `entire-report.txt:576-613` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:576-613` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:576-613` |
| 40 | CHECK | All required files present | Milestone layout: env Dockerfile + per-step instruction/tests/solution + task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task tree |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | go, payroll, garnishment, db_interaction match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | declared hard; worst-model 0%; platform hard | `task.toml:6`, `entire-report.txt:14-20` |
| 46 | CHECK | steps/ layout present | 3 milestones under steps/ | `task.toml:9`, task tree |
| 47 | CHECK | Each milestone has solveN.sh | solve1.sh, solve2.sh, solve3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has test_mN.py | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file scoped to that milestone | TestMilestone1/2/3 classes | `test_m*.py` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | Only pay-app stub copied | `environment/Dockerfile:17` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | fresh_db fixture wipes DB; dynamic reference engine | `test_m*.py` fixtures |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy | Worst-model 0% ≤80% | `entire-report.txt:19-20` |
| 55 | UNCHECK | Task is not too hard or unfair | Final-period compounding ambiguity caused systematic M2 failures on reasonable reading; uncompilable scaffold wastes agent time | Blockers #1, #2; `entire-report.txt:86-88` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 2, 9, 27, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Progressive tax brackets + round-half-to-even | `test_net_progressive_tax_matches_reference`, `test_net_round_half_even_tax_tie` | covered | `test_m2.py` |
| CCPA pool formula (21750 floor, 200000 cap) | `test_net_pool_zero_below_30x_floor`, `test_net_pool_absolute_cap_binds` | covered | `test_m2.py` |
| Coupled target-gross bisection (not naive shortcuts) | `test_target_gross_differs_from_both_naive`, `test_pool_underfills_when_caps_bind` | covered | `test_m2.py` |
| Grouped largest-remainder allocation | `test_allocate_proportional_largest_remainder`, `test_allocate_tie_break_smaller_id` | covered | `test_m2.py` |
| Project exemption-adjusted floor | `test_project_floor_arrears_and_split` | covered | `test_m2.py:771-778` |
| **Project final-period arrears compounding** | `test_project_floor_arrears_and_split`, `test_project_matches_reference_many` | **gap** | Instruction: "before the next period opens" (`instruction.md:25`); tests compound after last period (`test_m2.py:301-302`) |
| Stats nearest-rank p75 + population variance | `test_stats_nearest_rank_and_population_variance` | covered | `test_m2.py` |
| HMAC audit chain + verify precedence | `test_audit_chain_recompute`, `test_seq_gap_precedence` | covered | `test_m3.py` |
| add-order empty/missing `--kind` → bad_input | — | gap (minor) | `instruction.md:7`; no test in `test_m1.py` |
| add-employee fractional mandatory → bad_input | — | gap (minor) | `instruction.md:5`; only mandatory>gross tested |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_2/instruction.md` | Blocker #1, #27, #55, spec alignment |
| `steps/milestone_2/tests/test_m2.py` | Blocker #1, reference engine, project pins |
| `steps/milestone_2/solution/solve2.sh` | Blocker #1 oracle behavior |
| `environment/pay-app/employees.go` | Blocker #2 |
| `environment/pay-app/model.go` | Blocker #2 |
| `environment/Dockerfile` | #14, #15, #20 |
| `task.toml` | #45, #46, milestone metadata |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, Harbor warnings |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate payroll-garnishment/
Summary: 0 error(s), 61 warning(s), 4 info
Task type detected: milestone
```

Key warnings reviewed: pip pinning (false positive — packages are `==`-pinned); missing per-test docstrings (names are descriptive); M2 instruction length (noted, not blocking).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All trials stuck at 0.667 (M1+M3 pass, M2 fail) |
| terminus-claude-opus-4-8 | 60.0% (3/5) | |
| oracle | 100.0% (3/3) | Per submission report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

**Rubric per-block positive points:**

| Block | Positive pts | Cap | Status |
|-------|-------------|-----|--------|
| # Rubric 1 | 19 | 40 | pass |
| # Rubric 2 | 26 | 40 | pass |
| # Rubric 3 | 29 | 40 | pass |

Milestone rubric format: three `# Rubric N` headers — correct for `number_of_milestones = 3`.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches entire-report; 3-milestone Go payroll/garnishment |
| 1 Instruction | ☑ | M2 arrears wording ambiguous; M1/M3 clear |
| 2 Environment | ☑ | Period compile error; Dockerfile otherwise solid |
| 3 Oracle | ☑ | solveN.sh builds from source; not re-run locally |
| 4 Verifiers | ☑ | Strong reference engines; minor M1 validation gaps only |
| 5 Metadata | ☑ | Milestone task.toml correct; per-step timeouts present |
| 6 Rubric | ☑ | Milestone format correct; all blocks ≤40 pts; ≥3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Project compounding spec gap confirmed by agent failures |
| 8 Novelty & fairness | ☑ | Arrears ambiguity + scaffold compile are fairness issues |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the three-milestone structure, integer-cent reference engines, coupled bisection discriminators, and HMAC audit chain are all excellent. The milestone rubric blocks look correctly scoped too. Two things to fix before we can accept: please clarify in the M2 instruction that unmet arrears from the **final** simulated period are also compounded (125 bps, round half to even) before being printed as `final_arrears` — several agents reasonably skipped that step because the spec says compounding happens "before the next period opens." Also, the starter scaffold won't compile because `employees.go` references a `Period` type that doesn't exist in `model.go`; either add a minimal stub or remove those unused functions so `go build` works out of the box.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Environment | yes | 2 |
| Rubric | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
