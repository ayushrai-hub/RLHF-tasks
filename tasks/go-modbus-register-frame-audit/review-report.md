# Terminus Review Report: `go-modbus-register-frame-audit`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Go debugging task with digest-pinned offline env, independent Python recomputer, and clean oracle pass. Two real blockers: (1) `min_reg`/`max_reg` are documented as an “address span” but the verifier uses starting register addresses only — all GPT-5.5 runs failed on this single semantic gap; (2) platform rubric has only one negative criterion (needs ≥3) and references `/tests/`. Non-milestone `# Rubric 1` header is allowed per guidelines; category and Dockerfile findings from automated audit are false positives on manual review.

**Insights (concise):**

- All 5 GPT-5.5 trials passed 12/13 tests; sole failure was `test_practice_segment_three_matches_contract` with `max_reg` 301 vs expected 300 (`reg + count - 1` vs start address).
- Practice segment-3 reads: start addresses 100, 200, 300 (`gen_fixtures.py`); recomputer `summarize_reg_span` uses `fr["reg"]` only → `max_reg=300`.
- `audit_contract.md:16` phrase “address span” is the root ambiguity; instruction.md lists keys but does not define min/max semantics.
- Rubric positive total is exactly 40 (passes cap); `# Rubric 1` on a non-milestone task is optional per `rubrics.md` — not a format blocker.
- `requirements.lock` pins pytest with `==` + hashes; Dockerfile bakes `/opt/verifier-venv`; `test.sh` does not install at runtime — automated #14/#20 failures are false positives.
- Oracle: 1/1 pass (`./scripts/terminus oracle`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | `min_reg`/`max_reg` semantics under-specified: docs say “address span over collapsed segment reads” but verifier/reference use starting register addresses (`fr.Reg`) only, not inclusive end (`reg + count - 1`). | `environment/docs/audit_contract.md:16` (“address span over collapsed segment reads”); `tests/mreg_audit_recompute.py:136-140` (`regs = [int(fr["reg"]) for fr in frames if fr["func"] == 0x03]`); `environment/ci/gen_fixtures.py:114-115` (practice `reg=300, count=2` → agents expect `max_reg=301`, ref expects `300`); `entire-report.txt:59-62` (100% GPT-5.5 failure on this field) | Clarify in `instruction.md` and `audit_contract.md` that `min_reg`/`max_reg` are the min/max **starting register address** among collapsed `0x03` read frames only (not `reg + count - 1`). |
| 2 | Medium | Rubric | #32, #37 | Platform rubric has only **1** negative criterion (minimum **3** required). Existing negative also references `/tests/`. | `entire-report.txt:276` (`Agent modifies files under /tests …, -5` — sole negative); `docs/guidelines/rubrics.md:39` (≥3 distinct negatives) | Add ≥2 more distinct negative criteria (e.g. hand-writing JSON without rebuild, skipping `go build`, editing fixture bytes). Reword negative to avoid `/tests/` path reference per rubric rules. |

*Automated audit #14, #20, #31, #41 were false positives on manual review — not listed as blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `min_reg`/`max_reg` under-specified; verifier expects start addresses only (ChatGPT High; entire-report instruction sufficiency) | **Agree** | `audit_contract.md:16`; `mreg_audit_recompute.py:136-140`; `solution/files/scan/load.go:121-134` (oracle uses start addrs); `entire-report.txt:26-27,59-62` |
| 2 | Rubric needs ≥2 more distinct negatives (ChatGPT Medium) | **Agree** | `entire-report.txt:262-276` (13 positives, 1 negative); `rubrics.md:39` |
| 3 | Category should be `debugging` not `data-processing` (ChatGPT Medium; Harbor review warning) | **Partially agree** | `task.toml:7` `data-processing`; `instruction.md:3` “Repair sources”; `docs/task-type-taxonomy.md:29` (“Finding/fixing bugs” → `debugging`). Better fit but **not a revision blocker** per taxonomy (both valid; no High/Medium policy violation). |
| 4 | Optional: document checkpoint/exception exclusion from digest (ChatGPT Low) | **Agree (Low, non-blocking)** | `audit_contract.md:35` already states digest walk omits checkpoint/exception rows; optional clarity only. |
| 5 | Dockerfile FROM digest-pinned and appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:1a6d4452…`; tmux + asciinema `Dockerfile:12-13` |
| 6 | Non-milestone task uses milestone rubric format (`# Rubric 1`) | **Disagree (not a blocker)** | `task.toml:9` `number_of_milestones = 0`; `rubrics.md:66` (“Non-milestone: … `# Rubric 1` optional; no `# Rubric 2+`”). Single `# Rubric 1` header is permitted. |
| 7 | Harbor “READY TO USE” / test quality ACCEPT (entire-report) | **Partially agree** | Structure/tests/oracle are strong; spec gap on min/max and rubric negatives still warrant Revise. |
| 8 | LLMaJ `behavior_in_tests` PASS (entire-report) | **Disagree for min/max** | LLMaJ missed that tested semantics (“address span”) ≠ verifier behavior (start addresses only). |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~301 words; problem + requirements within budget | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem narrative, not spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | No heavy formatting | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No walkthrough steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | Describes outcomes, not fix order | `instruction.md` |
| 6 | CHECK | No design-doc tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, paths, keys, rebuild command | `instruction.md` |
| 8 | CHECK | Interesting | Realistic industrial Go protocol debugging | — |
| 9 | UNCHECK | Unique | Cannot verify vs corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name absent | No task slug in instruction | `instruction.md` |
| 12 | CHECK | No canary | No canary strings | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline fixtures only | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `requirements.lock` uses `pytest==8.4.1` + hashes; `--require-hashes` | `environment/requirements.lock:1-2`, `Dockerfile:17-19` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context scoped | COPY only environment subtree | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in env | Docs describe contract, broken code is intentional | `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | `/opt/verifier-venv` baked; `test.sh` uses venv pytest, no install | `Dockerfile:17-19`, `tests/test.sh:11-14` |
| 21 | CHECK | Oracle consistent | `./scripts/terminus oracle` → reward 1.0 | oracle run 2026-07-03 |
| 22 | CHECK | Oracle no internet | solve.sh copies files + go build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Rebuilds binary, runs CLI, checks behavior | `solution/solve.sh:6-45` |
| 24 | CHECK | reward.txt canonical | Writes 0/1 with failure path | `tests/test.sh:3-20` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | `min_reg`/`max_reg` tested semantics not stated in spec | Blocker 1 |
| 28 | CHECK | Correctness not format-only | Full equality vs independent recomputer | `tests/test_outputs.py:107-116` |
| 29 | CHECK | Behavior not implementation | Runs CLI, checks JSON output | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle strings | Deep dict equality appropriate for contract | `tests/test_outputs.py:116` |
| 31 | CHECK | Test docstrings | All 13 `test_*` functions have docstrings | `tests/test_outputs.py:119-197` |
| 32 | UNCHECK | ≥3 rubric negatives | Only 1 negative in platform rubric | `entire-report.txt:276` |
| 33 | CHECK | Rubric scores valid | All ±1,2,3,5 | `entire-report.txt:263-276` |
| 34 | CHECK | Rubric Agent format | 14 properly formatted lines | `entire-report.txt:263-276` |
| 35 | CHECK | Rubric detailed; cap | 40 positive pts (≤40 cap) | `entire-report.txt:263-275` |
| 36 | CHECK | Positive rubric language | No “does not” on positive lines | `entire-report.txt` |
| 37 | UNCHECK | Rubric no /tests/ refs | Negative cites “files under /tests” | `entire-report.txt:276` |
| 38 | CHECK | Rubric no metadata refs | No task.toml/instruction refs | `entire-report.txt` |
| 39 | CHECK | Rubric no oracle/NOP | No oracle mentions | `entire-report.txt` |
| 40 | CHECK | Required files | All present | task tree |
| 41 | CHECK | No stray parent files | No jobs/README in task root | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/category applicable | Go/modbus tags fit; category defensible | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard`; worst-model 0% | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | steps/ layout | N/A — non-milestone | `task.toml:9` |
| 47 | UNCHECK | solveN.sh | N/A — non-milestone | `task.toml:9` |
| 48 | UNCHECK | test_mN.py | N/A — non-milestone | `task.toml:9` |
| 49 | UNCHECK | Milestone scope | N/A — non-milestone | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Input not trivially hackable | Rebuild + recompute cross-check | `tests/test_outputs.py` |
| 53 | CHECK | Git pins | No unpinned git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:26-27` |
| 55 | UNCHECK | Not unfair | Systematic spec ambiguity caused 0% GPT-5.5 pass | Blocker 1; `entire-report.txt:52-80` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 27, 32, 37, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Modbus CRC16 validation | `test_crc_noise_excludes_bad_checksum` | covered | `instruction.md:13`; `audit_contract.md:27` |
| `.mregorder` scan order | `test_mregorder_overlay_applied`, `test_order_overlay_sidecar` | covered | `instruction.md:13` |
| Checkpoint removal | `test_checkpoint_marker_skipped` | covered | `audit_contract.md:28` |
| Slave allow-list reject | `test_slave_reject_excluded_from_chain` | covered | `instruction.md:13` |
| Duplicate-seq collapse by seq id | `test_duplicate_seq_last_frame_wins` | covered | `instruction.md:13` |
| Continuation seeding from `.mregtip` | `test_continue_seed_*`, `test_unrelated_stale_tip_*` | covered | `instruction.md:15` |
| Flat JSON (no debug envelope) | `_run_audit` assert | covered | `tests/test_outputs.py:103` |
| `.mregtip` persistence | `test_mregtip_written_after_successful_audit` | covered | `instruction.md:15` |
| `mreg_files` as `[]` not null | `test_empty_scan_zero_state` | covered | `instruction.md:15` |
| End-to-end practice segment 3 | `test_practice_segment_three_matches_contract` | covered | `instruction.md:13` |
| **`min_reg`/`max_reg` = start addresses of collapsed 0x03 reads** | all `_assert_contract` tests | **gap** | `audit_contract.md:16` (“address span”); `mreg_audit_recompute.py:136-140` |
| Checkpoint/exception excluded from chain digest | implied by chain tests | covered | `audit_contract.md:35` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, blocker 1, spec alignment |
| `environment/docs/audit_contract.md` | Blocker 1, spec alignment |
| `environment/docs/frame_layout.md` | Register field layout |
| `environment/ci/gen_fixtures.py` | Practice `reg=300,count=2` proof |
| `tests/mreg_audit_recompute.py` | Verifier semantics for min/max |
| `tests/test_outputs.py` | #27-31, verifier design |
| `tests/test.sh` | #20, #24 |
| `environment/Dockerfile` | #14-15, #20 |
| `environment/requirements.lock` | #14 |
| `task.toml` | #45-49, metadata |
| `entire-report.txt` | Agent stats, rubric, instruction sufficiency |
| `solution/solve.sh` | #21-23 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-modbus-register-frame-audit ===
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All failed `test_practice_segment_three_matches_contract` on `max_reg` |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3 platform; 1/1 local) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; report matches folder |
| 1 Instruction | ☑ | min_reg/max_reg ambiguity flagged |
| 2 Environment | ☑ | Digest-pinned Go base; deps baked; tmux/asciinema present |
| 3 Oracle | ☑ | Passes all tests locally |
| 4 Verifiers | ☑ | Independent recomputer; 13 behavioral tests |
| 5 Metadata | ☑ | `data-processing` acceptable; `number_of_milestones=0` |
| 6 Rubric | ☑ | 40 positives OK; 1 negative blocker; `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL on min/max confirmed |
| 8 Novelty & fairness | ☑ | Unfair min/max gap; otherwise strong anti-cheat |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid debugging task — the pinned Go environment, independent Python recomputer, and rebuild-from-source verifier design are all in great shape, and the multi-bug pipeline is a fair challenge. Two things before acceptance: please clarify in `instruction.md` and `audit_contract.md` that `min_reg` and `max_reg` are the min/max **starting register address** among collapsed `0x03` read frames (not the inclusive end `reg + count - 1`). Every GPT-5.5 run got this wrong while passing everything else. Also expand the platform rubric with at least two more distinct negative criteria (you currently have one), and reword that negative so it doesn’t reference the `/tests/` path.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
