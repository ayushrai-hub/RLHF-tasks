# Terminus Review Report: `go-tab-settle-optimizer`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Go min-cost-flow optimizer task with excellent anti-cheat (runtime adversarial datasets, independent optimality checker, digest-pinned offline env) and correct non-milestone rubric format (29 positive pts). One real High blocker: `format.md` states the GX1/GL1 checksum formula mod 36 but never explicitly says the `<check>` field is a single base-36 character (`0123456789abcdefghijklmnopqrstuvwxyz`), causing a documented agent failure (`strconv.Atoi` on `"y"`). ChatGPT corridor/max-transfer and Dockerfile findings are not blockers; missing test docstrings are quality fixes only.

**Insights (concise):**

- GX1/GL1 check encoding is the only spec gap that drove a systematic agent failure (ErK6jfv); corridor fee=204 vs 180 is algorithmic, not instructional.
- Platform rubric is flat (no `# Rubric 2+` headers), 29 positive points, 4 negatives — correct for `number_of_milestones = 0`.
- Worst-model pass rate 20% (Claude Opus 4.8) → hard tier; GPT-5.5 at 100% does not block (#54).
- Bundled `rules.json` omits empty corridor/forbidden arrays — optional clarity, not a blocker.
- Oracle not run locally (Docker daemon unavailable); static review of `solve.sh` shows real SPFA MCF implementation.
- Two pytest functions lack docstrings (validator warning) — fix before submit but not disposition-driving.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | GX1/GL1 `<check>` field encoding under-specified: formula says mod 36 but text never states check is a single base-36 alphabet character, not a decimal integer | `format.md:64-65,77-78` — `GX1:…:<payload_base36>:<check>` with `(n*29+…) mod 36` but no alphabet sentence; example `GX1:team-01:team-02:f6:j` uses letter `j`; `test_outputs.py:68-69` asserts `parts[4].lower() == ALPHABET[expected]`; `entire-report.txt:64-66,76-78` documents ErK6jfv `strconv.Atoi()` failure on base-36 check `"y"` | Add one explicit sentence for GX1 and GL1: the `<check>` field is exactly one character from `0123456789abcdefghijklmnopqrstuvwxyz` equal to `ALPHABET[(formula) mod 36]` |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | GX1/GL1 check digit encoding under-specified — check is base-36 character not decimal (ChatGPT High) | **Agree** | `format.md:64-65` names `payload_base36` but only `<check>` without encoding rule; `test_outputs.py:68-69` enforces `ALPHABET[expected]`; agent ErK6jfv failed per `entire-report.txt:64-66` |
| 2 | Corridor/max-transfer behavior sufficiently specified (ChatGPT Medium None) | **Agree** | `format.md:31-36,73-88` — `max_transfer_cents` caps default lane; GL1 tokens add parallel lanes with independent `lane_max_units`/`lane_fee_delta`; `test_outputs.py:82-96` models same semantics |
| 3 | Optional: empty `forbidden_pairs`/`corridor_*` arrays in bundled rules.json (ChatGPT Low) | **Agree (Low only)** | `rules.json:1-4` has only two fields; `format.md:21-28` documents full schema with examples — omission is cosmetic |
| 4 | Optional: parametrize `test_plans_are_valid_and_optimal` (ChatGPT Low / entire-report suggestion) | **Agree (Low only)** | `test_outputs.py:274-276` loops all datasets in one test — diagnostic improvement, not correctness |
| 5 | Dockerfile FROM digest-pinned, no base-image blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` — `golang:1.24-bookworm@sha256:1a6d4452…` digest-pinned official image |
| 6 | Non-canonical base image warning (entire-report WARNING #2) | **Disagree as blocker** | Digest-pinned official Go image is acceptable; no canonical-list violation demonstrated |
| 7 | Bundled rules.json missing corridor fields (entire-report WARNING #1) | **Partially agree (Low)** | Same as claim #3 — schema shown in `format.md`, adversarial data in `test.sh` exercises fields |
| 8 | Instruction sufficiency FAIL for GX1 check ambiguity (entire-report LLMaJ) | **Agree** | Consistent with claim #1 and `entire-report.txt:76-78` |
| 9 | Corridor failures are algorithm bugs not spec gaps (entire-report §4) | **Agree** | 3/4 trials failed fee=204 vs 180; `task_specification: pass` on those trials; `format.md:73-88` lane semantics sufficient |
| 10 | Rubric uses milestone format on non-milestone task (user question) | **Disagree** | `task.toml:14` `number_of_milestones = 0`; platform rubric in `entire-report.txt:335-349` is flat `Agent …, ±N` with no `# Rubric 2+` — matches `rubrics.md:66` |
| 11 | Rubric positive total >40 (user concern) | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 29/40 PASS |
| 12 | `#36` rubric negative phrasing blocker (auto review) | **Disagree** | Negatives (`Agent ignores…, -3`) are penalty criteria; rule #36 targets positive-score lines phrased as “does not do X, +1” — all positives use affirmative phrasing in `entire-report.txt:335-344` |
| 13 | `#41` stray `audit-report.md` (auto review) | **Disagree** | Reviewer-generated artifact from `./scripts/terminus audit`, not author submission content |
| 14 | Missing test docstrings (#31) | **Agree (Low)** | `test_outputs.py:267,274` — no docstrings; validator warns; required by `writing-tests.md` but not spec-fairness blocking |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~189 words, compact prose | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt | Conversational fix-the-optimizer framing | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | One JSON example only | `instruction.md` |
| 4 | CHECK | No step by step instructions | No HOW walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States WHAT/outcomes; warns greedy fails without solve steps | `instruction.md:23-28` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | GX1/GL1 check encoding gap | `format.md:64-78` |
| 8 | CHECK | Instruction is interesting | Realistic settlement optimization scenario | task content |
| 9 | UNCHECK | Instruction is unique | Cannot verify vs corpus | — |
| 10 | CHECK | All paths absolute | `/app/...` paths throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | Dockerfile no web content grab | No runtime fetch | `environment/Dockerfile` |
| 14 | CHECK | Python deps pinned | `pytest==8.2.0` | `environment/Dockerfile:13-14` |
| 15 | CHECK | Base image digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context scoped | `COPY task_file/` only | `environment/Dockerfile:21` |
| 17 | CHECK | No solution/ground truth in env | Broken greedy starter only | `settler.go:9-11` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; `test.sh` no installs | `Dockerfile:13-14`, `test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Docker daemon unavailable locally | oracle run failed |
| 22 | CHECK | Oracle no internet | `solve.sh` builds locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Writes SPFA MCF Go sources, compiles, runs | `solution/solve.sh` |
| 24 | CHECK | test.sh reward path | Writes `0` on failure, pytest exit captured | `test.sh:4-5,211-221` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `test.sh`, `test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0/1 via reward.txt | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Tests enforce base-36 check char not stated in spec | `test_outputs.py:68-69`, `format.md:64-65` |
| 28 | CHECK | Tests check correctness | MCF optimality + settlement invariants | `test_outputs.py:212-264` |
| 29 | CHECK | Behavior not implementation | No source grep | `test_outputs.py` |
| 30 | CHECK | No brittle exact matching | Structural/algorithmic asserts | `test_outputs.py` |
| 31 | UNCHECK | Informative test docstrings | 2 functions missing docstrings | `test_outputs.py:267,274` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:346-349` |
| 33 | CHECK | Rubric scores in allowed set | All ±1,2,3,5 | `entire-report.txt:335-349` |
| 34 | CHECK | Rubric Agent format | 15 properly formatted lines | `entire-report.txt:335-349` |
| 35 | CHECK | Rubric detailed; ≤40 positive | 29 positive pts | rubric-points output |
| 36 | CHECK | Rubric positive language | Negatives appropriately phrased; positives affirmative | `entire-report.txt:335-349` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:335-349` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:335-349` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:335-349` |
| 40 | CHECK | Required files present | All core files exist | task tree |
| 41 | CHECK | No unnecessary parent files | No jobs/README/data in task dir | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Go optimization/JSON task | `task.toml:7-10` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"` | `task.toml:6` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:14` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:14` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:14` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth | No solution in image | `environment/Dockerfile:21` |
| 52 | CHECK | Input not trivially hackable | Checksum verify + runtime adversarial gen | `test.sh:20,43+` |
| 53 | CHECK | Git clones pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤80% | `entire-report.txt:36-37` |
| 55 | UNCHECK | Not too hard/unfair | GX1 check ambiguity caused fair agent failure | `entire-report.txt:64-66` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 31, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/plan.json` schema | `test_plan_files_exist`, `validate_settlement` | covered | `instruction.md:4-7`, `test_outputs.py:219-221` |
| Exact zero settlement, debtor→creditor | `validate_settlement` | covered | `instruction.md:10-14`, `test_outputs.py:239-261` |
| Multiples of `settlement_unit_cents` | `validate_settlement` | covered | `instruction.md:12`, `test_outputs.py:238` |
| Unique pairs, forbidden pairs | `validate_settlement` | covered | `instruction.md:12-13`, `test_outputs.py:241-243` |
| Lane capacities (default + GL1) | `validate_settlement`, `lanes_for` | covered | `instruction.md:13-14`, `test_outputs.py:243,82-96` |
| Sorted transfers | `validate_settlement` | covered | `instruction.md:14`, `test_outputs.py:250` |
| Minimize `settlement_fee_units` (global optimum) | `validate_settlement` | covered | `instruction.md:16`, `test_outputs.py:263-264` |
| Fee model in `format.md` (base, GX1, GL1, rebate) | `optimal_fee`, `cheapest_pair_fee` | covered | `instruction.md:16-18`, `test_outputs.py:47-209` |
| GX1 check = base-36 character of mod-36 result | `decode_gx` | **gap** | `format.md:64-65` lacks encoding rule; `test_outputs.py:68-69` enforces `ALPHABET[expected]` |
| GL1 check = base-36 character of mod-36 result | `decode_gl` | **gap** | `format.md:77-78` same gap; `test_outputs.py:77-78` |
| Nonzero exit on malformed tokens | `test.sh` bad-token case | covered | `instruction.md:19-20`, `test.sh:181` |
| Nonzero exit on infeasible settlement | `test.sh` infeasible case | covered | `instruction.md:19-20`, `test.sh` |
| Adversarial hidden datasets | `test.sh` generator + 6 datasets | covered | `instruction.md:23-25`, `test_outputs.py:10-16` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-6, #10-11, spec alignment |
| `environment/task_file/docs/format.md` | Blocker 1, claims 1/8, #7, #27, #55 |
| `environment/task_file/input/rules.json` | Claim 3 |
| `environment/Dockerfile` | #13-16, #20, claim 5 |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec alignment |
| `tests/test.sh` | #20, #52, adversarial generation |
| `solution/solve.sh` | #22-23 |
| `task.toml` | #42-45, #46-49 N/A, rubric format |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, claim adjudication |
| `audit-report.md` | Automated 55-item baseline |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-tab-settle-optimizer/ ===
Summary: 0 error(s), 2 warning(s), 2 info
Warnings: test_plan_files_exist() and test_plans_are_valid_and_optimal() missing docstrings
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Not worst-model |
| terminus-claude-opus-4-8 | 20.0% (1/5) | Worst-model; corridor MCF modeling |
| oracle | 100.0% (3/3) | Per platform report; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test: `test_plan_files_exist` 9/9; `test_plans_are_valid_and_optimal` 6/9.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular Go task; `number_of_milestones = 0`; report matches folder |
| 1 Instruction | ☑ | One High spec gap (GX1/GL1 check encoding) |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema, pytest in image |
| 3 Oracle | ☐ | Not executed — Docker unavailable; static review PASS |
| 4 Verifiers | ☑ | Strong MCF optimality checker; missing docstrings only |
| 5 Metadata | ☑ | Fields complete; category/tags reasonable |
| 6 Rubric | ☑ | Flat non-milestone format; 29 pts; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL on GX1 check confirmed |
| 8 Novelty & fairness | ☑ | Multi-step optimizer; check-digit gap unfair to one agent pattern |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid optimizer task — the min-cost-flow objective, runtime adversarial datasets, independent fee recomputation, and pinned offline Go environment are all in great shape. The rubric format and point totals look correct for a non-milestone submission. One fix needed before accept: in `/app/docs/format.md`, please add an explicit sentence for both GX1 and GL1 that the `<check>` field is a single base-36 character from `0123456789abcdefghijklmnopqrstuvwxyz` (the mod-36 checksum value encoded as one digit), not a decimal integer. An agent reasonably parsed it as decimal and failed on letter checks like `"y"`. Optional polish: add one-line docstrings to the two pytest functions.

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
