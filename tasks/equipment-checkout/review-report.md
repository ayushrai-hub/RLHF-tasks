# Terminus Review Report: `equipment-checkout`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Rubric, Test Alignment/Coverage Issues, Milestones, Metadata Issues

**Decision (concise):** Strong Go/SQLite milestone task with digest-pinned environment, excellent M3 trap coverage (banker's rounding, nearest-rank, stored-rate HMAC), and correct milestone rubric *format* (`# Rubric 1`–`# Rubric 3` for `number_of_milestones = 3`). Real blockers: platform rubric describes wrong commands/behavior (`loan_chain`, `overdue-report`, category surcharge at checkout vs MAINTENANCE 1.5× at checkin), M1/M2 milestone tests omit required `init` table creation and M2 `audit_chain` checkout assertions, and milestone layout errors (`solveN.sh` missing; duplicate top-level `[agent]`/`[verifier]` in `task.toml`).

**Insights (concise):**

- ChatGPT rubric and M1/M2 coverage claims are **confirmed** with file evidence; rubric is not a non-milestone format misuse — headers are correct, **content** is wrong.
- `# Rubric 2` invents checkout-time category surcharges and a `days` validation order that do not exist in `steps/milestone_2/instruction.md` or `equipment-policies.md`.
- M2 `audit_chain` gap is milestone-scoring critical: `test_chain_verify_valid_single` passes with an empty chain if checkout never inserts rows (`test_m3.py:35-39`).
- `validate` errors on `task.toml:25-29` (forbidden top-level timeouts) and missing `solve1.sh`–`solve3.sh` per `docs/guidelines/milestones.md`.
- Worst-model 80% is **not** >80% rejected tier (`#54` passes); declared `hard` vs observed `easy` is informational only (`#45` UNCHECK, not a revision driver).
- `.ruff_cache/` is stray dev artifact (Low cleanup); no `jobs/` folder present despite `.dockerignore` entry.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric grades wrong behavior: `loan_chain` vs `audit_chain`; `overdue-report` vs `rental-report`; category surcharge (1.15/1.05/1.00) + banker's rounding **at checkout** vs MAINTENANCE 1.5× surcharge **at checkin** only. | `entire-report.txt:651-677`; `steps/milestone_2/instruction.md:26-32`; `environment/docs/equipment-policies.md:24-29`; `steps/milestone_3/instruction.md:22-30` | Rewrite all three rubric blocks to match `audit_chain`, `rental-report`, checkin MAINTENANCE surcharge, and actual M2 validation order (equipment → availability/DAMAGED → borrower). |
| 2 | High | Test Alignment/Coverage Issues | #27 | M1 requires `init` to create all four tables; tests only assert DB file exists. Agent can omit `checkouts`/`audit_chain` and pass M1. | `steps/milestone_1/instruction.md:7-8`; `steps/milestone_1/tests/test_m1.py:25-29` | Add `test_init_creates_all_tables` querying `sqlite_master` for `equipment`, `borrowers`, `checkouts`, `audit_chain`. |
| 3 | High | Test Alignment/Coverage Issues | #27 | M2 requires checkout to append HMAC row to `audit_chain`; no M2 test queries that table. Agent can skip chain logic and still pass all 29 M2 tests; some M3 tests also pass on empty chain. | `steps/milestone_2/instruction.md:15-18`; `steps/milestone_2/tests/test_m2.py` (no `audit_chain` query); `steps/milestone_3/tests/test_m3.py:35-39` | Add M2 test asserting `audit_chain` row count/hash after successful checkout (structural minimum; hash optional). |
| 4 | High | Milestones | #47 | Missing `solve1.sh`, `solve2.sh`, `solve3.sh`; only monolithic `solve.sh` per milestone. | `docs/guidelines/milestones.md:48-57`; `validate` errors; `steps/milestone_1/solution/` has `solve.sh` only | Split each milestone oracle into `solveN.sh`; make `solve.sh` a thin wrapper calling `solveN.sh`. |
| 5 | High | Metadata Issues, Milestones | #43 | Milestone task has forbidden top-level `[agent]` and `[verifier]` sections (duplicate of per-step timeouts). | `task.toml:25-29`; `validate_task.py` error; `docs/task-requirements.md:107` | Remove lines 25–29 from `task.toml`; keep only `[steps.agent]` / `[steps.verifier]` per milestone. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Rubric mismatch: category surcharge at checkout, `loan_chain`, `overdue-report` (ChatGPT High) | **Agree** | `entire-report.txt:657,662-663,671,673-677`; actual spec: `audit_chain` (`milestone_2/instruction.md:18`), `rental-report` (`milestone_3/instruction.md:22`), MAINTENANCE 1.5× at checkin (`milestone_2/instruction.md:29`, `equipment-policies.md:24-29`) |
| 2 | M1 `init` does not verify all four tables (ChatGPT / test-quality review) | **Agree** | `milestone_1/instruction.md:8`; `test_m1.py:25-29` only checks `os.path.exists` |
| 3 | M2 has no direct `audit_chain`/HMAC test (ChatGPT / test-quality review) | **Agree** | `milestone_2/instruction.md:18`; `test_m2.py` — no `audit_chain` SQL assertions |
| 4 | Optional: remove `jobs/` and `.ruff_cache/` (ChatGPT Low) | **Partially agree** | No `jobs/` directory in zip; `.ruff_cache/` present (`equipment-checkout/.ruff_cache/`). Low cleanup only |
| 5 | Optional: stdout assertions for invalid category/condition; `total_fee_cents=0` in empty stats (ChatGPT Low) | **Agree** (non-blocking) | `test_m1.py:58-60,132-135` exit-code only; `test_m2.py:101-105` omits `total_fee_cents=0` |
| 6 | Dockerfile digest-pinned Go base — no blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:1a6d4452...` |
| 7 | Harbor REVIEW REPORT: READY TO USE (export) | **Disagree** | Rubric and M1/M2 coverage gaps above are High; export warnings on stub schema are non-blocking |
| 8 | Test-quality M3 ROBUST (export) | **Agree** | `test_m3.py` tamper, stored-rate, nearest-rank, pop-stddev traps |
| 9 | Instruction sufficiency PASS — agent failures are execution not spec (export) | **Partially agree** | Go PATH discoverability tripped agents (`entire-report.txt:123-154`); separate from rubric/M1/M2 test gaps |
| 10 | Non-milestone task wrongly uses milestone rubric format (user ask) | **Disagree** | `task.toml:9` `number_of_milestones = 3`; `# Rubric 1`–`# Rubric 3` is **required** per `docs/guidelines/rubrics.md:53-64` — format is correct, content is wrong |
| 11 | Automated #1 instruction too long (788 words combined) | **Disagree** | Per-milestone files are ~130–250 words each with CLI command specs; milestone layout (`broken-pottery-studio` precedent) |
| 12 | Automated #11 task name in instruction | **Disagree** | `equipment-checkout` folder name absent; HMAC key `equipment-checkout-secret-2026` is normative spec (`milestone_3/instruction.md:12`, `chain-spec.md`) |
| 13 | Automated #41 stray `jobs/` | **Disagree** | `jobs/` only in `.dockerignore:2`; directory not present |
| 14 | Automated #46–#49 milestone layout failures | **Partially agree** | `test_m1.py`–`test_m3.py` exist and are scoped (`#48`, `#49` pass); `solveN.sh` missing (`#47` fail) |
| 15 | Automated #31 41 missing docstrings | **Disagree** | `#31` allows informative **names**; e.g. `test_checkin_maintenance_bankers_round_down`; TRAP tests have docstrings (`test_m2.py:206-214`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Per-milestone CLI specs ~130–250 words each | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer CLI spec, not synthetic essay | `milestone_1/instruction.md` |
| 3 | UNCHECK | No excessive markdown | `##` / `###` headers in all three milestone instructions | `milestone_1/instruction.md:5-30` |
| 4 | CHECK | No step-by-step HOW | Describes commands/outputs, not implementation steps | — |
| 5 | CHECK | No hints/solving strategies | Points to docs, no walkthrough | — |
| 6 | CHECK | No design-doc tables | No I/O mapping tables in instructions | — |
| 7 | CHECK | Well specified | Schema, chain, statistics docs are normative | `environment/docs/` |
| 8 | CHECK | Interesting | Go + SQLite + HMAC + statistical traps | — |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/app`, `/docs/...` | `milestone_1/instruction.md:3` |
| 11 | CHECK | Task name not in instruction | Folder name absent; HMAC key is spec literal | grep task folder name in `steps/` |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No web content fetch | Runtime env has `GOPROXY=off` | `environment/Dockerfile:19` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, etc. | `environment/Dockerfile:11` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only `source/`, `docs/` | `environment/Dockerfile:15,21` |
| 17 | CHECK | No ground-truth answers | Stubs return "not implemented"; docs are normative spec | `environment/source/cmds.go` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:11`, `milestone_1/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed (Harbor CLI error) | `./scripts/terminus oracle` |
| 22 | CHECK | Oracle no internet | `go build` + local SQLite | `steps/milestone_*/solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Full Go implementation, computed outputs | `steps/milestone_3/solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir + default 0 + pytest + 0/1 | `milestone_1/tests/test.sh:2-10` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | milestone test files |
| 26 | CHECK | Binary rewards | 0/1 only | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M1 four-table init and M2 audit_chain gaps | §2 blockers 2–3 |
| 28 | CHECK | Tests check correctness | Fee math, HMAC tamper, percentile traps | `test_m2.py`, `test_m3.py` |
| 29 | CHECK | Behavior not implementation grep | CLI subprocess + SQLite assertions | milestone tests |
| 30 | CHECK | No brittle string matching | Exact strings match instruction-required messages | `test_m2.py:44,72` |
| 31 | CHECK | Informative test names/docstrings | Descriptive `test_*` names; TRAP docstrings | `test_m2.py:206-214` |
| 32 | CHECK | ≥3 negative rubric criteria | 9 negatives across 3 blocks | `entire-report.txt:657-677` |
| 33 | CHECK | Valid rubric scores | ±1,2,3,5 only | rubric section |
| 34 | CHECK | Agent …, ±N format | 22 Agent lines with `# Rubric N` headers | rubric section |
| 35 | UNCHECK | Rubric detailed/precise | Wrong table names, commands, surcharge timing | §2 blocker 1 |
| 36 | CHECK | Positive rubric language | Bad-behavior negatives use `-N` scores | rubric section |
| 37 | CHECK | No /tests/ references | None in rubric | rubric section |
| 38 | CHECK | No task.toml/instruction.md refs | None in rubric | rubric section |
| 39 | CHECK | No oracle/NOP mentions | None in rubric | rubric section |
| 40 | CHECK | Required files present | Milestone layout: Dockerfile + task.toml + steps/ | task tree |
| 41 | UNCHECK | No stray parent files | `.ruff_cache/` dev artifact in task root | `equipment-checkout/.ruff_cache/` |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | UNCHECK | Other required metadata fields | Forbidden top-level `[agent]`/`[verifier]` | `task.toml:25-29` |
| 44 | CHECK | Tags/languages/category applicable | Go, sqlite, db_interaction, data-processing | `task.toml:5-12` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 80% → easy tier | `entire-report.txt:26-27`; not a revision driver alone |
| 46 | CHECK | steps/ milestone layout | 3 milestones under `steps/` | `task.toml:31-50` |
| 47 | UNCHECK | solveN.sh per milestone | Only `solve.sh`; no `solve1.sh`–`solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | Each file tests only its milestone commands | spot-check all three |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | No solution/ COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially cheat | HMAC/stats require real computation | `test_m3.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80% — not >80% rejected | `entire-report.txt:26-27` |
| 55 | CHECK | Not unfair | M3 failures are agent toolchain/discoverability, spec is complete | `entire-report.txt:136-154` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 42, 44, 46, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 3, 9, 21, 27, 35, 41, 43, 45, 47 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `init` creates four tables | `test_init_creates_db` | **gap** | `milestone_1/instruction.md:8`; `test_m1.py:25-29` |
| Invalid category prints stdout error | `test_add_equipment_invalid_category` | **gap** (exit only) | `milestone_1/instruction.md:15`; `test_m1.py:58-60` |
| Invalid condition prints stdout error | `test_add_equipment_invalid_condition` | **gap** (exit only) | `milestone_1/instruction.md:16`; `test_m1.py:132-135` |
| Checkout appends `audit_chain` HMAC row | — | **gap** | `milestone_2/instruction.md:18`; no M2 test |
| Checkout validation order | `test_checkout_damaged_error_before_borrower_check` | covered | `test_m2.py:188-195` |
| MAINTENANCE 1.5× + banker's rounding at checkin | `test_checkin_maintenance_*` | covered | `test_m2.py:199-262` |
| `checkout-stats` four fields | `test_checkout_stats_empty` | **partial** | `test_m2.py:101-105` omits `total_fee_cents=0` |
| `chain-verify` HMAC + stored rate | `test_chain_verify_*` | covered | `test_m3.py:50-80` |
| `rental-report` nearest-rank + pop stddev | `test_rental_report_*` | covered | `test_m3.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #43, #45, #46, blocker 5 |
| `entire-report.txt` | #32–39, #45, #54, rubric adjudication, agent stats |
| `steps/milestone_1/instruction.md` | M1 init requirement, blocker 2 |
| `steps/milestone_2/instruction.md` | M2 audit_chain, surcharge timing, blocker 1 |
| `steps/milestone_3/instruction.md` | `rental-report` command name, blocker 1 |
| `steps/milestone_1/tests/test_m1.py` | M1 table gap |
| `steps/milestone_2/tests/test_m2.py` | M2 audit_chain gap, stats partial |
| `steps/milestone_3/tests/test_m3.py` | empty-chain false pass, M3 strength |
| `environment/docs/equipment-policies.md` | MAINTENANCE surcharge at checkin |
| `environment/Dockerfile` | #15, #20 |
| `docs/guidelines/milestones.md` | solveN.sh requirement, blocker 4 |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml — Milestone tasks must not have top-level [agent] / [verifier]
ERROR: Missing solve1.sh, solve2.sh, solve3.sh
WARNING: 41 informative_test_docstrings warnings (names suffice for #31)
Summary: 5 errors, 41 warnings
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 80.0% (4/5) | Worst model |
| terminus-gpt5-5 | 40.0% (2/5) | |
| oracle | 100.0% (3/3) | per export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (60–80% worst) |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `equipment-checkout`, 3-milestone Go/SQLite task |
| 1 Instruction | ☑ | Per-milestone CLI specs; MAINTENANCE at checkin not checkout |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; pytest in image |
| 3 Oracle | ☐ | Not executed locally |
| 4 Verifiers | ☑ | M1/M2 coverage gaps; M3 strong |
| 5 Metadata | ☑ | Top-level agent/verifier must be removed |
| 6 Rubric | ☑ | Milestone format correct; content wrong |
| 7 LLMaJ & agent evidence | ☑ | Export adjudicated |
| 8 Novelty & fairness | ☑ | Trap design excellent; Go PATH friction noted |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task — the trap tests for banker's rounding, nearest-rank percentiles, and stored-rate HMAC verification are excellent, and the digest-pinned Go environment is in good shape. Before we can accept, three things need fixing. First, the platform rubric describes the wrong system: it mentions `loan_chain` and `overdue-report`, applies category surcharges at checkout, and misses that the 1.5× MAINTENANCE surcharge happens at checkin — please align all three rubric blocks with `audit_chain`, `rental-report`, and the actual M2 spec. Second, strengthen milestone tests so M1 verifies all four tables are created by `init`, and M2 verifies checkout writes an `audit_chain` row (right now an agent can pass M2 without any chain logic). Third, fix milestone packaging: remove the duplicate top-level `[agent]`/`[verifier]` from `task.toml` and add `solve1.sh`–`solve3.sh` wrappers per milestone convention.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2, 3 |
| Milestones | yes | 4 |
| Metadata Issues | yes | 5 |
| Instruction Styling | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
