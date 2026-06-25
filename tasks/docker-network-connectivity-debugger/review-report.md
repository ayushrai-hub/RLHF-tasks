# Terminus Review Report: `docker-network-connectivity-debugger`

**Generated:** 2026-06-21 (manual audit per `prompt.md`)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/docker-network-connectivity-debugger`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (1 error, 26 warnings — docstring warnings are false positives) |
| **Oracle** | not executed locally (Docker unavailable); report shows 100% (3/3) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Dependency Location, Task Difficulty, Metadata Issues, Instruction Styling

**Decision (concise):** Revise. The task is otherwise production-quality: canonical digest-pinned Go base, thorough 26-test verifier with golden SHA256 + independent Python reference replay, strong anti-cheating (`.dockerignore` excludes solution/tests), inline rubric with five negatives, and full spec↔test alignment per LLMaJ. Two High blockers remain: (1) `tests/test.sh` runs `pip install` at runtime though wheels are only COPY'd in the Dockerfile — Terminus requires verifier deps baked in the image; (2) `task.toml` declares `difficulty = "hard"` but worst-model pass rate is 60% (GPT-5.5), which is Medium tier per `docs/guidelines/difficulty.md`. Fix pip install first, then update difficulty to `medium` or rebalance until ≤20% on worst model.

**Insights (concise):**

- ChatGPT's **sole High finding (difficulty mismatch)** is **confirmed** — worst model GPT-5.5 at 60% ≠ declared `hard`.
- Automated script incorrectly flagged **#31** (26 missing docstrings) and **#54** (100% worst-model / too easy) — all 26 `test_*` functions have one-line docstrings; worst model is GPT **60%**, not Claude 100%.
- External report's **non-canonical base image** warning is **wrong** — `environment/Dockerfile:2` uses the exact canonical `golang:1.24-bookworm` digest from `docs/guidelines/dockerfxile.md:11`.
- External report treats runtime `pip install` as optional — Terminus treats it as **High** (`terminus-core.mdc`, `reviewer-checklist-full.md` "test.sh no network installs").
- Rubric text appended at `entire-report.txt:276-291` belongs to a **different task** (JavaScript gateway reconnect); this task's rubric is inline in `task.toml:54-73`.
- Per-test pass rates on golden/reference tests (8/10) reflect agent precision errors, not spec gaps — LLMaJ `behavior_in_task_description: pass` is supported.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | **High** | Test Dependency Location | #20 | `test.sh` installs verifier packages at runtime via `pip install` even though wheels are only COPY'd, not installed in the Dockerfile. Violates Terminus non-negotiable: verifier deps must be pre-installed in the image. | `tests/test.sh:14-17`; `environment/Dockerfile:32-33` (COPY only, no RUN pip); validate ERROR: `Runtime network install not allowed: pip\s+install` | Move the `pip install --no-index --find-links /opt/verifier/wheels --require-hashes` block to a Dockerfile `RUN` step; `test.sh` should invoke pytest only. |
| 2 | **High** | Task Difficulty, Metadata Issues | #45 | `task.toml` declares `difficulty = "hard"` but observed worst-model pass rate is 60% (GPT-5.5 3/5), which maps to **Medium** tier (20–60%). Claude at 100% does not override worst-model floor. | `task.toml:8`; `entire-report.txt:5,10-11`; `docs/guidelines/difficulty.md:7-14` | Set `difficulty = "medium"` in `task.toml`, **or** rebalance task (harder edge cases, remove clarifications) until worst-model ≤20%. |
| 3 | **Medium** | Instruction Styling | #11 | Task folder/binary name `docker-network-connectivity-debugger` appears verbatim in `instruction.md` (lines 1 and 3). | `instruction.md:1,3` — `"Repair the docker-network-connectivity-debugger program"` and executable path | Rephrase to avoid the kebab-case task folder name (e.g., "the connectivity debugger program" / "the debugger binary"). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Difficulty `hard` but evaluation is Medium; worst-model 60% GPT, 100% Claude (ChatGPT High; `entire-report.txt:5-11`) | **Agree** | `task.toml:8` `difficulty = "hard"`; `entire-report.txt:10-11` GPT 60%, Claude 100%; Medium = 20–60% worst model per `docs/guidelines/difficulty.md:10` |
| 2 | Task otherwise strong: pinning, offline deps, rubric, test/solution exclusion (ChatGPT) | **Partially agree** | Pinning, anti-cheat, rubric, spec alignment confirmed; **disagree** that runtime pip is acceptable — it is a Terminus High violation (`tests/test.sh:14-17`) |
| 3 | Optional: move verifier pip install to Dockerfile (`entire-report.txt:148-179`) | **Agree (required, not optional)** | Same as blocker #1; offline-safe wheels do not exempt runtime install per `reviewer-checklist-ui.md` item 20 note |
| 4 | Optional: trim task name from instruction (ChatGPT / `entire-report.txt:3`) | **Agree** | `instruction.md:1,3` contains `docker-network-connectivity-debugger` |
| 5 | Optional: add initial `reward.txt` write before pytest (`entire-report.txt:3`) | **Partially agree** | Low priority — `test.sh:12` mkdirs verifier dir; reward written on pytest completion (`tests/test.sh:22-26`); no `-e` but pytest failure path still writes `0`. Not blocking. |
| 6 | Non-canonical Go base image (`entire-report.txt:126-145`) | **Disagree** | `environment/Dockerfile:2` digest `sha256:1a6d4452…` matches canonical list `docs/guidelines/dockerfxile.md:11` exactly |
| 7 | 26 tests missing docstrings (automated validate/review) | **Disagree** | All 26 `test_*` in `tests/test_outputs.py:871-1121` have one-line docstrings (e.g. `:872`, `:880`, `:887`); validator AST heuristic false positive |
| 8 | Worst-model 100% / too easy / tier `trivial` (automated review §6) | **Disagree** | `entire-report.txt:10-11` worst model = GPT-5.5 **60%**, not Claude 100%; #54 passes (>80% threshold not met on worst model) |
| 9 | LLMaJ `behavior_in_task_description: pass` (`entire-report.txt:88`) | **Agree** | Instruction + `/app/docs` cover CNX1 decode, CONNECT_PROBE order, post-replay audits, schema encoding, path sandbox — all tested |
| 10 | LLMaJ `behavior_in_tests: pass` (`entire-report.txt:89`) | **Agree** | Golden SHA256, Python reference replay, Go decode probe, 16 scenario tests cover all instruction-stated behaviors |
| 11 | Agent failure analysis: precision ceiling, not spec gap (`entire-report.txt:49-85`) | **Agree** | Failures on `test_report_golden_sha256_byte_identical_digest` (8/10) and `test_report_matches_independent_python_reference_replay` (8/10) are implementation precision, not missing instruction reqs |
| 12 | Rubric at `entire-report.txt:276-291` (gateway JS reconnect) | **Disagree (wrong task)** | Unrelated rubric; this task's rubric is `task.toml:54-73` (Go/CNX1 connectivity debugger) |
| 13 | Test quality review: ACCEPT, robust (`entire-report.txt:232-272`) | **Agree** | Golden hash + independent reference replay + scenario assertions = strong anti-shortcut design |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise (1–3 paragraphs) | 3 paragraph blocks, ~120 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Incident-style engineering brief, not spec wall | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States deliverables and constraints, not debug steps | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Describes broken behaviors + doc references, not fix walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | CHECK | Instruction well specified | Goal, paths, edit scope, and key behaviors explicit; full spec in `/app/docs` | `instruction.md:1-5` |
| 8 | CHECK | Instruction interesting | Realistic Go binary decode + connectivity replay debugging | task content |
| 9 | UNCHECK | Instruction unique | Not verified vs TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | All paths absolute | `/app/cmd`, `/app/internal`, `/app/build/…`, `/app/docs`, `/app/data` | `instruction.md:1-5` |
| 11 | UNCHECK | Task name not in instruction | `docker-network-connectivity-debugger` appears verbatim | `instruction.md:1,3` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in environment code | `environment/` |
| 14 | CHECK | Pinned pip deps | `requirements.lock` uses `==` + `--hash=sha256:` for all packages | `environment/requirements.lock:1-12` |
| 15 | CHECK | Base image digest-pinned | `@sha256:1a6d4452…` on FROM | `environment/Dockerfile:2` |
| 16 | CHECK | Build context in environment/ only | All COPY from environment subtree | `environment/Dockerfile:32-43` |
| 17 | CHECK | No ground truth in environment | Intentionally buggy stubs only; solution/tests excluded | `environment/.dockerignore:16-17`; broken `decode.go`/`replay.go` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | task layout |
| 20 | UNCHECK | Verifier deps in image; test.sh no installs | `test.sh` runs `pip install` at runtime | `tests/test.sh:14-17` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3); not re-run locally (Docker unavailable) | `entire-report.txt:15`; `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | Writes source via heredoc, `make build`/`make run` only | `solution/solve.sh:14+` |
| 23 | CHECK | Oracle derives results (not hardcoded) | Full decode.go + replay.go implementations compiled and run | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir verifier dir; binary 0/1 on pytest result | `tests/test.sh:12,22-26` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:22-26` |
| 27 | CHECK | Tests aligned with instructions | All instruction reqs traced to tests (see §5) | `tests/test_outputs.py`; LLMaJ pass `entire-report.txt:88-89` |
| 28 | CHECK | Tests check correctness | Golden SHA256, Python reference replay, Go probe, scenario semantics | `tests/test_outputs.py:871-1121` |
| 29 | CHECK | Behavior not implementation grep | End-to-end binary output + structured replay validation | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string asserts | Hash/reference comparison; byte-identical required by spec | `instruction.md:5`; `tests/test_outputs.py:871-876` |
| 31 | CHECK | Informative test docstrings | All 26 `test_*` have one-line docstrings | `tests/test_outputs.py:871-1121` |
| 32 | CHECK | Rubrics ≥3 negatives | 5 negative criteria (-5, -5, -3, -2, -5) | `task.toml:68-72` |
| 33 | CHECK | Rubric score set | All scores ∈ {±1, ±2, ±3, ±5} | `task.toml:54-73` |
| 34 | CHECK | Rubric Agent format | Each line starts `Agent …, ±N` | `task.toml:54-73` |
| 35 | CHECK | Rubric criteria detailed | Specific behaviors (CNX1 endianness, CONNECT_PROBE order, etc.) | `task.toml:54-73` |
| 36 | CHECK | Rubric positive language | Bad behaviors use negative scores, not "does not" phrasing | `task.toml:68-72` |
| 37 | CHECK | Rubric no /tests/ refs | No pytest or /tests/ mentions | `task.toml:54-73` |
| 38 | CHECK | Rubric no task.toml/instruction refs | No metadata/instruction references | `task.toml:54-73` |
| 39 | CHECK | Rubric no oracle/NOP refs | None present | `task.toml:54-73` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task layout |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task layout |
| 42 | CHECK | author_name/email present | Both set | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields present | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | go/bash, debugging, docker/networking tags fit content | `task.toml:8-25` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared `hard`; worst-model 60% = Medium | `task.toml:8`; `entire-report.txt:10-11` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:13` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:13` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:13` |
| 50 | CHECK | Tests not baked into image | `.dockerignore` excludes `tests/`; Dockerfile no COPY tests | `environment/.dockerignore:17`; `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | `.dockerignore` excludes `solution/` | `environment/.dockerignore:16` |
| 52 | CHECK | Agent cannot trivially modify inputs | Instruction: `/app/data` read-only; fixtures binary CNX1 | `instruction.md:3` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model GPT 60% ≤ 80% | `entire-report.txt:10-11` |
| 55 | CHECK | Not too hard/unfair | 60–100% pass rates; LLMaJ instruction sufficiency pass; spec docs shipped | `entire-report.txt:49-85,88` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 11, 20, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / docs) | Test(s) | Status | Proof |
|----------------------------------|---------|--------|-------|
| Decode CNX1 captures with correct stats counters | `test_go_capture_decoder_stats_match_report_all_scenarios`, `test_scenario_05_dup_seq_rejects_capture_counter`, `test_scenario_20_truncated_tail_capture_stats` | covered | `tests/test_outputs.py:886-907,1073-1070` |
| Reject paths outside `/app/data` | `test_capture_decode_permission_denied_outside_app_data` | covered | `tests/test_outputs.py:907-911` |
| CONNECT_PROBE: EGRESS_DENIED before ZONE_BLOCKED | `test_scenario_07_zone_blocked_when_egress_present_not_egress_denied`, `test_scenario_02_egress_denied_then_bridge_gap_audit` | covered | `tests/test_outputs.py:936-947,1099-1106` |
| Post-replay audits at max event seq + 1 | `test_post_replay_audit_event_seq_max_plus_one`, scenario 02/17/19/31 tests | covered | `tests/test_outputs.py:913-921` |
| Stable sort_key ties + duplicate event_id dedup | `test_scenario_14_sort_key_duplicate_event_and_zone_blocked_before_duplicate_egress`, `test_scenario_25_skipped_duplicate_event_id_increments_audit_seq` | covered | `tests/test_outputs.py:923-934,1050-1059` |
| REVOKE_EGRESS / LEAVE_NETWORK / REGISTER_DNS handlers | `test_scenario_21_revoke_egress…`, `test_scenario_26_leave_network…`, `test_scenario_29_register_dns…` | covered | `tests/test_outputs.py:956-962,1082-1089,1108-1117` |
| policy_overrides on scenario booleans | `test_scenario_33_policy_override…`, `test_scenario_28_tls_policy_override…` | covered | `tests/test_outputs.py:1015-1021,1091-1097` |
| Report SCHEMA compact JSON + byte-identical runs | `test_report_golden_sha256_byte_identical_digest`, preflight `_verifier_preflight` | covered | `tests/test_outputs.py:821-832,871-876` |
| Independent algorithm correctness | `test_report_matches_independent_python_reference_replay` | covered | `tests/test_outputs.py:879-884` |
| Build dir contains only binary + report | `test_build_directory_contains_only_binary_and_report` | covered | `tests/test_outputs.py:1120-1123` |
| Output paths `/app/build/docker-network-connectivity-debugger` and `…_report.json` | All tests via `BINARY`, `REPORT_PATH` constants | covered | `tests/test_outputs.py:17-23` |

No spec gaps or phantom requirements found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #11, blocker 3, spec alignment |
| `task.toml` | #42-45, rubric #32-39, blocker 2 |
| `environment/Dockerfile` | #15, #20, canonical base adjudication |
| `environment/requirements.lock` | #14 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24, blocker 1 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, agent stats, external adjudication |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |
| `docs/guidelines/difficulty.md` | Tier classification |

---

## 7. Validation & agent performance

### Validation

```
ERROR: test.sh [tests/test.sh]: Runtime network install not allowed: pip\s+install
WARNING: informative_test_docstrings [tests/test_outputs.py]: 26 tests — FALSE POSITIVE (all have docstrings)
INFO: submission-diversity: non-milestone not blocked
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | **Worst model** — sets Medium floor |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | From report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

Per-test: golden SHA256 and Python reference replay at 8/10 pass — agent precision errors on edge cases (LEN_OVERFLOW, audit ordering), not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `docker-network-connectivity-debugger`; regular layout; report applies |
| 1 Instruction | ☑ | Concise, absolute paths; task name in text (#11 Medium) |
| 2 Environment | ☑ | Canonical Go digest; tmux+asciinema; no solution/tests COPY; pip not in Dockerfile |
| 3 Oracle | ☑ | Derives via full source rewrite + make; report 100% (not re-run locally) |
| 4 Verifiers | ☑ | Binary reward; behavior tests; **pip install in test.sh = High blocker** |
| 5 Metadata | ☑ | **difficulty mismatch High blocker**; rubric inline in task.toml |
| 6 Rubric | ☑ | 5 negatives; valid format; no test/metadata refs |
| 7 LLMaJ & agent evidence | ☑ | Difficulty Medium confirmed; spec alignment passes |
| 8 Novelty & fairness | ☑ | Multi-bug Go debugging; no cheating paths |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, Dockerfile pinning, offline-safe wheels, rubric, and spec↔test alignment are solid. Two High blockers: move verifier `pip install` from `tests/test.sh` into the Dockerfile (wheels are already COPY'd but not installed), and update `task.toml` `difficulty` from `hard` to `medium` (worst-model GPT-5.5 at 60%) or rebalance until worst-model ≤20%. Also rephrase `instruction.md` to drop the verbatim task folder name `docker-network-connectivity-debugger`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Dependency Location | yes | 1 |
| Task Difficulty | yes | 2 |
| Metadata Issues | yes | 2 |
| Instruction Styling | yes | 3 |
| Pinning Issues | no | — |
| Environment | no | — |
| Test Alignment/Coverage Issues | no | — |
| Oracle Solution Issues | no | — |
| Rubric | no | — |
