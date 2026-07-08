# Terminus Review Report: `windowed-float-checkpoint-drift`

**Generated:** 2026-07-04 20:35 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/windowed-float-checkpoint-drift`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3; local run blocked by Docker socket) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Rust checkpoint/resume debugging task with clear instruction + operator_notes, digest-pinned offline env, 20 behavioral tests, and 34/40 rubric positive points. One real blocker: platform rubric line references `/tests/test_outputs.py` (#37, High). Automated #14 pip-pin FAIL is a false positive — packages use `==` on subsequent Dockerfile lines. Rubric is correctly **flat** (not milestone-block format). Difficulty metadata mismatch is informational only.

**Insights (concise):**

- ChatGPT “Accept / no blockers” missed the rubric `/tests/` path violation; everything else largely holds.
- Non-milestone rubric is a single flat `Agent …, ±N` list (no `# Rubric 2+` headers) — correct format.
- Dockerfile pins `pytest==8.4.1` and `pytest-json-ctrf==0.3.5`; audit #14 fails only because `==` is not on the `pip install` continuation line.
- Worst-model pass rate 60% (GPT-5.5) → medium tier; not too easy (#54 passes).
- Platform oracle 100% (3/3); local `./scripts/terminus oracle` failed on Docker socket permission in this environment.
- `environment/ref/oracle_m7.rs` is in-pipeline reference code, not leaked golden answers; operator_notes are normative spec.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #37 | Platform rubric references `/tests/test_outputs.py` | `entire-report.txt:333` — `Agent changes verifier tests or /tests/test_outputs.py as the primary fix instead of repairing environment source, -3` | Reword on platform rubric without `/tests/` or pytest paths, e.g. “Agent changes verifier test files as the primary fix instead of repairing environment source, -3” |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: High severity none; Accept | Partially agree | Task quality is strong, but rubric `/tests/` reference is High per `docs/reviewer-checklist-full.md` — missed by ChatGPT |
| 2 | ChatGPT: Medium severity none | Agree | No spec↔test gaps, reward path, or >40 rubric cap found |
| 3 | ChatGPT: Low — Cargo semver not exact `=` pins | Agree | `environment/Cargo.toml` uses caret semver; `Cargo.lock` + no `cargo update` in Dockerfile mitigates — Low only |
| 4 | ChatGPT: Low — platform MEDIUM vs task.toml hard | Agree | `task.toml:6` `hard`; `entire-report.txt:31` MEDIUM — not a blocker per prompt.md |
| 5 | ChatGPT: Low — expand test docstrings | Agree | All 20 `test_*` have docstrings (`tests/test_outputs.py:359+`); expansion optional |
| 6 | ChatGPT: Dockerfile digest pinning Yes | Agree | `environment/Dockerfile:1` `@sha256:9f841bbe…` |
| 7 | ChatGPT: flat non-milestone rubric, 34 pts | Agree | `entire-report.txt:317-333` flat list, no `# Rubric N` blocks; sum +2×1 + +3×10 + +2×2 = 34 |
| 8 | entire-report LLMaJ: all quality checks pass | Agree | Verified instruction↔tests, anti-cheat, pinned deps, no tests in image |
| 9 | entire-report REVIEW REPORT: non-canonical base image warning | Disagree as blocker | Digest-pinned Rust 1.85-slim is appropriate; no canonical-list mismatch cited |
| 10 | entire-report REVIEW REPORT: unpinned Cargo.toml | Agree as Low | Same as claim 3 |
| 11 | entire-report: instruction sufficiency PASS | Agree | WAL salvage, combine_rank monotonicity, generation fields documented in `operator_notes.md:29-31,69` |
| 12 | User concern: non-milestone task in milestone rubric format | Disagree | `task.toml:11` `number_of_milestones = 0`; rubric has no `# Rubric 2+` headers — flat list is correct |
| 13 | Automated audit #14 unpinned pip | Disagree | `environment/Dockerfile:27-28` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; audit regex only checks the `pip install` line |
| 14 | Automated audit #37 rubric /tests/ | Agree | Same as blocker 1 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 6 short prose blocks, ~234 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem-first debugging brief, not spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no heavy formatting | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcomes and artifact paths only | `instruction.md` |
| 5 | CHECK | No solving hints in instruction | Prohibitions listed; normative detail deferred to operator_notes | `instruction.md:3-5` |
| 6 | CHECK | No design-doc tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, outputs, parity bands referenced | `instruction.md:5-11` |
| 8 | CHECK | Interesting | Realistic streaming checkpoint/resume debugging | task content |
| 9 | UNCHECK | Unique | Cannot verify against full TB corpus from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/output/…` | `instruction.md` |
| 11 | CHECK | Task name absent | No “windowed-float-checkpoint-drift” in instruction | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch | Offline Rust/Python env | `environment/` |
| 14 | CHECK | Pip deps pinned with == | Packages pinned on lines after pip install | `environment/Dockerfile:27-28` |
| 15 | CHECK | FROM digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context within environment/ | All COPY from environment tree | `environment/Dockerfile` |
| 17 | CHECK | No ground-truth leakage | operator_notes are normative spec; ref module is source to debug | `environment/docs/operator_notes.md`, `environment/ref/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh does not install | `environment/Dockerfile:25-28`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:41` |
| 22 | CHECK | Oracle offline | solve.sh patches source + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Rewrites Rust modules then rebuilds/runs binary | `solution/solve.sh:6+` |
| 24 | CHECK | reward.txt canonical block | Writes 0 first, 1/0 after pytest | `tests/test.sh:7-22` |
| 25 | CHECK | Same verifier for agent/oracle | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:18-21` |
| 27 | CHECK | Tests aligned with instructions | Behaviors in instruction + operator_notes exercised | §5 below |
| 28 | CHECK | Correctness not format-only | End-to-end CLI + numeric parity | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Invokes binary, compares artifacts | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Numeric tolerance bands | `tests/test_outputs.py:23-27` |
| 31 | CHECK | Informative test docstrings | All 20 tests documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:330-333` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines valid | `entire-report.txt:317-333` |
| 34 | CHECK | Agent line format | 17 properly formatted lines | `entire-report.txt:317-333` |
| 35 | CHECK | Rubric detailed; positive cap OK | 34 positive pts ≤ 40 | `entire-report.txt:317-329` |
| 36 | CHECK | Positive phrasing | Bad behaviors use negative scores | `entire-report.txt:330-333` |
| 37 | UNCHECK | No /tests/ references | References `/tests/test_outputs.py` | `entire-report.txt:333` |
| 38 | CHECK | No task.toml/instruction refs | None in rubric | `entire-report.txt:317-333` |
| 39 | CHECK | No oracle/NOP mentions | None in rubric | `entire-report.txt:317-333` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/category match | data-processing + rust streaming task | `task.toml:7-9` |
| 45 | CHECK | Difficulty field present | hard declared; platform medium — informational | `task.toml:6`, `entire-report.txt:31` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:11` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible | solution/ excluded from image | `.dockerignore` pattern |
| 52 | CHECK | Input data not trivially hackable | Tests reset durable state; outputs cleared before checks | `tests/test_outputs.py` helpers |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:37` |
| 55 | CHECK | Not unfair | Documented tolerances, seeds, WAL salvage in operator_notes | `operator_notes.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 37, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Cold/warm metric parity within bands | `test_warm_parity_all_metrics`, `test_precision_sensitive_moments` | covered | `instruction.md:11`, `operator_notes.md:49-55`, `test_outputs.py:371+` |
| frame_gen / seal_gen / drain_wm locking | `test_frame_gen_seal_lock`, `test_drain_watermark_frame_gen_lock` | covered | `operator_notes.md:29-31,71`, `test_outputs.py:382+` |
| WAL salvage skips malformed lines | `test_wal_mid_corruption_double_continue`, `test_wal_salvage_full_continue_cycle` | covered | `operator_notes.md:31`, `test_outputs.py:429+` |
| combine_rank monotone trace | `test_combine_rank_sequence_parity`, `test_warm_cold_warm_trace_triangle` | covered | `operator_notes.md:69`, `test_outputs.py:569+` |
| Inter-seed isolation / stale plan | `test_inter_seed_durable_isolation`, `test_stale_plan_after_seed_swap` | covered | `instruction.md:11`, `test_outputs.py:455+` |
| Reuse epoch advances on continue | `test_reuse_epoch_monotone_across_continues` | covered | `operator_notes.md:29`, `test_outputs.py:554+` |
| No hand-written /app/output JSON | enforced by `_clear_outputs` + pipeline runs | covered | `instruction.md:3`, test helpers |
| Chained continue plateau | `test_chained_continue_invariants`, `test_metric_plateau_across_mixed_profiles` | covered | `instruction.md:11`, `test_outputs.py:409+` |
| Independent full-run reference | `test_full_run_reference_parity` | covered | `operator_notes.md:49-55`, `test_outputs.py:359+` |
| BRANCH_ABS 1e-12 tolerance | branch total checks | covered | `operator_notes.md:47` (`1e-12` band), `test_outputs.py:27` |

No phantom High-severity gaps. Minor numeric literals in tests (seeds 42, 99, 1002) are harness choices, not hidden semantics.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #14-16, #20, #50 |
| `environment/docs/operator_notes.md` | #17, #27, #55, spec alignment |
| `environment/Cargo.toml` | Low-severity Cargo pin note |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #32-39, #45, #54, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: windowed-float-checkpoint-drift ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pip pin heuristic on continuation line (false positive — packages pinned)
INFO: non-milestone task (preferred milestone for new submissions)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures — debugging incompleteness |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) | platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

Local oracle: Docker socket permission denied in reviewer environment; platform evidence used instead.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches `entire-report.txt`; regular layout; rust/bash |
| 1 Instruction | ☑ | Concise; operator_notes normative |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; offline; pytest pinned |
| 3 Oracle | ☑ | Source patches + rebuild; platform 100% |
| 4 Verifiers | ☑ | 20 tests; canonical reward; no runtime installs |
| 5 Metadata | ☑ | Complete; allow_internet=false |
| 6 Rubric | ☐ | Blocker: `/tests/` path in negative criterion |
| 7 LLMaJ & agents | ☑ | Failures are agent debugging misses, not spec gaps |
| 8 Novelty & fairness | ☑ | Multi-subsystem bugs; anti-cheat solid |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task — the Rust checkpoint/resume debugging setup is thoughtful, operator_notes give clear schemas and tolerance bands, and the 20-test verifier exercises cold/warm parity, WAL salvage, and generation locking end to end. Oracle passes on platform runs and agent rates look well calibrated. One fix before accept: the platform rubric’s last negative criterion names `/tests/test_outputs.py` explicitly; please reword it without the `/tests/` path (e.g. “changes verifier test files as the primary fix”) so it meets rubric format rules. Everything else looks good.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
