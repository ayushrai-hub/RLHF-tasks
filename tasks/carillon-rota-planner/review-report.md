# Terminus Review Report: carillon-rota-planner

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3; local Docker unavailable) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Ruby constraint-optimization task — instruction, verifier, Dockerfile, and spec↔test alignment are solid; oracle passes on platform runs and worst-model rate is 40%. **Two rubric blockers** drive Revise: positive criteria sum to **42** (cap 40) and only **2** negative penalties (minimum **3**). ChatGPT’s “Accept” missed the negative-count rule; trim points and add at least one distinct negative on the platform rubric before acceptance.

**Insights (concise):**

- Instruction covers validation order, bell tiers, half-open intervals, rest gaps, minute caps, mandatory/infeasible cases, tie-breaks, and output schema — all mirrored in `expected_plan()` and 11 pytest functions.
- Platform rubric uses optional `# Rubric 1` header on a non-milestone task (`number_of_milestones = 0`) — allowed per `docs/guidelines/rubrics.md`; not a format blocker.
- Dockerfile digest-pins Ruby 3.3-slim-bookworm and bakes pytest with `==` pins; `.dockerignore` excludes `solution/` and `tests/`.
- `test_large_rota_respects_minute_caps_exactly` uses a 10s subprocess timeout — agents that pass correctness but run slowly fail; informational only, not a separate blocker.
- Author form text at top of `entire-report.txt` (database handlers / audit logs) is stale/wrong task — ignore; carillon content begins at Harbor review section.
- Non-canonical Ruby base (`public.ecr.aws/...`) is digest-pinned and justified (no canonical Ruby image in registry).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32, #35 | Platform rubric has only **2** negative criteria; minimum is **3** | `entire-report.txt:277-278` — negatives: `-2`, `-3` only | Add ≥1 more **distinct** negative penalty on platform (e.g. greedy approximation chosen over exact search, `-3`) |
| 2 | High | Rubric | #35 | Positive rubric total **42** exceeds **40** cap for non-milestone tasks | `entire-report.txt:263-276` — sum of 14 `+N` lines = 42 (3+2+5+3+2+3+3+3+5+3+3+3+2+2) | Trim **2** positive points on platform (e.g. change one `+3` → `+2`, or drop a minor `+2` verification line) |

*No other High-severity blockers found in task artifacts.*

**Not blockers (adjudicated):**

| Item | Verdict |
|------|---------|
| Only `# Rubric 1` header on non-milestone task | OK — `# Rubric 1` optional; no `# Rubric 2+` (`rubrics.md:66`) |
| ChatGPT “Accept” | Overturned — rubric negative count is a mandatory High bar |
| `#14` unpinned pip (automated script) | False positive — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` at `environment/Dockerfile:14-15` |
| Non-canonical Ruby base | Soft warning only; digest-pinned ECR mirror acceptable for Ruby |
| Bell `N/2` integer division | Low clarity; tests/solution use `tower["bells"] // 2` consistently (`test_outputs.py:96`, `solve.sh:75`) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: structurally sound, no High/Medium blockers (Accept) | **Disagree** | Rubric: 42 positive pts + only 2 negatives — both High per `rubrics.md:31-39`, `reviewer-checklist-full.md:77,85` |
| 2 | ChatGPT: rubric positive total 42, trim 2 pts (Low) | **Agree** (severity wrong) | `entire-report.txt:263-276`; **>40 = Revise blocker**, not Low |
| 3 | ChatGPT: optional bell-tier `floor(N/2)` clarity | **Agree** (Low only) | `instruction.md:7`; `test_outputs.py:96` uses `// 2` |
| 4 | ChatGPT: digest-pinned Ruby base OK | **Agree** | `environment/Dockerfile:1` |
| 5 | User: only 2 negative rubrics — blocker? | **Agree — blocker** | `entire-report.txt:277-278`; `validate_rubric.py` requires ≥3 |
| 6 | User: non-milestone in milestone rubric format | **Disagree** (not a blocker) | Single `# Rubric 1` allowed for non-milestone (`rubrics.md:66`) |
| 7 | LLMaJ: behavior_in_task_description PASS | **Agree** | Cross-checked `instruction.md` vs all 11 tests |
| 8 | LLMaJ: behavior_in_tests PASS | **Agree** | `tests/test_outputs.py` — validation order, ties, mandatory, rest, caps, empty input |
| 9 | Harbor review: non-canonical base image WARNING | **Partially agree** | `environment/Dockerfile:1` — warning only, not High |
| 10 | Harbor review: bell N/2 ambiguity WARNING | **Agree** (Low) | `instruction.md:7` |
| 11 | Test quality: no test near 45-proposal bound | **Agree** (informational) | Largest generated case ~34 proposals in `test_large_rota_respects_minute_caps_exactly`; `instruction.md:13` states 45 |
| 12 | Agent sufficiency: failures are algorithmic speed | **Agree** | `entire-report.txt:54-57`; `test_outputs.py:196` `timeout=10` |
| 13 | Platform: oracle 100% (3/3) | **Agree** | `entire-report.txt:25` |
| 14 | Platform: worst-model 40% (Claude), GPT-5.5 100% | **Agree** | `entire-report.txt:20-21`; #54 passes (≤80%) |
| 15 | Author explanations mention database/API handlers | **Disagree** (wrong task text) | `entire-report.txt:1-12` vs carillon content at lines 104+ — context only |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Four short paragraphs; dense but within norm for optimization tasks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Human engineering brief; not LLM bullet template | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT (CLI contract, rules), not implementation steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No branch-and-bound or algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Full schemas, reason strings, tie-breaks, output shape | `instruction.md:1-13` |
| 8 | CHECK | Instruction is interesting | Real scheduling/optimization problem | — |
| 9 | CHECK | Instruction is unique | Carillon rota planner not a duplicate pattern in corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/carillon-planner`, `/app/input/...`, `/app/output/...` | `instruction.md:1-3` |
| 11 | CHECK | Task name does not appear in instruction.md | No “carillon-rota-planner” string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No curl/wget of task data | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:14-15` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:e76733e9...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY only `task_file/input` | `environment/Dockerfile:19` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Public input only; no expected plan in image | `environment/Dockerfile:19`, `.dockerignore` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | venv in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:12-15`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:25` |
| 22 | CHECK | Oracle does not require internet | solve.sh writes local Ruby script only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full planner implementation, not hardcoded JSON | `solution/solve.sh:4-299` |
| 24 | CHECK | test.sh writes reward.txt; handles failure | Canonical 0/1 block | `tests/test.sh:4-19` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only (0 or 1) | reward.txt 0 or 1 | `tests/test.sh:15-18` |
| 27 | CHECK | All tests aligned with instructions | Every spec rule exercised; no phantom reqs | §5 table |
| 28 | CHECK | Tests check correctness, not just format | Reference `expected_plan()` equality | `tests/test_outputs.py:132-185`, `248-250` |
| 29 | CHECK | Tests verify behavior, not implementation | Subprocess + JSON compare; no source grep | `tests/test_outputs.py:188-202` |
| 30 | CHECK | No brittle exact string matching where flexible | Exact reason strings required by instruction | `instruction.md:7` |
| 31 | CHECK | Tests have informative names or docstrings | Module + 11 function docstrings | `tests/test_outputs.py:1`, `253-466` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Only 2 negatives | `entire-report.txt:277-278` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use ±1,2,3,5 | `entire-report.txt:263-278` |
| 34 | CHECK | Each rubric line: Agent …, ±N | 16 Agent lines | `entire-report.txt:263-278` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Positive total 42 > 40 cap | `entire-report.txt:263-276` |
| 36 | UNCHECK | Rubric criteria use positive language | One line uses “Agent fails to…” | `entire-report.txt:278` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | `entire-report.txt:263-278` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:263-278` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:263-278` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, allow_internet, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | ruby, json, planning, data-processing | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard` present; worst-model 40% → medium tier — mismatch informational only | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:14` |
| 51 | CHECK | Solution not accessible in environment | solution/ in .dockerignore | `environment/.dockerignore:13` |
| 52 | CHECK | Agent cannot trivially modify input | SHA256 guard on public input | `tests/test_outputs.py:17,258-259` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst-model 40% | `entire-report.txt:20-21` |
| 55 | CHECK | Task not too hard or unfair | Spec complete; failures are implementation efficiency | `entire-report.txt:62-77` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 35, 36, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| CLI at `/app/carillon-planner` with two path args | `test_executable_and_sample_rota_integrity` | covered | `tests/test_outputs.py:253-259` |
| Read-only public input; sample plan correctness | `test_executable_and_sample_rota_integrity`, `test_sample_rota_requires_global_choice` | covered | `tests/test_outputs.py:258-268` |
| Validation reasons in first-failure order (10 reasons) | `test_rejection_reasons_follow_rota_policy_order` | covered | `tests/test_outputs.py:271-294` |
| Bell tier rules (N/2 split) | `test_rejection_reasons_follow_rota_policy_order` (`tier`) | covered | `tests/test_outputs.py:287`, `96-99` |
| Half-open intervals | implicit in overlap helpers + rejection tests | covered | `tests/test_outputs.py:26-27` |
| scheduled/hard blocking only | rejection + variation tests | covered | `tests/test_outputs.py:104-110`, `445-465` |
| Mandatory inclusion + infeasible output | `test_conflicting_mandatory_sessions_make_rota_infeasible`, `test_mandatory_sessions_can_exceed_the_tower_cap` | covered | `tests/test_outputs.py:311-322`, `411-424` |
| 30-minute rest gap for shared ringers | `test_rest_gap_blocks_back_to_back_shared_ringers` | covered | `tests/test_outputs.py:324-333` |
| Tower/ringer minute caps on selected set | `test_minute_caps_can_outweigh_a_high_score_session`, `test_large_rota_respects_minute_caps_exactly` | covered | `tests/test_outputs.py:335-408` |
| Tie-break: score → count → minutes → lex ids | `test_tie_breaks_compare_the_complete_rota` | covered | `tests/test_outputs.py:296-308` |
| Output schema + `conflicts_with_selected` / mandatory reasons | all reference-matching tests | covered | `tests/test_outputs.py:132-185` |
| Empty arrays valid | `test_empty_input_arrays_are_valid` | covered | `tests/test_outputs.py:427-443` |
| Up to 45 proposals performance | partial — largest test ~34 proposals | gap (informational) | `instruction.md:13`, `tests/test_outputs.py:355-408` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/.dockerignore` | #50-51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39, #45, #54, agent stats, platform rubric |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate carillon-rota-planner/
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — false positive (packages are == pinned on following lines)
INFO: non-milestone preferred for new submissions
INFO: test.sh trailing exit unnecessary
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40% (2/5) | Worst model; 2 timeouts |
| oracle | 100% (3/3) | Platform runs |
| nop | 0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml:6`) |
| Platform classified | medium (`entire-report.txt:15`) |
| Tier match (#45) | informational only — not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `carillon-rota-planner`; regular task; report matches carillon content |
| 1 Instruction | ☑ | Dense but complete; absolute paths; no hints |
| 2 Environment | ☑ | Digest-pinned Ruby; tmux/asciinema; pytest venv; no tests/solution in image |
| 3 Oracle | ☑ | Full Ruby planner in solve.sh; platform 3/3 pass |
| 4 Verifiers | ☑ | 11 tests + reference solver; reward block canonical |
| 5 Metadata | ☑ | allow_internet=false; category/tags match |
| 6 Rubric | ☑ | **2 blockers:** 42 positive pts, 2 negatives; `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; failures algorithmic on large-caps test |
| 8 Novelty & fairness | ☑ | Multi-rule optimization; SHA256 anti-tamper |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong work on this one — the rota planner spec is exceptionally thorough, the Ruby CLI contract is clear, and the pytest suite with a reference solver gives solid end-to-end coverage of validation order, mandatory sessions, rest gaps, minute caps, and tie-breaks. Dockerfile and offline verifier setup look good, and agent difficulty calibration is reasonable.

Before we can accept, the platform rubric needs two fixes: trim the positive criteria total from 42 down to 40 or below (e.g. change one +3 to +2), and add at least one more distinct negative penalty — you currently have only two, and three is the minimum. Optionally rephrase the “Agent fails to make the file executable…” line to positive phrasing with a negative score.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1, 2 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
