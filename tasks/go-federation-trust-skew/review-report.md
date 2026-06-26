# Terminus Review Report: `go-federation-trust-skew`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform report; local oracle not executed) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** Rubric

**Decision (concise):** One real blocker: platform rubric has **3 negative lines but only 1 distinct** negative criterion — the same `Agent modifies … m4_grade_test.go …, -5` line is copy-pasted into all three `# Rubric N` blocks (`entire-report.txt:435,445,456`). `docs/guidelines/rubrics.md:33` and `docs/task-requirements.md:144` require **≥3 distinct** negative-reward criteria; `reviewer-checklist-full.md` rates this High. `scripts/validate_rubric.py` counts lines only (would pass), but manual review follows written policy. Everything else from prior audit holds: no difficulty/realm-normalization blockers; milestone `# Rubric N` headers and per-block positives are fine.

**Insights (concise):**

- **Blocker:** Add ≥2 more **distinct** negatives (e.g. hand-written probe/harness output, decoy `localeFold`-only realm fix, regressing prior-milestone fixes).
- Rubric has 3 negative **lines** / 1 distinct — `validate_rubric.py:48-56` does not check uniqueness; portal #32 fails on distinctness.
- Platform oracle 100% (3/3); digest-pinned offline env; SHA256 graded-suite integrity — solid.
- ChatGPT difficulty + realm-normalization Revise drivers still **not** blockers (worst model 60%; `parts.go` + 10/10 M3 pass rate).
- Declared `hard` vs observed Medium — #45 UNCHECK only (informational).
- Per-milestone rubric format (`# Rubric 1–3`) is correct for this 3-milestone task.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32 | Only **1 distinct** negative criterion across full rubric; same penalty repeated in each milestone block | `entire-report.txt:435,445,456` — identical line thrice; `docs/guidelines/rubrics.md:33`; `docs/task-requirements.md:144`; `reviewer-checklist-full.md:75` | Add ≥2 **distinct** negative criteria (different bad behaviors), keeping ≥1 negative per `# Rubric N` block. Examples: hand-written `/app/output/stage/probe.json` or `harness/status.txt` (-3); realm fix using decoy `localeFold` only without scheme/port/slash normalization (-3); regressing M1/M2 fixes while editing later milestones (-3). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `difficulty = "hard"` vs Medium evaluation — update metadata | **Disagree** (not a blocker) | `prompt.md:409-415`; worst-model Claude 60% (`entire-report.txt:20`) |
| 2 | ChatGPT: realm normalization undocumented but tested | **Partially agree** (not a blocker) | `contract.md:42-44`; `parts.go:5-21`; M3 binding 10/10 (`entire-report.txt:66-83`) |
| 3 | ChatGPT: Needs Revision (difficulty + test alignment) | **Partially agree** | Revise for **rubric** only; not for ChatGPT’s stated reasons |
| 4 | User: ≥3 negative rubrics — are we sure? | **Agree — blocker** | 3 lines, 1 distinct (`entire-report.txt:435,445,456`); `rubrics.md:33` requires distinct |
| 5 | entire-report: LLMaJ other checks PASS | **Agree** | `entire-report.txt:152-160` |
| 6 | entire-report: Agent instruction sufficiency PASS | **Agree** | `entire-report.txt:108-131` |
| 7 | entire-report: milestone rubric `# Rubric 1–3` format | **Agree** | `entire-report.txt:428-456`; `task.toml:9` |
| 8 | Automated `terminus review`: #1, #14, #31, #54 | **Disagree** | Prior audit — false positives |
| 9 | `validate_rubric.py` would accept rubric | **Agree** (script gap) | `scripts/validate_rubric.py:48-56` counts lines, not distinct text |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone ~3 short paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Operator symptoms + doc refs | `steps/milestone_1/instruction.md:1-4` |
| 3 | CHECK | No excessive markdown | No ##/tables in instructions | — |
| 4 | CHECK | No step-by-step solve instructions | Symptom + confirm commands | — |
| 5 | CHECK | No hints/strategies | WHAT not HOW | — |
| 6 | CHECK | No design-doc tables | None in instructions | — |
| 7 | CHECK | Well specified | Per-milestone goals + contract refs | — |
| 8 | CHECK | Interesting | Federation/security debugging | task domain |
| 9 | CHECK | Unique | `reference_pattern` justification | `task.toml:16-17` |
| 10 | CHECK | Absolute paths | `/app/environment/...` | — |
| 11 | CHECK | Task name not in instruction | None | — |
| 12 | CHECK | No canary string | None | — |
| 13 | CHECK | No web fetch in env | Build-only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with == | `pytest==8.4.1` | `environment/Dockerfile:20-22` |
| 15 | CHECK | Base image digest-pinned | Both stages | `environment/Dockerfile:1,10` |
| 16 | CHECK | Context in environment/ | `COPY . /app/environment` | `environment/Dockerfile:4` |
| 17 | CHECK | No ground truth in env | Buggy sources; decoy labeled | `display.go:5` |
| 18 | CHECK | No privileged/docker.sock | Clean Dockerfile | — |
| 19 | CHECK | Compose mount safe | No compose | — |
| 20 | CHECK | Verifier deps in image | pytest baked in; test.sh no installs | `environment/Dockerfile:19-22` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3) | `entire-report.txt:25` |
| 22 | CHECK | Oracle no internet | Local file copy + go build | `solve1.sh` |
| 23 | CHECK | Oracle reflective | Source patches, not echo | `steps/milestone_*/solution/` |
| 24 | CHECK | reward.txt always written | Pre-write 0; set 1 on pass | `steps/milestone_1/tests/test.sh` |
| 25 | CHECK | Same logic oracle/agent | No `/oracle` branch | — |
| 26 | CHECK | Binary rewards | 0 or 1 | — |
| 27 | CHECK | Tests aligned | Contract + code hints cover graded cases | `contract.md`, `parts.go` |
| 28 | CHECK | Correctness not format-only | `go test` deny codes/principals | `m4_grade_test.go` |
| 29 | CHECK | Behavior not impl grep | No source grep in pytest | — |
| 30 | CHECK | No brittle exact match | Deny codes contract-defined | `contract.md:54-61` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings | `test_m1.py:28-71` |
| 32 | UNCHECK | Rubrics ≥3 negative penalties | **3 lines, 1 distinct** — fails `rubrics.md:33` | `entire-report.txt:435,445,456` |
| 33 | CHECK | Scores ∈ {±1,2,3,5} | All valid | `entire-report.txt:428-456` |
| 34 | CHECK | Format `Agent …, ±N` | All conform | — |
| 35 | CHECK | Criteria detailed | Task-specific paths/functions | — |
| 36 | CHECK | Positive phrasing for negatives | Bad behavior gets `-5` | — |
| 37 | CHECK | No /tests/ references | `m4_grade_test.go` is env path in instruction | — |
| 38 | CHECK | No task.toml/instruction refs | None | — |
| 39 | CHECK | No oracle/NOP mentions | None | — |
| 40 | CHECK | Required files present | env + steps layout | — |
| 41 | CHECK | Clean parent directory | No stray root files | — |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | Complete | `task.toml` |
| 44 | CHECK | Tags/languages match | security, go | `task.toml:6-12` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; worst 60% → Medium | `task.toml:6`, `entire-report.txt:20` |
| 46 | CHECK | steps/ layout | 3 milestones | `task.toml:27-52` |
| 47 | CHECK | solveN.sh each milestone | solve1/2/3.sh | — |
| 48 | CHECK | test_mN.py each milestone | test_m1/2/3.py | — |
| 49 | CHECK | Milestone scope | M1 T01–T08; M2 bundle; M3 full | `test_m1.py:8`, `test_m2.py:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | steps/ only | — |
| 52 | CHECK | No trivial input tampering | SHA256 integrity gate | `test_m1.py:58-67` |
| 53 | CHECK | No unpinned git clone | None | — |
| 54 | CHECK | Not too easy | Worst model 60% (<80%) | `entire-report.txt:20` |
| 55 | CHECK | Not too hard/unfair | M3 10/10; M1/M2 reasoning failures | `entire-report.txt:66-125` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Time-window slack (DefaultSlack 5000ms) | T01–T08 | covered | `contract.md:30-34` |
| Retired bundle generations denied | T09–T16, T34–T35 | covered | `contract.md:36-38` |
| Equivalent realm strings | T17–T24, T33 | covered | `contract.md:40-44`; `parts.go:5-21` |
| Map generation staleness | T25–T32, T36 | covered | `contract.md:46-50` |
| probe.json / harness outputs | `test_probe_*`, `test_harness_*` | covered | `api.md:31-41` |
| Graded suite integrity | `test_graded_suite_integrity` | covered | `contract.md:13-17` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `entire-report.txt` | rubric blocker (#32), agent stats, adjudication |
| `docs/guidelines/rubrics.md` | distinct-negative requirement |
| `docs/task-requirements.md` | distinct-negative requirement |
| `docs/reviewer-checklist-full.md` | High severity for rubric negatives |
| `scripts/validate_rubric.py` | script counts lines only (gap) |
| `task.toml` | milestone count, #45 |
| `environment/Dockerfile` | pinning, env |
| `environment/docs/contract.md` | spec alignment |
| `steps/milestone_*/instruction.md` | instruction audit |
| `steps/milestone_*/tests/test_m*.py` | verifiers |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate go-federation-trust-skew/
Summary: 0 error(s), 7 warning(s), 3 info
```

### Agent performance

| Model | Pass rate |
|-------|-----------|
| terminus-gpt5-5 | 100.0% (5/5) |
| terminus-claude-opus-4-8 | 60.0% (3/5) |
| oracle | 100.0% (3/3) |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone Go security task |
| 1 Instruction | ☑ | No blockers |
| 2 Environment | ☑ | No blockers |
| 3 Oracle | ☑ | Platform 100% |
| 4 Verifiers | ☑ | No blockers |
| 5 Metadata | ☑ | #45 informational only |
| 6 Rubric | ☐ | **Blocker:** 1 distinct negative, need ≥3 |
| 7 LLMaJ & agents | ☑ | Realm flag = polish only |
| 8 Novelty & fairness | ☑ | Solid |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the three-milestone flow is well thought out, the hidden graded suite with integrity checking is a nice anti-cheat touch, and the Dockerfile/environment setup looks good. Oracle passes and the verifiers exercise real behavior. One thing to fix before accept: the rubric repeats the same negative penalty (modifying the graded test file) in all three milestone blocks. Please add at least two more distinct negatives — for example, penalizing hand-written probe/harness output, the decoy localeFold-only realm fix, or regressing earlier milestone fixes. If you have time, spelling out realm-equivalence rules in contract.md and tweaking the declared difficulty would be nice polish but aren’t required for accept.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| All others | no | — |
