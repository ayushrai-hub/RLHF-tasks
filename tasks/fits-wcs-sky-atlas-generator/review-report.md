# Terminus Review Report: `fits-wcs-sky-atlas-generator`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (not re-run locally; 100% in `entire-report.txt`) |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Strong C++ FITS/WCS task with digest-pinned GCC image, hidden verifier fixtures, independent Python reference, and 60% agent pass rates. One real blocker: `atlas-schema.md` tells agents to export `naxis1/naxis2 = 0` when `NAXIS=0`, but `test_header_only_naxis_zero` asserts `naxis1 == 1` (matching oracle/reference logic in `types.cpp:107-109` and `pixel-conventions.md:11`). All four failed agent runs stopped at 27/28 on this test only — agents following the schema doc were penalized. Fix the schema (preferred) or the test. Portal rubric is flat non-milestone format and is compliant.

**Insights (concise):**

- `atlas-schema.md:9` vs `tests/test_outputs.py:337` is a direct, reproducible spec↔verifier conflict — not agent weakness.
- `pixel-conventions.md:11` documents N/M=1 for corner math but does not say exported JSON fields should be 1; schema line 9 is the misleading part.
- Auto-review false positives on #14 (hash-pinned `requirements.lock`), #20 (pytest baked in Dockerfile), #31 (all 28 tests have method docstrings) — rejected after manual audit.
- Portal rubric (lines 329–345 in `entire-report.txt`) is **not** milestone-formatted: flat `Agent …, ±N` list, 31 positive pts, 4 negatives — correct for `number_of_milestones = 0`.
- Declared `difficulty = hard` vs observed 60% worst-model (medium tier) is informational only — not a revision blocker per policy.
- Axis-midpoint test checks count only (`test_outputs.py:347-352`); low severity, not blocking.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #55 | `atlas-schema.md` says exported `naxis1/naxis2` are 0 when `NAXIS=0`; verifier expects `naxis1 == 1` (oracle/reference set both to 1). Agents reading schema output 0 and fail 27/28. | `environment/docs/atlas-schema.md:9,19`; `tests/test_outputs.py:337`; `environment/src/types.cpp:107-109`; `environment/docs/pixel-conventions.md:11`; agent stat 6/10 on `test_header_only_naxis_zero` | Update `atlas-schema.md` to state that when `NAXIS=0`, exported `naxis1/naxis2` default to 1 for corner generation (align with `pixel-conventions.md` and reference), **or** change test + oracle to expect 0 consistently. Preferred: fix schema text. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `atlas-schema.md` contradicts `test_header_only_naxis_zero` on NAXIS=0 naxis1 value (ChatGPT / `entire-report.txt` LLMaJ) | **Agree** | `atlas-schema.md:9` "0 when NAXIS is 0"; `test_outputs.py:337` `assert data["naxis1"] == 1`; reference `keywords_from_cards` `test_outputs.py:163-165` sets 1 when naxis==0 |
| 2 | All failed agent runs 27/28, only `test_header_only_naxis_zero` fails (ChatGPT / report) | **Agree** | `entire-report.txt:42` 6/10 pass on that test; lines 66-73 identical failure pattern |
| 3 | Axis midpoint test only checks count, not coordinates (ChatGPT / test-quality review) | **Agree** (Low, non-blocking) | `test_outputs.py:347-352` `assert len(mids) == 4` only; formula in `pixel-conventions.md:13` |
| 4 | LLMaJ `behavior_in_tests: pass` (entire-report) | **Partially agree** | Most behaviors covered; NAXIS=0 exported field semantics are untested against schema doc |
| 5 | LLMaJ `behavior_in_task_description: pass` | **Partially agree** | Instruction defers to `atlas-schema.md` which contradicts verifier for NAXIS=0 export fields |
| 6 | Non-canonical GCC base image is blocking (automated review in report) | **Disagree** | `Dockerfile:1` digest-pinned; C++/CMake justifies non-tbench base; warning only |
| 7 | Corner sort not in instruction.md (automated review) | **Disagree** | `instruction.md:3` references `atlas-schema.md`; sorting at `atlas-schema.md:15` |
| 8 | Category should be scientific-computing (automated review) | **Disagree** (blocker) | `task.toml:7` `data-processing`; tags include `scientific-computing`; metadata preference only |
| 9 | Auto-review #14 unpinned pip | **Disagree** | `requirements.lock` pinned with `--hash=sha256`; `Dockerfile:20` `--require-hashes` |
| 10 | Auto-review #20 pytest not in image | **Disagree** | `Dockerfile:18-20` venv + pytest in lock; `test.sh:27` uses `/opt/verifier-venv/bin/python -m pytest`, no runtime install |
| 11 | Auto-review #31 missing docstrings | **Disagree** | All 28 `test_*` methods have one-line docstrings e.g. `test_outputs.py:333` |
| 12 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | Portal rubric (`entire-report.txt:329-345`) is flat list, no `# Rubric 2+` blocks; `number_of_milestones = 0` in `task.toml:9` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three short paragraphs, ~183 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering brief referencing normative docs, not a formal RFC | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Defers to docs; one rebuild note | `instruction.md:7` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | WHAT-only; formulas in separate docs | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Clear CLI + output paths + doc contracts | `instruction.md:1-9` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Real FITS/WCS astronomy pipeline | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct FITS lexer + WCS projection scope | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in body | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Hash-locked requirements | `requirements.lock`, `Dockerfile:20` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest on FROM | `Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY from environment/ only | `Dockerfile:24-30` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken baseline + docs only; hidden fixtures at build | `environment/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image venv; test.sh runs pytest only | `Dockerfile:18-20`, `tests/test.sh:27-28` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | 100% (3/3) in report | `entire-report.txt:25` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Copies files + local build | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Copies C++ source modules, rebuilds | `solution/solve.sh:8-14` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:5-7,30-34` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 on pytest rc | `tests/test.sh:30-34` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | NAXIS=0 export contradicts `atlas-schema.md` | Blocker 1 |
| 28 | CHECK | Tests check for correctness, not just format | Independent Python WCS reference + numeric tolerances | `tests/test_outputs.py:90-166,266-275` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Subprocess CLI + JSON output checks | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | `close()` tolerance for RA/Dec | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | 28 named tests with one-line docstrings | `tests/test_outputs.py:243-486` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives in portal rubric | `entire-report.txt:342-345` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All ±1,2,3 only | `entire-report.txt:329-345` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | All lines match format | `entire-report.txt:330-345` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific WCS/FITS trace checks | `entire-report.txt:330-345` |
| 36 | CHECK | Rubric criteria use positive language | Positive phrasing on + criteria | `entire-report.txt:330-341` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No test references | `entire-report.txt:329-345` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:329-345` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:329-345` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, allow_internet=false, languages | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | cpp/cmake/fits/wcs tags fit; category acceptable | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 60% → medium tier | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Hidden fixtures under /opt/verifier-fixtures | `Dockerfile:34-35`, `gen_fixtures.py:121` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Reference recomputes from FITS bytes | `tests/test_outputs.py:266-275` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Task is not too hard or unfair (not requiring unavailable info) | Schema doc makes passing all tests impossible when followed | Blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `build` subcommand, exit 0 on valid FITS | `test_build_tan_basic_success` | covered | `test_outputs.py:243-247` |
| `/app/output/wcs-atlas.json` schema fields | `test_atlas_schema_fields` | covered | `test_outputs.py:249-264` |
| TAN corner RA/Dec vs reference | `test_tan_corners_match_reference` | covered | `test_outputs.py:266-275` |
| Corners sorted ra_deg then dec_deg | `test_corners_sorted_by_ra_dec` | covered | `atlas-schema.md:15`, `test_outputs.py:277-283` |
| SIN projection distinct from TAN | `test_sin_projection_family`, `test_sin_differs_from_tan_same_pixels` | covered | `test_outputs.py:285-294,441-447` |
| PC/CD matrix composition | `test_pc_skew_matrix_corners`, `test_hidden_pc_sin_projection` | covered | `test_outputs.py:296-303,384-393` |
| CONTINUE merge | `test_hidden_continue_crval_tb3`, `test_hidden_continue_crval_value` | covered | `test_outputs.py:364-382` |
| HIERARCH in snapshot | `test_hidden_hierarch_snapshot_keyword` | covered | `test_outputs.py:395-402` |
| Keyword snapshot + canonical | `test_keyword_snapshot_written`, `test_snapshot_canonical_contains_crval` | covered | `test_outputs.py:305-320` |
| Idempotent byte-identical rebuild | `test_build_idempotent_bytes` | covered | `instruction.md:9`, `test_outputs.py:322-330` |
| TB3_FITS_PATH override | `test_tb3_overrides_positional_path`, `test_hidden_continue_crval_tb3` | covered | `test_outputs.py:364-375,411-418` |
| Ingest stamp file | `test_ingest_stamp_written` | covered | `test_outputs.py:404-409` |
| Missing file non-zero exit | `test_build_missing_file_fails` | covered | `test_outputs.py:457-461` |
| Fingerprint stable hex | `test_fingerprint_stable_and_non_empty` | covered | `test_outputs.py:471-483` |
| **Exported naxis1/naxis2 when NAXIS=0** | `test_header_only_naxis_zero` | **gap** | Schema `atlas-schema.md:9` says 0; test `test_outputs.py:337` expects 1 |
| Axis midpoint sky coordinates | `test_axis_midpoints_count` | partial | Count only; coords untested (low) |
| 1-based CRPIX | `test_center_pixel_near_crval`, `test_crpix_preserved_in_atlas` | covered | `test_outputs.py:354-362,426-432` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #7, spec alignment |
| `environment/docs/atlas-schema.md` | Blocker 1, claim 1 |
| `environment/docs/pixel-conventions.md` | Blocker 1, NAXIS=0 corner rule |
| `environment/src/types.cpp` | Blocker 1, oracle naxis override |
| `environment/Dockerfile` | #14-20, #50 |
| `environment/requirements.lock` | #14 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec alignment |
| `task.toml` | #43-46, #45 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, claim 2 |
| `solution/solve.sh` | #22-23 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate fits-wcs-sky-atlas-generator/
Summary: 0 error(s), 29 warning(s), 2 info
Task type detected: regular
```

Warnings are docstring false positives (class methods have docstrings) and non-milestone preference info — not blockers.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures on `test_header_only_naxis_zero` only |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Same single-test failure pattern |
| oracle | 100.0% (3/3) | — |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational; not a revision blocker) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `fits-wcs-sky-atlas-generator`; regular layout; report matches task |
| 1 Instruction | ☑ | Concise, absolute paths, doc-contract style |
| 2 Environment | ☑ | Digest-pinned GCC; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Real C++ modules; 100% in report |
| 4 Verifiers | ☑ | 28 tests; reference WCS; hidden fixtures; one spec gap |
| 5 Metadata | ☑ | allow_internet=false; cpp/cmake |
| 6 Rubric | ☑ | Portal rubric flat non-milestone format; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | NAXIS=0 failure convergence confirmed |
| 8 Novelty & fairness | ☑ | Unfair only on NAXIS=0 schema contradiction |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really strong FITS/WCS task — the digest-pinned C++ environment, hidden CONTINUE/HIERARCH fixtures, independent Python reference, and projection/matrix coverage are all well done, and agent runs at 60% look about right for the depth involved. One fix before accept: `atlas-schema.md` says exported `naxis1/naxis2` should be 0 when `NAXIS=0`, but the grader (and your reference code) expect 1 — every failed run stopped at 27/28 on exactly that mismatch. Please update the schema to document the default-to-1 export behavior (consistent with `pixel-conventions.md` for corner generation), or align the test to expect 0. Portal rubric format looks fine for a non-milestone task.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Test Dependency Location | no | — |
