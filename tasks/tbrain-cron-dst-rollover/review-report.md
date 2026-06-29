# Terminus Review Report: `tbrain-cron-dst-rollover`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Go DST debugging task — digest-pinned env, independent reference verifier, rubric at 39/40, flat non-milestone rubric format, and difficulty calibration look right. One real blocker: fall-back overlap wording in `instruction.md` contradicts the per-query “strictly after” rule tested when a query sits between the two repeated occurrences; five near-miss agent runs failed that sub-case. Automated script false-positives on #10 (`go build ./...`) and #20 (pytest via `requirements.lock`) were overturned on manual audit.

**Insights (concise):**

- ChatGPT High-severity fall-back claim is **confirmed** with file/line proof; it is the only disposition blocker.
- Platform rubric is **flat** (no `# Rubric 2+` headers) — correct for `number_of_milestones = 0`; positive total **39 ≤ 40**.
- `#20` automated fail is wrong: `environment/requirements.lock` installs `pytest==8.3.4` in Dockerfile lines 19–22.
- `#10` automated fail is wrong: `go build ./...` is Go package-glob syntax from `/app`, not a relative artifact path.
- `test_far_from_transitions_batch` lacks a docstring (#31 UNCHECK) — minor, not a disposition driver.
- Oracle not run locally; `solve.sh` applies `fix.patch` and rebuilds — static review passes #22–#23.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Fall-back overlap rule is ambiguous: instruction says the job “must fire at the first (earlier) of the two occurrences” without stating that per-query semantics apply — a query **between** the two occurrences must return the **second** (standard-time) occurrence, not always the earlier one. | `instruction.md:5` (“first (earlier) of the two occurrences”); `instruction.md:3` (“strictly after the query instant”); `tests/test_outputs.py:202-226` (`qs = [FALL - 3600, FALL - 1000]`; `assert want[1] == later`); `entire-report.txt:48` (`test_fall_overlap_fires_at_first_occurrence`: 4/10); `entire-report.txt:60-64` (five 10/11 trials failed this sub-case) | Clarify fall-back per-query semantics in `instruction.md`: when the query is before both occurrences return the earlier (daylight) one; when the query is after the first but before the second return the later (standard) one on the same local day. Optional worked example with three query positions. |

*No other disposition blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Fall-back overlap rule needs clarification; verifier expects second occurrence when query is between the two (ChatGPT High) | **Agree** | `instruction.md:5`; `tests/test_outputs.py:213-225`; agent stats `entire-report.txt:48,60-64` |
| 2 | Test suite is strong with independent reference (ChatGPT Medium/Low) | **Agree** | `tests/test_outputs.py:46-110` reference; 11 behavioral tests in Groups A–C |
| 3 | Optional worked fall-back example would help (ChatGPT Low) | **Agree** | Same gap as claim 1; not required for Accept but recommended with blocker fix |
| 4 | Dockerfile digest-pinned Go base — no base-image blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:1a6d4452…` |
| 5 | Decision: Needs Revision (ChatGPT) | **Agree** | Blocker 1 confirmed |
| 6 | Instruction sufficiency FAIL on fall-back between-query case (entire-report LLMaJ) | **Agree** | `entire-report.txt:51,77-78` corroborated by artifact cross-check |
| 7 | `behavior_in_task_description` PASS (entire-report LLMaJ) | **Partially agree** | Global strict-after rule is present (`instruction.md:3,5`) but fall-specific sentence creates contradictory reading for between-query case |
| 8 | Non-canonical base image warning (Harbor review report) | **Disagree as blocker** | Digest-pinned ECR `golang:1.24-bookworm`; acceptable when no canonical Go image exists (`entire-report.txt:144-162`) |
| 9 | Missing `set -e` in test.sh (Harbor review report) | **Disagree as blocker** | Low robustness note; `tests/test.sh:2` captures pytest exit code explicitly |
| 10 | `#10` relative paths blocker (automated review) | **Disagree** | Only hit is `go build ./...` at `instruction.md:9` — Go idiom from `/app`, not a relative file path |
| 11 | `#20` pytest not in Dockerfile (automated review) | **Disagree** | `environment/Dockerfile:19-22` + `environment/requirements.lock:7-8` install pytest at image build |
| 12 | Non-milestone task in milestone rubric format (user query) | **Disagree** | `task.toml:9` `number_of_milestones = 0`; platform rubric `entire-report.txt:282-302` is flat `Agent …, ±N` with no `# Rubric 2+` headers — correct per `docs/guidelines/rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Five prose paragraphs; long but within debugging-task norm | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Operator bug-report tone, not synthetic spec | `instruction.md:7-9` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | No solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes symptoms and contract, not patch steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | CLI, directives, DST rules, and bug symptoms defined | `instruction.md:1-9` |
| 8 | CHECK | Instruction is interesting | Real DST/cron scheduling debugging | — |
| 9 | CHECK | Instruction is unique | DST wall-clock resolver with sign-error + transition logic | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app` absolute; `go build ./...` is Go package glob, not a relative artifact path | `instruction.md:9` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder-name leak | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Only apt/pip at build | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Hash-locked `requirements.lock` | `environment/requirements.lock` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY scoped to `environment/` | `environment/Dockerfile:29` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Only buggy `repo/` sources | `environment/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest via `requirements.lock` in image; `test.sh` only runs pytest | `environment/Dockerfile:19-22`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed — Docker permission denied locally | oracle run 2026-06-29 |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` applies patch + `go build` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Patch rewrites `NextFire` + `FromLocal` | `solution/fix.patch` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:4-18` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | Binary 0/1 | `tests/test.sh:14-17` |
| 27 | UNCHECK | All tests are aligned with instructions | Fall-back between-query behavior tested but not clearly stated in instruction | Blocker 1 |
| 28 | CHECK | Tests check for correctness, not just format | Independent `expected_fire` reference | `tests/test_outputs.py:64-110` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs binary stdout only | `tests/test_outputs.py:127-143` |
| 30 | CHECK | No brittle exact string matching | Numeric UTC-second comparison via reference | `tests/test_outputs.py` |
| 31 | UNCHECK | Tests have informative names or docstrings | `test_far_from_transitions_batch` missing docstring | `tests/test_outputs.py:255` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 8 negatives | `entire-report.txt:295-302` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:282-302` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 21 Agent lines | `entire-report.txt:282-302` |
| 35 | CHECK | Rubric criteria are detailed and precise | 39 positive pts ≤ 40 cap | `entire-report.txt:282-294` |
| 36 | CHECK | Rubric criteria use positive language | Bad-behavior lines use negative scores | `entire-report.txt:295-302` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:282-302` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:282-302` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:282-302` |
| 40 | CHECK | All required files present | Regular layout complete | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, category, tags | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | go, cron, timezone, system-administration | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard`; worst-model 0%; platform hard | `task.toml:6`, `entire-report.txt:20-26` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Only buggy starter code | `environment/repo/` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Must fix Go scheduler logic | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | `git init` of shipped repo, no clone | `environment/Dockerfile:36-40` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% | `entire-report.txt:25-26` |
| 55 | UNCHECK | Task is not too hard or unfair | Fall-back between-query semantics underspecified despite being tested | Blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 31, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Ordinary-day local↔UTC uses offset in force; sign bug visible | `test_normal_day_*`, `test_far_from_transitions_batch` | covered | `instruction.md:7-9`; `tests/test_outputs.py:159-178,255-258` |
| Spring skipped wall-clock fires at transition instant | `test_spring_gap_fires_at_transition_instant` | covered | `instruction.md:5`; `tests/test_outputs.py:185-199` |
| Fall repeated wall-clock: earlier occurrence when query before both | `test_fall_overlap_fires_at_first_occurrence` (first query) | covered | `instruction.md:5`; `tests/test_outputs.py:216-220` |
| Fall repeated wall-clock: later occurrence when query between them | `test_fall_overlap_fires_at_first_occurrence` (second query) | **gap** | `instruction.md:5` lacks per-query rule; `tests/test_outputs.py:216-225` |
| Next fire strictly after each query | all tests via `expected_fire` | covered | `instruction.md:3`; `tests/test_outputs.py:91-92` |
| Daylight offset spring ≤ utc < fall | `test_offset_chosen_correctly_each_side` | covered | `instruction.md:3`; `tests/test_outputs.py:243-248` |
| One integer per query, input order preserved | all tests | covered | `instruction.md:3`; `tests/test_outputs.py:141-143` |
| `go build ./...` from `/app` | module fixture `built` | covered | `instruction.md:9`; `tests/test_outputs.py:30-43` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker 1, #7, #10, #27, spec table |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec table |
| `tests/test.sh` | #20, #24-26 |
| `environment/Dockerfile` | #15, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `task.toml` | #44-45, #46-49 N/A |
| `solution/solve.sh`, `solution/fix.patch` | #22-23 |
| `entire-report.txt` | Agent stats, rubric #32-39, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: tbrain-cron-dst-rollover ===
Summary: 0 error(s), 2 warning(s), 2 info
Task type detected: regular
Warnings: relative-path heuristic on instruction.md; missing docstring on test_far_from_transitions_batch
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All runs failed |
| terminus-claude-opus-4-8 | 80.0% (4/5) | One 10/11 near-miss |
| oracle | 100.0% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

**Per-test:** `test_fall_overlap_fires_at_first_occurrence` 4/10 — sole systematic failure mode (`entire-report.txt:48,60-64`).

### Rubric positive points

| Field | Value |
|-------|-------|
| Positive point total | 39 |
| Cap | 40 |
| Status | PASS |
| Format | Flat non-milestone list (no `# Rubric 2+`) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular Go task; `tbrain-cron-dst-rollover` matches export |
| 1 Instruction | ☑ | One fall-back ambiguity blocker |
| 2 Environment | ☑ | Digest-pinned; pytest baked; tmux/asciinema present |
| 3 Oracle | ☐ | Not run (Docker); static review OK |
| 4 Verifiers | ☑ | Strong reference impl; one missing docstring |
| 5 Metadata | ☑ | `number_of_milestones = 0`, hard, go |
| 6 Rubric | ☑ | 39/40; flat format correct for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency fail corroborates blocker |
| 8 Novelty & fairness | ☑ | Fair after instruction fix |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid DST debugging task — the digest-pinned Go env, independent Python reference verifier, and transition-day test coverage are all in great shape, and the difficulty calibration looks right. One fix before accept: the fall-back overlap sentence in the instruction says to fire at the “first (earlier) of the two occurrences,” which reads like you always pick the earlier one. The tests (and the global strict-after-query rule) actually need per-query behavior — query before both → earlier occurrence; query between the two → the later standard-time occurrence on the same day. Please spell that out explicitly, ideally with a short worked example using three query positions around the fall transition.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no | — |
| Milestones | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`._
