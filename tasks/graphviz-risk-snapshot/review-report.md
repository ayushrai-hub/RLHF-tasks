# Terminus Review Report: `graphviz-risk-snapshot`

**Generated:** 2026-07-09 16:30 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/graphviz-risk-snapshot`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (false-positive `[[steps]]` count from comment line) |
| **Oracle** | not executed locally; platform report 100% (3/3) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** Oracle Solution Issues, Test Alignment/Coverage Issues

**Decision (concise):** This is a valid 3-milestone task with correct `# Rubric 1/2/3` platform rubric format and per-block positive caps (24/17/24, all ≤40). The real blockers are oracle/instruction misalignment on `GET /` readiness and weak M2/M3 verifier coverage for OSV-sourced advisory values, ISO-8601 `age`, M3 JWT rejection, and non-empty graph `edges`. Automated audit false-positives on pip pinning (#14), pytest baking (#20), instruction length (#1), and task-name (#11) were rejected after file review.

**Insights (concise):**

- Oracle scripts install global JWT middleware before any route and never register `GET /`, so unauthenticated readiness returns 401 while instructions require a readiness response (`steps/milestone_1/instruction.md:8`, `solve1.sh:22-43`).
- All three milestone test helpers swallow any `GET /` failure (including 401) and proceed after timeout — readiness is never asserted (`test_m1.py:22-28`, same pattern in `test_m2.py`, `test_m3.py`).
- M2 worker test checks dependency *names* (`submitted_names >= EXPECTED_DEPENDENCIES`) but not OSV `advisoryId` values or ISO-8601 `age` (`test_m2.py:108-119`).
- M3 has strong HMAC canonicalization checks but allows `edges: []` and does not reject missing/invalid JWTs (`test_m3.py:74-87`, `117-119`).
- Platform rubric uses correct milestone headers; summed total 65 is not a blocker — cap applies per `# Rubric N` block, not across blocks (`rubrics.md:29-33`).
- `task.toml` validator error `[[steps]] count (4)` is a tooling false positive: comment line 12 contains the literal `[[steps]]`; only three real step blocks exist (`task.toml:34-61`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Oracle Solution Issues | #23 | Oracle omits unauthenticated `GET /` readiness route; global JWT middleware returns 401 on `GET /` | `steps/milestone_1/solution/solve1.sh:22-43` (no `app.get('/')`; middleware first); same in `solve2.sh:31-53`, `solve3.sh:49-71`; contract at `steps/milestone_1/instruction.md:8`, `steps/milestone_2/instruction.md:8`, `steps/milestone_3/instruction.md:8` | Add `app.get('/', …)` **before** JWT middleware in all three oracle solve scripts |
| 2 | High | Test Alignment/Coverage Issues | #27, #28 | `GET /` readiness required in instructions but never asserted; startup helper retries on any exception (including 401) then continues | `test_m1.py:22-28` (`except Exception` on `urlopen('http://localhost:8080/')`); no assertion on status 200 | Assert `GET /` returns success (e.g. HTTP 200) in startup helper or dedicated test |
| 3 | High | Test Alignment/Coverage Issues | #27, #28 | M2 does not verify `advisoryId`/`age`/`severity` come from bundled OSV JSON; only non-empty strings | `test_m2.py:110-113`; instruction requires OSV identifier + ISO-8601 age (`steps/milestone_2/instruction.md:13-18`) | Load `/app/data/*.json`, build expected ID/timestamp sets; assert advisories match |
| 4 | High | Test Alignment/Coverage Issues | #27, #28 | M3 does not test JWT rejection; only valid-token acceptance | `test_m3.py:74-87` (no `token=None` or bad-token case); preamble requires strict JWT (`steps/milestone_3/instruction.md:2`) | Add POST/GET cases with missing and invalid JWT expecting 4xx |
| 5 | High | Test Alignment/Coverage Issues | #27, #28 | M3 allows empty `edges` array — vacuously passes structural check | `test_m3.py:117-119` (`all(...)` on empty list is True); instruction requires graph edges (`steps/milestone_3/instruction.md:12`) | Assert `len(edges) > 0` when findings exist, or assert expected edge count from ledger |

*Non-blockers (noted):* repeated cross-milestone preamble + `vulnerabilties` typo = Medium/Low cleanup; rubric `Agent's` apostrophe lines = format nit, not cap violation.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Oracle violates `GET /` readiness contract (ChatGPT / entire-report CRITICAL) | **Agree** | `solve1.sh:22-43` — JWT `app.use` before routes, no `GET /`; tests workaround at `test_m1.py:22-28` |
| 2 | M2 tests don't validate advisory values against OSV JSON (ChatGPT / TEST QUALITY) | **Agree** | `test_m2.py:110-113` — type/non-empty only; OSV IDs in `environment/data/lodash.json:4` unused by verifier |
| 3 | M2 `age` not validated as ISO-8601 (ChatGPT / TEST QUALITY) | **Agree** | `test_m2.py:112` — `isinstance(..., str) and advisory['age']` only |
| 4 | M2 POST persistence not verified with non-empty data (ChatGPT / TEST QUALITY) | **Partially agree** | `test_m2.py:87-92` POSTs `[]`; worker test indirectly covers persistence but auth test does not |
| 5 | M3 missing/invalid JWT never rejected (ChatGPT / TEST QUALITY) | **Agree** | `test_m3.py:74-87` — only valid-token path; M2 covers rejection at `test_m2.py:75-77` but M3 file does not |
| 6 | M3 `edges: []` passes (ChatGPT / TEST QUALITY) | **Agree** | `test_m3.py:117-119` — no `len(edges)` check |
| 7 | M3 worker CSV/JSON loading untested (ChatGPT / TEST QUALITY) | **Partially agree** | M3 does not assert all three dependency names in findings; M2 does at `test_m2.py:119` |
| 8 | Cross-milestone preamble leaks future deliverables (ChatGPT / entire-report WARNING) | **Agree** (Medium, not standalone blocker) | All three `instruction.md` lines 1-4 reference `solve2.js`, `solve3.js`, `worker.js` |
| 9 | Typo `vulnerabilties` (ChatGPT / LLMaJ typos) | **Agree** (Low) | `steps/milestone_1/instruction.md:3` (and M2/M3 line 3) |
| 10 | Rubric present in `# Rubric 1/2/3` format (ChatGPT) | **Agree — correct for milestone task** | `entire-report.txt:720-763`; `task.toml:13`, `number_of_milestones = 3` |
| 11 | Rubric positive total 65 exceeds 40 (automated script) | **Disagree as blocker** | Per-block: #1=24, #2=17, #3=24 — all ≤40 per `docs/guidelines/rubrics.md:29-33` |
| 12 | Non-milestone task wrongly using milestone rubric format (user question) | **Disagree** | Task is milestone layout (`steps/milestone_N/`, `number_of_milestones = 3`); `# Rubric N` headers are required |
| 13 | `#14` unpinned pip / `#20` pytest not in image (automated audit) | **Disagree** | `requirements.lock:26-35` pins `pytest==8.4.1`, `pyjwt==2.13.0`; `Dockerfile:19` installs lockfile in image |
| 14 | `#11` task name in instruction (automated audit) | **Disagree as blocker** | `graphviz-risk-snapshot` appears as normative JWT **issuer** constant (`instruction.md:11`), not gratuitous task-name leakage |
| 15 | `#1` instruction too long (automated audit) | **Disagree as blocker** | Each milestone file ~13 lines / ~150 words; 839-word count aggregates all three files + repeated preamble |
| 16 | `number_of_milestones != [[steps]]` (validate) | **Disagree — validator bug** | `task.toml:12` comment contains literal `[[steps]]`; `validate_task.py:183` uses naive `text.count("[[steps]]")` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction ~13 lines; not one bloated doc | `steps/milestone_1/instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational preamble + normative contract bullets | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | No heavy headers/tables | — |
| 4 | CHECK | No step-by-step HOW | States WHAT to build | — |
| 5 | CHECK | No hints/solving strategies | No walkthrough commands | — |
| 6 | CHECK | No design-doc tables | None present | — |
| 7 | CHECK | Well specified | Paths, JWT constants, schemas explicit | `steps/milestone_2/instruction.md:14-18` |
| 8 | CHECK | Interesting/useful | JWT API + worker + HMAC snapshot is realistic | — |
| 9 | UNCHECK | Unique vs corpus | Cannot verify from artifacts alone | — |
| 10 | CHECK | Absolute paths only | `/app/...` throughout | `steps/milestone_1/instruction.md:3,8` |
| 11 | CHECK | Task name not in instruction | Issuer string is normative JWT claim, not folder-name leak | `steps/milestone_1/instruction.md:11` |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No web content fetch in env | Offline data files only | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip dependencies | `requirements.lock` uses `==` pins | `environment/requirements.lock:26-35` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:f3a68cf41a855d...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY limited to env files | `environment/Dockerfile:21-23` |
| 17 | CHECK | No ground truth in env | Data files are inputs, not answers | `environment/data/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image | pytest/pyjwt via lockfile in Dockerfile | `Dockerfile:17-19` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally this session | platform oracle 100% in `entire-report.txt:30` |
| 22 | CHECK | Oracle no runtime network | Heredoc writes only | `solve1.sh` |
| 23 | UNCHECK | Oracle reflects instruction | Violates `GET /` readiness contract | `solve1.sh:22-43` |
| 24 | CHECK | reward.txt + failure path | Canonical block in each `test.sh` | `steps/milestone_1/tests/test.sh:13-17` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | milestone `test.sh` files |
| 26 | CHECK | Binary rewards 0/1 | `echo 0/1 > reward.txt` | `steps/milestone_1/tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Gaps: `GET /`, OSV values, M3 JWT reject, edges | §2 blockers 2–5 |
| 28 | UNCHECK | Tests check correctness | M2/M3 allow hardcoded/shape-only passes | `test_m2.py:110-113`, `test_m3.py:117-119` |
| 29 | CHECK | Behavior not implementation grep | HTTP/integration tests | `test_m1.py` |
| 30 | CHECK | No brittle string matching | Exact `{success:true}` is specified | `steps/milestone_1/instruction.md:12` |
| 31 | CHECK | Informative names or docstrings | Descriptive `test_*` names | `test_m2.py:72,96` |
| 32 | CHECK | ≥3 negative rubric criteria | 9 negatives across blocks | `entire-report.txt:731-763` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines comply | `entire-report.txt:720-763` |
| 34 | CHECK | Agent …, ±N format | `Agent's …` lines still start with Agent | `entire-report.txt:741` |
| 35 | CHECK | Rubric detailed; positive cap | Per-block 24/17/24 ≤40 | `entire-report.txt:720-763` |
| 36 | CHECK | Positive phrasing in rubric | Negatives use `-N` form | `entire-report.txt:731+` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:720-763` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | — |
| 39 | CHECK | Rubric no oracle/NOP refs | None | — |
| 40 | CHECK | Required files present | Milestone layout: Dockerfile, task.toml, per-step files | `graphviz-risk-snapshot/` tree |
| 41 | CHECK | Clean parent directory | No jobs/README in task folder | — |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/category match | JS/Express/JWT API task | `task.toml:9-19` |
| 45 | CHECK | Difficulty field present | `medium` in task.toml; worst-model 20% → hard tier (informational) | `task.toml:8`, `entire-report.txt:25-26` |
| 46 | CHECK | steps/ milestone layout | Three `steps/milestone_N/` dirs | — |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` + wrappers | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | `test_m1.py`, `test_m2.py`, `test_m3.py` | — |
| 49 | CHECK | Milestone tests scoped | Each file tests only its milestone endpoints | `test_m1.py` JWT only; `test_m3.py` graphviz |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth | Solution not in image | `environment/Dockerfile` |
| 52 | CHECK | Agent can't trivially mutate inputs | Standard read-only app data pattern | `environment/data/` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | — |
| 54 | CHECK | Not too easy | Worst-model 20% ≤80% | `entire-report.txt:25-26` |
| 55 | CHECK | Not too hard/unfair | Agents pass individual milestones; failures are contract precision | `entire-report.txt:37-43` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 23, 27, 28 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| `GET /` readiness (M1–M3) | `_start_server` only | **gap** | `test_m1.py:22-28` swallows 401 |
| POST `/api/advisory` JWT HS256/issuer/audience (M1) | `test_invalid_jwt_claims_are_rejected`, `test_valid_jwt_is_accepted` | covered | `test_m1.py:71-93` |
| Bare Authorization header (M1–M3) | all milestone tests | covered | `test_m1.py:60`, `test_m3.py:81` |
| `GET /api/jwt-token` issues token (M2) | `test_post_requires_a_valid_token_and_persists_advisories` | covered | `test_m2.py:79-82` |
| Worker loads CSV + per-dep JSON (M2) | `test_worker_fetches_and_submits_advisories_for_all_ledgered_dependencies` | partial | names checked `test_m2.py:119`; IDs not |
| `advisoryId` from OSV identifier (M2) | worker test | **gap** | `test_m2.py:110` non-empty only |
| `age` ISO-8601 (M2) | worker test | **gap** | `test_m2.py:112` |
| POST rejects missing JWT (M2) | `test_post_requires_a_valid_token_and_persists_advisories` | covered | `test_m2.py:75-77` |
| `GET /api/graphviz` schema + HMAC (M3) | `test_graphviz_snapshot_matches_canonical_payload` | covered | `test_m3.py:102-130` |
| `edges` describe risk graph (M3) | graphviz test | **gap** | `test_m3.py:117-119` allows `[]` |
| Strict JWT validation (M3) | token/advisory test | **gap** | `test_m3.py:74-87` valid token only |
| `generatedAt` ISO-8601 (M3) | graphviz test | covered | `test_m3.py:104-105` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/instruction.md` | GET / contract, JWT issuer, blocker 1 |
| `steps/milestone_2/instruction.md` | OSV/advisory schema, blocker 3 |
| `steps/milestone_3/instruction.md` | graphviz/edges/JWT preamble, blockers 4–5 |
| `steps/milestone_1/solution/solve1.sh` | Oracle GET / violation |
| `steps/milestone_2/solution/solve2.sh` | Oracle GET / violation |
| `steps/milestone_3/solution/solve3.sh` | Oracle GET / violation |
| `steps/milestone_1/tests/test_m1.py` | Readiness workaround, M1 JWT coverage |
| `steps/milestone_2/tests/test_m2.py` | M2 coverage gaps |
| `steps/milestone_3/tests/test_m3.py` | M3 coverage gaps |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | pip pinning, pytest baked |
| `environment/data/lodash.json` | OSV ID ground truth for gap analysis |
| `task.toml` | milestone metadata, false-positive validate error |
| `entire-report.txt` | agent stats, platform rubric, external reports |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml [task.toml]: number_of_milestones (3) != [[steps]] count (4)
WARNING: Each [[steps]] block should have name = "milestone_N"  (false alarm — names are correct)
```

Root cause: `task.toml:12` comment `must match the number of [[steps]] blocks` is counted by `validate_task.py:183`.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | worst model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | best model |
| oracle | 100.0% (3/3) | platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | medium |
| Platform classified | hard |
| Tier match (#45) | differ — informational only |

### Rubric positive points

| Field | Value |
|-------|-------|
| Per `# Rubric N` block | #1=24, #2=17, #3=24 |
| Cap | 40 per block (milestone task) |
| Status | PASS — no block exceeds 40 |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone JS/Express task; report matches folder |
| 1 Instruction | ☑ | Cross-milestone preamble noted (Medium); typo Low |
| 2 Environment | ☑ | Digest-pinned Node 22; pytest baked; offline |
| 3 Oracle | ☐ | GET / contract violated in all solveN scripts |
| 4 Verifiers | ☐ | M2/M3 correctness gaps; readiness not asserted |
| 5 Metadata | ☑ | `number_of_milestones=3` correct; validate false positive |
| 6 Rubric | ☑ | Milestone `# Rubric 1/2/3` format correct; caps OK |
| 7 LLMaJ & agent evidence | ☑ | ChatGPT/readiness + test-quality claims largely confirmed |
| 8 Novelty & fairness | ☑ | Multi-step API task; 20–40% pass rates appropriate |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone structure here — pinned Node base, offline OSV fixtures, and the M3 HMAC canonicalization test are well thought out. The main fix before acceptance: the oracle never serves unauthenticated `GET /` for readiness (JWT middleware blocks it), while all three milestone instructions require that route, and the startup helpers don't actually catch the mismatch. Please add `GET /` before auth in solve1/2/3 and assert it in tests. Also strengthen M2/M3 verifiers: check `advisoryId` and ISO-8601 `age` against the bundled JSON, reject missing/invalid JWTs in M3, and require non-empty `edges` when findings exist. Optional cleanup: trim the repeated preamble so each milestone only lists its own deliverables, and fix the `vulnerabilties` typo.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Oracle Solution Issues | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2, 3, 4, 5 |
| Instruction Styling | no (Medium note only) | — |
| Rubric | no | — |
| Milestones | no (layout correct) | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review graphviz-risk-snapshot/ --report entire-report.txt`._
