# Terminus Review Report: `node-stream-csv-import-build`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report; local harbor CLI unavailable) |
| **CHECK count** | 55 |
| **UNCHECK count** | 0 |

**Error categories (internal):** none

**Decision (concise):** Strong five-milestone Node/Postgres task with excellent anti-cheat (randomized feeds, probe stashing, side-channel scan), digest-pinned offline env, and full spec↔test alignment across binary decode, streaming, resume/checkpoint, upsert idempotency, changelog reconciliation, and atomic fleet claiming. Automated `terminus review` blockers (#1 combined length, #14 pip, #30 brittle stdout, #31 docstrings) are false positives on manual audit. Platform rubric correctly uses milestone format (`# Rubric 1`–`# Rubric 5`). Oracle 100% (3/3); worst-model 0% supports declared `hard`. No High or Medium blockers.

**Insights (concise):**

- ChatGPT Accept and `entire-report.txt` READY TO USE are confirmed; only Low polish remains (`codebase_size = "small"`, optional M3/M4 per-test docstrings).
- Rubric is milestone-formatted correctly for `number_of_milestones = 5` — not a non-milestone/milestone rubric mismatch.
- `pytest==8.4.1` / `pytest-json-ctrf==0.3.5` are `==`-pinned at `environment/Dockerfile:45-46`; validator regex misses them.
- M3/M4 tests use 50k rows vs instruction’s 200k target — behavior covered, scale fidelity gap only (Low).
- Checkpoint durability (fsync/atomic rename) is specified but not mechanically verified — logical after-commit ordering is tested (Low).
- `ubuntu:24.04` final stage is justified (PG16 + Node20 + Go probe build); not a revision blocker.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept; no High/Medium (ChatGPT) | **Agree** | Full artifact audit; no spec gaps, env issues, or verifier blockers found |
| 2 | `codebase_size = "minimal"` underclassified → `small` (ChatGPT / `entire-report.txt:186-204`) | **Agree** (Low only) | `task.toml:9`; multi-file env (`import.js`, `lib/`, probe, SQL, docs) — metadata polish, not blocking |
| 3 | Non-canonical `ubuntu:24.04` base (`entire-report.txt:164-182`) | **Partially agree** (not blocking) | `environment/Dockerfile:12` digest-pinned; PG16+Node20+Go combo lacks single canonical image — justified |
| 4 | All LLMaJ quality checks pass (`entire-report.txt:126-135`) | **Agree** | Cross-checked instructions, tests, Dockerfile, oracle against each named behavior |
| 5 | Test quality robust, 0/5 milestones vulnerable (`entire-report.txt:258-525`) | **Agree** | Randomized feeds, probe stashing, field-level spot checks, heap caps in `steps/milestone_*/tests/` |
| 6 | Checkpoint fsync not mechanically tested (`entire-report.txt:362-395`) | **Agree** (Low) | `steps/milestone_2/instruction.md:24-25`; `test_m2.py:156-175` checks value ≤ max committed only |
| 7 | M3 tests 50k rows vs instruction 200k (`entire-report.txt:420-421`) | **Agree** (Low) | `steps/milestone_3/instruction.md:24-26`; `test_m3.py:23-31` uses 50k |
| 8 | Instruction sufficiency FAIL for trial bTJHoXK — scramble algorithm undocumented (`entire-report.txt:103-107`) | **Disagree** (as blocker) | `steps/milestone_3/instruction.md:1-6` directs probe-based RE; 9/10 trials passed `task_specification`; intentional difficulty |
| 9 | Agent 0% both models, oracle 100% (`entire-report.txt:26-32`) | **Agree** | Worst-model 0% ≤ 20% → hard tier; oracle 3/3 |
| 10 | Automated review #1 long instruction (`review-report.md` baseline) | **Disagree** | Script sums all 5 milestone instructions (~1450 words); per-milestone each ~220–290 words, 3 paragraphs — `steps/milestone_*/instruction.md` |
| 11 | Automated review #14 unpinned pip | **Disagree** | `environment/Dockerfile:45-46` (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`) |
| 12 | Automated review #30 brittle exact string | **Disagree** | `test_m2.py:65`, `test_m3.py:31` assert `processed <N> rows` — normative stdout contract in `catalog-feed-spec.md:64-67` |
| 13 | Automated review #31 missing docstrings | **Partially agree** (not blocking) | M1/M2/M5 all methods documented; M3/M4 lack 8 method docstrings but names are informative (`test_absent_text_cell_preserves_existing_value`, etc.); validator regex misses `-> None` annotations |
| 14 | Platform rubric uses milestone headers (`entire-report.txt:530-570`) | **Agree** (correct format) | `task.toml:14` (`number_of_milestones = 5`); rubric has `# Rubric 1`–`# Rubric 5` per `docs/guidelines/rubrics.md:49-58` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Per-milestone instructions ~220–290 words, 3 paragraphs each | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering brief, not synthetic spec | `steps/milestone_1/instruction.md:1-6` |
| 3 | CHECK | No excessive markdown | Plain prose, no ##/tables | All milestone instructions |
| 4 | CHECK | No step-by-step HOW | States outcomes/contracts, not patch steps | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints/solving strategies | Probe reference is task requirement, not leaked algorithm | `steps/milestone_3/instruction.md:1-6` |
| 6 | CHECK | No design-doc tables | None in instructions | — |
| 7 | CHECK | Well specified | Goals + `catalog-feed-spec.md` behavioural contract | `environment/docs/catalog-feed-spec.md` |
| 8 | CHECK | Interesting | Binary RE, streaming, PG upsert, fleet coordination | Task design |
| 9 | CHECK | Unique | Multi-milestone binary importer theme | Task content |
| 10 | CHECK | Absolute paths | `/app/import.js`, `/var/lib/csv-importer/.checkpoint`, etc. | All instructions |
| 11 | CHECK | Task name not in instruction | Name absent | Instructions |
| 12 | CHECK | No canary string | None | Instructions |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures; build-time package fetch only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with `==` | pytest pins present | `environment/Dockerfile:45-46` |
| 15 | CHECK | Base image digest-pinned | All FROM lines `@sha256:` | `environment/Dockerfile:1,7,12` |
| 16 | CHECK | Context stays in environment | COPY under build context | `environment/Dockerfile:51-63` |
| 17 | CHECK | No ground truth in env | Probe is intentional study aid; skeleton `import.js` not solution | `environment/app/import.js` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:44-46`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) | `entire-report.txt:32` |
| 22 | CHECK | Oracle no internet | solveN.sh writes local import.js | `steps/milestone_3/solution/solve3.sh` |
| 23 | CHECK | Oracle derives via implementation | Full decoder/upsert/reconcile in heredoc | `steps/milestone_3/solution/solve3.sh:10-60` |
| 24 | CHECK | reward.txt on pass/fail | Writes 0 early + overwrites on success | `steps/milestone_1/tests/test.sh:5-18` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test_m*.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `steps/milestone_1/tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All major behaviours traced; only Low scale/fsync gaps | §5 below |
| 28 | CHECK | Tests check correctness | DB row equality, counts, heap caps, concurrency | `test_m1.py`–`test_m5.py` |
| 29 | CHECK | Behavior not implementation grep | Primary checks are runtime outcomes; `assert_no_side_channel` enforces stated no-probe rule | `harness.py:82-102` |
| 30 | CHECK | Not brittle string-only | `processed N rows` is normative stdout contract | `catalog-feed-spec.md:64-67` |
| 31 | CHECK | Informative names or docstrings | Descriptive `test_*` names; M1/M2/M5 fully documented | `steps/milestone_*/tests/test_m*.py` |
| 32 | CHECK | Rubric ≥3 negatives | 3 negatives per milestone block (15 total) | `entire-report.txt:530-570` |
| 33 | CHECK | Rubric score set | Only ±1,2,3,5 | `entire-report.txt:530-570` |
| 34 | CHECK | Rubric `Agent …, ±N` format | All lines conform | `entire-report.txt:530-570` |
| 35 | CHECK | Rubric detailed/precise | Task-specific decode/stream/upsert/reconcile/claim criteria | `entire-report.txt:530-570` |
| 36 | CHECK | Rubric positive language | Negatives describe bad agent actions directly | `entire-report.txt:535-536` |
| 37 | CHECK | Rubric no /tests/ refs | No `/tests/` path references | `entire-report.txt:530-570` |
| 38 | CHECK | Rubric no instruction.md refs | No instruction.md or task.toml refs | `entire-report.txt:530-570` |
| 39 | CHECK | Rubric no oracle/NOP | No oracle/NOP mentions | `entire-report.txt:530-570` |
| 40 | CHECK | Required files present | `environment/Dockerfile`, `task.toml`, per-milestone layout | Task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README | Task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, category, tags, milestones | `task.toml` |
| 44 | CHECK | Tags/languages/category match | `javascript`, `data-processing`, `db_interaction` | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches rates | `hard` at 0% worst-model | `entire-report.txt:22-28`; `task.toml:6` |
| 46 | CHECK | Milestone steps/ layout | `steps/milestone_1`–`milestone_5` | `task.toml:24-67` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve5.sh + wrappers | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m5.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | Each `TestMilestoneN` scores only milestone N | `test_m*.py` class names |
| 50 | CHECK | Tests not baked in image | No COPY tests/ in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | Solutions under `steps/`, not image | `environment/Dockerfile` |
| 52 | CHECK | No trivial input mutation cheat | Random seeds/nonces per run | `harness.py:29-36` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:27-28` |
| 55 | CHECK | Not unfair | Probe-based RE is explicit; agent failures are implementation (NULL upsert, overfit) not hidden verifier semantics | `entire-report.txt:85-123` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | — |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: dry-run `processed <N> rows` | `test_dry_run_reports_decoded_record_count` | covered | `test_m1.py:15-32` |
| M1: 50k import, no NULL qty, field match | `test_import_completes_and_count_matches`, `test_every_row_has_non_null_qty`, `test_specific_rows_match_decoded_feed` | covered | `test_m1.py:34-70` |
| M1: decode without probe | `test_importer_decodes_without_the_probe` | covered | `test_m1.py:72-84` |
| M2: 200k stream under 64MB heap | `test_full_dry_run_under_tight_heap` | covered | `test_m2.py:55-65` |
| M2: three resume contracts | `test_resume_contract_binary_and` | covered | `test_m2.py:76-111` |
| M2: checkpoint after commit, format `id:<n>` | `test_checkpoint_format_canonical_after_full_import`, `test_checkpoint_never_names_uncommitted_rows_under_failed_batch` | covered | `test_m2.py:140-175` |
| M2: stop options-pinner watchdog | `test_options_pinner_supervisor_is_stopped` | covered | `test_m2.py:123-138` |
| M2: checkpoint durable (fsync/rename) | — | gap (Low) | `steps/milestone_2/instruction.md:24-25`; no fsync/rename assert |
| M3: scrambled numerics, upsert idempotency | `test_clean_import_processes_50000_rows`, `test_second_run_against_same_feed_does_not_unique_key_violate`, `test_upsert_propagates_drift_in_every_column` | covered | `test_m3.py:23-78` |
| M3: absent text cell preservation | `test_absent_text_cell_preserves_existing_value` | covered | `test_m3.py:94-122` |
| M3: sequence advance to MAX(id)+1 | `test_post_import_sequence_advanced_to_max_id` | covered | `test_m3.py:80-92` |
| M3: 200k row target in instruction | `test_clean_import_processes_50000_rows` | gap (Low) | `steps/milestone_3/instruction.md:24`; `test_m3.py:25` uses 50k |
| M4: changelog reconcile, tombstone/revive/del | `test_changelog_reconciles_to_exact_final_state`, `test_intricate_trap_battery` | covered | `test_m4.py:63-105` |
| M4: stream large changelog under 64MB | `test_reconcile_streams_a_large_changelog_under_tight_heap` | covered | `test_m4.py:107-118` |
| M5: atomic feed-key claim, one winner | `test_concurrent_imports_claim_atomically` | covered | `test_m5.py:63-101` |
| M5: losers `processed 0 rows`, ledger row | `test_concurrent_imports_claim_atomically` | covered | `test_m5.py:78-98` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #40–49, #45, metadata |
| `environment/Dockerfile` | #13–#20, #50–#53 |
| `environment/docs/catalog-feed-spec.md` | #7, #27, #30 |
| `steps/milestone_*/instruction.md` | #1–#12, #27 |
| `steps/milestone_*/tests/test_m*.py` | #27–#31 |
| `steps/milestone_*/tests/harness.py` | #29, #52 |
| `steps/milestone_*/tests/test.sh` | #20, #24, #26 |
| `steps/milestone_*/solution/solveN.sh` | #21–#23 |
| `entire-report.txt` | §3 adjudication, §7 agent stats, rubric §4 #32–39 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate node-stream-csv-import-build/
Summary: 0 error(s), 25 warning(s), 5 info
Task type detected: milestone
```

Warnings are docstring-regex false positives (`-> None` annotations) and informational test.sh trailing-exit notes — not blockers.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | — |
| terminus-claude-opus-4-8 | 0.0% (0/5) | — |
| oracle | 100.0% (3/3) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Mean agent reward ~0.76 (4/5 milestones typical); M3 NULL-into-NOT-NULL upsert is dominant failure mode — implementation weakness, not spec gap (`entire-report.txt:87-107`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 5-milestone Node/JS + Postgres; matches `entire-report.txt` |
| 1 Instruction | ☑ | Per-milestone concise; `catalog-feed-spec.md` is valid contract |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, offline, no tests/solution COPY |
| 3 Oracle | ☑ | solve1–5 derive full decoder; platform 100% pass |
| 4 Verifiers | ☑ | Randomized feeds, probe stash, behaviour tests; Low docstring/fsync gaps |
| 5 Metadata | ☑ | `hard`, `data-processing`, 5 milestones; `codebase_size` Low only |
| 6 Rubric | ☑ | Platform rubric uses correct milestone `# Rubric N` format |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; 0% agent rate supports hard |
| 8 Novelty & fairness | ☑ | Multi-step RE + streaming + DB; anti-cheat strong |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really strong five-milestone task. The binary-feed reverse engineering, streaming importer under a 64 MB cap, resume/checkpoint logic, upsert idempotency, changelog reconciliation, and concurrent claim tests are all well covered. Randomized feeds, probe stashing, side-channel checks, and the oracle pass make the verifier robust. I didn’t find any blocking spec gaps or compliance issues. Optional polish: consider `codebase_size = "small"` and adding docstrings to the M3/M4 test methods for consistency with M1/M2/M5.

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
