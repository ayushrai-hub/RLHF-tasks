# Terminus Review Report: `tbrain-transformer-thermal-excursion`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 4 warnings — all false positives on manual audit) |
| **Oracle** | pass (platform: 3/3; local Docker unavailable) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Accept. Strong Go continuous-time state-machine task: authoritative `docs/spec.md`, digest-pinned canonical `golang:1.24-bookworm` base, verifier deps baked in image via hash-locked wheels, independent Python reference + 8000-scenario differential verifier, and oracle/agent stats all align. Automated `terminus review` flagged #14/#20/#31 — manual audit disproves all three. Platform rubric is correctly formatted as a flat non-milestone list (not milestone blocks).

**Insights (concise):**

- `computeAsset` placeholder in `engine.go` is the sole fix surface; spec covers arm/clear dwells, service-window clock pauses, interpolated budget latch, boundary resolution, and `final.since` semantics.
- Worst-model pass rate is exactly 80% (GPT-5.5); not >80% rejected tier. Best-model 0% (Opus) justifies declared `hard` per `difficulty.md`.
- Harbor "non-canonical base" warning is incorrect — image matches `docs/guidelines/dockerfxile.md` canonical golang digest exactly.
- Agent failures are implementation precision (final.since bookkeeping, arm=0 boundaries), not spec gaps — instruction sufficiency analysis agrees.
- Rubric: 19 flat `Agent …, ±N` lines, 37 positive pts, 7 negatives — correct non-milestone format (no `# Rubric 2+` headers).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium blockers | Agree | Full artifact audit; no spec↔test gaps, env/oracle/verifier compliant |
| 2 | ChatGPT: Optional pointer to `computeAsset` in instruction | Partially agree | Low polish only; `engine.go:222-227` and `README.md:21-22` already orient agents; not blocking |
| 3 | Harbor review: non-canonical base image | Disagree | `environment/Dockerfile:1` matches canonical `golang:1.24-bookworm@sha256:1a6d4452…` in `docs/guidelines/dockerfxile.md:11` |
| 4 | Harbor review: instruction too brief | Partially agree | `instruction.md` is 6 lines but delegates to thorough `docs/spec.md`; LLMaJ `behavior_in_task_description` PASS; Low not blocker |
| 5 | Harbor review: READY TO USE | Agree | Structural audit confirms |
| 6 | Test quality review: ACCEPT | Agree | `tests/test_outputs.py` — curated fixtures + reference cross-check + 8000 differential |
| 7 | LLMaJ: all quality checks pass | Agree | Verified against artifacts; pinned deps in `requirements.lock`, no tests/solution in image |
| 8 | Instruction sufficiency: agent failures are implementation bugs | Agree | `spec.md:172-179` documents `final.since`; failures match edge-case bookkeeping not missing spec |
| 9 | Agent stats: Opus 0%, GPT-5.5 80%, oracle 100% | Agree | `entire-report.txt:24-30` |
| 10 | Automated `terminus review`: #14 unpinned pip | Disagree | `requirements.lock:1-12` uses `==` + SHA256; Dockerfile uses `--require-hashes -r requirements.lock` (`Dockerfile:20-24`) |
| 11 | Automated `terminus review`: #20 pytest not in Dockerfile | Disagree | `requirements.lock:9-10` installs `pytest==8.4.1`; `test.sh` has no runtime installs |
| 12 | Automated `terminus review`: #31 missing docstrings | Disagree | Checkbox requires informative names **or** docstrings; parametrized names like `test_curated_fixture[budget_fails_interpolated]` are descriptive; module docstring at `test_outputs.py:1-21` |
| 13 | User concern: non-milestone task uses milestone rubric format | Disagree (no issue) | `entire-report.txt:324-341` is flat `Agent …, ±N` list with no `# Rubric N` milestone blocks — correct per `rubrics.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 4 short paragraphs, ~91 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering brief tone; defers detail to spec by reference | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | No solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States WHAT (ledger, spec authority), not HOW to implement state machine | `instruction.md` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Goal, CLI contract, spec path, error behavior clear | `instruction.md`, `docs/spec.md` |
| 8 | CHECK | Instruction is interesting | Real continuous-time thermal compliance state machine | — |
| 9 | CHECK | Instruction is unique | Distinct arm/clear/service-window/budget semantics; no obvious TB2 duplicate | — |
| 10 | CHECK | All paths in instruction are absolute | `/app`, `/app/docs/spec.md` | `instruction.md:1,3` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY local wheels/repo only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.lock` pins `==` + hashes; `--require-hashes` | `requirements.lock`, `Dockerfile:20-24` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY wheels/, repo/ only | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Placeholder is intentionally wrong; no expected ledger values | `engine.go:222-227` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in requirements.lock; test.sh only runs pytest | `Dockerfile:20-24`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:30` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` patches and `go build` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | `fix.patch` implements full state machine | `solution/fix.patch` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:4-20` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` | `tests/test.sh:17-19` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to `docs/spec.md` referenced as authoritative | `spec.md`, `test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Full ledger equality vs reference/EXPECTED | `test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Black-box binary invocation | `test_outputs.py:47-55` |
| 30 | CHECK | No brittle exact string matching | JSON structural/deep equality | `test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | Parametrized descriptive case names + module docstring | `test_outputs.py:1-21`, `526-527` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 7 negatives | `entire-report.txt:336-341` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores valid | `entire-report.txt:324-341` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 19 Agent lines | `entire-report.txt:324-341` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific state-machine trace checks | `entire-report.txt:324-341` |
| 36 | CHECK | Rubric criteria use positive language | Bad behaviors described with negative scores; no "does not …, +1" | `entire-report.txt:336-341` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ | No /tests/ refs | `entire-report.txt:324-341` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No task.toml/instruction refs | `entire-report.txt:324-341` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:324-341` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go state-machine / scientific-computing fit | `task.toml:7-18` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: Opus 0% ≤20% Hard rule | `entire-report.txt:25-26`, `difficulty.md` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ not in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Generated scenarios in verifier | `test_outputs.py:583-644` |
| 53 | CHECK | Git repos pinned (no unpinned git clone) | `git init` local only, no remote clone | `environment/Dockerfile:37-41` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 80% is not >80% | `entire-report.txt:26` |
| 55 | CHECK | Task is not too hard or unfair | Complete spec; failures are implementation precision | `spec.md`, agent failure analysis |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / spec) | Test(s) | Status | Proof |
|----------------------------------|---------|--------|-------|
| Arm dwell confirmation; sub-arm transient suppressed | `test_curated_fixture[subarm_transient_suppressed]`, `[exact_arm_confirms_start_at_crossing]` | covered | `spec.md:71-75`, `test_outputs.py:386-395` |
| Clear dwell; sub-clear merge; end = r not r+clear | `[subclear_dip_merges]`, `[end_is_return_not_return_plus_clear]` | covered | `spec.md:80-92`, `test_outputs.py:405-408` |
| Computed boundaries resolve before same-t events | `[return_exactly_at_confirm]`, `[confirm_boundary_at_service_start]` | covered | `spec.md:97-104`, `test_outputs.py:421-443` |
| Service window pauses dwell and over_seconds clocks | `[service_pauses_arm_dwell]`, `[service_pauses_clear_dwell]`, `[service_pauses_over_seconds]` | covered | `spec.md:106-125`, `test_outputs.py:426-439` |
| Budget interpolation and budget=0 at confirm | `[budget_fails_interpolated]`, `[budget_zero_fails_at_confirm]` | covered | `spec.md:131-146`, `test_outputs.py:409-416` |
| Horizon truncation | `[until_truncates_open]` | covered | `spec.md:59-60`, `test_outputs.py:417-420` |
| Final state ok/over/failed and since semantics | `[final_over_at_horizon]`, `[final_ok_clearing_at_horizon]`, `[degenerate_all_zero]` | covered | `spec.md:172-179`, `test_outputs.py:454-465` |
| Assets sorted by name, all configured assets present | `test_assets_sorted_and_independent` | covered | `spec.md:164-165`, `test_outputs.py:537-544` |
| Invalid input → nonzero exit, no stdout ledger | `test_invalid_inputs_exit_nonzero_with_no_stdout` | covered | `spec.md:181-191`, `test_outputs.py:550-577` |
| Deterministic JSON ledger via stdin/stdout CLI | all tests via `run()` / `ledger()` | covered | `instruction.md:1-3`, `test_outputs.py:47-55` |
| Comprehensive boundary coverage | `test_differential_against_reference` (8000 scenarios) | covered | `test_outputs.py:629-644` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27 |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, #50, #53 |
| `environment/requirements.lock` | #14, #20 |
| `environment/repo/docs/spec.md` | #7, #27, section 5 |
| `environment/repo/internal/engine/engine.go` | #17, placeholder scope |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, section 5 |
| `solution/solve.sh`, `solution/fix.patch` | #21-23 |
| `entire-report.txt` | #32-39, #45, #54, section 7 |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `docs/guidelines/rubrics.md` | rubric format (#32-39) |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tbrain-transformer-thermal-excursion/
Summary: 0 error(s), 4 warning(s), 2 info
```

Warnings (#14 pip line heuristic, #31 parametrized docstrings) are false positives on manual audit.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | Worst model; at 80% boundary |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Best-model Hard justification |
| oracle | 100.0% (3/3) | Platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst) | easy (at boundary) |
| Observed tier (best) | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (Opus ≤20% rule) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `tbrain-transformer-thermal-excursion`; regular layout; Go scientific-computing |
| 1 Instruction | ☑ | Brief but spec-authoritative; absolute paths; no leakage |
| 2 Environment | ☑ | Canonical golang digest; tmux+asciinema; hash-locked wheels; no tests/solution COPY |
| 3 Oracle | ☑ | Patch-based real implementation; platform 100% |
| 4 Verifiers | ☑ | Binary reward; no runtime installs; reference + differential |
| 5 Metadata | ☑ | hard, allow_internet=false, timeouts reasonable |
| 6 Rubric | ☑ | Flat non-milestone format; 37/+ pts, 7 negatives |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; failures are agent bugs |
| 8 Novelty & fairness | ☑ | Multi-step state machine; anti-cheat strong |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — it's a strong, well-structured hard task. The offline Go environment is set up cleanly with a pinned base image and hash-locked verifier wheels, `docs/spec.md` is thorough and authoritative, and the test suite (curated fixtures plus an 8000-scenario differential against an independent reference) gives real confidence in correctness. Oracle passes and agent results look right for hard difficulty — Opus at 0% with GPT-5.5 at 80% on the boundary. I didn't find any blocking spec gaps, rubric format issues, or environment problems. The platform rubric is correctly a flat non-milestone list, not milestone blocks. Optional polish: a sentence in `instruction.md` pointing agents at `computeAsset` would help orientation, but the README and engine comments already do that.

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
