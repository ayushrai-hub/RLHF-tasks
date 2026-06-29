# Terminus Review Report: `go-cli-version-solver`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (platform report 3/3; local oracle not run — Docker unavailable) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling, Metadata Issues

**Decision (concise):** Strong Go semver resolver with solid fixtures, canonical digest-pinned base, and appropriate hard difficulty calibration. **One High blocker:** `diamond_conflict` tests a specific CONFLICT tie-break (`util ^1.0.0`) that `instruction.md` never defines when multiple constraints on the same package fail together — 8/10 agent runs failed only this fixture. Also fix `category = "games"` → `build-and-dependency-management` and clarify bare `NO_UPGRADE` output (Medium).

**Insights (concise):**

- Agent stats: worst-model 20% (gpt-5.5), opus 0% — defensible `hard`; not too easy (#54 passes).
- `diamond_conflict`: 1/10 fixture pass rate; 6/9 trials at 24/25 with this as sole failure — classic spec gap, not agent noise.
- Go base image is **canonical** per `docs/guidelines/dockerfxile.md` (same digest) — external “non-canonical” claim is wrong.
- Platform rubric uses correct **flat** non-milestone format (no `# Rubric 2+`); not milestone-layout rubric.
- Rubric `#36` fails automated positive-phrasing check (`fails to` / `omits` in negatives) — Medium style issue, not a task-acceptance blocker alone.
- UPGRADE transitive-safety untested is a Low coverage note only; not blocking.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | **High** | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | CONFLICT tie-break when multiple constraints on the same package fail is tested but unspecified. `diamond_conflict` expects `CONFLICT util ^1.0.0` (first accumulated constraint from `app`’s `DEPEND`), but instruction only says “print CONFLICT with the package and constraint that failed.” Agents reasonably emitted `CONFLICT util ^2.0.0`. | `instruction.md:5` — no tie-break rule. `tests/test_outputs.py:92-103` — expects `CONFLICT util ^1.0.0`. `solution/solve.sh:168-170,202-205` — oracle uses `constraints[0].raw` / first failing constraint in slice order. `entire-report.txt:63,87` — 1/10 on `diamond_conflict`; 6 trials 24/25. | Add explicit rule, e.g. when several constraints conflict on one package, report the **first** constraint encountered in command order (or first failing constraint in accumulated `needed[pkg]` order). Align oracle if wording differs. |
| 2 | Medium | Metadata Issues | #44 | `category = "games"` mismatches primary activity (semver dependency resolver). | `task.toml:7` — `category = "games"`. `docs/task-type-taxonomy.md:10,24` — build/dep conflict resolution → `build-and-dependency-management`. Tags already say `dependency`, `version-solver`. | Set `category = "build-and-dependency-management"`. |
| 3 | Medium | Instruction Styling, Test Alignment/Coverage Issues | #27 | `NO_UPGRADE` output format ambiguous vs `UPGRADED pkg version` parallel phrasing. | `instruction.md:5` — “prints UPGRADED pkg newVersion or NO_UPGRADE if already at the best” (no “alone” rule). `tests/test_outputs.py:61-63` — expects bare `NO_UPGRADE`. `entire-report.txt:51,89` — 8/10 passed `upgrade_no_change`; 2 agents printed `NO_UPGRADE foo`. | State explicitly: print exactly `NO_UPGRADE` on its own line with no package name. |

*Low-only items (not blockers):* UPGRADE transitive-safety fixture gap; dense instruction prose; rubric negative phrasing style (#36).

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | CONFLICT tie-break for `diamond_conflict` underspecified (ChatGPT High; entire-report instruction sufficiency) | **Agree** | See blocker #1 — `instruction.md:5` vs `test_outputs.py:103`; 8/9 agent failures on ordering. |
| 2 | `category = "games"` should be `build-and-dependency-management` (ChatGPT Medium; Harbor review CRITICAL) | **Agree** | `task.toml:7`; taxonomy `docs/task-type-taxonomy.md:10,24`. |
| 3 | `NO_UPGRADE` should be bare line without package name (ChatGPT Medium) | **Agree** | `instruction.md:5` vs `test_outputs.py:63`; 2/10 agent failures on `upgrade_no_change`. |
| 4 | Go base image may not be canonical (ChatGPT Medium; Harbor WARNING) | **Disagree** | `environment/Dockerfile:1` matches canonical entry `docs/guidelines/dockerfxile.md:11` (same image + digest). #15 passes; no justification needed. |
| 5 | Instruction needs heavy markdown restructuring (Harbor WARNING) | **Disagree** | Dense prose is acceptable per natural-prompt style (#2 passes). Not a spec blocker; optional polish only. |
| 6 | UPGRADE lacks transitive-safety test (test quality review) | **Partially agree** | `instruction.md:5` “without breaking anything” is broad; no transitive UPGRADE fixture in `test_outputs.py`. Low severity — not revision-blocking per `reviewer-checklist-full.md` Low rules. |
| 7 | Constraint string must preserve original syntax (`^2.0.0` not expanded) | **Partially agree** | All CONFLICT fixtures use original constraint strings (`conflict_no_version`, `yank_forces_backtrack`, `diamond_conflict`). Not stated explicitly; only 1/9 trials failed (ypw28Eh). Tie-break gap is the dominant issue; optional clarifying sentence on preserving input constraint text in CONFLICT output. |
| 8 | Rubric uses milestone format incorrectly | **Disagree** | `task.toml:9` — `number_of_milestones = 0`. Platform rubric (`entire-report.txt:414-430`) is flat `Agent …, ±N` list with no `# Rubric 2+` — correct per `docs/guidelines/rubrics.md:64`. |
| 9 | LLMaJ `behavior_in_tests` / `behavior_in_task_description` pass | **Agree with caveat** | Broad command coverage holds; LLMaJ missed the diamond CONFLICT ordering edge case (#1). |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two dense paragraphs, within limit | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Developer request tone, not RFC sections | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | No solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States protocol WHAT, not algorithm HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | CONFLICT multi-constraint tie-break undefined (blocker #1) | `instruction.md:5`, `test_outputs.py:103` |
| 8 | CHECK | Instruction is interesting | Real package-manager resolver problem | — |
| 9 | CHECK | Instruction is unique | Semver backtracking CLI not a duplicate pattern in review scope | — |
| 10 | CHECK | All paths absolute | `/app/solver.go`, `/app/solver` | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No `go-cli-version-solver` string | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | Dockerfile no web content fetch | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | Python deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:6` |
| 15 | CHECK | Base image digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context self-contained | No external COPY | `environment/Dockerfile` |
| 17 | CHECK | No solution/ground truth in environment | Only toolchain setup | `environment/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:6`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle no internet | solve.sh writes local Go source | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective implementation | ~335-line resolver with backtracking | `solution/solve.sh` |
| 24 | CHECK | test.sh reward.txt pattern | mkdir + 0 default + 1 on pass | `tests/test.sh:2-16` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards 0/1 | All-or-nothing pytest gate | `tests/test.sh:13-16` |
| 27 | UNCHECK | Tests aligned with instructions | `diamond_conflict` + `NO_UPGRADE` enforce unstated details | Blockers #1, #3 |
| 28 | CHECK | Tests check correctness | Full stdout protocol + resolution outcomes | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Subprocess on binary only | `tests/test_outputs.py:201-207` |
| 30 | CHECK | Exact matching appropriate | CLI specifies exact output strings | `instruction.md`, `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | Fixture keys + module/param docstrings | `tests/test_outputs.py:1-4,197-199` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives (-5,-3,-3,-2) | `entire-report.txt:427-430` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:414-430` |
| 34 | CHECK | Rubric `Agent …, ±N` format | 17 lines | `entire-report.txt:414-430` |
| 35 | CHECK | Rubric detailed and precise | Task-specific semver/resolver behaviors | `entire-report.txt:414-430` |
| 36 | UNCHECK | Rubric positive phrasing | Negatives use “Agent fails to…” / “Agent omits…” | `entire-report.txt:427-430`; `review_checklist.py:759` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:414-430` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | `entire-report.txt:414-430` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:414-430` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author_name/email present | anonymous fields | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | timeouts, languages, tags | `task.toml` |
| 44 | UNCHECK | Tags/languages/category applicable | `category = "games"` wrong | `task.toml:7` |
| 45 | CHECK | Difficulty matches agent rates | declared `hard`; worst-model 20% ≤20% hard band | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | Not copied to image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Dynamic stdin protocol | `tests/test_outputs.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤80% | `entire-report.txt:26-27` |
| 55 | UNCHECK | Not too hard/unfair | Underspecified CONFLICT rule caused 8/9 near-perfect runs to fail grading | `entire-report.txt:63-87`, blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 36, 44, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| PUBLISH → OK | `publish_single` | covered | `test_outputs.py:13-16` |
| YANK excludes from resolve | `yank_excludes_version`, `yank_forces_backtrack` | covered | `test_outputs.py:37-40,169-181` |
| Constraint types ^ ~ >= exact range | `resolve_*` fixtures | covered | `test_outputs.py:17-36` |
| RESOLVE highest non-yanked, alphabetical output | `multiple_packages_alphabetical`, `resolve_simple_caret` | covered | `test_outputs.py:17-20,65-68` |
| Transitive + diamond intersection | `dependency_resolution`, `diamond_dependency`, `transitive_chain_three_deep` | covered | `test_outputs.py:41-44,77-91,156-168` |
| Backtracking | `backtrack_to_lower_version`, `yank_forces_backtrack` | covered | `test_outputs.py:105-119,169-181` |
| CONFLICT pkg constraint on failure | `conflict_no_version` | covered | `test_outputs.py:45-48` |
| **CONFLICT which constraint when multiple fail** | `diamond_conflict` | **gap** | `instruction.md:5` vs `test_outputs.py:103` |
| LOCK / LOCK_ERROR | `lock_basic`, `lock_error_violates_constraint` | covered | `test_outputs.py:49-56` |
| UPGRADE / NO_UPGRADE | `upgrade_to_highest`, `upgrade_no_change` | partial | `NO_UPGRADE` format gap — `test_outputs.py:63` |
| UNLOCK / UNLOCK_ERROR | `unlock_basic`, `unlock_error_not_locked` | covered | `test_outputs.py:120-134` |
| REMOVE clears req + lock | `remove_package`, `remove_clears_lock` | covered | `test_outputs.py:135-155` |
| Binary at `/app/solver` | all fixtures | covered | `test_outputs.py:9`, `instruction.md:1` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers #1 #3, #7, #27, #55, spec table |
| `task.toml` | Blocker #2, #44, #45, milestone N/A |
| `tests/test_outputs.py` | Blockers #1 #3, #27, all fixtures |
| `solution/solve.sh` | Blocker #1 oracle tie-break, #23 |
| `environment/Dockerfile` | #15 canonical base, #20 |
| `tests/test.sh` | #24-26 |
| `entire-report.txt` | Agent stats, adjudication, rubric #32-39 |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |
| `docs/guidelines/rubrics.md` | Non-milestone rubric format |
| `docs/task-type-taxonomy.md` | Category blocker |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-cli-version-solver/ ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Within hard band |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Hard |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

**Per-fixture signal:** `diamond_conflict` 1/10; `upgrade_no_change` 8/10; all others ≥9/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; report matches folder |
| 1 Instruction | ☑ | Tie-break + NO_UPGRADE gaps found |
| 2 Environment | ☑ | Canonical golang digest; tmux/asciinema; offline |
| 3 Oracle | ☑ | Real Go resolver; platform 100% |
| 4 Verifiers | ☑ | Canonical reward block; 25 fixtures |
| 5 Metadata | ☑ | Category wrong (Medium) |
| 6 Rubric | ☑ | Flat non-milestone format OK; #36 phrasing fail |
| 7 Agent evidence | ☑ | diamond_conflict dominates failures |
| 8 Novelty & fairness | ☑ | Fair algorithmically except CONFLICT ordering |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid resolver task — the backtracking fixtures, semver coverage, and offline Go setup are all in great shape, and the difficulty calibration looks right for how hard this is. Before we can accept, please fix one spec gap: when multiple constraints on the same package conflict (the `diamond_conflict` case), the instructions need to say *which* constraint goes in the `CONFLICT` line — right now agents reasonably pick different ones and eight of ten runs failed only on that detail. Also switch `category` to `build-and-dependency-management`, and add that `NO_UPGRADE` is printed alone with no package name. Optional polish: rephrase rubric negatives to avoid “Agent fails to…” if you want #36 clean.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 3 |
| Instruction Styling | yes | 1, 3 |
| Metadata Issues | yes | 2 |
| Pinning Issues | no | — |
| Environment | no | — |
| Rubric | no (style only #36) | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Oracle Solution Issues | no | — |
| Other | no | — |
