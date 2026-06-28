# Terminus Review Report: `video-segment-coassigner`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 100% 3/3; local harbor CLI did not complete) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** No High or Medium blockers on manual audit. Spec, tests, oracle, Dockerfile, and platform rubric align. Automated `terminus review` blocker #14 (unpinned pip) is a false positive — `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are pinned. External report’s non-canonical base-image warning is wrong: `environment/Dockerfile:1` matches the sanctioned `node:22-bookworm-slim` digest in `docs/guidelines/dockerfxile.md`. Platform rubric uses correct **flat non-milestone** format (not milestone `# Rubric N` blocks). ChatGPT Accept is confirmed.

**Insights (concise):**

- Rubric format is correct for `number_of_milestones = 0` — flat `Agent …, ±N` lines with no `# Rubric 2+` headers; not incorrectly milestone-structured.
- Rubric positive sum is 43 pts (guideline 10–40) — Low polish only, not blocking.
- `task.toml` declares `medium` but worst-model 80% maps to easy tier — note for calibration (#45 UNCHECK), not a revision blocker.
- Fixed-seed requirement in `instruction.md:5` has no dedicated test — reproducibility only; no cheating path (Low).
- Portal justification field in `entire-report.txt:317-318` incorrectly says “approved Python image”; Dockerfile already uses canonical Node — author should fix portal text, not task files.
- Instruction is one dense spec paragraph — readability polish (Low); technically complete and fully tested.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept; no High/Medium (ChatGPT) | **Agree** | Full artifact audit; no spec/env/verifier/rubric blockers |
| 2 | Instruction dense; optional section formatting (ChatGPT / `entire-report.txt:174-196`) | **Agree** (Low only) | `instruction.md:1-5` single compressed paragraph with inline formulas |
| 3 | Non-canonical base image (`entire-report.txt:149-171`) | **Disagree** | `environment/Dockerfile:1` = `node:22-bookworm-slim@sha256:f3a68cf…` matches `docs/guidelines/dockerfxile.md:10` and `scripts/validate_task.py:66` |
| 4 | Portal justification says “approved Python image” (`entire-report.txt:317-318`) | **Agree** (portal metadata only) | Wrong portal text; Dockerfile uses canonical Node — fix submission note, not a task blocker |
| 5 | All LLMaJ quality checks pass (`entire-report.txt:112-121`) | **Agree** | Cross-checked instruction, tests, model, Dockerfile, solve.sh |
| 6 | Test quality robust; fixed seed untested (`entire-report.txt:277-278`) | **Agree** (Low) | `instruction.md:5` “fixed seed”; no `test_*` asserts seed — reproducibility only |
| 7 | Agent 80%/60%; oracle 100%; timeout gate pass (`entire-report.txt:24-37`) | **Agree** | Worst 80% ≤80% → #54 passes; oracle 3/3 |
| 8 | Instruction sufficiency PASS; npx ts-node env mismatch (`entire-report.txt:87-92`) | **Partially agree** (not blocking) | `environment/Dockerfile:17` pre-installs `npm ci`; agents should use `npx tsc && node` — agent tooling issue |
| 9 | READY TO USE recommendation (`entire-report.txt:249-253`) | **Agree** | Confirmed after challenging base-image and pip claims |
| 10 | Automated review #14 unpinned pip (`review-report.md` baseline) | **Disagree** | `environment/Dockerfile:9-11` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 11 | Platform rubric lines 296–311 (`entire-report.txt`) | **Agree** (correct non-milestone format) | Flat list, no `# Rubric 2+`; 4 negatives; see §4 #32–39 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | One paragraph, ~200 words | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Compressed inline formulas/thresholds read as spec block | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | No ##, tables, or code fences | `instruction.md` |
| 4 | CHECK | No step-by-step instructions | States requirements, not patch steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Formulas are normative requirements | `instruction.md` |
| 6 | CHECK | No design doc style tables | None | — |
| 7 | CHECK | Instruction is well specified | Paths, schema, scoring, thresholds, TS path all explicit | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Real constrained optimization / streaming assignment | Task design |
| 9 | CHECK | Instruction is unique | TypeScript co-assigner + FNV affinity theme | Task content |
| 10 | CHECK | All paths in instruction are absolute | `/app/task_file/...` throughout | `instruction.md:1,5` |
| 11 | CHECK | Task name does not appear in instruction.md | Name absent from instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Build-time packages only; `allow_internet=false` | `task.toml:24`, `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | pytest pins present | `environment/Dockerfile:9-11` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | FROM digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY task_file only | `environment/Dockerfile:13` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Empty placeholder `Main.ts`; scoring in `/tests` only | `environment/task_file/src/Main.ts:1-8` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:9-11`, `tests/test.sh:21-23` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) on platform | `entire-report.txt:30` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Writes TS, `npx tsc`, `node` locally | `solution/solve.sh:201-202` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Simulated annealing + greedy init in heredoc | `solution/solve.sh:6-198` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Early 0 + overwrite on result | `tests/test.sh:4-5,25-28` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward pattern | `tests/test.sh:25-28` |
| 27 | CHECK | All tests are aligned with instructions | All instruction reqs traced; fixed seed untested (Low) | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Score thresholds, capacity, probe, compile/run | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Primary checks are output scores/constraints; `test_source_is_not_a_shellout` enforces stated TS-not-Python rule | `tests/test_outputs.py:164-167` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | JSONL parsed; scores computed via model | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` methods documented | `tests/test_outputs.py:79-225` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives in platform rubric | `entire-report.txt:308-311` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Only ±1,2,3,5 used | `entire-report.txt:296-311` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | All lines conform | `entire-report.txt:296-311` |
| 35 | CHECK | Rubric criteria are detailed and precise | FNV, constraints, CLI, score thresholds | `entire-report.txt:296-311` |
| 36 | CHECK | Rubric criteria use positive language | Negatives name bad actions directly | `entire-report.txt:308-311` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No `/tests/` refs | `entire-report.txt:296-311` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No instruction.md/task.toml refs | `entire-report.txt:296-311` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:296-311` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | Task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | Task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | typescript, optimization, data-processing | `task.toml:8-11` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `medium`; worst-model 80% → easy tier | `task.toml:7`, `entire-report.txt:25-26`, `docs/guidelines/difficulty.md` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:12` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests; no COPY tests | `environment/.dockerignore:17`, `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ excluded | `environment/.dockerignore:16-17` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | SHA-256 integrity tests on inputs | `tests/test_outputs.py:78-87` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 80.0% — not >80% | `entire-report.txt:25-26` |
| 55 | CHECK | Task is not too hard or unfair | Complete spec; offline toolchain; fair thresholds | `instruction.md`, `environment/Dockerfile:17` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 2, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/task_file/output_data/assignment.jsonl` JSONL schema | `test_assignment_exists`, schema tests | covered | `instruction.md:1`; `tests/test_outputs.py:92-111` |
| Every segment exactly once | `test_every_segment_assigned_once` | covered | `instruction.md:1`; `tests/test_outputs.py:98-104` |
| Valid node IDs, no CPU/bitrate overflow | `test_all_node_ids_valid`, `test_capacity_respected` | covered | `instruction.md:1`; `tests/test_outputs.py:106-124` |
| Base score ≥ 0.925 | `test_base_score` | covered | `instruction.md:3`; `tests/test_outputs.py:136-145` |
| Strict score ≥ 0.925 (affinity/cpu gates) | `test_strict_score` | covered | `instruction.md:3`; `tests/test_outputs.py:149-156`, `tests/model_for_tests.py:7-17` |
| Modified-config score ≥ 0.60 | `test_program_reads_node_config` | covered | `instruction.md:3`; `tests/test_outputs.py:194-225` |
| FNV-1a constants, affinity, incompatible pairs | score tests via `model.py` | covered | `instruction.md:2-3`; `tests/model.py:29-77` |
| TypeScript at `/app/task_file/src/Main.ts`, compiles, runs | `TestTsImplementation` | covered | `instruction.md:5`; `tests/test_outputs.py:159-192` |
| CLI input/output dirs | `test_compiled_program_produces_output`, probe | covered | `instruction.md:5`; `tests/test_outputs.py:46-50,184` |
| Fixed seed / deterministic optimization | — | gap (Low) | `instruction.md:5`; no test asserts reproducibility |
| Input integrity (read-only inputs) | `test_segments_hash`, `test_node_config_hash` | covered | `tests/test_outputs.py:78-87` |
| No incompatible-pair penalty (hard) | `test_no_penalty` | covered | `tests/test_outputs.py:128-132` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #2, #7, #10, §5 |
| `task.toml` | #13, #42-45, #46-49 N/A |
| `environment/Dockerfile` | #14-17, #20, base-image adjudication |
| `environment/.dockerignore` | #50, #51 |
| `environment/task_file/src/Main.ts` | #17 placeholder |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `tests/model.py` | scoring alignment |
| `tests/model_for_tests.py` | strict gates |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | agent stats, rubric, external claims |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: video-segment-coassigner/ ===
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

(Warning on pip pinning is false positive — packages are `==`-pinned.)

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 timeouts |
| terminus-claude-opus-4-8 | 80.0% (4/5) | 1 timeout |
| oracle | 100.0% (3/3) | Platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (60–80% band) |
| Declared difficulty | medium |
| Tier match (#45) | no — calibration note only |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `video-segment-coassigner`; regular task; matches `entire-report.txt` |
| 1 Instruction | ☑ | Dense but complete; spec-like tone (#2 UNCHECK) |
| 2 Environment | ☑ | Canonical Node digest; tmux/asciinema; offline npm ci |
| 3 Oracle | ☑ | Algorithmic solve.sh; platform 100% |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, docstrings |
| 5 Metadata | ☑ | Complete; difficulty calibration mismatch only |
| 6 Rubric | ☑ | Flat non-milestone format correct; 43 pos pts (Low) |
| 7 LLMaJ & agent evidence | ☑ | Challenged base-image and pip claims |
| 8 Novelty & fairness | ☑ | Anti-cheat probe + hash checks |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall — the scoring contract is tight, anti-cheat is strong (input hashes, modified-config probe, no-Python-shellout check), and the offline TypeScript toolchain is set up well. Oracle passes cleanly and agent rates look reasonable for the difficulty band. I’d only suggest optional readability polish on the instruction (break scoring/constraints into short sections) and fixing the portal base-image justification text — the Dockerfile already uses the canonical pinned Node image. Rubric format is correct for a non-milestone task (flat criteria, not milestone blocks).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no (Low density only) | — |
| Test Alignment/Coverage Issues | no (fixed-seed gap Low) | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Rubric | no (43 pos pts Low) | — |
| Metadata Issues | no (#45 informational) | — |
| Task Difficulty | no (80% not >80%) | — |
| Milestones | no (N/A) | — |

*No blockers — error categories: none*
