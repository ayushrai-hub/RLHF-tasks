# Terminus Review Report: build-postgres-publication-column-filter-compatibility-gate-kotlin-sql-json

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed locally (platform report: 100% 3/3) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Kotlin/Postgres milestone task with digest-pinned JDK image, correct 3-block milestone rubric format, baked verifier deps, and fair agent difficulty (40% worst model). One real High blocker: M1 tests require alphabetically sorted `targetTables` but neither `snapshot_contract.md` nor milestone-1 instruction states that rule — three agent M1 failures trace to this undocumented expectation. ChatGPT’s other High claims (JSON `schema` field, weak subscription assertions) are real test gaps but do not unfairly fail agents; missing_column suppression and plan action ordering are already specified or test-enforced. Remove stray `Untitled` report copy before resubmit.

**Insights (concise):**

- Milestone rubric uses correct `# Rubric 1`–`# Rubric 3` blocks (not flat non-milestone format); 8 negatives total, ≥1 per block, 14/20/18 positive pts per block.
- Automated validate warnings on #14/#20 are false positives: `requirements.lock` pins `pytest==8.4.1` and Dockerfile installs it at build time.
- `fix_plan_contract.md:3` already defines action sort keys (severity → subscription → publication → table → type); `add_table_to_publication` before `widen_column_filter` is not an undisclosed requirement.
- M2 `sub_ghost` test enforces exactly two `missing_table` codes and no `missing_column` (`test_m2.py:201-203`); agent failures there are implementation bugs, not spec gaps.
- Non-canonical `eclipse-temurin` base is digest-pinned and justified for JDK 21 + `kotlinc`; advisory only.
- Declared `hard` vs observed 40% medium tier is informational (#45), not a revision blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | M1 tests require `targetTables` sorted alphabetically by `(schema, name)`, but contract and instruction omit this rule | `steps/milestone_1/tests/test_m1.py:123-126` input order widgets→events; `:140-143` expects events→widgets. `environment/docs/snapshot_contract.md:7` only says subscriptions sorted by name, not `targetTables` order. `entire-report.txt:68-72,95-100` — 3/6 M1 failures | Add explicit `targetTables` sort rule to `snapshot_contract.md` and/or M1 instruction (e.g. sorted by schema then table name), matching existing test expectation |

*No other High blockers verified. Medium test-strengthening items (JSON table `schema` field, fixture subscription shape) recommended but not unfair to agents.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M1 tests never assert `schema` on top-level table JSON objects (ChatGPT High; test-quality review) | Partially agree | `environment/docs/snapshot_contract.md:3` requires `schema` on table objects. `test_m1.py:46-47,133,173` look up tables by `name` only; no `t["schema"]` assert. SQLite `schema_name` is checked (`test_m1.py:64-70`). Real coverage gap; agents are not failing on this; not a fairness blocker |
| 2 | Fixture subscription JSON only checks `name`, not `publication`/`targetTables` (ChatGPT High) | Partially agree | `test_m1.py:54` asserts name only. SQLite `subscription_tables` rows fully verified (`test_m1.py:82-89`). Weak JSON assertion; not causing agent failures |
| 3 | `targetTables` must be alphabetically sorted — tested but undocumented (ChatGPT High; entire-report Pattern 1) | Agree | See blocker #1. `test_m1.py:140-143` vs `snapshot_contract.md:7` |
| 4 | `missing_column` suppression for absent publisher tables is underspecified (ChatGPT Medium) | Disagree as blocker | `test_m2.py:201-203` requires `ghost_codes == ["missing_table", "missing_table"]` with no `missing_column`. `validation_contract.md:9` orders publisher-schema `missing_table` before column checks. Test defines behavior; agent failures are implementation errors |
| 5 | Plan action ordering `add_table_to_publication` before `widen_column_filter` is ambiguous (ChatGPT Medium) | Disagree | `fix_plan_contract.md:3`: sort by severity, subscription, publication, table, then type. `add_table_to_publication` < `widen_column_filter` alphabetically. `test_m3.py:78-83` matches contract |
| 6 | Rubric `# Rubric 1`–`3` format wrong for non-milestone task (user question) | Disagree | `task.toml:14` `number_of_milestones = 3`. Milestone tasks require `# Rubric N` blocks per `docs/guidelines/rubrics.md:53-64`. Format is correct |
| 7 | Non-canonical JDK base image is a blocker (harbor review warning) | Disagree | `environment/Dockerfile:1` digest-pinned `eclipse-temurin:21-jdk-jammy`. Kotlin/JDK 21 + system `kotlinc` is credible justification; advisory only |
| 8 | #14 unpinned pip / #20 pytest not in image (automated review) | Disagree | `environment/requirements.lock:1-2` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; `Dockerfile:29-30` installs at build. `test.sh` has no pip/apt install |
| 9 | LLMaJ instruction sufficiency FAIL (entire-report) | Disagree as blocker | Failures decompose into documented agent bugs + one real spec gap (targetTables sort). Author comment (`entire-report.txt:500-506`) aligns with artifact review |
| 10 | Declared `hard` vs 40% pass rate (entire-report medium) | Partially agree | `task.toml:6` `difficulty = "hard"`; worst model 40% → medium tier. Not a revision blocker per review policy |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone instruction is 1–3 short paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first tone; contracts referenced not inlined | `steps/milestone_1/instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no heavy markdown | milestone instructions |
| 4 | CHECK | No step by step instructions | Describes outcomes, not dev steps | milestone instructions |
| 5 | CHECK | No hints or solving strategies | WHAT not HOW; normative docs only | milestone instructions |
| 6 | CHECK | No design doc style tables | No input/output mapping tables | milestone instructions |
| 7 | CHECK | Instruction is well specified | Clear CLI flags, outputs, contract refs | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic Postgres logical-replication gate | task domain |
| 9 | CHECK | Instruction is unique | Postgres pub/sub column-filter Kotlin CLI is distinct | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_1/instruction.md:1,3` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder slug in instructions | milestone instructions |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | milestone instructions |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Lock file uses `==` | `environment/requirements.lock:1-2` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:25d1276...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY only env paths | `environment/Dockerfile:29-40` |
| 17 | CHECK | Environment does not contain solution or ground truth | Examples are count summaries only | `environment/examples/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages | pytest in image; test.sh runs pytest only | `Dockerfile:29-30`, `steps/milestone_1/tests/test.sh:16` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet | solve scripts patch Kotlin locally | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle is reflective of instruction | solve1/2/3 implement parse/validate/plan logic | solution scripts |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block | `steps/milestone_1/tests/test.sh:4-22` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | test_m*.py, test.sh |
| 26 | CHECK | Verifier applies binary rewards only | 0/1 reward.txt | test.sh |
| 27 | UNCHECK | All tests aligned with instructions | `targetTables` alphabetical sort tested but not in contract/instruction | `test_m1.py:140-143`, `snapshot_contract.md:7` |
| 28 | CHECK | Tests check for correctness, not just format | Exact behavioral assertions on JSON/SQL/SQLite | test_m1/2/3.py |
| 29 | CHECK | Tests verify behavior, not implementation | No source grepping | test_m*.py |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Contract-required message substrings need exact match | `test_m2.py:121-125` |
| 31 | CHECK | Tests have informative names or docstrings | All test methods documented | test_m1/2/3.py |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 8 negatives across 3 blocks | `entire-report.txt:510-536` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores ±1,2,3,5 | platform rubric |
| 34 | CHECK | Each rubric criterion one Agent line | 22 Agent lines | platform rubric |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific parse/validate/plan behaviors | platform rubric |
| 36 | CHECK | Rubric uses positive language | Standard Agent …, ±N format | platform rubric |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | platform rubric |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | platform rubric |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP refs | platform rubric |
| 40 | CHECK | All required files present | Milestone layout: env Dockerfile, steps/, task.toml | task tree |
| 41 | UNCHECK | No unnecessary files in parent directory | Stray `Untitled` duplicates entire submission report | `Untitled` (539 lines) |
| 42 | CHECK | author_name and author_email present | Fields set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | kotlin/sql/json, data-processing, db_interaction | `task.toml:7-11` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 40% → medium tier | `task.toml:6`, `entire-report.txt:6-7` |
| 46 | CHECK | steps/ layout present | 3 milestones under steps/ | `steps/milestone_*` |
| 47 | CHECK | Each milestone has solveN.sh | solve1.sh, solve2.sh, solve3.sh | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has test_mN.py | test_m1/2/3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test scoped to that milestone | M1 parse only; M2 validate; M3 plan | test file contents |
| 50 | CHECK | Tests NOT baked into Docker image | .dockerignore excludes tests/ | `environment/.dockerignore:16-17` |
| 51 | CHECK | Solution not accessible in environment | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Input is read-only domain data | `environment/input/` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst model 40% | `entire-report.txt:6-7` |
| 55 | UNCHECK | Task not too hard or unfair | Undocumented `targetTables` sort causes systematic M1 failures | blocker #1, `entire-report.txt:68-72` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 41, 45, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Tables sorted by schema then name | `test_parse_public_fixture_*` | covered | `snapshot_contract.md:3`, `test_m1.py:45` |
| `targetTables` sorted alphabetically | `test_parse_runtime_sql_*` | phantom | `test_m1.py:140-143`; not in `snapshot_contract.md:7` |
| Table objects include `schema`, `name`, `columns`, `replicaIdentity` | M1 JSON tests | gap | contract `:3`; JSON tests omit `t["schema"]`; SQLite covers `schema_name` |
| Subscription objects: name, publication, targetTables | M1 fixture test | partial | `test_m1.py:54` name only; SQLite rows full (`:82-89`) |
| Suppress `missing_column` when publisher schema lacks table | `test_validate_runtime_catalog_reports_missing_publication_table` | covered | `test_m2.py:201-203` |
| Plan actions sorted per contract | `test_plan_runtime_validation_action_order_*` | covered | `fix_plan_contract.md:3`, `test_m3.py:78-83` |
| Diagnostic ordering within result | M2 edge tests | covered | `validation_contract.md:9`, `test_m2.py:218-219` |
| `publishedColumns`/`subscriberColumns` sorted | M2 fixture/runtime | covered | `test_m2.py:109-110,172` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, milestone layout, metadata |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | #14 |
| `environment/docs/snapshot_contract.md` | blocker #1, spec alignment |
| `environment/docs/validation_contract.md` | claim 4 adjudication |
| `environment/docs/fix_plan_contract.md` | claim 5 adjudication |
| `steps/milestone_1/tests/test_m1.py` | blocker #1, claims 1–3 |
| `steps/milestone_2/tests/test_m2.py` | claim 4 |
| `steps/milestone_3/tests/test_m3.py` | claim 5 |
| `entire-report.txt` | agent stats, rubric, LLMaJ, test-quality |
| `Untitled` | #41 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate build-postgres-publication-column-filter-compatibility-gate-kotlin-sql-json/
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: milestone
WARNING: pinned_dependencies — false positive (lock file uses ==)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | — |
| terminus-claude-opus-4-8 | 40.0% (2/5) | — |
| oracle | 100.0% (3/3) | platform only |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone Kotlin/Postgres task; report matches folder |
| 1 Instruction | ☑ | Concise; contract refs; targetTables sort missing |
| 2 Environment | ☑ | Digest-pinned JDK; tmux/asciinema; pytest baked in |
| 3 Oracle | ☑ | Not run locally; platform 100%; solve scripts derive output |
| 4 Verifiers | ☑ | Canonical reward block; no runtime installs; one phantom sort rule |
| 5 Metadata | ☑ | Complete; hard vs 40% noted |
| 6 Rubric | ☑ | Correct milestone `# Rubric 1–3` format; 8 negatives |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL overstated; Pattern 1 confirmed |
| 8 Novelty & fairness | ☑ | targetTables sort unfair; other failures agent-attributable |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task — the Kotlin/Postgres replication domain is well chosen, the three-stage progression makes sense, the Dockerfile is digest-pinned with verifier deps baked in, and agent pass rates look appropriately challenging. The milestone rubric blocks are formatted correctly with good negative coverage.

One fix before acceptance: Milestone 1 tests expect `targetTables` inside each subscription to be sorted alphabetically (by schema then table name), but that ordering rule isn’t written in `snapshot_contract.md` or the M1 instruction. Three agent runs failed M1 purely on sort order while getting the table set right — please document that rule to match the existing test. While you’re at it, consider asserting `schema` on JSON table objects and full subscription JSON shape in M1 tests, and delete the stray `Untitled` report copy from the task folder.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
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
