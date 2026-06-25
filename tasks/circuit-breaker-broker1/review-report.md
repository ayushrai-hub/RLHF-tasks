# Terminus Review Report: `circuit-breaker-broker1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (not executed locally; 100% per `entire-report.txt`) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Test Alignment/Coverage Issues, Oracle Solution Issues, Rubric

**Decision (concise):** Milestone structure, digest-pinned Rust Dockerfile, offline vendored build, and Hard difficulty calibration (worst-model 20%) are solid. Blockers are a confirmed M1 oracle/spec mismatch on `/api/admin/advance` auto-recovery, multiple High-severity spec↔test gaps that let incomplete state-machine, audit, and alert behavior pass, and platform rubrics with zero negative penalties (≥3 required).

**Insights (concise):**

- `SPEC.md` and M1 instruction both require OPEN→HALF-OPEN on advance; all three oracle `advance` handlers only bump `now_us` (`solve1.sh:115-131`, `solve2.sh:131-147`, `solve3.sh:187-204`).
- M1 tests conflate advance recovery with `/api/check` (`test_m1.py:109-121`); no test asserts OPEN-report 503 or HALF-OPEN failure→OPEN despite spec/instruction requiring both.
- M2 omits FIFO 1000-row eviction test; composite denial omits `retry_after_us` (`test_m2.py:77-88`).
- M3 integrity checks SHA-256 length only (`test_m3.py:30`); severity is set-membership only (`test_m3.py:85`); JSON-null threshold clearing is specified but untested.
- Agent failures are mostly dirty clock state at verify time (7/9 trials), not spec ambiguity; task is hard but fair (#55 passes).
- Automated script false positives on #14/#20/#22/#31 overturned: `requirements.lock` hash-pins pytest; Dockerfile installs verifier deps; oracle builds `--offline`; every test method has a docstring.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Oracle Solution Issues, Test Alignment/Coverage Issues | #23, #27 | M1 oracle `advance` omits OPEN→HALF-OPEN sweep required by SPEC/instruction; tests never catch it | `environment/spec/SPEC.md:15-16`; `steps/milestone_1/instruction.md:3`; `solve1.sh:115-131` (only updates `now_us`); same pattern `solve2.sh:131-147`, `solve3.sh:187-204` | Add breaker sweep after clock advance in all milestone oracles **or** remove requirement from SPEC/instruction; add test that GETs breaker state after advance without calling `/api/check` |
| 2 | High | Test Alignment/Coverage Issues | #27, #28 | OPEN-state `POST /api/breakers/report` must return HTTP 503 with `circuit open` body — untested | `environment/spec/SPEC.md:35-36`; no matching test in `steps/milestone_1/tests/test_m1.py` | Add test: trip breaker to OPEN, report again, assert 503 + `error`/`state`/`retry_after_us` |
| 3 | High | Test Alignment/Coverage Issues | #27, #28 | HALF-OPEN failure must reopen circuit — only success path tested | `steps/milestone_1/instruction.md:3` ("failed report reopens it"); `environment/spec/SPEC.md:37-39`; `test_half_open_recovery` only tests success (`test_m1.py:123-133`) | Add test: HALF-OPEN breaker, `success: false`, assert state OPEN |
| 4 | High | Test Alignment/Coverage Issues | #27, #28 | M2 FIFO 1000-row audit cap never exercised | `steps/milestone_2/instruction.md:5`; `environment/spec/SPEC.md:75`; no test generates >1000 rows in `test_m2.py` | Add test inserting >1000 audit rows, assert cap and oldest eviction |
| 5 | High | Test Alignment/Coverage Issues | #28 | M2 composite denial omits `retry_after_us` validation | `environment/spec/SPEC.md:67`; `test_m2.py:86-88` asserts only `allowed` and `denied_by` | Assert `retry_after_us` present and typed per spec |
| 6 | High | Test Alignment/Coverage Issues | #28 | M3 integrity SHA-256 checked for length only, not correctness | `environment/spec/SPEC.md:88`; `steps/milestone_3/instruction.md:3`; `test_m3.py:30` | Compare `sha256` to independently computed hash of canonical file JSON |
| 7 | High | Test Alignment/Coverage Issues | #28 | M3 alert severity formula not verified | `environment/spec/SPEC.md:115`; `test_m3.py:85` (`in ("low","medium","high","critical")`) | Assert severity from margin formula using `denial_count` and `threshold` |
| 8 | High | Test Alignment/Coverage Issues | #27, #28 | M3 JSON-null threshold clearing specified but untested | `steps/milestone_3/instruction.md:5`; `environment/spec/SPEC.md:100`; `test_alert_threshold_registration` only sets positive count (`test_m3.py:34-47`) | POST with `max_denial_count: null`, assert echo null and threshold removed |
| 9 | High | Rubric | #32 | Platform rubrics have zero negative penalties (≥3 required) | `entire-report.txt:785-814` — all criteria use +1/+2/+3/+5 only | Add ≥3 negative criteria across milestone rubric blocks per `docs/guidelines/rubrics.md` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M1 spec/oracle/test mismatch: `/api/admin/advance` must apply OPEN→HALF-OPEN but oracle only updates `now_us`; tests don't verify via GET after advance (ChatGPT) | **Agree** | `SPEC.md:15-16`; `solve1.sh:127-131`; `test_m1.py:113-121` calls `/api/check` after advance |
| 2 | M1 does not test OPEN report 503 (ChatGPT) | **Agree** | `SPEC.md:35-36`; absent from `test_m1.py` |
| 3 | M1 does not test HALF-OPEN failure reopening (ChatGPT) | **Agree** | `instruction.md:3`; `SPEC.md:37-39`; only `test_half_open_recovery` success path |
| 4 | M2 does not test 1000-row FIFO audit cap (ChatGPT) | **Agree** | `instruction.md:5`; `SPEC.md:75`; no eviction test in `test_m2.py` |
| 5 | M2 does not test `retry_after_us` in composite denial (ChatGPT) | **Agree** | `SPEC.md:67`; `test_m2.py:86-88` |
| 6 | M3 SHA-256 shape only, not correctness (ChatGPT) | **Agree** | `test_m3.py:30` |
| 7 | M3 alert severity formula not verified (ChatGPT) | **Agree** | `SPEC.md:115`; `test_m3.py:85` |
| 8 | M3 JSON-null threshold clearing untested (ChatGPT) | **Agree** | `instruction.md:5`; `SPEC.md:100`; `test_m3.py:34-47` |
| 9 | Milestone structure, Dockerfile, offline build, Hard calibration solid (ChatGPT) | **Agree** | `task.toml:6-9`; `Dockerfile:1,32-49`; `entire-report.txt:1-7` worst-model 20% |
| 10 | LLMaJ `behavior_in_tests` fail — multiple spec behaviors untested (`entire-report.txt`) | **Agree** | Same gaps as rows 1–8 above |
| 11 | Harbor warning: M1 oracle omits advance auto-recovery (`entire-report.txt:172-206`) | **Agree** | `solve1.sh:115-131` |
| 12 | Test quality: `last_state_change_us` never validated on registration (`entire-report.txt:383-413`) | **Partially agree** | `SPEC.md:24`; `test_m1.py:44-50` omits field; Medium gap, not standalone blocker |
| 13 | Chart.js test only checks substring not `<script>` tag (`entire-report.txt:591-612`) | **Partially agree** | `test_m2.py:131`; Low/Medium — instruction requires script tag |
| 14 | `count == len(audit)` invariant weakly tested (`entire-report.txt:119`) | **Partially agree** | `SPEC.md:73`; `test_m2.py:122` uses `count <= 2` only |
| 15 | M3 GET `/api/alerts` filter/sort untested (`entire-report.txt:119`) | **Agree** | `SPEC.md:117-118`; no filter test in `test_m3.py` |
| 16 | Atomic temp-file+rename persistence untested (`entire-report.txt:756-781`) | **Partially agree** | `instruction.md:3`; functional persist tested `test_m3.py:9-22`; implementation mechanism untestable without instrumentation — Low |
| 17 | Automated review blockers #14, #20, #22, #31 (`review` script) | **Disagree** | `#14`: `requirements.lock:15-16` pytest `==8.4.1` + hashes; `#20`: `Dockerfile:28-29` installs lock, `test.sh:21-22` no pip; `#22`: `solve1.sh:297-298` `cargo build --offline`; `#31`: every `test_*` has docstring in all three test files |
| 18 | Agent clock dirty-state failures indicate instruction spec gap (`entire-report.txt:91-94`) | **Disagree** | Spec states clock starts at 0 (`SPEC.md:13`); operational agent error, not missing requirement |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone instruction is one dense paragraph | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Task brief tone; normative detail delegated to SPEC | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No heavy markdown in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States deliverables (build, PID file), not solve walkthrough | `steps/milestone_1/instruction.md:1` |
| 5 | CHECK | No hints or solving strategies | WHAT not HOW; SPEC is normative reference | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instructions | — |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Clear milestone scopes + `/app/spec/SPEC.md` | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic resilience/broker service | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Multi-milestone Rust circuit-breaker broker; no duplicate observed in review | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app`, `/app/spec/SPEC.md`, `/app/state/state.json` | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No "circuit-breaker-broker1" string | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only; vendored Rust | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Hash-locked `requirements.lock` with `==` versions | `environment/requirements.lock:15-16` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY limited to `environment/` paths | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | SPEC is normative API contract, not walkthrough | `environment/spec/SPEC.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest installed in image; test.sh only runs pytest | `environment/Dockerfile:28-29`; `steps/milestone_1/tests/test.sh:21-22` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | 100% oracle pass rate reported | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `cargo build --release --offline` | `solve1.sh:297-298` |
| 23 | UNCHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | `advance` handler incomplete vs SPEC auto-recovery requirement | `solve1.sh:115-131`; `SPEC.md:15-16` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block present | `steps/milestone_1/tests/test.sh:4-29` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 reward | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Multiple instruction/SPEC requirements lack tests (blockers 2–8) | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 28 | UNCHECK | Tests check for correctness, not just format | SHA-256 length, severity set-membership, missing branches | `test_m3.py:30,85`; `test_m2.py:86-88` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | HTTP API behavior tests only | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Reasonable JSON field assertions | `steps/milestone_*/tests/test_m*.py` |
| 31 | CHECK | Tests have informative names or docstrings | Every test method has docstring | `test_m1.py:6-136`, `test_m2.py:6-131`, `test_m3.py:9-162` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Zero negatives in submitted rubrics | `entire-report.txt:785-814` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores are +1/+2/+3/+5 | `entire-report.txt:785-814` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format matches | `entire-report.txt:786-813` |
| 35 | CHECK | Rubric criteria are detailed and precise | Criteria describe concrete agent behaviors | `entire-report.txt:785-814` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Positive phrasing with positive scores | `entire-report.txt:785-814` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No test references | `entire-report.txt:785-814` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:785-814` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP refs | `entire-report.txt:785-814` |
| 40 | CHECK | All required files present | Milestone layout: env, steps, task.toml | `circuit-breaker-broker1/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, steps, env | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | rust/axum/circuit-breaker; system-administration | `task.toml:7-18` |
| 45 | CHECK | Difficulty matches observed agent pass rates | declared hard; worst-model 20% → hard tier | `task.toml:6`; `entire-report.txt:1-7` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `task.toml:30-53` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1/2/3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1/2/3.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | M1 simple only; M2 sliding/audit; M3 persistence/alerts | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Only spec/ copied | `environment/Dockerfile:53` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Live server API verification | `steps/milestone_*/tests/test_m*.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% | `entire-report.txt:6-7` |
| 55 | CHECK | Task is not too hard or unfair | Failures are operational (dirty clock) or logic bugs, not missing env info | `entire-report.txt:65-114` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 23, 27, 28, 32 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `GET /api/health` → `{"status":"ok"}` | `test_health` | covered | `test_m1.py:6-10` |
| Clock starts at 0; advance adds micros; 400 on negative | `test_now_clock`, `test_advance_clock` | covered | `test_m1.py:12-31` |
| Simple breaker registration 201/409/400 | `test_breaker_registration` | covered | `test_m1.py:33-59` |
| GET breaker 404 | `test_breaker_lookup` | covered | `test_m1.py:61-68` |
| CLOSED failure count → OPEN at threshold | `test_breaker_failure_reporting` | covered | `test_m1.py:70-96` |
| OPEN check denied + `retry_after_us` | `test_check_open_breaker` | covered | `test_m1.py:98-107` |
| OPEN→HALF-OPEN after timeout on check | `test_check_half_open_auto_transition` | covered | `test_m1.py:109-121` |
| OPEN→HALF-OPEN after timeout on **advance** (without check) | — | **gap** | `SPEC.md:15-16`; test uses `/api/check` after advance |
| HALF-OPEN success → CLOSED | `test_half_open_recovery` | covered | `test_m1.py:123-133` |
| HALF-OPEN failure → OPEN | — | **gap** | `SPEC.md:37-39`; `instruction.md:3` |
| OPEN report → HTTP 503 `circuit open` | — | **gap** | `SPEC.md:35-36` |
| Dashboard canvas IDs | `test_index_dashboard` | covered | `test_m1.py:135-142` |
| `last_state_change_us` on registration echo | — | **gap** | `SPEC.md:24`; `test_m1.py:44-50` |
| Sliding registration + reject `recovery_timeout_us` | `test_create_sliding_breaker` | covered | `test_m2.py:6-26` |
| Sliding window failure counting / expiry | `test_sliding_window_transition` | covered | `test_m2.py:28-47` |
| Sliding OPEN→HALF-OPEN recovery | `test_sliding_window_auto_recovery` | covered | `test_m2.py:49-57` |
| Composite allow/deny | `test_composite_check_success`, `test_composite_check_denied` | covered | `test_m2.py:59-88` |
| Composite denial `retry_after_us` | — | **gap** | `SPEC.md:67`; `test_m2.py:86-88` |
| Audit row fields + filters | `test_audit_*` | covered | `test_m2.py:90-125` |
| FIFO cap 1000 rows | — | **gap** | `SPEC.md:75`; `instruction.md:5` |
| `count == len(audit)` | `test_audit_limit` | **gap** | `test_m2.py:122` only `count <= 2` |
| Chart.js script tag | `test_chartjs_script_tag` | partial | `test_m2.py:131` substring only |
| Persist `/app/state/state.json` | `test_state_persistence_file` | covered | `test_m3.py:9-22` |
| Integrity SHA-256 of canonical JSON | `test_integrity_endpoint` | **gap** | `test_m3.py:30` length only |
| Alert threshold register/get | `test_alert_threshold_registration` | covered | `test_m3.py:34-47` |
| Threshold clear via JSON null | — | **gap** | `instruction.md:5`; `SPEC.md:100` |
| Alert firing (>threshold, ≥30 rows, cooldown) | `test_alert_firing_logic`, `test_alert_cooldown` | covered | `test_m3.py:49-98` |
| Severity margin formula | — | **gap** | `SPEC.md:115`; `test_m3.py:85` |
| Reload state / empty on missing file | `test_state_reload_*` | covered | `test_m3.py:110-135` |
| Schema conformance | `test_schema_conformance` | covered | `test_m3.py:137-162` |
| GET `/api/alerts` filter/sort | — | **gap** | `SPEC.md:117-118` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `environment/spec/SPEC.md` | Blockers 1–8, adjudication, spec alignment |
| `steps/milestone_1/instruction.md` | Blockers 1, 3, #7, #10 |
| `steps/milestone_2/instruction.md` | Blocker 4, #49 |
| `steps/milestone_3/instruction.md` | Blockers 6–8, #10 |
| `steps/milestone_1/solution/solve1.sh` | Blockers 1, #22, #23 |
| `steps/milestone_2/solution/solve2.sh` | Blocker 1 (advance pattern) |
| `steps/milestone_3/solution/solve3.sh` | Blocker 1 (advance pattern) |
| `steps/milestone_1/tests/test_m1.py` | Blockers 2–3, #27, #28, #31 |
| `steps/milestone_2/tests/test_m2.py` | Blockers 4–5, #27, #28 |
| `steps/milestone_3/tests/test_m3.py` | Blockers 6–8, #27, #28 |
| `environment/Dockerfile` | #14–#20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `task.toml` | #42–#46 |
| `entire-report.txt` | Agent stats, rubrics, LLMaJ, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate circuit-breaker-broker1/
Summary: 0 error(s), 5 warning(s), 3 info
Task type detected: milestone
Warnings: pip pin heuristic (false positive — hash lock used); module-level test docstrings; solution-hint heuristic on SPEC.md
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | |
| terminus-claude-opus-4-8 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) | Per external report; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `circuit-breaker-broker1` milestone Rust task; report matches folder |
| 1 Instruction | ☑ | 3 terse paragraphs + SPEC; absolute paths; no canary |
| 2 Environment | ☑ | Digest-pinned Rust base; tmux+asciinema; offline vendor; pytest baked in |
| 3 Oracle | ☑ | Full Rust compile; advance auto-recovery missing vs spec |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; major coverage gaps |
| 5 Metadata | ☑ | hard, 3 milestones, rust, api_integration |
| 6 Rubric | ☑ | Platform rubrics in report — zero negatives (blocker) |
| 7 LLMaJ & agent evidence | ☑ | `behavior_in_tests` fail confirmed; agent failures mostly dirty clock |
| 8 Novelty & fairness | ☑ | Multi-step Rust service; no cheat paths found |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Milestone structure, digest-pinned offline Rust environment, and Hard calibration (20% worst-model) look solid. Blockers: M1 oracle omits OPEN→HALF-OPEN auto-recovery on `/api/admin/advance` despite SPEC/instruction, and verifiers miss several required branches (OPEN report 503, HALF-OPEN failure reopen, advance-only recovery via GET, M2 FIFO 1000 cap and composite `retry_after_us`, M3 SHA-256 correctness, severity formula, JSON-null threshold clearing). Platform rubrics also need ≥3 negative penalties. Fix oracle and strengthen tests before resubmit.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 2, 3, 4, 5, 6, 7, 8 |
| Oracle Solution Issues | yes | 1 |
| Rubric | yes | 9 |
| Milestones | yes | 1 (oracle scoped per milestone) |
