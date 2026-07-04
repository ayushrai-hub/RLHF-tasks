# Terminus Review Report: `tbrain-checkpoint-recompute-plan`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are solid — precise instruction, digest-pinned Go image with verifier deps baked in, independent brute-force tests, and a patch-based oracle. The sole High blocker is the **platform rubric**, which is copied from an unrelated DST scheduler task (`dstcron`, `zone.go`, `spring_forward`) instead of this activation-checkpointing planner. Rubric **format** is correctly flat (non-milestone); only **content** must be replaced. No other real blockers found.

**Insights (concise):**

- ChatGPT's High-severity rubric finding is **confirmed** with line-level proof in `entire-report.txt`.
- Rubric is **not** in milestone format — flat `Agent …, ±N` list with no `# Rubric 2+` headers; `number_of_milestones = 0` in `task.toml`.
- Rubric positive total is **39** (≤40 cap) — point cap is **not** a blocker.
- Automated script false-positives on **#7, #10, #20** overturned: instruction is well-specified without file paths; pytest is installed via hash-locked `requirements.lock` in the Dockerfile.
- Worst-model pass rate **60%** (Claude Opus 4.8) — within acceptable range; `difficulty = hard` vs platform `medium` is informational only.
- Oracle not run locally; static review of `solve.sh` + `fix.patch` shows algorithmic fix, not hardcoded answers.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32, #35 | Platform rubric describes the wrong task (DST cron scheduler), not the activation-checkpointing planner | `entire-report.txt:296-315` references `internal/zone/zone.go`, `cmd/dstcron/main.go`, `spring_forward`, `fall_back`, local-to-UTC conversion; task uses `ckptplan`, `internal/plan/plan.go`, peak-memory formula, partition enumeration (`instruction.md:1-35`, `environment/repo/internal/plan/plan.go`) | Replace platform rubric with a flat non-milestone rubric for this task: correct peak-memory formula (checkpoint sum + max in-segment working set), exhaustive/optimal partition selection, feasible minimum-recompute objective, infeasible minimum-peak fallback, tie-breaks (fewer segments, lex-earliest starts), JSON output preservation, and ≥3 distinct negatives (e.g. greedy segmentation, wrong peak formula, hardcoded partitions) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Platform rubric is for wrong DST scheduler task (ChatGPT / user) | **Agree** | `entire-report.txt:296-315` — every positive/negative criterion references DST scheduling (`zone.go`, `schedule.go`, `dstcron`, `spring_forward`, `fall_back`); task is `ckptplan` per `instruction.md:1-8` |
| 2 | Instruction, env, tests, oracle are clean (ChatGPT) | **Agree** | `instruction.md` defines full cost model; `tests/test_outputs.py:64-100` independent `reference()`; `solution/solve.sh` applies `fix.patch` implementing enumeration in `internal/plan/plan.go` |
| 3 | Difficulty metadata should be medium not hard (ChatGPT Low) | **Disagree as blocker** | `task.toml:6` `hard` vs `entire-report.txt:15` `MEDIUM` — per `prompt.md` / `reviewer-checklist-ui.md`, declared vs observed mismatch is never a revision blocker; worst-model 60% ≤80% |
| 4 | Non-canonical Go base image (Harbor review warning) | **Disagree as blocker** | `environment/Dockerfile:1` digest-pinned `golang:1.24-bookworm@sha256:1a6d4452…`; credible justification when no canonical Go image exists; tmux + asciinema present (`Dockerfile:8-9`) |
| 5 | Rubric positive points >40 | **Disagree** | Sum of `+N` lines in `entire-report.txt:296-308` = **39** (≤40 cap) |
| 6 | Non-milestone task uses milestone rubric format | **Disagree** | Platform rubric has no `# Rubric 2+` headers — flat `Agent …, ±N` list per `rubrics.md:66`; `task.toml:9` `number_of_milestones = 0` |
| 7 | #7/#10 fail — no absolute paths (automated review) | **Disagree as blocker** | `instruction.md` has zero file paths (no relative paths either); goal, CLI interface, JSON schema, and optimization objective are fully specified (`instruction.md:10-35`); vacuously satisfies #10 |
| 8 | #20 fail — pytest not in Dockerfile (automated review) | **Disagree** | `environment/Dockerfile:19-22` installs hash-locked `requirements.lock` containing `pytest==8.3.4`; `tests/test.sh:12` runs pytest with no runtime `pip install` |
| 9 | LLMaJ behavior_in_task_description / behavior_in_tests PASS | **Agree** | Cross-checked: all 7 tests map to instruction requirements (see §5) |
| 10 | Agent timeout concern (instruction sufficiency report) | **Partially agree** | `entire-report.txt:29` 2/10 Opus timeouts; `Agent Timeout Gate: ✅`; not a correctness blocker; `task.toml:20` agent timeout 1800s |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three short problem paragraphs plus compact I/O and objective sections | `instruction.md:1-35` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer-facing bug-fix request, no LLM preamble | `instruction.md:1-8` |
| 3 | CHECK | No excessive markdown formatting | Two `##` section headers only; no tables/code blocks/bold | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT to fix, not HOW | `instruction.md:5-8` |
| 5 | CHECK | No hints or solving strategies | No algorithm hints; cost model only | `instruction.md:27-35` |
| 6 | CHECK | No design doc style tables | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear CLI, JSON schema, peak formula, objective, tie-breaks, infeasible fallback | `instruction.md:10-35` |
| 8 | CHECK | Instruction is interesting | Real ML systems memory-planning problem | — |
| 9 | CHECK | Instruction is unique | Activation-checkpointing partition planner; not a duplicate pattern in corpus (static review) | — |
| 10 | CHECK | All paths in instruction are absolute | No paths stated; no relative paths | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder/slug name in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `requirements.lock` uses `==` + hashes | `environment/requirements.lock:1-10` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY limited to `repo/`, `requirements.lock` | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth | Starter has buggy greedy planner, not answers | `environment/repo/internal/plan/plan.go:63-105` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages | pytest via `requirements.lock` in image; test.sh only runs pytest | `environment/Dockerfile:19-22`, `tests/test.sh:12` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed locally (Docker unavailable) | `./scripts/terminus oracle` — RuntimeError |
| 22 | CHECK | Oracle does not require internet | `git apply` + `go build` only | `solution/solve.sh:1-6` |
| 23 | CHECK | Oracle is reflective of instruction | Patch implements enumeration + correct peak formula | `solution/fix.patch`, `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt | Canonical reward block | `tests/test.sh:4-18` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `tests/test.sh:14-17` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to stated cost model / tie-breaks | §5 below |
| 28 | CHECK | Tests check correctness not format | Exact equality vs independent `reference()` | `tests/test_outputs.py:117-124` |
| 29 | CHECK | Tests verify behavior not implementation | Subprocess JSON output only | `tests/test_outputs.py:103-114` |
| 30 | CHECK | No brittle exact string matching | JSON dict equality against computed reference is appropriate | `tests/test_outputs.py:118-124` |
| 31 | CHECK | Tests have informative names or docstrings | Module + per-test docstrings | `tests/test_outputs.py:1-15`, `131+` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | 8 negatives exist but all target wrong (DST) task behaviors | `entire-report.txt:309-316` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use allowed magnitudes | `entire-report.txt:296-316` |
| 34 | CHECK | Each rubric criterion one Agent line | 21 `Agent …, ±N` lines | `entire-report.txt:296-316` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Criteria precise for DST scheduler, not ckptplan | `entire-report.txt:296-315` vs `instruction.md` |
| 36 | CHECK | Rubric criteria use positive language | Negatives phrased as bad behaviors with negative scores | `entire-report.txt:309-316` |
| 37 | CHECK | Rubric does not reference /tests/ | No test refs | `entire-report.txt:296-316` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No metadata refs | `entire-report.txt:296-316` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP mentions | `entire-report.txt:296-316` |
| 40 | CHECK | All required files present | Standard layout | task dir |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Fields set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go scientific-computing; tags match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Field present; mismatch not a blocker | `task.toml:6`, `entire-report.txt:15-21` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped to milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | Only `COPY repo/` | `environment/Dockerfile:29` |
| 51 | CHECK | Solution not accessible in environment | No solution/ COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Tests generate stdin programmatically | `tests/test_outputs.py:105-106` |
| 53 | CHECK | Git repos pinned / no unpinned clone | `git init` on shipped repo only | `environment/Dockerfile:36-40` |
| 54 | CHECK | Task is not too easy | Worst-model 60% ≤80% | `entire-report.txt:19-21` |
| 55 | CHECK | Task is not too hard or unfair | Spec complete; tests independently verify; Opus 60% | `entire-report.txt:19-21`, `instruction.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 21, 32, 35, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| Ample budget → min recompute (retain all when feasible) | `test_ample_budget_keeps_everything_resident`, `test_homogeneous_layers_ample_budget` | covered | `tests/test_outputs.py:131-144` |
| Peak = checkpoint sum + max in-segment working set | `test_peak_includes_in_segment_working_set` | covered | `tests/test_outputs.py:153-159`, `_score:49-61` |
| Optimal min-recompute partition (not greedy packing) | `test_cheapest_feasible_is_not_the_fullest_packing` | covered | `tests/test_outputs.py:162-169` |
| Infeasible → min-peak partition, `feasible: false` | `test_tight_budget_infeasible_reports_lowest_peak` | covered | `tests/test_outputs.py:172-178`, `reference:91-99` |
| Tie-break: fewer segments, lex-earliest starts | enforced in `reference()` | covered | `tests/test_outputs.py:73-79` |
| Single-layer edge | `test_single_layer` | covered | `tests/test_outputs.py:185-188` |
| Two-layer edge | `test_two_layers` | covered | `tests/test_outputs.py:191-195` |
| JSON field names and shape preserved | all tests via `check()` | covered | `tests/test_outputs.py:117-124`, `main.go:24-26` |
| `ckptplan plan --budget B` CLI | all tests via `run_plan` | covered | `tests/test_outputs.py:103-114` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, §5, blocker 1 contrast |
| `task.toml` | #42-45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #15, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `environment/repo/internal/plan/plan.go` | #17, starter bugs |
| `environment/repo/cmd/ckptplan/main.go` | JSON schema |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #22-23 |
| `solution/fix.patch` | #23, oracle algorithm |
| `entire-report.txt` | #32-35, §7 agent stats, rubric blocker |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tbrain-checkpoint-recompute-plan/
Summary: 0 error(s), 0 warning(s), 3 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | `entire-report.txt:21` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 timeouts | `entire-report.txt:20,29` |
| oracle | 100.0% (3/3) | per report; not re-run locally | `entire-report.txt:25` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

**Rubric points:** 39 positive (cap 40) — PASS

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches checkpoint planner; regular non-milestone layout |
| 1 Instruction | ☑ | Precise; no hints; no file paths needed |
| 2 Environment | ☑ | Digest-pinned Go; tmux/asciinema; pytest in image |
| 3 Oracle | ☑ | Static review OK; runtime not verified |
| 4 Verifiers | ☑ | Brute-force reference; canonical test.sh |
| 5 Metadata | ☑ | Complete; category/tags match |
| 6 Rubric | ☐ | **Wrong task content — blocker** |
| 7 LLMaJ & agent evidence | ☑ | Aligns with artifacts |
| 8 Novelty & fairness | ☑ | Non-trivial combinatorial optimization |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the instruction nails the cost model and tie-break rules, the Go environment is clean with a pinned base image, and the tests independently brute-force every partition so agents can't cheat with a greedy fix. The one thing blocking acceptance is the platform rubric: it's still written for a DST cron scheduler (`dstcron`, `zone.go`, spring/fall-back transitions) instead of this `ckptplan` activation-checkpointing planner. Please replace it with a flat rubric covering the peak-memory formula, optimal partition selection, feasible min-recompute vs infeasible min-peak fallback, tie-breaks, JSON preservation, and a few distinct negatives for common wrong approaches.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Test Dependency Location | no | — |
| Other | no | — |
