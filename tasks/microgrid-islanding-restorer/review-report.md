# Terminus Review Report: microgrid-islanding-restorer

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (not re-run locally; 3/3 per `entire-report.txt`) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** The task is well-built: digest-pinned canonical Go base, offline verifier, SHA-256 anti-cheat, mutated-config binary test, spec-to-test alignment, and oracle pass rate all check out. The sole real blocker is metadata calibration — `task.toml` declares `difficulty = "hard"` but the worst-model pass rate (Claude Opus 4.8 at 60%) places the task in the **Medium** tier per `docs/guidelines/difficulty.md`. Update `difficulty` to `"medium"` or rebalance until ≤20% on at least one reference model.

**Insights (concise):**

- Automated `terminus review` falsely flagged pip unpinned (#14), missing test docstrings (#31), and 100% worst-model (#54); manual re-audit disproves all three.
- `instruction.md` line 5 uses `./src` in the Go build command after `cd /app/task_file`; all data paths are absolute. Optional polish: use `/app/task_file/src` — not a revision driver.
- LLMaJ “non-canonical base image” claim is wrong: Dockerfile uses canonical `golang:1.24-bookworm` digest from `docs/guidelines/dockerfxile.md`.
- LLMaJ “stub must be replaced” and “scoring formula implicit” are fair UX notes but not blockers — instruction sufficiency PASS, agents at 60–100%.
- Rubric in `entire-report.txt` (lines 296–310) meets format/score rules but is not shipped in task folder; portal rubric items #32–#39 are N/A.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared `hard` but worst-model 60% → Medium tier | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:21` Claude 60% (3/5); `docs/guidelines/difficulty.md:10` Medium = 20–60% worst model | Set `difficulty = "medium"` in `task.toml`, or rebalance task until ≤20% on best or worst reference model |

*No other High-severity blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: difficulty `hard` but evaluation is Medium (Claude 60%, GPT 5.5 100%) — Needs Revision | **Agree** | `task.toml:6`; `entire-report.txt:16-22`; tier table `docs/reviewer-checklist-ui.md:52-57` |
| 2 | ChatGPT: digest-pinned Go env, offline verifier, artifact integrity, anti-cheat, oracle, scorer mutation, spec-to-test alignment all solid | **Agree** | `environment/Dockerfile:1-8`; `tests/test_outputs.py:21-23,36-40,89-118`; `tests/test.sh:1-26`; LLMaJ lines 87-97 in `entire-report.txt` |
| 3 | LLMaJ CRITICAL: stub `main.go` misleads; instruction must say replace placeholder and handle `argv[1]` | **Disagree** (as blocker) | `environment/task_file/src/main.go:9-17` stub is empty placeholder; `instruction.md:5` requires full optimizer, score gates, optional input/output args; `entire-report.txt:66-67` task_specification PASS; Claude 60% / GPT 100% show agents succeed without extra note |
| 4 | LLMaJ WARNING: non-canonical `golang:1.24-bookworm` base | **Disagree** | `environment/Dockerfile:1` digest matches canonical entry `docs/guidelines/dockerfxile.md:11` |
| 5 | LLMaJ WARNING: scoring formula implicit in instruction | **Partially agree** (Low) | `instruction.md:3` states base score = restored value / normalizer; full formula in `environment/task_file/scripts/model.py`; agents read public scorer by design — not blocking |
| 6 | LLMaJ TEST QUALITY: ACCEPT — comprehensive coverage | **Agree** | `tests/test_outputs.py` classes cover integrity, schema, constraints, scores, binary rebuild + mutated config |
| 7 | Automated review: #14 unpinned pip | **Disagree** | `environment/Dockerfile:7-8` `pytest==8.4.1 pytest-json-ctrf==0.3.5` |
| 8 | Automated review: #31 missing test docstrings | **Disagree** | `tests/test_outputs.py:36-37,44-45,58-59,80-81,90-91` — all five `test_*` methods have docstrings |
| 9 | Automated review: #54 worst-model 100% too easy | **Disagree** | Worst model is Claude 60% (`entire-report.txt:21`), not GPT 100%; 60% < 80% rejection threshold |
| 10 | Automated review: #10 relative paths | **Partially agree** (Low) | `instruction.md:5` contains `./src` in build command; all I/O paths use `/app/task_file/...` — minor polish only |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs, ~198 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer request, no LLM preamble | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States requirements and thresholds only | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | WHAT to build, not algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | No input/output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Paths, schema, constraints, scores, build cmd explicit | `instruction.md:1-5` |
| 8 | CHECK | Interesting | Real combinatorial optimization / Go task | — |
| 9 | CHECK | Unique | Microgrid islanding + resonance constraints; not a duplicate pattern | — |
| 10 | UNCHECK | Absolute paths only | `./src` in build command on line 5 | `instruction.md:5` |
| 11 | CHECK | Task name not in instruction | No task slug in body | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local data only | `environment/Dockerfile`, `task_file/` |
| 14 | CHECK | Pip deps pinned with == | pytest and ctrf pinned | `environment/Dockerfile:7-8` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452c...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | COPY only `task_file/` | `environment/Dockerfile:10` |
| 17 | CHECK | No ground truth in env | Stub is non-functional placeholder | `environment/task_file/src/main.go` |
| 18 | CHECK | No privileged/docker.sock | Standard RUN/COPY only | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:7-8`, `tests/test.sh:19-20` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:26` |
| 22 | CHECK | Oracle no internet | `GOPROXY=off`, local files | `solution/solve.sh`, `tests/test.sh:16` |
| 23 | CHECK | Oracle derives answer | DFS/backtracking Go solver written at runtime | `solution/solve.sh:5+` |
| 24 | CHECK | reward.txt + failure path | Canonical block lines 21-26 | `tests/test.sh:2-3,21-26` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards 0/1 | echo 0 or 1 only | `tests/test.sh:22-25` |
| 27 | CHECK | Tests aligned with instructions | Every instruction req has test coverage | §5 below |
| 28 | CHECK | Tests check correctness | Scorer violations, score thresholds, binary behavior | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Uses public `model.py` evaluator | `tests/test_outputs.py:18-19` |
| 30 | CHECK | No brittle exact-string checks | JSON/sha256/score thresholds | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All five test methods documented | `tests/test_outputs.py:36-91` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task dir | — |
| 33 | UNCHECK | Rubric scores from allowed set | N/A | — |
| 34 | UNCHECK | Rubric format Agent …, ±N | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Go optimization, system-administration | `task.toml:6-13` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; observed medium (60% worst) | `task.toml:6`, `entire-report.txt:21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:14` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:14` |
| 49 | UNCHECK | Milestone tests scoped | N/A | `task.toml:14` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile:10` |
| 51 | CHECK | Solution not accessible in env | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially mutate inputs | SHA-256 integrity on model.py, feeders, config | `tests/test_outputs.py:21-23,36-40` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model Claude 60% | `entire-report.txt:21` |
| 55 | CHECK | Not too hard/unfair | Instruction sufficiency PASS; 60–100% pass | `entire-report.txt:66-67` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 10, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-------------------------|---------|--------|-------|
| Output `/app/task_file/output_data/restoration_plan.json` | `test_assignment_file_uses_the_required_shape` | covered | `instruction.md:1`; `tests/test_outputs.py:44-54` |
| JSON shape `{"assignments":[{"feeder_id","island_id"}]}` | `test_assignment_file_uses_the_required_shape` | covered | `instruction.md:1`; `tests/test_outputs.py:49-54` |
| Zero-score violation rules (dupes, mandatory, caps, districts, resilience, resonance) | `test_plan_satisfies_capacity_floor_and_resonance_rules` | covered | `instruction.md:3`; `tests/test_outputs.py:58-76` |
| `total_score >= 0.98`, `total_score_strict >= 0.96`, `load_balance >= 0.32` | `test_base_and_strict_scores_clear_the_required_thresholds` | covered | `instruction.md:3-4`; `tests/test_outputs.py:80-86` |
| Build `microgrid_restorer` from `/app/task_file` | `test_binary_regenerates_the_plan_and_handles_a_changed_config` | covered | `instruction.md:5`; `tests/test.sh:14-17`, `tests/test_outputs.py:92-94` |
| Optional input/output directory args; fresh read on mutated config | `test_binary_regenerates_the_plan_and_handles_a_changed_config` | covered | `instruction.md:5`; `tests/test_outputs.py:99,113-118` |
| Do not tamper with scorer/inputs | `test_visible_scorer_and_policy_inputs_are_unchanged` | covered | `tests/test_outputs.py:36-40` |
| Critical spread and district coverage = 1.0 | `test_plan_satisfies_capacity_floor_and_resonance_rules` | covered | `tests/test_outputs.py:62-63` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45 blocker, #42-44 |
| `instruction.md` | #1-12, #27, spec alignment |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/task_file/src/main.go` | LLMaJ stub claim |
| `environment/task_file/scripts/model.py` | Scoring semantics |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment, anti-cheat |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | Agent stats, LLMaJ, oracle |
| `docs/guidelines/difficulty.md` | Tier rules, blocker 1 |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: microgrid-islanding-restorer/ ===
Summary: 0 error(s), 3 warning(s), 2 info
Task type detected: regular
Warnings: relative path hint (./src), module-level test docstring, pip line heuristic
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | `entire-report.txt:22` |
| terminus-claude-opus-4-8 | 60% (3/5) | 2 timeouts; `entire-report.txt:21,30` |
| oracle | 100% (3/3) | `entire-report.txt:26` |
| nop | 0% (0/1) | `entire-report.txt:25` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) Go task |
| 1 Instruction | ☑ | Concise, absolute I/O paths; `./src` minor |
| 2 Environment | ☑ | Canonical golang digest; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Backtracking solver; 3/3 per report |
| 4 Verifiers | ☑ | reward block, no runtime installs, behavior tests |
| 5 Metadata | ☐ | difficulty mismatch — sole blocker |
| 6 Rubric | N/A | Rubric only in external report, not task folder |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated; ChatGPT difficulty claim confirmed |
| 8 Novelty & fairness | ☑ | Multi-constraint optimization; anti-cheat solid |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The digest-pinned Go environment, offline verifier setup, SHA-256 artifact integrity checks, mutated-config anti-cheat, oracle pass rate, and full spec-to-test alignment all look solid. The only blocking issue is difficulty metadata: `task.toml` lists `hard` but evaluation shows Medium based on the worst-model pass rate (Claude Opus 4.8 at 60%). Update `difficulty` to `medium` or rebalance until the task qualifies as Hard.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Rubric | no | — |
