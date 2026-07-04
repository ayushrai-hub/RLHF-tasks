# Terminus Review Report: microgrid-dispatch-planner

**Generated:** 2026-07-03 17:50 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/microgrid-dispatch-planner`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are solid: medium difficulty, digest-pinned offline environment, absolute instruction paths, hashed verifier deps in the image, comprehensive dynamic Rust tests, and oracle passes cleanly. The only real blocker is the platform rubric — six criteria use malformed `Agent's …` phrasing that fails the required `Agent …, ±N` format. Non-milestone flat rubric layout is correct (no spurious `# Rubric 2+` headers). Automated audit false-positives on #14, #20, and #31 were overturned after manual proof.

**Insights (concise):**

- `number_of_milestones = 0`; rubric is a flat 18-line list — **not** milestone-block format.
- Manual rubric positive sum = **38** (within 10–40 cap; not a blocker).
- `environment/requirements.lock` pins pytest with `==` + SHA-256 hashes; Dockerfile installs via `--require-hashes --no-deps` (`environment/Dockerfile:27`).
- Oracle reward 1.0 in ~2 min (`./scripts/terminus oracle`).
- Worst-model pass rate 60% (Claude Opus 4.8) → medium tier; matches `task.toml` and platform classification.
- Input SHA-256 integrity tests enforce `instruction.md:7` “Do not modify any input file” — not an undocumented spec gap.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | Medium | Rubric | #34 | Six platform rubric lines use corrupted `Agent's …` grammar instead of clean `Agent …` action criteria; fail `^Agent .+, ±N` format (missing space after `Agent`). | `entire-report.txt:349-353,357` — e.g. `Agent's respects the max_committed_thermal cap…, +3`; `Agent's reads satisfies the emissions_budget…, +2` | Rewrite all six lines to `Agent <verb> …, ±N` (e.g. `Agent respects the max_committed_thermal cap…, +3`). |

*No High-severity blockers in task zip artifacts (instruction, env, oracle, verifiers, metadata).*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: structural fixes addressed (medium difficulty, .dockerignore, hashed lockfile, absolute paths, allow_internet=false) | Agree | `task.toml:6,24`; `environment/.dockerignore:10-11`; `environment/requirements.lock:1-12`; `environment/Dockerfile:27`; `instruction.md:1-7` |
| 2 | ChatGPT: platform rubric needs cleanup — malformed `Agent's …` phrasing | Agree | `entire-report.txt:349-353,357` — six lines fail `Agent .+, ±N` regex |
| 3 | ChatGPT: optional rubric reward for generalizing across alternate instances | Disagree as blocker | Dynamic instance behavior already tested (`tests/test_outputs.py:331-364`); rubric already has `Agent's reads input files dynamically…, +3` (`entire-report.txt:357`) |
| 4 | ChatGPT: Dockerfile FROM digest-pinned — no base-image blocker | Agree | `environment/Dockerfile:1` `@sha256:01f42367…` |
| 5 | ChatGPT: Decision Needs Revision for rubric wording only | Agree | Only rubric format issue found; task files otherwise pass |
| 6 | entire-report prior feedback: change difficulty hard→medium | Disagree as current blocker | Already `difficulty = "medium"` (`task.toml:6`); platform `Difficulty: ✅ MEDIUM` (`entire-report.txt:23`) |
| 7 | entire-report prior feedback: install verifier deps reproducibly | Disagree as blocker | `requirements.lock` + `--require-hashes` (`environment/Dockerfile:26-27`) |
| 8 | entire-report prior feedback: .dockerignore excludes solution/tests | Disagree as blocker | Already present (`environment/.dockerignore:10-11`) |
| 9 | entire-report prior feedback: convert relative instruction paths | Disagree as blocker | All paths absolute (`instruction.md:1-7`) |
| 10 | LLMaJ instruction sufficiency: hash integrity is undocumented hidden tripwire | Disagree as blocker | `instruction.md:7` forbids modifying input files; `tests/test_outputs.py:127-135` enforces that rule |
| 11 | Automated audit #14: unpinned pip | Disagree | `requirements.lock` uses `==` + hashes; Dockerfile `--require-hashes --no-deps` |
| 12 | Automated audit #20: pytest not in Dockerfile | Disagree | `requirements.lock:9-10` includes `pytest==8.4.1`; installed at build (`environment/Dockerfile:27`); `tests/test.sh` has no runtime installs |
| 13 | Automated audit #31: missing test docstrings | Disagree | All 23 `test_*` methods have docstrings (`tests/test_outputs.py:127-367`) |
| 14 | Automated audit #41: stray audit-report.md | Disagree as submission blocker | Reviewer-generated local artifact, not part of task zip |
| 15 | Automated audit #44: category mismatch → machine-learning | Disagree as blocker | `scientific-computing` fits constrained optimization / dispatch (`task.toml:7`) |
| 16 | Harbor review: scoring model visible by design | Agree (informational) | `instruction.md:5-7` references `model.py`; dynamic tests mitigate hardcoding |
| 17 | Non-milestone task using milestone rubric format | Disagree | `number_of_milestones = 0` (`task.toml:14`); rubric has no `# Rubric 2+` headers (`entire-report.txt:346-363`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~188 words, 4 prose blocks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt | Conversational microgrid scenario, not spec tables | `instruction.md:1-7` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States WHAT (finish Rust dispatcher), not HOW steps | `instruction.md:3-7` |
| 5 | CHECK | No hints or solving strategies | References docs/model for contract; no algorithm walkthrough | `instruction.md:5-7` |
| 6 | CHECK | No design-doc input/output tables | None | `instruction.md` |
| 7 | CHECK | Instruction well specified | Paths, constraints, score thresholds, dynamic reruns specified | `instruction.md:1-7` |
| 8 | CHECK | Instruction is interesting | Realistic islanded microgrid dispatch optimization | `instruction.md:1` |
| 9 | UNCHECK | Instruction is unique | Cannot verify vs TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | All paths absolute | Only `/app/...` paths | `instruction.md:1-7` |
| 11 | CHECK | Task name not in instruction | Name absent | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch in env | No runtime fetch in task code | `environment/` |
| 14 | CHECK | Python/pip deps pinned with == | `requirements.lock` exact versions + hashes | `environment/requirements.lock`, `environment/Dockerfile:27` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | COPY only `task_file` | `environment/Dockerfile:29` |
| 17 | CHECK | No ground truth answers in env | Skeleton dispatcher + public inputs only | `environment/task_file/dispatcher/src/dispatch.rs` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not conflict with Harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh no runtime installs | pytest in lockfile; test.sh only runs pytest | `environment/Dockerfile:27`, `tests/test.sh:22-24` |
| 21 | CHECK | Oracle passes consistently | reward=1.0 | `./scripts/terminus oracle` 2026-07-03 |
| 22 | CHECK | Oracle no internet at runtime | solve.sh compiles/runs Rust locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective of instruction | Implements greedy dispatch algorithm in Rust | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt on pass/fail | Canonical 0-then-1 pattern | `tests/test.sh:7,26-29` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:26-29` |
| 27 | CHECK | Tests aligned with instructions | All instruction requirements traced to tests | §5 below |
| 28 | CHECK | Tests check correctness | Numeric constraint/score assertions | `tests/test_outputs.py:180-302` |
| 29 | CHECK | Tests verify behavior not implementation | No source grep; runs binary + model | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Threshold/range checks | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative docstrings | 23/23 test methods documented | `tests/test_outputs.py:127-367` |
| 32 | CHECK | Rubric ≥3 negative penalties | Three negatives (-3, -3, -5) | `entire-report.txt:361-363` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All lines use valid magnitudes | `entire-report.txt:346-363` |
| 34 | UNCHECK | Each rubric line `Agent …, ±N` | Six malformed `Agent's …` lines | `entire-report.txt:349-353,357` |
| 35 | CHECK | Rubric criteria detailed; positive cap | 38 positive pts (≤40); 18 criteria | `entire-report.txt:346-363` |
| 36 | CHECK | Rubric positive language for positives | No `Agent does not …, +N` | `entire-report.txt:346-360` |
| 37 | CHECK | Rubric no /tests/ references | None | `entire-report.txt:346-363` |
| 38 | CHECK | Rubric no task.toml/instruction.md refs | None | `entire-report.txt:346-363` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:346-363` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task zip | task root |
| 42 | CHECK | author_name/email present | anonymous fields set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | rust optimization dispatch; scientific-computing | `task.toml:7-13` |
| 45 | CHECK | Difficulty matches agent rates | medium / medium / worst 60% | `task.toml:6`, `entire-report.txt:23-29` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:14` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:14` |
| 49 | UNCHECK | Milestone tests scoped | N/A | `task.toml:14` |
| 50 | CHECK | Tests not baked into image | .dockerignore excludes tests/ | `environment/.dockerignore:11` |
| 51 | CHECK | Solution not accessible in env | .dockerignore excludes solution/ | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially cheat via input mutation | Hash integrity + dynamic instances | `tests/test_outputs.py:127-135,331-364` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst-model 60% | `entire-report.txt:27-29` |
| 55 | CHECK | Not too hard/unfair | Spec complete in instruction + dataflow.md; oracle passes | `instruction.md`, oracle run |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 34, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `dispatch.json` at `/app/task_file/output_data/` | `test_output_file_exists` | covered | `instruction.md:3`, `tests/test_outputs.py:146-148` |
| Schema per `dataflow.md` | `test_plan_is_object`, `test_allocations_cover_all_units_uniquely`, `test_frequency_setpoint_in_range` | covered | `tests/test_outputs.py:152-175` |
| Hard constraints (demand, emissions, renewable, buses, reserve, conflicts, mandatory, thermal cap) | `TestHardConstraints` (8 tests) | covered | `instruction.md:5`, `tests/test_outputs.py:180-271` |
| `total_score >= 0.99` + subscore floors | `test_total_score`, `test_primary_subscores` | covered | `instruction.md:7`, `tests/test_outputs.py:275-292` |
| `total_score_strict >= 0.92` | `test_strict_score` | covered | `instruction.md:7`, `tests/test_outputs.py:296-302` |
| Dynamic instances raw ≥0.985 / strict ≥0.91 | `test_dynamic_input_not_hardcoded`, `test_tight_commitment_input_not_hardcoded` | covered | `instruction.md:7`, `tests/test_outputs.py:331-389` |
| Rust binary implementation (not hardcoded JSON) | `test_cargo_toml_exists`, `test_compiled_binary_exists`, `test_binary_produces_output` | covered | `instruction.md:3`, `tests/test_outputs.py:306-329` |
| Do not modify input files / model.py | `test_units_hash`, `test_config_hash`, `test_model_script_not_tampered` | covered | `instruction.md:7`, `tests/test_outputs.py:127-142` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #27, spec alignment |
| `task.toml` | #14, #45, milestone N/A |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #28, #31, spec alignment |
| `solution/solve.sh` | #21, #23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: microgrid-dispatch-planner/ ===
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | `entire-report.txt:29` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 1 timeout, 1 other |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle 2026-07-03 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | medium |
| Platform classified | medium |
| Tier match (#45) | yes (informational) |

### Rubric positive points (manual full parse)

| Field | Value |
|-------|-------|
| Source | `entire-report.txt:346-363` (full flat rubric) |
| Positive point total | **38** |
| Negative criteria | 3 (-3, -3, -5) |
| Cap status | PASS (≤40) |
| Milestone blocks | None (non-milestone flat list) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `microgrid-dispatch-planner`; rust/scientific-computing |
| 1 Instruction | ☑ | Concise, absolute paths, no hints |
| 2 Environment | ☑ | Digest-pinned, offline, hashed lockfile, tmux/asciinema |
| 3 Oracle | ☑ | Passes; implements real Rust dispatch |
| 4 Verifiers | ☑ | 23 tests, docstrings, dynamic anti-cheat, no runtime installs |
| 5 Metadata | ☑ | medium, allow_internet=false, number_of_milestones=0 |
| 6 Rubric | ☐ | Flat format correct; 6 malformed lines block #34 |
| 7 LLMaJ & agent evidence | ☑ | behavior_in_* pass; 60% worst-model; spec-gap claim rejected |
| 8 Novelty & fairness | ☑ | Multi-constraint optimizer; not trivially cheatable |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the Rust dispatch skeleton, dynamic instance testing, and offline Dockerfile setup are all in great shape, and the oracle passes cleanly at medium difficulty. The only thing holding this back is the platform rubric wording: six criteria still read like `Agent's respects…` / `Agent's reads satisfies…` instead of clean `Agent …` action lines. Please rewrite those six lines so every criterion starts with `Agent` followed by a verb (e.g. `Agent respects the max_committed_thermal cap…, +3`). Everything else looks ready.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |

---

_Generated by `./scripts/terminus review` and enriched via manual audit per `prompt.md`._
