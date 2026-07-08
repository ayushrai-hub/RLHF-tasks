# Terminus Review Report: `cartridge-salvaging (1)`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 3 warnings — all false positives on manual review) |
| **Oracle** | pass (platform report 3/3; local Docker daemon unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Accept. This is a well-designed statistical planning task with sealed hidden true rates, tight budget/capacity checks, and strong anti-cheating. Automated audit flagged three false positives (#4 “then runs” prose, #14 pip pins present, #41 reviewer-generated audit files). Platform rubric is valid for a non-milestone task (`# Rubric 1` only, 29 positive pts, 5 negatives). No spec↔test gaps or rubric cap violations.

**Insights (concise):**

- Core grading (`test_worst_case_recovery_floor_met`) uses `tests/held_out_truth.json` never copied into the image — agents cannot read or edit true rates.
- Cost ceiling, bench capacity, and recovery floor are graded from sealed `tests/threshold.json` / `tests/costs.json`, not agent-visible `/app/data/salvage_program.json`.
- Worst-model pass rate 0% (Claude Opus 4.8); GPT-5.5 40% — appropriately hard; not too easy (#54).
- Platform rubric: 29/40 positive points, 5 distinct negatives; `# Rubric 1` header alone is allowed on non-milestone tasks per `docs/guidelines/submission-export-format.md`.
- `category = scientific-computing` fits primary activity (numpy statistical estimation + constrained optimization).
- Optional polish only: JSON template for `kpis.json` in instruction (Low); explicit oracle Python error message (Low).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

**Automated false positives overturned on manual review:**

| Automated claim | Verdict | Proof |
|-----------------|---------|-------|
| #4 step-by-step hints | **Disagree** | `instruction.md:2` — “the plan **then runs** exactly as written” matches regex `then,?\\s+(run|…)` but is narrative prose, not a developer step (“then run …”). No run/edit/create/install directives. |
| #14 unpinned pip | **Disagree** | `environment/Dockerfile:12-15` — `numpy==2.3.1`, `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` all `==`-pinned. Auditor matched multiline `RUN` header only. |
| #41 stray parent files | **Disagree** | `audit-report.md` / `review-report.md` are reviewer-tool outputs, not author submission artifacts. Task zip contains only standard Terminus layout (13 files). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High severity blockers (ChatGPT) | **Agree** | Full artifact audit — no untested requirements, no answer leakage, no rubric >40, no runtime test installs. |
| 2 | No Medium severity blockers (ChatGPT) | **Agree** | Spec↔tests aligned; rubric valid; category appropriate. |
| 3 | Optional JSON template for kpis.json (ChatGPT / Harbor review) | **Agree** | `instruction.md:27-31` names all five fields and types in prose; structured example would improve readability only (Low). |
| 4 | Optional clearer oracle Python error message (ChatGPT / Harbor review) | **Agree** | `solution/solve.sh:97` — `set -euo pipefail` already fails fast; cosmetic only (Low). |
| 5 | Dockerfile digest-pinned (ChatGPT) | **Agree** | `environment/Dockerfile:1` — `@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb` |
| 6 | Rubric 29 pts, 5 negatives, shape OK (ChatGPT) | **Agree** | `entire-report.txt:263-279`; `./scripts/terminus rubric-points` → 29/40 PASS; `rubric-validate --milestones 0` → 0 errors. |
| 7 | Accept disposition (ChatGPT) | **Agree** | Artifacts support Accept after false-positive overturn. |
| 8 | Non-milestone task uses milestone rubric format | **Disagree** (not a blocker) | `task.toml:13` `number_of_milestones = 0`; rubric has only `# Rubric 1` (no `# Rubric 2+`). Per `docs/guidelines/submission-export-format.md:63` — “optional single `# Rubric 1` only” on non-milestone tasks. Mismatch would require multiple `# Rubric N` blocks without milestones. |
| 9 | LLMaJ `behavior_in_task_description` PASS | **Agree** | All seven test behaviors named in `instruction.md` (outputs, schema, capacity, ceiling, floor, formula). |
| 10 | LLMaJ `behavior_in_tests` PASS | **Agree** | Each instruction requirement mapped in §5 below. |
| 11 | LLMaJ `anti_cheating_measures` PASS | **Agree** | `environment/Dockerfile:17` copies only `data/`; truth in `tests/held_out_truth.json`. |
| 12 | Instruction sufficiency PASS (agent failures = calibration) | **Agree** | `entire-report.txt:41-63` — 6/7 tests pass all trials; sole failure `test_worst_case_recovery_floor_met` from sparse-log overconfidence, not missing spec. |
| 13 | Category mismatch → debugging (automated audit #44) | **Disagree** | `task.toml:9` `scientific-computing` — primary work is numpy WLS estimation + constrained pass allocation (`docs/task-type-taxonomy.md:17`). “Failing cartridges” is scenario framing, not debugging code. |
| 14 | Oracle 100% (platform report) | **Agree** (not re-run locally) | `entire-report.txt:25` oracle 3/3; local `./scripts/terminus oracle` blocked (Docker daemon unavailable). `solution/solve.sh` performs genuine computation, not hardcoded outputs. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 prose paragraphs, ~425 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as engineering scenario, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | “then runs” is narrative; no run/edit/create steps | `instruction.md:2` |
| 5 | CHECK | No solving-strategy hints | Describes WHAT (outputs, constraints, caution); not HOW (no algorithm steps) | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, absolute paths, measurable outputs | `instruction.md` |
| 8 | CHECK | Interesting | Realistic digital-preservation / salvage planning scenario | `instruction.md` |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3 index from artifacts alone | — |
| 10 | CHECK | Absolute paths only | `/app/data/...`, `/app/output/...` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No “cartridge-salvaging” string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline task; `allow_internet = false` | `task.toml:34`, `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned with == | All three packages `==`-pinned | `environment/Dockerfile:12-15` |
| 15 | CHECK | Base image digest-pinned | FROM with @sha256 | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY data only | `environment/Dockerfile:17` |
| 17 | CHECK | No ground truth in env | True rates only in `tests/held_out_truth.json` | `tests/held_out_truth.json`, `environment/Dockerfile:17` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose Harbor mounts OK | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest/numpy in Dockerfile; test.sh no installs | `environment/Dockerfile:12-15`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform 3/3; deterministic numpy solution | `entire-report.txt:25`, `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | WLS regression + greedy bench allocation, not echo | `solution/solve.sh:8-94` |
| 24 | CHECK | reward.txt canonical block | Writes 0 default, 1/0 after pytest | `tests/test.sh:5-20` |
| 25 | CHECK | Same verifier logic | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:16-19` |
| 27 | CHECK | Tests aligned with instructions | Full mapping §5; 40-cartridge count stated as “forty” / T01–T40 | `instruction.md:1`, `test_outputs.py:75-77` |
| 28 | CHECK | Tests check correctness | Hidden-rate floor, cost ceiling, capacity — not format-only | `test_outputs.py:95-121` |
| 29 | CHECK | Behavior not implementation | No source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Header/column names are instruction-specified | `instruction.md:26-27`, `test_outputs.py:63` |
| 31 | CHECK | Informative test docstrings | All 7 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives | `entire-report.txt:275-279` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All scores valid | `entire-report.txt:264-279` |
| 34 | CHECK | Rubric Agent format | 16 properly formatted lines | `entire-report.txt:264-279` |
| 35 | CHECK | Rubric detailed; pts in cap | 29 positive pts ≤40 | `rubric-points` output |
| 36 | CHECK | Positive phrasing | Bad behaviors use negative scores (-5, -3, -2) | `entire-report.txt:275-279` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:264-279` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:264-279` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:264-279` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No jobs/, README, stray author files | task root (reviewer reports excluded) |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, languages | `task.toml` |
| 44 | CHECK | Tags/category applicable | scientific-computing + estimation/optimization tags match | `task.toml:9,19` |
| 45 | CHECK | Difficulty field present | `hard`; platform `hard`; worst-model 0% → hard tier | `task.toml:8`, `entire-report.txt:15-21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:13` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:13` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:13` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | tests/ and solution/ not in image | `environment/Dockerfile:17` |
| 52 | CHECK | Agent cannot trivially cheat | Grading uses sealed `tests/*.json`; editing `/app/data` ineffective | `tests/test_outputs.py:5-27` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:19-21` |
| 55 | CHECK | Not unfair / too hard | Agents pass 6/7 tests; failure is estimation calibration, not missing info | `entire-report.txt:32-39,41-63` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Write `/app/output/recovery_plan.csv` with `cartridge_id`, `bench_passes`, `lab_passes` | `test_plan_file_exists_and_parses` | covered | `instruction.md:26-27`, `test_outputs.py:57-63` |
| Exactly 40 cartridges T01–T40, one row each | `test_plan_has_exactly_one_row_per_cartridge` | covered | `instruction.md:1`, `test_outputs.py:66-77` |
| Non-negative integer pass counts | `test_all_cartridges_covered_with_nonneg_integers` | covered | `instruction.md:27`, `test_outputs.py:80-85` |
| Bench total ≤ `bench_capacity` (900) | `test_bench_capacity_respected` | covered | `instruction.md:20-21`, `test_outputs.py:88-92` |
| Committed cost ≤ `cost_ceiling` | `test_committed_cost_within_ceiling` | covered | `instruction.md:21-22`, `test_outputs.py:95-102` |
| Recovery model `1-(1-p)^n`; weakest cartridge ≥ `recovery_floor` | `test_worst_case_recovery_floor_met` | covered | `instruction.md:4-6,13-14`, `test_outputs.py:105-121` |
| Write `/app/output/kpis.json` with five specified fields | `test_kpis_consistent_with_plan` | covered | `instruction.md:27-31`, `test_outputs.py:124-148` |
| KPI integers exact; cost consistent; worst prob in [0,1] | `test_kpis_consistent_with_plan` | covered | `test_outputs.py:132-144` |
| Constants from `salvage_program.json` (agent-visible) | — | N/A (grading uses sealed copies) | `instruction.md:24-25`; sealed `tests/threshold.json` |
| Use only shipped Python/numpy | — | untestable | `instruction.md:31` — honor system; not verifier scope |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, §5 spec alignment |
| `task.toml` | #13, #42-45, #46-49 N/A |
| `environment/Dockerfile` | #14-15, #20, #50-51 |
| `environment/data/salvage_program.json` | §5 constants (agent-visible) |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #25-31, §5, anti-cheat |
| `tests/held_out_truth.json` | #17, #51-52 |
| `tests/threshold.json`, `tests/costs.json` | Sealed grading constants |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, §3 adjudication, §7 agent stats, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: cartridge-salvaging (1) ===
Summary: 0 error(s), 3 warning(s), 3 info
Warnings (all false positives on manual review):
  - long_context: subcategories=[] — spurious (not tagged long_context)
  - pinned_dependencies: pip IS ==-pinned in Dockerfile:12-15
  - solution-hints: "then runs" narrative matched hint regex — not a real hint
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Best reference agent |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Worst reference agent |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test: `test_worst_case_recovery_floor_met` 2/10 — sole discriminator; all others 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `cartridge-salvaging (1)` matches `entire-report.txt` cartridge-salvage domain |
| 1 Instruction | ☑ | Concise, absolute paths, no hints; kpis schema in prose (optional JSON template = Low) |
| 2 Environment | ☑ | Digest-pinned base; tmux+asciinema; pip ==-pinned; no tests/solution COPY |
| 3 Oracle | ☑ | Genuine WLS + allocation; platform 3/3 (local Docker unavailable) |
| 4 Verifiers | ☑ | Canonical reward block; 7 behavior tests; sealed grading fixtures |
| 5 Metadata | ☑ | scientific-computing appropriate; hard; non-milestone |
| 6 Rubric | ☑ | 29/40 pts; 5 negatives; `# Rubric 1` only OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; failures = estimation calibration |
| 8 Novelty & fairness | ☑ | Multi-step statistical reasoning; cheating paths closed |
| 9 Long context | N/A | `subcategories = []` |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The instructions are clear about the output contract, the recovery formula, and the need to be conservative with sparse log evidence. The environment is well set up — digest-pinned base, verifier deps baked in, and the held-out true rates plus sealed cost/capacity constants mean agents can’t cheat by editing visible data. Tests cover schema, all forty cartridges, capacity, cost ceiling, and the hidden worst-case recovery floor. Oracle passes on platform runs and agent rates look right for hard difficulty. I didn’t find any blocking spec gaps, rubric issues, or environment problems. Optional polish: a small JSON template for `kpis.json` would make the schema even easier to scan.

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

---

*Manual accuracy review per `prompt.md`. Automated baseline from `./scripts/terminus validate`, `audit`, `review`.*
