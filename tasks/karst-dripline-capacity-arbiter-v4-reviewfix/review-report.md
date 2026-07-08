# Terminus Review Report: `karst-dripline-capacity-arbiter-v4-reviewfix`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (submission export 3/3; local run blocked — Docker unavailable) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** No High or Medium blockers. Prior revision feedback (bloated instruction, hardcoded test path, rubric overshoot) is resolved in artifacts. Rubric is correctly formatted as a flat non-milestone list (20 positive pts). Pip packages are digest-pinned on continuation lines despite a false-positive auditor #14 hit. Tests are contract-aligned via instruction delegation to `DRIPLINE_CONTRACT.md`, with strong dynamic fixtures and digest anti-cheat.

**Insights (concise):**

- `instruction.md` is 130 words / 2 paragraphs and cleanly delegates all behavior to `/app/docs/DRIPLINE_CONTRACT.md` — prior 834-word inline spec issue is fixed.
- `tests/test.sh:13-14` correctly uses `TEST_DIR="${TEST_DIR:-/tests}"` — prior hardcoded `/tests` issue is fixed.
- Platform rubric is a flat `Agent …, ±N` list (no `# Rubric 2+` milestone blocks); 8 positive lines sum to **20** (≤40 cap). `# Rubric 1` header is optional for non-milestone tasks per `rubrics.md`.
- `category = "data-processing"` fits: primary activity is parsing six input files and producing a deterministic JSON audit ledger. `codebase_size = "minimal"` fits: starter code is an 18-line stub `main.go` plus fixtures; agent implements the algorithm from scratch.
- Automated #27 “phantom threshold” warning is a heuristic false positive — asserted numbers (7, 10, 15, 20, 64, 75) are fixture-derived outputs / digest length, not unstated policy rules; full spec lives in the contract doc referenced by instruction.
- Worst-model pass rate 40% (Claude Opus 4.8) → observed **medium** tier; declared `hard` vs platform `medium` is informational only, not a blocker. GPT-5.5 at 80% does not trigger #54 (worst-model rule).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High severity; Accept (Docker digest-pinned, allow_internet false, test.sh offline) | **Agree** | `environment/Dockerfile:1` `@sha256:`; `task.toml:27` `allow_internet = false`; `tests/test.sh:14` pytest only, no apt/pip |
| 2 | ChatGPT: Prior feedback resolved — concise instruction, TEST_DIR default, rubric fine | **Agree** | `instruction.md` 130 words; `tests/test.sh:13-14`; rubric +20 pts flat list in `entire-report.txt:290-302` |
| 3 | ChatGPT: Non-canonical Go base is not a blocker when digest-pinned | **Agree** | `environment/Dockerfile:1` ECR golang bookworm with full digest; Go compile requires golang image |
| 4 | ChatGPT: Task directory name generic — harmless polish | **Agree** | Folder `karst-dripline-capacity-arbiter-v4-reviewfix` is descriptive; not a review blocker |
| 5 | ChatGPT: codebase_size / model-difficulty metadata not worth sending back | **Agree** | `codebase_size = "minimal"` matches stub starter; worst-model 40% ≤80% |
| 6 | Harbor REVIEW REPORT: NEEDS REVISION — non-canonical Go base | **Disagree** (not blocker) | Digest-pinned `golang:1.24-bookworm@sha256:…`; justified for Go task |
| 7 | Harbor REVIEW REPORT: NEEDS REVISION — generic directory name `tbench-task` | **Disagree** (stale/wrong) | Local folder is `karst-dripline-capacity-arbiter-v4-reviewfix`; naming not a blocker |
| 8 | Harbor TEST QUALITY: Accept — robust dynamic fixtures + digest | **Agree** | `tests/test_outputs.py:137-247` dynamic fixture; `test_digest_is_recomputed_from_canonical_lines` |
| 9 | LLMaJ: behavior_in_task_description PASS (contract covers all behaviors) | **Agree** | `instruction.md:3` delegates to contract; `DRIPLINE_CONTRACT.md` exhaustive schema/validation/allocation/digest |
| 10 | LLMaJ: behavior_in_tests PASS — full contract coverage | **Agree** | 8 tests cover validation order, transfers, waivers, digest, CLI errors, custom paths |
| 11 | LLMaJ: anti_cheating PASS | **Agree** | `environment/.dockerignore:15-16` excludes `solution/` and `tests/`; dynamic fixtures |
| 12 | Prior Reviewer Feedback (entire-report:306): instruction 834 words — trim | **Disagree** (stale) | Current `instruction.md` is 130 words, 2 paragraphs |
| 13 | Prior Reviewer Feedback: fix test.sh hardcoded `/tests` | **Disagree** (stale — fixed) | `tests/test.sh:13-14` `TEST_DIR="${TEST_DIR:-/tests}"` |
| 14 | Prior Reviewer Feedback: confirm `# Rubric 1` header; trim positives from 38 | **Partially agree** | Positives trimmed to 20; `# Rubric 1` optional for non-milestone (`rubrics.md:66`) |
| 15 | Instruction sufficiency analysis: spec gap none; quarantine attribution is implementation bug | **Agree** | `DRIPLINE_CONTRACT.md:205` attribution rule; agent failures are logic bugs not spec gaps |
| 16 | Audit #14 FAIL: unpinned pip | **Disagree** (false positive) | `environment/Dockerfile:14-16` `pytest==8.4.1`, `pytest-json-ctrf==0.5.2` on continuation lines; auditor checks only the `pip install` line |
| 17 | Audit #27 WARN: phantom numeric thresholds | **Disagree** (false positive) | Heuristic ignores contract doc; numbers are fixture outputs (`tests/test_outputs.py:302-344`, `586-587`) |
| 18 | Validator WARN: solution-hints in contract (“then runs”) | **Disagree** | `DRIPLINE_CONTRACT.md:5` describes system behavior, not agent commands |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 130 words, 2 paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineer request, not spec dump | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal + contract pointer only | `instruction.md` |
| 5 | CHECK | No hints/solving strategies in instruction | WHAT only; normative HOW in separate contract doc (approved pattern) | `instruction.md:3` |
| 6 | CHECK | No design-doc tables in instruction | None | `instruction.md` |
| 7 | CHECK | Well specified | Clear CLI goal, paths, contract reference, error behavior | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Realistic offline audit/ledger domain | task content |
| 9 | CHECK | Unique | Karst dripline capacity arbiter with transfer/waiver ledgers appears novel | task content |
| 10 | CHECK | Absolute paths | `/app/cmd/dripline`, `/app/input`, `/app/output/dripline_report.json`, `/app/docs/DRIPLINE_CONTRACT.md` | `instruction.md:1-3` |
| 11 | CHECK | Task name not in instruction | No folder/task name string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No urlopen/curl/wget in env code | env scan |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.5.2` | `environment/Dockerfile:14-16` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | No COPY outside environment | Only `COPY app/ /app/` | `environment/Dockerfile:18` |
| 17 | CHECK | No ground-truth answers in env | Contract is normative spec; inputs are fixtures not golden output | `DRIPLINE_CONTRACT.md`, `environment/app/input/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime install | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:14-16`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per submission export | `entire-report.txt:25` |
| 22 | CHECK | Oracle needs no internet | `solve.sh` copies Go impl and runs locally | `solution/solve.sh:6-8` |
| 23 | CHECK | Oracle derives answer | ~1000-line Go implementation, not echo | `solution/dripline_solution_impl.go` |
| 24 | CHECK | test.sh reward block | Writes 0/1 to `/logs/verifier/reward.txt` on pass/fail | `tests/test.sh:4-21` |
| 25 | CHECK | Same verifier for oracle and agent | No `/oracle` branching | `tests/test_outputs.py`, `tests/test.sh` |
| 26 | CHECK | Binary reward only | 0 or 1 | `tests/test.sh:17-20` |
| 27 | CHECK | Tests aligned with instructions | Instruction delegates all behavior to contract; tests trace to contract rules | `instruction.md:3`, `DRIPLINE_CONTRACT.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness | Integration tests with computed expected outputs + digest recompute | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Runs CLI via `go run`, asserts JSON outputs | `tests/test_outputs.py:17-33` |
| 30 | CHECK | No brittle string matching | Exact asserts on structured fixture outputs and dynamic fixtures; appropriate | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 8 `test_*` functions documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives | `entire-report.txt:298-302` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines comply | `entire-report.txt:290-302` |
| 34 | CHECK | Agent …, ±N format | 13 Agent lines | `entire-report.txt:290-302` |
| 35 | CHECK | Rubric detailed; positive cap | 20 positive pts ≤40 | `./scripts/terminus rubric-points` |
| 36 | CHECK | Positive language in rubric | No “Agent does not …, +N” | `entire-report.txt:290-302` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:290-302` |
| 38 | CHECK | Rubric no instruction.md/task.toml refs | None | `entire-report.txt:290-302` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:290-302` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task tree |
| 41 | CHECK | No unnecessary parent files | Only standard task layout (+ reviewer-generated audit/review reports) | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, languages, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Go JSON/CSV allocation audit task; `data-processing` primary activity is parse/transform/aggregate input files into audit report | `task.toml:7-12`, `docs/task-type-taxonomy.md` |
| 45 | CHECK | Difficulty field present | `hard` declared; platform `medium`; worst-model 40% — informational mismatch only | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked in image | `.dockerignore:16` `tests/`; Dockerfile copies only `app/` | `environment/.dockerignore`, `environment/Dockerfile:18` |
| 51 | CHECK | Solution not in environment | `.dockerignore:15` `solution/` | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot trivially cheat | Dynamic fixtures + digest; bundled input alone insufficient; `test_oracle_does_not_require_mutating_bundled_input` uses copy | `tests/test_outputs.py:137-247,661-671` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:20-21` |
| 55 | CHECK | Not too hard/unfair | Contract fully specifies rules; agent failures are implementation bugs | `entire-report.txt:74-76`, `DRIPLINE_CONTRACT.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Finish Go CLI at `/app/cmd/dripline` with `--input` / `--output` | `test_output_path_overwrite_and_missing_parent_behavior`, `test_missing_input_directory_fails_cleanly` | covered | `instruction.md:1`; `tests/test_outputs.py:639-658` |
| Default `/app/input` → `/app/output/dripline_report.json`; custom paths honored | `test_oracle_does_not_require_mutating_bundled_input` | covered | `instruction.md:1`; `tests/test_outputs.py:661-671` |
| Missing input: nonzero exit, stderr `missing input directory`, no output file | `test_missing_input_directory_fails_cleanly` | covered | `instruction.md:3`; `tests/test_outputs.py:651-658` |
| Success: quiet stdout, create parents, overwrite output | `test_public_fixture_exercises_stateful_transfer_allocation_and_schema` | covered | `instruction.md:3`; `tests/test_outputs.py:254-255` |
| All file formats, validation order, quarantine codes | `test_dynamic_validation_short_circuit_numeric_grammar_and_unknown_chamber` | covered | `DRIPLINE_CONTRACT.md:104-118`; `tests/test_outputs.py:538-577` |
| Stateful transfer allocation, waiver ledgers, summaries | `test_public_fixture_exercises_stateful_transfer_allocation_and_schema`, `test_dynamic_fixture_uses_sparse_rank_transfer_and_waiver_ledgers` | covered | `DRIPLINE_CONTRACT.md:64-77,155-203`; `tests/test_outputs.py:250-379` |
| Transfer efficiency, statuses, unknown target | `test_transfer_efficiency_source_reservation_and_statuses` | covered | `DRIPLINE_CONTRACT.md:72-76`; `tests/test_outputs.py:594-636` |
| Chamber attribution (sensor → batch → unknown) | `test_dynamic_validation_short_circuit_numeric_grammar_and_unknown_chamber` | covered | `DRIPLINE_CONTRACT.md:205`; `tests/test_outputs.py:568-577` |
| Canonical SHA-256 digest | `test_digest_is_recomputed_from_canonical_lines` | covered | `DRIPLINE_CONTRACT.md:219-257`; `tests/test_outputs.py:580-591` |
| Top-level JSON key order and schema version | `test_public_fixture_exercises_stateful_transfer_allocation_and_schema` | covered | `DRIPLINE_CONTRACT.md:209-217`; `tests/test_outputs.py:258-269` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment, prior-feedback adjudication |
| `task.toml` | #44-45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #14-16, #20, #53 |
| `environment/.dockerignore` | #50-51 |
| `environment/app/docs/DRIPLINE_CONTRACT.md` | #17, #27, spec alignment |
| `environment/app/cmd/dripline/main.go` | #17 starter stub |
| `tests/test.sh` | #20, #24-26, prior TEST_DIR fix |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #22-23 |
| `solution/dripline_solution_impl.go` | #23 |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats, rubric, prior feedback |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate karst-dripline-capacity-arbiter-v4-reviewfix
Summary: 0 error(s), 3 warning(s), 2 info
Warnings: pip pin false-positive on line continuation; contract "then runs" behavior description; trailing exit in test.sh (non-blocking)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | 1 failure |
| terminus-claude-opus-4-8 | 40.0% (2/5) | 3 failures |
| oracle | 100.0% (3/3) | per submission export |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | no (informational only — not a blocker) |

**Rubric (platform):** 8 positive lines = **20 pts**; 5 negatives; flat non-milestone format (no `# Rubric 2+`).

**Category / codebase_size (manual):**

| Field | Value | Assessment |
|-------|-------|------------|
| `category` | `data-processing` | **Correct** — primary work is parsing CSV/JSON/NDJSON inputs and producing a deterministic aggregated audit report (ETL/ledger pipeline). `software-engineering` would also be defensible but is not required. |
| `codebase_size` | `minimal` | **Correct** — starter application code is an 18-line stub (`environment/app/cmd/dripline/main.go`); agent implements the full auditor from scratch. Contract doc and input fixtures are spec/data, not starter codebase. |
| `languages` | `["go"]` | **Correct** — agent implements Go CLI; Python is verifier-only. |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular (non-milestone) layout |
| 1 Instruction | ☑ | Concise; delegates to contract; prior bloat fixed |
| 2 Environment | ☑ | Digest-pinned Go image; tmux+asciinema; pip pinned; no solution/tests in image |
| 3 Oracle | ☑ | Real Go implementation; 100% per export (local Docker unavailable) |
| 4 Verifiers | ☑ | 8 behavior tests; dynamic fixtures; digest guard; TEST_DIR fixed |
| 5 Metadata | ☑ | category/codebase_size/languages verified |
| 6 Rubric | ☑ | Flat non-milestone format; 20 positive pts; ≥3 negatives |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; failures are implementation bugs |
| 8 Novelty & fairness | ☑ | Multi-step stateful Go implementation; cheating paths closed |
| 9 Long context | ☐ N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on the revision — this is in good shape now. The instruction is short and points cleanly to the contract doc, `test.sh` uses the proper `TEST_DIR` default, and the verifier is strong with both bundled and dynamic fixtures plus digest recomputation. The rubric is correctly formatted as a flat non-milestone list at 20 positive points. Oracle passes, NOP fails, runtime internet is off, and I don’t see any remaining spec-test gaps or acceptance blockers.

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
