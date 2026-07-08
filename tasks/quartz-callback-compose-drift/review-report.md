# Terminus Review Report: `quartz-callback-compose-drift`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 1 info-level pip heuristic false positive) |
| **Oracle** | pass (platform report 3/3; local oracle not run — Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Task is a well-designed hard Rust debugging/integration task with a clear contract, digest-pinned offline environment, dynamic anti-hardcoding tests, independent Python model, and platform oracle 100%. Automated audit flagged #14 (pip) and #41 (stray files) as false positives on manual re-read. Rubric uses correct flat non-milestone format at 26/40 positive points. No blocking spec, rubric, test-alignment, or difficulty issues found.

**Insights (concise):**

- Instruction normatively references `contract.md` and `schema_stub.json`; carry formula, step-0 hook semantics, restart-before-callbacks ordering, and digest formatting are all specified there and exercised by tests.
- Platform rubric is a flat `Agent …, ±N` list (no `# Rubric 2+` milestone blocks) — correct for `number_of_milestones = 0`.
- Worst-model pass rate 20% (GPT-5.5) aligns with declared/platform `hard` tier; Claude Opus 4.8 at 100% does not block.
- Automated `#27` phantom-threshold warning (`4`, `6`, `11`) is a heuristic false positive: values are contract-derived model outputs or redundant anti-static guards, not unstated requirements.
- `Cargo.toml` uses `serde = "1"` major-version constraints; mitigated by `Cargo.lock` and `cargo build --locked` in Dockerfile, solution, and tests — Low only.
- Agent failure cluster (carry scaling, step-0 hook crossing, restart-before-callbacks) matches documented contract semantics — implementation misses, not spec gaps.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High severity: none found (ChatGPT) | Agree | Manual artifact review: instruction ↔ contract ↔ 39 tests aligned; no untested enforced requirements |
| 2 | Medium severity: none found (ChatGPT) | Agree | Rubric 26/40; both artifacts named in `instruction.md:1-4`; verifier covers dynamic + static paths |
| 3 | Low: Cargo.toml broad `serde = "1"` / `serde_json = "1"` (ChatGPT) | Partially agree | `environment/Cargo.toml:7-8` uses major-version pins; `Cargo.lock` + `--locked` in `Dockerfile:32`, `test_outputs.py:232`, `solve.sh` mitigates — Low, not blocking |
| 4 | Low: add worked mini-example for carry/step-0 hooks (ChatGPT) | Agree | Optional clarity polish; semantics already in `contract.md:19-21,32` — not a blocker |
| 5 | Dockerfile FROM digest-pinned (ChatGPT) | Agree | `environment/Dockerfile:1` — `@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` |
| 6 | Canonical base image appropriate for Rust task (ChatGPT) | Agree | Rust ODE harness requires Rust toolchain; digest-pinned `rust:1.85-slim` justified; tmux + asciinema at `Dockerfile:11-12` |
| 7 | Decision: Accept (ChatGPT) | Agree | Artifacts support accept after false-positive audit items dismissed |
| 8 | Error categories: none (ChatGPT) | Agree | No High/Medium blockers on manual re-audit |
| 9 | Non-canonical Rust base image warning (Harbor review) | Partially agree | `entire-report.txt:181-199` — advisory only; digest-pinned Rust base is appropriate; not blocking per `reviewer-checklist-full.md` canonical-base rule for language-specific tasks |
| 10 | Unpinned serde in Cargo.toml (Harbor review) | Partially agree | `entire-report.txt:202-227` — same as claim #3; Low with Cargo.lock mitigation |
| 11 | Checkpoint file vs memory test completeness (Harbor suggestion) | Disagree as blocker | `entire-report.txt:234-250` — suggestion only; `test_checkpoint_file_drives_carry_not_memory_only` + mutation tests adequately cover carry behavior |
| 12 | Test quality: ACCEPT, robust (Harbor) | Agree | 39 `test_*` functions with docstrings; independent Python model; dynamic nonce variants |
| 13 | LLMaJ `behavior_in_task_description` PASS | Agree | `instruction.md:4` references contract; `contract.md` covers all tested semantics |
| 14 | LLMaJ `behavior_in_tests` PASS | Agree | Tests cover pipeline, probes, mutations, schema, checkpoint carry, anti-static |
| 15 | Instruction sufficiency PASS (agent failure analysis) | Agree | `entire-report.txt:111-118` — failures on carry/hook/restart semantics documented in `contract.md` |
| 16 | Audit #14 FAIL unpinned pip | Disagree | `environment/Dockerfile:15-17` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` are `==`-pinned; validator regex false positive on multiline RUN |
| 17 | Audit #27 FAIL phantom thresholds [4,6,11] | Disagree | `4`/`6` are fixture-derived model outputs (`ode_plan.tbl:5-6,10-11`); `6` decimals in `contract.md:47`; `>= 11` redundant with `len == len(plan)` at `test_outputs.py:543-544` |
| 18 | Audit #41 FAIL stray `audit-report.md` | Disagree | `audit-report.md` is reviewer-tool output, not author submission artifact; task parent has only standard files |
| 19 | Non-milestone task using milestone rubric format (user concern) | Disagree | `entire-report.txt:336-347` — flat `Agent …, ±N` list with no `# Rubric N` headers; correct non-milestone format per `docs/guidelines/rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 paragraphs, ~181 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem statement, not spec dump | `instruction.md:1-4` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States goal/artifacts, not patch order | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | WHAT not HOW; contract is normative spec | `instruction.md:4` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | CHECK | Well specified | Clear outputs, paths, checkpoint carry reference | `instruction.md:1-4` |
| 8 | CHECK | Interesting/useful | Rust ODE callback debugging for scientific computing | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3/Edition 1 index from artifacts | — |
| 10 | CHECK | Absolute paths only | All `/app/...` paths | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No `quartz-callback-compose-drift` string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local data/docs only | `environment/` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15-17` |
| 15 | CHECK | FROM digest-pinned | `@sha256:9f841…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | All COPY from env subdirs | `environment/Dockerfile:19-26` |
| 17 | CHECK | No ground-truth answers in env | `contract.md` is published spec; buggy code has no golden outputs | `environment/docs/contract.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter Harbor mounts | No docker-compose.yaml | `task.toml` |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh only runs pytest | `Dockerfile:15-17`, `tests/test.sh:13-14` |
| 21 | CHECK | Oracle passes consistently | Platform report oracle 100% (3/3) | `entire-report.txt:32` |
| 22 | CHECK | Oracle no internet | Patches source + `cargo build --locked` | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective, not hardcoded | Multi-file Rust patches then rebuild/run | `solution/solve.sh:20-80+` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 with failure path | `tests/test.sh:11-20` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:16-19` |
| 27 | CHECK | Tests aligned with instructions | All assertions trace to `instruction.md` + normative `contract.md` | `contract.md:17-49`, `test_outputs.py` |
| 28 | CHECK | Tests check correctness | Independent Python model + probe integration | `test_outputs.py` `_model()` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Model-computed expectations; schema checks from contract | `test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 39 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:344-347` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:336-347` |
| 34 | CHECK | Rubric `Agent …, ±N` format | 12 properly formatted lines | `entire-report.txt:336-347` |
| 35 | CHECK | Rubric detailed; positive cap | 26 positive pts ≤ 40 | `entire-report.txt:336-342` |
| 36 | CHECK | Positive phrasing on positive scores | No inverted positive lines | `entire-report.txt:336-342` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:336-347` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | `entire-report.txt:336-347` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:336-347` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | Only standard task files (reviewer-generated reports excluded) | task root |
| 42 | CHECK | author_name/email present | Both `anonymous` | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust/scientific-computing/ode | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `hard`; worst-model 20% → hard tier | `task.toml:6`, `entire-report.txt:22-28` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked in image | No COPY tests/; .dockerignore excludes | `environment/Dockerfile`, `.dockerignore:13` |
| 51 | CHECK | Solution not in environment | .dockerignore excludes solution/ | `environment/.dockerignore:12` |
| 52 | CHECK | Agent can't trivially cheat via inputs | Dynamic nonce plan swaps + model verification defeat static tampering | `test_outputs.py:242-254`, `test_dynamic_variant_defeats_hardcoded_solution` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:27-28` |
| 55 | CHECK | Not too hard/unfair | Full contract available; agent failures are implementation bugs | `contract.md`, `entire-report.txt:111-118` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Rebuild release binaries `ode_harness` + `ode_probe` | `test_rebuild_locked_binary_runs_not_stale_script` | covered | `instruction.md:2`, `test_outputs.py` |
| Output `run_summary.json` with schema fields | `test_schema_json_exact_field_types_and_layout` | covered | `instruction.md:4`, `contract.md:47-48` |
| Output `trace.csv` with column order + booleans | `test_schema_csv_column_order_and_boolean_spelling` | covered | `contract.md:49`, `test_outputs.py:602-614` |
| Checkpoint `ode_checkpoint.json` carry across rows | `test_checkpoint_carry_couples_later_row_metrics`, `test_checkpoint_file_drives_carry_not_memory_only` | covered | `instruction.md:2`, `contract.md:17-21` |
| Euler `y_{n+1} = y_n - dt*y_n` | `test_probe_euler_secondary`, `test_pipeline_matches_independent_model` | covered | `contract.md:25-26` |
| Hook crossing `y_prev < threshold <= y`; step 0 uses `y0` | `test_probe_event_step0_and_boundary`, `test_step0_y0_only_requires_y0_not_post_euler` | covered | `contract.md:32` |
| Sort by load_order; registration tiebreak | `test_probe_sort_tiebreak_secondary`, `test_order_sensitive_tie_flip_interaction` | covered | `contract.md:31` |
| Restart before callbacks on restart_step | `test_probe_restart_and_metric_overlay`, `test_probe_chain_restart_before_callbacks_secondary` | covered | `contract.md:30-31` |
| Carry formula `metric_scale * (1 + carry_gain * last_event_step)` | `test_mutation_carry_gain_scales_order_sensitive_only`, `test_checkpoint_carry_couples_later_row_metrics` | covered | `contract.md:21` |
| Digest six-decimal lowercase tokens | `test_schema_digest_six_decimal_lowercase_tokens` | covered | `contract.md:47` |
| `summary_ok` = AND of sub-checks | `test_schema_summary_ok_requires_all_subchecks_and` | covered | `contract.md:39,47` |
| Anti-static / dynamic inputs defeat hardcoding | `test_dynamic_variant_defeats_hardcoded_solution`, `test_anti_static_plan_row_count` | covered | `contract.md:53`, `instruction.md:4` |
| `len(cases) >= 11` hardcoded guard | `test_anti_static_plan_row_count` | phantom (redundant) | `test_outputs.py:544` — redundant with `== len(_read_plan())` at `:543`; not blocking |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #43-45, #46-49 N/A |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/Cargo.toml` | adjudication #3 |
| `environment/Cargo.lock` | adjudication #3 |
| `environment/docs/contract.md` | #17, #27, spec alignment |
| `environment/docs/schema_stub.json` | #7, spec alignment |
| `environment/data/ode_plan.tbl` | adjudication #17 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: quartz-callback-compose-drift/ ===
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

Warning `pinned_dependencies` is false positive — pip packages use `==` at `Dockerfile:16-17`.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Lowest per-test pass rates: `test_pipeline_matches_independent_model` 60%, `test_checkpoint_carry_couples_later_row_metrics` 60%, `test_semantic_restart_chain_within_step_recheck` 60% — consistent with carry/restart contract semantics, not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `quartz-callback-compose-drift` matches report; regular layout; Rust/scientific-computing |
| 1 Instruction | ☑ | Concise, absolute paths, references contract; no hints |
| 2 Environment | ☑ | Digest-pinned Rust base; tmux+asciinema; allow_internet=false; no tests/solution COPY |
| 3 Oracle | ☑ | Derives via patches + rebuild; platform 3/3 pass |
| 4 Verifiers | ☑ | 39 tests; canonical reward block; no runtime installs; independent model |
| 5 Metadata | ☑ | Complete task.toml; number_of_milestones=0 |
| 6 Rubric | ☑ | Flat non-milestone format; 26/40 positives; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; failures are implementation misses |
| 8 Novelty & fairness | ☑ | Multi-module debugging; anti-cheat strong; fair contract |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The instructions are clear and point to a solid contract, the environment is well set up with a digest-pinned Rust base and verifier deps baked into the image, and the test suite is exceptionally thorough — independent Python model, dynamic anti-hardcoding, mutation sensitivity, and probe coverage all make cheating impractical. Oracle passes cleanly on platform runs and agent rates look right for hard difficulty (GPT-5.5 at 20%, well within calibration). I didn't find blocking spec gaps, rubric issues, or format problems — the rubric is correctly flat for a non-milestone task at 26 positive points. Optional polish only: a short worked example for checkpoint carry or step-0 hook semantics could help future agents, and exact crate version pins in Cargo.toml would match pip-level pinning style (already mitigated by Cargo.lock).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
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

---

_Report enriched after manual audit per `prompt.md`. Baseline generated by `./scripts/terminus review`._
