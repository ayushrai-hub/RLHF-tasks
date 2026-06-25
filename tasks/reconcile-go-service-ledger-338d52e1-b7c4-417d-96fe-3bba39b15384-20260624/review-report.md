# Terminus Review Report: reconcile-go-service-ledger

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report; local oracle not executed — Harbor config error) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Task Difficulty, Rubric

**Decision (concise):** Milestone structure, canonical digest-pinned Go base, offline verifier setup, spec-to-test alignment, oracle pass rate, and anti-cheat layers are solid. Two High blockers remain: (1) `task.toml` declares `difficulty = "hard"` but both frontier models scored 60% (Medium tier); (2) portal rubric has zero negative penalties and lines do not use required `Agent …, ±N` format. ChatGPT’s difficulty finding is confirmed; its implied acceptance of rubric is not.

**Insights (concise):**

- `environment/Dockerfile:1` matches the **canonical** `golang:1.24-bookworm` digest in `docs/guidelines/dockerfxile.md:11` — external “non-canonical base” warning is incorrect.
- `entire-report.txt` CRITICAL claim about missing top-level `[agent]`/`[verifier]` is **wrong** for milestone tasks — `docs/guidelines/milestones.md:99` requires per-step timeouts only.
- Auto-validator `#10` (`./cmd/ledger`) and `#14` (unpinned pip) are **false positives** — Go module paths from `/app` WORKDIR; `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are pinned.
- Agent failures are fair implementation errors (ServeMux route ordering on M4); instruction sufficiency checks passed.
- Rubric in `entire-report.txt:477–532` duplicates verifier outcomes as all-positive criteria with no process-trace negatives.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but worst-model pass rate is 60% → observed **Medium** tier | `task.toml:6`; `entire-report.txt:1–7` | Set `difficulty = "medium"` **or** rebalance task until worst-model ≤20% (Hard) |
| 2 | High | Rubric | #32, #34 | Portal rubric has **0** negative criteria (requires ≥3) and lines omit required `Agent` prefix | `entire-report.txt:477–532`; `docs/guidelines/rubrics.md:31–47` | Add ≥3 distinct negative penalties (-1/−2/−3/−5); rewrite each line as `Agent <behavior>, ±N` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `difficulty = "hard"` but evaluation is Medium (60% both models) — Needs Revision | **Agree** | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:6–7` Claude 60%, GPT-5.5 60%; tier table `docs/guidelines/difficulty.md:7–12` |
| 2 | ChatGPT: milestone structure, Dockerfile, tests, oracle, spec alignment all solid | **Agree** | 5 `[[steps]]` in `task.toml:24–67`; canonical digest `environment/Dockerfile:1`; quality checks PASS `entire-report.txt:87–97`; oracle 100% `entire-report.txt:11` |
| 3 | entire-report CRITICAL: missing top-level `[verifier]` and `[agent]` in task.toml | **Disagree** | `docs/guidelines/milestones.md:99` — milestone tasks use `[steps.agent]` / `[steps.verifier]` only; `task.toml:27–67` has per-step timeouts |
| 4 | entire-report WARNING: non-canonical Dockerfile base `golang:1.24-bookworm` | **Disagree** | `environment/Dockerfile:1` digest `sha256:1a6d4452…` matches canonical list `docs/guidelines/dockerfxile.md:11` |
| 5 | entire-report WARNING: env `id.go` uses 8-char SHA vs instruction 16-char | **Agree (non-blocking)** | `environment/app/internal/report/id.go:12` stub bug; M3 instruction specifies 16 chars; intentional starter defect |
| 6 | Quality: behavior_in_task_description PASS | **Agree** | `entire-report.txt:87`; spot-check M1–M5 instructions vs `test_m1.py`–`test_m5.py` |
| 7 | Quality: behavior_in_tests PASS | **Agree** | `entire-report.txt:88`; 27 milestone tests cover stated behaviors |
| 8 | Agent analysis: M4 ServeMux routing failures are agent errors, not spec gaps | **Agree** | `entire-report.txt:57–72`; M4 instruction specifies `POST /v1/reports/compare` route |
| 9 | Auto-review: #1 fail — aggregate 1769 words across milestones | **Disagree** | Milestone instructions evaluated per-step; M1 242w, M3 187w, M4 255w within norms; M5 686w is dense normative API spec, not step-by-step HOW |
| 10 | Auto-review: #10 fail — relative paths `./cmd/ledger` | **Disagree** | `steps/milestone_1/instruction.md:3` — Go package path from `/app` WORKDIR; I/O paths use `/app/...` |
| 11 | Auto-review: #14 fail — unpinned pip | **Disagree** | `environment/Dockerfile:24–25` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 12 | Test quality: all 5 milestones ROBUST | **Agree** | `entire-report.txt:249–472`; exact-value integration tests, runtime fixtures |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Per-milestone scope; M1–M4 within norms; M5 is long but single normative API contract | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer continuation prompts (“Continue in `/app`”, “Finish the reconciliation feature”) | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No heavy headers/tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes and schemas, not dev workflow | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT to build (normalization, API routes), not HOW to debug | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables | No input/output mapping tables | `steps/milestone_*/instruction.md` |
| 7 | CHECK | Instruction is well specified | All tested behaviors explicitly stated per milestone | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic Go service-ledger pipeline with HTTP API | — |
| 9 | CHECK | Instruction is unique | Multi-milestone Go ledger/reconcile task; no duplicate identified | — |
| 10 | CHECK | All paths in instruction are absolute | `./cmd/ledger` is Go module path from `/app`; configs/outputs use `/app/...` | `steps/milestone_1/instruction.md:3` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in body | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `steps/milestone_*/instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:24–25` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Canonical golang digest | `environment/Dockerfile:1`, `docs/guidelines/dockerfxile.md:11` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY `app/` only | `environment/Dockerfile:27` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Intentionally broken stubs; README is neutral overview | `environment/app/internal/config/normalize.go:8–10`, `environment/app/README.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:22–25`, `steps/milestone_1/tests/test.sh:12` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Platform oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solveN.sh patches Go source, `go test ./...` | `steps/milestone_1/solution/solve1.sh:104` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | solve scripts write full Go implementations | `steps/milestone_1/solution/solve1.sh:6–104` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical 0/1 block per milestone | `steps/milestone_1/tests/test.sh:4–19` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching in tests | `steps/milestone_*/tests/test_m*.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary reward per milestone test.sh | `steps/milestone_1/tests/test.sh:15–18` |
| 27 | CHECK | All tests are aligned with instructions | Every assertion traces to milestone instruction | See §5; `entire-report.txt:87–88` |
| 28 | CHECK | Tests check for correctness, not just format | Exact numeric/JSON assertions on computed outputs | `steps/milestone_4/tests/test_m4.py:39+` |
| 29 | CHECK | Tests verify behavior, not implementation | CLI/HTTP integration tests, no source grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact values required for aggregation/reconcile math | `steps/milestone_5/tests/test_m5.py` |
| 31 | CHECK | Tests have informative names or docstrings | All test methods have docstrings | `steps/milestone_1/tests/test_m1.py:38+` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | **0** negatives in portal rubric | `entire-report.txt:477–532` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Uses +1, +2, +3 only (valid set) | `entire-report.txt:477–532` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | Lines start with outcome descriptions, not `Agent` | `entire-report.txt:478` (e.g. “The `go run…`”) |
| 35 | CHECK | Rubric criteria are detailed and precise | Behavior-specific per milestone | `entire-report.txt:477–532` |
| 36 | CHECK | Rubric criteria use positive language | No “Agent does not do X, +1” anti-pattern | `entire-report.txt:477–532` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:477–532` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata/instruction refs | `entire-report.txt:477–532` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:477–532` |
| 40 | CHECK | All required files present | Milestone layout: Dockerfile, per-step instruction/tests/solution, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder (`.snorkel_config` only extra) | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both anonymous | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | version, category, milestones=5, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | Go HTTP API + aggregation; `api_integration` subcategory fits | `task.toml:7–12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 60% → **medium** | `task.toml:6`, `entire-report.txt:6–7` |
| 46 | CHECK | steps/ layout present with per-milestone files | 5 milestones under `steps/` | `task.toml:24–67` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1.sh–solve5.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1.py–test_m5.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | `TestMilestone1`–`TestMilestone5` classes | `steps/milestone_*/tests/test_m*.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests/; no COPY tests | `environment/.dockerignore:14–15` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ excluded from image | `environment/.dockerignore:14–15` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests generate runtime configs/events in `/app/tmp` | `steps/milestone_4/tests/test_m4.py:41–77` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% < 80% | `entire-report.txt:6–7` |
| 55 | CHECK | Task is not too hard or unfair | Failures are agent routing/implementation errors; env provides Go, tmux, asciinema | `entire-report.txt:57–72`, `environment/Dockerfile` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 34, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: normalize names/aliases, validation, `/app/out/config.normalized.json` | `test_normalized_config_is_deterministic_and_complete`, rejection tests | covered | `steps/milestone_1/instruction.md:3–7`, `test_m1.py` |
| M1: boundary weight 1.0, retention 1/365 | `test_boundary_retention_and_weight_values_are_accepted` | covered | `steps/milestone_1/instruction.md:5`, `test_m1.py:158` |
| M2: dedupe, corrections, suppression, retention | `test_summary_dedupes_corrections_aliases_and_unknowns`, `test_summary_applies_retention_after_corrections_per_service` | covered | `steps/milestone_2/instruction.md:5–11`, `test_m2.py` |
| M3: HTTP reports, 16-char report_id, CSV export | `test_report_api_creates_stable_json_and_csv_reports` | covered | `steps/milestone_3/instruction.md:5–7`, `test_m3.py` |
| M4: compare endpoint, statuses, threshold, errors | `test_compare_reports_classifies_metric_drift_and_errors` | covered | `steps/milestone_4/instruction.md:3–14`, `test_m4.py:39` |
| M5: reconcile, impact_score, budget_plan greedy deferral | 12 tests in `TestMilestone5` | covered | `steps/milestone_5/instruction.md:5–11`, `test_m5.py` |

No spec gaps or phantom requirements identified.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45 blocker, #42–44, #46 |
| `entire-report.txt` | Agent stats, rubric, quality checks, oracle |
| `environment/Dockerfile` | #14–15, #20 |
| `environment/.dockerignore` | #50–51 |
| `environment/app/internal/config/normalize.go` | #17 |
| `steps/milestone_*/instruction.md` | #1–11, §5 |
| `steps/milestone_*/tests/test_m*.py` | #27–31, §5 |
| `steps/milestone_*/tests/test.sh` | #20, #24, #26 |
| `steps/milestone_*/solution/solveN.sh` | #22–23 |
| `docs/guidelines/milestones.md` | Adjudication #3 |
| `docs/guidelines/dockerfxile.md` | Adjudication #4 |
| `docs/guidelines/difficulty.md` | Blocker #1 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate → WARN (0 errors, 4 warnings)
- False-positive relative-path warnings on ./cmd/ledger
- False-positive pip pin warning (packages are == pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 other failures |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 other failures |
| oracle | 100.0% (3/3) | Platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | **no** |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 5-milestone Go service-ledger task; report matches folder |
| 1 Instruction | ☑ | Per-milestone prompts; spec-test aligned |
| 2 Environment | ☑ | Canonical golang digest; tmux/asciinema; offline |
| 3 Oracle | ☑ | Platform 100%; solveN.sh implements logic |
| 4 Verifiers | ☑ | Canonical reward block; behavior tests; docstrings |
| 5 Metadata | ☑ | Blocker: difficulty mismatch |
| 6 Rubric | ☑ | Blocker: 0 negatives, wrong line format |
| 7 LLMaJ & agent evidence | ☑ | Quality checks PASS; M4 routing failures fair |
| 8 Novelty & fairness | ☑ | Multi-step reasoning; no cheat paths |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Milestone layout, digest-pinned canonical Go base, verifier wiring, oracle pass rate, and instruction-to-test alignment are strong. Two blockers remain: update `task.toml` `difficulty` from `hard` to `medium` (both frontier models at 60%) or rebalance until Hard-qualified; and fix the portal rubric — add at least three negative penalties and rewrite criteria in `Agent …, ±N` format per rubric guidelines.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Rubric | yes | 2 |
| Metadata Issues | yes | 1 (difficulty field) |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
