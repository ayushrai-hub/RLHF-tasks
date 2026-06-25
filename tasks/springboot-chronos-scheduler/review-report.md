# Terminus Review Report: `springboot-chronos-scheduler`

**Generated:** 2026-06-18  
**Disposition:** Accept  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/springboot-chronos-scheduler`

---

## 1. Executive summary

- **Recommendation:** Accept
- **Automated validation:** FAIL (5 errors, 5 warnings) — manual re-audit shows 3 validator errors are false positives; 2 are Low-severity metadata/style fixes
- **Checkboxes to CHECK:** 47 items → `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55`
- **Checkboxes to UNCHECK:** 8 items → `32, 33, 34, 35, 36, 37, 38, 39` (rubrics N/A — no `rubric.txt` in task folder; rubric content in external report is portal-only)

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

---

## 2. Main blockers (detailed)

**No High-severity blockers after manual re-audit.**

### Low — task.toml redundant top-level timeouts (non-blocking)

- **Severity:** Low
- **Section:** TASK METADATA / MILESTONE TASKS
- **What failed:** `task.toml` lines 16–20 define top-level `[verifier]` and `[agent]` blocks; milestone tasks must use only per-step `[steps.agent]` / `[steps.verifier]` per `docs/guidelines/milestones.md:99`
- **Proof files:** `task.toml:16-20`, `task.toml:33-55`
- **Required fix:** Delete lines 16–20 (per-milestone timeouts already present). Does not affect oracle or agent runs.

### Low — milestone test class naming convention

- **Severity:** Low
- **Section:** MILESTONE TASKS
- **What failed:** `test_m1.py` / `test_m2.py` / `test_m3.py` use module-level `test_*` functions instead of `class TestMilestoneN`
- **Proof files:** `steps/milestone_1/tests/test_m1.py:1`, `docs/guidelines/milestones.md:21`
- **Required fix:** Optional style alignment; tests function correctly.

### Info — validator false positives (not blockers)

| Validator error | Manual verdict | Evidence |
|-----------------|----------------|----------|
| `curl` in test.sh | **Disagree** — health-check only, not package install | `steps/milestone_1/tests/test.sh:37` uses `curl -fsS http://localhost:8080/health`; no `pip`/`apt` in test.sh |
| Unpinned pip | **Disagree** — packages pinned on continuation lines | `environment/Dockerfile:37-39` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `requests==2.32.3` |
| Instruction too long (#1) | **Disagree** — must evaluate per milestone | M1: 2 paragraphs; M2: 3 paragraphs; M3: 2 paragraphs — each within 3-paragraph limit |

---

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise | Each milestone instruction is 2–3 paragraphs; combined-length check is inappropriate for milestone layout | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md`, `steps/milestone_3/instruction.md` |
| 2 | Natural prompt tone | Reads as infra-engineer narrative, not spec boilerplate | `steps/milestone_1/instruction.md:1-3` |
| 3 | No excessive markdown | Plain prose, no ##/tables | all milestone instructions |
| 4 | No step-by-step solve script | Requirements describe outcomes, not a command sequence | all milestone instructions |
| 5 | No hints (WHAT not HOW) | API shapes and semantics specified; no solve walkthrough | `steps/milestone_2/instruction.md` |
| 6 | No design-doc tables | No I/O mapping tables | all milestone instructions |
| 7 | Well specified | Clear goals, absolute paths, measurable API contracts | `steps/milestone_2/instruction.md:9-10` |
| 8 | Interesting | Realistic multi-milestone scheduler engineering task | task scope |
| 9 | Unique | Hand-rolled Quartz-dialect parser + JDBC scheduler + failover — not a common TB2 duplicate | task content |
| 10 | Absolute paths only | `/app/...` throughout | `steps/milestone_1/instruction.md:5` |
| 11 | Task name not in instruction | No "springboot-chronos-scheduler" string | all milestone instructions |
| 12 | No canary string | None found | all milestone instructions |
| 13 | No web fetch in environment | No runtime URL fetches in env source | `environment/` |
| 14 | Pinned pip dependencies | `pytest==8.4.1`, `requests==2.32.3`, etc. | `environment/Dockerfile:37-39` |
| 15 | Digest-pinned FROM | Both stages use `@sha256:` | `environment/Dockerfile:4,15` |
| 16 | Context stays in environment/ | COPY only from `app/` within build context | `environment/Dockerfile:44-54` |
| 17 | No ground truth in environment | Stubs throw `UnsupportedOperationException` only | `environment/app/src/main/java/com/snorkel/chronos/cron/QuartzCronExpression.java:27` |
| 18 | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | Compose does not alter Harbor mounts | No docker-compose.yaml | task root |
| 20 | Verifier deps baked; test.sh does not install packages | pytest venv in image; test.sh only curls localhost health | `environment/Dockerfile:35-39`, `steps/milestone_1/tests/test.sh` |
| 21 | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | Oracle no runtime network installs | solve scripts write Java source + `mvn package` only | `steps/milestone_2/solution/solve2.sh:14-80` |
| 23 | Oracle derives answer | Full Java implementations written, not echoed output | `steps/milestone_2/solution/solve2.sh` |
| 24 | test.sh reward.txt pattern | mkdir, reward 0/1 on pass/fail | `steps/milestone_1/tests/test.sh:6,47-59` |
| 25 | Same verifier logic for oracle/agent | No `/oracle` branching | all `test.sh` files |
| 26 | Binary rewards only | 0 or 1 in reward.txt | all `test.sh` files |
| 27 | Tests aligned with instructions | All major behaviors traced instruction ↔ test (see § Spec alignment) | test files + instructions |
| 28 | Tests check correctness | HTTP integration asserts DB/API outcomes, not format-only | `steps/milestone_2/tests/test_m2.py` |
| 29 | Behavior tests not implementation grep | Classpath scan for `org.quartz` is an explicit instruction constraint | `steps/milestone_1/tests/test_m1.py`, M1 instruction line 1 |
| 30 | No brittle string matching | Literal strings (`job_not_found`, `concurrent_execution_disallowed`) are instruction-specified | `steps/milestone_2/instruction.md:9`, `steps/milestone_3/instruction.md:3` |
| 31 | Informative test docstrings | Every `test_*` has a docstring | `steps/milestone_1/tests/test_m1.py:21+` |
| 40 | Required files present | `environment/Dockerfile`, per-milestone `instruction.md`, `test.sh`, `solveN.sh` | `steps/milestone_*/` |
| 41 | Clean parent directory | No stray jobs/README/dev-notes | task root |
| 42 | author_name / author_email | Present | `task.toml:4-5` |
| 43 | Required metadata fields | version, category, difficulty, milestones, timeouts, resources all present | `task.toml` |
| 44 | Tags/languages/category match | Java Spring Boot scheduler with API + DB interaction | `task.toml:7-12` |
| 45 | Difficulty matches pass rates | Declared `hard`; **worst-model** GPT-5.5 = 0% (≤20% = hard) | `task.toml:6`, `entire-report.txt:6-7` |
| 46 | steps/ milestone layout | 3 milestones under `steps/milestone_N/` | task structure |
| 47 | solveN.sh per milestone | solve1.sh, solve2.sh, solve3.sh present | `steps/milestone_*/solution/` |
| 48 | test_mN.py per milestone | test_m1.py, test_m2.py, test_m3.py present | `steps/milestone_*/tests/` |
| 49 | Milestone scope correct | Each test file covers only its milestone APIs | test file contents |
| 50 | Tests not in Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | Solution not accessible | Only `steps/` has solution; not in image | `environment/Dockerfile` |
| 52 | Agent cannot trivially cheat | UUID job names, real concurrency/race tests | `steps/milestone_3/tests/test_m3.py:34-48` |
| 53 | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | Not too easy | Worst-model 0% — well below 80% rejection threshold | `entire-report.txt:6-7` |
| 55 | Not unfair | H2 generated-key trap is hard but debuggable (1/6 agents passed M2); schema provided | `entire-report.txt:88`, `schema.sql:11` |

### UNCHECK these (fail, unverified, or N/A)

| # | Status | Label | Reason |
|---|--------|-------|--------|
| 32 | N/A | Rubrics ≥3 negatives | No `rubric.txt` in task folder (rubric entered via portal UI per external report lines 584–642) |
| 33 | N/A | Rubric scores ∈ {±1,2,3,5} | No rubric file in repo |
| 34 | N/A | Rubric format `Agent …, ±N` | No rubric file in repo |
| 35 | N/A | Rubric criteria detailed | No rubric file in repo |
| 36 | N/A | Rubric positive language | No rubric file in repo |
| 37 | N/A | Rubric no /tests/ refs | No rubric file in repo |
| 38 | N/A | Rubric no task.toml/instruction refs | No rubric file in repo |
| 39 | N/A | Rubric no oracle/NOP mentions | No rubric file in repo |

### Quick copy-paste

**CHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55

**UNCHECK:** 32, 33, 34, 35, 36, 37, 38, 39

---

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `task.toml` | #42, #43, #44, #45 |
| `environment/Dockerfile` | #14, #15, #16, #20, #50 |
| `steps/milestone_1/instruction.md` | #1, #7, #10 |
| `steps/milestone_2/instruction.md` | #7, #27 |
| `steps/milestone_3/instruction.md` | #7, #27 |
| `steps/milestone_1/tests/test.sh` | #20, #24 |
| `steps/milestone_1/tests/test_m1.py` | #27, #28, #31 |
| `steps/milestone_2/tests/test_m2.py` | #27, #28 |
| `steps/milestone_3/tests/test_m3.py` | #27, #28, #52 |
| `steps/milestone_2/solution/solve2.sh` | #22, #23 (uses `new String[]{"id"}` at line 68) |
| `environment/app/src/main/resources/schema.sql` | #17, #55 |
| `entire-report.txt` | #21, #45, #54 |

---

## 5. Validation output (re-audit)

```
ERROR: task.toml — Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml — Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
ERROR: test.sh (×3) — Runtime network install not allowed: curl
WARNING: Non-canonical final base image (eclipse-temurin — acceptable for Java 21 task)
WARNING: Unpinned pip (false positive — versions on next lines)
WARNING: test_mN.py should define class TestMilestoneN (style only)
```

**Manual verdict:** Only the redundant `task.toml` top-level `[agent]`/`[verifier]` is a real fix (Low). `curl` health checks and multi-line pip pins are compliant.

---

## 6. Agent performance (from report)

| Model | Pass rate |
|-------|-----------|
| terminus-claude-opus-4-8 | 80.0% (4/5) |
| terminus-gpt5-5 | 0.0% (0/5) |
| oracle | 100.0% (3/3) |
| nop | 0.0% (1/1) |

- **Worst-model rate:** 0% (GPT-5.5) → tier **hard** per `docs/guidelines/difficulty.md`
- **Report classified difficulty:** hard ✅
- **Note:** Automated `review_checklist.py` uses `max()` for worst-model (bug) — incorrectly flagged #45 using Claude's 80%. Correct worst-model is GPT-5.5 at 0%.

**Failure pattern:** 5/6 agents hit H2 `RETURN_GENERATED_KEYS` multi-column trap in `JobDao.insert()` (`created_at DEFAULT` in `schema.sql:11`). One agent (EyiVYTv) passed M2; M3 failure was a timing edge on `test_max_recovery_attempts_caps_at_three` (7/8 tests). This supports hard difficulty without being unfair.

---

## 7. Audit log

- [x] Phase 0 — Task identity: `springboot-chronos-scheduler`, 3-milestone Java/Spring Boot layout; report matches
- [x] Phase 1 — Instructions: per-milestone 2–3 paragraphs; absolute paths; no hints/leakage
- [x] Phase 2 — Environment: digest-pinned, tmux+asciinema, pytest baked, no tests/solution COPY
- [x] Phase 3 — Oracle: solveN.sh writes real Java; solve2 uses `new String[]{"id"}` for H2 keys
- [x] Phase 4 — Verifiers: reward.txt canonical; no runtime package installs; behavior HTTP tests
- [x] Phase 5 — Metadata: fields complete; remove redundant top-level agent/verifier (Low)
- [x] Phase 6 — Rubrics: present in portal report only (lines 584–642); not in task folder
- [x] Phase 7 — Agent evidence reconciled; JDBC trap adjudicated (see below)
- [x] Phase 8 — Novelty/fairness: multi-step, no cheating path; closed test image
- [x] Ran `terminus validate` (FAIL — see §5 adjudication)
- [x] Oracle not run locally (Harbor config unavailable); cited report oracle 100%

### Spec ↔ test alignment (selected)

| Requirement | Test(s) | Status |
|-------------|---------|--------|
| Quartz cron parse + DST | `test_next_dst_spring_forward_skipped_hour`, etc. | covered |
| Mutual `?` rule | `test_parse_mutual_exclusion_*` | covered |
| Misfire policies (3) | `test_misfire_*`, `test_resume_after_missed_fire_*` | covered (DO_NOTHING resume path gap = Low) |
| Atomic claim 20 concurrent | `test_20_concurrent_triggers_produce_20_unique_executions` | covered |
| `concurrent_execution_disallowed` literal | `test_concurrent_execution_disallowed_skips_second_run` | covered |
| Failover + max recovery 3 | `test_simulated_crash_*`, `test_max_recovery_attempts_caps_at_three` | covered |
| SlowJob `slow-done:<id>` | none | minor gap (Low — dispatch proven via LoggingJob) |

---

## External findings adjudication

### Claim: Accept — clean milestone layout, digest-pinned, strong coverage
- **Source:** ChatGPT findings
- **Verdict:** Agree
- **Evidence:** `steps/milestone_*/`, `environment/Dockerfile:4,15`, 41 integration tests across milestones
- **Severity:** —
- **Action:** none

### Claim: Hard difficulty supported by evaluation spread
- **Source:** ChatGPT + `entire-report.txt:1-7`
- **Verdict:** Agree (with correction)
- **Evidence:** Worst model GPT-5.5 0% supports `hard`; Claude 80% is best-model rate, not worst
- **Severity:** —
- **Action:** none

### Claim: JDBC key-retrieval issue is intended debugging work, not a spec blocker
- **Source:** ChatGPT + `entire-report.txt:82-101`
- **Verdict:** Partially agree
- **Evidence:** `schema.sql:11` (`created_at DEFAULT CURRENT_TIMESTAMP`) causes H2 multi-key return; instructions do not document `new String[]{"id"}` but rubric line 607 does; 1/6 agents passed M2
- **Severity:** Low
- **Action:** Optional spec note in M2 instruction; not blocking Accept

### Claim: Instruction sufficiency FAIL (LLMaJ)
- **Source:** `entire-report.txt:64`
- **Verdict:** Disagree as blocking
- **Evidence:** 5/6 trials marked `task_specification: pass`; cascade failure from one DAO bug, not systematic spec gap; M1 100% across all trials
- **Severity:** Low
- **Action:** none

### Claim: test.sh curl = runtime network install
- **Source:** `terminus validate` / automated review
- **Verdict:** Disagree
- **Evidence:** `steps/milestone_1/tests/test.sh:37` — localhost health poll only; `curl` installed in image at build time (`environment/Dockerfile:22`)
- **Severity:** —
- **Action:** none

### Claim: Combined instruction too long (#1)
- **Source:** automated review
- **Verdict:** Disagree
- **Evidence:** Milestone layout requires per-file evaluation; each file ≤3 paragraphs
- **Severity:** —
- **Action:** none

---

## 8. Reviewer note (copy-paste to portal)

Accepted. This is a well-structured 3-milestone Spring Boot task with digest-pinned images, verifier dependencies baked into the Dockerfile, and strong HTTP integration tests across cron parsing, persistence/misfires, and concurrency recovery. Oracle passes at 100% and worst-model pass rate (GPT-5.5 0%) supports the declared hard difficulty. Spec-test alignment is solid; minor gaps (SlowJob message, DO_NOTHING-on-resume) are Low severity. Remove redundant top-level `[agent]`/`[verifier]` blocks from `task.toml` before final submission — per-milestone timeouts are already defined.

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review springboot-chronos-scheduler/ --report entire-report.txt`._
