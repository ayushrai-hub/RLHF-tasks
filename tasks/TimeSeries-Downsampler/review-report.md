# Terminus Review Report: TimeSeries-Downsampler.

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (per submission export 3/3; local oracle not run — Harbor path error on folder name) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** none

**Decision (concise):** No acceptance blockers found. This is a correctly structured 4-milestone Rust task with digest-pinned base (canonical digest), verifier deps baked into the image, milestone-scoped rubric blocks (each ≤40 positive pts), and task-facing rubric negatives. Prior rubric `/tests/` references are fixed. Harbor “NEEDS REVISION” and automated `review` blockers (#20 pytest missing, rubric 62>40 total) are false positives on manual re-audit.

**Insights (concise):**

- Rubric format is **correct milestone layout** (`# Rubric 1`–`4`); this is not a non-milestone task misusing milestone headers.
- Per-block positive caps pass: 18 / 11 / 15 / 18 — only per-block >40 is a blocker for milestones, not summed total.
- `environment/Dockerfile:15` installs hashed `pytest==8.4.1` from `requirements.lock`; `test.sh` does not runtime-install.
- Base image digest `sha256:9f841bbe9e7d8…` matches canonical `public.ecr.aws/docker/library/rust:1.85-slim` list in `docs/guidelines/dockerfxile.md:12`.
- M3 cycle-detection wording is ambiguous (3/4 agent trials failed only cycle tests) but specified; optional clarity polish, not a spec gap blocker.
- M3/M4 env stubs (`causal.rs` missing `deadletter_ids`, `eviction.rs` has `evict_stale`) are Low polish — milestone instructions name the required API.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High/Medium blockers; Accept (ChatGPT) | **Agree** | Full artifact re-audit; see sections 2, 4, 5 |
| 2 | Dockerfile digest-pinned Rust base; no pinning blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:9f841bbe9e7d8…`; matches `dockerfxile.md:12` |
| 3 | Rubric test-file refs fixed; task-facing negatives (ChatGPT / Reviewer Feedback) | **Agree** | `entire-report.txt:673,682,694,707` use “modifies files outside the Rust crate…, -5”; no `/tests/` or “edits test files” |
| 4 | M3 cycle wording optional polish (ChatGPT Low) | **Partially agree** | `steps/milestone_3/instruction.md:13` ambiguous backward vs forward orphan traversal; `entire-report.txt:86-90` agent analysis; 7/10 pass on cycle tests — not acceptance blocker |
| 5 | M3/M4 stub API mismatch optional polish (ChatGPT Low) | **Partially agree** | `environment/app/src/causal.rs:4-11` lacks `deadletter_ids`; `eviction.rs:9` has `evict_stale` not `evict_over_capacity`; M3/M4 instructions specify correct API |
| 6 | Non-canonical Docker base — CRITICAL (Harbor review) | **Disagree as blocker** | Same digest as canonical `rust:1.85-slim`; `validate_task.py:68` accepts digest match; registry path differs only |
| 7 | Harbor RECOMMENDATION: NEEDS REVISION | **Disagree** | Base + stub issues are Low or resolved by instructions; no High/Medium acceptance gaps |
| 8 | M3 test quality VULNERABLE — shallow cycle test, no diamond dedup test (Test Quality Review) | **Partially agree, not blocker** | `steps/milestone_3/tests/test_m3.rs:32-38` 3-node cycle; no diamond dedup scenario; core M3 behaviors otherwise covered — Medium test-strength note only |
| 9 | Instruction sufficiency PASS (entire-report LLMaJ) | **Agree** | `entire-report.txt:67-68`; M3 ambiguity caused agent errors, not missing requirements |
| 10 | Automated review: pytest not in Dockerfile (#20) | **Disagree** | `environment/requirements.lock:27-29` `pytest==8.4.1`; `Dockerfile:15` pip install from lock |
| 11 | Automated review: rubric 62>40 total blocker | **Disagree** | Milestone task (`task.toml:14`); per-block totals 18/11/15/18 all ≤40 per `rubrics.md:32` |
| 12 | Automated review: instruction too long (#1), I/O tables (#6) | **Disagree** | Milestone prompts evaluated per `steps/milestone_N/instruction.md`; no markdown tables; bullet lists only |
| 13 | Prior reviewer: rubric referenced test/verifier files | **Agree — fixed** | Current platform rubric in `entire-report.txt:665-710` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone instruction is scoped and readable | `steps/milestone_1/instruction.md` (22 lines), M2–M4 similarly scoped |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone; algorithm requirements without LLM opener | All milestone `instruction.md` files |
| 3 | CHECK | No excessive markdown formatting | `#` headers + bullets appropriate for algo spec; no tables/code fences | Milestone instructions |
| 4 | CHECK | No step by step instructions | Describes WHAT to implement, not shell walkthrough | Milestone instructions |
| 5 | CHECK | No hints or solving strategies | No detection guidance or answer leakage | Milestone instructions |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables | Milestone instructions |
| 7 | CHECK | Instruction is well specified | All graded behaviors named with types/formulas | M1 parsing rules; M3 four fields; M4 eviction algorithm |
| 8 | CHECK | Instruction is interesting | Realistic stream processing / causal buffering problem | Task content |
| 9 | CHECK | Instruction is unique | Distinct 4-stage Rust downsampler pipeline | Task structure |
| 10 | UNCHECK | All paths in instruction are absolute | Uses crate-relative `src/parser.rs` not `/app/app/src/...` | `steps/milestone_1/instruction.md:3`, M2–M4 `src/...` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder name in prompts | Milestone instructions |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | Milestone instructions |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Hashed lockfile entries | `environment/requirements.lock:27-29` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only `app/` + lockfile | `environment/Dockerfile:21` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stubs only; no walkthrough answers | `environment/app/src/*.rs` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `Dockerfile:15`, `requirements.lock:27`, `steps/milestone_1/tests/test.sh:7` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per export | `entire-report.txt:34` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solveN.sh write local Rust sources | `steps/milestone_3/solution/solve3.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Algorithmic Rust implementations, not hardcoded test outputs | All `solveN.sh` scripts |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward pattern all milestones | `steps/milestone_1/tests/test.sh:2-12` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | All `test_mN.py` harnesses |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0/1` only | All milestone `test.sh` |
| 27 | CHECK | All tests are aligned with instructions | Core requirements traced to Rust integration tests | Section 5 |
| 28 | CHECK | Tests check for correctness, not just format | Numeric/stat assertions in `test_mN.rs` | `steps/milestone_1/tests/test_m1.rs:7-12` etc. |
| 29 | CHECK | Tests verify behavior, not implementation | Cargo harness tests public API behavior | `test_m1.py:42-48` offline cargo test |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Asserts computed stats/IDs | Rust test files |
| 31 | CHECK | Tests have informative names or docstrings | Python docstrings + descriptive Rust fn names | `test_m1.py:66-92`, `test_m3.rs` fn names |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 15 negatives across 4 blocks | `entire-report.txt:673-710` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All lines valid ±1,2,3,5 | `entire-report.txt:665-710` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 39 Agent lines | `entire-report.txt:665-710` |
| 35 | CHECK | Rubric criteria are detailed and precise | Per-block positives 18/11/15/18 (all ≤40) | `entire-report.txt:665-710` |
| 36 | CHECK | Rubric criteria use positive language | Positives describe actions; negatives penalize failures | `entire-report.txt:696-697` “fails to detect…” on negative lines |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ or pytest refs | `entire-report.txt:665-710` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | None | `entire-report.txt:665-710` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:665-710` |
| 40 | CHECK | All required files present | Milestone layout: env, steps, task.toml | Task tree |
| 41 | CHECK | No unnecessary files in parent directory | Only `task.toml` + `environment/` + `steps/` | Task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, category, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | rust / data-processing / windowing | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` declared; platform `hard`; worst-model 20% | `task.toml:6`, `entire-report.txt:24-30` |
| 46 | CHECK | steps/ layout present with per-milestone files | 4 milestones under `steps/` | `task.toml:14`, task tree |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1–4.sh present | `steps/milestone_N/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1–4.py present | `steps/milestone_N/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | `TestMilestoneN` classes | `test_m1.py:65` etc. |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore:10` `**/tests/`; Dockerfile copies `app/` only | `environment/.dockerignore`, `Dockerfile:21` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution excluded from image | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Temp cargo harness outside `/app`; path dep on agent crate | `test_m1.py:20-40` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% | `entire-report.txt:29` |
| 55 | UNCHECK | Task is not too hard or unfair | M3 cycle traversal wording caused convergent agent misreads; optional clarity fix | `entire-report.txt:76-90` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 10, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: parse 4/5 columns, quotes, b64, invalid → None | `parse_valid_event`, `parse_b64_event`, `parse_valid_event_with_quotes`, `parse_invalid_events_returns_none` | covered | `test_m1.rs:6-46` |
| M1: tumbling bucket formula + exact median + flush | `tumbling_window_calculates_correct_bounds`, `tumbling_window_aggregates_stats`, `flush_window_removes_data` | covered | `test_m1.rs:48+` |
| M2: sliding window boundaries + XOR dedup + median | `test_single_event_populates_multiple_windows`, `test_duplicate_events_apply_bitwise_xor`, etc. | covered | `test_m2.rs` |
| M3: immediate process, orphan buffer, recursive unblock | `events_without_dependencies_process_immediately`, `orphaned_event_is_buffered`, `recursive_unblocking_cascades_correctly` | covered | `test_m3.rs:5-29` |
| M3: cycle deadletter + cascade | `cycle_is_detected_and_deadlettered`, `deadletter_cascades_to_dependents` | covered | `test_m3.rs:32-48` |
| M3: multi-parent gating | `multi_parent_event_unblocks_only_when_all_met` | covered | `test_m3.rs:51-66` |
| M3: don't process same orphan twice (diamond) | — | gap (minor) | No diamond-graph dedup test; `test_m3.rs` lacks scenario from test-quality review |
| M4: subtree value eviction, ties, cascade, dedup return | `test_evict_lowest_subtree_value`, `test_tie_breaking_by_event_id`, etc. | covered | `test_m4.rs` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, #46, milestone metadata |
| `environment/Dockerfile` | #15, #20, base image |
| `environment/requirements.lock` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/src/causal.rs` | stub mismatch adjudication |
| `environment/app/src/eviction.rs` | stub mismatch adjudication |
| `steps/milestone_*/instruction.md` | #1–#7, #10, spec alignment |
| `steps/milestone_*/tests/test.sh` | #20, #24 |
| `steps/milestone_*/tests/test_mN.rs` | #27, #28 |
| `steps/milestone_*/tests/test_mN.py` | #31, anti-cheat |
| `steps/milestone_*/solution/solveN.sh` | #22, #23 |
| `entire-report.txt` | agent stats, rubric, external adjudication |
| `docs/guidelines/dockerfxile.md` | canonical base digest |
| `docs/guidelines/rubrics.md` | milestone rubric cap rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate TimeSeries-Downsampler./
Summary: 0 error(s), 0 warning(s), 0 info
Task type detected: milestone
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 20.0% (1/5) | Worst model |
| oracle | 100.0% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

### Rubric positive points (milestone per-block)

| Block | Positive pts | Cap | Status |
|-------|-------------|-----|--------|
| # Rubric 1 | 18 | 40 | pass |
| # Rubric 2 | 11 | 40 | pass |
| # Rubric 3 | 15 | 40 | pass |
| # Rubric 4 | 18 | 40 | pass |

Summed total 62 is **not** a milestone-task blocker.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone Rust task; report matches folder |
| 1 Instruction | ☑ | Per-milestone specs; M3 cycle wording ambiguous (Low) |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; pytest baked in |
| 3 Oracle | ☑ | solveN.sh algorithmic; 3/3 per export |
| 4 Verifiers | ☑ | Temp cargo harness; reward.txt; no runtime installs |
| 5 Metadata | ☑ | `number_of_milestones=4`, `allow_internet=false` |
| 6 Rubric | ☑ | Milestone format correct; per-block ≤40; negatives fixed |
| 7 LLMaJ & agent evidence | ☑ | Hard tier; M3 dominant failure pattern |
| 8 Novelty & fairness | ☑ | Anti-cheat harness strong |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — it's a strong hard Rust milestone task with a clever offline Cargo harness, clear staged requirements, and a well-pinned environment. The rubric looks good now with task-facing negatives instead of test-file references, and each milestone block stays within the point cap. I didn't find any acceptance blockers. Optional polish if you revisit: use `/app/app/src/...` absolute paths in milestone instructions, clarify M3 cycle detection as backward orphan traversal (find the orphan whose `event_id` matches the dependency, then follow that orphan's deps), and align M3/M4 starter stubs with the instructed API (`deadletter_ids`, `evict_over_capacity`).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no | — |
| Environment | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Uses Internet | no | — |
| Task Difficulty | no | — |

*No categories apply as acceptance blockers.*
