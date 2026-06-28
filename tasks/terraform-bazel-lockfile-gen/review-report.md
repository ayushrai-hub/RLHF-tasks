# Terminus Review Report: `terraform-bazel-lockfile-gen`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 13 warnings) |
| **Oracle** | not executed locally (Docker unavailable); report 100% (3/3) |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** none

**Decision (concise):** Re-audit rejects both ChatGPT revision drivers as real blockers. `test_h13` trailing-period HTML is handled correctly when policy pins are validated against catalog version lists (oracle pattern); greedy-regex failures are agent implementation errors. Exact Debian apt revision pins are over-pinning maintenance, not a Terminus compliance failure. Task is fairly hard (Claude 0%, GPT 5.5 60%), oracle-backed, digest-pinned, and normatively specified via referenced docs.

**Insights (concise):**

- Four 26/27 agent failures on `test_h13` reflect unvalidated regex captures (`1.0.0.`), not missing spec text; oracle uses the same `([\d.]+)` regex plus `contains(pkg.Versions, pin)` guard.
- Automated `terminus review` false-positived #13 (dead `preview_emit.py`), #14 (hash-locked pip), #20 (pytest via `requirements.lock`), and #45 (used max not min for worst-model rate).
- `instruction.md` is terse by design but explicitly delegates to normative `artifact_shapes.md` and `vol_h/` — aligned with hard debugging-task pattern.
- Minor non-blockers: 12 public tests lack docstrings; `test.sh` omits canonical `mkdir -p /logs/verifier` (works in Harbor per platform oracle runs).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT High: `test_h13` injects `series 1.0.0.` and expects `1.0.0` but docs do not state version captures must strip trailing punctuation | **Disagree** (not a blocker) | `tests/test_hidden_outputs.py:422-423` injects `<p>…series 1.0.0.</p>`; oracle regex `([\d.]+)` at `solution/oracle/catalog_fold.go:11` is identical greedy pattern; `pickVersion` rejects pins not in catalog via `contains(pkg.Versions, pin)` (`catalog_fold.go:81-82`); `depot_integration.html` requires lowest semver among explicit `@version` pins; `mod_base` resolves to `1.0.0` via dep-pin logic even if amendment capture is `1.0.0.`; existing amendments (`january.html:3`) never place sentence period immediately after `V` — edge is test-only but not unstated semantics |
| 2 | ChatGPT Medium: Dockerfile apt pins (`bash=5.2.15-2+b13`, etc.) create build fragility | **Disagree** (not a blocker) | `environment/Dockerfile:6-8` pins revisions; `docs/guidelines/docker-environment.md:17` example uses unpinned apt names; `reviewer-checklist-full.md` requires pinned packages (High) but not revision-level apt locks; fragility is maintenance preference, not Edition 2 violation |
| 3 | ChatGPT: Needs Revision overall | **Disagree** | No High-severity gaps found on manual re-audit |
| 4 | entire-report LLMaJ: `behavior_in_task_description` FAIL — instruction vague vs tested behaviors | **Partially agree** (non-blocking) | `instruction.md:5` points to `/app/environment/docs/artifact_shapes.md` and `/app/environment/docs/vol_h/` as normative; schemas and amendment rules documented there; terse top-level prompt is intentional for hard doc-discovery tasks per `prompt-styling.md` spec-files pattern |
| 5 | entire-report human: non-canonical Docker base image | **Disagree** (not a blocker) | `environment/Dockerfile:2` digest-pins `python:3.13-slim-bookworm`; matches `docs/guidelines/docker-environment.md:12` starter; Go+Terraform installed on top; `task.toml:29-30` documents reference pattern justification |
| 6 | entire-report human: instruction.md too terse | **Partially agree** (non-blocking) | `instruction.md` is 5 lines; normative contracts live in referenced docs; not a spec-test gap |
| 7 | entire-report: `epoch.json` flat vs nested unspecified | **Disagree** (not a blocker for this task) | `artifact_shapes.md:26` defines flat per-entry counters; `journal_replay.html:3,6` confirms; `tests/test_hidden_outputs.py:49-53` reads flat map; oracle `ReadEpochState() map[string]int` at `solution/oracle/journal_ledger.go:110-118`; single trial nested-format failure was agent misread |
| 8 | entire-report: legacy mirror URL ambiguity caused 2 agent failures | **Disagree** (not a blocker) | `march.html:3` states alias used verbatim with no path suffix; agent misread, not missing spec |
| 9 | entire-report agent stats: GPT 5.5 60%, Claude 0% → hard tier | **Agree** | `entire-report.txt:24-26`; `docs/guidelines/difficulty.md:9` hard ≤20% on best OR worst model; Claude 0% satisfies hard |
| 10 | Automated review: #13 runtime web fetch in `preview_emit.py` | **Disagree** | `preview_emit.py:12-14` is dead code (no imports elsewhere); localhost depot fetch is task architecture; `allow_internet = false` in `task.toml:23` |
| 11 | Automated review: #14 unpinned pip | **Disagree** | `environment/Dockerfile:17-19` installs via `--require-hashes -r requirements.lock`; `requirements.lock:23-25` pins `pytest==8.4.1` |
| 12 | Automated review: #20 pytest not in Dockerfile | **Disagree** | pytest installed from hash-locked `requirements.lock` in Dockerfile |
| 13 | Automated review: #45 difficulty mismatch (60% → medium) | **Disagree** | Script used max rate; worst model is Claude 0% → hard; matches `task.toml:6` |
| 14 | Automated review: #24 missing mkdir, #31 missing docstrings | **Partially agree** (non-blocking) | `tests/test.sh:8-14` writes reward but lacks `mkdir -p /logs/verifier`; 12 functions in `tests/test_outputs.py` lack docstrings (hidden file has docstrings on all 15 tests); CI warns only; platform oracle 100% |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering incident description, not spec dump | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, backtick paths only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal and doc pointers only | `instruction.md` |
| 5 | CHECK | No hints/strategies | No solve walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Goal + normative doc references | `instruction.md:5`, `artifact_shapes.md` |
| 8 | CHECK | Interesting | Realistic Go/Terraform lockfile pipeline repair | task design |
| 9 | UNCHECK | Unique vs TB2/TB3 | Not verified against full corpus | — |
| 10 | CHECK | Absolute paths only | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web grab (except packages) | Build fetches Go/Terraform only; dead `preview_emit.py` | `environment/Dockerfile:11-15` |
| 14 | CHECK | Pinned pip deps | Hash-locked `requirements.lock` | `environment/Dockerfile:17-19` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:2` |
| 16 | CHECK | Context in environment/ only | `COPY . /app/environment` from env context | `environment/Dockerfile:21` |
| 17 | CHECK | No ground truth in env | Symptoms only in `staging_notes.md`; no answers | `environment/docs/staging_notes.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not conflict mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest baked via requirements.lock | `environment/Dockerfile:17-19` |
| 21 | CHECK | Oracle passes consistently | Platform report 100% (3/3); local oracle blocked by Docker | `entire-report.txt:30` |
| 22 | CHECK | Oracle no internet at runtime | Patch + terraform apply only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answers | Applies `oracle_clean.patch`, rebuilds, runs pipeline | `solution/solve.sh:7-31` |
| 24 | UNCHECK | test.sh reward + mkdir | Writes reward; missing `mkdir -p /logs/verifier` | `tests/test.sh:8-14` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, test py files |
| 26 | CHECK | Binary rewards 0/1 | `echo 1` / `echo 0` only | `tests/test.sh:10-14` |
| 27 | CHECK | Tests aligned with instructions | Tests trace to `artifact_shapes.md` + `vol_h/` referenced by instruction | §5 below |
| 28 | CHECK | Tests check correctness | Digest, seal, chain, version assertions | `tests/test_hidden_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Subprocess harness + output inspection | `tests/support/run_apply_checks.sh` |
| 30 | CHECK | No brittle long-string asserts | Structured JSON/digest checks | test files |
| 31 | UNCHECK | Informative docstrings | 12 public tests in `test_outputs.py` lack docstrings | `tests/test_outputs.py:120+` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no `rubric.txt` in task folder | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle mentions | N/A | — |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README at task root | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category match | go/terraform/build-and-dependency-management | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches rates | hard + Claude 0% worst model | `task.toml:6`, `entire-report.txt:25-26` |
| 46 | UNCHECK | Milestone layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | — |
| 48 | UNCHECK | test_mN.py per milestone | N/A | — |
| 49 | UNCHECK | Milestone test scope | N/A | — |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | solution/ outside build context | `environment/Dockerfile:21` |
| 52 | CHECK | No trivial input cheat | Full pipeline repair required | test harness design |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 0% ≤80% | `entire-report.txt:25` |
| 55 | CHECK | Not unfair | Normative docs cover tested semantics; `test_h13` edge is agent-validation issue | §3 claim 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 24, 31, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate outputs from live fixtures/catalog per apply | all `test_*` via harness | covered | `instruction.md:3`, `artifact_shapes.md:13` |
| Output schemas (lock, checksum, repo, module_lock) | p01–p15, h01–h15 | covered | `artifact_shapes.md:5-9` |
| Journal slot isolation + seed_digest format | p04, h05, h08 | covered | `artifact_shapes.md:31`, `tests/test_outputs.py` |
| Replay chain prefix linkage + rebuild on corruption | p10, p15, h09–h12, h15 | covered | `artifact_shapes.md:33`, hidden tests |
| Amendment policy pins (generic root entries) | p04, p09, h13 | covered | `closure_semantics.html:3`, `test_h13` |
| Lowest explicit dep semver pin | h13 | covered | `depot_integration.html:5`, `test_h13:433` |
| Legacy mirror alias verbatim | p07, h06 | covered | `march.html:3` |
| Live catalog checksum reseal | h14 | covered | `artifact_shapes.md:15` |
| Foreign tail / stale seed hydrate miss | p12, h04, h12 | covered | `artifact_shapes.md:33` |
| Dynamic root index + amendment discovery | h13 | covered | `closure_semantics.html:3`, `test_h13` |
| Trailing-period HTML version token stripping | — | **not required** | Oracle validates pins against catalog versions; agent regex bug |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–8, #10–12, §5 |
| `task.toml` | #42–45 |
| `environment/Dockerfile` | #13–20 |
| `environment/docs/artifact_shapes.md` | §3 claims 4,7; §5 |
| `environment/docs/vol_h/runbooks/closure_semantics.html` | §3 claim 1, §5 |
| `environment/docs/vol_h/runbooks/depot_integration.html` | §3 claim 1, §5 |
| `environment/docs/vol_h/amendments/march.html` | §3 claim 8 |
| `solution/oracle/catalog_fold.go` | §3 claim 1 |
| `tests/test_hidden_outputs.py` | §3 claim 1, #27–28 |
| `tests/test_outputs.py` | #31 |
| `tests/test.sh` | #24–26 |
| `entire-report.txt` | #21, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate terraform-bazel-lockfile-gen/
Summary: 0 error(s), 13 warning(s), 1 info
Warnings: missing docstrings on 12 public tests; pip == lint on hash-install line
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures; 4 trials at 26/27 |
| terminus-claude-opus-4-8 | 0.0% (0/5) | All failed |
| oracle | 100.0% (3/3) | Platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (Claude) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test: `test_h13` 4/10 — isolated to unvalidated regex capture, not broad spec gap.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `terraform-bazel-lockfile-gen` matches report |
| 1 Instruction | ☑ | Terse but normative doc delegation valid |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; deps baked |
| 3 Oracle | ☑ | Patch-based; not run locally (no Docker) |
| 4 Verifiers | ☑ | 27 tests; minor docstring/mkdir gaps non-blocking |
| 5 Metadata | ☑ | hard matches Claude 0% |
| 6 Rubric | ☑ | N/A — rubric only in platform report text |
| 7 Agent evidence | ☑ | ChatGPT claims challenged |
| 8 Novelty/fairness | ☑ | No cheating path; test_h13 fair |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction delegates normatively to `artifact_shapes.md` and `vol_h/` runbooks/amendments; tests comprehensively verify pipeline repair across rotation, tamper recovery, chain witnesses, and dynamic roots. Oracle passes on platform runs; agent rates (Claude 0%, GPT 5.5 60%) match declared hard difficulty. ChatGPT revision items are not blockers: `test_h13` trailing-period HTML is handled by catalog version validation (same as oracle), and exact apt revision pins are optional maintenance not a compliance failure. Minor polish only: add docstrings to 12 public tests and canonical `mkdir -p /logs/verifier` in test.sh.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Rubric | no | — |
