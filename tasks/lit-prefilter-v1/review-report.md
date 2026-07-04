# Terminus Review Report: lit-prefilter-v1

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally; submission export reports 100% 3/3) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** Instruction Styling

**Decision (concise):** Strong hard-tier reverse-engineering task with pinned offline Go env, clean verifiers, and a compliant platform rubric (22 positive pts, flat non-milestone format). ChatGPT’s spec-gap Revise call is **not** upheld as a blocker: held-out graded cases are intentional, instruction explicitly withholds thresholds, and agents median 79/80. The **only real blocker** is `./litpre` / relative binary paths in `instruction.md` (#10, High). Pip pinning (#14) is a false-positive FAIL.

**Insights (concise):**
- Platform rubric uses optional `# Rubric 1` header only — correct for `number_of_milestones = 0`; 22 pts ≤ 40 cap; 4 negatives.
- t06 (8/9 agent trials) tests memchr collapse when LCP=1 but minLiteralLen>1 — not shown in any of 30 examples (ex19 has minLen=1); agents over-inferred `len(LCP)==minLiteralLen`.
- t27–t31 cluster is weaker evidence: 7/10 pass; instruction mentions exact-set fallback; `litpre.go:51-56` documents poison rule.
- `environment/app/examples/README.txt:21-23` claims examples “cover the range of behaviors” — slightly overbroad but not a portal blocker given discovery framing.
- Dockerfile pip **is** pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); automated audit misparsed the continuation line.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling | #10 | Relative binary paths in instruction | `instruction.md:1` — `go build -o litpre .` and `run it as ./litpre <cases-file>`; validator flags `./` | Use absolute paths: `go build -o /app/litpre .` and `/app/litpre <cases-file>` (or equivalent fully qualified paths) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High: examples miss large-set short-LCP collapse (t06); hidden behavior not inferable (ChatGPT / `entire-report.txt` instruction sufficiency) | **Partially agree** (fact) / **Disagree** (blocker) | t06 `cases.py:29` → 30 literals sharing byte `2`, LCP len 1, minLen>1, expected `{"b":[2],"exact":false}`. No training example has this combo: ex19 `scenarios.txt:20` collapses to `[51]` but includes `{"b":[51],"exact":true}` (minLen=1). Oracle memchr in `solution/solve.sh:49-52` has no minLen guard. **Not a blocker:** `instruction.md:5` withholds thresholds by design; graded set is held-out by intent; worst-model 0%, median 79/80; LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:181`). |
| 2 | High: exact-literal poison exemption (t27–t31) absent from examples (ChatGPT) | **Partially agree** (fact) / **Disagree** (blocker) | t30 `cases.py:53` keeps `[32]` exact (rank 255 ≥ 250 per `litpre.go:54-55`) via exactrev path in oracle `solve.sh:89-101`. No training example shows rank≥250 exact byte surviving poison. **Not a blocker:** 7/10 pass on t27–t31; instruction `instruction.md:5` states fallback when shrinking worsens set; ex14/ex15 `expected.txt:15-16` show exact singles surviving. |
| 3 | Medium: none (ChatGPT) | **Agree** | No Medium findings in external review. |
| 4 | Low: add WORKDIR guard to test.sh (ChatGPT / Harbor review) | **Agree** (optional) | `tests/test.sh:1-18` has no `PWD` guard; non-blocking per `writing-tests.md` best practice. |
| 5 | Low: label 30 examples as training (ChatGPT) | **Agree** (optional) | `examples/README.txt:1-8` already describes worked pairs; graded cases disjoint (`cases.py:1-19`). |
| 6 | Dockerfile digest-pinned Go base appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:7` — `golang:1.24-bookworm@sha256:1a6d4452…`; comment justifies Go toolchain for runtime compile. |
| 7 | Non-milestone rubric acceptable ~22 pts (ChatGPT) | **Agree** | `entire-report.txt:356-370` — 9 positives sum 22; 4 negatives; single `# Rubric 1` block only. |
| 8 | Decision Needs Revision for spec gaps (ChatGPT) | **Disagree** | See rows 1–2; sole High blocker is #10 paths. |
| 9 | Instruction sufficiency FAIL (`entire-report.txt:114`) | **Disagree** (as blocker) | Platform analysis correct on t06 failure mode but conflates hard held-out generalization with unfair spec gap. |
| 10 | Harbor review READY TO USE (`entire-report.txt:306`) | **Agree** (infra) | Pinned env, offline tests, reward path OK; does not override #10 path fail. |
| 11 | Test quality ACCEPT (`entire-report.txt:325`) | **Agree** | `test_outputs.py:8-17` — behavioral exact match + shape checks; 40 cases documented in `cases.py`. |
| 12 | Non-milestone task uses milestone rubric format (user concern) | **Disagree** | `rubrics.md:66` — non-milestone allows optional `# Rubric 1`; forbids `# Rubric 2+`. Export has one block only. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 prose blocks, ~375 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational; no spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | No walkthrough steps | `instruction.md` |
| 5 | CHECK | No hints / HOW leakage | Describes goal + examples; algorithm withheld intentionally | `instruction.md:5` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified goal | Clear deliverable: `Optimize` in `/app/optimize.go`, CLI I/O schema | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Real ripgrep-style prefilter reverse-engineering | task design |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | UNCHECK | Absolute paths only | `./litpre` and `litpre` relative output path | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No task slug | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No web fetch in env | `GOPROXY=off` | `environment/Dockerfile:26-27` |
| 14 | CHECK | Pip pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:22-24` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:7` |
| 16 | CHECK | Context in environment/ only | `COPY app/ /app/` | `environment/Dockerfile:32` |
| 17 | CHECK | No graded ground truth in env | 30 training pairs only; 40 graded cases in `tests/cases.py` not in image | `.dockerignore`, `cases.py` |
| 18 | CHECK | No dangerous Docker ops | Standard build | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts OK | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; `test.sh` no installs | `Dockerfile:22-24`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Submission: oracle 100% (3/3); solution algorithmic | `entire-report.txt:24`, `solution/solve.sh` |
| 22 | CHECK | Oracle no network | `GOPROXY=off`, local build | `solution/solve.sh`, `Dockerfile:26` |
| 23 | CHECK | Oracle not hardcoded | Full `Optimize` implementation written | `solution/solve.sh:11-104` |
| 24 | CHECK | reward.txt canonical | Writes 0/1 on pass/fail | `tests/test.sh:14-18` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh`, `test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:14-18` |
| 27 | CHECK | Tests aligned with instruction | Tests exact reference match per stated goal | `instruction.md:1,5`; `test_outputs.py:8-12` |
| 28 | CHECK | Tests check correctness | Exact output equality on 40 cases | `test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Subprocess + output compare | `test_outputs.py:67-79` |
| 30 | CHECK | String match appropriate | Exact engine output required by task | `test_outputs.py:8-12` |
| 31 | CHECK | Test docstrings | All `test_*` documented | `test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 4 negatives | `entire-report.txt:367-370` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All valid | `entire-report.txt:358-370` |
| 34 | CHECK | Agent …, ±N format | 13 lines | `entire-report.txt:358-370` |
| 35 | CHECK | Rubric detailed; pts ≤40 | 22 positive pts | `entire-report.txt:356-370` |
| 36 | CHECK | Positive phrasing | No “does not” on + lines | `entire-report.txt:358-366` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:356-370` |
| 38 | CHECK | Rubric no metadata refs | Clean | `entire-report.txt:356-370` |
| 39 | CHECK | Rubric no oracle/NOP | Clean | `entire-report.txt:356-370` |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | Only standard task files (audit/review reports are reviewer-local) | task tree |
| 42 | CHECK | author fields | Present | `task.toml:5-6` |
| 43 | CHECK | Metadata complete | timeouts, env, tags | `task.toml` |
| 44 | CHECK | Tags/category match | Go algorithm / data-processing | `task.toml:8-18` |
| 45 | CHECK | Difficulty field present | `hard`; worst-model 0% → hard tier | `task.toml:7`, `entire-report.txt:14-20` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | `environment/.dockerignore` |
| 51 | CHECK | Solution not in image | `.dockerignore` excludes solution | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot trivially cheat | Only `optimize.go` mutable; expected values in `/tests` | `instruction.md:3`, `cases.py` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:18-20` |
| 55 | CHECK | Not unfair | Discovery task with 30 examples + full primitives; hard not impossible | `instruction.md:5`, agent stats |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 10, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Implement `Optimize` in `/app/optimize.go` only | build + run | covered | `test_outputs.py:67-71` |
| CLI: `<case-id> <seq-json>` → optimized JSON | all cases | covered | `test_outputs.py:73-79` |
| Match reference engine output exactly | `TestOutputMatch` | covered | `test_outputs.py:8-12` |
| Output literals are prefixes of inputs | `TestOutputValid` | covered | `test_outputs.py:13-16` |
| JSON schema finite/infinite, b, exact | parse + match | covered | `instruction.md:3`, `parse.go` |
| Reconstruct rule from `/app/examples` | held-out 40 cases | covered (by design) | `instruction.md:5`; `cases.py` disjoint from `examples/` |
| Memchr: collapse to rare first byte (LCP 1–3, rank<200) | t06, t00–t05, ex19 | covered | `solve.sh:49-52`; t06 `cases.py:29` |
| Exact-set fallback when shrink worsens | t27–t31, t29 | covered | `instruction.md:5`; `solve.sh:89-101` |
| Poison → infinite | t21–t26, ex10–ex12 | covered | `litpre.go:51-56`; graded + training cases |
| Large-set trim schedule | t14–t20, ex07–ex09 | covered | `solve.sh:69-78` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #5, #7, #10, blocker 1, spec alignment |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/app/litpre.go` | poison rule, primitives |
| `environment/app/examples/scenarios.txt` | ex19 memchr example |
| `environment/app/examples/expected.txt` | training outputs |
| `environment/app/examples/README.txt` | examples scope claim |
| `tests/cases.py` | t06, t27–t31 graded inputs |
| `tests/test_outputs.py` | #27–#31 verifier behavior |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh` | #21–#23, oracle logic |
| `task.toml` | #45, milestone N/A |
| `entire-report.txt` | agent stats, rubric, LLMaJ, external claims |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: lit-prefilter-v1 ===
Summary: 0 error(s), 3 warning(s), 1 info
Warnings: non-milestone preferred; relative paths in instruction; long_context false positive
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Best reference agent |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Worst reference agent |
| oracle | 100.0% (3/3) | per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

Per-test hotspots: `test_values[t06]` 3/10; `test_values[t27-t31]` 7/10 each.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `lit-prefilter-v1`, regular, Go, `number_of_milestones=0` |
| 1 Instruction | ☑ | #10 relative path is sole High fail |
| 2 Environment | ☑ | Pinned digest; pip pinned; tmux+asciinema |
| 3 Oracle | ☑ | Algorithmic; not run locally (Docker) |
| 4 Verifiers | ☑ | Canonical reward; no runtime installs |
| 5 Metadata | ☑ | `hard`, `tool_specific`, `allow_internet=false` |
| 6 Rubric | ☑ | 22 pts; flat non-milestone format OK |
| 7 LLMaJ & agents | ☑ | Spec-gap claim adjudicated — not blocker |
| 8 Novelty & fairness | ☑ | Hard discovery task; anti-cheat sound |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the pinned Go environment, held-out graded suite, and rubric all look great, and the difficulty calibration (0–20% pass) fits a genuine reverse-engineering challenge. I don’t buy the spec-gap Revise call: agents are told to discover thresholds from examples, and median 79/80 shows the materials are mostly sufficient; t06 is a tough generalization edge, not missing env info. One small fix before accept: `instruction.md` uses `./litpre` and a bare `litpre` output name — please switch to absolute paths like `/app/litpre` per Edition 2 path rules. Optional quality tweak (not blocking): add one training example where a large set collapses to a single rare first byte even when LCP is shorter than the shortest literal.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
