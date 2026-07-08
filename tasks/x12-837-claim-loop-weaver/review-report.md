# Terminus Review Report: `x12-837-claim-loop-weaver`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass (0 errors, 1 false-positive pip warning) |
| **Oracle** | pass (platform 3/3; local oracle timed out at 120s — platform evidence used) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** No blocking spec, verifier, rubric, environment, or difficulty issues found. Instruction delegates to normative `/app/docs` contracts; tests use an independent Python reference weaver with adversarial mutations; platform rubric is a correct flat non-milestone list at 12 positive points (≤40 cap) with 7 negatives. Harbor “non-canonical base” and automated audit #14/#41 findings are false positives on re-audit.

**Insights (concise):**

- Strong Go/X12 debugging task: ingest → reconcile → export pipeline with ~14 intentional bugs across edi/, weave/, reconcile/, and main.go.
- Platform rubric uses correct **flat** format for `number_of_milestones = 0` — no `# Rubric N` milestone blocks; 12 positive pts, 7 negatives.
- Dockerfile uses the **canonical** `golang:1.24-bookworm` digest listed in `docs/guidelines/dockerfxile.md:11` and `validate_task.py:67`.
- Pip packages are pinned (`pytest==9.0.3`, `pytest-json-ctrf==0.5.0`); validator warning is a line-wrapping false positive.
- Agent failures (snapshot schema, inherited_pointers timing, pipe-separator bug) are documented in `weave-snapshot.md` and `837-weave.md` — implementation misses, not hidden verifier semantics.
- Worst-model pass rate 60% (Claude Opus 4.8); GPT-5.5 at 80% — neither exceeds 80% rejection threshold.
- `task.toml` declares `hard` while platform classifies `medium` — informational only, not a blocker.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High/Medium blockers; Accept | **Agree** | Full artifact audit; rubric 12/40; docs cover tested semantics; oracle 100% in report |
| 2 | ChatGPT: Dockerfile FROM digest-pinned golang — no base-image blocker | **Agree** | `environment/Dockerfile:1` digest `1a6d4452…` matches canonical list `dockerfxile.md:11`, `validate_task.py:67` |
| 3 | ChatGPT: Snapshot/pointer misses are agent errors, not hidden verifier behavior | **Agree** | `weave-snapshot.md:21-27` specifies `claims` array and `inherited_pointers` at LX open; `test_outputs.py:107-138` |
| 4 | ChatGPT: Optional typos in explanation fields; optional worked example in weave-snapshot.md | **Agree (Low only)** | `entire-report.txt:4-18` explanation fields present; `weave-snapshot.md` has schema table but no JSON example — polish only |
| 5 | Harbor REVIEW REPORT: Non-canonical Docker base → NEEDS REVISION | **Disagree** | Exact canonical golang digest; Harbor referenced wrong registry expectation |
| 6 | Harbor REVIEW REPORT: Generic task directory name "tbench-task" | **Disagree as blocker** | Folder is `x12-837-claim-loop-weaver`; Harbor report used export path alias — Low naming note only |
| 7 | Harbor TEST QUALITY: TB3_WEAVE_STATE test only negative case | **Agree (Low only)** | `test_outputs.py:407-428` asserts digest mismatch when ledger removed; default-path ledger tests cover happy path |
| 8 | LLMaJ `behavior_in_task_description`: PASS | **Agree** | `instruction.md:1-3` + docs cover all tested behaviors per quality check lines 108-117 |
| 9 | LLMaJ `behavior_in_tests`: PASS | **Agree** | 21 test methods map to instruction/docs requirements — see §5 |
| 10 | Agent analysis: Instruction Sufficiency FAIL | **Disagree as blocker** | 2/3 trials passed task_specification; failures trace to schema/timing details documented in `weave-snapshot.md` |
| 11 | Agent analysis: GzfgPXQ pipe-separator cascade is spec gap | **Partially agree** | Dense cross-referencing required but ISA re-read is in `837-weave.md`; agent diagnostic failure, not untested requirement |
| 12 | Automated audit #14: Unpinned pip | **Disagree** | `environment/Dockerfile:12-14` `pytest==9.0.3`, `pytest-json-ctrf==0.5.0`; audit checks line-by-line without continuation |
| 13 | Automated audit #41: Stray audit-report.md | **Disagree** | `audit-report.md` is reviewer-generated artifact, not author submission content |
| 14 | User concern: non-milestone task in milestone rubric format | **Disagree (no issue)** | `entire-report.txt:408-419` flat `Agent …, ±N` list; no `# Rubric N` headers; `task.toml:9` `number_of_milestones = 0` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 paragraphs, ~264 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational task brief, not spec dump | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Describes goal + doc references only | `instruction.md` |
| 5 | CHECK | No hints/strategies | No solve walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, subcommands, doc contracts named | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Realistic healthcare EDI claim-weaving scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | No task name in instruction | No folder/slug name | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local COPY only | `environment/Dockerfile:28-32` |
| 14 | CHECK | Pinned pip deps | `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` | `environment/Dockerfile:12-14` |
| 15 | CHECK | Digest-pinned FROM | Canonical golang `@sha256:1a6d4452…` | `environment/Dockerfile:1`, `dockerfxile.md:11` |
| 16 | CHECK | Build context scoped | COPY only go.mod, cmd/, internal/, docs/, data/ | `environment/Dockerfile:28-32` |
| 17 | CHECK | No ground truth in env | Intentional bugs; docs are contracts not golden output | `environment/internal/weave/engine.go:219`, `weave-snapshot.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:12-14`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle offline | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | Patches 14 Go source files, rebuilds binary | `solution/solve.sh:10-50` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on failure and success | `tests/test.sh:6-27` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:23-27` |
| 27 | CHECK | Tests aligned with instruction/docs | All assertions trace to instruction + `/app/docs` | §5 below |
| 28 | CHECK | Tests check correctness | Full output equality vs reference weaver | `tests/test_outputs.py:140-146` |
| 29 | CHECK | Behavior not implementation grep | Runs binary, compares structured output | `tests/test_outputs.py:59-77` |
| 30 | CHECK | No brittle string matching | Reference-model structural comparison | `tests/test_outputs.py:140-146` |
| 31 | CHECK | Informative test docstrings | All 21 test methods documented | `tests/test_outputs.py:100-411` |
| 32 | CHECK | ≥3 rubric negatives | 7 negatives | `entire-report.txt:413-419` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:408-419` |
| 34 | CHECK | Rubric Agent format | 12 properly formatted lines | `entire-report.txt:408-419` |
| 35 | CHECK | Rubric detailed; positive cap | 12 positive pts ≤ 40 | `./scripts/terminus rubric-points entire-report.txt` |
| 36 | CHECK | Positive rubric language | Negative scores use negative phrasing for bad behavior | `entire-report.txt:413-419` |
| 37 | CHECK | Rubric no /tests/ refs | No `/tests/` or pytest refs | `entire-report.txt:408-419` |
| 38 | CHECK | Rubric no metadata/instruction refs | No task.toml/instruction.md | `entire-report.txt:408-419` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:408-419` |
| 40 | CHECK | Required files present | All standard paths exist | task tree |
| 41 | CHECK | No stray parent files | Clean task root (instruction, task.toml, env, solution, tests) | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Go/X12/EDI/healthcare; data-processing fits EDI weaving | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; platform medium informational | `task.toml:6`, `entire-report.txt:21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/; .dockerignore excludes | `environment/Dockerfile`, `environment/.dockerignore:1-2` |
| 51 | CHECK | Solution not accessible | `.dockerignore` excludes solution/ and tests/ | `environment/.dockerignore:1-2` |
| 52 | CHECK | Agent cannot trivially cheat | Reference weaver + seed mutations + hidden fixture + SHA-256 fixture checks | `tests/test_outputs.py:36-40,370-405` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:26-27` |
| 55 | CHECK | Not unfair | Edge cases documented; agent failures are implementation precision | `entire-report.txt:65-104`, docs |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / docs) | Test(s) | Status | Proof |
|----------------------------------|---------|--------|-------|
| Output files woven-claims.json, weave-summary.json, errors.log | `test_output_files_exist` | covered | `instruction.md:1`, `test_outputs.py:101-105` |
| weave-snapshot.json on ingest | `test_weave_snapshot_written` | covered | `instruction.md:1`, `test_outputs.py:107-113` |
| ingest exits 0 with skipped segments | `test_ingest_exits_zero_when_segments_skipped` | covered | `instruction.md:3`, `test_outputs.py:115-121` |
| manifest_fingerprint SHA-256 of manifest bytes | `test_snapshot_manifest_fingerprint_after_ingest` | covered | `weave-snapshot.md:20`, `test_outputs.py:123-129` |
| inherited_pointers captured at LX open | `test_snapshot_stores_inherited_pointers_at_lx_open` | covered | `weave-snapshot.md:27`, `test_outputs.py:131-138` |
| claims as array in snapshot | `test_weave_snapshot_written` | covered | `weave-snapshot.md:21`, `test_outputs.py:112` |
| ISA delimiter re-read (pipe shard) | `test_pipe_separator_shard_parsed` | covered | `instruction.md:2`, `test_outputs.py:148-153` |
| LX ordering by lx_sequence | `test_service_line_lx_ordering`, `test_Agent_fails_seed_lx_shuffle_ordering` | covered | `test_outputs.py:155-164,370-385` |
| Diagnosis pointer inheritance | `test_diagnosis_pointer_inheritance_on_second_line` | covered | `instruction.md:2`, `test_outputs.py:166-174` |
| Frequency-7 supersession + chained REF*F8 | `test_Agent_fails_frequency_supersession_removes_prior_claim`, `test_Agent_fails_chained_frequency_supersession` | covered | `test_outputs.py:284-342` |
| NM1 U+00A0 normalization | `test_Agent_fails_nbsp_patient_name_normalization` | covered | `test_outputs.py:222-229` |
| Raw malformed segment text in errors.log | `test_Agent_fails_malformed_segment_preserved_in_errors_log` | covered | `test_outputs.py:231-240` |
| errors.log sorted lexicographically | `test_Agent_fails_errors_log_lines_sorted_alphabetically` | covered | `test_outputs.py:242-252` |
| Exit code 3 on default/export with skips | `test_Agent_fails_exit_code_three_on_skipped_segments` | covered | `instruction.md:3`, `test_outputs.py:273-282` |
| Export must not re-open shards | `test_Agent_fails_export_errors_from_snapshot_after_shard_mutation`, `test_Agent_fails_export_without_reingest_after_shard_mutation` | covered | `weave-snapshot.md:9`, `test_outputs.py:254-368` |
| weave-ledger.json written on ingest | `test_ledger_written_after_ingest` | covered | `weave-snapshot.md:31`, `test_outputs.py:196-207` |
| errors_digest / export_epoch from ledger | `test_export_summary_errors_digest_from_ledger` | covered | `weave-snapshot.md:41-42`, `test_outputs.py:209-218` |
| Idempotent output bytes | `test_idempotent_output_bytes` | covered | `test_outputs.py:176-186` |
| TB3_WEAVE_STATE isolated directory | `test_tb3_isolated_state_requires_ledger_for_export_summary` | covered | `weave-snapshot.md:33`, `test_outputs.py:407-428` |
| Post-supersession summary counts | `test_Agent_fails_summary_counts_post_supersession`, `test_hidden_validate_post_supersession_line_count` | covered | `test_outputs.py:304-405` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/weave-snapshot.md` | #17, spec alignment, rubric adjudication |
| `environment/docs/837-weave.md` | spec alignment |
| `solution/solve.sh` | #21-23 |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats |
| `docs/guidelines/dockerfxile.md` | #15 canonical base |
| `terminus/scripts/validate_task.py` | #15 CANONICAL_BASE_IMAGES |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate x12-837-claim-loop-weaver/
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — false positive (packages pinned on continuation lines)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst model |
| terminus-gpt5-5 | 80.0% (4/5) | Best model |
| oracle | 100.0% (3/3) | Platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | differ — informational only |

### Rubric positive points

| Field | Value |
|-------|-------|
| Positive point total | 12 |
| Cap | 40 |
| Status | PASS (12/40) |
| Format | Flat non-milestone (no `# Rubric N` blocks) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `x12-837-claim-loop-weaver` matches task content |
| 1 Instruction | ☑ | Concise, doc-delegated, absolute paths |
| 2 Environment | ☑ | Canonical golang digest; pip pinned; tmux+asciinema; allow_internet=false |
| 3 Oracle | ☑ | Platform 100%; solve.sh patches real Go sources |
| 4 Verifiers | ☑ | Reference weaver; 21 tests; reward block canonical |
| 5 Metadata | ☑ | Go/data-processing tags fit; hard vs medium informational |
| 6 Rubric | ☑ | Flat format; 12/+7 negatives; ≤40 cap |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; agent failures are implementation misses |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; anti-cheat strong |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one. The Go/X12 claim-weaving pipeline is well thought out — clear instructions, solid normative docs for snapshot and export behavior, and tests that compare against an independent reference weaver with good adversarial coverage. The Dockerfile uses the canonical pinned golang base, verifier deps are in the image, and the rubric is a clean flat non-milestone list. I didn't find any blocking spec gaps or cheating paths. Optional polish: a small JSON worked example in weave-snapshot.md for `claims` array and `inherited_pointers` at LX open would help future agents, and the submission explanation fields have a few typos.

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

---

_Report enriched after manual audit per `prompt.md`. Baseline generated by `./scripts/terminus review`._
