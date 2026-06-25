# Terminus Review Report: `mavlink-mission-upload-sequence-auditor`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt` 3/3; local oracle timed out at 300s) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** none

**Decision (concise):** Re-audit confirms no High blockers. Automated script false-positives on pip pinning (#14), docstrings (#31), and difficulty (#45) are disproven by artifact inspection. Builder `rust:1.85-slim@sha256:9f841bbe…` is on the canonical base list. All 70 `test_*` functions have one-line docstrings. Worst-model pass rate is Claude **60%** (Medium tier), matching `task.toml` `difficulty = "medium"`. Spec↔test alignment, anti-cheat, digest-pinned env, and offline verifier deps are solid.

**Insights (concise):**

- External report’s **CRITICAL** “non-canonical Rust builder” claim is false — same image+digest as `docs/guidelines/dockerfxile.md:12`.
- Validate’s 70 “missing docstrings” warnings are false positives (docstrings follow function signatures).
- Automated review used GPT-5.5 **80%** as worst model; tier floor is **min(60%, 80%) = 60%** per `docs/guidelines/difficulty.md`.
- 55+ tests with `test_partial_fix_fails_*` traps and `mission_expect.py` independent recompute close partial-fix cheating paths.
- Instruction is terse (2 paragraphs) but delegates normative behavior to seven `/app/docs/*.md` contracts — appropriate for spec-driven debugging.
- Rubric lines in `entire-report.txt` (portal UI) are not in task folder; checkboxes #32–#39 are N/A.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept — metadata matches Medium, digest-pinned Dockerfile, verifier deps in image, test.sh reward init, oracle passes, no solution/tests in image (ChatGPT) | **Agree** | `task.toml:7`; `environment/Dockerfile:1,12,28-31`; `tests/test.sh:4-6,31-35`; `environment/.dockerignore:16-17`; `entire-report.txt:11` |
| 2 | No High/Medium/Low severity issues (ChatGPT) | **Agree** | Full artifact re-audit below |
| 3 | Non-canonical builder `rust:1.85-slim` — NEEDS REVISION (entire-report CRITICAL) | **Disagree** | `environment/Dockerfile:1` digest matches canonical list `docs/guidelines/dockerfxile.md:12`; runtime stage `debian:bookworm-slim` at `dockerfxile.md:22` |
| 4 | Difficulty understated — scope argues for `hard` (entire-report WARNING/SUGGESTION) | **Partially agree** (not blocker) | 5-file multi-bug Rust scope is hard-adjacent; worst-model **60%** still falls in Medium band (20–60%) per `difficulty.md` |
| 5 | `test.sh` requires exactly `/app` PWD (entire-report WARNING) | **Agree** (Low only) | `tests/test.sh:12-16`; defensible because build assumes `/app`; not a verifier defect |
| 6 | `build.sh` checks binaries only, does not recompile (entire-report WARNING) | **Agree** (by design) | `environment/app/scripts/build.sh:3-8`; `instruction.md:3` directs agents to `oracle-build.sh` |
| 7 | Instruction too terse for medium scope (entire-report SUGGESTION) | **Partially agree** (not blocker) | `instruction.md` is 3 sentences + doc pointers; normative contracts in `/app/docs/` satisfy spec-driven tasks |
| 8 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` pass | **Agree** | `entire-report.txt:161-162`; CRC extra byte at `mseq-format.md:29`, export epoch at `instruction.md:3` + `db-schema.md` |
| 9 | Oracle 100% (3/3) | **Agree** (not re-run locally) | `entire-report.txt:11`; `solution/solve.sh:7-20` copies fixed sources + `oracle-build.sh` + CLI run |
| 10 | Agent instruction sufficiency PASS | **Agree** | `entire-report.txt:93,123-124`; failures are execution bugs (CRC, SQL operator), not spec gaps |
| 11 | Hack check clean | **Agree** | `entire-report.txt:118-119`; hidden fixtures via `gen_mseq_fixtures.py` at verify time |
| 12 | Test quality ROBUST / ACCEPT | **Agree** | `entire-report.txt:334-341`; `mission_expect.py` independent recompute |
| 13 | Automated review: #14 unpinned pip | **Disagree** | `environment/Dockerfile:30-31` `pytest==9.0.3`, `pytest-json-ctrf==0.5.0`; `requirements-verifier.txt` |
| 14 | Automated review: 70 tests missing docstrings (#31) | **Disagree** | All 70 `test_*` have `"""…"""` e.g. `tests/test_outputs.py:114,132,1039` |
| 15 | Automated review: difficulty mismatch #45 (80% → easy) | **Disagree** | Worst model Claude **60%** `entire-report.txt:6`; `task.toml:7` `medium` matches Medium tier |
| 16 | `pinned_dependencies` quality check pass | **Agree** | `entire-report.txt:166`; `Cargo.toml:19-24` exact versions; `Cargo.lock` present |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 2 problem paragraphs + requirements; ~102 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer incident narrative, not LLM walkthrough | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | No heavy headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step solve steps | States WHAT (fix Rust, recompile, use CLIs); no bug-by-bug guide | `instruction.md:3` |
| 5 | CHECK | No hints/solving strategies | `/app/docs/` are normative contracts (schemas/rules), not fix walkthroughs | `environment/app/docs/*.md` |
| 6 | CHECK | No design-doc I/O tables | Instruction has no input→output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal + seven normative doc paths + build/export CLIs | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Multi-module Rust MAVLink/SQLite debugging with binary CRC | task content |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app`, `/app/docs/…`, `/app/src/`, `/app/scripts/oracle-build.sh` | `instruction.md:1-3` |
| 11 | CHECK | Task name not in instruction | No `mavlink-mission-upload-sequence-auditor` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md`, `environment/` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in env code | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` | `environment/Dockerfile:30-31` |
| 15 | CHECK | Base image digest-pinned | Canonical `rust:1.85-slim` + `debian:bookworm-slim` with digests | `environment/Dockerfile:1,12`, `docs/guidelines/dockerfxile.md:12,22` |
| 16 | CHECK | Context in environment/ only | COPY from `app/`, `scripts/` within environment | `environment/Dockerfile:42-47` |
| 17 | CHECK | No ground-truth answers in env | Buggy scaffold + normative contracts (allowed debugging pattern) | `environment/app/src/`, `environment/app/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter Harbor mounts | No `docker-compose.yaml` | task root |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:28-31`, `tests/test.sh:25-27` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle no runtime network | `solve.sh` copies patches, builds, runs locally | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results | Patches 5 Rust files + `oracle-build.sh` + CLI ingest/export | `solution/solve.sh:7-20` |
| 24 | CHECK | reward.txt + failure path | Writes 0 first; 1/0 after pytest; mkdir verifier | `tests/test.sh:4-6,31-35` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards 0/1 | `echo 0` / `echo 1` only | `tests/test.sh:5,32-34` |
| 27 | CHECK | Tests aligned with instructions | All doc-contract behaviors covered incl. partial-fix traps | §5; `entire-report.txt:162` |
| 28 | CHECK | Tests check correctness | `mission_expect.expected_export` recomputes from SQLite | `tests/mission_expect.py`, `tests/test_outputs.py:192` |
| 29 | CHECK | Behavior not implementation grep | No source grepping in tests | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Independent oracle + computed distances/altitudes | `tests/test_outputs.py`, `tests/mission_expect.py` |
| 31 | CHECK | Informative test docstrings | 70/70 `test_*` + class docstring | `tests/test_outputs.py:1-7,114,1036` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README at task root | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, `allow_internet=false`, resources | `task.toml:16-27` |
| 44 | CHECK | Tags/languages/category applicable | `rust`, `mavlink`, `sqlite`, `data-processing` + `db_interaction` fit | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches pass rates | Declared `medium`; worst-model Claude 60% → Medium tier | `task.toml:7`, `entire-report.txt:1,6` |
| 46 | UNCHECK | steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:17`, `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:16` |
| 52 | CHECK | Agent can't trivially cheat | Hidden fixtures at verify time; `mission_expect` recomputes | `tests/gen_mseq_fixtures.py`, `tests/mission_expect.py` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 60% ≤ 80% | `entire-report.txt:6` |
| 55 | CHECK | Not too hard/unfair | LLMaJ instruction sufficiency PASS; agents reach 60–80% | `entire-report.txt:93,6-7` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| CRC extra byte `0x4D` when `flags & 0x01` | `test_foxtrot_crc_omits_extra_when_v2_flag_clear`, `test_quebec_bad_waypoint_crc_aborts_ingest` | covered | `mseq-format.md:29`; `tests/test_outputs.py:253+` |
| Frame-3 relative altitude minus home | `test_relative_altitude_export_v2`, `test_oscar_mixed_frame_altitude_export` | covered | `instruction.md` + rollup docs; `tests/test_outputs.py:211+` |
| Distance sum-then-round (not per-leg) | `test_november_distance_round3_after_sum_not_per_leg`, `test_partial_fix_fails_per_leg_distance_rounding` | covered | `tests/test_outputs.py:325,347` |
| Hold/suppress flag semantics | `test_tango_hold_skips_inbound_leg_distance`, `test_bravo_suppress_middle_hold_dest_skips_last_leg` | covered | `tests/test_outputs.py:664,834` |
| Transaction rollback on corrupt ingest | `test_gamma_corrupt_upload_rolls_back` | covered | `tests/test_outputs.py:151` |
| Duplicate seq abort | `test_papa_duplicate_seq_aborts_ingest`, `test_kilo_nonadjacent_duplicate_seq_aborts_ingest` | covered | `tests/test_outputs.py:360,437` |
| Idempotent replay (vehicle-scoped) | `test_beta_idempotent_replay`, `test_partial_fix_fails_upload_id_only_idempotency` | covered | `tests/test_outputs.py:131,543` |
| Upload-scoped `exported_at_unix` (not global/vehicle/rowid) | `test_tango_export_epoch_scoped_to_upload_not_vehicle`, `TestCrossRunExportClock` | covered | `instruction.md:3`; `tests/test_outputs.py:506,1035+` |
| `upload_qc_pass` symmetric altitude bands | `test_uniform_rel_alt_qc_fail`, `test_delta_hidden_negative_rel_qc_fail` | covered | `tests/test_outputs.py:887,945` |
| `audit_hash` excludes `exported_at_unix` / epoch override | `test_audit_hash_ignores_mission_epoch_base_override`, `test_partial_fix_fails_audit_hash_includes_epoch` | covered | `tests/test_outputs.py:973,929` |
| Independent export recompute oracle | `test_partial_fix_canary_export_matches_mission_expect` | covered | `tests/test_outputs.py:186` |
| Empty upload edge case | `test_yankee_empty_upload_export` | covered | `tests/test_outputs.py:677` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #4, #7, #10, #27 |
| `task.toml` | #43, #44, #45 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/docs/mseq-format.md` | #27, CRC spec |
| `environment/app/docs/db-schema.md` | #27, export epoch |
| `environment/app/Cargo.toml` | #14 (Rust pins) |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #28, #31 |
| `tests/mission_expect.py` | #28, #52 |
| `solution/solve.sh` | #21, #23 |
| `entire-report.txt` | #21, #45, #54, adjudication |
| `docs/guidelines/dockerfxile.md` | #15 canonical base |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate mavlink-mission-upload-sequence-auditor/
Summary: 0 error(s), 73 warning(s), 2 info
```

Warnings are false positives: docstrings present but not detected by AST heuristic; pip line flagged despite `==` pins on following lines.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | `entire-report.txt:7` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model; 1 timeout |
| oracle | 100.0% (3/3) | `entire-report.txt:11` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes |

Agent timeout gate: 1/10 (<5) — not blocking (`entire-report.txt:18`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) Rust task |
| 1 Instruction | ☑ | Terse but complete via normative `/app/docs/` contracts |
| 2 Environment | ☑ | Canonical digest-pinned bases; tmux+asciinema; offline verifier venv |
| 3 Oracle | ☑ | Derives via patched sources + build; 100% per report |
| 4 Verifiers | ☑ | Canonical reward block; 70 behavior tests; no runtime installs |
| 5 Metadata | ☑ | `medium` matches 60% worst-model; `allow_internet=false` |
| 6 Rubric | ☑ | N/A — no rubric file in task (portal lines in report only) |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; failures are agent execution not spec gaps |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; partial-fix traps; hidden fixtures |
| 9 Long context | — | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction is concise and delegates behavior to seven normative `/app/docs/` contracts that fully align with the 70-test verifier suite (including partial-fix traps and `mission_expect.py` recomputation). The environment uses canonical digest-pinned Rust and Debian bases, bakes verifier deps offline, and excludes tests/solution from the image. Oracle passes at 100% and worst-model agent pass rate (Claude 60%) matches declared medium difficulty. No spec-test gaps or cheating paths found on re-audit.

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
