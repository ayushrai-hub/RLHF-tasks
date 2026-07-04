# Terminus Review Report: love-letter-collection-preservation-planner

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed locally (Docker unavailable); platform 100% (3/3) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** Metadata Issues

**Decision (concise):** Strong preservation-planner task with thorough verifiers, pinned Docker image, and well-documented contracts. Prior schema gaps (`migration_pairs` object shape, `schema_version: 1` in atlas/report) are fixed in current artifacts. Platform rubric is correctly flat (non-milestone) at 36 positive points (≤40). **Only real blocker:** `task.toml` has 7 tags (limit 3–6). Trim one tag to accept.

**Insights (concise):**

- `preservation-staging.md:8-13` now explicitly requires `{migration_id, primary, replica, round}` objects — stale reviewer feedback at `entire-report.txt:410` is resolved.
- Platform rubric (`entire-report.txt:389-405`) is flat `Agent …, ±N` with no `# Rubric 2+` headers — correct for `number_of_milestones = 0`.
- Verifier uses independent `reference_preservation_plan.py` oracle; 32 behavior tests with docstrings; hidden `/opt/verifier-fixtures` trap archives.
- `migration-rollup.md:12` omits explicit `sort_keys` for `rollup_hash` — minor fairness note only; not a blocker (one agent trial failed on serialization; contract pattern matches other witness hashes).
- Duplicate `environment/opt-fixtures/` vs `tests/verifier-fixtures/` is maintainability noise only (`test.sh:29-32` overwrites at runtime).
- Worst-model pass rate 60% (Claude Opus 4.8); declared `hard` vs platform `medium` is informational per policy.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Metadata Issues | #43 | `tags` array has 7 entries; schema requires 3–6 | `task.toml:12` — `["love-letters", "heirloom-archive", "format-migration", "redundancy-planning", "preservation-schedule", "index-ledger", "storage-budget"]`; `./scripts/terminus validate` warns | Remove or merge one tag (e.g. drop `love-letters` or `index-ledger`) to reach ≤6 |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: schema gaps fixed — `migration_pairs` objects + `schema_version: 1` (High) | **Agree** | `environment/contracts/preservation-staging.md:8-13` defines object keys; `preservation-atlas-schema.md:6`, `preservation-report-schema.md:6` include `schema_version: 1` |
| 2 | ChatGPT: 7 tags exceeds 3–6 limit — only remaining blocker (High) | **Agree** | `task.toml:12` (7 tags); `docs/task-requirements.md:28`; validate warning |
| 3 | ChatGPT: verifier broad and well-aligned (Medium none) | **Agree** | 32 tests in `tests/test_outputs.py`; reference oracle in `tests/reference_preservation_plan.py`; LLMaJ `behavior_in_tests` pass at `entire-report.txt:146` |
| 4 | ChatGPT: duplicate opt-fixtures redundant (Low) | **Agree** | `environment/Dockerfile:35-37` copies `opt-fixtures/`; `tests/test.sh:29-32` copies `tests/verifier-fixtures/` to same path — not blocking |
| 5 | Harbor review: tags exceed 6 (`entire-report.txt:183-203`) | **Agree** | `task.toml:12` |
| 6 | Harbor review: duplicate fixtures warning (`entire-report.txt:210-230`) | **Agree** | `Dockerfile:35-37`, `test.sh:29-32` — Low only |
| 7 | Harbor review: non-canonical Debian base (`entire-report.txt:234-251`) | **Disagree** as blocker | `Dockerfile:1` digest-pinned `debian:bookworm-slim@sha256:4724b8cc…`; tmux + asciinema installed; acceptable per `docs/reviewer-checklist-full.md:44` |
| 8 | Prior reviewer feedback: `migration_pairs` dict schema missing (`entire-report.txt:410`) | **Disagree** (stale) | Now specified at `preservation-staging.md:8-13` |
| 9 | Instruction sufficiency FAIL: `rollup_hash` serialization unspecified (`entire-report.txt:119-120`) | **Partially agree** | `migration-rollup.md:12` says "canonical body" without `sort_keys`; `preservation-report-schema.md:12` does specify `sort_keys=True` for report fingerprint; reference uses `sort_keys=True` throughout `reference_preservation_plan.py:60,202-203`. Fairness note for #55, not Revise blocker |
| 10 | Test quality: fragile-pair test weak assertion (`entire-report.txt:348-384`) | **Agree** | `test_outputs.py:151-157` only asserts `primary != replica`; oracle-backed tests elsewhere limit cheat paths — Low |
| 11 | Rubric positive total ≤40 | **Agree** | `entire-report.txt:389-401` sums to **36** positive points |
| 12 | Non-milestone task must use flat rubric (not milestone `# Rubric N` blocks) | **Agree** (passes) | No `# Rubric` headers in `entire-report.txt`; flat `Agent …, ±N` list; `task.toml:9` `number_of_milestones = 0` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose paragraphs, ~260 words | `instruction.md:1-6` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer request referencing contract docs; not LLM walkthrough | `instruction.md:1-6` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/bold/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes and doc paths, not dev steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT (artifacts, CLI, contracts) not HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input→output tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | 8 output paths, 2 CLI commands, env override, idempotency rules | `instruction.md:1-6` |
| 8 | CHECK | Instruction is interesting | Real multi-stage preservation pipeline | — |
| 9 | CHECK | Instruction is unique | No duplicate found in repo corpus | — |
| 10 | CHECK | All paths in instruction are absolute | All `/app/...` paths | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Kebab slug `love-letter-collection-preservation-planner` absent; prose title only | `instruction.md:1` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY-only build; apt packages only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `requirements.lock` hash-pinned; `pip install --require-hashes --no-deps` | `environment/Dockerfile:15-18`, `requirements.lock` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | All COPY from environment tree | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth | Broken stubs only; hidden traps in `/opt` | `environment/heirloom-preservation/lib/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages | pytest venv in image; test.sh runs pytest only | `Dockerfile:15-18`, `tests/test.sh:36-37` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3); local not run (no Docker) | `entire-report.txt:34` |
| 22 | CHECK | Oracle does not require internet | `solve.sh` copies patches + `build.sh` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Algorithmic lib patches, not hardcoded outputs | `solution/files/lib/` |
| 24 | CHECK | test.sh writes reward.txt | Canonical reward block lines 7, 39-42 | `tests/test.sh` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0/1 in reward.txt | `tests/test.sh:39-42` |
| 27 | CHECK | All tests aligned with instructions | Contracts cited in instruction match verifier assertions; staging object schema now documented | `preservation-staging.md:8-13`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness not just format | Reference oracle recomputation throughout | `tests/reference_preservation_plan.py` |
| 29 | CHECK | Tests verify behavior not implementation | Subprocess CLI + JSON output checks | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Hash/digest checks required by witness contracts | contract docs |
| 31 | CHECK | Tests have informative names or docstrings | All 32 `test_*` have one-line docstrings | `tests/test_outputs.py:25-257` |
| 32 | CHECK | Rubrics contain ≥3 negative penalty criteria | 4 negatives | `entire-report.txt:402-405` |
| 33 | CHECK | Rubric scores from {±1,2,3,5} | All lines use ±2,3,5 | `entire-report.txt:389-405` |
| 34 | CHECK | Each rubric criterion one Agent line | 17 Agent lines | `entire-report.txt:389-405` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific trace checks | `entire-report.txt:389-405` |
| 36 | CHECK | Rubric uses positive language on positives | +lines describe desired behavior; -lines penalize bad behavior | `entire-report.txt:389-405` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | `entire-report.txt:389-405` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:389-405` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP mentions | `entire-report.txt:389-405` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | UNCHECK | All other required metadata fields present | `tags` has 7 entries (limit 3–6) | `task.toml:12` |
| 44 | CHECK | Tags, languages, categories applicable | bash/build-and-dependency-management tags match content; count issue is #43 | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Field present; declared `hard` vs platform `medium` informational only | `task.toml:6`, `entire-report.txt:24-30` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoped to milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | No `COPY tests/` | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | No solution COPY; traps in `/opt/verifier-fixtures` | `Dockerfile`, `test.sh:29-32` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Hidden trap archives + oracle recomputation | `tests/verifier-fixtures/` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst-model 60% ≤80% | `entire-report.txt:29-30` |
| 55 | CHECK | Task not too hard or unfair | Spec gaps from prior cycle fixed; rollup_hash ambiguity minor | `preservation-staging.md:8-13` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 43, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Intake writes collection-snapshot.json | `test_intake_seals_collection_capture` | covered | `test_outputs.py:32-34` |
| Stable `collection_snapshot_hash` on re-intake | `test_repeat_intake_stable_folio_digest` | covered | `test_outputs.py:37-43` |
| `run_sequence` advances on duplicate scan | `test_registry_counter_advances_on_duplicate_scan` | covered | `test_outputs.py:46-52` |
| ERA-based redundancy pools (not keepsake) | `test_era_clustering_rejects_keepsake_bins` | covered | `test_outputs.py:55-58` |
| FORMAT-based migration rollup | `test_format_transcoding_not_keepsake_sort` | covered | `test_outputs.py:75-77` |
| `migration_pairs` as objects with keys | `test_mirror_pairing_round_one_transcode`, `test_staging_carries_transcode_pairs` | covered | `preservation-staging.md:8-13`; oracle match tests |
| FRAGILE pair avoidance | `test_fragile_acid_free_pairing_avoids_trap` | covered (weak assertion) | `test_outputs.py:151-157` |
| Negative MEDIA_SLOT preserved | `test_chronology_offsets_preserve_negative_slots` | covered | `test_outputs.py:175-177` |
| Wave bands by media slot | `test_vault_wave_bands_compress_slots` | covered | `test_outputs.py` |
| `within_storage_budget` | `test_byte_cap_envelope_honored_in_staging` | covered | `test_outputs.py` |
| Manifest witness binding | `test_registry_witness_binds_all_captures` | covered | `test_outputs.py` |
| Publish reads staging only (no re-scan) | implied by tamper/missing tests | covered | `test_publish_aborts_on_missing_captures` |
| `HEIRLOOM_ARCHIVE_ROOT` override | `test_heirloom_root_override_hidden_vault` | covered | `test_outputs.py` |
| Byte-identical atlas on re-publish | `test_idempotent_publish_atlas_bytes` | covered | `test_outputs.py` |
| Tampered witness rejection | `test_publish_rejects_tampered_witness_hash` | covered | `test_outputs.py` |
| All 8 instruction output paths | `test_instruction_contract_paths_materialize` | covered | `test_outputs.py` |
| Atlas/report `schema_version: 1` | atlas/report content tests | covered | schema docs + publish tests |
| `rollup_hash` canonical serialization | oracle hash match | gap (minor) | `migration-rollup.md:12` lacks explicit `sort_keys`; inferred from other contracts |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker 1 (#43), #44-45 |
| `instruction.md` | #1-12, spec alignment |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/contracts/preservation-staging.md` | External claim 1, 8; #27 |
| `environment/contracts/preservation-atlas-schema.md` | External claim 1 |
| `environment/contracts/preservation-report-schema.md` | External claim 1 |
| `environment/contracts/migration-rollup.md` | External claim 9 |
| `tests/test.sh` | #20, #24-25 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `tests/reference_preservation_plan.py` | #28, oracle witness logic |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | Agent stats, rubric, prior feedback |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: love-letter-collection-preservation-planner. ===
WARNING: task.toml: tags should have 3-6 entries (found 7)
Summary: 0 error(s), 34 warning(s), 2 info
Task type detected: regular
```

(Other warnings: test docstring false-positives from validator AST; pip line heuristic despite hash-locked `requirements.lock`.)

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model |
| oracle | 100.0% (3/3) | platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only (never blocks) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; folder `love-letter-collection-preservation-planner.` (trailing dot) |
| 1 Instruction | ☑ | 3 paragraphs; absolute paths; contract refs |
| 2 Environment | ☑ | Digest-pinned Debian; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Platform 100%; local blocked (no Docker daemon) |
| 4 Verifiers | ☑ | 32 tests; reward block; no runtime installs |
| 5 Metadata | ☑ | **Blocker:** 7 tags |
| 6 Rubric | ☑ | Flat non-milestone format; 36 pts; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency rollup_hash note = minor only |
| 8 Novelty & fairness | ☑ | Multi-stage pipeline; hidden fixtures |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this preservation planner — the contract docs are thorough, the verifier suite with hidden trap archives is well thought out, and the prior schema issues look fixed (`migration_pairs` object shape and `schema_version` in atlas/report are now explicit). The platform rubric is in the right flat format for a non-milestone task and under the positive-point cap. One small metadata fix before we can accept: `task.toml` currently lists 7 tags and the limit is 6 — please drop or merge one (e.g. `love-letters` or `index-ledger`) and you should be good to go.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Pinning Issues | no | — |
