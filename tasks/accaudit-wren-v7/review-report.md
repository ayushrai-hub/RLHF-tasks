# Terminus Review Report: `accaudit-wren-v7`

**Generated:** 2026-06-27 (manual accuracy audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/accaudit-wren-v7`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | Medium |
| **Validation** | pass |
| **Oracle** | pass (report: 100%, 3/3) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** none

**Decision (concise):** Task artifacts are structurally sound: digest-pinned Ubuntu/Wren build, offline verifier with hash-pinned pytest in the image, strong perturbation anti-cheat, and full spec↔test alignment. ChatGPT’s AutoEval build-failure Revise call is not supported by static artifact review (Dockerfile installs deps correctly; FAQ treats intermittent AutoEval as resubmit). Automated `./scripts/terminus review` false positives on #20 (pytest via `requirements.txt`) and #54 (miscomputed “worst model” as max not min) are overturned. Platform rubric is flat (correct for non-milestone), not milestone-block format.

**Insights (concise):**

- `worst_model_rate()` in `review_checklist.py` uses `max()` pass rates, falsely flagging #54 at 100% (GPT-5.5) instead of Claude Opus 4.8 at 20%.
- `#20` automation only greps `pytest` inside `Dockerfile` text; misses `pip3 install -r requirements.txt` which pins `pytest==8.3.2`.
- Portal rubric (lines 312–331 of `entire-report.txt`) is a single flat list — correct for `number_of_milestones = 0`; not incorrectly split into milestone blocks.
- AutoEval `Build status: FAILED` could not be reproduced locally (Docker daemon unavailable); static Dockerfile review shows no defect.
- Instruction is dense (6 paragraphs) but every rule is tested; LLMaJ `behavior_in_task_description` and `behavior_in_tests` both pass.
- 20 `/app/examples/` TSV files are generous hints but not instruction-mandated; informational only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | AutoEval build FAILED — must Revise before acceptance (ChatGPT) | Partially agree | `entire-report.txt:309-310` reports failure; static `environment/Dockerfile:1-44` digest-pins Ubuntu, pins wren-cli commit `18553636618a4d33f10af9b5ab92da6431784a8c`, installs hash-pinned pytest via `requirements.txt`; `task.toml:27` `allow_internet = false`; LLMaJ + harbor review (`entire-report.txt:132-142,257-262`) all pass. Local docker build not run (daemon down). `docs/faq.md:183,230` — intermittent AutoEval → resubmit, not a design defect. |
| 2 | Dependencies baked in image; verifier offline; `allow_internet = false`; test.sh no runtime installs (ChatGPT strengths) | Agree | `task.toml:27`; `tests/test.sh:13` only invokes pytest; `environment/Dockerfile:40-41` `pip3 install --require-hashes -r /tmp/requirements.txt`; `environment/requirements.txt:13-14` `pytest==8.3.2` |
| 3 | Non-canonical Ubuntu base needs justification (harbor review warning) | Agree (non-blocking) | `environment/Dockerfile:19-24` credible Wren compile justification; digest-pinned |
| 4 | Verifier timeout 1800s disproportionate (harbor review warning) | Agree (non-blocking) | `task.toml:17` `timeout_sec = 1800.0`; perturbation runs 10 small seeds (`tests/test_outputs.py:350`); tuning to ~600s suggested but not blocking |
| 5 | 20 example TSV files reduce difficulty (harbor suggestion) | Partially agree | `environment/app/examples/` has 20 files; not referenced as required in `instruction.md`; informational |
| 6 | `#20` pytest not in Dockerfile (automated review) | Disagree | `environment/Dockerfile:40-41` installs `requirements.txt`; `environment/requirements.txt:13-14` contains `pytest==8.3.2` |
| 7 | `#54` worst-model 100% too easy (automated review) | Disagree | `entire-report.txt:24-25` Claude 20%, GPT-5.5 100%; per `docs/guidelines/difficulty.md:12` rejected only when worst-performing model >80%; Claude at 20% passes #54 |
| 8 | LLMaJ behavior_in_task_description / behavior_in_tests PASS | Agree | `entire-report.txt:133-134`; manual spot-check of all 12 error codes + interest rules in `instruction.md:3-11` vs `tests/test_outputs.py` |
| 9 | Non-milestone task uses milestone rubric format | Disagree | `task.toml:9` `number_of_milestones = 0`; portal rubric (`entire-report.txt:312-331`) has no `# Rubric 2+` blocks — flat list per `docs/guidelines/rubrics.md:60` |
| 10 | Rubric references `/tests/` (potential #37 fail) | Disagree | Line reads “under /tests or /solution” (`entire-report.txt:325`) — no `/tests/` path with trailing slash; `./scripts/terminus rubric-validate` passes |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 6 paragraphs; dense spec (~600+ words) exceeds 3-paragraph guideline | `instruction.md:1-11` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Reads as formal audit specification, not conversational prompt | `instruction.md:1-11` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States WHAT (rules/output), not HOW to implement | `instruction.md` |
| 5 | CHECK | No hints or solving strategies in instruction | No detection guidance or walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | All 12 codes, interest rules, paths, sort order explicit | `instruction.md:1-11` |
| 8 | CHECK | Instruction is interesting | Real financial audit + niche Wren language | — |
| 9 | UNCHECK | Instruction is unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | All paths absolute | `/app/audit.wren`, `/app/audit_report.json`, `/app/transactions.tsv` | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction.md | No “accaudit-wren-v7” string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | Dockerfile no runtime web fetch in env code | Build-time git clone only; app shipped locally | `environment/Dockerfile` |
| 14 | CHECK | Python deps pinned with == and hashes | `requirements.txt` uses `--hash=sha256:` pins | `environment/requirements.txt:1-18` |
| 15 | CHECK | Base image digest-pinned | Both stages `@sha256:0d39fcc8…` | `environment/Dockerfile:1,25` |
| 16 | CHECK | Build context within environment/ | Only `COPY app/`, `requirements.txt` | `environment/Dockerfile:40-44` |
| 17 | CHECK | Environment has no ground truth answers | Examples are partial inputs, not audit JSON answers | `environment/app/examples/` |
| 18 | CHECK | No privileged/dangerous Docker | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not conflict with Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest via Dockerfile pip install; test.sh only runs pytest | `environment/Dockerfile:40-41`, `tests/test.sh:13` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:29` |
| 22 | CHECK | Oracle no internet/downloads | `solve.sh` writes Wren + runs `wren_cli` | `solution/solve.sh:359` |
| 23 | CHECK | Oracle reflects instruction (not hardcoded) | Full ~360-line Wren computation | `solution/solve.sh:4-359` |
| 24 | CHECK | test.sh writes reward.txt with failure path | Canonical 0/1 block | `tests/test.sh:4-18` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:15-18` |
| 27 | CHECK | Tests aligned with instructions | All 12 codes, interest subtleties, sort order covered | `tests/test_outputs.py`, `instruction.md` |
| 28 | CHECK | Tests check correctness not format-only | Perturbation + reference deep-compare | `tests/test_outputs.py:339-380` |
| 29 | CHECK | Behavior tests not implementation grep | No source-code grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching on detail | `reference.normalize()` drops `detail` | `tests/test_outputs.py:326-334`, `tests/reference.py:7-8` |
| 31 | CHECK | Tests have docstrings | All `test_*` functions documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics ≥3 negatives | N/A — no `rubric.txt` in task folder (portal-side only) | — |
| 33 | UNCHECK | Rubric scores ±1,2,3,5 | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed/precise | N/A (portal rubric validates locally when extracted) | `entire-report.txt:312-331` |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ references | N/A in folder; portal rubric OK on manual read | `entire-report.txt:325` |
| 38 | UNCHECK | Rubric no metadata/instruction refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP mentions | N/A | — |
| 40 | CHECK | Required files present | All present | task root |
| 41 | CHECK | No unnecessary parent files | Clean layout | — |
| 42 | CHECK | author_name/email in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | category, difficulty, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | `languages = ["wren"]`, `category = "data-processing"` | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches agent rates | `hard` defensible: Claude 20% ≤20% per `difficulty.md` | `entire-report.txt:24-25`, `task.toml:6` |
| 46 | UNCHECK | Milestone steps/ layout | N/A `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked into image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:12`, `environment/Dockerfile` |
| 51 | CHECK | Solution/answers not accessible in env | `solution/` and `tests/` in `.dockerignore` | `environment/.dockerignore:11-12` |
| 52 | CHECK | Agent cannot trivially cheat via input mutation | Perturbation restores schedule; 10-seed reference compare | `tests/test_outputs.py:339-380` |
| 53 | CHECK | Git repos pinned to commit | `git checkout 18553636618a4d33f10af9b5ab92da6431784a8c` | `environment/Dockerfile:14` |
| 54 | CHECK | Not too easy (>80% worst model) | Claude worst at 20% — not rejected tier | `entire-report.txt:24-25` |
| 55 | CHECK | Not too hard/unfair | 2/4 agent trials perfect; failures were timeout/syntax loops, not spec gaps | `entire-report.txt:85-129` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 2, 9, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| MISSING_FIELD (<6 tab fields) | `test_missing_field_flagged`, `test_missing_field_count` | covered | `instruction.md:3`, `tests/test_outputs.py:115-121` |
| BAD_TXN_ID (T + 9 digits) | `test_bad_txn_id_flagged`, `test_bad_txn_id_count` | covered | `instruction.md:3`, `tests/test_outputs.py` |
| BAD_ACCT_ID (AC + 6 digits) | `test_bad_acct_id_*` | covered | `instruction.md:3` |
| BAD_DATE (valid YYYYMMDD, ≤2026-06-13) | `test_bad_date_*`, `test_cutoff_date_inclusive_not_flagged` | covered | `instruction.md:3`, `tests/test_outputs.py` |
| BAD_AMOUNT decimal rules | `test_bad_amount_*` | covered | `instruction.md:3` |
| BAD_TYPE / BAD_CURRENCY | `test_bad_type_*`, `test_bad_currency_*` | covered | `instruction.md:3` |
| DUPLICATE_TXN / FEE_OVERCAP | `test_duplicate_txn_*`, `test_fee_overcap_*` | covered | `instruction.md:5` |
| OVERDRAFT / HIGH_VELOCITY | `test_overdraft_*`, `test_high_velocity_*` | covered | `instruction.md:7` |
| BAD_INTEREST (Actual/Actual, per-day round, USD schedule, reset) | `test_bad_interest_*`, `test_correct_interest_not_flagged`, `test_leap_year_interest_not_flagged`, `test_interest_reset_between_postings_not_flagged` | covered | `instruction.md:9`, `tests/test_outputs.py:250-286` |
| JSON schema + sort order | `test_each_record_has_required_keys`, `test_output_sorted_*` | covered | `instruction.md:11` |
| Must run via Wren (`/app/audit.wren`) | `test_audit_wren_script_exists`, `test_report_is_produced_by_wren_cli` | covered | `instruction.md:1`, `tests/test_outputs.py:70-82` |
| Anti-hardcoding | `test_zzz_perturbation_on_generated_holdouts` | covered | `tests/test_outputs.py:339-380` |
| Total errors = 19 on bundled fixture | `test_total_error_count` | covered | `tests/test_outputs.py:291-294` |

No spec gaps or phantom requirements found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #2, #7, #10, section 5 |
| `task.toml` | #45, #54, #46-49 N/A |
| `environment/Dockerfile` | #15, #20, blocker adjudication |
| `environment/requirements.txt` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #28, #31, section 5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | Agent stats, AutoEval, rubric, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: accaudit-wren-v7/ ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | `entire-report.txt:25` |
| terminus-claude-opus-4-8 | 20% (1/5) | 4 timeouts; `entire-report.txt:24,33` |
| oracle | 100% (3/3) | `entire-report.txt:29` |

| Metric | Value |
|--------|-------|
| Worst-model rate (lowest pass) | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; Wren data-processing; matches report |
| 1 Instruction | ☑ | Dense but complete; #1/#2 stylistic UNCHECK only |
| 2 Environment | ☑ | Digest pins, tmux, asciinema, offline, no tests/solution COPY |
| 3 Oracle | ☑ | Genuine Wren implementation; report 100% pass |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, perturbation anti-cheat |
| 5 Metadata | ☑ | `allow_internet = false`, hard difficulty justified |
| 6 Rubric | ☑ | Portal rubric flat (non-milestone correct); N/A in folder |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; failures = timeout not spec |
| 8 Novelty & fairness | ☑ | Multi-rule Wren + interest math; cheating paths closed |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task — the Wren audit spec is thorough, the perturbation test with an independent reference is excellent anti-cheat design, and the Dockerfile setup (digest-pinned Ubuntu, wren-cli from a pinned commit, pytest baked in via hash-pinned requirements) looks right. Oracle passes and agent stats support hard difficulty (Claude 20%). I didn’t find any real spec-test gaps or verifier issues. The AutoEval build failure in the submission summary doesn’t match what the artifacts show — if that persists on resubmit, flag the build ID to platform support per FAQ; it’s not a task-design fix from what I can see. Optional polish: trim verifier timeout from 1800s and consider whether 20 `/app/examples/` files are more hint than you want for hard tier.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no (style notes only, not blocking) | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Environment | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Uses Internet | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus review accaudit-wren-v7/ --report entire-report.txt` overturned on #20 and #54._
