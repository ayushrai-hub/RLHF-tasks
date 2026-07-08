# Terminus Review Report: migrate

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | Medium |
| **Validation** | warn |
| **Oracle** | not executed (docker daemon unavailable in this environment) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Test Build Issues, Rubric

**Decision (concise):** Task quality is generally strong (environment, anti-cheat setup, deterministic verifier shape, and difficulty calibration). However, the instruction leaves core semantics implicit while hidden exact-match tests enforce them, creating a fairness/spec-alignment blocker. The rubric also has only two negative penalties, and verifier tests are missing required docstrings.

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Instruction asks agents to infer behavior from examples, but hidden tests enforce strict semantics not explicitly documented as rules (notably missing-prerequisite staleness/propagation and ordering interactions in edge cases). | `instruction.md`; `tests/expected/missing_source_partial.txt`; `tests/expected/multi_phony_interleaved.txt`; `entire-report.txt` (analysis and repeated held-out failures while examples pass) | Add explicit normative rules section in `instruction.md` (staleness and tie-breaking semantics) so hidden exact-match outcomes are fully specified, not only inferred. |
| 2 | High | Test Build Issues | #31 | Verifier tests lack per-test docstrings. | `tests/test_outputs.py` | Add one-line docstrings to each `test_*` function. |
| 3 | High | Rubric | #32 | Platform rubric contains only 2 negative criteria; minimum is 3. | `entire-report.txt` rubric block (`# Rubric 1`) | Add at least one additional distinct negative penalty criterion. |

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Instruction omits critical staleness and ordering rules enforced by verifier (ChatGPT/high severity) | Partially agree | Missing-rule fairness concern is valid; however, some semantics are inferable from examples (`tiebreak_demo`, `same_second`, `phony_stamp`). The blocker remains because hidden exact-match behavior is still under-specified in instruction text. |
| 2 | Docker setup pinned/offline and generally sound (ChatGPT) | Agree | `environment/Dockerfile`; `task.toml` (`allow_internet = false`); `.dockerignore`. |
| 3 | Solution has unused order-only prerequisite handling (ChatGPT/low severity) | Agree | `solution/solve.sh` lines describing `&` prereqs; no `&` usage in provided `.mk` cases. |
| 4 | Non-milestone task may be in milestone rubric format (user check request) | Disagree | `task.toml` has `number_of_milestones = 0`; rubric has only `# Rubric 1`, which is allowed for non-milestone when no `# Rubric 2+` blocks exist (`docs/guidelines/rubrics.md`). |

## 4. Portal checkbox decisions (all 55)

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 8, 9, 21, 27, 31, 32, 46, 47, 48, 49, 55 |

## 5. Reviewer note (copy-paste to portal)

Nice task overall — the environment setup is clean and pinned, anti-cheat controls are good, and the verifier is deterministic. Before acceptance, please make the instruction fully explicit on the staleness/ordering semantics currently inferred from examples, since hidden exact-match cases depend on those details. Also add docstrings to all tests and include at least one more negative rubric criterion (currently 2; minimum is 3).