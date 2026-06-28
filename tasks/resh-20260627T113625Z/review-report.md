# Terminus Review Report: `resh-20260627T113625Z`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (2 errors, 34 warnings — most warnings are false positives) |
| **Oracle** | pass (100% per `entire-report.txt`; not re-run locally — Harbor dataset error) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Milestones, Instruction Styling, Test Alignment/Coverage Issues, Metadata Issues

**Decision (concise):** Strong 5-milestone MSBuild audit task with correct `steps/` layout, pinned Dockerfile, preinstalled pytest, solve wrappers, and comprehensive verifiers. Three real High blockers remain: duplicate top-level `[agent]`/`[verifier]` in `task.toml` (validate ERROR), M4 instruction ambiguity on test-project `Nullable` vs `required_nullable` (6/8 agents failed the same test), and M5 missing explicit blocked-row reason format (distinct from pending policy reasons). Prior revision items (root files, uvx, dockerignore) are fixed.

**Insights (concise):**

- ChatGPT’s three High findings are confirmed with file/line proof; automated script blockers on #1 conciseness, #14 pinning, and #31 docstrings are false positives.
- M2 scopes nullable drift checks to “non-test projects” in prose while oracle/tests apply `required_nullable` to test projects — root cause of universal M4 `Nullable` failures.
- M3/M4 already document `retired dependency: <path>` for blocked rows; M5 omits that for `verify-apply` project rows and `dependency_risks`, causing policy-reason vs blocking-reason confusion.
- Portal rubrics in `entire-report.txt` use correct milestone `# Rubric 1`–`# Rubric 5` headers (not flat non-milestone layout); lines omit required comma before score (`fields +3` vs `fields, +3`) — fix in portal, Low not a revision driver alone.
- Agent rates: Claude 0%, GPT-5.5 40% — not too easy (#54 pass); declared `hard` defensible (#45 pass per best-model rule).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Milestones, Metadata Issues | #43 | Milestone `task.toml` has forbidden top-level `[agent]` and `[verifier]` while per-step timeouts already exist | `task.toml:16-20` duplicates `steps/milestone_*/[steps.agent]` and `[steps.verifier]`; `./scripts/terminus validate` ERROR | Remove lines 16–20 (`[verifier]` and `[agent]` blocks); keep only `[steps.agent]` / `[steps.verifier]` per `docs/guidelines/milestones.md:99` |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | M4 does not unambiguously require test projects to set `Nullable` to policy `required_nullable` on apply | `steps/milestone_2/instruction.md:5` scopes nullable drift to “non-test projects”; `steps/milestone_4/instruction.md:5` says “target … Nullable, including applied test projects” without naming `required_nullable`; `test_m4.py:504` asserts `Nullable == "enable"` for test project with `disable`; 6/8 agent trials failed `test_apply_removes_test_project_rids_and_blocks_cycles_without_edits` per `entire-report.txt:95-96` | Add explicit M4 sentence + example: applied test projects must set `<Nullable>` to `required_nullable` from policy (not leave current value), while still removing RID properties when target RID list is empty |
| 3 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27 | M5 does not state blocked project `reasons` / `dependency_risks.reasons` use blocking strings, not plan policy-mismatch strings | `steps/milestone_5/instruction.md:7-8` says pending rows carry plan reasons but blocked rows lack format; `test_m5.py:196,205` require exact `"retired dependency: Verifier.Retired/Verifier.Retired.csproj"`; trial svYpNyA used policy strings per `entire-report.txt:100` | State explicitly: blocked rows and `dependency_risks` use `retired dependency: <path>` or `dependency cycle` (same as M3/M4), not plan drift reasons like `target framework` or `nullable` |

*No other High blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Top-level `[verifier]`/`[agent]` must be removed (ChatGPT) | **Agree** | `task.toml:16-20`; validate ERROR; `docs/guidelines/milestones.md:99` |
| 2 | M4 test-project nullable not explicit enough (ChatGPT / entire-report) | **Agree** | `steps/milestone_2/instruction.md:5`, `steps/milestone_4/instruction.md:5`, `test_m4.py:458,504`; agent failure pattern in `entire-report.txt:95-96,116-117` |
| 3 | M5 blocked-row reasons need explicit blocking format (ChatGPT / entire-report) | **Agree** | `steps/milestone_5/instruction.md:7-8` vs `steps/milestone_3/instruction.md:7`; `test_m5.py:196,205`; `entire-report.txt:100,118` |
| 4 | Root-level instruction/tests/solution invalid (entire-report L15) | **Disagree — fixed** | No root `instruction.md`, `tests/`, or `solution/`; only `steps/milestone_N/` per glob |
| 5 | Milestone solve.sh should wrap solveN.sh (entire-report L16) | **Disagree — fixed** | `steps/milestone_1/solution/solve.sh:1-5` calls `solve1.sh`; same pattern M2–M5 |
| 6 | Runtime uvx disallowed (entire-report L17) | **Disagree — fixed** | No `uvx` in task tree; `steps/milestone_*/tests/test.sh` uses `python3 -m pytest` |
| 7 | dockerignore incomplete (entire-report L18) | **Disagree — fixed** | `environment/.dockerignore:18-22` excludes `solution/`, `tests/`, `steps/`, `instruction.md` |
| 8 | LLMaJ behavior_in_tests PASS (entire-report L142) | **Partially agree** | Broad coverage holds; M4/M5 instruction gaps are narrow but material for agents |
| 9 | Instruction too long — blocker #1 (automated review) | **Disagree** | Combined 5 milestones = ~1129 words; each `steps/milestone_N/instruction.md` is 2–3 short paragraphs (M1 ≈170 words). Milestone rule: per-milestone prompts (`docs/guidelines/milestones.md:37-39`) |
| 10 | Unpinned pip — blocker #14 (automated review) | **Disagree** | `environment/Dockerfile:10-16` pins `pytest==8.4.1`, etc.; validator false positive on continuation line |
| 11 | 33 tests missing docstrings — blocker #31 (automated review) | **Disagree** | All `test_m*.py` functions have docstrings; validator regex fails on `-> None:` return annotations (`validate_task.py:558` pattern) |
| 12 | Rubric uses milestone format correctly (user question) | **Agree** | `entire-report.txt:707-735` has `# Rubric 1`–`# Rubric 5` blocks with ≥1 negative each — correct milestone layout, not flat non-milestone format. Minor: lines use `+3` without comma before score (`rubrics.md:42` wants `, +3`); 8 positive pts/block (below 10–40 Low advisory) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction is 2–3 paragraphs; aggregate word-count misleading | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering problem framing, not LLM spec boilerplate | `steps/milestone_1/instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | No ##/tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only, no dev walkthrough | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints/strategies | Describes commands and schemas, not implementation steps | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design-doc tables | No input/output mapping tables | — |
| 7 | UNCHECK | Well specified | M4 nullable + M5 blocked-reason gaps | Blockers 2–3 |
| 8 | CHECK | Interesting | Real MSBuild/NuGet policy migration tool | Task content |
| 9 | CHECK | Unique | No duplicate identified in review scope | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name not in instruction | `resh-20260627T113625Z` absent | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No web content fetch | Offline env | `task.toml:23`, `environment/` |
| 14 | CHECK | Pip pinned with == | All packages version-pinned | `environment/Dockerfile:11-16` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367...` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context only | `COPY app/` only | `environment/Dockerfile:18` |
| 17 | CHECK | No ground truth in env | Stub `msbuild_audit.py` prints incomplete | `environment/app/tools/msbuild_audit.py` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safe | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:10-16`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) per platform report | `entire-report.txt:31` |
| 22 | CHECK | Oracle no internet | solve scripts write local Python only | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle not hardcoded | Composes parsing/policy/wave/apply logic | `steps/milestone_4/solution/solve4.sh` |
| 24 | CHECK | reward.txt pattern | mkdir + 0/1 write | `steps/milestone_1/tests/test.sh:9-20` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M4/M5 test assertions exceed written spec clarity | Blockers 2–3; `test_m4.py:504`, `test_m5.py:196` |
| 28 | CHECK | Tests check correctness | Value assertions on JSON and XML | `steps/milestone_*/tests/test_m*.py` |
| 29 | CHECK | Behavior not implementation | No source grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | String matching justified | Exact reason formats are instruction-specified | `steps/milestone_3/instruction.md:7` |
| 31 | CHECK | Informative names/docstrings | All `test_*` have docstrings + descriptive names | `steps/milestone_*/tests/test_m*.py` |
| 32 | UNCHECK | Rubrics ≥3 negatives | N/A — no rubric file in task zip | Portal rubrics in report only |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent line format | N/A | — |
| 35 | UNCHECK | Rubric criteria precise | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Milestone layout: env + task.toml + steps/* | Task tree |
| 41 | CHECK | Clean parent directory | No stray README/jobs | Task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | UNCHECK | Required metadata | Top-level agent/verifier invalid for milestone | `task.toml:16-20` |
| 44 | CHECK | Tags/languages/category | csharp/xml/python, build-and-dependency-management | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: best-model 0%, worst 40% | `entire-report.txt:26-27` |
| 46 | CHECK | steps/ milestone layout | No root instruction/tests/solution | Task tree |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve5.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m5.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | `TestMilestoneN` classes score one milestone | `steps/milestone_*/tests/test_mN.py` |
| 50 | CHECK | Tests not in image | No COPY tests/; dockerignore excludes | `environment/Dockerfile`, `.dockerignore` |
| 51 | CHECK | Solution not in env | dockerignore excludes solution/steps | `environment/.dockerignore:18-20` |
| 52 | CHECK | Input not trivially mutable | Dynamic fixtures + restore_base_projects | `test_m4.py` helpers |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:27` |
| 55 | UNCHECK | Not unfair | M4/M5 spec gaps caused systematic agent failures | `entire-report.txt:113-117` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 32, 33, 34, 35, 36, 37, 38, 39, 43, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| M4: apply TargetFramework + Nullable for test projects | `test_apply_removes_test_project_rids_and_blocks_cycles_without_edits` | **gap** | `instruction.md:5` ambiguous vs `test_m4.py:504` |
| M4: remove test-project RID properties when target RID list empty | same test | covered | `test_m4.py:505-506` |
| M4: blocked rows use `retired dependency:` / `dependency cycle` | `test_apply_honors_dependency_blocks...` | covered | `test_m4.py:379,515`; `instruction.md:7` |
| M5: blocked project reasons = blocking format | `test_verify_reports_retired_dependency_blocks` | **gap** | `test_m5.py:196` exact format; `instruction.md:7-8` silent |
| M5: pending rows carry plan reasons | `test_verify_uses_runtime_profile_targets...` | covered | `test_m5.py:261-265` |
| M2: test project target nullable = required_nullable | `test_plan_classifies_framework_rid_nullable...` | **gap** | `test_m2.py:98-101` never asserts `target.nullable` for Tests.Integration |
| M3: wave ordering by ProjectReference | `test_waves_schema_and_dependency_order` | covered | `test_m3.py:90+` |
| M1: inventory schema + central package resolution | `test_inventory_*` | covered | `test_m1.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker 1, #43 |
| `steps/milestone_2/instruction.md` | Blocker 2, spec gap |
| `steps/milestone_4/instruction.md` | Blocker 2 |
| `steps/milestone_5/instruction.md` | Blocker 3 |
| `steps/milestone_4/tests/test_m4.py` | Blocker 2, #27 |
| `steps/milestone_5/tests/test_m5.py` | Blocker 3, #27 |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `entire-report.txt` | Agent stats, prior claims, portal rubrics |
| `docs/guidelines/milestones.md` | Milestone toml rule |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml: Milestone tasks must not have top-level [agent]
ERROR: task.toml: Milestone tasks must not have top-level [verifier]
(warnings: docstring false positives, pip false positive)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | — |
| terminus-claude-opus-4-8 | 0.0% (0/5) | — |
| oracle | 100.0% (3/3) | platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% supports hard per difficulty.md) |

**Per-test signal:** `test_apply_removes_test_project_rids_and_blocks_cycles_without_edits` 3/10 — systematic spec gap, not random agent noise.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 5-milestone MSBuild audit task; report matches folder |
| 1 Instruction | ☑ | M4/M5 gaps confirmed |
| 2 Environment | ☑ | Pinned, offline, dockerignore OK |
| 3 Oracle | ☑ | Platform 100%; solveN.sh derives logic |
| 4 Verifiers | ☑ | pytest preinstalled; reward block OK |
| 5 Metadata | ☑ | Top-level timeouts blocker |
| 6 Rubric | ☑ | Portal rubrics use milestone headers; comma format advisory |
| 7 Agent evidence | ☑ | M4 dominant failure mode |
| 8 Fairness | ☑ | Spec gaps drive UNCHECK #55 |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task — the `steps/` layout, Dockerfile, anti-cheat dockerignore, and verifier depth are all in great shape, and the earlier structural fixes (no root tests/solution, solve wrappers, preinstalled pytest) look good. Three things before accept: remove the duplicate top-level `[agent]` and `[verifier]` blocks from `task.toml` (you already have per-milestone timeouts). In milestone 4, spell out that applied test projects must set `<Nullable>` to the policy’s `required_nullable` value (with a before/after example for a test project on `disable`), not just update TargetFramework and strip RIDs. In milestone 5, state that blocked project rows and `dependency_risks` use blocking reason strings like `retired dependency: <path>` or `dependency cycle`, not the policy-drift reasons used on pending rows.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Milestones | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | yes | 2, 3 |
| Test Alignment/Coverage Issues | yes | 2, 3 |
| Instruction Styling (portal rubric comma) | advisory only | — |
