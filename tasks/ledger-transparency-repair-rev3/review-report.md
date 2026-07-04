# Terminus Review Report: ledger-transparency-repair-rev3

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | not executed (Harbor CLI error locally; submission report: 100% 3/3) |
| **CHECK count** | 54 |
| **UNCHECK count** | 1 |

**Error categories (internal):** Milestones, Metadata Issues

**Decision (concise):** Strong three-milestone ledger transparency task — digest-pinned Ruby/C environment, robust per-milestone tests, correct milestone rubric format (# Rubric 1–3, 15/23/20 pts per block). One real blocker: `task.toml` retains forbidden top-level `[agent]` and `[verifier]` sections alongside per-step timeouts. ChatGPT’s “Revise for stale explanation fields” and “rubric >40” claims are not blockers per Edition 2 rules.

**Insights (concise):**
- Milestone task with correct platform rubric shape (`# Rubric 1`, `# Rubric 2`, `# Rubric 3`); per-block positives 15/23/20 — not a non-milestone rubric mismatch.
- Author explanation fields in export describe an unrelated PostgreSQL/pyproject task — context-only, not a revision blocker.
- Worst-model pass rate 60% (GPT-5.5); Claude 100%; tier medium; not too easy.
- M2 agent failures traced to C return-code convention (0=success); inferable from starter `ledger_verify.c:31` — optional clarity note, not High.
- Digest-pinned `ruby:3.3-slim-bookworm` justified for Rack + native C; non-canonical base is advisory only.
- `./scripts/terminus validate` fails on `task.toml` structure before other checks.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Milestones, Metadata Issues | #43 | Milestone task has forbidden top-level `[agent]` and `[verifier]` blocks; per-milestone timeouts already exist under `[[steps]]` | `task.toml:24-28` duplicates `steps/milestone_*/[steps.agent]` and `[steps.verifier]` at `task.toml:33-55`; validator: `Milestone tasks must not have top-level [agent]` | Remove lines 24–28 (`[verifier]` and `[agent]` top-level sections). Keep only `[steps.agent]` / `[steps.verifier]` per `[[steps]]`. |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High severity: none; task structure/oracle/tests sound (ChatGPT) | Agree | `allow_internet=false` `task.toml:22`; digest-pinned FROM `environment/Dockerfile:1`; no COPY tests/solution `environment/Dockerfile:28-32`, `environment/.dockerignore:19-20`; oracle derives answers `steps/milestone_1/solution/solve1.sh:4-40`; report oracle 100% `entire-report.txt:24` |
| 2 | Medium: stale Difficulty/Solution/Verification explanations for unrelated PostgreSQL task (ChatGPT) | Disagree (not a blocker) | Export lines 1–12 describe pyproject/PostgreSQL; task is C/Ruby ledger. `docs/guidelines/submission-export-format.md`: author explanations are **context only — not normative** |
| 3 | Low: add explicit C return 0=success in M2 instruction (ChatGPT) | Partially agree (optional) | Tests assert `rc == 0` `test_m2.py:52,85,126,135`; starter uses `return … ? 0 : -1` `environment/native/ledger_verify.c:31`; not stated in `steps/milestone_2/instruction.md` — borderline, agents failed M2 at 80% |
| 4 | Low: split M3 monolithic test (ChatGPT / test-quality report) | Partially agree (optional) | Single test `test_m3.py:47-97`; diagnostics only, not fairness/security gap |
| 5 | Low: add `$PWD = "/"` guard to step test.sh (ChatGPT / review report) | Partially agree (optional) | `steps/milestone_*/tests/test.sh` lack guard; `WORKDIR /app` set `environment/Dockerfile:24` |
| 6 | Non-canonical Ruby base image is warning (entire-report review) | Disagree (not a blocker) | Digest-pinned `environment/Dockerfile:1`; Ruby/Rack + native C requires Ruby runtime; credible justification per `docs/reviewer-checklist-full.md` canonical-base rule |
| 7 | Rubric positive total 58 > 40 (misspelled-folder auto-review) | Disagree | Milestone task `number_of_milestones=3` `task.toml:9`; per-block: #1=15, #2=23, #3=20 `entire-report.txt:380-413`; cap is **per milestone block** per `docs/guidelines/rubrics.md:32` |
| 8 | Non-milestone task in milestone rubric format (user question) | Disagree (N/A) | Task **is** milestone (`number_of_milestones=3`); rubric correctly uses `# Rubric 1`, `# Rubric 2`, `# Rubric 3` — correct shape per `docs/guidelines/submission-export-format.md:63-64` |
| 9 | Instruction sufficiency FAIL — return-code spec gap (entire-report) | Partially agree (not blocker) | Convention inferable from `ledger_verify.c:31`; both agents failed M2 on inverted returns; single Medium → accept-with-note per severity rules |
| 10 | LLMaJ behavior_in_tests / behavior_in_task_description PASS | Agree | Verified M1–M3 instructions map to `test_m1.py`, `test_m2.py`, `test_m3.py` assertions |
| 11 | Test quality ROBUST all milestones (entire-report) | Agree | Independent oracles in `ledger_expected.py`; live HTTP in M3; adversarial forged rows in M2 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction is 1–2 paragraphs when scored **per file** (149/223/181 words); automated sum of 553 across three files is wrong for milestone layout | `steps/milestone_*/instruction.md`; `docs/guidelines/milestones.md:37-39` |
| 2 | CHECK | Natural prompt tone | Engineer voice; no “You are an expert…” | `steps/milestone_1/instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Only `#` title headers; no tables/bold dumps | all milestone instructions |
| 4 | CHECK | No step-by-step HOW | Requirements only; no command walkthrough | all milestone instructions |
| 5 | CHECK | No hints/strategies | Describes outputs/contracts, not solve script | all milestone instructions |
| 6 | CHECK | No design-doc tables | No I/O mapping tables in instructions | all milestone instructions |
| 7 | CHECK | Well specified | Clear outputs, paths, schemas | M1 `/app/output/ceremony_rules.json`; M3 `validation_report.json` schema |
| 8 | CHECK | Interesting | Realistic crypto/ledger transparency repair scenario | task content |
| 9 | CHECK | Unique | No duplicate in repo; corpus check N/A | — |
| 10 | CHECK | Absolute paths | All paths `/app/...` | all milestone instructions |
| 11 | CHECK | Task name not in instruction | No task slug in text | grep clean |
| 12 | CHECK | No canary string | No canary patterns | grep clean |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:16-18` |
| 15 | CHECK | FROM digest-pinned | `@sha256:e76733e…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only under env | `environment/Dockerfile:28-32` |
| 17 | CHECK | No ground truth in env | BUG markers only; no golden answers in docs | `environment/native/ledger_verify.c:9-78` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts OK | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest/gems in Dockerfile; test.sh no installs | `environment/Dockerfile:16-20`; `steps/milestone_1/tests/test.sh:5` |
| 21 | CHECK | Oracle passes | Submission oracle 100% 3/3; solutions compute outputs | `entire-report.txt:24`; `solve1.sh`, `solve2.sh`, `solve3.sh` |
| 22 | CHECK | Oracle offline | No network in solve scripts | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle not hardcoded | M1 builds JSON from notice; M2 rebuilds .so; M3 live HTTP | `solve1.sh:8-40`; `solve2.sh`; `solve3.sh:5-7` |
| 24 | CHECK | reward.txt canonical | Binary 0/1 on pass/fail | `steps/milestone_1/tests/test.sh:8-12` |
| 25 | CHECK | Same logic oracle/agent | No `/oracle` branching | grep clean in `steps/` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `test.sh` reward block |
| 27 | CHECK | Tests aligned with instructions | All asserted behaviors stated in milestone instructions | spec↔test table §5 |
| 28 | CHECK | Correctness not format-only | Crypto verify, chain root, live API | `test_m2.py:80-138`; `test_m3.py:71-94` |
| 29 | CHECK | Behavior not implementation grep | ctypes/HTTP behavior tests | `test_m2.py`, `test_m3.py` |
| 30 | CHECK | Not brittle where flexible | Exact JSON fields required by spec | instructions define exact keys |
| 31 | CHECK | Informative docstrings | All 13 `test_*` have docstrings | grep `def test_` + docstrings |
| 32 | CHECK | ≥3 negative rubric criteria | Three negatives (-3, -5, -3) | `entire-report.txt:389,402,413` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines valid scores | `entire-report.txt:380-413` |
| 34 | CHECK | Agent …, ±N format | 29 formatted lines | `entire-report.txt:380-413` |
| 35 | CHECK | Rubric detailed; point cap OK | Per-block 15/23/20 ≤40 | `entire-report.txt:380-413` |
| 36 | CHECK | Positive phrasing | Negatives use negative scores | e.g. line 389 `-3` |
| 37 | CHECK | No /tests/ refs in rubric | Clean | `entire-report.txt:380-413` |
| 38 | CHECK | No task.toml/instruction refs | Clean | rubric section |
| 39 | CHECK | No oracle/NOP in rubric | Clean | rubric section |
| 40 | CHECK | Required files present | Milestone layout complete | `steps/milestone_{1,2,3}/`, `environment/Dockerfile`, `task.toml` |
| 41 | CHECK | Clean parent directory | No stray author files (audit-report is reviewer artifact) | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | UNCHECK | All metadata fields correct | Top-level `[agent]`/`[verifier]` forbidden on milestone tasks | `task.toml:24-28`; validate errors |
| 44 | CHECK | Tags/category match | `security`, `long_context`, `api_integration`; languages C/Ruby/Bash; minor `rails` tag imprecision (Rack not Rails) — single Medium note only | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `difficulty=hard`; platform medium; worst-model 60% — informational mismatch only | `task.toml:6`; `entire-report.txt:14-20` |
| 46 | CHECK | steps/ milestone layout | Three milestones under `steps/` | directory tree |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | Present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | M1 JSON only; M2 native only; M3 API/report only | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests not in image | `.dockerignore` + no COPY | `environment/.dockerignore:20`; `Dockerfile` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/tests | `environment/.dockerignore:19-20` |
| 52 | CHECK | No trivial input cheat | Tests recompute from fixtures/oracle | `ledger_expected.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:18-20` |
| 55 | CHECK | Not unfair | Agents pass M1/M3; M2 failure is convention not missing env | `entire-report.txt:30-43` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 43 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: write `/app/output/ceremony_rules.json` with template keys | `test_output_exists`, `test_required_top_level_keys` | covered | `test_m1.py:14-22` |
| M1: exact enum tokens (hmac-sha256, memo_normalization, chain formulas) | `test_signing_contract`, `test_chain_and_receipt_contract` | covered | `test_m1.py:24-63` |
| M1: key rotation from notice JSON | `test_key_rotation_and_bootstrap` | covered | `test_m1.py:36-51` |
| M1: authoritative_docs list | `test_authoritative_docs` | covered | `test_m1.py:65-72` |
| M2: pipe canonicalization + memo/time/amount rules | `test_canonicalization_matches_fixture` | covered | `test_m2.py:73-78` |
| M2: Ed25519 + HMAC verify, forged/wrong-key rejection | `test_valid_fixture_signatures_verify`, `test_forged_rows_rejected`, `test_wrong_key_for_posted_at_rejected` | covered | `test_m2.py:80-110` |
| M2: chain root from v3 genesis digest | `test_chain_root_matches_independent_recompute` | covered | `test_m2.py:112-138` |
| M3: validation_report.json schema + live API agreement | `test_validation_report_and_api` | covered | `test_m3.py:47-97` |
| M3: rcpt-HBR- receipt prefix, string seq | same | covered | `test_m3.py:53-60,77-81` |
| C return 0 on success (implicit from starter code) | all M2 `assert rc == 0` | covered (implicit) | `test_m2.py:52`; `ledger_verify.c:31` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker 1, #43, #45 |
| `environment/Dockerfile` | #13-20, #15 |
| `environment/.dockerignore` | #50, #51 |
| `environment/native/ledger_verify.c` | Claim 3, #17, spec gap adjudication |
| `steps/milestone_1/instruction.md` | #1-12, §5 |
| `steps/milestone_2/instruction.md` | #1-12, §5 |
| `steps/milestone_3/instruction.md` | #1-12, §5 |
| `steps/milestone_*/tests/test.sh` | #20, #24-26 |
| `steps/milestone_*/tests/test_mN.py` | #27-31, #49, §5 |
| `steps/milestone_*/solution/solveN.sh` | #21-23 |
| `entire-report.txt` | §3, §7, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml [task.toml]: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
Summary: 2 error(s), 0 warning(s)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures on M2 |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) | per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only — not a blocker) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `ledger-transparency-repair-rev3`; milestone layout; export matches ledger task (explanations stale but irrelevant) |
| 1 Instruction | ☑ | Per-milestone prompts concise; absolute paths; no hints |
| 2 Environment | ☑ | Digest-pinned Ruby slim; tmux/asciinema; deps pinned; no tests/solution in image |
| 3 Oracle | ☑ | Solutions derive; report 100%; local oracle not run (Harbor config error) |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; docstrings; behavior tests |
| 5 Metadata | ☐ | **Blocker:** top-level agent/verifier in task.toml |
| 6 Rubric | ☑ | Milestone format correct; 15/23/20 per block; 3 negatives |
| 7 LLMaJ & agents | ☑ | 60% worst model; M2 return-code pattern; not too easy |
| 8 Novelty & fairness | ☑ | Multi-step crypto repair; anti-cheat solid |
| 9 Long context | ☑ | `incident_transcript.md` ~473KB; subcategory `long_context` valid |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the three-milestone progression, hidden graded tests, and pinned Ruby/C environment all look great, and the platform rubric is correctly split across three milestone blocks with sensible point totals. One fix before we can accept: remove the top-level `[agent]` and `[verifier]` sections from `task.toml` (lines 24–28). Milestone tasks should only declare timeouts under each `[[steps]]` block, which you already have. Optional polish if you want: add one sentence to Milestone 2 that exported C functions return 0 on success, and refresh the submission explanation fields so they describe this ledger task instead of the old PostgreSQL packaging write-up.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Milestones | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |
