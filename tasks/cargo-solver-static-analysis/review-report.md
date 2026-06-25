# Terminus Review Report: cargo-solver-static-analysis

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 39 |
| **UNCHECK count** | 16 |

**Error categories (internal):** Task Difficulty, Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Dockerfile pinning, verifier layout, oracle, and anti-cheating measures are solid. Two High blockers remain: `task.toml` declares `hard` but worst-model pass rate is 40% (medium tier), and `instruction.md` does not explain that errata-table rules without inline `severity=` must take severity from the separate errata severity-assignment table in the dossier — causing systematic `test_violations_exact_set` failures (R-009 emitted as WARNING instead of CRITICAL). Fix metadata and add one explicit errata-severity lookup sentence before resubmit.

**Insights (concise):**

- Oracle passes 1/1; all 20 pytest functions pass when solution runs.
- Worst-model rate is GPT-5.5 at 40% (2/5), not Claude at 100% — observed tier is **medium**, not trivial.
- All three GPT-5.5 failures were identical: 19/20 tests, sole miss on `test_violations_exact_set` for R-009 severity.
- Dossier **does** contain the severity table (`validation_dossier.md:456-462`) immediately after the errata table; the gap is instruction clarity, not missing dossier data.
- `#14` pip-pinning auto-fail is a false positive — `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are digest-pinned in the Dockerfile.
- Long-context bar met: dossier ~299 KB, rules scattered across four annotation formats with decoy non-active rows.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared `difficulty = "hard"` but worst-model pass rate is 40% → medium tier (20–60%) | `task.toml:7`; `entire-report.txt:1-7` | Set `difficulty = "medium"` or rebalance task until worst-model ≤20% |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27 | Errata-table rules lack inline severity; tests require CRITICAL for R-009 via dossier severity table, but instruction only says "severity … as given by the dossier" without explaining the secondary lookup | `instruction.md:17`; `validation_dossier.md:450-462`; `test_outputs.py:228-255`; `entire-report.txt:48-52,70-67` | Add explicit note: when errata rows have no inline `severity=`, use the errata severity-assignment table in the dossier |

*No other High-severity blockers found on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `difficulty=hard` but evaluation classifies Medium (100% / 40% pass rates) | Agree | `task.toml:7`; `entire-report.txt:1-7` — worst model GPT-5.5 40% → medium per `docs/guidelines/difficulty.md` |
| 2 | ChatGPT: errata severity lookup not explicit enough; agents emit WARNING for R-009 instead of CRITICAL | Partially agree | Dossier table exists at `validation_dossier.md:456-462` ("used by the auditor when emitting violations"); errata rows at `:450-452` lack inline severity; `instruction.md:17` does not bridge the two-part lookup; all GPT failures on `test_violations_exact_set` |
| 3 | ChatGPT: Decision Needs Revision | Agree | Blockers 1–2 confirmed on artifact re-audit |
| 4 | entire-report: Task Instruction Sufficiency FAIL — systematic R-009 severity gap | Agree | `entire-report.txt:40-67`; `test_violations_exact_set` 7/10 pass |
| 5 | entire-report: Difficulty MEDIUM, solvable | Agree | `entire-report.txt:1-3`; oracle pass executed locally |
| 6 | entire-report: Non-canonical Python base image warning | Disagree (not a blocker) | `environment/Dockerfile:1` — Python needed for pytest verifier; digest-pinned ECR image; functional and acceptable |
| 7 | entire-report: "READY TO USE" / ACCEPT recommendation | Disagree | Contradicts agent failure analysis (`task_specification: fail`) and difficulty metadata mismatch |
| 8 | entire-report: Errata severity implicit coupling is intentional hard-task complexity | Partially agree | Appropriate for long-context depth, but instruction must still state lookup rule when tests enforce exact severity |
| 9 | Auto validate: unpinned pip (#14) | Disagree | `environment/Dockerfile:16-18` — both packages use `==` pins |
| 10 | Auto review: worst-model 100% / #54 fail | Disagree | Script uses `max()` not `min()` for agent rates; correct worst-model is GPT-5.5 40% (<80%) → #54 passes |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Problem + output schemas; no LLM bloat | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone describing broken auditor | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no ##/tables/code fences | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT outputs to produce, not HOW to debug | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No solve walkthrough in instruction | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | Tab headers inline, not mapping tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | Errata severity lookup path unstated | `instruction.md:17`; blocker 2 |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic Cargo/AWK static-analysis scenario | `instruction.md:1` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Novel AWK+Cargo+CFL dossier combination; not verified against full corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/wavebench`, `/app/reports/…`, `/app/docs/…` | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task folder name in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | COPY only local env files | `environment/Dockerfile:24-26` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:16-18` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | FROM digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | All COPY from env subtree | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Rust comments cite errata IDs only, not violation tables; no solution/tests COPY | `environment/Dockerfile:22-23` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pip in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:16-18`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | `./scripts/terminus oracle` → reward 1.0 (1/1) | oracle run 2026-06-23 |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes/runs local gawk only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rewrites audit.awk; parses manifests + dossier | `solution/solve.sh:67-80,191` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical 0/1 block | `tests/test.sh:6,18-22` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary reward.txt | `tests/test.sh:18-22` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | `test_violations_exact_set` enforces errata severity-table lookup not stated in instruction | `test_outputs.py:251-255`; blocker 2 |
| 28 | CHECK | Tests check for correctness, not just format | Exact row content, transitive closure, weak-dep semantics | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Assert report TSV content, not awk internals | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact TSV values appropriate for deterministic audit output | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 20 tests have docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no rubric file in task folder (portal rubric separate) | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | awk/bash/rust, build-and-dependency-management, long_context | `task.toml:8-13` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared hard; worst-model 40% → medium | `task.toml:7`; blocker 1 |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile:22-26` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Expected violation tables only in tests/ | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Manifests + dossier are inputs; idempotency reruns script | `test_idempotent_and_script_driven` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 40% < 80% | `entire-report.txt:6-7` |
| 55 | CHECK | Task is not too hard or unfair | Severity data is in dossier; failure is spec clarity not unavailable info | `validation_dossier.md:456-462` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 7, 27, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Four TSV reports with exact headers | `test_feature_gates_header`, `test_cfl_rules_header`, `test_violations_header`, `test_cfl_margins_header` | covered | `instruction.md:8-21`; `test_outputs.py` |
| Parse dep:/crate?/feature; multi-line arrays | `test_feature_gates_dep_classification`, `test_optional_dep_syntax_preserved` | covered | `instruction.md:9`; `test_outputs.py:118-150` |
| Extract rules from four dossier formats; active-only | `test_cfl_rules_all_present_and_sorted`, `test_decoy_rules_excluded` | covered | `instruction.md:3,13`; `test_outputs.py:192-222` |
| Transitive closure + weak-dep semantics | `test_weak_dependency_semantics`, `test_no_false_positive_on_safe_features` | covered | `instruction.md:5`; `test_outputs.py:267-295` |
| CFL margins: min max_cfl, 4 decimals, tie-break | `test_cfl_margins_*` | covered | `instruction.md:19-21`; `test_outputs.py:320-380` |
| Violation types PROHIBITED_COMBINATION / MISSING_GUARD | `test_violations_exact_set` | covered | `instruction.md:17` |
| Severity CRITICAL/WARNING from dossier | `test_violations_exact_set` | **gap** | Dossier table at `validation_dossier.md:456-462` not referenced in `instruction.md:17`; R-009 CRITICAL enforced at `test_outputs.py:229,232` |
| Errata source `errata-<id>` | `test_cfl_rules_exact_values` | covered | `instruction.md:13`; `test_outputs.py:173-175` |
| Idempotent script-driven output | `test_idempotent_and_script_driven` | covered | `test_outputs.py:383+` |
| Sorting rules per report | multiple `*_sorted` / exact-set tests | covered | `instruction.md:9,13,17,21` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blocker 2, spec alignment |
| `task.toml` | #44, #45, blocker 1 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/docs/validation_dossier.md` | blocker 2, long-context, errata severity table |
| `environment/scripts/audit.awk` | broken baseline context |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #28, spec alignment, blocker 2 |
| `solution/solve.sh` | #21, #23, oracle severity lookup (`sev_map` at :67-68) |
| `entire-report.txt` | agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: cargo-solver-static-analysis/ ===
Summary: 0 error(s), 2 warning(s), 1 info
Task type detected: regular
WARN: pinned_dependencies false positive on Dockerfile line continuation
WARN: solution-hints pattern in solve.sh (benign: writes awk script)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | 3 failures all 19/20 on `test_violations_exact_set` |
| terminus-claude-opus-4-8 | 100.0% (5/5) | All runs pass |
| oracle | 100.0% (3/3 report; 1/1 local) | Consistent pass |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% (GPT-5.5) |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `cargo-solver-static-analysis`; regular layout; report matches task |
| 1 Instruction | ☑ | Errata severity lookup gap (#7, #27) |
| 2 Environment | ☑ | Digest-pinned, tmux+asciinema, no tests/solution COPY |
| 3 Oracle | ☑ | Pass 1/1 locally; derives via gawk parsing |
| 4 Verifiers | ☑ | 20 tests, binary reward, no runtime installs |
| 5 Metadata | ☑ | difficulty mismatch (#45) |
| 6 Rubric | N/A | No rubric file in task dir |
| 7 LLMaJ & agent evidence | ☑ | Reconciled report contradictions; GPT systematic R-009 miss |
| 8 Novelty & fairness | ☑ | Multi-step AWK repair; no cheating path found |
| 9 Long context | ☑ | ~299 KB dossier; four formats + decoys; not grep-only |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Dockerfile is digest-pinned, verifier deps are baked in, tests and solution are excluded from the image, and the AWK/static-analysis verifier is strong. The blockers are the Hard/Medium metadata mismatch (worst-model GPT-5.5 at 40%) and the underspecified errata severity lookup: instruction says severity comes from the dossier but does not state that errata-table rows without inline `severity=` must use the separate severity-assignment table (`validation_dossier.md` §10), which caused every GPT-5.5 failure on R-009 CRITICAL vs WARNING. Add one clarifying sentence to `instruction.md` and set `difficulty = "medium"` (or rebalance for hard).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 2 |
| Test Alignment/Coverage Issues | yes | 2 |
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Pinning Issues | no | — |
| Exposing Hints/Answers | no | — |
| Uses Internet | no | — |
| Milestones | no | — |
| Rubric | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review cargo-solver-static-analysis/ --report entire-report.txt`._
