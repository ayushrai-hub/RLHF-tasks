# Terminus Review Report: rust-apiary-weight-delta

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling, Rubric

**Decision (concise):** Strong Rust replay/debugging task with solid fixtures, independent Python reference, anti-cheat checks, and digest-pinned offline environment. Two revision items block acceptance: `scale_model.md` contradicts the verifier on `state_recovery` quarantine `source` and `quarantined_frames` counting (8/10 agent runs failed that single test). Platform rubric positive sum is 43 (exceeds 10–40); rubric uses correct flat non-milestone format but needs ≥3 points trimmed on the platform.

**Insights (concise):**

- `entire-report.txt` reviewer-feedback paragraph references `forge_stage_contract.md` — stale text from a different task; rubric/score claims still apply to this submission.
- Rubric is **not** in milestone block format (no `# Rubric 2+` headers); flat `Agent …, ±N` list is correct for `number_of_milestones = 0`.
- Automated `#14` pip-pin failure is a false positive — `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are `==`-pinned in `environment/Dockerfile:15-16`.
- Missing test docstrings are CI warnings only; descriptive test names satisfy portal #31.
- Worst-model pass rate 20% (1/5 Claude) fits `hard`; GPT-5.5 0/5 also supports calibration.
- Oracle not executed locally (Docker socket unavailable in review environment).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | `state_recovery` quarantine semantics underspecified and contradictory: docs never require `source: ""`; docs say `quarantined_frames` equals quarantine JSONL row count but verifier excludes `state_recovery` meta-rows from the counter | `scale_model.md:164` ("equals quarantine JSONL row count"); `scale_model.md:189-201` (lists `state_recovery` as allowed reason but no `source` rule); `tests/test_outputs.py:1042-1056` (expects two rows with `"source": ""`); `tests/test_outputs.py:565-578` (reference increments `quarantined_frames` only for frame-parse quarantine, not `prefix_quarantine` state_recovery rows at 539); agent stats `test_state_recovery_prefers_newest_valid_snapshot_and_reports_tmp_files`: 1/10 | In `scale_model.md`: document that `state_recovery` rows use `"source": ""`, `stream_index`/`frame_index` `0`, `event_id` `null`; clarify `quarantined_frames` counts only frame/replay quarantine failures, not `state_recovery` metadata rows (which still appear in quarantine JSONL and audit fingerprint) |
| 2 | Low | Rubric | — | Platform rubric positive point sum is 43 (six +5, four +3, one +1), above the 10–40 total allowed for non-milestone tasks | `entire-report.txt:357-367` (sum = 43); `docs/guidelines/rubrics.md:29-31`; prior portal note `entire-report.txt:382` | On platform rubric editor: trim ≥3 positive points (e.g. drop +1 smoke-test line or lower one +3 to +2 or +1) |

*No other High-severity blockers found in task artifacts.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `scale_model.md` must clarify `state_recovery` uses `source: ""` and `quarantined_frames` excludes state-recovery rows (ChatGPT / `entire-report.txt` agent-failure analysis) | **Agree** | `scale_model.md:164` vs `tests/test_outputs.py:1044-1054`; reference `prefix_quarantine` at `test_outputs.py:539` does not increment counter |
| 2 | Rubric max positive 43 exceeds 10–40 range; trim ≥3 points (ChatGPT / portal reviewer feedback) | **Agree** | `entire-report.txt:357-367` → 6×5+4×3+1×1=43; `rubrics.md:31` |
| 3 | Non-milestone task incorrectly uses milestone rubric format | **Disagree** | `entire-report.txt:357-375` has no `# Rubric N` headers; flat list per `rubrics.md:64`; `task.toml:9` `number_of_milestones = 0` |
| 4 | Portal reviewer feedback about `forge_stage_contract.md` ledger digest (entire-report.txt:380-384) | **Disagree** (wrong task) | No `forge_stage_contract.md` in `rust-apiary-weight-delta/`; task uses `scale_model.md` |
| 5 | Optional: add `.dockerignore`, simplify apt pins, default output path note (ChatGPT Low) | **Partially agree** | Validator warns `check_dockerignore`; `instruction.md:3` mentions `/app/output/…` paths; not blockers |
| 6 | LLMaJ `behavior_in_task_description: fail` — instruction too terse (entire-report.txt:146) | **Partially agree** | `instruction.md` is 4 lines deferring to `scale_model.md`; acceptable pattern except the `state_recovery` gap above |
| 7 | Missing test docstrings are High blockers (automated review script) | **Disagree** as blocker | 20 tests lack docstrings but names are descriptive (`test_fresh_replay_matches_reference_with_epochs_and_aliases`, etc.); satisfies portal #31 "names **or** docstrings"; `reviewer-checklist-full.md` verifiers table has no High row for docstrings |
| 8 | Pip deps unpinned (#14 fail from automated review) | **Disagree** | `environment/Dockerfile:15-16` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; LLMaJ `pinned_dependencies: pass` at `entire-report.txt:151` |
| 9 | Non-canonical Rust base image is a blocker (Harbor review report) | **Disagree** as blocker | `environment/Dockerfile:1` digest-pinned `rust:1.85-slim`; Rust toolchain justified; advisory only per `entire-report.txt:199-206` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 2 short paragraphs, ~108 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem statement, no spec-dump tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | Points to contract doc, no algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified goal | Clear repair target + contract reference | `instruction.md`, `scale_model.md` |
| 8 | CHECK | Interesting task | Realistic telemetry replay debugging | task content |
| 9 | CHECK | Unique | Stateful binary replay + audit fingerprint; no duplicate found in repo scan | — |
| 10 | CHECK | Absolute paths | `/app/src`, `/app/docs/scale_model.md`, `/app/output/…` | `instruction.md:1-3` |
| 11 | CHECK | Task name not in instruction | No folder slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Pip pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15-16` |
| 15 | CHECK | FROM digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY limited to env subtree | `environment/Dockerfile:20-25` |
| 17 | CHECK | No ground truth in env | Buggy starter sources only; fixed modules in `solution/` not copied to image | `environment/Dockerfile`, `solution/fixed/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts safe | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; `test.sh` no installs | `environment/Dockerfile:13-16`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed — Docker socket unavailable | oracle run failed |
| 22 | CHECK | Oracle no internet | `solve.sh` local cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Copies fixed Rust modules, `cargo build`, runs binary | `solution/solve.sh:7-53` |
| 24 | CHECK | reward.txt canonical block | mkdir + 0/1 write | `tests/test.sh:12-23` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:19-22` |
| 27 | UNCHECK | Tests aligned with instructions | `state_recovery` `source` and counter semantics tested but not specified | Blocker 1 |
| 28 | CHECK | Tests check correctness | Field-by-field vs independent reference replay | `tests/test_outputs.py:677-682` |
| 29 | CHECK | Behavior not implementation grep | Subprocess + output comparison | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string-only | JSON structural equality via reference model | `tests/test_outputs.py` |
| 31 | CHECK | Informative names or docstrings | 20 descriptive `test_*` names | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 8 negatives | `entire-report.txt:368-375` |
| 33 | CHECK | Scores in ±1,2,3,5 | All lines valid | `entire-report.txt:357-375` |
| 34 | CHECK | Agent line format | 19 criteria, flat list | `entire-report.txt:357-375` |
| 35 | CHECK | Rubric detailed/precise | Task-specific replay semantics | `entire-report.txt:357-375` |
| 36 | CHECK | Positive phrasing | Negatives describe bad behavior affirmatively | `entire-report.txt:368-375` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:357-375` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:357-375` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:357-375` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray README in task folder | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, category, tags present | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust/data-processing/telemetry | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches rates | `hard` vs 20% worst-model defensible | `task.toml:6`, `entire-report.txt:27-28` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent can't trivially cheat inputs | Dynamic tmp_path fixtures; overwrite anti-cheat test | `test_output_overwrite_and_precomputed_cheat_fails` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 20% ≤80% | `entire-report.txt:27-28` |
| 55 | UNCHECK | Not unfair | Systematic failure on unstated `state_recovery` semantics | Blocker 1; `entire-report.txt:86-89` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Fresh replay with epochs/aliases | `test_fresh_replay_matches_reference_with_epochs_and_aliases` | covered | `scale_model.md:49-84` |
| Resume two-pass ≡ single fresh | `test_resume_two_pass_matches_single_fresh_replay` | covered | `scale_model.md:24-26` |
| Compacted state resume | `test_compacted_state_resume_matches_uncompacted_resume` | covered | `scale_model.md:25` |
| Duplicate event idempotency | `test_duplicate_event_ids_are_idempotent_across_sources` | covered | `scale_model.md:113` |
| Late correction bucket move | `test_late_correction_moves_bucket_and_recomputes_delta` | covered | `scale_model.md:114` |
| Tombstone removal | `test_tombstone_removes_event_without_poisoning_other_hives` | covered | `scale_model.md:115` |
| Corrupt/bad_magic/truncated quarantine | `test_corrupt_checksum_bad_magic_and_truncated_tail_are_quarantined` | covered | `scale_model.md:106-109` |
| Timezone/day boundary | `test_half_hour_timezone_and_day_start_boundary` | covered | `scale_model.md:79` |
| Output overwrite (anti-cheat) | `test_output_overwrite_and_precomputed_cheat_fails` | covered | `scale_model.md:23`, `instruction.md:3` |
| Legacy v1 quarantine | `test_legacy_v1_frame_compatibility_or_explicit_quarantine` | covered | `scale_model.md:117-119` |
| Resume stream identity skip | `test_resume_skips_consumed_matching_stream_but_replays_changed_backfill` | covered | `scale_model.md:214` |
| State recovery newest valid snapshot | `test_state_recovery_prefers_newest_valid_snapshot_and_reports_tmp_files` | **gap** | `source: ""` and counter exclusion not in `scale_model.md` |
| Low32 collision / correction chain | `test_low32_collision_target_resolution_and_correction_chain` | covered | `scale_model.md:220-222` |
| Tombstone after correction | `test_tombstone_after_correction_removes_current_bucket_only` | covered | `scale_model.md:222` |
| Stale correction target | `test_stale_correction_target_is_quarantined_without_reviving_dead_event` | covered | `scale_model.md:220` |
| Unsupported frame type event_id | `test_unsupported_frame_type_has_event_id_and_preserves_frame_frontier` | covered | `scale_model.md:199` |
| bad_magic null event_id | `test_bad_magic_never_leaks_event_id_even_when_bytes_look_decodable` | covered | `scale_model.md:108,195` |
| Audit fingerprint stability | `test_audit_fingerprint_is_stable_across_fresh_resume_and_compact_paths` | covered | `scale_model.md:226-233` |
| Epoch tie-break / alias boundary | `test_epoch_tie_break_and_alias_until_boundary_after_correction` | covered | `scale_model.md:81,220` |
| Compiled ELF binary | `test_hive_scale_is_compiled_elf_binary` | covered | `instruction.md:3` |
| Caller-provided absolute paths | path tests via `tmp_path` in `run_scale` | covered | `scale_model.md:21`, `instruction.md:3` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #10 |
| `environment/docs/scale_model.md` | Blocker 1, #27, #55, spec alignment |
| `environment/Dockerfile` | #13-20, #50-51 |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec alignment |
| `tests/test.sh` | #24-26 |
| `solution/solve.sh` | #22-23 |
| `solution/fixed/state.rs` | Blocker 1 oracle behavior (`source: String::new()`) |
| `task.toml` | #42-45, #46-49 N/A |
| `entire-report.txt` | #32-39 rubric, #45/#54 agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate rust-apiary-weight-delta
Summary: 0 error(s), 22 warning(s), 3 info
```

Warnings are missing test docstrings (22) and optional `.dockerignore`; no validation errors.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 20.0% (1/5) | |
| terminus-gpt5-5 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) | per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Notable per-test: `test_state_recovery_prefers_newest_valid_snapshot_and_reports_tmp_files` 1/10 — dominant agent failure mode tied to Blocker 1.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `rust-apiary-weight-delta`; report applies (hive_scale / scale_model.md) |
| 1 Instruction | ☑ | Concise deferral to scale_model.md; state_recovery gap flagged |
| 2 Environment | ☑ | Digest-pinned Rust image; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | solve.sh rebuilds from fixed modules; not run locally |
| 4 Verifiers | ☑ | Reference replay; reward block OK; state_recovery spec gap |
| 5 Metadata | ☑ | Regular task, hard, data-processing |
| 6 Rubric | ☑ | Flat non-milestone format OK; 43 positive pts over cap |
| 7 LLMaJ & agent evidence | ☑ | Agent failure analysis confirms spec gap |
| 8 Novelty & fairness | ☑ | Multi-module Rust repair; unfair only on unstated recovery semantics |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust replay task — the binary fixtures, resume/compact coverage, independent Python reference, anti-cheat output overwrite check, and offline digest-pinned environment are all in great shape. Two things to fix before we can accept: in `scale_model.md`, please document that `state_recovery` quarantine rows use an empty `source` string and that `quarantined_frames` counts only frame/replay quarantine failures (not those metadata rows, even though they still land in quarantine JSONL). That mismatch is why almost every strong run failed the same state-recovery test. On the platform rubric, trim at least 3 positive points — the sum is 43 and needs to be 40 or below (e.g. drop the +1 smoke-test line or lower one +3).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
| Rubric | yes | 2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
