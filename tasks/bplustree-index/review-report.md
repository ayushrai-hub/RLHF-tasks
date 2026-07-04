# Terminus Review Report: `bplustree-index`

**Generated:** 2026-07-04 17:45 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/bplustree-index`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass (0 errors, 0 warnings; 2 INFO module-docstring hints) |
| **Oracle** | pass (submission export 3/3; local Harbor run blocked — config error) |
| **CHECK count** | 55 |
| **UNCHECK count** | 0 |

**Error categories (internal):** none

**Decision (concise):** No real blockers after manual re-audit. This is a well-specified two-milestone C++ B+tree task with byte-exact verification via an independent Python reference, digest-pinned offline environment, correct milestone rubric format (`# Rubric 1` / `# Rubric 2`, 28 and 25 positive pts per block), and well-calibrated difficulty (0% GPT-5.5 / 100% Claude). Automated review false positives on #30/#31/#35/#41 and the stale Harbor shebang warning are all overturned by artifact evidence.

**Insights (concise):**

- Milestone rubric format is **correct** for `number_of_milestones = 2`; per-block caps (28, 25) are ≤40; combined 53 pts is within the 2×10–2×40 range for two milestones.
- All 27 `test_*` functions across `test_m1.py` and `test_m2.py` have docstrings; only module-level docstrings are absent (INFO only).
- Numeric constants flagged by automated audit (#27: 4096, 4, 5) are authoritative in `/app/docs/bptree-spec.md`, explicitly referenced by both milestone instructions.
- Agent M2 failures (`test_apply_bytes_exact`, `test_apply_dump_matches` at 5/10) are separator-rotation implementation misses per spec §6.2, not spec gaps.
- Per-step `test.sh` files include `#!/bin/bash` (Harbor REVIEW REPORT shebang warning is stale).
- No `__pycache__` present in task tree; `.dockerignore` excludes it.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept — no High/Medium blockers | **Agree** | Full artifact re-audit; rubric per-block caps OK, env compliant, spec-test aligned |
| 2 | ChatGPT: Strong two-milestone C++ task with byte-exact serialization | **Agree** | `bptree-spec.md:1-5`; `test_m1.py:55-57`, `test_m2.py:103-105` |
| 3 | ChatGPT: M2 misses are narrow separator-rotation implementation misses | **Agree** | `entire-report.txt:56-57,78-82`; spec §6.2 borrow-from-right at `bptree-spec.md:165-166` |
| 4 | ChatGPT: Milestone structure correct, allow_internet=false | **Agree** | `task.toml:9,21`; `steps/milestone_1/`, `steps/milestone_2/` layout |
| 5 | ChatGPT: Independent Python reference for byte-exact comparisons | **Agree** | `steps/milestone_1/tests/bpt_ref.py`, `steps/milestone_2/tests/bpt_ref.py` |
| 6 | ChatGPT: Shebang warning in report appears stale | **Agree** | `steps/milestone_1/tests/test.sh:1`, `steps/milestone_2/tests/test.sh:1` both have `#!/bin/bash` |
| 7 | ChatGPT: Optional __pycache__ cleanup | **Agree** (Low only) | No `__pycache__` found; `.dockerignore:3` already excludes |
| 8 | ChatGPT: Optional root-level [agent]/[verifier] timeouts | **Agree** (Low only) | Per-step timeouts valid for milestone tasks per `docs/guidelines/milestones.md` |
| 9 | ChatGPT: Dockerfile digest-pinned GCC base appropriate | **Agree** | `environment/Dockerfile:1` `@sha256:930f2ebe…` |
| 10 | Harbor REVIEW REPORT: Missing shebang in test.sh | **Disagree** | Both per-step test.sh start with `#!/bin/bash` — stale warning |
| 11 | Harbor REVIEW REPORT: Non-canonical GCC base image | **Agree** non-blocking | Digest-pinned; no canonical C++ base required; appropriate for C++17 build |
| 12 | Harbor REVIEW REPORT: NEEDS REVISION for shebang/base | **Disagree** as blocker | Shebang present; base image warning is informational only |
| 13 | entire-report: Instruction Sufficiency PASS | **Agree** | Spec §6–7 covers borrow/merge/separator rotation; agent failures are capability gaps |
| 14 | entire-report: Oracle 100% (3/3) | **Agree** (report evidence) | `entire-report.txt:24`; local oracle blocked by Harbor config |
| 15 | entire-report: GPT-5.5 0%, Claude 100% | **Agree** | `entire-report.txt:19-20`; worst-model 0% → hard tier |
| 16 | Automated audit #27: Phantom numeric thresholds | **Disagree** as blocker | 4096/4/5 in `bptree-spec.md:16-18,22,33-37`; instructions cite spec as contract |
| 17 | Automated audit #30: Brittle exact string matching | **Disagree** as blocker | Byte-exact output is explicit spec requirement (`bptree-spec.md:4-5`, `instruction.md` M1/M2) |
| 18 | Automated review #31: 2 tests missing docstrings | **Disagree** | All 13 M1 + 14 M2 `test_*` have docstrings (AST-verified in audit; grep confirmed) |
| 19 | Automated review #35: Rubric 53 >40 blocker | **Disagree** as blocker | Milestone task: per-block 28 and 25 ≤40; combined 53 within 20–80 for 2 milestones |
| 20 | Automated review #36: Rubric positive-language fail | **Disagree** | Negative scores use negative phrasing (correct); + lines use positive behavior descriptions |
| 21 | Automated review #41: Stray audit-report.md | **Disagree** as blocker | Reviewer-generated local artifact; not part of author submission |
| 22 | User concern: Non-milestone task in milestone rubric format | **N/A — task is milestone** | `task.toml:9` `number_of_milestones = 2`; rubric correctly uses `# Rubric 1` + `# Rubric 2` per `docs/guidelines/submission-export-format.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 5 prose blocks, ~435 words across two milestones | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as embedded-storage engineering scenario, not synthetic checklist | milestone instruction files |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables/code blocks | milestone instruction files |
| 4 | CHECK | No step-by-step HOW | Describes outcomes and spec reference, not build walkthrough | milestone instruction files |
| 5 | CHECK | No hints/strategies | WHAT to build; `/app/docs/bptree-spec.md` is normative contract | `steps/milestone_1/instruction.md:1`, `steps/milestone_2/instruction.md:1` |
| 6 | CHECK | No design-doc tables | None in instructions | milestone instruction files |
| 7 | CHECK | Well specified | Commands, byte-exact requirement, spec path, behaviors enumerated | milestone instruction files |
| 8 | CHECK | Interesting | Real on-disk B+tree index with mmap-style reproducibility | `steps/milestone_1/instruction.md:1` |
| 9 | CHECK | Unique | Byte-exact B+tree with canonical BFS page numbering + deletion rebalancing; corpus dup not verified | — |
| 10 | CHECK | Absolute paths | `/app/docs/bptree-spec.md`, `/app/bin/bpt`, `/app/data` | milestone instruction files |
| 11 | CHECK | Task name absent | No `bplustree-index` slug in instructions | milestone instruction files |
| 12 | CHECK | No canary strings | None detected | milestone instruction files |
| 13 | CHECK | No runtime web fetch | Offline env; apt/curl at build only for uv installer | `environment/Dockerfile`, `task.toml:21` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:13` |
| 15 | CHECK | FROM digest-pinned | `@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` | `environment/Dockerfile:1` |
| 16 | CHECK | Env self-contained | COPY only Makefile/include/src/docs/data from environment/ | `environment/Dockerfile:17-21` |
| 17 | CHECK | No ground-truth leakage | Data files are operation sequences, not precomputed index bytes; spec is contract not answers | `environment/data/`, `environment/.dockerignore:17-18` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts OK | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; per-step test.sh has no runtime installs | `environment/Dockerfile:12-13`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | Export: oracle 100% (3/3); solve scripts write full C++ implementations | `entire-report.txt:24`, `steps/milestone_1/solution/solve1.sh` |
| 22 | CHECK | Oracle offline | No network in solve scripts | `steps/milestone_1/solution/solve.sh`, `steps/milestone_2/solution/solve.sh` |
| 23 | CHECK | Oracle derives results | solve1.sh/solve2.sh emit complete algorithmic C++ source, not hardcoded bytes | `steps/milestone_1/solution/solve1.sh:6+`, `steps/milestone_2/solution/solve2.sh:6+` |
| 24 | CHECK | reward.txt canonical | Writes 0/1; mkdir /logs/verifier | `steps/milestone_1/tests/test.sh:1-8`, `steps/milestone_2/tests/test.sh:1-8` |
| 25 | CHECK | Same verifier for agent/oracle | No /oracle branching | per-step test.sh and test_mN.py |
| 26 | CHECK | Binary rewards | 0 or 1 only | per-step test.sh |
| 27 | CHECK | Tests aligned with spec | Every assertion traces to instruction or bptree-spec.md | §5 below |
| 28 | CHECK | Tests check correctness | Byte-exact + reference-model comparisons, not format-only | `test_m1.py:55-57`, `test_m2.py:103-105` |
| 29 | CHECK | Behavior not implementation | No source grepping | test_m1.py, test_m2.py |
| 30 | CHECK | Not brittle beyond spec | Byte-exact comparison required by authoritative spec | `bptree-spec.md:4-5`; `test_m1.py:55-57` |
| 31 | CHECK | Informative test docstrings | All 27 `test_*` have docstrings | `test_m1.py:55-208`, `test_m2.py:94-276` |
| 32 | CHECK | ≥3 negative rubric criteria | 7 negatives total (3 in block 1, 4 in block 2) | `entire-report.txt:391-407` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use valid scores | `entire-report.txt:382-407` |
| 34 | CHECK | Agent …, ±N format | 23 properly formatted lines | `entire-report.txt:382-407` |
| 35 | CHECK | Rubric detailed; positive cap | Per-block: #1=28, #2=25 (both ≤40) | `entire-report.txt:382-407`; `task.toml:9` |
| 36 | CHECK | Positive rubric language | + lines describe desired behavior; − lines penalize bad behavior | `entire-report.txt:382-407` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:382-407` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:382-407` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:382-407` |
| 40 | CHECK | Required files present | Milestone layout: Dockerfile, per-step instruction/tests/solution, task.toml | `task.toml`, `steps/milestone_1/`, `steps/milestone_2/` |
| 41 | CHECK | No stray parent files | No jobs/, README, dev notes in task dir | task root listing |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, timeouts, allow_internet=false, codebase_size | `task.toml` |
| 44 | CHECK | Tags/languages/category match | cpp, b-plus-tree, on-disk-index, data-processing | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | hard; platform hard; worst-model 0% → hard tier | `task.toml:6`, `entire-report.txt:14-22` |
| 46 | CHECK | Milestone steps/ layout | 2 steps matching number_of_milestones | `task.toml:9,24-36` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh, solve2.sh present | `steps/milestone_1/solution/solve1.sh`, `steps/milestone_2/solution/solve2.sh` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py, test_m2.py present | `steps/milestone_1/tests/`, `steps/milestone_2/tests/` |
| 49 | CHECK | Milestone test scope | M1 tests build/get/dump; M2 tests range/apply/delete (+ M1 regression smoke) | `test_m1.py`, `test_m2.py` |
| 50 | CHECK | Tests not in image | No COPY tests/; .dockerignore excludes | `environment/Dockerfile`, `environment/.dockerignore:17-18` |
| 51 | CHECK | Solution not in env | .dockerignore excludes solution/ and tests/ | `environment/.dockerignore:17-18` |
| 52 | CHECK | No trivial input cheat | Expected bytes from independent bpt_ref.py, not embedded in data fixtures | `steps/milestone_1/tests/bpt_ref.py`; data/*.ops are inputs only |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:19-22` |
| 55 | CHECK | Not unfair | Comprehensive spec; agent M2 failures are documented separator-rotation semantics | `bptree-spec.md:151-174`; `entire-report.txt:92-94` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | (none) |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / spec) | Test(s) | Status | Proof |
|----------------------------------|---------|--------|-------|
| Byte-exact build output | `test_serialize_bytes_exact`, `test_apply_bytes_exact` | covered | `bptree-spec.md:4-5`; `test_m1.py:55`, `test_m2.py:103` |
| 4096-byte pages, superblock fields | `test_file_length_multiple_of_page`, `test_superblock_fields` | covered | `bptree-spec.md:22-39`; `test_m1.py:66-86` |
| Canonical dump format | `test_dump_matches_reference`, `test_dump_header_lines` | covered | `bptree-spec.md:198+`; `test_m1.py:88-125` |
| get: value or NOT-FOUND | `test_get_present_and_absent` | covered | milestone 1 instruction; `test_m1.py:98` |
| Leaf split at LEAF_CAP=4 (5 keys triggers) | `test_leaf_split_boundary_five` | covered | `bptree-spec.md:115-117`; `test_m1.py:127` |
| BFS canonical page numbering | `test_serialize_bytes_exact`, `test_dump_header_lines` | covered | `bptree-spec.md:76-92`; `test_m1.py:55,118` |
| Deterministic rebuild | `test_deterministic_rebuild` | covered | milestone 1 instruction; `test_m1.py:207` |
| Leaf chain ordering | `test_leaf_chain_left_to_right` | covered | `bptree-spec.md:67-68`; `test_m1.py:177` |
| Usage errors: nonzero, no stdout | `test_usage_errors_nonzero_no_stdout` | covered | `test_m1.py:192` |
| range: inclusive [lo,hi], tab-separated | `test_range_matches_reference`, `test_range_single_point` | covered | milestone 2 instruction; `test_m2.py:170,199` |
| apply: load+modify+write, input untouched | `test_apply_does_not_touch_input` | covered | milestone 2 instruction; `test_m2.py:253` |
| Deletion rebalancing borrow/merge/root collapse | `test_root_collapse_scenario`, `test_underflow_cascade_scenario` | covered | `bptree-spec.md:151-196`; `test_m2.py:228,241` |
| Delete absent is noop | `test_delete_absent_is_noop` | covered | `bptree-spec.md:140-141`; `test_m2.py:263` |
| B+tree invariants after apply | `test_apply_preserves_invariants` | covered | `test_m2.py:132` |
| M1 still works in M2 | `test_m1_build_still_byte_exact` | covered | `test_m2.py:94` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #40, #45, #46, milestone metadata |
| `steps/milestone_1/instruction.md` | #1–12, #27 |
| `steps/milestone_2/instruction.md` | #1–12, #27 |
| `environment/Dockerfile` | #13–18, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/bptree-spec.md` | #17, #27, #55, spec alignment |
| `steps/milestone_1/tests/test.sh` | #24, shebang adjudication |
| `steps/milestone_2/tests/test.sh` | #24, shebang adjudication |
| `steps/milestone_1/tests/test_m1.py` | #27–31 |
| `steps/milestone_2/tests/test_m2.py` | #27–31, #49 |
| `steps/milestone_1/tests/bpt_ref.py` | #52, oracle alignment |
| `steps/milestone_1/solution/solve1.sh` | #21–23 |
| `steps/milestone_2/solution/solve2.sh` | #21–23 |
| `entire-report.txt` | #21, #32–39, #45, #54, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate bplustree-index
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: milestone
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All trials M1=1.0, M2=0.0 |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Full pass |
| oracle | 100.0% (3/3) | Submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

**M2 narrow failure:** `test_apply_bytes_exact` and `test_apply_dump_matches` at 5/10 — separator key after borrow-from-right (318 vs 329 expected).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone C++ B+tree; report matches task |
| 1 Instruction | ☑ | Natural tone; spec-referenced; absolute paths |
| 2 Environment | ☑ | Digest-pinned GCC; tmux/asciinema; offline |
| 3 Oracle | ☑ | Full C++ implementations in solve1/2.sh; export 100% |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; all docstrings |
| 5 Metadata | ☑ | number_of_milestones=2; per-step timeouts |
| 6 Rubric | ☑ | Correct milestone format; per-block ≤40 |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency PASS; agent gap not spec gap |
| 8 Novelty & fairness | ☑ | Deep multi-step; no cheating paths |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The two-milestone structure is clean, the bptree-spec is an excellent authoritative contract, and the Python reference verifier gives real byte-exact confidence without leaking answers into the image. Oracle passes and difficulty calibration look right — GPT struggles on the separator-rotation edge case while Claude clears it, which fits hard tier. I didn't find any blocking spec-test gaps, rubric issues, or environment problems. The milestone rubric blocks are correctly formatted with 28 and 25 positive points respectively.

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

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review bplustree-index --report entire-report.txt`._
