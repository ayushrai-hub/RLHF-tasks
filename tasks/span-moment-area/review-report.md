# Terminus Review Report: span-moment-area

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (local Docker unavailable); platform report shows oracle 3/3 |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Rubric, Test Alignment/Coverage Issues

**Decision (concise):** Core task quality is strong (environment pinning/offline setup, verifier depth, and hard difficulty profile). Two real blockers remain: the platform rubric text is for a different task domain/CLI, and one tested requirement (byte-identical reruns) is not explicitly stated in the instruction/spec docs. Fix those two items and re-submit.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric criteria target a different task (`beam-moment` with `--span`, `span_id`, `beam_digest`) instead of this task (`beam-envelope` with `--stage`, `beam_id`, `report_digest`). | `entire-report.txt` (rubric lines), `instruction.md`, `environment/docs/contract.md` | Replace platform rubric with task-specific criteria tied to staged `.beam` flow, provenance/envelope fields, amendment semantics, failure cleanup, and digest behavior. |
| 2 | High | Test Alignment/Coverage Issues | #27, #55 | Tests require byte-identical output across repeated invocations, but this deterministic/idempotent rerun requirement is not explicitly stated in instruction/spec docs. | `tests/test_outputs.py` (`test_byte_identical_regeneration`), `instruction.md`, `environment/docs/report-format.md`, `environment/docs/contract.md` | Add an explicit requirement that repeated runs with unchanged inputs must produce byte-identical output (including cache serialization precision expectations). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Rubric is for wrong task (beam-moment/span fields) | Agree | `entire-report.txt` rubric lines reference `beam-moment`, `--span`, `span_id`, `beam_digest`; task artifacts use `beam-envelope`, `--stage`, `beam_id`, `report_digest` in `instruction.md` and `environment/docs/contract.md`. |
| 2 | Byte-identical regeneration tested but not explicitly documented | Agree | `tests/test_outputs.py` includes `test_byte_identical_regeneration`; no explicit rerun-byte-identical requirement text in `instruction.md` / `environment/docs/report-format.md` / `environment/docs/contract.md`. |
| 3 | `author_email = "anonymous"` is invalid metadata | Disagree | `docs/task-requirements.md` example explicitly uses `author_email = "anonymous"`. |
| 4 | `category = "scientific-computing"` non-standard/wrong | Disagree | `docs/task-type-taxonomy.md` lists `scientific-computing` as a valid category. |
| 5 | `subcategories = []` is invalid | Disagree | `docs/task-requirements.md` states subcategories can be empty. |
| 6 | Oracle must write `/app/output/envelope_report.json`; current `/tmp` path is blocker | Partially agree | `instruction.md` says grading expects `/app/output/envelope_report.json`; `solution/solve.sh` writes `/tmp/envelope_simple.json`. This is a quality mismatch but not a demonstrated high-severity blocker because verifier rebuilds and runs binary independently. |
| 7 | `tests/test.sh` missing CTRF artifact is blocker | Partially agree | Canonical examples include `--ctrf` in `docs/guidelines/writing-tests.md`; current `tests/test.sh` omits it but still writes reward and runs pytest correctly. Treat as improvement/warning, not core blocker here. |
| 8 | Non-milestone task should not use milestone rubric format | Disagree (no issue found) | Rubric is a flat `Agent ..., ±N` list (no `# Rubric 2+` blocks), which matches non-milestone format requirements in `docs/guidelines/rubrics.md`. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | # | Decision | # | Decision | # | Decision | # | Decision |
|---|----------|---|----------|---|----------|---|----------|---|----------|
| 1 | CHECK | 12 | CHECK | 23 | CHECK | 34 | CHECK | 45 | CHECK |
| 2 | CHECK | 13 | CHECK | 24 | CHECK | 35 | UNCHECK | 46 | UNCHECK |
| 3 | CHECK | 14 | CHECK | 25 | CHECK | 36 | CHECK | 47 | UNCHECK |
| 4 | CHECK | 15 | CHECK | 26 | CHECK | 37 | CHECK | 48 | UNCHECK |
| 5 | CHECK | 16 | CHECK | 27 | UNCHECK | 38 | CHECK | 49 | UNCHECK |
| 6 | CHECK | 17 | CHECK | 28 | CHECK | 39 | CHECK | 50 | CHECK |
| 7 | CHECK | 18 | CHECK | 29 | CHECK | 40 | CHECK | 51 | CHECK |
| 8 | CHECK | 19 | CHECK | 30 | CHECK | 41 | CHECK | 52 | CHECK |
| 9 | UNCHECK | 20 | CHECK | 31 | CHECK | 42 | CHECK | 53 | CHECK |
| 10 | CHECK | 21 | CHECK | 32 | CHECK | 43 | CHECK | 54 | CHECK |
| 11 | CHECK | 22 | CHECK | 33 | CHECK | 44 | CHECK | 55 | UNCHECK |

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 27, 35, 46, 47, 48, 49, 55 |

---

## 5. Reviewer note (copy-paste to portal)

Strong task overall: pinned/offline environment, real source rebuild, and high-signal physics/staging tests make this a solid hard C++ debugging challenge. Two things to fix before acceptance: the platform rubric currently describes a different beam-moment/span task, and one tested behavior (byte-identical reruns) is enforced in tests but not clearly stated in the written spec. Once the rubric is rewritten for this task and determinism is explicitly documented, this should be ready.

---

## 6. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2 |

