# Terminus Review Report: `origin-include-normalize`

**Generated:** 2026-06-30  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/origin-include-normalize`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Manual re-audit overturns the automated Revise disposition. The three scripted blockers (#14 pinned pip, #20 verifier deps, #31 docstrings) are false positives on inspection. Spec, tests, oracle design, and platform rubric align; rubric is correctly flat for a non-milestone task (26 positive pts ≤40). No High-severity gaps found.

**Insights (concise):**

- Platform rubric is **flat** `Agent …, ±N` (no `# Rubric 2+` headers) — correct for `number_of_milestones = 0`; not milestone-format.
- `requirements.lock` pins pytest with `==` + SHA-256 hashes; Dockerfile bakes verifier venv at build time; `test.sh` does not install packages.
- All six `test_lane_*` functions have one-line docstrings; LLMaJ `informative_test_structure` pass is accurate.
- Non-canonical `docker.io/library/rust:1.85-slim@sha256:…` is digest-pinned and justified for a Rust toolchain task — Low only.
- Worst-model pass rate 60% (Claude Opus 4.8); GPT-5.5 at 100% does not trigger #54 (>80% worst-model).
- `task.toml` declares `hard` while platform classifies `medium` — informational only, never a blocker.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

**Overturned automated flags (not blockers):**

| Automated claim | Manual verdict | Proof |
|-----------------|----------------|-------|
| #14 unpinned pip | **Disagree** — pinned via hash lockfile | `environment/requirements.lock:19-25` (`pytest==8.4.1` + `--hash=sha256:…`); `environment/Dockerfile:26-27` (`--require-hashes --no-deps`) |
| #20 pytest not in image | **Disagree** — baked at build | `environment/Dockerfile:24-27` creates `/opt/verifier-venv` and installs lockfile; `tests/test.sh:12` invokes venv pytest only |
| #31 missing docstrings | **Disagree** — all tests documented | `tests/test_outputs.py:281-477` — each `test_lane_*` has `"""…"""` docstring |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High-severity issues; spec/tests/rubric aligned (ChatGPT) | Agree | Cross-checked `instruction.md`, `tests/test_outputs.py`, platform rubric lines 288–301 in `entire-report.txt` |
| 2 | Verifier robust; builds real binary, drives full workflow (ChatGPT) | Agree | `tests/test_outputs.py:81-89` `_build_binary()`; lanes run init→apply-scope→normalize→reload |
| 3 | Non-canonical Rust base image is non-blocking (ChatGPT) | Agree | `environment/Dockerfile:1` digest-pinned; Rust task requires toolchain — Low per `docs/reviewer-checklist-full.md` canonical-base rule |
| 4 | Dockerfile digest-pinned; no blocking base issue (ChatGPT) | Agree | `FROM docker.io/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` |
| 5 | Decision: Accept (ChatGPT) | Agree | No artifact-backed High findings after manual audit |
| 6 | Non-canonical base image warning (Harbor REVIEW REPORT) | Partially agree | Warning valid; severity Low — credible justification for Rust task |
| 7 | `shell_digest` internal vs `zone_digest` JSON key mismatch (Harbor REVIEW REPORT) | Agree — cosmetic | `environment/src/model.rs:140-143` serializes `zone_digest`; internal field `shell_digest` — instruction/tests use `zone_digest` consistently |
| 8 | Add more specific test docstrings (Harbor suggestion) | Disagree as issue | Docstrings exist at `tests/test_outputs.py:282,311,343,388,416,446`; suggestion is optional polish |
| 9 | LLMaJ `behavior_in_task_description` PASS | Agree | Instruction names outputs, commands, fixtures, doc paths — `instruction.md:1-7` |
| 10 | LLMaJ `behavior_in_tests` PASS | Agree | Six lanes cover cold normalize, reload/idempotency, anchor edits, material loss, snap alignment, journal carry |
| 11 | LLMaJ `pinned_dependencies` PASS | Agree | `requirements.lock`, `Cargo.lock`, apt version pins in `environment/Dockerfile:12-19` |
| 12 | Instruction sufficiency PASS — agent failures not spec gaps (export) | Agree | Failures are compile timeout and lane-order logic, both documented in `toolchain.md` / `reload-path.md` |
| 13 | Test quality ACCEPT (export) | Agree | Dynamic digest helpers `_fnv1a16`, `_fold_label`; state-mutation scenarios |
| 14 | Non-milestone task uses milestone rubric format (user concern) | **Disagree** | `task.toml:9` `number_of_milestones = 0`; platform rubric has **no** `# Rubric N` headers — flat 14-line list per `docs/guidelines/submission-export-format.md:63-64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~187 words across four short blocks; within practical concision bar | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Symptom-oriented prose, no numbered solve script | `instruction.md:1-7` |
| 3 | CHECK | No excessive markdown formatting | Plain paragraphs only | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Describes WHAT/failures; no edit-order walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Docs are behavioral contracts, not patch recipes | `environment/docs/toolchain.md`, `reload-path.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Binary, commands, outputs, fixtures named | `instruction.md:7` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Rust state-replay / DNS-like serialization debugging | task content |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct znctl multi-module Rust workflow | task design |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/environment`, `/tmp/znctl-build`, doc paths | `instruction.md:1,3,7` |
| 11 | CHECK | Task name does not appear in instruction.md | No `origin-include-normalize` string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only; `allow_internet = false` | `task.toml:23`, `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Hash-locked `requirements.lock` with explicit `==` pins | `environment/requirements.lock:19-25` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | FROM digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY paths under build context | `environment/Dockerfile:24-39` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Buggy starter modules; docs specify behavior not patches | `environment/pivot/`, `braid/`, etc. |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | Venv + lockfile in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:24-27`, `tests/test.sh:12` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed in this review environment | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` patches local Rust sources and `cargo build` | `solution/solve.sh:1-4` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Writes algorithmic Rust for pivot/braid/latch/grain/knot/lens then builds | `solution/solve.sh:5-347` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:4-18` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 0` / `echo 1` only | `tests/test.sh:14-17` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Every lane traces to instruction symptoms + doc contracts | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Digest recomputation, lane order, journal flags, binary layouts | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Invokes built binary; no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Expected values derived from fixtures + FNV rules | `tests/test_outputs.py:52-78,245` |
| 31 | CHECK | Tests have informative names or docstrings | Six `test_lane_*` with scenario docstrings | `tests/test_outputs.py:281-477` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives (-3,-3,-2,-2) | `entire-report.txt:298-301` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All lines use ±1,2,3 | `entire-report.txt:288-301` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 14 Agent lines | `entire-report.txt:288-301` |
| 35 | CHECK | Rubric criteria are detailed and precise | Module-specific trace checks; 26 pts ≤40 cap | `entire-report.txt:288-301` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Bad behaviors carry negative scores | `entire-report.txt:298-301` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:288-301` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:288-301` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:288-301` |
| 40 | CHECK | All required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh present | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, environment block complete | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | rust/bash, dns/serialization tags match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty = "hard"` present; platform `medium`; worst-model 60% — mismatch informational only | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not milestone | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not milestone | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not milestone | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | `.dockerignore` excludes tests/ | `environment/.dockerignore:13-14` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ excluded from image | `environment/.dockerignore:13` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests copy fixtures to workroot; multi-lane cross-checks prevent fixture-only edits | `tests/test_outputs.py:97-100` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% ≤ 80% | `entire-report.txt:19-21` |
| 55 | CHECK | Task is not too hard or unfair | Docs supply binary layouts and reload rules; 60% worst-model indicates solvable | `environment/docs/toolchain.md`, `entire-report.txt:19-21` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 21, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build znctl at `/tmp/znctl-build/debug/znctl` | all lanes (session fixture) | covered | `tests/test_outputs.py:81-94` |
| init / apply-scope / normalize / reload workflow | `test_lane_a`–`test_lane_f` | covered | each lane calls `_run_cmd` |
| Fixtures m1–m3, scopes s1–s3 | lanes use m1/m2/m3 + s1/s2/s3 | covered | e.g. `test_lane_a:284-285` m2/s2 |
| Lane order matches include visit order | `test_lane_a` | covered | `tests/test_outputs.py:298` `["nest","deep","top"]` |
| Wrong anchor scope on nested includes | `test_lane_a`, `test_lane_c` | covered | `tests/test_outputs.py:300-301,365-368` |
| Carry totals / reload idempotency | `test_lane_b`, `test_lane_f` | covered | `tests/test_outputs.py:310-339,445-477` |
| State deletion mid-workflow converges | `test_lane_b`, `test_lane_d` | covered | journal/material deletion scenarios |
| record-catalog.jsonl fields | all lanes | covered | `_CATALOG_FIELDS`, `_catalog()` |
| equiv-report.jsonl fields | all lanes | covered | `_EQUIV_FIELDS`, `_assert_catalog_equiv_zone_align` |
| emitted.zone lane order | all lanes | covered | `_zone_lines`, alignment helper |
| Do not hand-edit `.state` products | implicit (commands only) | covered | tests wipe products then re-run commands |
| Binary layouts / digest rules in docs | `test_lane_e`, helpers | covered | `_read_scope`, `_material_rows_in_order`, `_fnv1a16` |
| Ordinal-zero includes kept | `test_lane_a` (m2 nested) | covered | m2 include structure + lane order assertion |
| Re-run without master edits reproduces prior pass | `test_lane_b` | covered | reload after product wipe |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #13-20, #15 base pin |
| `environment/requirements.lock` | #14 pinning |
| `environment/.dockerignore` | #50-51 |
| `environment/docs/toolchain.md` | #5, #27, digest/binary spec |
| `environment/docs/reload-path.md` | #5, #27, reload carry rules |
| `environment/src/model.rs` | adjudication claim 7 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate origin-include-normalize/
Summary: 0 error(s), 10 warning(s), 2 info
Task type detected: regular
```

Warnings are non-blocking: docstring linter false negatives (docstrings present), reload-path.md "then" pattern heuristic, diversity info for non-milestone.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model; 1 timeout |
| oracle | 100.0% (3/3) | per export |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not required |

### Rubric positive points

| Field | Value |
|-------|-------|
| Source | `entire-report.txt` lines 288–301 |
| Positive point total | **26** |
| Cap | 40 |
| Status | PASS (26/40) |
| Format | Flat non-milestone (no `# Rubric N` headers) |
| Per-block | N/A (non-milestone) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `origin-include-normalize` matches export; regular layout |
| 1 Instruction | ☑ | Concise, absolute paths, no hints in instruction body |
| 2 Environment | ☑ | Digest-pinned Rust base; tmux/asciinema; offline verifier venv |
| 3 Oracle | ☑ | Static review only — algorithmic patches, not hardcoded outputs |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; docstrings present |
| 5 Metadata | ☑ | `allow_internet=false`; timeouts plausible |
| 6 Rubric | ☑ | Flat format correct for non-milestone; 26 pts; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; worst-model 60% |
| 8 Novelty & fairness | ☑ | Multi-module Rust repair; anti-cheat via dynamic checks |
| 9 Long context | ☐ | N/A — no `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The instructions are clear about the znctl workflow and output artifacts, the toolchain and reload docs give agents enough to reason about binary layouts and carry semantics, and the six integration lanes exercise real cold/reload/state-loss scenarios with dynamically computed digests. The Dockerfile is digest-pinned with verifier deps baked in at build time, and the platform rubric is correctly scoped as a flat non-milestone list under the 40-point cap. I didn't find any spec-test gaps or easy cheating paths. Only note: oracle wasn't re-run in this review pass — worth a quick oracle check on submit if you haven't recently.

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

_Report enriched after manual audit per `prompt.md`. Automated `./scripts/terminus review` initially flagged #14/#20/#31 — all overturned with file evidence._
