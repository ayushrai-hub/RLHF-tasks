# Terminus Review Report: `clinicflow-milestone-capacity-actions-v6-reviewfix`

**Generated:** 2026-06-28 (manual re-audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/clinicflow-milestone-capacity-actions-v6-reviewfix`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 38 warnings — all false positives on manual audit) |
| **Oracle** | pass (100% per `entire-report.txt`; local `./scripts/terminus oracle` not runnable — Harbor config error) |
| **CHECK count** | 55 |
| **UNCHECK count** | 0 |

**Error categories (internal):** none

**Decision (concise):** Accept. This is a well-built four-milestone Clinicflow CLI task. Contract, per-milestone instructions, verifiers, oracle, and platform rubrics align. The prior `batch_prefix` → `CF` spec gap is fixed in `clinicflow_contract.md`. Automated `./scripts/terminus review` blockers (#1, #14, #20, #31) are false positives after file-level proof. No High or Medium blockers remain.

**Insights (concise):**

- Each milestone `instruction.md` is ~100 words / 3 paragraphs; automated tool wrongly summed all four files (414 words) as one prompt.
- `pytest==8.4.1` is baked via `requirements.lock` + `--require-hashes` in `environment/Dockerfile:9`; `test.sh` does not install at runtime.
- All 31 `test_*` functions have docstrings; validator AST check is stale.
- Milestone tasks must **not** have root `[agent]`/`[verifier]` per `docs/guidelines/milestones.md:99` — external Harbor warning is incorrect for this layout.
- Platform rubric uses correct milestone format (`# Rubric 1`–`# Rubric 4`); task is milestone (`number_of_milestones = 4`), not a flat non-milestone rubric.
- Worst-model pass rate is 80% (at tier boundary, not >80%); best-model 20% supports declared `hard`.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M4 `batch_prefix` must default to `CF` but contract omits it (entire-report L15) | **Disagree** (fixed in reviewfix) | `environment/docs/clinicflow_contract.md:127` — "If `batch_prefix` is missing, use the default string `CF`"; `:133` repeats in `batch_key` rule |
| 2 | ChatGPT Accept — no High/Medium issues | **Agree** | Manual re-audit confirms; see sections 2, 5 |
| 3 | Optional: remove unused `uv` from lock file (ChatGPT Low) | **Agree** (Low only) | `environment/requirements.lock:1`; no script uses `uv`; not blocking |
| 4 | Missing root `[verifier]`/`[agent]` in task.toml (entire-report L168–187) | **Disagree** | `docs/guidelines/milestones.md:99` — "No top-level `[agent]` or `[verifier]`"; per-step timeouts at `task.toml:27–52` |
| 5 | NEEDS REVISION for root timeouts (entire-report L257–260) | **Disagree** | Same as #4; milestone layout is canonical |
| 6 | LLMaJ `behavior_in_task_description` PASS | **Agree** | Contract covers schemas, ordering, digest, fallbacks, `batch_prefix` default |
| 7 | LLMaJ `behavior_in_tests` PASS | **Agree** | 31 tests across M1–M4 with dynamic fixtures; spot-checked M4 reconciliation, cap order, empty audit |
| 8 | Agent M4 failures = implementation gaps, not spec (entire-report L107–111) | **Agree** | Failures on `test_missing_or_malformed_dependency_returns_empty_audit_schema` match agent code bugs; contract L127 + L142 define empty audit path |
| 9 | Automated review blockers #1, #14, #20, #31 | **Disagree** | See section 4 proofs; each fails on manual read |
| 10 | Test quality ROBUST all milestones (entire-report L263–449) | **Agree** | Synthetic fixtures, exact recomputation, no shortcut paths found |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone file is 3 short paragraphs (~100 words), not one combined prompt | `steps/milestone_1/instruction.md` (109w), `milestone_2` (100w), `milestone_3` (102w), `milestone_4` (103w) |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer briefs pointing to contract dossier | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve steps | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes commands/outputs, defers rules to contract | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instructions | — |
| 7 | CHECK | Instruction is well specified | Clear milestone goals + contract reference | `steps/milestone_*/instruction.md`, `environment/docs/clinicflow_contract.md` |
| 8 | CHECK | Instruction is interesting | Realistic multi-stage clinic scheduling CLI | Task design |
| 9 | CHECK | Instruction is unique | Distinct four-stage Clinicflow domain; no duplicate in repo | Task scope |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder/task slug in prompts | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | Grep clean |
| 13 | CHECK | Dockerfile does not grab web content | COPY local files only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies pinned with == | `requirements.lock` uses `package==version` + sha256 hashes; `--require-hashes` | `environment/requirements.lock:1–12`, `environment/Dockerfile:9` |
| 15 | CHECK | Base Docker image digest-pinned | `@sha256:01f42367...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | COPY only clinicflow, data, docs | `environment/Dockerfile:10–12` |
| 17 | CHECK | No ground truth in environment | Contract specifies behavior, not oracle code; stub CLI raises NotImplementedError | `environment/clinicflow/cli.py:5–18`, `environment/docs/clinicflow_contract.md` |
| 18 | CHECK | No dangerous Docker operations | No privileged mode | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh no runtime installs | `pytest==8.4.1` in lock; test.sh runs pytest only | `environment/requirements.lock:11`, `steps/milestone_1/tests/test.sh:12` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) in submission report | `entire-report.txt:27` |
| 22 | CHECK | Oracle no internet/downloads | `cp` + `python -m clinicflow` only | `steps/milestone_1/solution/solve1.sh:4–5` |
| 23 | CHECK | Oracle reflects instruction | Full algorithmic CLI per milestone, not echo | `steps/milestone_4/solution/clinicflow_cli_m4.py` |
| 24 | CHECK | test.sh reward.txt pattern | mkdir, default 0, binary 0/1 | `steps/milestone_4/tests/test.sh:4–18` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `steps/milestone_*/tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | Contract-backed assertions including `batch_prefix` CF, empty audit, digest | `environment/docs/clinicflow_contract.md:127–142`, `steps/milestone_4/tests/test_m4.py:180–193` |
| 28 | CHECK | Tests check correctness | Exact recomputed scores, caps, mismatch codes | `steps/milestone_1/tests/test_m1.py`, `steps/milestone_4/tests/test_m4.py` |
| 29 | CHECK | Behavior not implementation grep | CLI integration via `main()` | `steps/milestone_4/tests/test_m4.py:8–12` |
| 30 | CHECK | Exact matching justified | Deterministic domain requires exact JSON values | Contract + tests |
| 31 | CHECK | Informative names or docstrings | All 31 tests named + docstringed | `steps/milestone_*/tests/test_m*.py` |
| 32 | CHECK | Rubrics ≥3 negative penalties | 13 negatives across 4 blocks | `entire-report.txt:452–496` |
| 33 | CHECK | Rubric scores from {±1,2,3,5} | No ±4 | `entire-report.txt:452–496` |
| 34 | CHECK | Rubric format `Agent …, ±N` | All lines compliant | `entire-report.txt:452–496` |
| 35 | CHECK | Rubric criteria detailed | Milestone-specific process checks | `entire-report.txt:452–496` |
| 36 | CHECK | Rubric positive phrasing | Bad behavior uses negative scores | `entire-report.txt:470–471` |
| 37 | CHECK | Rubric no /tests/ references | Clean | `entire-report.txt:452–496` |
| 38 | CHECK | Rubric no instruction.md/task.toml refs | Clean | `entire-report.txt:452–496` |
| 39 | CHECK | Rubric no oracle/NOP mentions | Clean | `entire-report.txt:452–496` |
| 40 | CHECK | Required files present | Milestone layout: env Dockerfile + per-step instruction/tests/solution | `task.toml`, `steps/milestone_*/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | Task root listing |
| 42 | CHECK | author_name/email present | anonymous / anonymous | `task.toml:4–5` |
| 43 | CHECK | Other metadata present | category, difficulty, milestones, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | python/bash, data-processing, clinic/cli tags match | `task.toml:7–12` |
| 45 | CHECK | Difficulty matches agent rates | Declared `hard`; best-model 20% supports Hard per difficulty.md | `entire-report.txt:17–23`, `task.toml:6` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/` | `steps/milestone_1` … `milestone_4` |
| 47 | CHECK | solveN.sh per milestone | solve1–4.sh present | `steps/milestone_*/solution/solveN.sh` |
| 48 | CHECK | test_mN.py per milestone | test_m1–m4.py present | `steps/milestone_*/tests/test_mN.py` |
| 49 | CHECK | Milestone test scope | Each file tests one command only | Class `TestMilestoneN` per file |
| 50 | CHECK | Tests not in Docker image | `.dockerignore` excludes tests/; no COPY tests | `environment/.dockerignore:16`, `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | solution/ in dockerignore | `environment/.dockerignore:15` |
| 52 | CHECK | Input data not trivially mutable for cheat | Tests use tmp fixtures + dynamic rules; public CSV preserved by contract | `steps/milestone_1/tests/test_m1.py:45–58` |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80% — at boundary, not >80% | `entire-report.txt:22–23` |
| 55 | CHECK | Not too hard/unfair | M4 edge cases documented in contract; agent failures are implementation bugs | `entire-report.txt:69–111`, contract M4 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | — |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1 normalize schema, validation, scoring, aliases | `test_cli_integration_*`, edge-case M1 tests | covered | `clinicflow_contract.md` M1; `test_m1.py` |
| M2 capacity gates, buffers, owner caps, ordering | `test_service_buffer_*`, `test_risk_buffers_*`, etc. | covered | `clinicflow_contract.md` M2; `test_m2.py` |
| M3 actions, alerts, overrides, empty plan | `test_reason_action_overrides_*`, `test_missing_default_*` | covered | `clinicflow_contract.md` M3; `test_m3.py` |
| M4 reconciliation mismatch codes (5 codes, order) | `test_reconciliation_mismatch_codes_*` | covered | `test_m4.py:113`; contract M4 reconciliation |
| M4 stateful review cap by sorted audit order | `test_stateful_review_cap_*` | covered | `test_m4.py:120–151` |
| M4 `batch_prefix` default `CF` | `test_cli_integration_*` (CF batch keys), override test uses `Q` | covered | `clinicflow_contract.md:127,133`; `test_m4.py:86,145` |
| M4 empty audit on missing/malformed deps | `test_missing_or_malformed_dependency_*` | covered | `clinicflow_contract.md:127,142`; `test_m4.py:180–193`, `EMPTY_AUDIT` |
| M4 digest canonical lines | `test_cli_integration_*`, mismatch test | covered | `test_m4.py:24–39,91` |
| M4 owner_blocked_reasons + hold_code_minutes | `test_owner_reason_blocks_*` | covered | `test_m4.py:153–178` |
| M4 `--rules` override for recomputation | `test_reason_overrides_are_used_*` | covered | `test_m4.py:195–214` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #43–46, milestone metadata |
| `environment/Dockerfile` | #13–16, #20, tmux/asciinema |
| `environment/requirements.lock` | #14, #20 |
| `environment/.dockerignore` | #50–51 |
| `environment/docs/clinicflow_contract.md` | #17, #27, #55, batch_prefix, empty audit |
| `environment/clinicflow/cli.py` | #17 stub scaffold |
| `steps/milestone_*/instruction.md` | #1–12, #27 |
| `steps/milestone_*/tests/test.sh` | #20, #24–26 |
| `steps/milestone_*/tests/test_m*.py` | #27–31, #49 |
| `steps/milestone_*/solution/solveN.sh` | #21–23 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate clinicflow-milestone-capacity-actions-v6-reviewfix/
Summary: 0 error(s), 38 warning(s), 5 info
Task type detected: milestone
```

Warnings are non-blocking: docstring checker false positives (docstrings present), instruction word-count sums all milestones, pip pin heuristic ignores hash lock file.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% | Supports declared `hard` |
| terminus-claude-opus-4-8 | 80.0% | At easy-tier boundary |
| oracle | 100.0% | 3/3 runs |
| nop | 0.0% | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst-model) | easy (at 80% boundary) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model ≤20% Hard rule) |

**Rubric format note:** Task is a **milestone** task (`number_of_milestones = 4`). Platform rubric correctly uses `# Rubric 1` … `# Rubric 4` blocks with 10–40 positive points and ≥1 negative per block — not the flat non-milestone format. No rubric format mismatch.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches clinicflow milestone task; 4 steps |
| 1 Instruction | ☑ | Per-milestone concise prompts + contract dossier |
| 2 Environment | ☑ | Digest-pinned base, tmux/asciinema, hash-locked pytest |
| 3 Oracle | ☑ | Algorithmic solveN.sh; 100% in report |
| 4 Verifiers | ☑ | Binary reward, no runtime installs, behavior tests |
| 5 Metadata | ☑ | Milestone task.toml valid; no root agent/verifier (correct) |
| 6 Rubric | ☑ | Milestone-format rubric in platform submission passes rules |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated in section 3 |
| 8 Novelty & fairness | ☑ | Multi-step reasoning; M4 failures fair |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — it’s a strong four-milestone Clinicflow task. The contract dossier, CLI scaffold, progressive milestones, dynamic fixtures, and audit digest checks all line up well. The earlier M4 `batch_prefix` gap is now documented with the `CF` default, and the empty-audit fallback is clear enough in the contract for agents to implement. I didn’t find any remaining blocking spec, verifier, or environment issues. Optional cleanup: drop unused `uv` from `requirements.lock` if you want a slightly leaner image.

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
