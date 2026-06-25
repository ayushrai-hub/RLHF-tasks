# Terminus Review Report: `fstab-variant-remount-ladder`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (local 1/1) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Digest-pinned offline environment, oracle pass, Hard difficulty calibration (20% worst-model), anti-cheat fixtures, and 10/11 per-test agent pass rates on most behaviors are solid. Revise for one High blocker: `test_ladder_sparse_lane_corpus_converges` requires `lane_k2` `state_digest` to equal the `lane_k1` baseline, but `pact_f2.md` names only `lane_k3` and `lane_k4` as held-out convergence targets; the built-in driver enforces the same k1/k3/k4 set and omits `lane_k2` (`k1_driver.sh:143-146`). The general “sparse lanes reconcile against full corpus” rule does not explicitly state k2 must match the k1 digest — 1/10 agent pass on that test.

**Insights (concise):**

- `pact_f2.md:63` names k3/k4 convergence; `test_outputs.py:121-127` tests k2; `k1_driver.sh:145` driver guard matches pact_f2, not the test.
- 8/9 agent trials that changed code passed 10/11 tests; universal failure was `test_ladder_sparse_lane_corpus_converges` (`entire-report.txt:19-21,42-46`).
- `contract_hash.py` scope is inferable: instruction assigns ceiling to consumer emission (`instruction.md:7`); `test_ladder_slot4_excluded_from_digest` proves the tool digests all rows received (`test_outputs.py:138-151`).
- Monolithic pipeline bypass is theoretically possible but mitigated by pact_f2 algorithm spec, rubric negatives (-5 hardcode/static), and standard E2E debugging-task pattern.
- Automated `terminus review` blockers #24 (mkdir) and #31 (docstrings) are minor / false positive; all 11 `test_*` functions have docstrings.
- Portal rubric in `entire-report.txt:401-411` is well-formed (4 negatives, valid scores); no `rubric.txt` in task folder.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `lane_k2` sparse-corpus convergence to `lane_k1` baseline digest is tested but not explicitly specified. `pact_f2.md` names only `lane_k3` and `lane_k4` as held-out convergence targets. Instruction says sparse lanes must reconcile against the full table corpus but does not state k2 must match k1 digest. Built-in driver enforces k1/k3/k4 only. Agents consistently fixed k3/k4 and missed k2 (1/10 pass on `test_ladder_sparse_lane_corpus_converges`). | `environment/docs/pact_f2.md:63,69`; `instruction.md:7,9`; `tests/test_outputs.py:121-127`; `environment/scripts/k1_driver.sh:143-146`; `environment/profiles/lane_k2.json:3-5`; `entire-report.txt:19-21,42-46,64-65` | Add explicit pact_f2 + instruction wording: `lane_k2` (sparse fragment list) must reconcile against the full `tables/` corpus and converge to the `lane_k1` baseline `state_digest`, with corpus-authoritative slot rows taking precedence over unit-fragment overrides where they conflict. Optionally align `k1_driver.sh` guard to include `lane_k2`. |

*No additional High blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | lane_k2 sparse convergence underspecified; tests require k2 == k1 digest; pact_f2 names only k3/k4 (ChatGPT High) | **Agree** | `pact_f2.md:63` vs `test_outputs.py:121-127`; `k1_driver.sh:145` omits k2; 1/10 pass `entire-report.txt:21` |
| 2 | contract_hash.py ceiling-filter scope ambiguous; tool must hash rows received, caller enforces ceiling (ChatGPT High) | **Partially agree** | `instruction.md:6-7` separates emission ceiling from helper; `contract_hash.py:10-24` hashes all rows; `test_outputs.py:138-151` enforces; only 2/9 trials failed `entire-report.txt:48` — clarify in pact_f2, not primary blocker |
| 3 | Verifier only checks final JSON; monolithic replacement can pass (ChatGPT Medium / test-quality report) | **Partially agree** | All tests use `_run_checker()` → `verify_k9 --matrix-full` (`test_outputs.py:80-85`); instruction prohibits static writes (`instruction.md:6`); rubric -5 hardcode (`entire-report.txt:410`); standard E2E pattern — enhancement optional, not Revise driver |
| 4 | Task Instruction Sufficiency FAIL; systematic k2 ambiguity (entire-report) | **Agree** | `entire-report.txt:32-68,90-94` |
| 5 | LLMaJ `behavior_in_task_description` PASS (entire-report:96) | **Partially agree** | Most behaviors documented; k2 convergence-to-k1 digest gap remains |
| 6 | LLMaJ `behavior_in_tests` PASS (entire-report:97) | **Agree** | Tests cover pact_f2 behaviors; issue is underspec not missing coverage |
| 7 | Test quality VULNERABLE — no module/intermediate checks (entire-report:257-337) | **Partially agree** | Theoretical bypass via monolithic script; not unfair given full pact_f2 algorithm + inputs in env |
| 8 | READY TO USE recommendation (entire-report:247-250) | **Disagree** | k2 convergence spec gap drives 0% full-task agent pass despite near-complete solutions |
| 9 | Non-canonical base image warning (entire-report:133-157) | **Partially agree** | `environment/Dockerfile:1` digest-pinned `debian:bookworm-slim`; tmux/asciinema present (`Dockerfile:5,11`); acceptable for bash-primary task |
| 10 | Instruction density / navigational hint suggestion (entire-report:161-181) | **Partially agree** | Dense kit terminology; intentional for Hard task; not a blocker |
| 11 | Automated review blocker #24 missing mkdir (terminus review) | **Agree (Low)** | `tests/test.sh:1-14` lacks `mkdir -p /logs/verifier`; oracle passed — Harbor pre-creates path |
| 12 | Automated review blocker #31 missing docstrings (terminus review) | **Disagree** | All 11 `test_*` functions have one-line docstrings (`test_outputs.py:108-259`); validate warning is module-level only |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Five prose paragraphs (problem, fix/schema, lane rules, recovery, symptoms) | `instruction.md:1-11` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Incident-style ops brief referencing dossiers | `instruction.md:1-9` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes and doc refs, not module edit order | `instruction.md:3-7` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | No broken-module walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | Schema tables only in env `pact_f2.md` | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | k2 convergence to k1 digest untested in pact_f2 held-out list | Blocker #1 |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic mount-matrix / fstab debugging workflow | `task.toml:7-9` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | fstab remount-ladder digest kit; distinct reference_pattern | `task.toml:17-18` |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/environment/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | No runtime web fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY . /app/environment` | `environment/Dockerfile:19` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | `solution/` and `tests/` in `.dockerignore` | `environment/.dockerignore:6-7` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:14-16`, `tests/test.sh:8` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Local oracle 1/1; report 3/3 | `./scripts/terminus oracle`; `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes shell modules locally | `solution/solve.sh:1-62` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rewrites row_sink, slot_carry, fan_emit; runs verify_k9 | `solution/solve.sh` |
| 24 | UNCHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing `mkdir -p /logs/verifier`; no early PWD failure reward | `tests/test.sh:1-14` vs `docs/guidelines/writing-tests.md:11` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 reward only | `tests/test.sh:10-14` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | k2 == k1 digest enforced by test but not named in pact_f2 held-out list | Blocker #1 |
| 28 | CHECK | Tests check for correctness, not just format | Digest equality, band_class, recovery, decoy rejection | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | JSON/subprocess behavior only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Digest hex comparisons are required for contract | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 11 `test_*` have one-line docstrings | `tests/test_outputs.py:108-259` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives in portal rubric | `entire-report.txt:408-411` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:401-411` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format compliant | `entire-report.txt:401-411` |
| 35 | CHECK | Rubric criteria are detailed and precise | Pipeline-stage criteria with concrete actions | `entire-report.txt:401-411` |
| 36 | CHECK | Rubric criteria use positive language | Positive phrasing with negative scores for bad behavior | `entire-report.txt:401-411` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | Penalizes agent editing tests/ (standard); no pytest refs | `entire-report.txt:411` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No task.toml/instruction refs | `entire-report.txt:401-411` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:401-411` |
| 40 | CHECK | All required files present | Regular layout complete | `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/solve.sh`, `tests/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | `fstab-variant-remount-ladder/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, subcategories | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | bash/system-administration/fstab match | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 20% | `task.toml:6`, `entire-report.txt:6-7` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task (`number_of_milestones = 0`) | `task.toml:12` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not milestone | `task.toml:12` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not milestone | `task.toml:12` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not milestone | `task.toml:12` |
| 50 | CHECK | Tests are NOT baked into Docker image | `tests/` in `.dockerignore`; no COPY tests/ | `environment/.dockerignore:7`, `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/tests excluded from image | `environment/.dockerignore:6-7` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Canonical rows derived at runtime; p9_stub is decoy | `tests/test_outputs.py:34-57,215-229` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% | `entire-report.txt:6-7` |
| 55 | UNCHECK | Task is not too hard or unfair | Systematic k2 convergence gap caused 0% full passes with 10/11 partial success | `entire-report.txt:36-37,86,90-94` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 7, 24, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `run_report.json` with schema_version 1, command `verify_k9 --matrix-full` | `test_ladder_summary_emit_ceiling` | covered | `instruction.md:3`; `test_outputs.py:130-135` |
| `contract_hash.py` agrees with pact_f2 tuple normalization | `test_ladder_digest_tool_agrees` | covered | `instruction.md:6`; `test_outputs.py:108-112` |
| Sparse lanes reconcile against full table corpus | `test_ladder_sparse_lane_corpus_converges` | **gap** | `instruction.md:7`; `pact_f2.md:69` says reconcile but `pact_f2.md:63` names only k3/k4 for baseline convergence; test requires k2 == k1 (`test_outputs.py:121-127`) |
| `digest_emit_ceiling` = 3; summary `row_count` counts emitted rows only | `test_ladder_summary_emit_ceiling` | covered | `instruction.md:7`; `test_outputs.py:130-133` |
| Overflow slot_id > ceiling excluded from digest tuples | `test_ladder_slot4_excluded_from_digest` | covered | `pact_f2.md:38`; `test_outputs.py:138-151` |
| `lane_k2` lane `band_class` = 3 for slave unit carry | `test_ladder_k2_slave_profile_band` | covered | `pact_f2.md:49`; `test_outputs.py:115-118` |
| `lane_k3` workdir scoring converges to tc.mnt baseline | `test_ladder_workdir_scoring_k3_converges` | covered | `pact_f2.md:63,67`; `test_outputs.py:154-160` |
| Bind relocation canonical path `/mnt/y` | `test_ladder_bind_reloc_canonical_path` | covered | `pact_f2.md:69`; `test_outputs.py:163-191` |
| `lane_k4` duplicate recovery zero drift | `test_ladder_duplicate_recovery_zero_drift` | covered | `pact_f2.md:83`; `test_outputs.py:194-201` |
| q9_clear + arena_seed recovery preserves digest | `test_ladder_q9_anchor_recovery_preserves_digest` | covered | `instruction.md:9`; `pact_f2.md:71-81`; `test_outputs.py:204-212` |
| p9_stub interim rows are decoy only | `test_ladder_p9_interim_rows_decoy` | covered | `pact_f2.md:93-95`; `test_outputs.py:215-229` |
| Consumer strips `slave` from digest option strings | `test_ladder_slave_opts_stripped_before_digest` | covered | `instruction.md:7`; `test_outputs.py:232-259` |
| Kit modules implement pact_f2 (not static output) | — | untested (rubric only) | `instruction.md:6`; rubric `entire-report.txt:408,410` |
| `interim_trace_ids` / `summary.run_id` schema fields | — | untested | `pact_f2.md:11-12,29`; no assertion in `test_outputs.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, blocker #1, spec alignment |
| `environment/docs/pact_f2.md` | Blocker #1, spec alignment, adjudication |
| `environment/scripts/k1_driver.sh` | Blocker #1 (driver guard omits k2) |
| `environment/profiles/lane_k2.json` | Blocker #1 (sparse lane profile) |
| `environment/scripts/contract_hash.py` | Adjudication claim #2 |
| `tests/test_outputs.py` | #27, #31, all spec alignment rows |
| `tests/test.sh` | #24 |
| `environment/Dockerfile` | #15, #20 |
| `environment/.dockerignore` | #17, #50 |
| `task.toml` | #45, metadata |
| `solution/solve.sh` | #23, oracle |
| `entire-report.txt` | Agent stats, rubric, external claims |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: fstab-variant-remount-ladder/ ===
Summary: 0 error(s), 3 warning(s), 1 info
Task type detected: regular
Warnings: k1_driver.sh solution-hint patterns (reviewed — orchestration comments only);
          test_outputs.py missing module-level docstring (all test_* docstrings present)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | 4 other failures |
| terminus-claude-opus-4-8 | 0.0% (0/5) | 5 other failures |
| oracle | 100.0% (3/3 report; 1/1 local) | Deterministic |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

**Per-test pass rates (report):** `test_ladder_sparse_lane_corpus_converges` 1/10; all other tests ≥7/10 (`entire-report.txt:18-29`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular bash task; folder matches report |
| 1 Instruction | ☑ | k2 convergence gap flagged |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema, no tests/solution in image |
| 3 Oracle | ☑ | Local pass; derives via module rewrites |
| 4 Verifiers | ☑ | Canonical reward mostly; missing mkdir (#24 Low) |
| 5 Metadata | ☑ | hard/system-administration/bash/tool_specific |
| 6 Rubric | ☑ | Portal rubric in report verified; no rubric.txt |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed for k2 |
| 8 Novelty & fairness | ☑ | Multi-module pipeline; k2 ambiguity unfair at full-pass bar |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

> Needs revision. Dockerfile pinning, offline verifier setup, oracle pass, Hard difficulty calibration, and rubric negatives look solid. The blocker is spec alignment for sparse-lane convergence: `test_ladder_sparse_lane_corpus_converges` requires `lane_k2` to match the `lane_k1` baseline digest, but `pact_f2.md` only names `lane_k3` and `lane_k4` as held-out convergence targets (the driver guard matches k3/k4 only). Add explicit wording that `lane_k2` must reconcile against the full table corpus and converge to the `lane_k1` digest. Optionally clarify in `pact_f2.md` that `contract_hash.py` performs tuple normalization only and does not apply `digest_emit_ceiling` filtering.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — (#24 Low only) |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | N/A |
| Uses Internet | no | — |
| Rubric | no | — |
| Environment | no | — |
| Pinning Issues | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review fstab-variant-remount-ladder/ --report entire-report.txt`; oracle run locally._
