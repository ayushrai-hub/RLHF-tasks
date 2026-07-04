# Terminus Review Report: kotlin-terraform-aurora-triage

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (3 errors: missing solveN.sh) |
| **Oracle** | pass (platform: 100% 3/3; local not run) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Milestones

**Decision (concise):** Two real High blockers: (1) Milestone 3 requires `flagged` in each result JSON but never defines when it is true/false while tests enforce `flagged=true` for any non-`archive` action; (2) each milestone is missing the required `solveN.sh` oracle script (only `solve.sh` wrappers exist). ChatGPT’s `task.toml` root-timeout claim is wrong for milestone tasks. Rubric uses correct milestone `# Rubric N` format with per-block caps ≤15. All other Harbor/automation flags (#1 combined length, #14, #20, #31) are false positives on manual audit.

**Insights (concise):**

- Strong anti-cheat design: mutation tests (M1/M3), path-relocation tests (M2/M3), independent PNG/softmax reference in M3.
- Agent stats: GPT-5.5 100% (5/5), Claude Opus 4.8 60% (3/5); worst model 60% → medium tier; not too easy (#54 passes).
- Platform LLMaJ `behavior_in_task_description` PASS is contradicted for `flagged` semantics — artifacts win.
- Rubric: 3 milestone blocks (13+13+15 pts); each block ≤40; ≥3 negatives total — format correct for `number_of_milestones = 3`.
- M3 rule-priority ambiguity (weak-quarantine vs strong-escalate) is Medium/Low clarity only — not a revision blocker.
- M1 oracle fallback defaults (`0.85`, `-25.0`, etc.) are Low polish — mutation test still validates dynamic extraction.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | M3 lists `flagged` as a required boolean but never defines when it must be true; verifier enforces `flagged=true` for `quarantine` and `escalate`, `false` for `archive` | `steps/milestone_3/instruction.md:5` lists `flagged` with no semantics; `steps/milestone_3/tests/test_m3.py:194-214` sets `expected_flagged = True` for quarantine/escalate; `entire-report.txt:76-78` agent AKLMcft failed on this | Add explicit rule to M3 instruction, e.g. “`flagged` must be `true` whenever `action` is not `archive`; otherwise `false`.” |
| 2 | High | Milestones | #46, #47 | Missing `solve1.sh`, `solve2.sh`, `solve3.sh`; only `solve.sh` wrappers that inline oracle logic | `docs/guidelines/milestones.md:49-57,99`; `docs/reviewer-checklist-full.md:109`; validate errors on `steps/milestone_*/solution/solveN.sh` | Add `solveN.sh` per milestone with scoped oracle commands; make `solve.sh` a thin wrapper calling `solveN.sh` |

*No other High-severity blockers found on manual audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M3 `flagged` semantics undefined (ChatGPT High; `entire-report.txt:76-78`) | **Agree** | See blocker #1 |
| 2 | `task.toml` missing top-level `[verifier]` and `[agent]` (ChatGPT Medium; Harbor `entire-report.txt:159-181`) | **Disagree** | `docs/guidelines/milestones.md:99`: “**No** top-level `[agent]` or `[verifier]` — use per-milestone `[steps.agent]` / `[steps.verifier]`”; `task.toml:27-49` has per-step timeouts — correct for milestone layout |
| 3 | Optional M3 priority between weak-quarantine and strong-escalate (ChatGPT Medium) | **Partially agree** (not a blocker) | `steps/milestone_3/instruction.md:3` lists weak then strong; `test_m3.py:200-205` checks strong (`probabilities[2]`) before weak; `entire-report.txt:449-482` notes edge case may not arise in fixtures — Medium/Low clarity only |
| 4 | Remove hardcoded M1 oracle fallbacks (ChatGPT Low; Harbor `entire-report.txt:188-209`) | **Agree** (Low only) | `steps/milestone_1/solution/ProtocolExtractor.kt:20-48` initializes defaults then regex-overwrites; mutation test passes — not a revision blocker |
| 5 | LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:102`) | **Disagree** for `flagged` | Same as blocker #1 — field listed but boolean semantics untested in spec |
| 6 | LLMaJ `pinned_dependencies` PASS (`entire-report.txt:107`) | **Agree** | `environment/verifier-requirements.lock:27-36` pins `pytest==8.4.1` with hashes; Dockerfile uses `--require-hashes` |
| 7 | Harbor: non-canonical base image (`entire-report.txt:138-156`) | **Disagree** as blocker | `environment/Dockerfile:1` digest-pinned `eclipse-temurin:21-jdk-jammy`; JVM required for Kotlin — acceptable per `docs/reviewer-checklist-full.md:44` |
| 8 | Automated review: instruction too long #1 | **Disagree** | Script combines all 3 milestone files (~523 words); each file alone is 1–2 short paragraphs (`steps/milestone_1/instruction.md` ~120 words, M2 ~100, M3 ~130) — concise per milestone |
| 9 | Automated review: #14 unpinned pip | **Disagree** | Lock file has `==` + hashes; not a blocker |
| 10 | Automated review: #20 pytest not in Dockerfile | **Disagree** | `environment/Dockerfile:28-31` installs `/opt/verifier-venv` from lock; `test.sh` uses `/opt/verifier-venv/bin/python -m pytest` |
| 11 | Automated review: #31 missing docstrings | **Disagree** | All `test_mN.py` methods have docstrings; validator regex fails on `def test_x(self) -> None:` signature |
| 12 | Rubric positive total 41 > 40 | **Disagree** as blocker | Milestone task: per-block caps `{1:13, 2:13, 3:15}` all ≤40; `./scripts/terminus rubric-points entire-report.txt --milestones 3` → PASS |
| 13 | Non-milestone task in milestone rubric format | **Disagree** (N/A — task IS milestone) | `task.toml:10` `number_of_milestones = 3`; `entire-report.txt:488-517` uses `# Rubric 1/2/3` — **correct** format per `docs/guidelines/rubrics.md:55-66` |
| 14 | Task too easy (>80% worst model) | **Disagree** | `entire-report.txt:17-19` worst model Claude 60% |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction is 1–2 paragraphs; combined count is N/A for milestone layout | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineer voice; no synthetic patterns | `steps/milestone_1/instruction.md:1` |
| 3 | CHECK | No excessive markdown | No ##/tables | — |
| 4 | CHECK | No step-by-step HOW | Requirements only | — |
| 5 | CHECK | No hints/solving strategies | Describes outputs and rules, not implementation steps | — |
| 6 | CHECK | No design-doc tables | None | — |
| 7 | UNCHECK | Well specified | `flagged` boolean semantics missing | blocker #1 |
| 8 | CHECK | Interesting | Multi-step ML + triage pipeline | — |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | All paths absolute | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name not in instruction | Clean | — |
| 12 | CHECK | No canary string | Clean | — |
| 13 | CHECK | No runtime web fetch in env | Data shipped locally | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip dependencies | Lock file with `==` and hashes | `environment/verifier-requirements.lock` |
| 15 | CHECK | Docker FROM digest-pinned | `@sha256:25d127…` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context in environment/ only | COPY limited to lock + task data | `environment/Dockerfile:36-39` |
| 17 | CHECK | No ground truth in env | Docs are noisy by design; no literal JSON answers | `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest via `/opt/verifier-venv` | `environment/Dockerfile:28-31` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally; platform 100% | `entire-report.txt:23` |
| 22 | CHECK | Oracle no internet | solve.sh copies/compiles/runs Kotlin only | `steps/milestone_*/solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Kotlin derives outputs; platform oracle 100% | `steps/milestone_1/solution/ProtocolExtractor.kt`; `entire-report.txt:110` |
| 24 | CHECK | reward.txt canonical | All milestone test.sh write reward | `steps/milestone_1/tests/test.sh:14-17` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Binary rewards | 0/1 only | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | `flagged` tested but undefined | blocker #1; `test_m3.py:211-214` |
| 28 | CHECK | Tests check correctness | Independent PNG parser + softmax in M3 | `test_m3.py:34-118,186-190` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `test_m*.py` |
| 30 | CHECK | No brittle exact strings | Numeric tolerances, rule logic | `test_m3.py:188-190` |
| 31 | CHECK | Informative docstrings | Class + method docstrings present | `test_m1.py:11-18` |
| 32 | CHECK | ≥3 negative rubric criteria | 8 negatives across 3 blocks | `entire-report.txt:494-517` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All lines valid | `entire-report.txt:488-517` |
| 34 | CHECK | Agent …, ±N format | 25 Agent lines | `entire-report.txt:488-517` |
| 35 | CHECK | Rubric detailed; per-block ≤40 | Blocks 13/13/15 pts | `rubric-points --milestones 3` |
| 36 | CHECK | Positive phrasing | Bad behavior scored negative | `entire-report.txt:494-517` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:488-517` |
| 38 | CHECK | Rubric no task.toml/instruction refs | Clean | `entire-report.txt:488-517` |
| 39 | CHECK | Rubric no oracle/NOP | Clean | `entire-report.txt:488-517` |
| 40 | CHECK | Required files present | Milestone layout + Dockerfile + task.toml | `steps/`, `environment/Dockerfile` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, difficulty, milestones, tags | `task.toml` |
| 44 | CHECK | Tags/languages/category match | kotlin/terraform/ML triage | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `medium`; worst model 60% informational | `task.toml:8`; `entire-report.txt:13-19` |
| 46 | UNCHECK | steps/ milestone layout | Missing solveN.sh files | blocker #2 |
| 47 | UNCHECK | solveN.sh per milestone | solve1/2/3.sh absent | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/m2/m3.py exist | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone tests scoped | Each TestMilestoneN tests only its step | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests/ | `environment/.dockerignore:16-17` |
| 51 | CHECK | No accessible ground truth | solution/ and tests/ excluded from image | `environment/.dockerignore` |
| 52 | CHECK | Agent can't trivially cheat | Mutation + relocation tests | `test_m1.py:45-100`, `test_m3.py:228-342` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 60% ≤80% | `entire-report.txt:17-19` |
| 55 | UNCHECK | Not too hard/unfair | Undocumented `flagged` semantics caused systematic M3 failure | `entire-report.txt:51-52,76-78` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 46, 47, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| M1: four JSON fields from archive | `test_milestone_1_base_execution`, `test_milestone_1_mutated_execution` | covered | `test_m1.py:40-43,91-94` |
| M1: approved rule disambiguation (Feb 18, strictly below) | `test_milestone_1_mutated_execution` | covered | `test_m1.py:59-73` |
| M2: classifier.bin 3-line format, 50 epochs, acc>0.95, loss<0.2 | `test_milestone_2_execution` | covered | `test_m2.py:167-176` |
| M2: dataset path from terraform outputs | `test_milestone_2_reads_dataset_path_from_outputs` | covered | `test_m2.py:178-216` |
| M3: five result fields including `flagged` | `test_milestone_3_execution` | **gap** | Field required `instruction.md:5`; semantics only in test `test_m3.py:194-214` |
| M3: rule priority (untrusted > strong > weak > archive) | `test_milestone_3_execution` | covered | `test_m3.py:196-205`; oracle `TriageWorker.kt:118-128` |
| M3: run_summary counts | `test_milestone_3_execution` | covered | `test_m3.py:219-226` |
| M3: stale prediction cleanup + relocated paths | `test_milestone_3_relocated_paths_and_fresh_snapshot` | covered | `test_m3.py:294-342` |
| M3: dynamic thresholds (mutation) | `test_milestone_3_mutated_execution` | covered | `test_m3.py:228-292` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_3/instruction.md` | blocker #1, #27, #55 |
| `steps/milestone_3/tests/test_m3.py` | blocker #1, spec alignment |
| `steps/milestone_*/solution/solve.sh` | blocker #2, #46, #47 |
| `task.toml` | #45, milestone metadata, rubric format check |
| `docs/guidelines/milestones.md` | adjudication #2 (no root timeouts) |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/verifier-requirements.lock` | #14 |
| `entire-report.txt` | agent stats, rubric #32-39, external claims |
| `steps/milestone_1/solution/ProtocolExtractor.kt` | oracle adjudication (Low) |

---

## 7. Validation & agent performance

### Validation

```
ERROR: milestone [steps/milestone_1/solution/solve1.sh]: Missing solve1.sh
ERROR: milestone [steps/milestone_2/solution/solve2.sh]: Missing solve2.sh
ERROR: milestone [steps/milestone_3/solution/solve3.sh]: Missing solve3.sh
WARNING: informative_test_docstrings (false positive — docstrings exist)
WARNING: pinned_dependencies (false positive — lock file has hashes)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60% (3/5) | Worst model |
| oracle | 100% (3/3) | Platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes (informational) |

Per-test: M3 execution 9/10 runs — single failure tied to `flagged` semantics (`entire-report.txt:37-38,51-52`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone task, 3 steps, ML category |
| 1 Instruction | ☑ | `flagged` gap confirmed; per-milestone instructions concise |
| 2 Environment | ☑ | Digest-pinned JVM base  tmux/asciinema, verifier venv |
| 3 Oracle | ☑ | Kotlin logic; missing solveN.sh structure |
| 4 Verifiers | ☑ | Strong mutation/relocation; docstrings present |
| 5 Metadata | ☑ | Per-step timeouts correct; no root [agent]/[verifier] needed |
| 6 Rubric | ☑ | Milestone `# Rubric 1-3` format correct; per-block ≤40 |
| 7 LLMaJ & agent evidence | ☑ | Flagged spec defect confirmed; metadata timeout claim rejected |
| 8 Novelty & fairness | ☑ | Multi-step, closed cheat paths; flagged unfairness only |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this pipeline — the three-milestone flow, mutation tests, and independent M3 verifier logic are all strong. Two things to fix before accept: in Milestone 3, please define when `flagged` should be true (tests expect `true` for any non-`archive` action, `false` for `archive`); and add the required `solve1.sh` / `solve2.sh` / `solve3.sh` files with `solve.sh` as thin wrappers per the milestone oracle layout. Optional polish: clarify that strong-aurora escalation wins over weak-aurora quarantine when both could apply, and drop the hardcoded fallback defaults in the M1 oracle.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Milestones | yes | 2 |
| Metadata Issues | no | — |
| Rubric | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
