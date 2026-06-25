# Terminus Review Report: `vlq-event-tape-rollup`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** none

**Decision (concise):** Accept. C++ VLT1 rollup debugging task with digest-pinned Docker base, `allow_internet = false`, verifier deps baked into the image, tests/solution excluded from runtime, and 12 behavior tests that rebuild from source and compare against an independent Python reference. Oracle passes locally (reward 1.0). GPT-5.5 at 20% supports declared `hard` per `docs/guidelines/difficulty.md`. Automated blockers #4, #14, #31, and #45 are false positives on re-audit. No High-severity spec, env, oracle, or verifier gaps found.

**Insights (concise):**

- `validate_task.py` docstring regex misses `-> None:` annotations; all 12 `test_*` functions have docstrings (`tests/test_outputs.py:202-357`).
- `review_checklist.py` uses `max(agent_rates)` for “worst model” — incorrect; GPT-5.5 at 20% (not Claude 80%) sets the Hard tier floor.
- `entire-report.txt` line 1 claim of “untested warm-cache fingerprint invalidation” is wrong — `test_vlt_warm_lane_fingerprint_invalidation` exists and ran 6/10 agent trials.
- Python-slim base with g++/cmake/ninja + pytest venv is a credible dual-language pattern (C++ agent work + Python verifier).
- Rubric criteria appear in `entire-report.txt:240-258` (portal submission); no `rubric.txt` in task folder → checkboxes #32–39 N/A.
- Six planted bugs span endianness, cache fingerprinting, zigzag/fold/peek, tally filter, row serialization, and journal tail binding — all contract-documented and tested.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

**Low (non-blocking):**

| Item | Proof | Note |
|------|-------|------|
| Missing module-level docstring | `tests/test_outputs.py:1-6` | All 12 `test_*` functions have docstrings; satisfies #31 |
| Validator pip warning | `environment/Dockerfile:27-29` | False positive — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` on continuation lines |
| Non-canonical Python base for C++ task | `environment/Dockerfile:1` | Defensible: verifier needs Python; g++/cmake/ninja installed for agent |
| Verifier timeout 1200s | `task.toml:20` | Generous for small rebuild + 12 tests; not unfair |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium/Low issues | Agree | Full artifact re-audit; no High gaps |
| 2 | ChatGPT: digest-pinned Docker, `allow_internet = false`, tests/solution excluded | Agree | `task.toml:27`, `environment/Dockerfile:1`, no `COPY tests/` or `COPY solution/` |
| 3 | ChatGPT: warm fingerprint invalidation directly exercised | Agree | `tests/test_outputs.py:328-354` `test_vlt_warm_lane_fingerprint_invalidation` |
| 4 | ChatGPT: base-image/timeout notes not blocking | Agree | Non-canonical base justified; timeout is Low only |
| 5 | entire-report L1-2: blockers = non-canonical base + untested warm invalidation | Disagree | Base is digest-pinned Python+build toolchain (justified); invalidation test at `tests/test_outputs.py:328` |
| 6 | entire-report L3: Hard difficulty, solvable, oracle 100% | Agree | `task.toml:6`, `entire-report.txt:3-13`; local oracle reward 1.0 |
| 7 | entire-report L7-9: Claude 80%, GPT 20% | Agree | `entire-report.txt:7-9` |
| 8 | entire-report L31: `test_vlt_warm_lane_fingerprint_invalidation` 6/10 | Agree | Hardest edge case; contract-covered; agent implementation gap not spec gap |
| 9 | entire-report L54: instruction sufficient, no systematic spec issues | Agree | `vlt_contract.md:16-20` warm invalidation; agent analysis L54-55 |
| 10 | Quality: behavior_in_task_description PASS | Agree | `instruction.md:1-5` + `vlt_contract.md` cover all tested fields |
| 11 | Quality: behavior_in_tests PASS | Agree | 12 tests; no phantom requirements found |
| 12 | Quality: anti_cheating PASS | Agree | No tests in image; ref_caps in `/tests/` only; binary rebuild enforced |
| 13 | Quality: hardcoded_solution PASS | Agree | `solution/solve.sh:4-13` applies six C++ patches then rebuilds |
| 14 | Validation warning: step/hint pattern (#4) | Disagree | `instruction.md:3` “then run” states deliverable/flags, not debug walkthrough |
| 15 | Validation warning: unpinned pip (#14) | Disagree | `environment/Dockerfile:28-29` uses `==` pins |
| 16 | Validation warning: missing docstrings (#31) | Disagree | All tests have docstrings; regex misses `-> None:` return type |
| 17 | Automated review #45 difficulty mismatch (80% → easy) | Disagree | Worst model = min(20%, 80%) = 20% → Hard; script uses `max()` bug at `scripts/review_checklist.py:167-169` |
| 18 | Non-canonical base image warning (entire-report L116-136) | Partially agree | Python slim for C++ is non-canonical but credible; digest-pinned; not a blocker |
| 19 | Verifier timeout 1200s suggestion (entire-report L142-161) | Agree | Low only; tests rebuild small project |
| 20 | Test quality: ACCEPT, robust (entire-report L205-236) | Agree | Independent reference in `tests/test_outputs.py:23-165` |
| 21 | Rubric in portal report (entire-report L240-258) | Agree | ≥3 negatives present (`-5,-5,-3,-3,-5,-3,-3,-2`); task folder has no `rubric.txt` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraphs, ~149 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone; problem + contract pointer | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States deliverable paths/flags, not debug steps | `instruction.md:3-4` |
| 5 | CHECK | No hints or solving strategies | Points to contract for WHAT, not which files to patch | `instruction.md:5` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, output path, campaign, flags, contract ref | `instruction.md:1-5` |
| 8 | CHECK | Instruction is interesting | Realistic C++ binary-format / digest debugging | — |
| 9 | CHECK | Instruction is unique | VLT1 rollup + lane cache + journal tail binding; no duplicate found | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/vlt_report.json`, etc. | `instruction.md:1-5` |
| 11 | CHECK | Task name does not appear in instruction.md | `vlq-event-tape-rollup` absent | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | apt at build only; no runtime fetch | `environment/Dockerfile:11-22` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:27-29` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY only env subdirs | `environment/Dockerfile:31-42` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are normative spec; buggy C++ only | `environment/docs/vlt_contract.md`, source bugs in `m02/`, `r04/`, etc. |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:26-29`, `tests/test.sh:11-12` |
| 21 | CHECK | Oracle passes consistently | Local oracle reward 1.0 | `jobs/2026-06-21__23-44-05/result.json` |
| 22 | CHECK | Oracle does not require internet | cmake/ninja build + binary run offline | `solution/solve.sh:10-13` |
| 23 | CHECK | Oracle is reflective of instruction | Six apply_*.sh patches fix C++ bugs, rebuild, run | `solution/solve.sh:4-13`, `solution/apply_tape_lane.sh:39-44` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical block | `tests/test.sh:3-4,14-17` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `tests/test.sh:14-17` |
| 27 | CHECK | All tests aligned with instructions | Every contract/instruction req tested | §5 table |
| 28 | CHECK | Tests check correctness, not just format | Full panel/digest equality vs reference | `tests/test_outputs.py:207-287` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs compiled binary; no source grep | `tests/test_outputs.py:192-199` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact digests/JSON required by contract | `tests/test_outputs.py:209,266` |
| 31 | CHECK | Tests have informative names or docstrings | All 12 `test_*` have docstrings despite validator regex miss | `tests/test_outputs.py:202-357` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — rubric via portal, not in task folder | `entire-report.txt:240-258` |
| 33 | UNCHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion one line Agent, score | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference /tests/ | N/A | — |
| 38 | UNCHECK | Rubric does not reference task.toml or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | cpp/cmake/vlq/binary/rollup match content | `task.toml:7-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | GPT-5.5 20% ≤20% earns Hard | `task.toml:6`, `entire-report.txt:7-9` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests NOT baked into Docker image | No `COPY tests/` | `environment/Dockerfile`, `.dockerignore:19` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ excluded via `.dockerignore:18` | `environment/.dockerignore:18-19` |
| 52 | CHECK | Agent cannot trivially modify input data to pass | Expected values from `/tests/ref_caps/`; hand-written JSON overwritten | `tests/test_outputs.py:12-13,290-314` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst model GPT-5.5 20% ≤80% | `entire-report.txt:7-9` |
| 55 | CHECK | Task not too hard or unfair | Contract documents warm invalidation; agent failures are implementation gaps | `vlt_contract.md:16-20`, `entire-report.txt:54-55` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/vlt_report.json` for `vlt_roll_demo` | all tests via `_run()` | covered | `instruction.md:1`, `tests/test_outputs.py:9,197` |
| Fix C++ under `/app/environment`, rebuild, run binary | all tests call `_build()` + `_run()` | covered | `tests/test_outputs.py:168-199` |
| `--reset` cold runs rebuild journal | `test_vlt_journal_tail_binding`, panel answer tests | covered | `instruction.md:3`, `tests/test_outputs.py:205` |
| `--warm` when fingerprints match | `test_vlt_warm_lane_fingerprint_guard` | covered | `instruction.md:3`, `tests/test_outputs.py:317-325` |
| Warm reload when fingerprint changes | `test_vlt_warm_lane_fingerprint_invalidation` | covered | `vlt_contract.md:18`, `tests/test_outputs.py:328-354` |
| fold/peek/tally answers per panel | `test_v01_t2_answers`, `test_v02_t5_answers`, `test_v03_t8_answers` | covered | `vlt_contract.md:26-28`, `tests/test_outputs.py:215-242` |
| fold/peek consistency on same lane | `test_vlt_fold_peek_lane_consistency` | covered | `tests/test_outputs.py:356-374` |
| Journal checkpoints in manifest order | `test_vlt_checkpoint_manifest_order` | covered | `vlt_contract.md:20`, `tests/test_outputs.py:245-258` |
| Campaign digest with journal tail binding | `test_vlt_journal_tail_binding`, `test_v05_root_chain` | covered | `vlt_contract.md:50-57`, `tests/test_outputs.py:202-266` |
| row_digest per panel | `test_v06_row_chain_roundtrip` | covered | `vlt_contract.md:37-40`, `tests/test_outputs.py:269-274` |
| Journal corruption recovery via `--reset` | `test_vlt_reset_recovers_corrupt_journal` | covered | `tests/test_outputs.py:277-287` |
| No static/hand-written output bypass | `test_v08_static_output_rejected` | covered | `instruction.md:5`, `tests/test_outputs.py:290-314` |
| Byte-identical output on unchanged fixtures | `test_vlt_warm_lane_fingerprint_guard` (`warm == cold`) | covered | `instruction.md:5`, `tests/test_outputs.py:323` |
| VLT1 little-endian fields, VLQ decode | implied by answer/digest tests | covered | `vlt_contract.md:5-10`, planted bug in `m02/t2_pull.cpp:20-21` |
| tally `(tag & mask) != 0` | panel answer tests | covered | `vlt_contract.md:28`, bug in `w33/k9_filter.cpp:9` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/.dockerignore` | #50-51 |
| `environment/docs/vlt_contract.md` | #17, #27, #55, spec alignment |
| `environment/r04/tape_lane.cpp` | planted warm-cache bug, oracle fix |
| `environment/m02/t2_pull.cpp` | planted endianness bug |
| `environment/common/stage_seal.cpp` | planted missing tail binding |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment, anti-cheating |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, agent stats, adjudication |
| `jobs/2026-06-21__23-44-05/result.json` | #21 oracle pass |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate vlq-event-tape-rollup/
Summary: 0 error(s), 15 warnings, 2 info
```

Warnings are false positives (#4 hint pattern, #14 pip on continuation lines, #31 docstring regex vs `-> None:`) or Low (missing module docstring).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Sets Hard tier floor |
| terminus-claude-opus-4-8 | 80.0% (4/5) | At easy-tier ceiling; does not exceed 80% rejection |
| oracle | 100.0% (3/3 platform; 1/1 local) | Consistent pass |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% (GPT-5.5) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test: `test_vlt_warm_lane_fingerprint_invalidation` hardest at 6/10 — contract-covered warm reload on mutation, not a spec gap.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular layout; `vlq-event-tape-rollup`; report matches task |
| 1 Instruction | ☑ | Concise, absolute paths, contract pointer, no canary |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Six patches + rebuild; local reward 1.0 |
| 4 Verifiers | ☑ | Canonical reward block; no runtime installs; 12 behavior tests |
| 5 Metadata | ☑ | hard/cpp/data-processing; timeouts plausible |
| 6 Rubric | N/A | Portal rubric in `entire-report.txt:240-258`; no file in task folder |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; GPT 20% supports Hard |
| 8 Novelty & fairness | ☑ | Six distinct bugs; ref_caps anti-cheating; fair warm invalidation test |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction is a clear C++ VLT1 rollup debugging brief with `vlt_contract.md` as the normative contract; tests rebuild from source, run the compiled binary, and compare output against an independent Python reference over 12 behaviors including warm-cache fingerprint guard and invalidation. The Dockerfile is digest-pinned, verifier deps are baked in, and tests/solution are not copied into the image. Oracle passes (reward 1.0); GPT-5.5 at 20% matches declared Hard difficulty. Automated review false-flags on pip pinning, docstrings, step hints, and difficulty tier should be ignored on re-audit.

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

_Generated by `./scripts/terminus review` and enriched after manual audit per `prompt.md`._
