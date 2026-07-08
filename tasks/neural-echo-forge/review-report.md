# Terminus Review Report: `neural-echo-forge`

**Generated:** 2026-07-08 17:40 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/neural-echo-forge`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt` 3/3; not re-run — Docker unavailable locally) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Instruction Styling

**Decision (concise):** Strong Rust memory-pipeline task with digest-pinned offline setup, reference-based verifiers, hidden fixtures, and a compliant flat non-milestone rubric (21/40 positive). One real blocker: `environment/docs/memory-contract.md` still documents the default CLI as ingest→export and omits the `reconcile` subcommand, while `instruction.md` (normative) and tests require ingest→reconcile→export. Fix that doc so all referenced specs agree.

**Insights (concise):**

- ChatGPT’s High-severity doc-conflict finding is confirmed with file evidence; this is the only Revise driver.
- Platform rubric is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct non-milestone format; 21 positive points ≤ 40 cap.
- Automated audit #14 (unpinned pip) is a false positive — `pytest==9.0.3` and `pytest-json-ctrf==0.5.0` are pinned on continuation lines.
- Harbor “non-canonical Rust base” warning is informational; digest-pinned `public.ecr.aws/docker/library/rust:1.85-slim` matches accepted Rust-task corpus pattern.
- LLMaJ `typos` fail on `memory-contract.md` aligns with the same doc conflict; other LLMaJ checks pass.
- Agent calibration is appropriate: worst-model 60%, oracle 100%; declared `hard` vs platform `medium` is informational only.
- `staging_digest` / byte-identical nuance from agent-failure analysis is not a spec-test blocker — instruction scopes idempotency to snapshot and output files; tests exclude digest fields from audit comparison.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling | #17, #27 | `memory-contract.md` contradicts normative instruction on default pipeline and subcommands | `memory-contract.md:5` “ingest then export”; `instruction.md:1` “ingest, then reconcile, then export”; `reconcile-contract.md:23` correct order; `tests/test_outputs.py:147-164` export fails without reconcile | Update `memory-contract.md` Command surface to ingest→reconcile→export and list `reconcile` as a subcommand |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Conflicting command-surface docs: `memory-contract.md` omits reconcile (ChatGPT High) | **Agree** | `memory-contract.md:5` vs `instruction.md:1,3` vs `reconcile-contract.md:23`; LLMaJ `typos` fail `entire-report.txt:129` |
| 2 | Verifier is strong: rebuild, hidden fixtures, reference impl, anti-cheat (ChatGPT) | **Agree** | `tests/test.sh:22-30`; `tests/echo_reference.py`; `tests/fixtures/hidden/`; `entire-report.txt:126` anti_cheating pass |
| 3 | Rubric is flat non-milestone with reasonable positive total (ChatGPT) | **Agree** | `entire-report.txt:330-347` — no `# Rubric 2+`; `./scripts/terminus rubric-points` → 21/40; 9 negatives |
| 4 | Non-milestone task incorrectly uses milestone rubric format (user query) | **Disagree** | Rubric is flat `Agent …, ±N` only; `number_of_milestones = 0` in `task.toml:9`; `docs/guidelines/rubrics.md:66` — `# Rubric 1` optional, no `# Rubric 2+` required on non-milestone |
| 5 | Non-canonical Docker base image is a blocker (Harbor review `entire-report.txt:161-186`) | **Disagree** (not a Terminus blocker) | `environment/Dockerfile:1` digest-pinned ECR Rust matches corpus Rust tasks; `docs/reviewer-checklist-full.md:44` allows credible non-canonical — Rust toolchain justification is implicit across accepted tasks |
| 6 | Instruction dense / hard to parse (Harbor warning) | **Partially agree** (Low only) | `instruction.md` is 3 dense prose blocks (~389 words); complete and within concise budget; not a Revise driver |
| 7 | `staging_digest_sha256` conflicts with byte-identical rerun guarantee (agent-failure analysis `entire-report.txt:103`) | **Partially agree** (not a blocker) | `instruction.md:5` limits byte-identical scope to “snapshot and output files except snapshot_seq and … export_generation”; `tests/test_outputs.py:287-290` pops digest fields from audit compare |
| 8 | Pip deps unpinned (#14 audit fail) | **Disagree** (false positive) | `environment/Dockerfile:15-17` `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` |
| 9 | Rubric negative phrasing fails #36 (automated `review` script) | **Disagree** | `entire-report.txt:339-347` use bad-behavior descriptions with negative scores — compliant per `rubrics.md:41` |
| 10 | `audit-report.md` stray file (#41) | **Disagree** | Generated locally by audit run; not part of task submission |
| 11 | Task name in instruction (#11) | **Partially agree** (checkbox only) | `instruction.md:1` names `neural-echo-forge` as required CLI binary; Medium severity, not a Revise driver alone |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose blocks, ~389 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer brief tone; defers schemas to `/app/docs/` | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States WHAT (pipeline stages, paths), not algorithm steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear CLI, paths, stages, doc references | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic LLM memory compiler exercise | `instruction.md`, `environment/docs/` |
| 9 | UNCHECK | Instruction is unique | Corpus uniqueness not verified from artifacts | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | UNCHECK | Task name does not appear in instruction.md | Folder/binary name `neural-echo-forge` appears as required CLI name | `instruction.md:1` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build only apt/pip/COPY local scaffold | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` | `environment/Dockerfile:15-17` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | rust:1.85-slim digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only env subtree | `environment/Dockerfile:28-33` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are contracts/schemas; no golden outputs | `environment/docs/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:14-17`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report: oracle 100% (3/3) | `entire-report.txt:28` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh copies Rust sources and `cargo build --locked` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Six algorithmic Rust modules compiled in solve.sh | `solution/solve.sh:22-35` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Writes 0 upfront, 1/0 after pytest; compile-fail path | `tests/test.sh:8-35` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | Binary reward pattern | `tests/test.sh:31-35` |
| 27 | CHECK | All tests are aligned with instructions | Tests trace to instruction + referenced docs; one env doc typo is author fix, not phantom test | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Reference impl comparison, behavioral subprocess checks | `tests/echo_reference.py`, `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Subprocess on built binary; no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Dynamic reference oracle; property checks on ordering/winners | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 9 negatives | `entire-report.txt:339-347` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:330-347` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 18 properly formatted lines | `entire-report.txt:330-347` |
| 35 | CHECK | Rubric criteria are detailed and precise | 21 positive pts ≤ 40 cap | `entire-report.txt:330-347` |
| 36 | CHECK | Rubric criteria use positive language | Bad behaviors use negative scores | `entire-report.txt:339-347` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:330-347` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:330-347` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:330-347` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean submission layout | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | Core fields + `allow_internet = false` | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `data-processing`, `rust`, memory-pipeline tags fit | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard` present; worst-model 60% → medium tier — informational only | `task.toml:6`, `entire-report.txt:18-24` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/; `.dockerignore` excludes tests | `environment/Dockerfile`, `environment/.dockerignore:10` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | `.dockerignore` excludes `solution/`, `tests/` | `environment/.dockerignore:9-10` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Hidden fixtures mounted at test time; echo-mutate shuffle | `tests/test_outputs.py`, `environment/scripts/echo-mutate.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% ≤ 80% | `entire-report.txt:23-24` |
| 55 | CHECK | Task is not too hard or unfair | Spec complete in docs; single fixable doc conflict | `instruction.md`, companion docs |

### Quick copy-paste

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 11, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Default run: ingest → reconcile → export | `test_reconcile_report_written_by_subcommand`, `test_export_requires_reconcile_report` | covered | `instruction.md:1`; `tests/test_outputs.py:147-168` |
| Write ingest-staging.json before snapshot | `test_staging_ledger_written_by_ingest` | covered | `instruction.md:3`; `tests/test_outputs.py:175+` |
| Export requires snapshot + staging + reconcile | `test_export_requires_snapshot`, `test_export_requires_staging_ledger`, `test_export_requires_reconcile_report` | covered | `instruction.md:1,3`; `tests/test_outputs.py:163-210` |
| Temporal precedence / drink_pref winner | `test_drink_pref_winner_is_latest_temporal` | covered | `tests/test_outputs.py:233-239` |
| Semantic dedup hobby | `test_semantic_dedup_hobby` | covered | `tests/test_outputs.py:241-246` |
| Correction chains / cycles / cross-group | `TestAdversarialTraps` hidden fixture tests | covered | `tests/test_outputs.py:294+` |
| Rerun idempotency (except seq fields) | `test_rerun_unchanged_inputs_byte_identical` | covered | `instruction.md:5`; `tests/test_outputs.py:248-291` |
| NEF_POLICY_PATH absolute or exit 2 | `test_relative_policy_path_rejected` | covered | `instruction.md:3`; `tests/test_outputs.py` |
| Vault rows staged but not exported | `test_staging_vault_exceeds_export_records`, `test_superseded_not_in_export` | covered | `tests/test_outputs.py` |
| memory-contract.md command surface (ingest→export only) | — | **gap in env doc** (not test phantom) | `memory-contract.md:5` contradicts instruction; tests enforce reconcile |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, blocker 1, spec alignment |
| `environment/docs/memory-contract.md` | Blocker 1, adjudication #1 |
| `environment/docs/reconcile-contract.md` | Blocker 1, spec alignment |
| `environment/Dockerfile` | #13-16, #20, adjudication #8 |
| `task.toml` | #42-45, #46-49 N/A |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `tests/echo_reference.py` | #28-29, anti-cheat |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats, rubric |
| `environment/.dockerignore` | #50-51 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate neural-echo-forge/
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | |
| oracle | 100.0% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `neural-echo-forge` matches report; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Dense but complete; doc conflict in companion file |
| 2 Environment | ☑ | Digest-pinned Rust base, tmux+asciinema, offline, no tests/solution in image |
| 3 Oracle | ☑ | Algorithmic Rust solve.sh; 100% per export (not re-run locally) |
| 4 Verifiers | ☑ | Canonical reward block, reference oracle, 26 tests with docstrings |
| 5 Metadata | ☑ | `allow_internet = false`, category/tags fit |
| 6 Rubric | ☑ | Flat non-milestone format; 21/40 positive; 9 negatives |
| 7 LLMaJ & agent evidence | ☑ | `typos` fail confirms doc conflict; agent rates appropriate |
| 8 Novelty & fairness | ☑ | Multi-stage pipeline; anti-cheat strong |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the Rust scaffold, reference-based verifiers, hidden fixtures, and rubric all look great, and agent pass rates feel about right for the difficulty. One fix before we can accept: `/app/docs/memory-contract.md` still says the default command runs ingest then export and only lists those two subcommands, but the instruction and tests require ingest → reconcile → export with `reconcile` as its own stage. Please update that doc’s Command surface section so it matches `instruction.md` and `reconcile-contract.md`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Uses Internet | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
