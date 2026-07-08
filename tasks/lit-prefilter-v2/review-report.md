# Terminus Review Report: `lit-prefilter-v2`

**Generated:** 2026-07-07 11:12 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/lit-prefilter-v2`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Accept. The prior relative-path issue (`./litpre`) is fixed — `instruction.md` now uses absolute `/app/litpre` paths throughout. Pip deps are pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); automated #14 FAIL is a false positive. Oracle passes 1.0. Platform rubric is valid for a non-milestone task (22 positive pts, 4 negatives; optional single `# Rubric 1` header only). No High/Medium blockers found.

**Insights (concise):**

- Strong reverse-engineering task: 30 visible examples, 40 hidden graded cases, clean anti-cheat (tests/solution excluded from image).
- Agent calibration fits hard tier: worst-model 0%, best-model 40%; average per-test pass ~97% but binary reward masks near-misses.
- LLMaJ "instruction sufficiency FAIL" overstates a spec gap — instruction explicitly requires inferring thresholds from examples; hidden-case failures (t06, t27–t31) are intentional generalization, not phantom requirements.
- Non-milestone rubric shape is compliant: one optional `# Rubric 1` block, no `# Rubric 2+`.
- Optional polish only: add a worked example for large-set rare-first-byte LCP collapse (t06 cluster); inline branch comments in `cases.py`.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: path issue fixed; instruction uses absolute `/app/litpre` (ChatGPT) | Agree | `instruction.md:1` — `go build -o /app/litpre .` and `/app/litpre <cases-file>`; no `./litpre` or bare `litpre` |
| 2 | ChatGPT: no High/Medium blockers; Accept (ChatGPT) | Agree | Full artifact audit; oracle pass; rubric 22/40; pip pinned at `environment/Dockerfile:22-24` |
| 3 | ChatGPT: spec-gap concern not blocking for reverse-engineering task (ChatGPT) | Agree | `instruction.md:5` — "precise conditions and thresholds are not written down here. Reconstruct them from the worked input → reference output pairs"; agents avg 96.7% per-test pass |
| 4 | ChatGPT: optional large-set rare-byte collapse example (ChatGPT) | Agree (Low only) | `cases.py:29` t06 expects `{b:[2],exact:false}` for ~30 literals; no matching pattern in 30 `examples/scenarios.txt` lines |
| 5 | ChatGPT: optional inline comments in `cases.py` (ChatGPT) | Agree (Low only) | `cases.py:21-63` — branch coverage only in module docstring, not per-case |
| 6 | ChatGPT: digest-pinned Go base appropriate (ChatGPT) | Agree | `environment/Dockerfile:7` — `golang:1.24-bookworm@sha256:1a6d4452…`; comment documents canonical Go base justification |
| 7 | Prior reviewer: switch `./litpre` to `/app/litpre` (`entire-report.txt:1`) | Agree — resolved | Current `instruction.md:1` uses absolute paths; stale feedback from prior cycle |
| 8 | LLMaJ: instruction sufficiency FAIL — example gap for t06/t27–t31 (`entire-report.txt:117-177`) | Partially agree | Gap exists in training examples for t06 cluster, but instruction frames task as reverse-engineering from examples + generalization; not a verifier/instruction blocker per Edition 2 reverse-engineering norms |
| 9 | LLMaJ quality checks: all `behavior_in_*` pass (`entire-report.txt:196-205`) | Agree | Cross-checked instruction ↔ tests ↔ env; anti-cheat, schema, pinning all verified |
| 10 | Harbor review: non-canonical base image warning (`entire-report.txt:232-250`) | Disagree as blocker | `environment/Dockerfile:1-3` documents sanctioned digest-pinned Go base; runtime compile requirement justifies non-slim image |
| 11 | Harbor test quality: ACCEPT, robust (`entire-report.txt:312-351`) | Agree | 40 disjoint graded cases; 30 examples non-overlapping; `TestOutputMatch` + `TestOutputValid` |
| 12 | Automated audit #14: unpinned pip (`audit-report.md:87`) | Disagree | `environment/Dockerfile:22-24` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` with `==` pins |
| 13 | Automated review #41: stray `audit-report.md` (`review-report.md` baseline) | Disagree as task blocker | Reviewer-generated artifact, not part of task submission zip |
| 14 | Non-milestone task uses milestone rubric format (`user query`) | Disagree | `task.toml:12` `number_of_milestones = 0`; platform rubric has only `# Rubric 1` (optional per `docs/guidelines/submission-export-format.md:63`); no `# Rubric 2+` — compliant flat rubric |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 prose blocks, ~375 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational problem statement, not spec-doc | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Describes WHAT (match reference); thresholds left to examples | `instruction.md:5` |
| 6 | CHECK | No design-doc tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | JSON schema, paths, build/run, single mutable file named | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Real engine reverse-engineering problem | `instruction.md`, `litpre.go` |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | Absolute paths | `/app`, `/app/litpre`, `/app/optimize.go`, `/app/examples` | `instruction.md:1,3,5` |
| 11 | CHECK | No task name in instruction | "lit-prefilter-v2" absent | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch | `GOPROXY=off`; no curl/wget in env | `environment/Dockerfile:26-27` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:22-24` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452…` | `environment/Dockerfile:7` |
| 16 | CHECK | Env context scoped | `COPY app/ /app/` only | `environment/Dockerfile:32` |
| 17 | CHECK | No ground-truth leakage | Examples are training pairs; graded `cases.py` not in image | `environment/.dockerignore:2-3`, `tests/cases.py` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | No compose mount tampering | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest baked in Dockerfile; `test.sh` no installs | `environment/Dockerfile:22-24`, `tests/test.sh:1-11` |
| 21 | CHECK | Oracle passes | Mean reward 1.000 (1/1 trial) | `./scripts/terminus oracle` 2026-07-07 |
| 22 | CHECK | Oracle offline | No network in `solve.sh` | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | Full algorithm in heredoc, not hardcoded case outputs | `solution/solve.sh:11-103` |
| 24 | CHECK | reward.txt on failure | Writes 0/1 with failure path | `tests/test.sh:14-17` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh:14-17` |
| 27 | CHECK | Tests aligned with instruction | Tests exact reference match + prefix validity per instruction | `tests/test_outputs.py:91-130`, `instruction.md:1,5` |
| 28 | CHECK | Tests check correctness | Byte-for-byte reference equality | `tests/test_outputs.py:96-106` |
| 29 | CHECK | Behavior not implementation | Compiles/runs binary; no source grep | `tests/test_outputs.py:67-78` |
| 30 | CHECK | Exact match appropriate | Algorithm output must match exactly by spec | `instruction.md:1` |
| 31 | CHECK | Test docstrings | All `test_*` have docstrings | `tests/test_outputs.py:96,115` |
| 32 | CHECK | ≥3 rubric negatives | 4 negatives | `entire-report.txt:364-367` |
| 33 | CHECK | Rubric scores valid | ±1,2,3,5 only | `entire-report.txt:355-367` |
| 34 | CHECK | Rubric format | 13 `Agent …, ±N` lines | `entire-report.txt:355-367` |
| 35 | CHECK | Rubric detailed; ≤40 pts | 22 positive pts (9 +lines) | `./scripts/terminus rubric-points` |
| 36 | CHECK | Positive rubric language | Positives describe desired behaviors | `entire-report.txt:355-363` |
| 37 | CHECK | No /tests/ in rubric | Clean | `entire-report.txt:355-367` |
| 38 | CHECK | No metadata refs in rubric | No task.toml/instruction refs | `entire-report.txt:355-367` |
| 39 | CHECK | No oracle/NOP in rubric | Clean | `entire-report.txt:355-367` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | No stray parent files | Only standard task layout in submission | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:5-6` |
| 43 | CHECK | Other metadata | category, tags, timeouts, languages | `task.toml` |
| 44 | CHECK | Tags/category match | `go`, `regex`, `prefilter`; `data-processing` | `task.toml:8,16-18` |
| 45 | CHECK | Difficulty present | `difficulty = "hard"`; platform hard; worst-model 0% | `task.toml:7`, `entire-report.txt:18,23` |
| 46 | UNCHECK | steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile:32`, `.dockerignore:3` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution | `environment/.dockerignore:2` |
| 52 | CHECK | No trivial input tampering | Graded cases injected at `/tests`; agent edits `optimize.go` only | `tests/cases.py`, `instruction.md:3` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:23` |
| 55 | CHECK | Not unfair | Solvable (GPT-5.5 40%); examples + primitives provided; near-misses are calibration | `entire-report.txt:20-24,117-195` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build `cd /app && go build -o /app/litpre .` | `results` fixture | covered | `tests/test_outputs.py:67-71` |
| Run `/app/litpre <cases-file>` one case per line | `results` fixture | covered | `tests/test_outputs.py:73-78` |
| Output `<case-id> <optimized-seq-json>` | `TestOutputMatch.test_values` | covered | `tests/test_outputs.py:96-106` |
| Match reference engine output exactly | `TestOutputMatch.test_values` (40 cases) | covered | `tests/cases.py`, `tests/test_outputs.py:96-106` |
| JSON schema finite/infinite | `TestOutputValid.test_shape` | covered | `tests/test_outputs.py:115-130` |
| Emitted literals are prefixes of inputs | `TestOutputValid.test_shape` | covered | `tests/test_outputs.py:128-130` |
| Only `/app/optimize.go` may change | env constraint (not directly tested) | covered | Anti-cheat via hidden cases; instruction constraint |
| Reconstruct thresholds from `/app/examples` | hidden graded cases (generalization) | covered | `instruction.md:5`; 30 examples vs 40 hidden `cases.py` |
| `allow_internet = false` | env config | covered | `task.toml:30` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, spec alignment, path-fix adjudication |
| `task.toml` | #45, milestone N/A, metadata |
| `environment/Dockerfile` | #14, #15, #20, pinning |
| `environment/.dockerignore` | #17, #50, #51 |
| `environment/app/optimize.go` | stub, single-file target |
| `environment/app/examples/` | training examples (30 pairs) |
| `tests/test.sh` | #24, #20 |
| `tests/test_outputs.py` | #27-31, verifier behavior |
| `tests/cases.py` | graded cases t00-t39 |
| `solution/solve.sh` | #21-23, oracle |
| `entire-report.txt` | agent stats, rubric, LLMaJ, prior feedback |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate lit-prefilter-v2/
Summary: 0 error(s), 2 warning(s), 1 info
Task type detected: regular
```

Warnings: non-milestone info (preferred not blocked); long_context false-positive (task uses `tool_specific` not `long_context`); pip warning is false positive (packages are pinned).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Best reference agent |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Worst reference agent |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle 1.000 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Common failure clusters: t06 (large-set LCP collapse), t27-t31 (exact multi-literal poison exemption). Per-test pass rates 91-99% across trials.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `lit-prefilter-v2`, regular layout, Go reverse-engineering |
| 1 Instruction | ☑ | Absolute paths fixed; reverse-engineering framing clear |
| 2 Environment | ☑ | Digest-pinned Go base; tmux+asciinema; pip pinned |
| 3 Oracle | ☑ | Pass 1.0; full algorithm implementation |
| 4 Verifiers | ☑ | Canonical test.sh; behavioral tests; docstrings |
| 5 Metadata | ☑ | hard, data-processing, tool_specific, go |
| 6 Rubric | ☑ | 22/40 pts; 4 negatives; non-milestone shape OK (`# Rubric 1` only) |
| 7 LLMaJ & agent evidence | ☑ | Spec-gap claim adjudicated; calibration fits hard |
| 8 Novelty & fairness | ☑ | Multi-step algorithm; anti-cheat solid |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The Go environment is well set up with a digest-pinned base, verifier deps baked into the image, and the absolute `/app/litpre` paths are correct now. The reverse-engineering framing is clear, the 30 worked examples give agents a fair starting point, and the hidden graded suite plus anti-cheat separation look solid. Oracle passes cleanly and the 0–40% agent pass rates fit hard difficulty. I didn't find any blockers. Optional polish if you want to reduce the t06 near-miss cluster: add one more training example where a large set collapses to a single rare first byte instead of trimming.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| All others | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus validate`, `audit`, `review`, and local oracle run._
