# Terminus Review Report: cdn-pop-coassigner

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per submission report; not re-run — Docker unavailable locally) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Task is structurally sound with strong anti-cheat verifiers (input hashes, Go recompilation, modified-capacity probing). ChatGPT’s Accept call is supported by artifacts. Automated review false-positives on #14 (multiline pip pins) and #36 (“does not” inside a positive criterion) are overturned. Rubric is correctly flat for a non-milestone task at exactly 40 positive points. Only non-blocking note: `category = system-administration` should be `software-engineering`.

**Insights (concise):**

- Non-milestone rubric uses a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct format, not milestone layout.
- Positive rubric total is exactly 40/40 (10 +lines); three distinct −5 negatives present.
- Worst-model pass rate is 60% (Opus 4.8) → medium tier; GPT-5.5 at 100% does not trigger the >80% easy-tier blocker.
- Spec↔test coverage is strong; `SCORING.md` in environment matches `tests/model.py` and all instruction requirements.
- Fixed-seed determinism is stated in `instruction.md` but not tested — Low polish only, not blocking.
- `task.toml` category mislabels an algorithmic optimization task as `system-administration` (#44 UNCHECK).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High/Medium severity issues; Accept | Agree | Full artifact audit; no High/Medium gaps found |
| 2 | ChatGPT: Dockerfile digest-pinned Python base; Go SHA256-verified | Agree | `environment/Dockerfile:3,10` |
| 3 | ChatGPT: Strong anti-cheat via recompilation + modified config | Agree | `tests/test_outputs.py:53-69,176-216` |
| 4 | ChatGPT: Optional polish — inline scoring summary in instruction | Partially agree | `instruction.md:3` delegates to `SCORING.md`; Low only, not blocking |
| 5 | ChatGPT: Optional polish — determinism test for fixed seed | Partially agree | `instruction.md:5` requires fixed seed; no matching test in `test_outputs.py` — Low only |
| 6 | Harbor review: Instruction brevity / SCORING.md delegation | Partially agree | `instruction.md` is 5 lines; `SCORING.md` is authoritative spec — works, suboptimal UX only |
| 7 | Harbor review: Non-canonical Go install on Python base | Agree (informational) | `environment/Dockerfile:9-12` — justified dual-language need |
| 8 | Test quality: “standard library only” not syntactically enforced | Agree (informational) | `GOPROXY=off` in `environment/Dockerfile:18`; sufficient env enforcement |
| 9 | Test quality: Fixed seed not tested | Agree | `instruction.md:5`; no determinism test — Low only |
| 10 | LLMaJ: behavior_in_task_description PASS | Agree | `instruction.md:1-5`, `environment/task_file/SCORING.md:1-25` |
| 11 | LLMaJ: behavior_in_tests PASS | Agree | `tests/test_outputs.py` classes cover all stated behaviors |
| 12 | LLMaJ: anti_cheating PASS | Agree | `.dockerignore:9-10`, recompile probe `test_outputs.py:176-189` |
| 13 | Submission: oracle 100% (3/3) | Agree (report) | `entire-report.txt:32` |
| 14 | Submission: worst-model 60%, medium tier | Agree | `entire-report.txt:27-28,52` |
| 15 | Automated review: #14 unpinned pip | Disagree | `environment/Dockerfile:21-23` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` on continuation lines |
| 16 | Automated review: #36 negative rubric phrasing | Disagree | Match is `does not` inside positive line “…cliff does not reduce the score, +5”; negatives use “Agent modifies/hardcodes/writes…, -5” |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 short paragraphs, ~152 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer-style request; no LLM boilerplate | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT/paths, not solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Build/run paths are output contract; scoring in `SCORING.md` | `instruction.md:3-5` |
| 6 | CHECK | No design doc style tables | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Paths, schema, Go entrypoint, thresholds via `SCORING.md` | `instruction.md`, `SCORING.md` |
| 8 | CHECK | Instruction is interesting | Real CDN PoP co-assignment optimization | — |
| 9 | CHECK | Instruction is unique | Distinct FNV-cliff coassigner domain | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/task_file/...` throughout | `instruction.md:1-5` |
| 11 | CHECK | Task name does not appear in instruction.md | No `cdn-pop-coassigner` in instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Go tarball at image build only; no runtime fetch in env code | `environment/Dockerfile:9-12` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | pytest and pytest-json-ctrf pinned | `environment/Dockerfile:21-23` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:3` |
| 16 | CHECK | Environment does not use context from outside the environment directory | Only `COPY task_file/` | `environment/Dockerfile:25` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Starter skeleton writes empty file only | `environment/task_file/src/main.go:1-12` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:21-23`, `tests/test.sh:19-21` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Submission report oracle 100% (3/3) | `entire-report.txt:32` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes/compiles/runs Go locally | `solution/solve.sh:1-7` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full Go optimizer with search/repair | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward pattern | `tests/test.sh:3-4,23-27` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | Only 0/1 written | `tests/test.sh:4,24-26` |
| 27 | CHECK | All tests are aligned with instructions | Every instruction req traced to tests (see §5) | `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Score thresholds, constraints, dynamic probe | `tests/test_outputs.py:141-216` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep; evaluates output + rebuild | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Thresholds/hashes used appropriately | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All test methods have docstrings | `tests/test_outputs.py:102-192` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 lines at −5 | `entire-report.txt:353-355` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All ±1,3,5 | `entire-report.txt:343-355` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 13 Agent lines, flat list | `entire-report.txt:343-355` |
| 35 | CHECK | Rubric criteria are detailed and precise; positive cap ≤40 | 40 positive pts exactly | `entire-report.txt:343-352` |
| 36 | CHECK | Rubric criteria use positive language | Negatives are “Agent modifies/hardcodes/writes…, -5”; no “Agent does not X, +1” | `entire-report.txt:353-355` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:343-355` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No task.toml/instruction refs | `entire-report.txt:343-355` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:343-355` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | No stray README/jobs/data | task root |
| 42 | CHECK | author_name and author_email fields present | Both in task.toml | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | difficulty, category, tags, timeouts, allow_internet | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories are applicable to the task | `category = system-administration` wrong for Go optimization; should be `software-engineering` | `task.toml:8`, `docs/task-type-taxonomy.md:13` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `medium` in task.toml; platform medium; worst-model 60% | `task.toml:7`, `entire-report.txt:22-28` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:12` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:10` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ excluded from image | `environment/.dockerignore:9-10` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | SHA-256 integrity check on inputs | `tests/test_outputs.py:19-22,102-105` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% worst-model pass rate) | Worst-model 60% ≤ 80% | `entire-report.txt:27-28` |
| 55 | CHECK | Task is not too hard or unfair | Failures are timeout/compile, not spec gaps | `entire-report.txt:53-91` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Read-only inputs `assets.jsonl`, `pops_config.json` | `test_inputs_unmodified` | covered | `test_outputs.py:102-105` |
| Write `assignment.jsonl` to output_data | `test_assignment_exists` | covered | `test_outputs.py:108-111` |
| JSONL schema `{"asset_id","pop_id"}` | schema tests | covered | `test_outputs.py:114-138` |
| Every asset assigned exactly once | `test_every_item_assigned_once` | covered | `test_outputs.py:115-121` |
| Valid pop ids only | `test_all_bucket_ids_valid` | covered | `test_outputs.py:123-128` |
| No capacity overflow | `test_capacity_respected` | covered | `test_outputs.py:130-138` |
| Hard constraints (no penalty) | `test_no_penalty` | covered | `test_outputs.py:141-146` |
| Base score ≥ 0.67 | `test_base_score` | covered | `test_outputs.py:149-158`, `SCORING.md:22-23` |
| Strict score ≥ 0.67 (affinity/balance gates) | `test_strict_score` | covered | `test_outputs.py:161-168`, `SCORING.md:21-23` |
| Go `main.go` at `/app/task_file/src/main.go` | `test_go_source_present` | covered | `test_outputs.py:172-174` |
| Recompiled binary must score | `test_recompiled_program_scores` | covered | `test_outputs.py:176-189` |
| Dynamic config / modified capacities ≥ 0.57 | `test_program_reads_config_dynamically` | covered | `test_outputs.py:191-216`, `SCORING.md:24-25` |
| FNV-1a affinity/incompat model | score tests via `model.py` | covered | `tests/model.py:11-27`, `SCORING.md:8-18` |
| Standard library only | — | gap (env only) | `GOPROXY=off` `Dockerfile:18`; Low |
| Fixed seed for randomized search | — | gap | `instruction.md:5`; Low |
| Build/run commands | recompile + `_run` | covered | `test_outputs.py:61-74,176-189` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #13-20, #14 adjudication |
| `environment/.dockerignore` | #50-51 |
| `environment/task_file/SCORING.md` | #7, #27, scoring spec |
| `environment/task_file/src/main.go` | #17 starter skeleton |
| `solution/solve.sh` | #21-23 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, anti-cheat |
| `tests/model.py` | scoring fidelity |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats |
| `docs/task-type-taxonomy.md` | #44 category |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: cdn-pop-coassigner/ ===
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

Warning on multiline `pip install` line is a false positive — packages are `==`-pinned on following lines.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | worst model; 2 timeouts |
| oracle | 100.0% (3/3) | per submission report |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | medium |
| Platform classified | medium |
| Tier match (#45) | yes |

### Rubric format (non-milestone check)

| Check | Result | Proof |
|-------|--------|-------|
| `number_of_milestones` | 0 | `task.toml:12` |
| Rubric has `# Rubric 2+` headers | No — flat list only | `entire-report.txt:343-355` |
| Positive point total | 40 (cap 40; not >40) | rubric-points script |
| Negative criteria | 3 at −5 | `entire-report.txt:353-355` |
| Milestone rubric format misuse | **No** — correctly flat | — |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task `cdn-pop-coassigner`; regular layout; report matches task |
| 1 Instruction | ☑ | Concise; delegates scoring to `SCORING.md` (acceptable spec file) |
| 2 Environment | ☑ | Digest-pinned base; tmux/asciinema; GOPROXY=off; no solution/tests COPY |
| 3 Oracle | ☑ | Derives via Go compile+run; not hardcoded |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; strong anti-cheat |
| 5 Metadata | ☑ | Category mislabel only (Medium, non-blocking) |
| 6 Rubric | ☑ | Flat non-milestone format; 40/40 positives; ≥3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Agent failures execution/timeouts, not spec gaps |
| 8 Novelty & fairness | ☑ | Multi-step algorithmic task; cheating paths closed |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The Go optimizer contract is clear, the environment is well set up with a pinned base and offline Go toolchain, and the tests are strong — especially recompiling `main.go` and probing modified capacities so hardcoded assignments can’t slip through. Oracle and agent stats look right for medium difficulty. One small metadata fix: change `category` from `system-administration` to `software-engineering` since this is an optimization/constraint task, not OS admin. Optional polish if you want: a one-line scoring summary in `instruction.md` and a determinism check for the fixed-seed requirement.

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
| Metadata Issues | no (note only) | — |
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
