# Terminus Review Report: `parallel-solver-divergence-mask`

**Generated:** 2026-06-24 19:05 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/parallel-solver-divergence-mask`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | fail |
| **CHECK count** | 39 |
| **UNCHECK count** | 16 |

**Error categories (internal):** Oracle Solution Issues, Task Difficulty

**Decision (concise):** Prior portal blockers (difficulty metadata, `test.sh` reward path) are fixed in artifacts, but the oracle does **not** pass locally: `./scripts/terminus oracle` yields reward 0 with 5/21 gates failing on `audit_chain` / `fold_token` full-contract checks—the same failure cluster agents hit. ChatGPT’s Accept verdict and the platform’s “oracle 100%” claim are not supported by current files. Fix `solution/solve.sh` (or contract/reference alignment) until oracle passes all gates; optionally retier difficulty (worst model 80% = easy band).

**Insights (concise):**

- `task.toml:5` now declares `medium`; `tests/test.sh:3-4,15-18` correctly initializes `/logs/verifier/reward.txt` and writes binary reward.
- Dockerfile digest `4724b8cc…` matches canonical `debian:bookworm-slim` in `docs/guidelines/dockerfxile.md` — external “non-canonical base” claim is incorrect for this digest.
- Automated `#14` / `#31` failures from `terminus review` are false positives: pip packages are `==`-pinned (`environment/Dockerfile:17-19`); `test_acceptance_gate` has a docstring (`tests/test_outputs.py:92`).
- Verifier design is strong: hidden C++ reference model, `cases_csv_immutable`, rebuild-from-source anti-cheat.
- Worst-model Claude 80% sits at the easy-tier ceiling per `docs/guidelines/difficulty.md`; declared `medium` is borderline for #45.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Oracle Solution Issues | #21, #23 | Oracle fails 5/21 verifier gates locally (reward 0) | `./scripts/terminus oracle parallel-solver-divergence-mask/` → `jobs/2026-06-24__18-53-23/.../verifier/reward.txt` = `0`; `test-stdout.txt` lines 255-259: `worker_antipode_blob_lock`, `parallel_full_contract_worker_sweep`, `audit_chain_antipode_lock`, `continue_fresh_parity_with_journal`, `continued_report_neutral_parity` failed with `audit_chain mismatch` / `fold_token mismatch` | Repair `solution/solve.sh` until `./scripts/terminus oracle` passes all 21 gates; confirm `assert_full_contract` in `tests/verifier/harness.cpp:185-204` passes for hard seeds |
| 2 | Medium | Task Difficulty | #45 | Declared `medium` vs worst-model 80% (easy band) | `task.toml:5` `difficulty = "medium"`; `entire-report.txt:19` Claude 80% (4/5); `docs/guidelines/difficulty.md:11` easy = 60–80% worst model | Set `difficulty = "easy"` or rebalance task until worst-model rate falls into 20–60% for medium |

*No other High-severity blockers found on static audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept; prior blockers fixed | **Partially agree** | `task.toml:5` medium ✓; `tests/test.sh:3-18` reward ✓; but oracle still fails (#1 above) — cannot Accept |
| 2 | ChatGPT: digest-pinned Dockerfile solid | **Agree** | `environment/Dockerfile:1` `@sha256:4724b8cc…`; matches `docs/guidelines/dockerfxile.md:22` canonical debian digest |
| 3 | ChatGPT: spec-to-test alignment solid | **Agree** | `entire-report.txt:117-119` quality checks; manual trace: `report_contract.md:31-69` ↔ gates in `tests/verifier/main.cpp` |
| 4 | ChatGPT: oracle pass rate 100% | **Disagree** | Local `./scripts/terminus oracle` reward 0, 16/21 passed (`jobs/2026-06-24__18-53-23/.../verifier/test-stdout.txt:255-260`) |
| 5 | Prior reviewer: difficulty hard vs medium | **Agree (fixed)** | Was `hard`; now `task.toml:5` `medium` |
| 6 | Prior reviewer: test.sh missing reward init | **Agree (fixed)** | `tests/test.sh:3-4` mkdir + `echo 0`; final write `15-18` |
| 7 | LLMaJ report: non-canonical Docker base (CRITICAL) | **Disagree** | Same digest as canonical `public.ecr.aws/docker/library/debian:bookworm-slim` in `scripts/validate_task.py:73`; image name differs but digest is sanctioned |
| 8 | LLMaJ report: verifier timeout may be tight | **Partially agree** | `task.toml:20` 900s; local run 196.75s for 5 failures — sufficient locally; monitor on 2-CPU CI |
| 9 | Platform: Difficulty MEDIUM, solvable | **Partially agree** | `entire-report.txt:14-16`; solvable yes; tier arguable given 80% worst model |
| 10 | Agent analysis: no spec gaps, audit_chain is hard wall | **Agree** | `entire-report.txt:84-87`; matches oracle/agent shared failure pattern |
| 11 | Quality: behavior_in_tests PASS | **Agree** | `entire-report.txt:119`; 21 gates cover contract requirements |
| 12 | Submitter: non-canonical base justified | **Partially agree** | Justification in `entire-report.txt:356-358` only — not in Dockerfile/README; digest is canonical anyway |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~9 sentences, no essay | `instruction.md:1-9` |
| 2 | CHECK | Natural prompt tone | Problem statement, not spec template | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | No headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | Single rebuild command is stated requirement, not bug walkthrough | `instruction.md:7-8` |
| 5 | CHECK | No hints / HOW leakage | Points to contract schema only | `instruction.md:3` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Outputs, workers, journal, checkpoint reqs testable | `instruction.md:3-9`, `report_contract.md` |
| 8 | CHECK | Interesting task | Real C++ parallel numerics debugging | — |
| 9 | UNCHECK | Unique vs corpus | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...`, `/usr/local/bin/tb_iter` | `instruction.md:1-7` |
| 11 | CHECK | Task name not in instruction | No task slug | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No web content fetch | Local data only | `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:17-19` |
| 15 | CHECK | Base image digest-pinned | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Canonical base (digest match) | Same digest as sanctioned debian bookworm | `docs/guidelines/dockerfxile.md:22` |
| 17 | CHECK | No ground truth in env | Contract is normative schema, not answers | `environment/docs/report_contract.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh only pytest | `environment/Dockerfile:17-19`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Local oracle 16/21, reward 0 | `jobs/2026-06-24__18-53-23/.../verifier/test-stdout.txt` |
| 22 | CHECK | Oracle no internet | sed/cmake only | `solution/solve.sh` |
| 23 | UNCHECK | Oracle reflects instruction | Patches source but incomplete — 5 gates fail | Blocker #1 |
| 24 | CHECK | test.sh reward.txt canonical | mkdir, init 0, CTRF, final 0/1 | `tests/test.sh:3-18` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branch | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:15-18` |
| 27 | CHECK | Tests aligned with instructions | All contract reqs gated | §5 below |
| 28 | CHECK | Tests check correctness | C++ reference model comparisons | `tests/verifier/harness.cpp:185-204` |
| 29 | CHECK | Behavior not implementation grep | Runtime tb_iter execution | `tests/test_outputs.py:76-87` |
| 30 | CHECK | No brittle string matching | Exact fold_token required by contract | `report_contract.md:44` |
| 31 | CHECK | Informative test docstrings | Module + per-test docstring | `tests/test_outputs.py:1-7,92` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task dir | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | — |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, env, tags | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | c++, scientific-computing, mpi | `task.toml:6-9` |
| 45 | UNCHECK | Difficulty matches pass rates | medium declared; worst 80% = easy band | `task.toml:5`, `entire-report.txt:19`, `difficulty.md:11` |
| 46 | UNCHECK | Milestone layout | N/A `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | — |
| 48 | UNCHECK | test_mN.py per milestone | N/A | — |
| 49 | UNCHECK | Milestone scope | N/A | — |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile:21-31` |
| 51 | CHECK | Solution not in environment | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially edit inputs | SHA256 gate | `report_contract.md:29`, gate `cases_csv_immutable` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst 80% ≤ 80% threshold | `entire-report.txt:19` |
| 55 | CHECK | Not unfair / impossible | Spec complete; failures are implementation precision | `entire-report.txt:84-87` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 23, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Worker invariance workers 2–10 | `worker_antipode_blob_lock`, `parallel_full_contract_worker_sweep` | covered | `tests/verifier/main.cpp` gates; `instruction.md:8` |
| fold_token exact `%.8f` global | `fold_token_exact_precision_sweep` | covered | `report_contract.md:41-44` |
| Weight bump before renorm | `weight_pre_renorm_precision_seeds` | covered | `report_contract.md:33-35` |
| objective cross-worker invariant | `objective_cross_worker_invariance` | covered | `report_contract.md:37` |
| audit_chain contract | `audit_chain_antipode_lock` | covered | `report_contract.md:46` |
| fresh/continued parity | `continue_fresh_parity_with_journal`, `continued_report_neutral_parity` | covered | `report_contract.md:48,56-57` |
| phase_id +1 per hop | `journal_eight_hop_phase_ladder` | covered | `report_contract.md:52-54` |
| Journal reject bad tail | `journal_*_rejects*` gates | covered | `report_contract.md:54` |
| Checkpoint full double precision | `checkpoint_precision_roundtrip` | covered | `report_contract.md:73-75` |
| cases.csv immutable | `cases_csv_immutable` | covered | `report_contract.md:29` |
| Layout flag neutrality | `layout_dual_flag_invariance` | covered | `report_contract.md:79-81` |
| Runtime validation (workers<2, bad load) | `runtime_validation_matrix` | covered | `report_contract.md:48` |
| Dispersion formula global max-min | `dispersion_objective_formula_grid` | covered | `report_contract.md:41,64-65` |
| Rebuild from source required | `rebuild_agent_binary` | covered | `instruction.md:7-8` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, §5 |
| `task.toml` | #42-45, blocker 2 |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/docs/report_contract.md` | §5, #17 |
| `tests/test.sh` | #24, prior blocker fix |
| `tests/test_outputs.py` | #31, #29 |
| `tests/verifier/harness.cpp` | Blocker #1, §5 |
| `solution/solve.sh` | Blocker #1, #22-23 |
| `entire-report.txt` | §3, #45, #54 |
| `jobs/2026-06-24__18-53-23/.../verifier/test-stdout.txt` | Blocker #1 oracle proof |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate parallel-solver-divergence-mask/
Summary: 0 error(s), 2 warning(s), 2 info
```

Warnings: false-positive pip docstring linter noise; milestone preference info.

### Oracle (local)

```
./scripts/terminus oracle parallel-solver-divergence-mask/
reward = 0.0 — 5 failed, 16 passed (196.75s)
```

### Agent performance (from report)

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | `entire-report.txt:20` |
| terminus-claude-opus-4-8 | 80.0% (4/5) | worst model |
| oracle (platform) | 100.0% (3/3) | **contradicted by local run** |
| nop | 0.0% | baseline |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst model) | easy (60–80% band) |
| Declared difficulty | medium |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; C++ scientific-computing |
| 1 Instruction | ☑ | Concise; contract reference; absolute paths |
| 2 Environment | ☑ | Digest-pinned canonical debian; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☐ | **Fails locally 5/21** — blocker |
| 4 Verifiers | ☑ | reward.txt, CTRF, C++ gates, no runtime installs |
| 5 Metadata | ☑ | Prior difficulty fix applied; #45 borderline |
| 6 Rubric | ☑ | Portal rubric in report only; N/A in task dir |
| 7 Agent evidence | ☑ | MEDIUM platform tier; shared audit_chain failure mode |
| 8 Novelty & fairness | ☑ | Multi-bug C++ debug; anti-cheat solid |
| 9 Long context | ☑ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The prior blockers are addressed (`task.toml` medium, `test.sh` reward/CTRF path), and verifier design is excellent—but `./scripts/terminus oracle` fails 5/21 gates (`audit_chain` / `fold_token` full-contract mismatches), the same wall agents hit. Repair `solution/solve.sh` until oracle passes 21/21. Optionally retier difficulty: worst-model Claude is 80% (easy band) while metadata says medium.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Oracle Solution Issues | yes | 1 |
| Task Difficulty | yes | 2 |
| Test Build Issues | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Instruction Styling | no | — |
| Metadata Issues | no | — |
| Rubric | no | N/A in task dir |
