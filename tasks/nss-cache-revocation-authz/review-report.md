# Terminus Review Report: nss-cache-revocation-authz

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (platform export 100% 3/3; local run produced no Docker output) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Strong Go authorization-cache repair task with realistic multi-surface debugging, source-rebuild enforcement, generated scenario coverage, and durable disk/resume checks. Prior reviewer blockers (denial-reason precedence, operator-contract verifier leakage) are fixed in current artifacts. Platform rubric is correctly **flat** (non-milestone), 26 positive points, 4 distinct negatives. No blocking spec, test, environment, or rubric issues found.

**Insights (concise):**

- ChatGPT Accept verdict confirmed after full artifact re-audit; no High/Medium blockers.
- Prior `Reviewer Feedback` denial-reason and cheat-sheet issues are resolved in `trace-schema.md:15`, `cache-state.md:24`, `test_outputs.py:334`, and trimmed `operator-contract.md` (17 lines, no generated-scenario names).
- Non-milestone rubric uses correct **flat** `Agent …, ±N` layout — no `# Rubric 2+` milestone headers; 26/40 positive cap passes.
- Automated `terminus review` script false-positives on #31 (class docstring) and #36 (negative rubric lines) — audit AST-verifies all 8 `test_*` docstrings and rubric negatives correctly use `-N` scores.
- Declared `hard` vs platform `medium` is informational per difficulty policy; worst-model 60% is acceptable calibration; Claude 100% does not block (#54 uses worst model only).
- Eight integration tests (not seven as Harbor summary states) rebuild binary and generate inline scenarios — anti-cheat design is excellent.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High-severity blockers; denial-reason gap fixed (ChatGPT) | **Agree** | `trace-schema.md:13-15` precedence rule; `cache-state.md:24` `revoked-principal`; `test_outputs.py:334` pins `revoked-principal` only |
| 2 | No verifier leakage; operator-contract cheat paragraph removed (ChatGPT) | **Agree** | `operator-contract.md` ends at line 17 with public `run-case` workflow only; no generated scenario strings or scratch output paths |
| 3 | Focused Go codebase, source-rebuild, generated scenarios, durable state checks (ChatGPT) | **Agree** | `test_outputs.py:12-14` `build_binary()` every run; scenarios inline in each test; disk surface checks in `test_revocation_chain_keeps_disk_surfaces_coherent` |
| 4 | Flat non-milestone rubric 26 positive pts, distinct negatives (ChatGPT) | **Agree** | `entire-report.txt:278-290` — flat list, no `# Rubric 2+`; sum +2+3+3+5+3+3+2+2+3=26; 4 negatives at lines 287-290 |
| 5 | Dockerfile digest-pinned Go base acceptable (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:1a6d4452…`; no canonical Go t-bench image exists |
| 6 | Optional: task.toml `hard` vs platform MEDIUM (ChatGPT Low) | **Agree (Low, non-blocking)** | `task.toml:6` `hard`; `entire-report.txt:21` `Difficulty: ✅ MEDIUM`; policy: metadata mismatch never blocks |
| 7 | Optional: add class-level test docstring (ChatGPT / Harbor suggestion) | **Agree (Low, non-blocking)** | `TestAuthorizationCacheRevocation` at `test_outputs.py:199` lacks class docstring; all 8 `test_*` methods have docstrings |
| 8 | Prior reviewer: denial-reason accepts multiple reasons for sana revoke (Reviewer Feedback) | **Disagree (stale — fixed)** | `test_outputs.py:334` `assert denied["reason"] == "revoked-principal"`; spec precedence at `trace-schema.md:15` |
| 9 | Prior reviewer: operator-contract names generated scenario strings (Reviewer Feedback) | **Disagree (stale — fixed)** | `operator-contract.md` has no such paragraph; grep for `chain-mono`/`poisoned` in `environment/docs/` returns no matches |
| 10 | Harbor review non-canonical base image warning | **Agree (Low, non-blocking)** | `environment/Dockerfile:1`; digest-pinned official Go image justified |
| 11 | Harbor review instruction brevity warning | **Agree (Low, non-blocking)** | `instruction.md` 4 paragraphs ~262 words; appropriate for discovery-style debugging task |
| 12 | LLMaJ `behavior_in_task_description` PASS | **Agree** | `entire-report.txt:90`; cross-checked instruction + four spec docs |
| 13 | LLMaJ `behavior_in_tests` PASS | **Agree** | `entire-report.txt:91`; 8 tests cover refresh/revoke/resume/epoch/poisoned-index/disk coherence |
| 14 | LLMaJ `informative_test_docstrings` PASS | **Agree** | All 8 `test_*` at `test_outputs.py:200-668` have docstrings; class docstring absent (optional) |
| 15 | Test quality review ACCEPT | **Agree** | `entire-report.txt:243-246`; rebuild-from-source + exact decision/reason checks |
| 16 | Instruction sufficiency PASS (agent failures are execution gaps) | **Agree** | `entire-report.txt:67-68`; epoch reconciliation and nil-slice issues documented in `cache-state.md:22-24` |
| 17 | `#31` 1 test missing docstring (automated review script) | **Disagree** | Audit AST: all 8 `test_*` have docstrings; script likely flags class not method |
| 18 | `#36` rubric negative phrasing fail (automated review script) | **Disagree** | Negatives at `entire-report.txt:287-290` use `-5/-3/-2` scores; forbidden pattern is `Agent does not…, +N` |
| 19 | Non-milestone task uses milestone rubric format (user query) | **Disagree** | `task.toml:12` `number_of_milestones = 0`; platform rubric has no `# Rubric 2+` blocks — flat list per `docs/guidelines/rubrics.md:66` |
| 20 | Claude Opus 100% makes task too easy | **Disagree (non-blocking)** | `#54` uses **worst** model only; GPT-5.5 60% ≤80%; best-model rate does not alone block |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 4 prose paragraphs, ~262 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem narrative referencing contract docs, not synthetic walkthrough | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States repair goal + doc refs, not module-by-module steps | `instruction.md` |
| 5 | CHECK | WHAT not HOW hints | Defers contract to four spec docs; anti-cheat list is appropriate | `instruction.md:7` |
| 6 | CHECK | No design-doc tables in instruction | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Build command, binary path, output file, four normative docs | `instruction.md:5-6` |
| 8 | CHECK | Interesting | Realistic NSS-style auth cache / revocation / resume debugging | task content |
| 9 | CHECK | Unique | Specialized authzctl simulator with epoch/revocation/resume semantics; no duplicate in review scope | subjective |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/output/authorization-trace.json`, etc. | `instruction.md` |
| 11 | CHECK | No task name in instruction | Folder name absent | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline; `allow_internet = false` | `task.toml:23`, `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:` on golang base | `environment/Dockerfile:1` |
| 16 | CHECK | Build context scoped | COPY only under environment | `environment/Dockerfile:21-27` |
| 17 | CHECK | No ground truth in env | Docs are normative contract; Go source is buggy stub; no walkthrough answers | `environment/docs/`, no TODO/FIXME in source |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in venv via Dockerfile; test.sh no installs | `environment/Dockerfile:14-15`, `tests/test.sh:16-17` |
| 21 | CHECK | Oracle passes | Platform export: oracle 100% (3/3); local blocked (no Docker output) | `entire-report.txt:29-31` |
| 22 | CHECK | Oracle offline | solve.sh applies patch + make build only | `solution/solve.sh:4-6` |
| 23 | CHECK | Oracle derives output | Multi-file `fix.patch` touching refresh/runner/evaluator/store; not hardcoded trace | `solution/fix.patch` |
| 24 | CHECK | Canonical reward block | Writes 0/1 to reward.txt on pass/fail | `tests/test.sh:7,20-24` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All spec behaviors traced to tests; prior denial-reason gap fixed | sections 3, 5 |
| 28 | CHECK | Tests check correctness | Integration tests assert decisions, epochs, disk surfaces, resume equivalence | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Grading via authzctl subprocess + trace JSON; no source grep | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string matching | Exact denial reasons required by normative `trace-schema.md` | `trace-schema.md:13-15` |
| 31 | CHECK | Informative test names/docstrings | All 8 `test_*` have docstrings | `tests/test_outputs.py:200-668` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:287-290` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use allowed magnitudes | `entire-report.txt:278-290` |
| 34 | CHECK | Agent …, ±N format | 13 properly formatted lines | `entire-report.txt:278-290` |
| 35 | CHECK | Rubric detailed; positive cap | 26 positive pts (≤40); flat non-milestone list | `entire-report.txt:278-286` |
| 36 | CHECK | Positive rubric language | No `Agent does not…, +N` lines; negatives use `-N` | `entire-report.txt:287-290` |
| 37 | CHECK | Rubric avoids /tests/ | No pytest or /tests/ references | platform rubric |
| 38 | CHECK | Rubric avoids instruction.md/task.toml | References behavior and public paths only | platform rubric |
| 39 | CHECK | Rubric avoids oracle/NOP | No oracle/NOP mentions | platform rubric |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | security + go + nss-cache + authorization match content | `task.toml:6-10` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; worst-model 60% → medium tier (informational) | `task.toml:6`, `entire-report.txt:25-26` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/; `.dockerignore` excludes tests | `environment/Dockerfile`, `environment/.dockerignore:17` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/; no solution COPY | `environment/.dockerignore:16` |
| 52 | CHECK | Agent cannot trivially cheat | Rebuild from source + runtime-generated scenarios in `/tmp` | `test_outputs.py:12-14,31-32` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:25-26` |
| 55 | CHECK | Not unfair | Spec covers epoch reconciliation, nil-slice `[]`, denial precedence; agent failures are implementation | `cache-state.md:22-24`, `trace-schema.md:15`; `entire-report.txt:67-68` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build with `make -C /app/environment build` → `bin/authzctl` | all tests via `build_binary()` | covered | `test_outputs.py:12-14` |
| Output `/app/output/authorization-trace.json` with schema fields | implicit via `run_case` trace loads | covered | `instruction.md:5`; `trace-schema.md:3` |
| Proof-revision-mismatch fail-closed index | `test_chained_reject_reaccept_resume_coherence` | covered | `test_outputs.py:254,260` |
| Proof-expired-at-authorize per tick | `test_staggered_proof_expiry_multi_user` | covered | `test_outputs.py:292` |
| Revoked-principal when absent from snapshot | `test_staggered_proof_expiry_multi_user` | covered | `test_outputs.py:334` |
| Subject-generation-mismatch only when username present | `test_subject_lineage_dual_resume_boundaries` | covered | `test_outputs.py:451-455` |
| Resume ≡ monolithic run | `test_chained_*`, `test_quad_*`, `test_subject_lineage_*` | covered | `test_outputs.py:249-250,456-457,520-521` |
| Epoch counter / refresh_epoch stamping | `test_staggered_*`, `test_quad_*`, `test_group_shrink_*` | covered | `test_outputs.py:335-336,528-530,662` |
| Poisoned index/manifest epoch reconciliation on resume | `test_poisoned_index_and_manifest_epoch_recovery` | covered | `test_outputs.py:617-618` |
| Group shrink removes stale index (not revocation) | `test_group_shrink_removes_stale_group_index` | covered | `test_outputs.py:659-660` |
| Revocation chain disk surface coherence | `test_revocation_chain_keeps_disk_surfaces_coherent` | covered | `test_outputs.py:707-712` |
| Empty `groups` as `[]` not `null` on revoked entries | `test_revocation_chain_keeps_disk_surfaces_coherent` | covered | `test_outputs.py:707` |
| case_digest in provenance | `test_quad_resume_epoch_and_digest_continuity` | covered | `test_outputs.py:518-519` |
| epoch_start at resume boundary | `test_quad_resume_epoch_and_digest_continuity` | covered | `test_outputs.py:530` |
| Rejected refresh clears stale group index | `test_chained_*`, `test_replay_*` | covered | `test_outputs.py:260-261,387-388` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27 |
| `task.toml` | #45, #46-49 N/A |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/trace-schema.md` | blocker adjudication, #27, #30 |
| `environment/docs/cache-state.md` | blocker adjudication, #27 |
| `environment/docs/operator-contract.md` | verifier-leakage adjudication |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, #52 |
| `solution/solve.sh`, `solution/fix.patch` | #21-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate nss-cache-revocation-authz/
Summary: 0 error(s), 0 warning(s), 3 info

./scripts/terminus audit nss-cache-revocation-authz/ --report entire-report.txt
Verdict: APPROVED WITH WARNINGS (0 FAIL)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | worst model — sets tier |
| terminus-claude-opus-4-8 | 100.0% (5/5) | best model |
| oracle | 100.0% (3/3) | platform export |
| nop | 0.0% (0/1) | baseline |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

Per-test pass rates (lowest): `test_poisoned_index_and_manifest_epoch_recovery` 8/10, `test_revocation_chain_keeps_disk_surfaces_coherent` 9/10 — agent execution gaps (epoch reconciliation, nil-slice JSON), not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `nss-cache-revocation-authz` matches export; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise debugging prompt; four normative docs; no hints/leakage |
| 2 Environment | ☑ | Digest-pinned Go base; tmux+asciinema; deps in image; no tests/solution in image |
| 3 Oracle | ☑ | Patch-based repair; platform 100% 3/3 |
| 4 Verifiers | ☑ | 8 integration tests; reward block; rebuild-from-source; all test docstrings |
| 5 Metadata | ☑ | security/go tags fit; timeouts plausible |
| 6 Rubric | ☑ | Flat non-milestone; 26/40 positives; 4 negatives; no test/metadata refs |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; worst-model 60%; prior feedback issues fixed |
| 8 Novelty & fairness | ☑ | Multi-bug interrelated repair; cheating paths closed |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — it reads like a real authorization-cache repair job, not a toy exercise. The Go codebase is focused, the Docker setup is clean with a pinned base and verifier deps baked in, and the tests rebuild from source and run generated scenarios so shortcut fixes do not work. The prior spec issues around denial-reason precedence and the operator-contract cheat sheet are fixed, and I did not find remaining blocking gaps between the docs, tests, and environment. Optional polish only: a class-level docstring on the test class, and aligning declared difficulty with the observed medium calibration if you want metadata consistency.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
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
