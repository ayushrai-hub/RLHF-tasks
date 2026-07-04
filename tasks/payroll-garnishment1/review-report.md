# Terminus Review Report: `payroll-garnishment1`

**Generated:** 2026-07-03 19:40 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/payroll-garnishment1`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 1 false-positive pip warning) |
| **Oracle** | not executed (Harbor local job config error) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** none

**Decision (concise):** Strong three-milestone Go payroll/garnishment task with correct milestone layout, digest-pinned Dockerfile, offline tests, and a properly segmented platform rubric. ChatGPT’s “Needs Revision” call is not supported: difficulty metadata mismatch and missing root-level timeouts are explicitly non-blockers (and root-level timeouts would violate milestone `task.toml` rules). No real High-severity blockers found in artifacts.

**Insights (concise):**

- `number_of_milestones = 3` with `steps/milestone_N/` layout, per-step timeouts, and `# Rubric 1/2/3` blocks — correct milestone format (not a flat non-milestone rubric).
- Per-block rubric positives: 19 / 34 / 29 — all ≤40; total 82 is expected for 3 milestones and is not capped at 40.
- Worst-model pass rate 60% (Opus 3/5) → medium tier; not too easy (#54 passes).
- `task.toml` `difficulty = "hard"` vs platform `MEDIUM` is informational only — never blocks (#45 still CHECK).
- Milestone 2 instruction is dense (~2076 words) but specifies testable financial behavior (WHAT), not implementation steps (HOW); LLMaJ instruction sufficiency PASS.
- `__pycache__` artifact cited by ChatGPT is absent from the task tree.
- Oracle not run locally; solve scripts build full Go implementations algorithmically.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Difficulty metadata should align: change `hard` → `medium` (ChatGPT Medium) | **Disagree** (not a blocker) | `prompt.md:477-484`, `docs/reviewer-checklist-ui.md:81-85` — declared vs platform/agent tier mismatch never blocks; #45 CHECK when field present. `task.toml:6` `difficulty = "hard"`; `entire-report.txt:16` platform `MEDIUM`. |
| 2 | Add root-level `[agent]` / `[verifier]` timeout fallbacks (ChatGPT Medium; Harbor WARNING) | **Disagree** | `docs/guidelines/milestones.md:99` — milestone tasks must use per-step `[steps.agent]` / `[steps.verifier]` and **no** top-level `[agent]`/`[verifier]`. `task.toml:24-49` already has three `[[steps]]` with timeouts. |
| 3 | Remove committed `steps/milestone_2/tests/__pycache__/` (ChatGPT Low; Harbor SUGGESTION) | **Disagree** (stale) | Glob search returns 0 `__pycache__` files under `payroll-garnishment1/`; only `environment/.dockerignore:3` ignores them. |
| 4 | Milestone layout correct; `allow_internet = false`; digest-pinned FROM; rubric blocks separated (ChatGPT) | **Agree** | `task.toml:9,17`; `environment/Dockerfile:1`; `entire-report.txt:531-573` three `# Rubric N` headers. |
| 5 | Non-canonical Go base image may need justification (Harbor WARNING) | **Disagree** (not a blocker) | `environment/Dockerfile:1` digest-pinned `golang:1.24-bookworm@sha256:…`; Go compile task requires Go base; digest pinning satisfied (#15). |
| 6 | Platform rubric positive total 82 > 40 is a blocker | **Disagree** | Milestone task: cap is **per `# Rubric N` block** ≤40 (`docs/guidelines/rubrics.md:31-33`). Blocks: 19, 34, 29 — all pass. |
| 7 | Non-milestone task incorrectly uses milestone rubric format | **Disagree** (wrong premise) | `task.toml:9` `number_of_milestones = 3`; platform rubric correctly uses `# Rubric 1`, `# Rubric 2`, `# Rubric 3` (`entire-report.txt:531-573`). Flat rubric would be wrong here. |
| 8 | Instruction sufficiency / spec gaps drive agent failures | **Disagree** | `entire-report.txt:133` “None”; failures from `child_support` vs `child-support` agent bug (`entire-report.txt:125`) and M3 patch failure (`entire-report.txt:127`), not untested requirements. |
| 9 | M1 missing `--kind` / fractional cap tests (TEST QUALITY) | **Partially agree** (not a blocker) | Gaps noted `entire-report.txt:344-400`; severity Minor — “does not enable a meaningful shortcut.” |
| 10 | Automated audit #1 instruction too long (2771 words summed) | **Disagree** (not a blocker) | Per-milestone: M1=306w, M2=2076w, M3=389w. M2 is dense algorithmic spec without step-by-step HOW; LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:148`). |
| 11 | Automated audit #14 unpinned pip | **Disagree** (false positive) | `environment/Dockerfile:13-15` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` — pinned with `==`. |
| 12 | Automated audit #27 phantom numeric thresholds | **Disagree** | Values like 57954/64488 are discriminator pins from reference engine (`test_m2.py:660-662`); 9750/10000 derive from instruction floor math (`instruction.md:25-27`, `test_m2.py:838-839`); 70000 is sample-variance trap vs population spec (`instruction.md:33`, `test_m2.py:1000-1007`). |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Milestone-scoped: M1/M3 concise; M2 is long but necessary algorithmic WHAT-spec, not step-by-step HOW | `steps/milestone_*/instruction.md` word counts |
| 2 | CHECK | Natural prompt tone | Conversational prose; no spec-doc tables | `audit-report.md:28` PASS |
| 3 | CHECK | No excessive markdown | No heavy markdown | `audit-report.md:29` |
| 4 | CHECK | No step-by-step dev instructions | Describes behavior/algorithms, not coding steps | `steps/milestone_2/instruction.md` |
| 5 | CHECK | No hints/solving strategies | No walkthrough hints in env or instruction | `environment/pay-app/*.go` stubs only |
| 6 | CHECK | No design-doc tables | None | — |
| 7 | CHECK | Well specified | Clear CLI commands, cents, error words, formulas | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Interesting | Real payroll/garnishment domain with coupled solvers | — |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against full TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | Absolute paths | `/app/pay`, `/app/data/pay.db` | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No task name string | — |
| 12 | CHECK | No canary string | None detected | — |
| 13 | CHECK | No runtime web fetch | `allow_internet = false` | `task.toml:17` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:13-15` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | No env context outside environment/ | COPY only `pay-app` | `environment/Dockerfile:17` |
| 17 | CHECK | No solution/ground truth in env | Stubs return `not_implemented`; CONVENTIONS generic | `environment/pay-app/*.go` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:13-15`, `steps/milestone_*/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Harbor `ValueError: Either datasets or tasks must be provided`) | solve scripts algorithmic |
| 22 | CHECK | Oracle no internet | No network in solve scripts | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle reflective | Builds Go source with algorithms | `steps/milestone_2/solution/solve2.sh` |
| 24 | CHECK | test.sh writes reward.txt on pass/fail | Canonical block present | `steps/milestone_1/tests/test.sh:1-11` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0/1 reward.txt | `steps/milestone_*/tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | LLMaJ PASS; discriminators trace to spec formulas | `entire-report.txt:148-149` |
| 28 | CHECK | Tests check correctness | Reference engine + literal pins | `test_m2.py` |
| 29 | CHECK | Behavior not implementation grep | CLI integration tests | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 30 | CHECK | No brittle over-matching | Exact error words specified in instruction | `steps/milestone_1/instruction.md:3-9` |
| 31 | CHECK | Informative test names/docstrings | All `test_*` have docstrings | `audit-report.md:57` |
| 32 | CHECK | ≥3 negative rubric criteria | 15 negatives across 3 blocks | `entire-report.txt:539-573` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All compliant | `entire-report.txt:531-573` |
| 34 | CHECK | Agent …, ±N format | 39 Agent lines | `entire-report.txt:531-573` |
| 35 | CHECK | Rubric detailed; positive cap | Per-block 19/34/29 ≤40 | `entire-report.txt:531-573` |
| 36 | CHECK | Positive rubric language | No positive-score “does not” phrasing | `entire-report.txt:531-573` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:531-573` |
| 38 | CHECK | Rubric no metadata/instruction refs | Clean | `entire-report.txt:531-573` |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | `entire-report.txt:531-573` |
| 40 | CHECK | Required files present | Milestone layout with env/Dockerfile, steps/* | `payroll-garnishment1/` tree |
| 41 | CHECK | No unnecessary parent files | Task root has only `task.toml`, `environment/`, `steps/` | glob |
| 42 | CHECK | author_name/email present | `anonymous` / `anonymous` | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, tags, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags/category applicable | `data-processing` + `db_interaction` defensible for payroll CLI + SQLite; `software-engineering` also reasonable | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform MEDIUM — mismatch not a failure | `task.toml:6`, `entire-report.txt:16` |
| 46 | CHECK | steps/ milestone layout | No root instruction/tests/solution | `steps/milestone_{1,2,3}/` |
| 47 | CHECK | solveN.sh per milestone | solve1/2/3.sh + wrappers | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/m2/m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone tests scoped | `TestMilestone1/2/3` classes | `test_m1.py:62`, `test_m2.py:537`, `test_m3.py:152` |
| 50 | CHECK | Tests not in image | Dockerfile COPY only pay-app | `environment/Dockerfile:17` |
| 51 | CHECK | No accessible ground truth | Stubs + no solution COPY | `environment/pay-app/` |
| 52 | CHECK | Agent cannot trivially cheat | Discriminator tests pin naive shortcuts | `test_m2.py:660-672` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:20-22` |
| 55 | CHECK | Not too hard/unfair | Agent failures are implementation bugs, not spec gaps | `entire-report.txt:110-133` |

### Quick copy-paste

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| M1 CRUD, error words, sort orders | `TestMilestone1::*` | covered | `test_m1.py` |
| M1 missing `--kind` → bad_input | (no dedicated test) | gap (minor) | `entire-report.txt:344-370` |
| M2 progressive tax, half-even, CCPA pool | `test_net_*`, `test_net_round_half_even_tax_tie` | covered | `test_m2.py` |
| M2 coupled target-gross bisection | `test_target_gross_differs_from_both_naive` | covered | `test_m2.py:660-672` |
| M2 delinquency promotion + reset | `test_project_delinquency_promotion_differs_from_static`, `test_project_mid_horizon_reset_differs_from_fixed_pool` | covered | `test_m2.py` |
| M2 stats conventions (nearest-rank, population var, half-even mean) | `test_stats_nearest_rank_and_population_variance` | covered | `test_m2.py:1000-1007` |
| M2 kind percents `child-support`/`tax-levy` | Reference + allocate tests use hyphens | covered | `test_m2.py:41`, `instruction.md:15` |
| M3 HMAC audit chain, precedence | `test_seq_gap_precedence`, `test_external_*` | covered | `test_m3.py` |
| M3 remit gross-up per order | `test_remit_grossup_per_order` | covered | `test_m3.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, #46, milestone metadata |
| `environment/Dockerfile` | #14, #15, #20 |
| `steps/milestone_1/instruction.md` | M1 spec, #10 |
| `steps/milestone_2/instruction.md` | M2 financial spec |
| `steps/milestone_3/instruction.md` | M3 audit spec |
| `steps/milestone_*/tests/test_mN.py` | #27-31, #49 |
| `steps/milestone_*/tests/test.sh` | #24-26 |
| `steps/milestone_*/solution/solveN.sh` | #22-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats |
| `docs/guidelines/milestones.md` | Root-timeout adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate payroll-garnishment1/
Summary: 0 error(s), 1 warning(s) — pip warning is false positive (packages are == pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | — |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model |
| oracle | 100.0% (3/3) | per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

### Rubric positive points (milestone)

| Block | Positive pts | Cap | Status |
|-------|-------------|-----|--------|
| # Rubric 1 | 19 | 40 | PASS |
| # Rubric 2 | 34 | 40 | PASS |
| # Rubric 3 | 29 | 40 | PASS |
| Total (3 milestones) | 82 | 30–120 expected | PASS |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `payroll-garnishment1` matches `entire-report.txt` payroll garnishment domain |
| 1 Instruction | ☑ | M2 dense but complete; no answer leakage |
| 2 Environment | ☑ | Digest-pinned Go base; tmux+asciinema; pytest in image |
| 3 Oracle | ☐ | Not run locally; static review PASS |
| 4 Verifiers | ☑ | reward.txt canonical; no runtime installs |
| 5 Metadata | ☑ | Milestone task.toml correct; no root agent/verifier (correct) |
| 6 Rubric | ☑ | Three `# Rubric N` blocks; per-block caps pass |
| 7 LLMaJ & agents | ☑ | All quality checks PASS; 60% worst-model |
| 8 Novelty & fairness | ☑ | Discriminator anti-cheat design strong |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the three-milestone structure, coupled financial discriminators, and HMAC audit chain are all well thought out. Dockerfile is digest-pinned, verifier deps are baked in, and the platform rubric is correctly split into three milestone blocks with sensible negatives. Agent pass rates look right for medium difficulty, and failures trace to implementation mistakes (like normalizing kind names to underscores), not missing spec. I didn’t find any blockers; optional polish only if you want to align `difficulty` to medium for metadata consistency (not required for acceptance).

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
