# Terminus Review Report: `build-graph-acyclicity-proof`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass (0 errors, 1 info warning) |
| **Oracle** | pass (submission report 3/3; local run blocked by Docker socket) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** After re-reading all artifacts and adjudicating external findings, no High-severity blockers remain. The prior `test.sh` exit-code and CTRF claims are incorrect under Edition 2 canonical verifier rules. The platform rubric is a valid flat non-milestone rubric at 26 positive points (not 44). Environment, oracle, verifiers, anti-cheat, and difficulty calibration all meet the bar.

**Insights (concise):**

- `tests/test.sh` follows the canonical reward block; trailing `exit "$rc"` is explicitly **not** required (`docs/guidelines/writing-tests.md`, `docs/reviewer-checklist-full.md`).
- CTRF stub is copied before the root-workdir guard (`tests/test.sh:4-5`), so the early-exit path is covered.
- Dockerfile uses the **canonical** digest-pinned `node:22-bookworm-slim` image listed in `docs/guidelines/dockerfxile.md` — the Harbor review report’s `ghcr.io` complaint does not apply.
- Platform rubric: `# Rubric 1` header with flat `Agent …, ±N` lines is allowed for `number_of_milestones = 0` (`docs/guidelines/rubrics.md:66`); 26 positive points, 5 negatives.
- Agent failures on `test_s13_format_cycle_ordering_empty` reflect a hard normalization rule already in `/app/docs/format_spec.md:16`, not an instruction gap.
- Advisory only: e2e tests do not golden-assert driver topological `ordering` sequences (self-consistency hash only) — not a Revise blocker.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `test.sh` must add `exit "$rc"` after reward write (ChatGPT / prior Reviewer Feedback L1-4) | **Disagree** | `tests/test.sh:12-18` ends with reward block only. `docs/guidelines/writing-tests.md:29`: “no trailing `exit`”. `docs/reviewer-checklist-full.md:62`: “no trailing exit required”. `./scripts/terminus validate` info: “Trailing exit … unnecessary”. |
| 2 | CTRF missing on root-workdir early exit (prior Reviewer Feedback L4) | **Disagree** | `tests/test.sh:4-5` copies `ctrf_stub.json` before `PWD` check; reward `0` written at L4. |
| 3 | Non-canonical base image is Critical (entire-report Harbor review L148-171) | **Disagree** | `environment/Dockerfile:1` = `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` — exact canonical entry in `docs/guidelines/dockerfxile.md:10`. |
| 4 | Rubric positive total 44 / three milestone blocks (automated `terminus review` output) | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → **26** pts, single block `{1: 26}`. `entire-report.txt:443-458` sums 2+3+3+3+3+2+3+2+3+2 = 26. |
| 5 | Non-milestone task uses milestone rubric format (`# Rubric 1` header) | **Disagree** (not a blocker) | `task.toml:11` `number_of_milestones = 0`. `docs/guidelines/rubrics.md:66`: “`# Rubric 1` optional; no `# Rubric 2+` headers” for non-milestone. Only one header present. |
| 6 | pytest / pip deps not pinned or not in image (#14, #20 audit FAIL) | **Disagree** | `environment/requirements.txt:1-12` — `pytest==8.4.1` etc. with `--hash=sha256`. `environment/Dockerfile:16-17` installs into `/opt/verifier` at build time; `tests/test.sh` has no runtime installs. |
| 7 | Instruction sufficiency FAIL — `op_d` ordering override ambiguous (entire-report L62-89) | **Partially agree** (not a blocker) | Rule is normative in referenced `/app/docs/format_spec.md:16` (“empty array when cyclic”). Enforced by `test_s13_format_cycle_ordering_empty` (`tests/test_outputs.py:221-228`). `verification_contract.md:19-21` names `op_d` the canonical formatter. Agent near-misses are fairness calibration, not untested requirements. |
| 8 | Topological ordering only self-consistency checked (entire-report test-quality L327-361) | **Partially agree** (advisory) | `test_s16_e2e_primary_golden` (`tests/test_outputs.py:252-268`) uses `assert_report_consistency` only — no golden `ordering` array. Driver obligation at `verification_contract.md:35`. Coverage gap is Low/Medium quality note; joint-SAT, implicit edges, hash, and phase unit tests are strong. |
| 9 | Instruction extremely terse (Harbor review warning) | **Partially agree** (Low) | `instruction.md` is 6 lines but points to full contracts under `/app/docs/`. Acceptable for debugging/repair tasks with shipped specs. |
| 10 | Formulaic test docstrings (ChatGPT Low / Harbor suggestion) | **Partially agree** (Low) | All 23 `test_*` functions have docstrings (`tests/test_outputs.py:119+`); wording repeats test names. Not a High bar failure. |
| 11 | `solve.sh` lacks `set -euo pipefail` (Harbor warning) | **Partially agree** (Low) | `solution/solve.sh:1-3` — best practice only; oracle passes per report. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~89 words, 3 blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering brief, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | Single `#` title only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No walkthrough patterns | `instruction.md` |
| 5 | CHECK | No hints/strategies | WHAT + doc refs only | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, absolute paths, output schema | `instruction.md:3-5` |
| 8 | CHECK | Interesting | Realistic multi-module build-graph repair | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3 index | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | Slug not embedded in body text | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline env | `task.toml:23`, Dockerfile |
| 14 | CHECK | Pinned Python deps | `==` + hashes in requirements.txt | `environment/requirements.txt` |
| 15 | CHECK | FROM digest-pinned | `@sha256:f3a68cf4…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY scoped to env | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in env | Bugs intentional; no golden answers in docs | `environment/docs/` |
| 18 | CHECK | No privileged Docker | Standard run | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile venv; test.sh clean | `Dockerfile:16-17`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) in submission report | `entire-report.txt:28` |
| 22 | CHECK | Oracle no internet | patch only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | `oracle.patch` fixes modules, real computation | `solution/oracle.patch` |
| 24 | CHECK | reward.txt canonical block | Pre-write 0, update after pytest | `tests/test.sh:3-18` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | Major behaviors traced to docs + tests | §5 below |
| 28 | CHECK | Tests check correctness | Behavioral JS execution + golden hashes | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | Runs modules/pipeline, no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Structured JSON/graph asserts | `tests/test_outputs.py` |
| 31 | CHECK | Informative docstrings | All 23 tests documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives | `entire-report.txt:454-458` |
| 33 | CHECK | Rubric scores ∈ ±1,2,3,5 | Verified | `entire-report.txt:443-458` |
| 34 | CHECK | `Agent …, ±N` format | 15 lines | `entire-report.txt:443-458` |
| 35 | CHECK | Rubric detailed; ≤40 positives | 26 positive pts | `rubric-points` output |
| 36 | CHECK | Positive phrasing | No “does not” positives | rubric text |
| 37 | CHECK | Rubric no /tests/ refs | None | rubric text |
| 38 | CHECK | Rubric no metadata refs | None | rubric text |
| 39 | CHECK | Rubric no oracle/NOP | None | rubric text |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Metadata complete | Timeouts, category, tags | `task.toml` |
| 44 | CHECK | Tags/category applicable | JS build-graph / DAG task | `task.toml:7-9` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; worst-model 0% | `task.toml:6`, `entire-report.txt:18-24` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:11` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/` | `environment/.dockerignore:11` |
| 51 | CHECK | Solution not in image | `.dockerignore` excludes `solution/` | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially cheat | Fresh pipeline + module unit tests | `test_s14`, anti-cheat |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:23-24` |
| 55 | CHECK | Not unfair / too hard | Spec in shipped docs; 6/9 trials at 22/23 tests | `entire-report.txt:91-100` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output at `/app/output/results.json` with schema fields | `test_s14`, `test_s16`–`s19` | covered | `instruction.md:3-5`; `test_s14` |
| `op_a` implicit cross-branch edges + sharedResources filter | `test_s1`–`s3` | covered | `verification_contract.md:7-9` |
| `op_b` precedence, negation, whitespace, unknown id | `test_s4`–`s6`, `s22` | covered | `verification_contract.md:11-13` |
| `op_c` joint-SAT cycle witnesses | `test_s7`–`s10` | covered | `verification_contract.md:15-17` |
| `op_d` sort/normalize; cyclic `ordering` = `[]` | `test_s11`–`s13` | covered | `format_spec.md:16`; `test_s13:228` |
| `op_e` append merge semantics | `test_s20` | covered | `verification_contract.md:25` |
| `op_f` checkpoint digest invalidation | `test_s21` | covered | `verification_contract.md:27` |
| `op_g` bit-order enumeration | `test_s23` | covered | `verification_contract.md:29-31` |
| Driver topo sort alphabetical re-sort | — | gap (advisory) | `verification_contract.md:35`; e2e uses self-consistency only |
| Deterministic consecutive runs | `test_s15` | covered | `test_s15:242-250` |
| Fresh pipeline overwrites stale output | `test_s14` | covered | `test_s14:230-240` |
| signature_hash canonical algorithm | `test_s12`, `assert_report_consistency` | covered | `format_spec.md:24`; `test_s12:217-219` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, spec alignment |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-16, #20, #15 canonical base |
| `environment/requirements.txt` | #14 |
| `environment/.dockerignore` | #50-51 |
| `environment/docs/format_spec.md` | #27, claim 7 |
| `environment/docs/verification_contract.md` | #27, spec alignment |
| `tests/test.sh` | #24, claims 1-2 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh`, `solution/oracle.patch` | #21-23 |
| `entire-report.txt` | #45, #54, rubric #32-39, agent stats |
| `docs/guidelines/writing-tests.md` | claim 1 |
| `docs/guidelines/dockerfxile.md` | claim 3 |
| `docs/guidelines/rubrics.md` | claim 5 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate build-graph-acyclicity-proof
Summary: 0 error(s), 1 warning(s), 3 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | `entire-report.txt:24` |
| terminus-claude-opus-4-8 | 0.0% (0/5) | `entire-report.txt:23` |
| oracle | 100.0% (3/3) | `entire-report.txt:28` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; JS/Node |
| 1 Instruction | ☑ | Concise; refs normative docs |
| 2 Environment | ☑ | Canonical digest-pinned Node; tmux/asciinema; offline |
| 3 Oracle | ☑ | Patch-based; report 100% pass |
| 4 Verifiers | ☑ | Canonical test.sh; 23 behavior tests |
| 5 Metadata | ☑ | `number_of_milestones = 0`; category fits |
| 6 Rubric | ☑ | Flat rubric 26 pts; 5 negatives; `# Rubric 1` only — valid |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; sufficiency contested — ruled non-blocker |
| 8 Novelty & fairness | ☑ | Multi-module repair; anti-cheat solid |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall — the multi-phase JS repair work is well structured, the environment is pinned and offline with verifier deps baked into the image, and the 23-test suite exercises each phase module plus end-to-end pipeline behavior with good anti-cheat (fresh-run overwrite, held-out fixtures). Oracle passes cleanly and agent pass rates look right for hard difficulty.

The earlier revision note about `test.sh` needing `exit "$rc"` doesn’t apply under the current canonical verifier pattern — your script already writes reward correctly and ends at the reward block, which is what we want. CTRF pre-creation is also in place before the workdir guard.

Optional polish if you revisit: richer per-test docstrings, and a golden `ordering` assertion on one acyclic e2e scenario would close the only meaningful coverage gap in an otherwise strong verifier suite.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no (advisory topo-ordering gap only) | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Other | no | — |

---

*Review per `prompt.md`. Commands run: `validate`, `audit --report entire-report.txt`, `review --report entire-report.txt`, `rubric-points entire-report.txt`. Oracle not re-run locally (Docker socket permission).*
