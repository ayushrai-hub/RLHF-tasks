# Terminus Review Report: `meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260623`

**Generated:** 2026-06-23 18:50 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260623`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; not re-run locally — Docker unavailable) |
| **CHECK count** | 52 |
| **UNCHECK count** | 3 |

**Error categories (internal):** Task Difficulty, Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Milestone layout, digest-pinned Dockerfile, offline verifier setup, oracle design, and M1/M2 spec-test alignment are solid. Three blockers remain: `difficulty = "medium"` mismatches observed hard tier (Claude 0%, GPT-5.5 20%); M3 `instruction.md` under-specifies tested JSON field names and null-vs-zero semantics despite `/app/docs/reconciliation-format.md` being available; portal rubric has only `# Rubric 1` and `# Rubric 2` for a 3-milestone task.

**Insights (concise):**

- M1/M2 pass 100% across all agent runs; M3 drives all failures (`test_reconciliation_report_matches_prior_ledger_union` 1/10).
- Agent failures are format-semantics (field names, `null` vs `0`, `status_counts` keys), not missing domain logic — fixable via M3 instruction clarity.
- `environment/requirements.txt` pins `pytest==8.4.1`; validate WARN on Dockerfile `pip install -r` line is a false positive for #14.
- Per-milestone `task.toml` (no top-level `[agent]`/`[verifier]`) matches `docs/guidelines/milestones.md`; external report warning on that point is not applicable.
- LLMaJ `behavior_in_task_description` PASS overstates M3 coverage — M3 instruction does not enumerate row field names.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | `task.toml` declares `difficulty = "medium"` but worst-model pass rate is 20% (Claude 0%, GPT-5.5 20%) → **hard** tier per `docs/guidelines/difficulty.md` (≤20%) | `task.toml:6`; `entire-report.txt:1-7` | Set `difficulty = "hard"` |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #27 | M3 instruction omits exact row field names (`adjustment_cents`, `adjustment_reason`, `prior_total_cents`, `prior_kwh`), does not distinguish delta zero-fill from output-field `null`, does not require all four `status_counts` keys, and does not point agents to `/app/docs/reconciliation-format.md` | `steps/milestone_3/instruction.md:1-7`; `environment/docs/reconciliation-format.md:5-7`; `steps/milestone_3/tests/test_m3.py:172-211`; `entire-report.txt:47-83` | Add explicit field list, null rules for missing prior/current sides, `status_counts` key rule, and doc reference to M3 instruction |
| 3 | High | Rubric, Milestones | #35 | Submitted rubric (in `entire-report.txt`) has only `# Rubric 1` and `# Rubric 2`; 3-milestone task requires `# Rubric 3` per `docs/guidelines/milestones.md` and `docs/guidelines/rubrics.md` | `entire-report.txt:417-441`; `task.toml:9` (`number_of_milestones = 3`) | Add `# Rubric 3` block covering reconciliation union rows, null handling, adjustment fields, status counts, M2 output preservation |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "medium"` but evaluation calibrates Hard (Claude 0%, GPT 20%) — update to `hard` (ChatGPT) | **Agree** | `task.toml:6` `difficulty = "medium"`; `entire-report.txt:5-7` Claude 0%, GPT 20%; worst 20% → hard per `docs/guidelines/difficulty.md` |
| 2 | M3 instruction gap: `adjustment_cents`/`adjustment_reason`, prior nulls, `status_counts` keys, doc reference (ChatGPT) | **Partially agree** | Field names in `environment/docs/reconciliation-format.md:5` but not `steps/milestone_3/instruction.md`; prior-field `null` for `new` rows tested at `test_m3.py:174,193-196` but unstated in instruction or env doc; `status_counts` all-keys tested at `test_m3.py:204-211` but unstated; M3 never references `/app/docs/reconciliation-format.md` |
| 3 | Rubric incomplete — only Rubric 1 and 2 for 3-milestone task (ChatGPT) | **Agree** | `entire-report.txt:417-441` ends at `# Rubric 2`; no `rubric.txt` in task folder; `task.toml:9` `number_of_milestones = 3` |
| 4 | LLMaJ `behavior_in_task_description` PASS — M3 lists all 12 row fields (entire-report) | **Disagree** | `steps/milestone_3/instruction.md` uses prose ("manual adjustment") without naming `adjustment_cents`/`adjustment_reason`; field list only in `environment/docs/reconciliation-format.md:5` |
| 5 | Non-canonical Node base image warning (entire-report §WARNINGS) | **Partially agree** | `environment/Dockerfile:1` uses digest-pinned `node:22-bookworm-slim`; digest pinning passes #15; canonical-list verification not run — advisory only, not a portal blocker |
| 6 | Missing top-level `[verifier]`/`[agent]` in task.toml (entire-report) | **Disagree** | `docs/guidelines/milestones.md:99` explicitly: "No top-level `[agent]` or `[verifier]` — use per-milestone"; per-step timeouts at `task.toml:27-49` |
| 7 | Task Instruction Sufficiency FAIL — systematic M3 spec issues (entire-report) | **Agree** | `entire-report.txt:33,71-83`; M3 test pass rates 1/10 and 6/10; failure patterns A–D align with unstated M3 semantics |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three milestone prompts; each 1–2 paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Domain prose; no LLM anti-patterns | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No ##/tables/code blocks | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions | Requirements stated as WHAT, not dev steps | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints or solving strategies | No hint language | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `steps/milestone_*/instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | M1/M2 fully specified; M3 goal clear (needs field-detail fix) | `steps/milestone_1/instruction.md`, `steps/milestone_2/instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic meter-settlement pipeline | task domain |
| 9 | CHECK | Instruction is unique | Meter-settlement + reconciliation domain; not a known duplicate | manual corpus check |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Folder name absent | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `steps/milestone_*/instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1` in requirements.txt | `environment/requirements.txt:1` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:...` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY only env subdirs | `environment/Dockerfile:24-27` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are format specs; rates in SQLite not plaintext answers | `environment/docs/`, `environment/.dockerignore:16-17` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:14-18`, `steps/milestone_*/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Oracle 100% (3/3) per evaluation report | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve scripts use local files + sqlite3/node | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | solve1/2/3 derive from raw data | `steps/milestone_3/solution/solve3.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical pattern all milestones | `steps/milestone_*/tests/test.sh` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `steps/milestone_*/tests/test.sh`, `test_m*.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | echo 0/1 to reward.txt | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | M3 tests enforce field names, prior nulls, full status_counts not stated in M3 instruction | `steps/milestone_3/instruction.md:3-5`; `test_m3.py:174-211` |
| 28 | CHECK | Tests check for correctness, not just format | Reference oracles recompute from raw data | `test_m1.py:53+`, `test_m2.py`, `test_m3.py:161-216` |
| 29 | CHECK | Tests verify behavior, not implementation | Output equality vs reference; no source grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact JSON/DB equality appropriate for structured settlement outputs | `test_m3.py:243` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` have docstrings | `steps/milestone_*/tests/test_m*.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives across submitted rubric | `entire-report.txt:427-428,440-441` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:417-441` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format correct on all lines | `entire-report.txt:417-441` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Missing `# Rubric 3` for milestone 3 reconciliation behavior | `entire-report.txt:417-441`; `task.toml:9` |
| 36 | CHECK | Rubric criteria use positive language | No "Agent does not…" positives | `entire-report.txt:417-441` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No test refs | `entire-report.txt:417-441` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:417-441` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:417-441` |
| 40 | CHECK | All required files present | Milestone layout complete | `steps/milestone_{1,2,3}/`, `environment/Dockerfile`, `task.toml` |
| 41 | CHECK | No unnecessary files in parent directory | No jobs/, README.md, stray data | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, milestones, timeouts, env | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | data-processing, db_interaction, javascript/sql/bash match oracle + SQLite | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared medium; worst-model 20% → hard | `task.toml:6`; `entire-report.txt:5-7` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under steps/ | `steps/milestone_{1,2,3}/` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1.sh, solve2.sh, solve3.sh | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | M1→normalized; M2→settlement; M3→reconciliation | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | .dockerignore excludes tests/; no COPY tests | `environment/.dockerignore:17`, `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ excluded from image | `environment/.dockerignore:16-17` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | SHA256 hash guard on raw events (M1/M2) | `test_m1.py:12,34-41` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% ≤80% | `entire-report.txt:5-7` |
| 55 | CHECK | Task is not too hard or unfair | Format spec in `/app/docs/reconciliation-format.md`; failures are clarity not missing env info | `environment/docs/reconciliation-format.md`; `entire-report.txt:63-65` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 27, 35, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: dedup by revision + source_priority | `test_normalized_feed_matches_catalog_rules` | covered | `steps/milestone_1/instruction.md:3`; `test_m1.py` |
| M1: quality + active-window filter | `test_filtered_and_duplicate_events_do_not_leak` | covered | `steps/milestone_1/instruction.md:3`; `test_m1.py` |
| M1: exact 8-field schema | `test_normalized_schema_is_exact` | covered | `steps/milestone_1/instruction.md:3` |
| M2: account_months columns + rounding | `test_settlement_database_rows_are_correct` | covered | `steps/milestone_2/instruction.md:3-4`; `test_m2.py` |
| M2: settlement-summary.json fields | `test_summary_json_matches_database_totals` | covered | `steps/milestone_2/instruction.md:4` |
| M3: union of current + prior keys | `test_reconciliation_report_matches_prior_ledger_union` | covered | `steps/milestone_3/instruction.md:3`; `test_m3.py:168` |
| M3: row fields `adjustment_cents`, `adjustment_reason` | `test_reconciliation_report_matches_prior_ledger_union` | gap | names in `reconciliation-format.md:5` only; not in M3 instruction |
| M3: `prior_total_cents`/`prior_kwh` = `null` when no prior row | `test_reconciliation_report_matches_prior_ledger_union` | gap | `test_m3.py:174,193-196`; unstated in instruction + env doc |
| M3: delta arithmetic uses 0 for missing side | `test_reconciliation_report_matches_prior_ledger_union` | covered | `steps/milestone_3/instruction.md:3`; `test_m3.py:194,197` |
| M3: all four `status_counts` keys present | `test_reconciliation_report_matches_prior_ledger_union` | gap | `test_m3.py:204-211`; unstated |
| M3: preserve M2 outputs | `test_settlement_outputs_are_preserved` | covered | `steps/milestone_3/instruction.md:7`; `test_m3.py:220-238` |
| M3: all four status values exercised | `test_reconciliation_report_exercises_all_statuses` | covered | `steps/milestone_3/instruction.md:5`; `test_m3.py:245-253` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, blocker 1, metadata |
| `entire-report.txt` | #45, #54, agent stats, rubric, adjudication |
| `steps/milestone_1/instruction.md` | M1 spec alignment |
| `steps/milestone_2/instruction.md` | M2 spec alignment |
| `steps/milestone_3/instruction.md` | #27, blocker 2 |
| `environment/docs/reconciliation-format.md` | M3 field schema, adjudication claim 2 |
| `environment/requirements.txt` | #14 |
| `environment/Dockerfile` | #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `steps/milestone_3/tests/test_m3.py` | #27, M3 spec gaps |
| `steps/milestone_*/tests/test.sh` | #24, #25, #26 |
| `steps/milestone_*/solution/solveN.sh` | #22, #23 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate meter-settlement-ledger-8017804a-20de-4d74-92e1-381dd62ab237-20260623/
Summary: 0 error(s), 1 warning(s), 0 info
WARNING: pinned_dependencies — pip install -r line lacks == (false positive; requirements.txt pins pytest==8.4.1)
Task type detected: milestone
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | M3 format failures dominate |
| terminus-claude-opus-4-8 | 0.0% (0/5) | All partial 0.667 (M1+M2 only) |
| oracle | 100.0% (3/3) | Per evaluation report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | medium |
| Tier match (#45) | no |

**Per-test M3 pass rates:** `test_reconciliation_report_matches_prior_ledger_union` 1/10; `test_reconciliation_report_exercises_all_statuses` 6/10; `test_settlement_outputs_are_preserved` 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone meter-settlement task; report matches folder |
| 1 Instruction | ☑ | M1/M2 strong; M3 field/null gaps |
| 2 Environment | ☑ | Digest-pinned, tmux+asciinema, offline, .dockerignore OK |
| 3 Oracle | ☑ | Derives outputs; 100% per report (local oracle not run) |
| 4 Verifiers | ☑ | Canonical test.sh, reference oracles, docstrings |
| 5 Metadata | ☑ | difficulty mismatch blocker |
| 6 Rubric | ☑ | Portal rubric missing # Rubric 3 |
| 7 LLMaJ & agent evidence | ☑ | M3 instruction sufficiency FAIL supported; behavior_in_task_description overstated |
| 8 Novelty & fairness | ☑ | Multi-step pipeline; no cheating paths |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Milestone structure, digest-pinned Dockerfile, offline verifiers, and M1/M2 spec-test alignment look solid. Blockers: update `task.toml` `difficulty` to `hard` (Claude 0%, GPT-5.5 20%); expand M3 `instruction.md` with exact row field names (`adjustment_cents`, `adjustment_reason`, `prior_total_cents`, `prior_kwh`), clarify that zero-fill applies only to delta arithmetic while missing prior/current fields stay `null`, require all four `status_counts` keys, and reference `/app/docs/reconciliation-format.md`; add `# Rubric 3` for reconciliation behavior in the portal rubric.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | yes | 2 |
| Test Alignment/Coverage Issues | yes | 2 |
| Rubric | yes | 3 |
| Milestones | yes | 3 |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review`._
