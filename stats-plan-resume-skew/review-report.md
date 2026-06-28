# Terminus Review Report: stats-plan-resume-skew

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable in review session; static review of `solution/solve.sh` + test logic) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling, Rubric

**Decision (concise):** Strong C debugging task with excellent replay-oracle verifiers, digest-pinned offline environment, and defensible Hard calibration (0% best-model, 40% worst-model). Two real blockers: `test_resume_impl_sites_repaired` enforces SHA changes on eight exact leaf files not disclosed in `instruction.md` or any agent-visible manifest (agents hit 27/28 tests, 2/10 on this test); platform rubric references non-existent `/app/doc/shipped_impl_manifest.txt`. Automated validate warnings for missing docstrings and unpinned pip are false positives.

**Insights (concise):**

- ChatGPT High-severity finding on hidden eight-file SHA checklist is **confirmed** with file/line proof; this is the primary revision driver.
- `gcc:13-bookworm@sha256:930f2ebe…` is a **canonical** base per `docs/guidelines/dockerfxile.md` — entire-report “non-canonical base” warning is **wrong**.
- All 13 pytest functions in `tests/test_outputs.py` **have docstrings**; validate #31 warning is a false positive.
- Dockerfile pip packages use `pytest==8.4.1` / `pytest-json-ctrf==0.3.5`; validate #14 warning is a false positive.
- Platform rubric is **not** milestone-formatted (correct for `number_of_milestones = 0`) but cites a phantom manifest path agents cannot read.
- LLMaJ `behavior_in_tests: pass` contradicts itself on the impl-site SHA test — instruction never states that requirement.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #29, #55 | Verifier requires SHA256 changes on eight exact leaf modules when `pair_mismatch_count == 0`, but instructions only say defects are spread across nested helpers under `implementation_roots` and never list these files. Agents achieve full behavioral parity (27/28 tests) yet fail uniformly on the undisclosed structural checklist (2/10 pass on `test_resume_impl_sites_repaired`). | `tests/test_outputs.py:59-68` (`REQUIRED_IMPL_SITES`); `tests/test_outputs.py:456-465` (`test_resume_impl_sites_repaired`); `instruction.md:5` (vague “spread across nested helper modules”); `entire-report.txt:61,67-70,84-86` | Either (a) publish the required leaf modules in an agent-visible doc referenced from `instruction.md` (e.g. extend `/app/doc/frozen_sources.txt` counterpart or add a shipped-impl manifest in `environment/doc/`), **or** (b) drop/relax `test_resume_impl_sites_repaired` to accept functional parity only. Prefer (a) if anti-cheat on untouched buggy sources is desired. |
| 2 | High | Rubric | #35 | Platform rubric (+3 and −5 criteria) references `/app/doc/shipped_impl_manifest.txt`, which is **not shipped** in the environment, not mentioned in `instruction.md`, and not findable anywhere under `stats-plan-resume-skew/`. | `entire-report.txt:302,307`; `Glob **/shipped_impl*` → 0 files; `environment/doc/` listing has no such file | Replace phantom path with an existing agent-visible artifact (e.g. document the same eight leaf paths the verifier tracks) or remove those rubric lines. Align rubric with whichever fix is chosen for blocker 1. |

*No other High-severity blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier requires all eight specific implementation modules to change when `pair_mismatch_count == 0`, but instructions do not enumerate them (ChatGPT High) | **Agree** | `tests/test_outputs.py:59-68,456-465`; `instruction.md:5`; `entire-report.txt:61,67-70` |
| 2 | Hidden structural check is stronger than behavioral contract; some modules may have no observable effect after other fixes (ChatGPT High) | **Partially agree** | Test gates on file hashes independent of behavior (`test_outputs.py:458-465`). Report claim at `entire-report.txt:87-88` is plausible but not re-proven per-file here; fairness issue stands regardless because requirement is undisclosed. |
| 3 | Non-canonical Docker base image needs revision (entire-report Warning #1) | **Disagree** | `environment/Dockerfile:1` uses `gcc:13-bookworm@sha256:930f2ebe…`; canonical list in `docs/guidelines/dockerfxile.md:14` includes identical image+digest |
| 4 | Instruction brevity/opacity needs revision (entire-report Warning #2) | **Partially agree** | `instruction.md` is dense and contract-referential (4 paragraphs). Acceptable for Hard tier; **not** a standalone blocker — the undisclosed eight-file checklist is the fairness issue. |
| 5 | LLMaJ `behavior_in_tests: pass` — impl-site test covers instruction behavior | **Disagree** | `instruction.md` never mentions repairing specific leaf files or SHA change requirement; only `tests/test_outputs.py:456-465` enforces it |
| 6 | LLMaJ `task_specification: fail` — systemic instruction gap on impl sites | **Agree** | Same proof as claim 1 |
| 7 | Fixing `engine/plan_drive.c` contradicts frozen checksums (entire-report §4) | **Disagree as task bug** | `environment/cfg/runtime.toml:5` lists `engine/plan_drive.c` in `frozen_sources`; `environment/doc/frozen_sources.txt:2`; oracle fixes leaf modules only (`solution/solve.sh:7-107`), not `plan_drive.c` |
| 8 | Automated review blockers #14 unpinned pip, #31 missing docstrings | **Disagree** | `environment/Dockerfile:38-39` pins `pytest==8.4.1`; every `test_*` in `tests/test_outputs.py:344-471` has a docstring |
| 9 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `task.toml:11` `number_of_milestones = 0`; platform rubric at `entire-report.txt:296-308` is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct non-milestone shape per `docs/guidelines/rubrics.md:60` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Four short paragraphs, ~200 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer brief tone; no spec boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal/constraints, not a recipe | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (parity, edit scope), not HOW to patch each module | `instruction.md` |
| 6 | CHECK | No design doc style tables | None present | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Output path, schema, parity goal, edit scope, frozen paths all named | `instruction.md:1-5` |
| 8 | CHECK | Instruction is interesting | Realistic query-planner resume debugging | — |
| 9 | CHECK | Instruction is unique | Multi-module C resume-path task; no duplicate signal in repo | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No “stats-plan-resume-skew” string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only; offline PIP_NO_INDEX | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `uv==0.9.5` | `environment/Dockerfile:23,29-30,38-39` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only env subdirs | `environment/Dockerfile:43-67` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No solution/tests COPY; no answer files | `environment/Dockerfile` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | `/opt/verifier-venv`; test.sh runs pytest only | `environment/Dockerfile:35-39`, `tests/test.sh:12` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | `solve.sh` writes eight leaf fixes + rebuild + asserts; static pass expected | `solution/solve.sh` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Local file writes + build hook | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Patches C sources, rebuilds, validates JSON counters | `solution/solve.sh:7-126` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:3-17` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward pattern | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | `test_resume_impl_sites_repaired` enforces undisclosed eight-file SHA checklist | `tests/test_outputs.py:456-465`, `instruction.md:5` |
| 28 | CHECK | Tests check for correctness, not just format | Independent replay oracle + parity field equality | `tests/test_outputs.py:418-436` |
| 29 | UNCHECK | Tests verify behavior, not implementation | SHA256 source-file gate is implementation-level | `tests/test_outputs.py:456-465` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Structural JSON + replay equality appropriate | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 13 tests have docstrings | `tests/test_outputs.py:344-471` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | Four negatives (−5, −5, −5, −3) | `entire-report.txt:305-308` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:296-308` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format compliant | `entire-report.txt:296-308` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | References non-existent `/app/doc/shipped_impl_manifest.txt` | `entire-report.txt:302,307`; no file in `environment/doc/` |
| 36 | CHECK | Rubric criteria use positive language | Penalties use negative scores on bad behavior | `entire-report.txt:305-308` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:296-308` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No direct refs | `entire-report.txt:296-308` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:296-308` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | C/bash debugging/data-processing fit | `task.toml:7-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 0%, worst-model 40% ≤80%; best ≤20% per `difficulty.md` | `entire-report.txt:21-22`, `task.toml:6` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task (`number_of_milestones = 0`) | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Tests/solution excluded | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | `test_frozen_inputs_unchanged` checksums tapes/docs | `tests/test_outputs.py:344-353` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 40% | `entire-report.txt:22` |
| 55 | UNCHECK | Task is not too hard or unfair | Undisclosed eight-file edit requirement fails fairness bar | Blocker 1 proof |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 29, 35, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Produce `/app/output/plan_audit.json` via build hook | `test_matrix_binary_is_elf`, `built_audit` fixture | covered | `instruction.md:1`; `tests/test_outputs.py:325-328,356-360` |
| Schema fields per plan_audit_contract | `test_report_schema` | covered | `instruction.md:1`; `tests/test_outputs.py:363-375` |
| Manifest order (continuous then pause_resume) | `test_manifest_order` | covered | `instruction.md:1`; `tests/test_outputs.py:377-388` |
| Summary counters zero when repaired | `test_summary_counters_clean` | covered | `instruction.md:3`; `tests/test_outputs.py:391-394` |
| Pause rows match continuous on parity fields | `test_all_pause_rows_pair_ok` | covered | `instruction.md:3`; `tests/test_outputs.py:397-408` |
| stats_ok true on every row | `test_all_rows_stats_ok` | covered | `tests/test_outputs.py:411-415` |
| Match independent replay on all scenarios | `test_matches_independent_replay`, `test_hard_scenario_matches_replay` | covered | `instruction.md:3-4`; `tests/test_outputs.py:418-436` |
| Byte-identical repeated hook runs | `test_report_byte_stable` | covered | `instruction.md:5`; `tests/test_outputs.py:439-444` |
| Do not modify frozen inputs/checksum paths | `test_frozen_inputs_unchanged`, `test_non_impl_sources_pinned` | covered | `instruction.md:5`; `tests/test_outputs.py:344-353,447-453` |
| Only edit under `implementation_roots` | *(partial)* | gap | `instruction.md:5`; no test asserts edits stay in roots — only frozen-path checksums |
| Repair every nested resume-path module in verifier set | `test_resume_impl_sites_repaired` | **phantom** | Not in `instruction.md` or env docs; enforced only in `tests/test_outputs.py:59-68,456-465` |
| 18 scenarios / 36 rows | `test_stress_scenario_count` | covered | `tests/test_outputs.py:468-471` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, blocker 1, spec alignment |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50, canonical base adjudication |
| `environment/cfg/runtime.toml` | implementation_roots scope |
| `environment/doc/frozen_sources.txt` | frozen path list |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, blockers 1, spec alignment |
| `solution/solve.sh` | #21-23, oracle alignment |
| `entire-report.txt` | agent stats, rubric text, external adjudication |
| `docs/guidelines/dockerfxile.md` | canonical base rebuttal |
| `docs/guidelines/rubrics.md` | rubric format check |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate stats-plan-resume-skew/
Summary: 0 error(s), 14 warning(s), 2 info
```

Warnings for missing docstrings (#31) and unpinned pip (#14) are **false positives** — see adjudication rows 8.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Only failures on `test_resume_impl_sites_repaired` per report |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Same single-test failure pattern |
| oracle | 100.0% (3/3) | Per platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium (worst-model) / hard (best-model 0%) |
| Declared difficulty | hard |
| Tier match (#45) | yes — best-model ≤20% supports Hard per `difficulty.md:14` |

**Per-test signal:** `test_resume_impl_sites_repaired` at 2/10 runs; all other listed tests 9-10/10 (`entire-report.txt:34-61`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular C task; folder matches report domain |
| 1 Instruction | ☑ | Clear parity goal; undisclosed impl-site list is test-side gap |
| 2 Environment | ☑ | Canonical gcc base, tmux/asciinema, digest-pinned, offline pytest |
| 3 Oracle | ☑ | Static review pass; Docker oracle not run |
| 4 Verifiers | ☑ | Strong replay oracle; impl-site SHA test misaligned |
| 5 Metadata | ☑ | `number_of_milestones = 0`, tags/category fit |
| 6 Rubric | ☑ | Non-milestone flat format OK; phantom manifest path fails #35 |
| 7 LLMaJ & agent evidence | ☑ | Confirmed spec-gap on impl sites; rebutted base-image warning |
| 8 Novelty & fairness | ☑ | Fair debugging depth undermined by hidden file checklist |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the digest-pinned GCC environment, independent Python replay oracle, frozen-input checksums, and byte-stability checks are all in great shape, and the difficulty calibration looks right for a hard C debugging problem. The one thing blocking acceptance: the verifier’s `test_resume_impl_sites_repaired` requires agents to modify eight specific leaf files (the weave_u, shard_k, spool_q, and vault_r modules tracked in the test), but neither the instructions nor any shipped doc tells agents that checklist exists. Agents are routinely hitting full behavioral parity and still failing because one untouched leaf file keeps its original hash. Please either document those required implementation sites in an agent-visible file referenced from the instructions, or relax that test to reward functional correctness alone. Also update the platform rubric — it references `/app/doc/shipped_impl_manifest.txt`, which isn’t in the image; point it at whatever manifest you add or drop those lines.

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
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline generated by `./scripts/terminus review stats-plan-resume-skew/ --report entire-report.txt`._
