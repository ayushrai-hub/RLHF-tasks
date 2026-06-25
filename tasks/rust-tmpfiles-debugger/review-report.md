# Terminus Review Report: `rust-tmpfiles-debugger`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** No High-severity blockers on re-audit. Instruction, `docs/SPEC.md` / `docs/format.md` contract, digest-pinned canonical Rust base, offline verifier venv, runtime-generated hidden tests, tests/solution exclusion, oracle pass, and Hard difficulty calibration (Claude 0% worst-model) are solid. ChatGPT’s Revise call rests only on metadata polish (`category`, `codebase_size` casing) and a false non-canonical-base warning — none rise to High blockers. Automated `terminus review` false-flags on docstrings (#31) and difficulty (#45, #54) are overturned below.

**Insights (concise):**

- `rust:1.85-slim@sha256:9f841bbe…` is listed in `CANONICAL_BASE_IMAGES` (`scripts/validate_task.py:68`) — external “non-canonical base” warning is incorrect.
- Worst-model rate is **Claude 0%** (0/5), not GPT 100%; declared `hard` matches `docs/guidelines/difficulty.md` (≤20% on worst model).
- LLMaJ and agent analysis both mark `task_specification: pass`; near-miss agent failures (13–14/15 hidden tests) trace to implementation gaps, not spec gaps (`entire-report.txt:50-56`).
- Three pytest entrypoints use informative names (`test_hidden_semantics`, `test_generated_reference_cases`, `test_fix_report`); 15 embedded Rust scenarios have descriptive `#[test]` names — satisfies portal #31.
- Optional polish (not blocking): `category` fits `debugging` better than `system-administration` (Medium); lowercase `codebase_size = "small"`; absolute paths for doc refs (`/app/task_file/docs/SPEC.md`).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `codebase_size = "Small"` must be lowercase `small` (ChatGPT High) | **Partially agree** | `task.toml:14`; `validate_task.py` checks field presence only (no case ERROR); `docs/task-requirements.md:26` shows lowercase example — cosmetic, not a High blocker |
| 2 | `category = "system-administration"` invalid; should be `debugging` (ChatGPT High) | **Partially agree** | `task.toml:7` — value is in `VALID_CATEGORIES` (`validate_task.py:86-96`); primary activity is Rust bug repair → `debugging` per `docs/task-type-taxonomy.md:29` — **Medium** severity per `docs/reviewer-checklist-full.md:98`, not Revise-driving |
| 3 | Non-canonical Docker base image (entire-report.txt L146-170) | **Disagree** | `environment/Dockerfile:1` digest matches `CANONICAL_BASE_IMAGES["public.ecr.aws/docker/library/rust:1.85-slim"]` at `scripts/validate_task.py:68` |
| 4 | NEEDS REVISION for metadata + base image (entire-report.txt L264-268) | **Disagree** | Claims 1–3 above do not meet High bar; task design and verifiers are sound |
| 5 | LLMaJ `behavior_in_task_description` PASS (entire-report.txt L83) | **Agree** | Instruction + docs cover masking, quoting, cleanup, exclusions, `fix_report.json` schema |
| 6 | LLMaJ `behavior_in_tests` PASS (entire-report.txt L84) | **Agree** | Hidden semantics + 24 generated cases + `test_fix_report` cover instruction contract |
| 7 | Task Instruction Sufficiency PASS (entire-report.txt L51-56) | **Agree** | Exclusion-descendant and non-empty user/group rules explicit in `docs/format.md:18`, `docs/SPEC.md:64-65` |
| 8 | Test quality ACCEPT / robust (entire-report.txt L277-316) | **Agree** | Python reference oracle generates Rust integration tests at runtime; no shortcut path |
| 9 | Automated review blocker #31 missing docstrings | **Disagree** | Portal #31 allows informative names; `tests/test_outputs.py:483,961,974`; embedded Rust tests e.g. `config_file_order_normalization_and_first_match_hold` — validate regex misses `-> None:` / name-only pattern |
| 10 | Automated review blockers #45, #54 difficulty too easy | **Disagree** | `review_checklist.py:167-169` uses `max()` not `min()`; correct worst-model = Claude 0% (`entire-report.txt:6-7`) → Hard tier |
| 11 | Missing `RecursiveRemove` in buggy parser is unfair (entire-report suggestion) | **Disagree** | Intentional bug surface; `docs/format.md:13` lists `R`; `docs/SPEC.md:41-43` defines semantics — standard debugging depth |
| 12 | Portal rubric (entire-report.txt L320-339) | **Agree** | 4 negatives (-5,-5,-3,-3); valid scores; no `/tests/` or `instruction.md` refs |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two prose paragraphs (~192 words) | `instruction.md:1-3` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Ops-style debugging brief referencing crate docs | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States contract and output path, not edit order | `instruction.md:1-3` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | No module-by-module walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Public API constraint + doc contract + `fix_report.json` schema stated | `instruction.md:1-3` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic tmpfiles-policy Rust debugging | `task.toml:7-9` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct tmpfiles_audit + Python-generated Rust verifier pattern | — |
| 10 | UNCHECK | All paths in instruction are absolute (not relative) | `docs/SPEC.md` and `docs/format.md` are crate-relative, not `/app/task_file/docs/...` | `instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | COPY only local `task_file/` | `environment/Dockerfile:19-20` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:17` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned canonical Rust base | `environment/Dockerfile:1`; `scripts/validate_task.py:68` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY task_file` only | `environment/Dockerfile:20` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are behavioral spec; `basic_tests.rs` is smoke only, not hidden oracle | `environment/task_file/docs/SPEC.md`; `environment/task_file/tests/basic_tests.rs` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in venv; test.sh only runs pytest | `environment/Dockerfile:16-17`, `tests/test.sh:16` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Local oracle 1/1; report 3/3 | `./scripts/terminus oracle`; `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes Rust sources locally | `solution/solve.sh:1-665` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full parser/glob/plan implementations written | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block + mkdir | `tests/test.sh:12-22` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 reward only | `tests/test.sh:18-22` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Hidden + generated cases trace to SPEC/format/cleanup docs | `docs/SPEC.md`; `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | `assert_eq` on `plan.actions` / `plan.errors` | `tests/test_outputs.py` HIDDEN_TEST_SRC |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | `cargo test` against compiled crate | `tests/test_outputs.py:483-493` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact plan equality required by spec determinism | `docs/SPEC.md:80-83` |
| 31 | CHECK | Tests have informative names or docstrings | Three descriptive pytest names + 15 named Rust scenarios | `tests/test_outputs.py:483,961,974`; HIDDEN_TEST_SRC |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives in portal rubric | `entire-report.txt:336-339` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:320-339` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format compliant | `entire-report.txt:320-339` |
| 35 | CHECK | Rubric criteria are detailed and precise | Parser/cleanup/API-stability criteria | `entire-report.txt:320-339` |
| 36 | CHECK | Rubric criteria use positive language | Positive phrasing with negative scores for bad behavior | `entire-report.txt:320-339` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No pytest/`/tests/` refs | `entire-report.txt:320-339` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No task.toml/instruction refs | `entire-report.txt:320-339` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:320-339` |
| 40 | CHECK | All required files present | Regular layout complete | `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/solve.sh`, `tests/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | `rust-tmpfiles-debugger/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, subcategories | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories are applicable to the task | `category = "system-administration"` — primary work is Rust debugging (`debugging`/`software-engineering` per taxonomy) | `task.toml:7`; `docs/task-type-taxonomy.md:15-29` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model Claude 0% | `task.toml:6`; `entire-report.txt:6-7`; `docs/guidelines/difficulty.md:9` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task (`number_of_milestones = 0`) | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not milestone | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not milestone | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not milestone | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | No `COPY tests/`; hidden tests written at runtime | `environment/Dockerfile:20`; `tests/test_outputs.py:484` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | `solution/` not in image; verifier reference lives in `/tests/` | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Grading uses runtime-generated Rust tests + reference oracle | `tests/test_outputs.py:918-962` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% (Claude) | `entire-report.txt:6-7` |
| 55 | CHECK | Task is not too hard or unfair | Spec sufficient; agents reached 13–14/15 hidden tests; failures are implementation | `entire-report.txt:50-70,90-94` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 10, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Config file ordering / masking | `config_file_order_normalization_and_first_match_hold`, `basename_masking_uses_highest_priority_file` | covered | `tests/test_outputs.py` HIDDEN_TEST_SRC |
| Quoted field parsing | `quoted_fields_comments_and_symlink_targets_are_preserved` | covered | HIDDEN_TEST_SRC |
| Path normalization / `..` rejection | `paths_with_dot_segments_normalize_and_parent_segments_error` | covered | HIDDEN_TEST_SRC |
| First-match create/adjust precedence | `config_file_order_normalization_and_first_match_hold` | covered | HIDDEN_TEST_SRC |
| Ensure on existing paths / wrong kind errors | `ensure_rules_adjust_existing_matching_kind_and_error_on_wrong_kind` | covered | HIDDEN_TEST_SRC |
| Globbed cleanup + age (inclusive) | `removes_aged_glob_matches` (basic); generated cases | covered | `basic_tests.rs:43`; generated seeds |
| Recursive `R` + exclusions protect descendants | `recursive_cleanup_respects_excluded_and_young_descendants` | covered | HIDDEN_TEST_SRC; `docs/SPEC.md:64-65` |
| Create/adjust does not shield cleanup | instruction + cleanup docs | covered | generated + hidden scenarios |
| Deterministic action/error sorting | hidden + generated equality asserts | covered | `docs/SPEC.md:80-83` |
| `fix_report.json` schema (≥10 unique entries) | `test_fix_report` | covered | `tests/test_outputs.py:974-988` |
| Public API stability | all tests compile against exported types | covered | `instruction.md:3`; `types.rs` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, spec alignment |
| `task.toml` | #42-45, #44 category |
| `environment/Dockerfile` | #13-20, #50, canonical base |
| `environment/task_file/docs/SPEC.md` | #17, #27, spec alignment |
| `environment/task_file/docs/format.md` | #27, agent failure analysis |
| `environment/task_file/docs/cleanup.md` | #27, exclusion semantics |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, anti-cheat |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, adjudication |
| `scripts/validate_task.py` | Canonical base list, category validation |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate rust-tmpfiles-debugger/
Summary: 0 error(s), 6 warning(s), 2 info
```

Warnings: `informative_test_docstrings` (false positive — informative names); `solution-hints` heuristic on SPEC.md (spec contract, not walkthrough); milestone preference INFO.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | `entire-report.txt:7` |
| terminus-claude-opus-4-8 | 0% (0/5) | 1 timeout, 4 other; `entire-report.txt:6,14-15` |
| oracle | 100% (3/3) | `entire-report.txt:11` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (Claude) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test pass rates (`entire-report.txt:19-22`): `test_fix_report` 9/10; `test_hidden_semantics` 5/10; `test_generated_reference_cases` 6/10 — agent errors, not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout |
| 1 Instruction | ☑ | Concise, testable; doc refs crate-relative (#10 UNCHECK) |
| 2 Environment | ☑ | Canonical digest-pinned Rust; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Pass 1/1 local; substantive derived implementation |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; informative names |
| 5 Metadata | ☑ | Category mismatch Medium-only (#44); `codebase_size` casing cosmetic |
| 6 Rubric | ☑ | Portal rubric in report valid (4 negatives) |
| 7 LLMaJ & agent evidence | ☑ | Spec sufficiency PASS; Claude 0% supports Hard |
| 8 Novelty & fairness | ☑ | Multi-subsystem Rust debug; anti-cheat via runtime test generation |
| 9 Long context | ☐ | N/A — `subcategories = []` |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction is a clear Rust tmpfiles-policy debugging brief with `docs/SPEC.md` and `docs/format.md` as the normative contract; verifiers compile and run hidden plus 24 generated Rust scenarios against a Python reference oracle, with `fix_report.json` schema validation. The environment uses the canonical digest-pinned `rust:1.85-slim` base, verifier deps are baked in, and tests/solution are not in the image. Oracle passes; Claude 0% worst-model pass rate matches declared Hard difficulty. ChatGPT’s metadata Revise items (`category`, `codebase_size` casing) and non-canonical-base warning are not High blockers on re-audit — optional polish only.

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
