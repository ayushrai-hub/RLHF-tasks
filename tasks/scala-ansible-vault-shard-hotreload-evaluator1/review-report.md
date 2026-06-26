# Terminus Review Report: `scala-ansible-vault-shard-hotreload-evaluator1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per platform report; not re-run locally — Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Accept. Manual re-audit overturns three automated false positives (#14, #20, #31). The Scala/JVM environment is digest-pinned, verifier deps are preinstalled in `/opt/verifier-venv`, and `test.sh` runs offline without runtime installs. Normative docs, hidden-fixture coverage, partial-fix canaries, and anti-cheat design are strong. Platform rubric (entire-report lines 312–326) is valid for a non-milestone task; `# Rubric 1` alone is permitted.

**Insights (concise):**

- Automated `validate`/`review` falsely flag docstrings and pip pinning because the docstring regex ignores `-> None:` type hints and `#14`/`#20` only inspect Dockerfile lines, not `requirements-verifier.txt` / venv install.
- Public `sample_bundle.vshard` is physically out-of-order (shard_seq 3,1,2 per `gen_vault_fixtures.py:117-118`), so `test_out_of_order_file_stores_three_shards` is valid without a separate OOO ingest in that test.
- Worst-model pass rate is exactly 80% (GPT-5.5 4/5) — at the easy-tier ceiling but not >80%; #54 passes, #45 tier mismatch is informational only.
- Platform rubric has 4 distinct negatives and 29 positive points; `# Rubric 1` header on a non-milestone task is allowed per `docs/guidelines/rubrics.md` (optional single header; no `# Rubric 2+`).
- JDK build stage uses non-canonical `eclipse-temurin` but is digest-pinned and only supplies the JRE into canonical `debian:bookworm-slim` runtime — justified for Scala/JVM.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

**Overturned automated false positives (not blockers):**

| Automated claim | Verdict | Proof |
|-----------------|---------|-------|
| #14 unpinned pip | Disagree | `environment/requirements-verifier.txt:1-2` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; `environment/Dockerfile:45-48` installs via `-r` |
| #20 pytest not in image | Disagree | `environment/Dockerfile:45-48` creates `/opt/verifier-venv`; `tests/test.sh:20` uses `/opt/verifier-venv/bin/python -m pytest`; no runtime `pip install` |
| #31 missing docstrings | Disagree | All 33 `test_*` functions have docstrings, e.g. `tests/test_outputs.py:126-127`; validator regex `def fn(...):` fails on `-> None:` annotations |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium/Low severity issues | Agree | Full artifact audit; no High-severity gaps found |
| 2 | ChatGPT: digest-pinned JVM/Debian, verifier venv, offline test.sh | Agree | `environment/Dockerfile:1-3,45-48`; `task.toml:28`; `tests/test.sh:1-29` |
| 3 | ChatGPT: clear normative docs, hidden fixtures, anti-cheat | Agree | `instruction.md:3`; `tests/test_outputs.py:481-506`; `environment/.dockerignore:8-9` |
| 4 | ChatGPT: Medium difficulty supported | Partially agree | Worst-model 80% is easy-tier boundary; acceptable for Accept, note #45 UNCHECK |
| 5 | entire-report: behavior_in_task_description PASS | Agree | `instruction.md:1-5` names symptoms + six normative docs covering all tested behaviors |
| 6 | entire-report: behavior_in_tests PASS | Agree | 33 tests map to contract docs; spot-checked CRC, precedence, reload gate, audit_hash |
| 7 | entire-report: informative_test_docstrings PASS | Agree | Every `test_*` has docstring despite validator false negatives |
| 8 | entire-report: anti_cheating PASS | Agree | `.dockerignore` excludes `solution/` and `tests/`; hidden bundles built at runtime |
| 9 | entire-report: pinned_dependencies PASS | Agree | Digest-pinned FROM, sha256-verified Scala tarball and JARs, pinned pip requirements |
| 10 | entire-report: hardcoded_solution PASS | Partially agree | Oracle copies fixed Scala sources (`solution/solve.sh:19-22`) then rebuilds — standard debugging-oracle pattern, not echo-hardcode |
| 11 | entire-report WARNING: non-canonical JDK base | Agree (non-blocking) | `environment/Dockerfile:1` — JVM build stage only; runtime is `debian:bookworm-slim@sha256:…` |
| 12 | entire-report WARNING: instruction brevity | Agree (non-blocking) | `instruction.md` is 5 lines + doc refs; sufficient as ops-ticket style with normative contracts |
| 13 | entire-report SUGGESTION: increase agent timeout | Agree (non-blocking) | `task.toml:17` `timeout_sec=900` vs `expert_time_estimate_min=90`; agents still pass at 60–80% |
| 14 | entire-report TEST QUALITY: ACCEPT | Agree | `vault_expect.py` independent oracle; partial-fix and hidden-fixture tests |
| 15 | entire-report: agent failures are implementation not spec gaps | Agree | Duplicate-count and DB-init ordering regressions in agent traces; requirements explicit in `vshard-frame-format.md` |
| 16 | Platform rubric lines 312–326 | Agree | 13 Agent lines, 4 negatives, scores ∈ {±1,2,3,5}, 29 positive pts; `rubric-validate` pass on extracted text; no `/tests/` or `instruction.md` refs |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~76 words, 4 short blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Ops-ticket style, not spec dump | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | States symptoms + doc refs; rebuild line is operational fact | `instruction.md:5` |
| 5 | CHECK | No hints/strategies | Does not name buggy files or fix order | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Clear symptoms, output path, six normative contracts | `instruction.md:1-5` |
| 8 | CHECK | Interesting | Multi-module Scala binary-protocol debugging | Task design |
| 9 | CHECK | Unique | Vault-shard hot-reload domain; no duplicate in repo | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md:1-5` |
| 11 | CHECK | Task name not in instruction | No folder/slug string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env code | Build-time package fetch only in Dockerfile | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip `==` | Requirements file fully pinned | `environment/requirements-verifier.txt:1-2` |
| 15 | CHECK | FROM digest-pinned | Both stages `@sha256:` | `environment/Dockerfile:1,3` |
| 16 | CHECK | Context in environment/ only | `COPY app/ /app/` | `environment/Dockerfile:52` |
| 17 | CHECK | No ground truth in env | README minimal; broken Scala intentional | `environment/app/README.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | venv baked; test.sh no installs | `environment/Dockerfile:45-48`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform: oracle 100% (3/3), 33/33 | `entire-report.txt:30-31` |
| 22 | CHECK | Oracle no runtime network | solve.sh copies sources + build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Rebuilds fixed Scala, runs ingest/export CLIs | `solution/solve.sh:19-29` |
| 24 | CHECK | reward.txt canonical block | mkdir, write 0 early, 0/1 at end | `tests/test.sh:4-28` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | Only 0 or 1 | `tests/test.sh:26-28` |
| 27 | CHECK | Tests aligned with instruction | All contract-doc behaviors traced to tests | §5 below |
| 28 | CHECK | Tests check correctness | CLI subprocess + `vault_expect` recomputation | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Tests run binaries, assert JSON/DB state | `tests/test_outputs.py` |
| 30 | CHECK | Assert style appropriate | Exact dict match against independently computed expected | `tests/test_outputs.py:111-117` |
| 31 | CHECK | Informative docstrings | All 33 tests documented | `tests/test_outputs.py:126+` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives in platform rubric | `entire-report.txt:322-325` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | All lines valid | `entire-report.txt:312-325` |
| 34 | CHECK | Agent-line format | 13 criteria, all `Agent …, ±N` | `entire-report.txt:312-325` |
| 35 | CHECK | Rubric detailed/precise | Task-specific module and doc references | `entire-report.txt:313-325` |
| 36 | CHECK | Positive phrasing | No "does not" negatives with positive scores | `entire-report.txt:312-325` |
| 37 | CHECK | No /tests/ in rubric | References `/app/docs/` only | `entire-report.txt:312-325` |
| 38 | CHECK | No instruction.md/task.toml in rubric | None | `entire-report.txt:312-325` |
| 39 | CHECK | No oracle/NOP in rubric | None | `entire-report.txt:312-325` |
| 40 | CHECK | Required files present | All five core files | Task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | Task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, difficulty, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Scala task, db_interaction, vault tags | `task.toml:6-12` |
| 45 | UNCHECK | Difficulty matches agent rates | Declared `medium`; worst-model 80% → easy tier (60–80%) | `task.toml:8`, `entire-report.txt:25-26` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | `.dockerignore` + no COPY tests | `environment/.dockerignore:9` |
| 51 | CHECK | Solution not in environment | Excluded from build | `environment/.dockerignore:8` |
| 52 | CHECK | Input not trivially mutable | Binary bundles; hidden fixtures generated at test time | `tests/test_outputs.py:481-499` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80% — not >80% | `entire-report.txt:25-26` |
| 55 | CHECK | Not too hard/unfair | Agents pass 60–80%; failures are implementation regressions | `entire-report.txt:72-126` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Export `/app/output/vault-hotreload-audit.json` | `test_public_tenant_alpha` | covered | `instruction.md:1`; `tests/test_outputs.py:126-136` |
| Wrong active secret versions / reload gate | `test_reload_gate_active_version_empty`, `test_api_active_version_after_reload`, `test_worker_reload_pending` | covered | `instruction.md:1`; `hotreload-policy.md` |
| Missing leak rows / unredacted preview | `test_leak_row_unredacted_preview`, `test_partial_fix_replay_only_fails_leak_detail` | covered | `instruction.md:1`; `tests/test_outputs.py:252-263` |
| reported_at_unix tracks max shard_seq | `test_reported_at_epoch_plus_max_seq` | covered | `instruction.md:1`; `audit-report-schema.md` |
| Frame CRC + transaction rollback | `test_malformed_crc_rollback`, `test_cross_bundle_conflict_rollback` | covered | `vshard-frame-format.md`; `tests/test_outputs.py:185-227` |
| Noise resync | `test_noise_resync_prefix`, `test_partial_fix_ingest_only_fails_noise_without_resync` | covered | `vshard-frame-format.md` |
| Mixed-tenant rejection | `test_mixed_tenant_rejected` | covered | `tests/test_outputs.py:215-219` |
| Material precedence env > vault_file | `test_precedence_env_beats_vault_file`, `test_hidden_fixture_precedence_shadow` | covered | `material-precedence.md` |
| Shard load order by shard_seq | `test_out_of_order_file_stores_three_shards`, `test_hidden_fixture_ooo_shard_seq` | covered | `gen_vault_fixtures.py:117-118`; `tests/test_outputs.py:350-357` |
| Tenant-scoped duplicate_skipped | `test_duplicate_skipped_tenant_scoped`, `test_shard_id_duplicate_skipped` | covered | `tests/test_outputs.py:173-182,329-338` |
| audit_hash + key order | `test_audit_hash_trailing_newline`, `test_top_level_key_order` | covered | `audit-report-schema.md` |
| Partial-fix isolation (anti single-module patch) | 8× `test_partial_fix_*` | covered | `tests/test_outputs.py:389-478` |
| Migrations before insert | `test_migrations_applied` | covered | `db-schema.md`; `tests/test_outputs.py:150-160` |
| CLI contract ingest/export | All tests via `run_ingest`/`run_export` | covered | `cli-contract.md` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, §5 |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/requirements-verifier.txt` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `tests/gen_vault_fixtures.py` | §5 OOO public bundle |
| `tests/vault_expect.py` | #28, anti-cheat |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #21, #32-39, #45, #54-55, §3 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate scala-ansible-vault-shard-hotreload-evaluator1/
Summary: 0 error(s), 34 warning(s), 1 info
```

34 warnings are docstring false positives (type-hint regex) and non-milestone preference info — not blockers.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | At easy-tier ceiling |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Medium-tier |
| oracle | 100.0% (3/3) | 33/33 tests |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (boundary) |
| Declared difficulty | medium |
| Tier match (#45) | no — informational only, not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) layout |
| 1 Instruction | ☑ | Concise ops ticket + six normative docs |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, venv verifier deps, allow_internet=false |
| 3 Oracle | ☑ | Copies fixed Scala, rebuilds, runs CLIs; platform 100% pass |
| 4 Verifiers | ☑ | 33 behavior tests, reward block, no runtime installs |
| 5 Metadata | ☑ | category/tags/languages consistent; timeout tight but non-blocking |
| 6 Rubric | ☑ | Platform rubric valid; `# Rubric 1` optional for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; failures are agent regressions |
| 8 Novelty & fairness | ☑ | Multi-bug debugging; hidden fixtures; partial-fix canaries |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The ops-ticket instruction plus six normative contract docs give agents a clear target without walking them through the fix. The Dockerfile is well set up — digest-pinned JVM/Debian stages, verifier deps baked into a venv, and `test.sh` stays offline. The test suite is especially strong: independent `vault_expect` oracle, runtime-generated hidden bundles, and partial-fix canaries that catch single-module patches. Oracle passes cleanly on platform runs and agent rates (60–80%) look reasonable, though GPT-5.5 at 80% sits right at the easy-tier boundary if you ever want to revisit the declared difficulty. I didn’t find any spec gaps, cheating paths, or rubric format issues — the single `# Rubric 1` header is fine for a non-milestone task.

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

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review scala-ansible-vault-shard-hotreload-evaluator1/ --report entire-report.txt`._
