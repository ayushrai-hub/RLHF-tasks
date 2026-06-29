# Terminus Review Report: `inventory-reconciliation-engine.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3; local not run — Docker unavailable) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Test Alignment/Coverage Issues, Task Difficulty

**Decision (concise):** Strong Go ledger repair task with an independent Python reference verifier and solid core coverage, but **not acceptable yet**. GPT-5.5 passes at **100%** (above the >80% rejection threshold). Verifiers also leave two instruction-mandated behaviors under-tested: `audit_trail.json` schema/digest (only 2 of 6 fields asserted) and the documented `CARRY_FORWARD` operation (zero test events). ChatGPT/Harbor claims about a non-canonical Docker base and milestone rubric format are **false** on file evidence.

**Insights (concise):**

- `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452…` **is** the canonical Go base (`docs/guidelines/dockerfxile.md:11`) — Harbor “non-canonical base” warning is incorrect.
- Non-milestone rubric with only `# Rubric 1` + flat `Agent …, ±N` lines is **correct**; positive sum is 35 (within 10–40); 3 distinct negatives present.
- `tests/test_audit_matches_report_digest` allows a stub audit file with only `projection_digest` + `batch_count` (`test_outputs.py:557-560`).
- `CARRY_FORWARD` is specified in `ledger_rules.md` (referenced by `instruction.md:30`) and implemented in `reference_reconcile` (`test_outputs.py:470-473`) but never exercised by any test fixture.
- Platform oracle 100% (3/3) and Claude Opus 60% show the task is solvable; GPT saturation drives the difficulty rejection.
- Cleanup noise: `tests/__pycache__/`, `.step2b-metrics.jsonl`, and decoy `environment/inventory_engine/` Python tree — Low, not blocking.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #54 | Worst-model pass rate **100%** (>80% = too easy / rejected tier) | `entire-report.txt:26` `terminus-gpt5-5: 100.0% (5/5)`; `docs/guidelines/difficulty.md:12` | Harden task until worst-model rate ≤80% (ideally ≤60% for medium), or document platform re-run if rates were anomalous |
| 2 | High | Test Alignment/Coverage Issues | #27 | `audit_trail.json` required fields largely untested — stub with 2 fields can pass | `instruction.md:69`; `output_contract.toml:40-46`; `test_outputs.py:557-560` asserts only `projection_digest` and `batch_count` | Add full audit schema checks: `generated_from`, `journal_digest`, `batches`, self-consistent `audit_digest` |
| 3 | High | Test Alignment/Coverage Issues | #27 | `CARRY_FORWARD` documented mutating op has **zero** test coverage | `environment/docs/ledger_rules.md:30`; `test_outputs.py:470-473` (reference impl); no `CARRY_FORWARD` in `seed.jsonl` or any test fixture | Add a dedicated test with CARRY_FORWARD events comparing full report to `reference_reconcile` |

*No other High-severity blockers confirmed on artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical `golang:1.24-bookworm` base image (ChatGPT / Harbor REVIEW REPORT) | **Disagree** | `environment/Dockerfile:1` digest matches `docs/guidelines/dockerfxile.md:11` canonical table exactly |
| 2 | `audit_trail.json` underchecked — only `projection_digest` + `batch_count` (ChatGPT / TEST QUALITY REVIEW) | **Agree** | `instruction.md:69`; `test_outputs.py:557-560` |
| 3 | `CARRY_FORWARD` documented but never tested (ChatGPT / TEST QUALITY REVIEW) | **Agree** | `ledger_rules.md:30`; `grep CARRY_FORWARD seed.jsonl` → no matches; no `test_carry_forward*` in `test_outputs.py` |
| 4 | Reservation expiration test only spot-checks one account (ChatGPT / TEST QUALITY REVIEW) | **Partially agree** | `test_outputs.py:681-683` checks `held==0`, `available==20` only; non-blocking alone (Medium) — full `reference_reconcile` comparison would strengthen |
| 5 | ZIP cleanup noise — pytest cache, inventory_engine decoy files (ChatGPT Low) | **Agree** | `tests/__pycache__/`, `.step2b-metrics.jsonl`, `environment/inventory_engine/` present; Low severity |
| 6 | Non-milestone task uses milestone rubric format (user concern) | **Disagree** | `task.toml:12` `number_of_milestones = 0`; rubric has only `# Rubric 1` + flat lines; `docs/guidelines/rubrics.md:64` “`# Rubric 1` optional; no `# Rubric 2+`” |
| 7 | Needs Revision for base image + tests (ChatGPT summary) | **Partially agree** | Base-image claim false; test gaps and #54 are real drivers |
| 8 | LLMaJ `behavior_in_tests` PASS (entire-report) | **Partially agree** | Core ledger behaviors covered; audit schema and CARRY_FORWARD gaps remain |
| 9 | Instruction sufficiency FAIL note in export header (entire-report:53) | **Disagree as blocker** | Export shows placeholder “workflow to analyze”; per-trial analysis documents real agent errors, not systematic spec gaps |
| 10 | Missing `mkdir -p /logs/verifier` in test.sh (automated review) | **Partially agree** | `tests/test.sh:1-14` lacks mkdir; `docs/guidelines/writing-tests.md:11` canonical pattern; platform oracle 100% suggests Harbor provides mount — polish, not primary blocker |
| 11 | Instruction too long / heavy markdown (automated #1, #3) | **Partially agree** | ~574 words, 4 `##` headers, JSON schema block in `instruction.md`; borderline but schema may justify length — not listed as main blocker |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction concise | ~574 words, 4 `##` sections + JSON schema block exceeds 3-paragraph guidance | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational problem statement, not LLM role-play | `instruction.md:1-5` |
| 3 | UNCHECK | No excessive markdown | `##` headers + fenced JSON example | `instruction.md:7-62` |
| 4 | CHECK | No step-by-step HOW | States workflow commands + defers semantics to normative docs | `instruction.md:7-16`, `:30` |
| 5 | CHECK | No hints/solving strategies | WHAT to repair; rules in `ledger_rules.md` / `domain.go` | `instruction.md` |
| 6 | CHECK | No design-doc tables | No input→output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear CLI workflow, paths, schema, digest rules | `instruction.md` |
| 8 | CHECK | Interesting | Real event-sourced quota ledger engineering | task content |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/bin/ledgerctl`, `/app/output/…`, etc. | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No slug/canary | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No web content fetch | `allow_internet = false`; offline env | `task.toml:34` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` in Dockerfile | `environment/Dockerfile:12-14` |
| 15 | CHECK | Digest-pinned canonical FROM | Canonical golang digest per policy | `Dockerfile:1`, `docs/guidelines/dockerfxile.md:11` |
| 16 | CHECK | Context in environment/ | COPY only env subdirs | `Dockerfile:19-24` |
| 17 | CHECK | No ground truth in env | Starter Go has intentional bugs; decoy Python not solution | `environment/internal/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose safe | No docker-compose.yaml | task root |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no runtime installs | `Dockerfile:12-14`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3) | `entire-report.txt:30` |
| 22 | CHECK | Oracle no internet | Local `go build` + CLI only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Copies repaired Go packages, builds, runs pipeline | `solution/solve.sh:8-22` |
| 24 | UNCHECK | reward.txt canonical block | Missing `mkdir -p /logs/verifier` | `tests/test.sh:1-14`; `docs/guidelines/writing-tests.md:11` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:10-14` |
| 27 | UNCHECK | Tests aligned with instruction | Audit schema + CARRY_FORWARD gaps | `test_outputs.py:557-560`; `ledger_rules.md:30` |
| 28 | CHECK | Tests check correctness | Independent `reference_reconcile` for most scenarios | `test_outputs.py:546-554`, `:593-594` |
| 29 | CHECK | Behavior not implementation | CLI integration + reference comparison | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Structural + digest comparisons | `tests/test_outputs.py` |
| 31 | CHECK | Informative names or docstrings | Descriptive `test_*` names (`test_truncated_batch_durable_prefix`, etc.) | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives (-5, -3, -5) | `entire-report.txt:505-507` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All criteria use allowed magnitudes | `entire-report.txt:493-507` |
| 34 | CHECK | Rubric Agent format | 15 `Agent …, ±N` lines | `entire-report.txt:493-507` |
| 35 | CHECK | Rubric detailed/precise | Ledger-specific: chronological sort, durable prefix, reversal inversion | `entire-report.txt:493-504` |
| 36 | CHECK | Positive rubric phrasing | Negatives describe bad actions taken, not “does not” positives | `entire-report.txt:505-507` |
| 37 | CHECK | Rubric no /tests/ refs | No pytest or /tests/ | `entire-report.txt:493-507` |
| 38 | CHECK | Rubric no instruction.md refs | References `ledger_rules.md` / `quota_policy.md` (env docs), not instruction.md | `entire-report.txt:493` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:493-507` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | UNCHECK | Clean parent directory | `tests/__pycache__/`, `.step2b-metrics.jsonl` in task root | task root listing |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Metadata complete | category, languages, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags/category match | `data-processing`, go, ledger tags | `task.toml:7-10` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 100% → rejected tier | `task.toml:6`, `entire-report.txt:26` — metadata mismatch not sole blocker per policy, but noted |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/; explicit absence checks | `Dockerfile:28-29` |
| 51 | CHECK | Solution not in env | No solution COPY; build-time checks | `Dockerfile:28-30` |
| 52 | CHECK | Agent cannot trivially cheat | Reference replayer + generated random batches | `tests/test_outputs.py:612-632` |
| 53 | CHECK | Git pinned | No git clone | `Dockerfile` |
| 54 | UNCHECK | Not too easy (>80%) | GPT-5.5 100% (5/5) | `entire-report.txt:26` |
| 55 | CHECK | Not unfair | Agents failed on real boundary bugs; spec is testable | `entire-report.txt:65-118` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 50, 51, 52, 53, 55 |
| **UNCHECK** | 1, 3, 9, 24, 27, 41, 45, 46, 47, 48, 49, 54 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Chronological replay order | `test_chronological_order_beats_file_order` | covered | `test_outputs.py:597-609` |
| Durable-prefix truncated journal | `test_truncated_batch_durable_prefix` | covered | `test_outputs.py:645-666` |
| Idempotent import/rebuild | `test_idempotent_import_and_rebuild` | covered | `test_outputs.py:563-574` |
| REVERSAL per-type inversion | `test_reversal_consume_and_correction` | covered | `test_outputs.py:576-594` |
| Legacy snapshot merge | `test_legacy_migration_only_account` | covered | `test_outputs.py:635-642` |
| Reservation expiration at rebuild | `test_reservation_expiration_at_rebuild` | partial | `test_outputs.py:669-683` — spot-check only |
| Replica conflict / resume mismatch | `test_replica_correction_conflict`, `test_resume_replica_mismatch` | covered | `test_outputs.py:686+` |
| `quota_report.json` full schema + digest | `test_report_schema_and_digest`, `test_seed_matches_reference` | covered | `test_outputs.py:541-554` |
| `audit_trail.json` full schema + digests | `test_audit_matches_report_digest` | **gap** | `test_outputs.py:557-560` — 2/6 fields |
| `CARRY_FORWARD`: double available, clear held, set epoch | — | **gap** | `ledger_rules.md:30`; no test fixture |
| `processed_count = applied + rejected` | `test_seed_matches_reference` (via reference) | covered | `test_outputs.py:548-552` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #3, #10, #27, audit schema req |
| `environment/Dockerfile` | #14, #15, #20, canonical base |
| `docs/guidelines/dockerfxile.md` | #15 canonical base adjudication |
| `environment/docs/ledger_rules.md` | CARRY_FORWARD spec |
| `tests/test_outputs.py` | #27, #28, audit/CARRY_FORWARD gaps |
| `tests/test.sh` | #24 reward block |
| `task.toml` | #45, #54, metadata |
| `entire-report.txt` | agent stats, rubric #32-39, platform oracle |
| `output_contract.toml` | audit_trail required fields |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate inventory-reconciliation-engine.
Summary: 0 error(s), 16 warning(s), 1 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Drives #54 failure |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Medium tier |
| oracle | 100.0% (3/3) | Platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 100.0% |
| Observed tier | rejected (>80%) |
| Declared difficulty | hard |
| Tier match (#45) | no — declared hard vs observed rejected/easy for GPT |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `inventory-reconciliation-engine.`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Well-specified; borderline length/markdown (#1, #3) |
| 2 Environment | ☑ | Canonical digest-pinned Go base; tmux+asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Platform 3/3; local Docker unavailable |
| 4 Verifiers | ☑ | Gaps: audit schema, CARRY_FORWARD; missing mkdir |
| 5 Metadata | ☑ | Complete; difficulty vs rates mismatch |
| 6 Rubric | ☑ | Non-milestone format OK; 35 positive pts; 3 negatives |
| 7 LLMaJ & agent evidence | ☑ | GPT saturation + test gaps override LLMaJ behavior_in_tests PASS |
| 8 Novelty & fairness | ☑ | Multi-package Go repair; reference verifier; fair failures |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid ledger task — the Go repair scope, reference-style verifier, and anti-cheat design are in great shape, and the Dockerfile base image is correctly pinned. Three things to fix before we can accept: GPT-5.5 is passing at 100%, which puts the task above the too-easy threshold, so it needs more difficulty calibration. Please also tighten the audit test so `audit_trail.json` validates all required fields and digest self-consistency (right now a stub with just `projection_digest` and `batch_count` could pass), and add a direct test for `CARRY_FORWARD` since it's documented in the ledger rules but never exercised. The rubric format looks fine for a non-milestone task — no changes needed there.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 2, 3 |
| Task Difficulty | yes | 1 |
| Environment | no | — |
| Pinning Issues | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Instruction Styling | no | — (borderline #1/#3 noted, not gated) |
| Other | no | — |
