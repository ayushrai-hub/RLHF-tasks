# Terminus Review Report: `rust-forge-die-stage`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (platform: 100% 3/3) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Rust replay task — digest-pinned environment, normative contract for FDIE/bundles/recovery/cache, dynamic hidden fixtures, Python reference oracle, and Hard-tier calibration (0%/20% worst models) are all solid. One real blocker: `ledger_digest_hex` is tested against an exact 8-field pipe-delimited row serialization that is not documented in `forge_stage_contract.md`, causing otherwise near-complete agent runs (24/26) to fail on an invisible formatting rule. Platform rubric is flat (not milestone-blocked); all 26 tests have docstrings.

**Insights (concise):**

- Broken `environment/src/ledger.rs:151-154` omits `lineage_digest_hex` and `snapshot_id` from digest rows — agents must discover the full format from tests or guess; contract prose at `forge_stage_contract.md:293` is insufficient.
- Other digests in the same contract (`lineage_digest_hex`, `die_root_digest`) are specified algorithmically — `ledger_digest_hex` is the outlier.
- `entire-report.txt` agent analysis: 5/9 trials flagged `task_specification: fail`; top tier (24/26) failed exclusively on `ledger_digest_hex`.
- Automated `informative_test_docstrings` warnings are false positives — every `test_*` in `tests/test_outputs.py` has a docstring.
- Rubric in `entire-report.txt:377-392` uses flat `Agent …, ±N` lines (no `# Rubric 2+`); not milestone-block format.
- Test-quality notes (missing `bound_dies` sort assert, probe `lineage_digest_hex` equality) are minor coverage gaps, not fairness blockers.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | `ledger_digest_hex` serialization is tested with exact pipe-delimited rows but contract only gives vague prose | `forge_stage_contract.md:293` “deterministic lowercase hex digest from canonical ledger content…”; `tests/test_outputs.py:439-453` builds `die_id\|checksum\|tonnage\|forge_epoch\|journal_digest\|root_digest\|lineage_digest\|snapshot_id` per die (sorted by `die_id`), SHA-256 over newline-joined rows; `tests/test_outputs.py:876` asserts exact match; `solution/fixed/ledger.rs:145-157` implements same format; `environment/src/ledger.rs:151-154` uses empty lineage/snapshot (intentional bug) | Document exact row format, field order, pipe delimiter, per-die sort order, newline join, and SHA-256 step in `forge_stage_contract.md` (mirror detail level of `lineage_digest_hex` at `forge_stage_contract.md:76` and `die_root_digest` at `forge_stage_contract.md:257`) |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `ledger_digest_hex` under-specified; verifier expects 8-field pipe-delimited rows (ChatGPT High) | Agree | `forge_stage_contract.md:293` vs `tests/test_outputs.py:439-453,876`; `entire-report.txt:87-99,116-125` |
| 2 | LLMaJ `behavior_in_task_description` PASS | Partially agree | Broad contract coverage passes, but `ledger_digest_hex` algorithm absent from normative docs while enforced in tests |
| 3 | LLMaJ `Task Instruction Sufficiency` FAIL on `ledger_digest_hex` | Agree | `entire-report.txt:106-125`; 4 trials at 24/26 blocked only on this field |
| 4 | Automated review READY TO USE / no significant weaknesses | Disagree | Same `ledger_digest_hex` gap; automated pass missed spec-test mismatch |
| 5 | Test quality: probe `lineage_digest_hex` equality not asserted | Agree (non-blocker) | `forge_stage_contract.md:252`; `tests/test_outputs.py:1401-1408` checks `die_root_digest` and `die_count` only |
| 6 | Test quality: `bound_dies` sort order not explicitly tested | Agree (non-blocker) | `forge_stage_contract.md:291`; multi-die tests check totals not order |
| 7 | Verifier timeout 1500s ≈ agent 1800s (warning) | Agree (non-blocker) | `task.toml:17-20`; cold `cargo build --release` in verifier justifies headroom |
| 8 | Apt version pins may become stale (suggestion) | Agree (non-blocker) | `environment/Dockerfile:7-12`; digest-pinned base already locks repo state |
| 9 | 26 tests missing docstrings (#31 automated fail) | Disagree | All 26 `test_*` methods have docstrings, e.g. `tests/test_outputs.py:830,840,925` |
| 10 | Non-milestone task uses milestone rubric format | Disagree | `task.toml:11` `number_of_milestones = 0`; `entire-report.txt:377-392` has no `# Rubric N` headers — flat non-milestone format per `docs/guidelines/rubrics.md:60` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 short paragraphs, ~134 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer problem statement; defers detail to contract | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | No solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT not HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | `ledger_digest_hex` algorithm undocumented | `forge_stage_contract.md:293`, §2 blocker 1 |
| 8 | CHECK | Instruction is interesting | Real journal-replay / recovery systems task | — |
| 9 | CHECK | Instruction is unique | Distinct Rust FDIE/bundle replay task | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task name string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:16-17`, `tests/test.sh:14-15` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:9f841bbe…` | `environment/Dockerfile:3` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY limited to env tree | `environment/Dockerfile:19-25` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Intentional bugs only; contract is normative spec | `environment/src/ledger.rs:151-154` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in image; test.sh runs uvx offline only | `environment/Dockerfile:16-17`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Docker unavailable); platform 100% 3/3 | `entire-report.txt:24-25` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Copies fixed `.rs`, local `cargo build --locked` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Patches sources, rebuilds ELF, runs fixtures | `solution/solve.sh:7-27` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block with failure path | `tests/test.sh:4-23` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | Writes 0 or 1 | `tests/test.sh:19-22` |
| 27 | UNCHECK | All tests aligned with instructions | `ledger_digest_hex` exact format tested but not specified | §2 blocker 1 |
| 28 | CHECK | Tests check for correctness, not just format | Reference replay compares semantics end-to-end | `tests/test_outputs.py:456-626` |
| 29 | CHECK | Tests verify behavior, not implementation | CLI output assertions; ELF integrity check only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Digest equality required because algorithm is deterministic once specified | — |
| 31 | CHECK | Tests have informative names or docstrings | All 26 `test_*` have docstrings | `tests/test_outputs.py:830+` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 distinct negatives | `entire-report.txt:387-392` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All criteria use allowed scores | `entire-report.txt:377-392` |
| 34 | CHECK | Each rubric criterion one line starting with Agent, comma, score | Format matches | `entire-report.txt:377-392` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific replay/cache/FDIE criteria | `entire-report.txt:377-392` |
| 36 | CHECK | Rubric criteria use positive language | Bad behavior scored negative | `entire-report.txt:387-392` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ | No `/tests/` references | `entire-report.txt:377-392` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No `task.toml`/`instruction.md` refs | `entire-report.txt:377-392` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:377-392` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | rust/data-processing/journal-replay match | `task.toml:7-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 20% ≤20% Hard tier | `task.toml:7`, `entire-report.txt:19-21` |
| 46 | UNCHECK | steps/ layout present | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests NOT baked into Docker image | No `COPY tests/` | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | `solution/` not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Hidden dynamic fixtures + reference oracle | `tests/test_outputs.py` HIDDEN_SEED paths |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model 20% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Task is not too hard or unfair | Hidden `ledger_digest_hex` row format caused systematic near-miss failures | `entire-report.txt:87-99`, §2 blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Normal `--stage` replay with log/report emission | `test_run_alpha_*`, `test_report_v2_schema_and_digest_fields` | covered | `instruction.md:3`; `tests/test_outputs.py:839-876` |
| Recovery `--stage-recover` with rollback | `test_run_gamma_recovery_rolls_back_snapshot`, `test_corrupt_v3_recovery_has_no_partial_bind_log` | covered | `forge_stage_contract.md:170-194`; `tests/test_outputs.py:1189+` |
| Bundle parent-chain ordering | `test_bundle_replay_uses_parent_chain_before_filename_order` | covered | `forge_stage_contract.md:74`; `tests/test_outputs.py:924+` |
| Cross-pack `op_id` collapse + tombstones | `test_duplicate_op_id_collapses_*`, `test_op_tombstone_suppresses_*` | covered | `forge_stage_contract.md:89-93`; `tests/test_outputs.py:970+` |
| FDIE v3 footer digest includes chunk lengths | `test_fdie_v3_chunk_digest_includes_chunk_lengths` | covered | `forge_stage_contract.md:152`; `tests/test_outputs.py:1095+` |
| FDIE v3 scaled tonnage truncation | `test_fdie_v3_scaled_delta_tonnage_truncates_toward_zero` | covered | `forge_stage_contract.md:154`; `tests/test_outputs.py:1141+` |
| State v1→v2 migration / quarantine | `test_legacy_empty_v1_*`, `test_legacy_ambiguous_v1_*`, `test_stale_tmp_state_*` | covered | `forge_stage_contract.md:205-220`; `tests/test_outputs.py:1209+` |
| Registry cache key includes lineage + state_generation | `test_probe_cache_key_includes_lineage_and_state_generation` | covered | `forge_stage_contract.md:241`; `tests/test_outputs.py:1382+` |
| `lineage_digest_hex` algorithm | `test_equivalent_bundle_layouts_share_lineage_digest` | covered | `forge_stage_contract.md:76`; `tests/test_outputs.py:1023+` |
| `die_root_digest` algorithm | `test_probe_cache_isolates_same_lineage_different_die_root` | covered | `forge_stage_contract.md:257`; `tests/test_outputs.py:1401+` |
| **`ledger_digest_hex` exact row serialization** | `test_report_v2_schema_and_digest_fields`, `test_recovery_good_snapshot_*` | **gap** | `forge_stage_contract.md:293` prose only; `tests/test_outputs.py:439-453,876` |
| `bound_dies` sorted by `die_id` | multi-die tests | minor gap | `forge_stage_contract.md:291`; no explicit sort assert |
| Probe: lineage equal when only die root changes | `test_probe_cache_isolates_*` | minor gap | `forge_stage_contract.md:252`; not asserted |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-6, #10-12 |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50-51 |
| `environment/docs/forge_stage_contract.md` | §2 blocker 1, §5 alignment |
| `environment/src/ledger.rs` | §2 blocker 1 (broken baseline) |
| `solution/fixed/ledger.rs` | §2 blocker 1 (correct format) |
| `solution/solve.sh` | #22-23 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | §2 blocker 1, #27-31, #52 |
| `entire-report.txt` | §3 adjudication, §7 agent stats, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate rust-forge-die-stage/
Summary: 0 error(s), 27 warning(s), 3 info
```

27 warnings are all `informative_test_docstrings` false positives (docstrings present) plus `.dockerignore` info.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | `entire-report.txt:20-21` |
| terminus-claude-opus-4-8 | 20.0% (1/5) | `entire-report.txt:19-20` |
| oracle | 100.0% (3/3) | platform report; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test: `test_report_v2_schema_and_digest_fields` 1/10; `test_recovery_good_snapshot_preserves_snapshot_counts_and_digest` 1/10 — both hinge on `ledger_digest_hex`.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Rust task; report matches folder |
| 1 Instruction | ☑ | Concise; points to contract; `ledger_digest_hex` gap in contract |
| 2 Environment | ☑ | Digest-pinned Rust image; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | solve.sh patches sources + rebuilds; platform 100%; local Docker unavailable |
| 4 Verifiers | ☑ | Canonical test.sh; reference replay; docstrings present |
| 5 Metadata | ☑ | `hard` defensible at 20% worst model |
| 6 Rubric | ☑ | Flat format in platform report; 6 negatives; not milestone-blocked |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL on `ledger_digest_hex` confirmed |
| 8 Novelty & fairness | ☑ | Multi-module Rust debugging; hidden digest format is unfair |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the digest-pinned Rust environment, the contract depth on bundles/FDIE/recovery/cache, dynamic hidden fixtures, and difficulty calibration all look great. Agents are getting very close (median 23–24/26) but consistently stall on `ledger_digest_hex`. The contract says it should be a deterministic digest of canonical ledger content, but it never spells out the exact per-die row format the verifier checks: eight pipe-separated fields (`die_id`, checksum, tonnage, forge_epoch, journal digest, die-root digest, lineage digest, snapshot ID), sorted by die ID, joined with newlines, then SHA-256 hashed. Please add that serialization spec to `forge_stage_contract.md` at the same level of detail as the other digest definitions. Everything else looks ready once that’s in place.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
