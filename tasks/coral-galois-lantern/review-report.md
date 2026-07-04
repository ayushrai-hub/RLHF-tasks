# Terminus Review Report: `coral-galois-lantern`

**Generated:** 2026-07-03 (manual enrichment)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/coral-galois-lantern`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 2 warnings) |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Rubric, Instruction Styling

**Decision (concise):** The Rust task artifacts (instruction, Dockerfile, verifier, oracle) are strong and difficulty-calibrated, but the **platform rubric is for a different Go milestone task** and uses milestone format on a non-milestone submission with 71 positive points (>40 cap). Add one explicit arbitrary-precision sentence to `instruction.md` so the hidden bignum requirement is derivable. Optional submission-form explanations also describe an unrelated telemetry task and should be corrected on resubmit.

**Insights (concise):**

- Platform rubric references `docs/measure-spec.md`, `big.Rat`, `go build`, and `# Rubric 1–3` — none of which exist in this Rust quintic task (`task.toml:9` `number_of_milestones = 0`).
- Verifier is excellent: fresh random batch, independent Python ground truth, 2^127 discriminant scaling, std-only and no-shell-out checks (`tests/test_outputs.py:334`, `469–474`).
- `#14` automated FAIL is a **false positive** — pytest packages are pinned with `==` in `environment/Dockerfile:26–28`.
- Sample input `environment/app/data/quintics.txt` uses small coefficients; agents cannot infer bignum need from env alone.
- Agent stats are consistent: 0/7 full passes vs per-test partial passes (e.g. `test_project_builds` 7/10) are different metrics.
- Digest-pinned Rust base is appropriate; Harbor review canonical-image warning is advisory only.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric describes an unrelated Go measurement/conversion milestone task, not Coral Galois Lantern | `entire-report.txt:314–347` — `docs/measure-spec.md`, `big.Rat`, `go build ./...`, `report subcommand`, `# Rubric 1–3` | Replace platform rubric with Coral-specific criteria: exact discriminant, arbitrary-precision arithmetic, pair-sum resolvent, irreducibility, Galois classification (C5/D5/F20/A5/S5), solvability, std-only Rust, no shell-outs |
| 2 | High | Rubric | #35 | Non-milestone task submitted with milestone rubric shape (`# Rubric 2`, `# Rubric 3`) | `task.toml:9` `number_of_milestones = 0`; `entire-report.txt:325`, `337`; `docs/guidelines/rubrics.md:66` — flat list required, no `# Rubric 2+` | Use flat `Agent …, ±N` list (optional single `# Rubric 1` only) |
| 3 | High | Rubric | #35 | Rubric positive point total 71 exceeds 40 cap for non-milestone | `./scripts/terminus rubric-points entire-report.txt` → 71 total, blocks `{1:23, 2:25, 3:23}` | Trim Coral rubric to ≤40 positive points total |
| 4 | Medium | Instruction Styling | #27, #55 | Arbitrary-precision requirement tested but not stated in instruction; sample data uses small coefficients | `instruction.md:3` says "exact discriminant" only; `tests/test_outputs.py:334` scales by `s ∈ 70–200` (disc × s^20); `469–474` requires \|disc\| > 2^127; `environment/app/data/quintics.txt:1–6` small ints; LLMaJ `entire-report.txt:91–97` | Add one sentence: fixed-width types (e.g. `i128`) are insufficient; implement arbitrary-precision integer arithmetic using Rust std only |

*Platform form text (optional explanations at `entire-report.txt:4–15`) describes an unrelated telemetry reconciliation task — correct on resubmit; not a task-zip artifact blocker.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Platform rubric unrelated to submitted Rust task (ChatGPT High) | **Agree** | `entire-report.txt:314–347` vs `instruction.md`, `task.toml` languages=`rust` |
| 2 | Submission metadata/explanations inconsistent (ChatGPT Medium) | **Agree** | `entire-report.txt:4–15` telemetry pipeline text; unrelated to quintic/Galois task |
| 3 | Agent-summary contradiction 0/7 vs some passes (ChatGPT Medium) | **Disagree** | `entire-report.txt:20` "Solvable (all tests passed by at least one agent run)" = per-test; `56` "0/7 complete passes" = full 12/12 suite — consistent |
| 4 | Instruction should call out arbitrary-precision (ChatGPT Medium) | **Agree** | `instruction.md:3`; `tests/test_outputs.py:334`, `469–474`; sample `quintics.txt` small coeffs |
| 5 | Optional: log verifier random seed (ChatGPT Low) | **Agree (non-blocking)** | `tests/test_outputs.py:364` `os.urandom(8)` with no stderr log |
| 6 | Optional: state reducible quintics solvable (ChatGPT Low) | **Partially agree** | `instruction.md:5` requires "correct … solvability results"; `test_outputs.py:519–529` enforces `True`; derivable by correct computation, explicit sentence would help |
| 7 | Dockerfile digest pinning OK (ChatGPT) | **Agree** | `environment/Dockerfile:7` `@sha256:9f841bbe…` |
| 8 | Non-canonical base image warning (Harbor report) | **Disagree as blocker** | Digest-pinned Rust base with documented compile-time justification `environment/Dockerfile:1–6`; no evidence image is wrong |
| 9 | `#14` unpinned pip (automated audit) | **Disagree** | `environment/Dockerfile:26–28` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` — audit false positive on multiline RUN |
| 10 | LLMaJ instruction sufficiency FAIL (bignum) | **Partially agree** | Bignum gap real; other behaviors well-specified per `entire-report.txt:127` |
| 11 | Harbor review "READY TO USE" | **Disagree for submission** | Ignores wrong platform rubric; task zip quality ≠ complete submission |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~175 words, 4 prose blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineering request, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only | `instruction.md` |
| 5 | CHECK | No hints/strategies | No algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | UNCHECK | Well specified | Bignum magnitude requirement not stated | `instruction.md:3`; blocker 4 |
| 8 | UNCHECK | Interesting | Subjective; not verified against corpus | — |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | Absolute paths | `/app` used | `instruction.md:7` |
| 11 | CHECK | No task name in instruction | "coral galois lantern" not used as task-id string | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch | Offline task | `task.toml:28`, `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:26–28` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:…` present | `environment/Dockerfile:7` |
| 16 | CHECK | Context in environment/ | COPY app/ only | `environment/Dockerfile:35` |
| 17 | CHECK | No ground truth in env | Sample quintics only, no answers | `environment/app/data/quintics.txt` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:26–28`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not run (Docker unavailable) | — |
| 22 | CHECK | Oracle no internet | Writes Rust source, cargo offline | `solution/solve.sh:23`, `environment/Dockerfile:32` |
| 23 | CHECK | Oracle reflective | Full computational Rust implementation | `solution/solve.sh:42+` |
| 24 | CHECK | reward.txt canonical | Writes 0/1 with failure path | `tests/test.sh:4–20` |
| 25 | CHECK | Same verifier for oracle/agent | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:16–19` |
| 27 | UNCHECK | Tests aligned with instruction | Bignum enforced in verifier, not in instruction | `tests/test_outputs.py:334`, `469–474`; blocker 4 |
| 28 | CHECK | Tests check correctness | Value checks vs independent ground truth | `tests/test_outputs.py:460–516` |
| 29 | CHECK | Behavior not implementation grep | Integration tests on program output | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Numeric/structural assertions | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 3 negative lines in export | `entire-report.txt:323`, `335`, `347` |
| 33 | CHECK | Rubric scores in allowed set | ±1,2,3,5 only | `entire-report.txt:314–347` |
| 34 | CHECK | Rubric Agent format | 29 Agent lines | `entire-report.txt:314–347` |
| 35 | UNCHECK | Rubric detailed and precise | Wrong task + >40 pts + milestone shape on non-milestone | Blockers 1–3 |
| 36 | CHECK | Rubric positive phrasing | No "Agent does not …, +N" pattern | `entire-report.txt:314–347` |
| 37 | CHECK | Rubric no /tests/ refs | None in rubric text | `entire-report.txt:314–347` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:314–347` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:314–347` |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4–5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust, galois, scientific-computing | `task.toml:7–12` |
| 45 | CHECK | Difficulty field present | `hard`; platform hard; worst-model 20% | `task.toml:6`, `entire-report.txt:18–24` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | COPY app/ only | `environment/Dockerfile:35` |
| 51 | CHECK | Solution not accessible | Not copied to image | `environment/Dockerfile:35` |
| 52 | CHECK | Agent cannot trivially modify inputs | Fresh random batch at verify time | `tests/test_outputs.py:361–365` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:23–24` |
| 55 | UNCHECK | Not too hard/unfair | Hidden bignum requirement not in instruction | Blocker 4; `entire-report.txt:91–97` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 8, 9, 21, 27, 35, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build Rust CLI in `/app` | `test_project_builds` | covered | `instruction.md:7`; `test_outputs.py:419–423` |
| CLI: input file + output path args | `test_program_runs_and_emits_valid_schema` | covered | `instruction.md:3`, `7`; `test_outputs.py:426–431` |
| JSON array, input order preserved | `test_program_runs_and_emits_valid_schema` | covered | `instruction.md:5`; `test_outputs.py:408–411` |
| Required keys + decimal strings | `test_program_runs_and_emits_valid_schema` | covered | `instruction.md:5`; `test_outputs.py:435–451` |
| Galois labels C5/D5/F20/A5/S5 or null | `test_galois_group_is_correct`, schema test | covered | `instruction.md:5`; `test_outputs.py:452–457`, `501–507` |
| Exact discriminant | `test_discriminant_is_correct` | covered | `instruction.md:3`; `test_outputs.py:460–466` |
| Arbitrary precision for large discriminants | `test_discriminant_is_correct`, `test_discriminants_force_bignum` | **gap** | `instruction.md:3` lacks bignum note; verifier scales to \|disc\| > 2^127 `test_outputs.py:334`, `469–474` |
| Pair-sum resolvent (degree 10, monic) | `test_pair_sum_resolvent_is_correct` | covered | `instruction.md:3`, `5`; `test_outputs.py:477–489` |
| Irreducibility over Q | `test_irreducibility_is_correct` | covered | `instruction.md:3`; `test_outputs.py:492–498` |
| Solvability by radicals | `test_solvability_is_correct` | covered | `instruction.md:5`; `test_outputs.py:510–516` |
| Reducible → null group, solvable | `test_reducible_quintics_marked_solvable` | covered | `instruction.md:5`; `test_outputs.py:519–529` |
| Std library only | `test_uses_only_standard_library` | covered | `instruction.md:1`, `7`; `test_outputs.py:542–552` |
| No shell out to external math tools | `test_does_not_shell_out` | covered | `instruction.md:7`; `test_outputs.py:555–574` |
| All five Galois branches + reducible | `test_all_branches_exercised` | covered (verifier batch sanity) | `test_outputs.py:533–539` |
| Resolvent 11 coefficients | schema test | covered | `instruction.md:5`; `test_outputs.py:448–451` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #27, blocker 4, spec alignment |
| `task.toml` | #44, #45, #46–49, rubric shape |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/app/data/quintics.txt` | bignum gap (small sample) |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #28, #52, spec alignment, bignum |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | rubric, agent stats, metadata adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: coral-galois-lantern/ ===
Summary: 0 error(s), 2 warning(s), 2 info
Task type detected: regular
```

Warnings: non-milestone preference (info); solution-hints heuristic on solve.sh comments (info-level).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Best reference agent |
| terminus-claude-opus-4-8 | 20.0% (1/5) | Worst reference agent |
| oracle | 100.0% (3/3) | Per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test pass rates (`entire-report.txt:36–47`) show partial success on build/bignum/static checks; full-suite pass rate 0/7.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Rust quintic task; report rubric is wrong domain |
| 1 Instruction | ☑ | Strong; bignum sentence missing |
| 2 Environment | ☑ | Digest-pinned Rust; pip pinned (despite audit false positive) |
| 3 Oracle | ☐ | Not executed locally (Docker) |
| 4 Verifiers | ☑ | Excellent randomized verifier |
| 5 Metadata | ☑ | task.toml correct; platform form text wrong |
| 6 Rubric | ☑ | **Blockers:** wrong task, milestone format, 71 > 40 |
| 7 Agent evidence | ☑ | Hard tier; bignum main agent failure mode |
| 8 Fairness | ☑ | Bignum gap affects fairness (#55) |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong work on the task itself — the offline Rust environment, randomized verifier, and mathematical depth are excellent, and the difficulty calibration looks right. Two things to fix before we can accept: the platform rubric is still for a completely different Go milestone task (measure-spec / big.Rat / report subcommand) and needs to be replaced with a flat Coral-specific rubric capped at 40 positive points; and please add one sentence to `instruction.md` that test inputs can produce discriminants beyond fixed-width integers, so agents know they need std-only arbitrary-precision arithmetic. Also update the optional difficulty/solution/verification explanations on the form — they currently describe an unrelated telemetry task.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1, 2, 3 |
| Instruction Styling | yes | 4 |
| Test Alignment/Coverage Issues | no (subsumed by Instruction Styling for bignum) | — |
| Metadata Issues | no (platform form only, not task.toml) | — |
| Environment | no | — |
| Pinning Issues | no | — |

---

_Report enriched per `prompt.md` after `./scripts/terminus validate`, `audit`, and `review`._
