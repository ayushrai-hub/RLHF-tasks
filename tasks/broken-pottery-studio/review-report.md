# Terminus Review Report: `broken-pottery-studio`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong 8-milestone Python debugging task with digest-pinned environment, correct milestone rubric layout (`# Rubric 1`–`# Rubric 8`), aligned per-milestone tests, and hard-tier agent calibration (GPT-5.5 20%). One High blocker: Milestone 7 does not state that the 5-wheel then 4-wheel bookings must both succeed and only the next booking is rejected — agents systematically pre-reject the second booking (6/10 on `test_cumulative_tickets_exceed_limit`). Category `data-processing` → `debugging` is a valid Medium metadata fix, not a standalone blocker.

**Insights (concise):**

- Automated script false positives on #1 (aggregates all milestone instructions), #31 (docstring regex misses `-> None:` annotations), #54 (uses max pass rate as “worst”), and #38 (no rubric metadata refs) — all rejected after file audit.
- Harbor export “CRITICAL: missing root `[verifier]`/`[agent]`” is wrong for milestone tasks (`docs/task-requirements.md` §Milestone: per-step timeouts, no top-level sections).
- Platform instruction-sufficiency analysis attributes M7 failures to agent over-engineering; artifacts still show a spec gap on *when* the limit fires (stored count vs projected total).
- Milestone 4 `test_active_hold_blocks_booking_before_expiry` already exists — prior reviewer note to add it is stale.
- Rubric format matches milestone rules (`number_of_milestones = 8`); not a non-milestone rubric misuse.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27 | Milestone 7 does not specify that limit enforcement uses the **stored** cumulative count before each booking (not a projected total for the requested wheels). `test_cumulative_tickets_exceed_limit` requires booking 5 then 4 wheels to both succeed and only the third booking to raise `ReservationError`; instruction describes the 5+4 scenario only as buggy behavior (“Both bookings succeed…”) without stating this remains true after the fix. | `steps/milestone_7/instruction.md:5-7`; `steps/milestone_7/tests/test_m7.py:94-100`; `environment/reservation_system.py:62-63,91` (check before `record_tickets`); `entire-report.txt:82` (6/10 on cumulative test); agent failure analysis `entire-report.txt:127-135` | Add explicit wording, e.g. that after fixing accumulation, a student may complete separate bookings whose combined wheels exceed 8; reject only when `has_reached_ticket_limit` is true **before** starting a new booking (no pre-check of `current + len(wheels)`). |

*No other High blockers.*

**Non-blocking recommended fix (Medium):** Change `task.toml` `category = "data-processing"` to `category = "debugging"` (`task.toml:5`; tags already include `debugging`).

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Milestone 7 needs clearer booking-limit wording; 5+4 must succeed, next blocked (ChatGPT High) | **Agree** | `test_m7.py:94-100`; `instruction.md:5-7` describes bug narrative without post-fix booking semantics; 6/10 pass rate `entire-report.txt:82` |
| 2 | `category` should be `debugging` not `data-processing` (ChatGPT Medium) | **Agree** | `task.toml:5-7`; all 8 milestones are bug-fix debugging; Harbor export `entire-report.txt:278-296` |
| 3 | Rubric `# Rubric 1`–`# Rubric 8` format OK for milestone task (ChatGPT) | **Agree** | `task.toml:12`; `entire-report.txt:836-888`; `docs/guidelines/rubrics.md:53-64` |
| 4 | Milestone 4 active-hold test not needed as blocker (ChatGPT) | **Agree** | `test_m4.py:70-77` `test_active_hold_blocks_booking_before_expiry` |
| 5 | Dockerfile digest-pinned canonical Python base (ChatGPT) | **Agree** | `environment/Dockerfile:1` |
| 6 | Instruction sufficiency PASS — agent over-engineering, not spec gap (export analysis) | **Partially agree** | Failures are agent hacks (`entire-report.txt:135`), but unstated limit-timing semantics still drive systematic misreads; instruction gap remains |
| 7 | CRITICAL: missing root `[verifier]`/`[agent]` in task.toml (Harbor REVIEW REPORT) | **Disagree** | `task.toml:27-81` per-step timeouts; `docs/task-requirements.md:107` milestone tasks omit top-level agent/verifier; `validate` 0 errors |
| 8 | #1 instruction too long (907 words combined) (automated review) | **Disagree** | Milestone layout: per-file word counts 79–205 (`milestone_7` highest); `docs/guidelines/prompt-styling.md:49-52` per-milestone instructions |
| 9 | #31 76 tests missing docstrings (automated review) | **Disagree** | Tests have docstrings, e.g. `test_m1.py:37-40`, `test_m7.py:61,95`; validator regex `validate_task.py:558` requires `):` not `) -> None:` |
| 10 | #54 too easy — 100% worst model (automated review) | **Disagree** | `docs/reviewer-checklist-ui.md:66-71`: worst model = lowest pass rate = GPT-5.5 **20%** (`entire-report.txt:27`), not Claude 100% |
| 11 | #38 rubric references instruction.md (automated review) | **Disagree** | `entire-report.txt:836-888` — no `instruction.md` or `task.toml` strings |
| 12 | Strengthen Milestone 4 active-hold tests (Reviewer Feedback) | **Disagree** | `test_m4.py:70-77` already covers active hold blocking |
| 13 | Rubric wrongly uses milestone headers on non-milestone task (user ask) | **Disagree** | `number_of_milestones = 8`; milestone rubric headers are required |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Per-milestone instructions 79–205 words each; not one combined prompt | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer bug-report style, no synthetic opener | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | No ##/tables in instructions | — |
| 4 | CHECK | No step-by-step HOW | Describes bugs/outcomes, not sed commands | — |
| 5 | CHECK | No hints/solving strategies | No walkthrough fixes | — |
| 6 | CHECK | No design-doc tables | None | — |
| 7 | UNCHECK | Well specified | M7 limit-timing semantics ambiguous | `milestone_7/instruction.md:5-7` |
| 8 | CHECK | Interesting | Realistic reservation-system debugging | — |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No “broken-pottery-studio” string | — |
| 12 | CHECK | No canary string | None | — |
| 13 | CHECK | No web content fetch | No runtime fetch in env | — |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, etc. | `environment/Dockerfile:4` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only env modules | `environment/Dockerfile:8` |
| 17 | CHECK | No ground-truth answers | Intentionally buggy code, no solution leak | `environment/student.py:28-34` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:4`, `milestone_1/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed locally | harbor CLI error |
| 22 | CHECK | Oracle no internet | solve scripts use sed only | `solve7.sh` |
| 23 | CHECK | Oracle reflective | Targeted sed patches, not echo answers | `solve7.sh:4-14` |
| 24 | CHECK | reward.txt canonical block | mkdir + 0 default + pytest + 0/1 | `milestone_1/tests/test.sh:4-17` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | milestone test files |
| 26 | CHECK | Binary rewards | 0/1 only | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M7 cumulative limit timing unstated | `test_m7.py:94-100` vs `instruction.md` |
| 28 | CHECK | Tests check correctness | Behavioral assertions on booking/refund state | milestone test files |
| 29 | CHECK | Behavior not implementation grep | Imports modules, exercises API | `test_m7.py` |
| 30 | CHECK | No brittle string matching | Numeric/tolerance asserts | `test_m1.py`, `test_m7.py` |
| 31 | CHECK | Informative test names/docstrings | Descriptive names + docstrings on tests | `test_m7.py:61,95`; `test_m4.py:70-71` |
| 32 | CHECK | ≥3 negative rubric criteria | 16 negatives across 8 blocks | `entire-report.txt:836-888` |
| 33 | CHECK | Valid rubric scores | ±1,2,3,5 only | rubric section |
| 34 | CHECK | Agent …, ±N format | 38 Agent lines | rubric section |
| 35 | CHECK | Rubric detailed/precise | Task-specific per-milestone fixes | rubric section |
| 36 | CHECK | Positive rubric language | “Agent fixes…” phrasing | rubric section |
| 37 | CHECK | No /tests/ references | None in rubric | rubric section |
| 38 | CHECK | No task.toml/instruction.md refs | None in rubric | rubric section |
| 39 | CHECK | No oracle/NOP mentions | None | rubric section |
| 40 | CHECK | Required files present | Milestone layout: Dockerfile + task.toml + steps/ | `task.toml`, `environment/` |
| 41 | CHECK | No stray parent files | Clean task root | — |
| 42 | CHECK | author_name/email | Present | `task.toml:8-9` |
| 43 | CHECK | Other metadata fields | version, difficulty, milestones, timeouts in steps | `task.toml` |
| 44 | UNCHECK | Tags/languages/category applicable | `category = "data-processing"` mismatches debugging content | `task.toml:5-7` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: best-model GPT 20% ≤20% | `entire-report.txt:26-27`; `difficulty.md` |
| 46 | CHECK | steps/ milestone layout | 8 milestones under `steps/` | `task.toml:12,27-81` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve8.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m8.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | Each test_mN imports only relevant modules | spot-check all 8 files |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | No solution/ COPY | `environment/Dockerfile:8` |
| 52 | CHECK | Agent cannot trivially cheat | Tests not visible at runtime | `allow_internet=false` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model pass rate 20% (GPT-5.5), not >80% | `entire-report.txt:27` |
| 55 | CHECK | Not unfair | M7 failures are implementer misreads; env deterministic | `entire-report.txt:107-154` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 7, 9, 21, 27, 44 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| M1: 15% group + 10% loyalty + 8% fee on post-discount total | `test_standard_student_group_session_invoice_total`, `test_returning_student_group_session_invoice_total` | covered | `milestone_1/` |
| M2: senior 10% after group; peak = weekend AND evening | `test_weekend_evening_is_peak`, `test_senior_discount_applied_after_group` | covered | `milestone_2/tests/test_m2.py` |
| M3: audit/event store isolation | `test_audit_entry_not_modified_by_caller_mutation`, `test_event_log_read_returns_snapshot_not_live_reference` | covered | `milestone_3/tests/test_m3.py` |
| M4: expired holds release; cache serves stored None | `test_wheel_released_when_hold_period_expires`, `test_null_result_stored_and_served_without_re_fetching`, `test_active_hold_blocks_booking_before_expiry` | covered | `milestone_4/tests/test_m4.py` |
| M5: tier waitlist + 1-based position + cancel guard | `test_premium_tier_student_promoted_before_standard_tier`, `test_cancelling_unconfirmed_booking_raises_error` | covered | `milestone_5/tests/test_m5.py` |
| M6: lock debounce clear + blocked wheel exclusion | `test_release_allows_waiting_student_to_acquire`, `test_blocked_wheel_excluded_from_section_availability` | covered | `milestone_6/tests/test_m6.py` |
| M7: coverage flag, proration, accumulate tickets, inclusive `>=` | refund tests + limit tests | **gap** | cumulative timing unstated: `instruction.md:5-7` vs `test_cumulative_tickets_exceed_limit` |
| M8: backoff, CB timer reset, token cap, ceiling pages | gateway + pagination tests | covered | `milestone_8/tests/test_m8.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #44, #45, #46, milestone metadata |
| `environment/Dockerfile` | #15, #20, #50 |
| `environment/reservation_system.py` | M7 limit check order |
| `environment/student.py` | M7 buggy baseline |
| `steps/milestone_7/instruction.md` | Blocker 1, #7, #27 |
| `steps/milestone_7/tests/test_m7.py` | Blocker 1, #27 |
| `steps/milestone_7/solution/solve7.sh` | #23 oracle approach |
| `steps/milestone_4/tests/test_m4.py` | Adjudication claim 4, 12 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, prior feedback |
| `docs/guidelines/rubrics.md` | Rubric format (#32–39) |
| `docs/task-requirements.md` | Milestone task.toml schema |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate broken-pottery-studio/
Summary: 0 error(s), 85 warning(s), 1 info
Task type detected: milestone
```

Warnings are non-blocking (docstring regex false positives, `TestMilestoneN` class naming, 8 milestones > recommended 5).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20% (1/5) | Supports `hard` tier |
| terminus-claude-opus-4-8 | 100% (5/5) | Best model |
| oracle | 100% (3/3) | per export |
| nop | 0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% (GPT-5.5) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

M7 failure cluster: all agent trials failed M7; `test_cumulative_tickets_exceed_limit` at 6/10 (`entire-report.txt:82`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Report matches pottery-studio milestone task |
| 1 Instruction | ☑ | M7 limit wording gap |
| 2 Environment | ☑ | tmux + digest pin OK |
| 3 Oracle | ☐ | Not executed (harbor config error) |
| 4 Verifiers | ☑ | reward.sh pattern OK; docstrings present |
| 5 Metadata | ☑ | Category mismatch Medium only |
| 6 Rubric | ☑ | Milestone `# Rubric 1`–`8` correct |
| 7 LLMaJ & agent evidence | ☑ | Parsed entire-report.txt |
| 8 Novelty & fairness | ☑ | No cheat paths found |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone debugging task — the step structure, digest-pinned Python image, per-milestone tests, and `# Rubric 1` through `# Rubric 8` rubric blocks all look great, and the difficulty calibration on GPT-5.5 is in a good place. One fix before accept: in Milestone 7, please clarify the booking-limit behavior so agents know the 5-wheel and 4-wheel bookings should both succeed and only the *next* booking is blocked after accumulation is fixed (the limit check uses the stored count before each booking, not a projected total for the requested wheels). Also worth switching `category` from `data-processing` to `debugging` in `task.toml` since that better matches the task.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Metadata Issues | no (Medium only) | — |
| Rubric | no | — |
| Milestones | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |
