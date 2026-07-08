# Terminus Review Report: `span-moment-area1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (submission report 3/3; local oracle not run — Docker unavailable) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Metadata Issues

**Decision (concise):** Strong hard C++ debugging task with digest-pinned offline env, source-rebuild verifiers, and physics-based invariants. Two real blockers: `test_byte_identical_regeneration` enforces cross-run byte identity not stated in instruction or linked docs, and `codebase_size = "small"` is objectively wrong (~1,512 C++ LOC → `large`). Platform rubric is flat (correct for non-milestone), sums to 30 positive points, and matches this task. ChatGPT Accept overstates readiness by dismissing the determinism spec gap.

**Insights (concise):**

- C++ source under `environment/` totals **1,512 lines** across 24 `.cpp`/`.hpp` files — well above the 200-line `large` threshold.
- `category = "scientific-computing"` is a weak fit; primary activity is multi-file C++ bug repair → `debugging` per taxonomy.
- Platform rubric (lines 392–405 in export) is **not** milestone format: flat `Agent …, ±N` list, no `# Rubric 2+`, 30/+9 lines, 5 negatives — passes rubric rules.
- Auditor phantom-threshold warning (`5000`, `8000`, `14000`) is a false positive — those are fixture load magnitudes in physics checks, not unstated requirements.
- Persistent disk cache at `/tmp/beam_envelope_cache.tsv` makes byte-identical reruns a hidden contract; oracle patch adds `setprecision(17)` in `store.cpp` to satisfy it.
- Prior portal note claiming rubric describes a different task is **stale** — current export rubric matches beam-envelope semantics.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | Medium | Test Alignment/Coverage Issues | #27, #55 | `test_byte_identical_regeneration` requires consecutive runs to produce byte-identical JSON; requirement is not in `instruction.md` or any doc it references (`contract.md`, `report-format.md`, `failure-behavior.md`, `load-semantics.md`). Only JSON pretty-print/rounding is documented — not cross-invocation byte identity with persistent `/tmp` cache. | `tests/test_outputs.py:326-333`; no `byte`/`identical`/`determin` in `instruction.md` or `environment/docs/`; agent stat 7/10 on this test; `environment/src/cache/store.cpp:15,45-52` persists cache across invocations within a test | Add explicit determinism/byte-identical requirement to `instruction.md` or a referenced doc (e.g. `report-format.md`), **or** remove/narrow the test |
| 2 | Medium | Metadata Issues | #44 | `codebase_size = "small"` is incorrect. C++ application source alone is 1,512 lines; Terminus thresholds are minimal (0–20), small (20+), **large (200+)**. | `task.toml:11`; `wc -l` on `environment/src/**/*.cpp` + `environment/include/**/*.hpp` = 1,512 | Set `codebase_size = "large"` |

*Additional metadata note (non-blocking alone):* `category = "scientific-computing"` — primary activity is C++ bug repair; taxonomy maps “finding/fixing bugs” → `debugging`. Recommend relabeling; not elevated to separate blocker because scientific-computing examples include “simulation debug.”

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High severity; Dockerfile digest-pinned, offline verifier, tiny env (entire-report / ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:…`; `task.toml:23` `allow_internet = false`; `tests/test.sh` no apt/pip; no runtime installs |
| 2 | ChatGPT: Debian non-canonical base not a blocker (entire-report WARNING + ChatGPT) | **Agree** | Digest-pinned `debian:bookworm-slim`; g++/cmake/make justified; warning is advisory per Harbor review |
| 3 | ChatGPT: Coordinate-normalization ambiguity not a revision blocker (ChatGPT) | **Agree** | `load-semantics.md:32` defines normalization; `instruction.md:5` references that doc; `test_amended_load_case_uses_new_segment_frame` checks physics outcome, not magic constants |
| 4 | ChatGPT: Oracle `/tmp` smoke output is polish, not blocker (ChatGPT + Harbor WARNING #2) | **Agree** | `solution/solve.sh:8-13` writes `/tmp/envelope_simple.json`; tests rebuild via `conftest.py:30-38` and run full pipeline; oracle 3/3 in export |
| 5 | ChatGPT: Missing `schema_version` / `accepted_stages` assertions are optional polish (ChatGPT + TEST QUALITY) | **Agree** | `instruction.md:5` + `contract.md:16` require `schema_version`; no test asserts it — low exploit risk; not a blocker |
| 6 | ChatGPT: **Accept** overall (ChatGPT) | **Disagree** | Blockers #1–#2 above; byte-identical gap also flagged by LLMaJ instruction-sufficiency FAIL (`entire-report.txt:82-86`) and prior portal note (`entire-report.txt:409`) |
| 7 | Harbor review: NEEDS REVISION for oracle path + base image (entire-report REVIEW REPORT) | **Partially agree** | Base image: not blocking. Oracle path: polish only. Real revision driver is spec gap #1, not Harbor’s oracle-path warning |
| 8 | LLMaJ: Instruction sufficiency FAIL — coord ambiguity, byte-identical, settlement (entire-report:54-86) | **Partially agree** | Byte-identical: **agree** (blocker). Coord ambiguity: **disagree** as blocker — spec exists, agents misread. Settlement: `load-semantics.md:8-9` documents sign convention; 7/10 pass — not blocking |
| 9 | Auditor: Tests assert thresholds `[5000, 8000, 14000]` not in instruction (#27) | **Disagree** | Values are **input load magnitudes** in dynamically written fixtures (`test_outputs.py:84,144,156`) used as analytical lower bounds, not unstated grading requirements |
| 10 | Auditor: Category `scientific-computing` mismatches → `debugging` (#44) | **Agree** | `task.toml:7`; `instruction.md:3` “Repair the C++ implementation”; `docs/task-type-taxonomy.md:29` maps bug-fix primary activity to `debugging` |
| 11 | Prior portal note: rubric describes different beam-moment/span task (`entire-report.txt:409`) | **Disagree** | Export rubric lines 392–405 reference beam-envelope, cache keying, `piecewise.cpp`, staged fixtures — matches this task |
| 12 | Prior portal note: byte-identical enforced but not in written spec (`entire-report.txt:409`) | **Agree** | Same evidence as blocker #1 |
| 13 | TEST QUALITY: ACCEPT with minor schema gaps | **Agree** | 20 behavior tests, physics invariants, source rebuild; schema gaps are Low |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 short paragraphs, ~134 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer bug-report style, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve guide | States goal + build/run + schema refs, not file-by-file fix steps | `instruction.md` |
| 5 | CHECK | No hints/answers | No oracle walkthrough or bug-location hints | `instruction.md`, `environment/README.md` |
| 6 | CHECK | No design-doc I/O tables in instruction | No mapping tables in prompt | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, output path, schema fields, doc refs | `instruction.md:3-5` |
| 8 | CHECK | Interesting | Realistic structural-analysis debugging scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify against TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/output/envelope_report.json`, doc paths | `instruction.md` |
| 11 | CHECK | Task name absent from instruction | No `span-moment-area1` string | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in app code | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:16-17` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context scoped to environment | `COPY . /app/environment/` from `environment/` | `environment/Dockerfile:19` |
| 17 | CHECK | No solution leakage in env | Docs are contracts/specs, not patch walkthroughs | `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Export: oracle 100% (3/3) | `entire-report.txt:25` |
| 22 | CHECK | Oracle no internet | patch + local build only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives from implementation | Applies `oracle.patch`, rebuilds, runs binary | `solution/solve.sh:5-13` |
| 24 | CHECK | test.sh reward block | Writes 0 then 1; failure path covered | `tests/test.sh:11-20` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward only | 0 or 1 | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instruction | Byte-identical regeneration tested but undocumented | Blocker #1 |
| 28 | CHECK | Tests check correctness | Physics invariants, staging semantics, digest | `tests/test_outputs.py`, `beam_invariants.py` |
| 29 | CHECK | Behavior not implementation grep | Runs binary, checks JSON physics | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Numeric tolerances, not long exact strings | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 20 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 5 negative lines | `entire-report.txt:401-405` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines comply | `entire-report.txt:392-405` |
| 34 | CHECK | Rubric `Agent …, ±N` format | 14 Agent lines | `entire-report.txt:392-405` |
| 35 | CHECK | Rubric detailed; positive cap ≤40 | 30 positive points (9 +lines) | `./scripts/terminus rubric-points entire-report.txt` |
| 36 | CHECK | Rubric positive language | Bad behaviors use negative scores | `entire-report.txt:401-405` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:392-405` |
| 38 | CHECK | Rubric no instruction.md/task.toml refs | None | `entire-report.txt:392-405` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:392-405` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No stray parent files | Standard task layout only (reviewer-generated reports excluded from submission) | task root listing |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Required metadata fields | All core fields present | `task.toml` |
| 44 | UNCHECK | Tags/languages/category applicable | `codebase_size` wrong; category better as `debugging`; 7 tags (warn) | `task.toml:7-11` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; worst-model 0% → hard tier | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Ground truth not in env | solution/ outside image | `environment/Dockerfile:19` |
| 52 | CHECK | Inputs not trivially mutable | Tests use tmp fixtures + rebuild; bundled fixtures read-only in practice | `tests/conftest.py`, `test_outputs.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Not too hard/unfair | Undocumented byte-identical requirement unfair at 7/10 pass | Blocker #1; `entire-report.txt:45` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 27, 44, 46, 47, 48, 49, 55 |

**Rubric format (non-milestone):** Export uses flat `Agent …, ±N` lines with **no** `# Rubric 2+` headers — correct non-milestone layout per `docs/guidelines/rubrics.md:66`. Not milestone rubric format.

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Staged updates atomic; internally consistent reports | `test_combination_recomputed_after_revision`, `test_cross_beam_cache_isolation` | covered | `test_outputs.py:221-227,365-372` |
| Rejected amendments leave committed results unchanged | `test_rejected_amendment_preserves_report` | covered | `test_outputs.py:201-208` |
| Vertical / moment equilibrium | `test_vertical_equilibrium_simple`, `test_global_moment_equilibrium` | covered | `test_outputs.py:48-64`; `load-semantics.md:44-49` |
| Amendment coordinate frame (accepted segment origin) | `test_amended_load_case_uses_new_segment_frame` | covered | `test_outputs.py:192-198`; `load-semantics.md:32` |
| Point-moment right-side discontinuity | `test_point_moment_jump_no_shear_jump`, `test_coincident_moment_udl_side_semantics` | covered | `test_outputs.py:67-94,158-161`; `load-semantics.md:36-37` |
| `report_digest` formula | `test_report_provenance_matches_envelope_revision` | covered | `test_outputs.py:348-362`; `report-format.md:44-48` |
| Fatal parse removes output | `test_fatal_parse_removes_output` | covered | `test_outputs.py:336-345`; `failure-behavior.md:3-5` |
| `schema_version` = 2 | — | gap (low) | `instruction.md:5`; no test asserts |
| `provenance.accepted_stages` count | — | gap (low) | `contract.md:23`; only `rejected_stages` checked |
| **Byte-identical regeneration across runs** | `test_byte_identical_regeneration` | **phantom** | `test_outputs.py:326-333`; not in instruction or linked docs |
| Grading output `/app/output/envelope_report.json` | used in several tests via `OUT` | covered | `test_outputs.py:25,43` |
| Settlement / deflection semantics | `test_support_settlement_reflected` | covered | `test_outputs.py:164-189`; `load-semantics.md:8-9` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blocker #1, spec alignment |
| `task.toml` | #44, #45, blocker #2, category/codebase_size |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/docs/load-semantics.md` | coord normalization, equilibrium, settlement |
| `environment/docs/report-format.md` | digest, JSON formatting (no byte-identical) |
| `environment/docs/contract.md` | schema fields |
| `environment/docs/failure-behavior.md` | fatal parse behavior |
| `environment/src/cache/store.cpp` | persistent cache, byte-identical hidden deps |
| `tests/test_outputs.py` | #27, #28, all verifier behavior |
| `tests/test.sh` | #20, #24 |
| `tests/conftest.py` | source rebuild, cache isolation between tests |
| `solution/solve.sh` | #21-23, oracle path note |
| `solution/oracle.patch` | fix semantics (cache key, amend frames, piecewise) |
| `entire-report.txt` | agent stats, rubric, LLMaJ, prior feedback |
| `docs/task-type-taxonomy.md` | category guidance |
| `docs/task-requirements.md` | codebase_size thresholds |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate span-moment-area1/
→ 0 errors, 1 warning (tags: 7 entries, recommend 3-6)
→ Task type: regular
```

```
./scripts/terminus audit span-moment-area1/ --report entire-report.txt
→ APPROVED WITH WARNINGS (#27 phantom-threshold heuristic disputed; #44 category)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | |
| terminus-claude-opus-4-8 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) | |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

**Per-test signal:** `test_byte_identical_regeneration` 7/10; `test_support_settlement_reflected` 7/10; `test_valid_amendment_after_reject_clears_stale_deflection` 7/10 — byte-identical is the clearest spec-gap correlate.

### Rubric (platform export)

| Field | Value |
|-------|-------|
| Format | Flat non-milestone (`Agent …, ±N`; no `# Rubric 2+`) |
| Positive total | 30 (cap 40 — PASS) |
| Negative count | 5 |
| Matches task | Yes — beam-envelope C++ repair criteria |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `span-moment-area1`; content is beam-envelope C++; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise, absolute paths, references docs; byte-identical gap |
| 2 Environment | ☑ | Digest-pinned Debian; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Patch+build+smoke run; 3/3 per export; `/tmp` output polish only |
| 4 Verifiers | ☑ | 20 pytest tests; rebuild fixture; reward block OK; blocker on byte-identical |
| 5 Metadata | ☑ | `codebase_size` wrong; category debatable; tags=7 warn |
| 6 Rubric | ☑ | Flat format OK; 30 pts; matches task (stale “wrong rubric” feedback rejected) |
| 7 LLMaJ & agents | ☑ | Instruction sufficiency FAIL partially upheld (byte-identical only) |
| 8 Novelty & fairness | ☑ | Multi-module C++ debug depth; byte-identical unfair until documented |
| 9 Long context | ☐ | N/A — no `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid C++ debugging task — the offline pinned environment, source-rebuild grading, and physics-based invariants are exactly what we want at hard difficulty. Oracle passes and agent rates look right. Two things before accept: (1) `test_byte_identical_regeneration` requires identical bytes on back-to-back runs, but neither the instruction nor the linked docs state that — please add an explicit determinism/byte-identity requirement (especially given the persistent `/tmp` cache) or drop the test; (2) `codebase_size` should be `large`, not `small` — there are ~1,500 lines of C++ under `/app/environment`. Optional polish: have `solve.sh` also emit `/app/output/envelope_report.json`, and consider `category = "debugging"`. Platform rubric format and content look good now.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Metadata Issues | yes | 2 |
| Instruction Styling | no | — |
| Rubric | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
