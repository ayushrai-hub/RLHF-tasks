# Terminus Review Report: band-localizing

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (report: 100% 3/3; local run blocked — Docker socket) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** The statistical-planning core, sealed hidden-truth verifier, Dockerfile, and rubric (23/40 pts) are solid. One real High blocker: prose maps the rationed cheap bench to “lab’s split-Hopkinson bar” and the unlimited expensive bench to “outside dynamic-test house,” while `house_shots`/`cost_house` are cheap+capped and `lab_shots`/`cost_lab` are expensive+unlimited — confirmed by tests and oracle. This naming inversion explains 7/8 agent bar-capacity failures. Instruction length (~869 words, 6+ prose blocks) also fails the concise-prompt rule but is secondary to the functional spec gap.

**Insights (concise):**

- ChatGPT naming claim is **confirmed** with file evidence; Harbor export instruction-sufficiency analysis agrees (6/8 `task_specification: fail`).
- `# Rubric 1` header on a non-milestone task is **allowed** per `docs/guidelines/rubrics.md` — not a blocker.
- Automated audit **false positives**: #14 (pip packages are `==`-pinned) and #41 (`audit-report.md` is reviewer output, not a submission artifact).
- Rubric positive total 23/40; 4 distinct negatives — passes cap and penalty rules.
- Worst-model 0% (Claude Opus 4.8); GPT-5.5 40% — appropriate hard tier; not too easy (#54 passes).
- Oracle implements full empirical-Bayes + greedy `house_shots`-first allocation matching verifier semantics (`solution/solve.sh:130-139`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues; Instruction Styling | #7, #27, #55 | Resource column names contradict prose and verifier semantics. Prose: lab split-Hopkinson bar = cheap + rationed (`bar_capacity`); outside dynamic-test house = expensive + unlimited. Data/tests: `cost_house` < `cost_lab` (e.g. A01 2.482 vs 6.89); `test_bar_capacity_respected` sums `house_shots`; oracle fills cheap capped bar into `house_shots`. Agents reading prose naturally map `lab_shots` → rationed bar → 7/8 bar-capacity failures (1015–1050 vs cap 900). | `instruction.md:11`; `alloys.csv:1`; `tests/test_outputs.py:95-99`; `tests/costs.json:3-4`; `solution/solve.sh:130-139`; `entire-report.txt:53-78` | Explicitly state in `instruction.md` that `house_shots` = in-house split-Hopkinson bar (cheap, capped at `bar_capacity`) and `lab_shots` = outside dynamic-test house (expensive, uncapped), **or** rename columns/costs/tests so prose and verifier agree. |
| 2 | High | Instruction Styling | #1 | Instruction exceeds concise limit: 6 blank-line prose blocks, ~869 words vs 1–3 paragraphs / ~150–200 words target. | `instruction.md` (full file); `docs/guidelines/prompt-styling.md:7-8` | Trim to ≤3 paragraphs while preserving requirements, or split non-normative narrative from measurable requirements without a spec-file loophole. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Resource naming contradicts verifier: prose says lab bar is cheap/capped but `house_shots` is capped and `cost_house` is cheaper (ChatGPT High) | **Agree** | `instruction.md:11` vs `alloys.csv:1-2` vs `tests/test_outputs.py:95-99` vs `solution/solve.sh:130-139` |
| 2 | Output schema, hidden-truth anti-cheat, budget/capacity checks, rubric otherwise coherent (ChatGPT Medium none) | **Agree** | Sealed `held_out_truth.json`/`threshold.json`/`costs.json`; `test_worst_of_array_band_floor_met`; rubric 23 pts, 4 negatives in `entire-report.txt:294-306` |
| 3 | Optional: add example sentence for house/lab/cost/bar_capacity interaction (ChatGPT Low) | **Agree** (Low, non-blocking) | Would reduce ambiguity after blocker #1 fix |
| 4 | Optional: make KPI types explicit (ChatGPT Low) | **Partially agree** (Low) | `instruction.md:13-22` implies types; `test_kpis_consistent_with_plan` uses `_as_int` — explicit typing would help edge cases only |
| 5 | Dockerfile digest pinning appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` |
| 6 | Instruction sufficiency FAIL — naming drives bar-capacity failures (entire-report) | **Agree** | `entire-report.txt:53-78`, `test_bar_capacity_respected: 3/10 pass` |
| 7 | Harbor REVIEW REPORT: READY TO USE (entire-report) | **Disagree** on readiness | Harbor report did not catch naming inversion; artifact evidence overrides |
| 8 | LLMaJ `behavior_in_task_description` PASS (entire-report) | **Partially agree** | Behaviors are *described* but `house_shots`/`lab_shots` bench mapping is not — creates alignment gap #27 |
| 9 | Automated audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:14-17` pins `numpy==2.3.1`, `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 10 | Automated audit #41 stray `audit-report.md` | **Disagree** as task blocker | File is reviewer-generated output, not part of task zip |
| 11 | Non-milestone task uses `# Rubric 1` milestone header format (user query) | **Disagree** as blocker | `task.toml:13` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:66` — `# Rubric 1` optional for non-milestone; no `# Rubric 2+` present |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~869 words, 6+ prose blocks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Literary engineering narrative, not synthetic spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No `##` headers, tables, or bold blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No command walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Domain conservatism requirements, not algorithm steps | `instruction.md:9` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | `house_shots`/`lab_shots` bench mapping ambiguous vs prose | `instruction.md:11,13` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Genuine statistical planning under uncertainty | `instruction.md` |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Not verified against full corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/data/...`, `/app/output` | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No `band-localizing` string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | COPY data only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | All pip deps `==`-pinned | `environment/Dockerfile:14-17` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY data/ only | `environment/Dockerfile:20` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No truth rates in image; only agent-visible inputs | `environment/data/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest/numpy in image; test.sh runs pytest only | `environment/Dockerfile`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report: oracle 100% (3/3) | `entire-report.txt:26` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Stdlib + numpy only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full beta-binomial + allocation logic | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block | `tests/test.sh:5-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | Tests cap `house_shots`; prose describes lab bar as capped resource without column mapping | `instruction.md:11`, `tests/test_outputs.py:95-99` |
| 28 | CHECK | Tests check for correctness, not just format | Held-out floor, capacity, cost ceiling | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Outcome-based on plan outputs | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Tolerances on cost (0.5) and prob (5e-3) | `tests/test_outputs.py:165-176` |
| 31 | CHECK | Tests have informative names or docstrings | All 8 tests documented | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives | `entire-report.txt:303-306` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All ±1,3,5 | `entire-report.txt:294-306` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 12 Agent lines | `entire-report.txt:294-306` |
| 35 | CHECK | Rubric criteria are detailed and precise | 23 positive pts ≤40 cap | `entire-report.txt:294-306` |
| 36 | CHECK | Rubric criteria use positive language | Penalties phrased as actions taken | `entire-report.txt:303-306` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:294-306` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:294-306` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:294-306` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Task folder clean (audit-report is reviewer artifact) | task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:6-7` |
| 43 | CHECK | All other required metadata fields present | category, difficulty, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | scientific-computing, python, estimation | `task.toml` |
| 45 | CHECK | Difficulty matches observed agent pass rates | declared hard; worst-model 0% | `task.toml:8`, `entire-report.txt:20-22` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — non-milestone | `task.toml:13` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:13` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:13` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:13` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Truth only in `/tests/` at grade time | `tests/held_out_truth.json` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Grading uses sealed verifier fixtures | `tests/test_outputs.py:16-27` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% | `entire-report.txt:20-22` |
| 55 | UNCHECK | Task is not too hard or unfair | Naming inversion makes correct mapping unavailable from prose alone | `instruction.md:11`, `entire-report.txt:53-78` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 7, 9, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/shot_plan.csv` with header `alloy_id,house_shots,lab_shots,adopted_rate` | `test_plan_file_exists_and_parses` | covered | `instruction.md:13`, `tests/test_outputs.py:64-70` |
| Exactly 40 alloys A01–A40, one row each | `test_plan_has_exactly_one_row_per_alloy` | covered | `instruction.md:3,13`, `tests/test_outputs.py:73-84` |
| Non-negative integer shot counts | `test_all_alloys_covered_with_nonneg_integers` | covered | `instruction.md:13`, `tests/test_outputs.py:87-92` |
| `adopted_rate` within `rate_min`–`rate_max` | `test_adopted_rates_within_declared_range` | covered | `instruction.md:13`, `tests/test_outputs.py:102-113` |
| Total cost ≤ `spend_ceiling` | `test_committed_cost_within_ceiling` | covered | `instruction.md:11`, `tests/test_outputs.py:116-123` |
| Lab split-Hopkinson bar shots ≤ `bar_capacity` (rationed cheap bench) | `test_bar_capacity_respected` | **gap** | Prose: lab bar rationed (`instruction.md:11`); test caps `house_shots` (`tests/test_outputs.py:95-99`) |
| `cost_house`/`cost_lab` bill to correct bench columns | `test_committed_cost_within_ceiling` | **gap** | Prose names lab=cheap, house=expensive; data has `cost_house` < `cost_lab` |
| Worst-of-array band floor on withheld true rates | `test_worst_of_array_band_floor_met` | covered | `instruction.md:5`, `tests/test_outputs.py:126-142` |
| `kpis.json` internal consistency | `test_kpis_consistent_with_plan` | covered | `instruction.md:13-22`, `tests/test_outputs.py:145-176` |
| Conservative rates for thin-evidence alloys | `test_worst_of_array_band_floor_met` (outcome only) | covered (implicit) | No explicit quantile in instruction; graded via hidden truth |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers #1–2, #1, #7, #27, #55, spec alignment |
| `environment/data/alloys.csv` | Blocker #1 cost column semantics |
| `environment/Dockerfile` | #14, #15, #20 |
| `tests/test_outputs.py` | Blocker #1, #27, all verifier checks |
| `tests/costs.json` | Blocker #1 cost semantics |
| `tests/threshold.json` | `bar_capacity` = 900 |
| `solution/solve.sh` | Oracle maps cheap bar → `house_shots` |
| `task.toml` | #45, milestone N/A #46–49 |
| `entire-report.txt` | Agent stats, rubric #32–39, instruction sufficiency |
| `tests/test.sh` | #24, #20 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate band-localizing/
Summary: 0 error(s), 2 warning(s), 3 info
Task type detected: regular
```

Warnings: long_context info (subcategory empty — N/A); pip pin heuristic false alarm (packages are pinned).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | 3 failures on bar cap + floor |
| terminus-claude-opus-4-8 | 0.0% (0/5) | All failed bar cap + floor |
| oracle | 100.0% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test pass rates (`entire-report.txt:33-41`): `test_bar_capacity_respected` 3/10; `test_worst_of_array_band_floor_met` 3/10 — systematic, consistent with naming blocker.

### Rubric

| Field | Value |
|-------|-------|
| Positive point total | 23 |
| Cap | 40 |
| Status | PASS |
| `# Rubric 1` only | Allowed for non-milestone (`rubrics.md:66`) |
| Negatives | 4 (≥3 required) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `band-localizing`, regular task, scientific-computing |
| 1 Instruction | ☐ | Naming gap + length exceed |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, deps baked |
| 3 Oracle | ☑ | Full implementation; 100% per report |
| 4 Verifiers | ☑ | 8 behavior tests, sealed fixtures, reward path |
| 5 Metadata | ☑ | hard, python, number_of_milestones=0 |
| 6 Rubric | ☑ | 23/40 pts; `# Rubric 1` optional; not milestone format violation |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency naming claim verified |
| 8 Novelty & fairness | ☐ | Fairness impacted by naming (#55) |
| 9 Long context | N/A | No long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the held-out truth design, sealed grading constants, and constrained optimization setup are well thought out, and the Dockerfile and verifier suite are in great shape. The one thing blocking acceptance is a naming mismatch: the prose describes the lab’s split-Hopkinson bar as the cheap, rationed bench and the outside dynamic-test house as the expensive unlimited one, but the output columns and costs do the opposite (`house_shots` is cheap and capped, `lab_shots` is expensive). That’s likely why most runs blew past the 900-shot bar cap. Please add an explicit mapping in the instruction (or rename the columns to match the prose) so agents know which column is which bench. Trimming the instruction length would also help, but fixing the house/lab mapping is the priority.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
