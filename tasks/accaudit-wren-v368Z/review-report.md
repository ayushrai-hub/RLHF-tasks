# Terminus Review Report: accaudit-wren-v368Z

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** Task Difficulty, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Needs revision. Dockerfile pinning, dependency hygiene, oracle design, and behavioral JSON coverage are strong. Three High blockers remain: `difficulty = "hard"` vs observed medium tier (Claude 60%), verifiers never enforce the mandated Wren/`wren_cli` path (Python or static JSON bypass), and the portal rubric is copied from an unrelated CHICKEN Scheme payroll task. Add a future-date fixture row (Medium) to close the `BAD_DATE` cutoff gap.

**Insights (concise):**

- Automated `./scripts/terminus review` falsely flagged #20 and #54; pytest is baked in `environment/Dockerfile:41` and worst-model pass rate is 60% (Claude), not 100%.
- ChatGPT overstated difficulty: GPT-5.5 at 100% is not the worst model; Claude at 60% sets the tier at medium (20–60% band).
- `tests/test_outputs.py` only loads `/app/audit_report.json`; no test asserts `/app/audit.wren` exists or re-runs `wren_cli`.
- `transactions.tsv` BAD_DATE rows use invalid months (13, 00), not valid-format dates after `2026-06-13`; `examples/ex_bad_date_future.tsv` is not the runtime input.
- Portal rubric lines 391–403 of `entire-report.txt` reference `/app/SCHEMA.md`, `csi`, and CHICKEN Scheme — wrong task entirely.
- Wren language quirks (no semicolons, no string `<`) caused agent timeouts but 60% still passed; fairness concern for #55, not a standalone blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | `task.toml` declares `difficulty = "hard"` but worst-model pass rate is 60% (medium tier) | `task.toml:6`; `entire-report.txt:1,6-7` | Set `difficulty = "medium"` or rebalance until worst model ≤20% |
| 2 | High | Test Alignment/Coverage Issues | #27 | Instruction requires Wren script + `wren_cli`; verifiers only check JSON output | `instruction.md:1`; `tests/test.sh:13`; `tests/test_outputs.py:6-15` (no `audit.wren` / `wren_cli` assertion) | Add tests that `/app/audit.wren` exists and `wren_cli /app/audit.wren` succeeds (re-run in verifier or assert file mtime) |
| 3 | High | Rubric | #32–#39 | Visible portal rubric is for CHICKEN Scheme payroll/CSV, not Wren transaction audit | `entire-report.txt:391-403` (no `rubric.txt` in task folder) | Replace rubric with Wren-audit criteria; ≥3 negatives; no `/tests/` refs |
| 4 | Medium | Test Alignment/Coverage Issues | #27 | Future-date cutoff (`no later than 2026-06-13`) untested in runtime fixture | `instruction.md:3`; `transactions.tsv:18,24` (months 13 and 00 only); `examples/ex_bad_date_future.tsv:1-2` not copied to image input | Add row with valid calendar date > `20260613` to `transactions.tsv` and assert `BAD_DATE` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` but evaluation is Medium; pass rates 60% and 100% (ChatGPT) | **Partially agree** | `task.toml:6` = `hard`; `entire-report.txt:6-7` Claude 60%, GPT 100%. Worst model = Claude **60%** → medium tier per `docs/guidelines/difficulty.md:10`. GPT 100% does not set worst-model tier. |
| 2 | Verifier does not enforce Wren path; pytest only loads JSON; no `audit.wren` / `wren_cli` check (ChatGPT) | **Agree** | `instruction.md:1` mandates `/app/audit.wren` + `wren_cli`; `tests/test.sh:13` runs pytest only; `tests/test_outputs.py` has no `Path("/app/audit.wren")` or `subprocess` call |
| 3 | Portal rubric is unrelated CHICKEN Scheme payroll task (ChatGPT) | **Agree** | `entire-report.txt:391-403` references `/app/SCHEMA.md`, `csi`, `audit.scm`, employee pay; task is Wren transaction audit. No `rubric.txt` in task dir. |
| 4 | Future-date rule not exercised; only invalid months tested (ChatGPT) | **Agree** | `instruction.md:3` cutoff `2026-06-13`; `transactions.tsv:18` `20261301` (month 13), `:24` `20260000` (month 0); no `20260614`+ row. `test_bad_date_count` expects 2 (`test_outputs.py:108-111`) |
| 5 | Hardcoded static JSON can pass all tests (test-quality report) | **Partially agree** | 45-row input + 26 exact errors make manual hardcoding laborious but possible; primary bypass is Python → JSON without Wren (blocker 2). Held-back test fixture would strengthen; not sole High blocker. |
| 6 | pytest not in Dockerfile / #20 fail (automated review script) | **Disagree** | `environment/requirements.txt:13-14` pins `pytest==8.3.2`; `environment/Dockerfile:40-41` installs via `pip3 install --require-hashes`; `tests/test.sh` has no `pip install` |
| 7 | Worst-model 100% / #54 fail (automated review script) | **Disagree** | `entire-report.txt:6-7` worst model Claude **60%**; >80% rejection threshold not met; #54 should CHECK |
| 8 | LLMaJ `behavior_in_tests` PASS (entire-report) | **Agree with caveat** | JSON behavioral rules are well covered (`entire-report.txt:110`); does not contradict Wren-path gap — LLMaJ did not check language enforcement |
| 9 | Wren quirks undocumented caused timeouts (entire-report) | **Agree** | `entire-report.txt:72-76,86` semicolons invalid, string `<` missing; contributes to fairness concern (#55) but 60% pass shows task is solvable |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Six dense prose paragraphs (lines 1, 3, 5, 7, 9, 11) exceed 3-paragraph guidance | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Formal enumerated error-code spec, not conversational prompt | `instruction.md:3-9` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT (rules/output), not developer steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input/output mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | All 12 error codes, paths, sort order, thresholds explicit | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic financial batch-audit in uncommon language | — |
| 9 | CHECK | Instruction is unique | Wren + velocity-hold/reversal netting is distinctive | — |
| 10 | CHECK | All paths are absolute | `/app/transactions.tsv`, `/app/audit.wren`, `/app/audit_report.json` | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No `accaudit-wren` string | `instruction.md` |
| 12 | CHECK | No canary string | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile no runtime web fetch in env code | Build-time git clone only; no runtime fetch in app | `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned with == | All packages hash-pinned in requirements.txt | `environment/requirements.txt` |
| 15 | CHECK | Base image digest-pinned | Both stages `@sha256:0d39fcc8...` | `environment/Dockerfile:1,25` |
| 16 | CHECK | Environment self-contained | COPY only from `environment/` | `environment/Dockerfile:44` |
| 17 | CHECK | No ground truth in environment | `examples/` are mini illustrations, not full 26-error answer | `environment/app/examples/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh no runtime installs | pytest in image; test.sh only runs pytest | `environment/Dockerfile:41`; `tests/test.sh:13` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed in this review | — |
| 22 | CHECK | Oracle no internet | solve.sh writes Wren locally, runs `wren_cli` | `solution/solve.sh:334` |
| 23 | CHECK | Oracle reflective of instruction | Full Wren implementation with parsing, velocity, reversals | `solution/solve.sh:4-334` |
| 24 | CHECK | test.sh reward.txt canonical block | mkdir, pytest, binary 0/1 reward | `tests/test.sh:4-18` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:15-18` |
| 27 | UNCHECK | Tests aligned with instructions | Wren path untested; future-date cutoff gap | blockers 2, 4 |
| 28 | CHECK | Tests check correctness | Specific txn_ids, counts, sorting, interaction rules | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Asserts JSON outcomes, no source parsing | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | txn_id assertions tied to fixture data are appropriate | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 41 tests documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics ≥3 negative criteria | Portal rubric is wrong task (CHICKEN Scheme) | `entire-report.txt:391-403` |
| 33 | UNCHECK | Rubric scores in allowed set | Wrong rubric content | `entire-report.txt:391-403` |
| 34 | UNCHECK | Rubric format Agent, ±N | Wrong rubric content | `entire-report.txt:391-403` |
| 35 | UNCHECK | Rubric criteria detailed | Wrong rubric content | `entire-report.txt:391-403` |
| 36 | UNCHECK | Rubric positive language | Wrong rubric content | `entire-report.txt:391-403` |
| 37 | UNCHECK | Rubric no /tests/ refs | Wrong rubric content | `entire-report.txt:391-403` |
| 38 | UNCHECK | Rubric no task.toml/instruction refs | Wrong rubric content | `entire-report.txt:391-403` |
| 39 | UNCHECK | Rubric no oracle/NOP refs | Wrong rubric content | `entire-report.txt:391-403` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary parent files | Clean task directory | task root |
| 42 | CHECK | author_name/email present | `task.toml:4-5` | `task.toml` |
| 43 | CHECK | Other metadata present | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | `languages = ["wren"]`, data-processing tags fit | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; observed medium (60% worst) | `task.toml:6`; `entire-report.txt:6-7` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Milestone solveN.sh | N/A — not milestone | `task.toml:9` |
| 48 | UNCHECK | Milestone test_mN.py | N/A — not milestone | `task.toml:9` |
| 49 | UNCHECK | Milestone scope | N/A — not milestone | `task.toml:9` |
| 50 | CHECK | Tests not in image | `.dockerignore:11-12`; Dockerfile copies `app/` only | `environment/.dockerignore` |
| 51 | CHECK | No accessible ground truth | solution/tests excluded from image | `environment/.dockerignore` |
| 52 | CHECK | Input not trivially modifiable to pass | Tests expect specific txn_ids from fixed fixture | `transactions.tsv`; `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned | wren-cli checkout `18553636618a4d33f10af9b5ab92da6431784a8c` | `environment/Dockerfile:14` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 60%, below 80% rejection threshold | `entire-report.txt:6-7` |
| 55 | UNCHECK | Not too hard/unfair | Undocumented Wren quirks caused 2/5 Claude timeouts | `entire-report.txt:72-76,15` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 2, 21, 27, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Write `/app/audit.wren` | — | **gap** | `instruction.md:1`; no test in `test_outputs.py` |
| Run `wren_cli /app/audit.wren` | — | **gap** | `instruction.md:1`; `test.sh` only pytest |
| Output `/app/audit_report.json` JSON array | `test_report_is_json_array` | covered | `test_outputs.py:32-35` |
| Four fields per record | `test_each_record_has_required_keys` | covered | `test_outputs.py:38-45` |
| 12 known error codes | `test_error_codes_are_known` | covered | `test_outputs.py:48-55` |
| MISSING_FIELD | `test_missing_field_*` | covered | `test_outputs.py:60-69` |
| BAD_TXN_ID | `test_bad_txn_id_*` | covered | `test_outputs.py:72-81` |
| BAD_ACCT_ID | `test_bad_acct_id_*` | covered | `test_outputs.py:84-93` |
| BAD_DATE (invalid calendar) | `test_bad_date_future_month_flagged`, `test_bad_date_zero_month_flagged` | covered | `test_outputs.py:96-105` |
| BAD_DATE (future cutoff 2026-06-13) | — | **gap** | `instruction.md:3`; no valid future date in `transactions.tsv` |
| BAD_AMOUNT | `test_bad_amount_*` | covered | `test_outputs.py:114-123` |
| BAD_TYPE | `test_bad_type_*` | covered | `test_outputs.py:126-135` |
| BAD_CURRENCY | `test_bad_currency_*` | covered | `test_outputs.py:138-147` |
| DUPLICATE_TXN | `test_duplicate_txn_*` | covered | `test_outputs.py:152-167` |
| FEE_OVERCAP (>25.00) | `test_fee_overcap_*` | covered | `test_outputs.py:170-179` |
| HIGH_VELOCITY (>5 debits/day) | `test_high_velocity_*` | covered | `test_outputs.py:184-205` |
| Velocity hold prevents overdraft | `test_velocity_held_debits_do_not_overdraft` | covered | `test_outputs.py:208-216` |
| OVERDRAFT | `test_overdraft_*` | covered | `test_outputs.py:221-252` |
| UNMATCHED_REVERSAL | `test_unmatched_reversal_*` | covered | `test_outputs.py:255-280` |
| Matched reversals not flagged | `test_matched_reversals_not_flagged` | covered | `test_outputs.py:283-288` |
| Sort order account/error/txn | `test_output_sorted_*` | covered | `test_outputs.py:299-321` |
| Total 26 errors | `test_total_error_count` | covered | `test_outputs.py:293-296` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #2, #7, #10, blockers 2/4, spec alignment |
| `task.toml` | #44, #45, blocker 1 |
| `environment/Dockerfile` | #13-#20, #53 |
| `environment/requirements.txt` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/transactions.tsv` | blocker 4, spec alignment |
| `environment/app/examples/ex_bad_date_future.tsv` | claim 4 adjudication |
| `tests/test.sh` | #20, #24-#26, blocker 2 |
| `tests/test_outputs.py` | #27-#31, blockers 2/4 |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | #45, #54, blockers 1/3, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: accaudit-wren-v368Z ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | — |
| terminus-claude-opus-4-8 | 60% (3/5) | 2 timeouts |
| oracle | 100% (3/3) | per report |
| nop | 0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `accaudit-wren-v368Z`; regular layout; Wren data-processing |
| 1 Instruction | ☑ | Precise but long (6 paragraphs); absolute paths; no hints |
| 2 Environment | ☑ | Digest-pinned Ubuntu; tmux/asciinema; wren-cli pinned; tests/solution excluded |
| 3 Oracle | ☑ | Static review: full Wren derive; not executed |
| 4 Verifiers | ☑ | Canonical test.sh; 41 behavior tests; Wren-path gap |
| 5 Metadata | ☑ | hard vs medium mismatch |
| 6 Rubric | ☑ | Portal rubric wrong task; no rubric.txt in folder |
| 7 LLMaJ & agent evidence | ☑ | Reconciled automated false positives on #20/#54 |
| 8 Novelty & fairness | ☑ | Multi-rule reconciliation; Python bypass open; Wren quirks undocumented |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Dockerfile pinning, dependency hygiene, and JSON behavioral tests are solid. Blockers: (1) update `difficulty` from hard to medium (Claude 60% worst-model) or rebalance; (2) add verifier coverage that `/app/audit.wren` exists and `wren_cli` produces the report — agents can bypass Wren with Python/static JSON today; (3) replace the portal rubric (currently CHICKEN Scheme payroll criteria) with Wren transaction-audit rubric. Also add a valid-format future-date row to exercise the `2026-06-13` cutoff.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2, 4 |
| Rubric | yes | 3 |
| Instruction Styling | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
