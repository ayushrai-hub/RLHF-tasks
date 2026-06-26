# Terminus Review Report: `mount-graph-reconciler`

**Generated:** 2026-06-25 (manual re-audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/mount-graph-reconciler`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 4 warnings) |
| **Oracle** | pass (per `entire-report.txt` 3/3; not re-run — Harbor local config error) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Environment pinning, milestone layout, anti-cheat, oracle design, rubrics, and Hard difficulty calibration (0% worst-model) are solid. The **only substantive blocker** is that `contract_m4.md` does not document the full-tab `path_a_hex` merge algorithm that verifiers enforce — 9/10 agent trials failed digest-chain tests with the same cluster-scoped misinterpretation. Add explicit merge pseudocode to the contract (or equivalent normative prose). Automated review false positives on #1 (combined milestone word count) and #31 (module docstrings) are not blockers.

**Insights (concise):**

- `path_a_hex` verifiers hash all 9 `fs0.tab` slots merged with per-cluster GRF overlay and tab tombstone re-enforcement (`test_m1.py:48-59`); contract only says “sorted key:marker slot map” (`contract_m4.md:33`).
- Broken `anchor_b.ts` omits tombstone guard/re-enforcement; oracle fix in `solve2.sh:30-42` matches test oracle exactly — agents who fix anchor but hash cluster-only slots still fail.
- Agent digest tests: `test_m1_c0_row_hash` 1/10, `test_m2_dual_path_hex` 1/10, `test_m2_link_derive_hex` 1/10; M3 repeat/cycle tests 10/10 — failure pattern is spec-local, not environment flakiness.
- Each milestone `instruction.md` is 9–13 lines (~81–224 words); combined 407-word automated #1 flag is invalid for milestone layout.
- Rubrics in `entire-report.txt` meet format/negative-count rules; no `rubric.txt` in task dir (portal-entered).
- All three `test.sh` files omit `mkdir -p /logs/verifier` (minor canonical deviation; oracle still passes in Harbor).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | `path_a_hex` full-tab merge algorithm tested but not specified in contract | `contract_m4.md:33` defines only “sha256 hex of sorted key:marker slot map”; `contract_m4.md:60-62` hints at tab↔slice consistency but gives no merge steps; `test_m1.py:48-59` / `test_m2.py:55-66` implement: copy all `fs0.tab` slots (9 keys) → overlay alive GRF keys as `A` unless tab slot is `T` → re-enforce tab `T` markers → hash sorted `key:marker` pairs; `entire-report.txt:65-67,85-88` 9/10 trials failed with cluster-scoped (3-entry) `path_a_hex`; per-test pass `test_m1_c0_row_hash` 1/10, `test_m2_dual_path_hex` 1/10 | Add normative merge pseudocode to `contract_m4.md` under `path_a_hex` (start from full tab layout, overlay alive slice keys skipping tab tombstones, re-enforce tab `T`, then sha256 sorted pairs) |

*No other High/Medium blockers found on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `path_a_hex` merge under-specified in `contract_m4.md`; agents fail digest tests (ChatGPT) | **Agree** | See blocker 1; `solve2.sh:30-42` oracle anchor matches test merge; `settle_c.ts:9-12` hashes full `layout.slots` after anchor |
| 2 | Digest-pinned env, milestones, anti-cheat, rubrics, Hard calibration solid (ChatGPT) | **Agree** | `environment/Dockerfile:1,11-15`; `.dockerignore:1-2`; `entire-report.txt:17,21-27,136-145`; `task.toml:6` + 0% worst-model |
| 3 | LLMaJ `behavior_in_task_description` PASS (entire-report:137) | **Partially agree** | Most behaviors mapped; **exception** is `path_a_hex` merge scope — contract line 33 insufficient vs `test_m1.py:48-59` |
| 4 | LLMaJ `behavior_in_tests` PASS (entire-report:138) | **Agree** | Tests cover contract behaviors including digest chain, tombstones, repeat-cycle, cycle guard |
| 5 | Agent Instruction Sufficiency FAIL — systematic `path_a_hex` misunderstanding (entire-report:45,79-90) | **Agree** | 9/10 trials same failure mode; digest tests 1/10 pass on M1/M2 hash assertions |
| 6 | Task design bug not agent capability gap (entire-report:90) | **Agree** | Agents pass M3 10/10, weave tombstone filtering 9/10, marker guard 9/10 — failures concentrate on undocumented merge semantics |
| 7 | Recommended pseudocode for merge (entire-report:120-129) | **Agree** | Matches `test_m1.py:48-59` and `solve2.sh:30-42` |
| 8 | Automated review READY TO USE (entire-report:270-274) | **Disagree** | Misses `path_a_hex` spec↔test gap driving 90% digest-test failure |
| 9 | Tags array exceeds recommended max / should consolidate (entire-report:175-196) | **Disagree** | `task.toml:12` has exactly 6 tags (valid 3–6 range); suggestion is cosmetic |
| 10 | M1 instruction needs clearer “Objective” heading (entire-report:199-218) | **Partially agree** (not a blocker) | `milestone_1/instruction.md:9` states “Infer and implement sources”; clarity nit only |
| 11 | Duplicate test helper code across milestones (entire-report:225-241) | **Agree** (not a blocker) | `_expected_path_a_hex` duplicated in `test_m1.py` / `test_m2.py`; intentional self-containment |
| 12 | Test quality reviews ACCEPT all milestones (entire-report:308-450) | **Agree** for verifier robustness; **does not override** instruction gap on `path_a_hex` scope |
| 13 | Automated `terminus review` blockers #1, #24, #31 | **Disagree** as substantive blockers | #1: per-milestone instructions 81–224 words each (`wc -w`); #31: all 8 `test_*` methods have docstrings; only module-level docstrings missing (validator warn) |
| 14 | Missing `mkdir -p /logs/verifier` (#24) | **Agree** as deviation, **not Revise-driving** | `steps/milestone_*/tests/test.sh` lack mkdir; `writing-tests.md:11` canonical pattern; oracle 100% in Harbor suggests mount pre-exists |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each milestone 9–13 lines, 81–224 words; M1 context-appropriate | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer scenario tone; no “You are an expert…” | `milestone_1/instruction.md:1-11` |
| 3 | CHECK | No excessive markdown formatting | One `#` title per milestone; no tables/bold dumps | milestone instructions |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes + contract pointer, not solve walkthrough | milestone instructions |
| 5 | CHECK | No hints or solving strategies (WHAT not HOW) | Bugs must be inferred; contract defines schema not TS patches | `milestone_1/instruction.md:9-11` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instructions | milestone instructions |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | `path_a_hex` merge scope ambiguous in contract vs tests | `contract_m4.md:33`, `test_m1.py:48-59` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Multi-surface graph reconciliation + digest chains | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing task) | TypeScript milestone reverse-engineering with weave/anchor/settle | `task.toml:17` |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/graph_report.json`, etc. | milestone instructions |
| 11 | CHECK | Task name does not appear in instruction.md | Folder slug `mount-graph-reconciler` absent | milestone instructions |
| 12 | CHECK | No canary string in instruction.md | None detected | milestone instructions |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/npm/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:12` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Node bookworm-slim digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY . /app/environment` only | `environment/Dockerfile:17` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Contract is normative spec; broken TS is starter code not answers | `environment/docs/contract_m4.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | task layout |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:11-13`, `test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | 100% (3/3) per report | `entire-report.txt:27` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Local bake + mgr_run pipeline | `solve3.sh:77-79` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Progressive TS patches + pipeline execution | `solve1.sh`–`solve3.sh` |
| 24 | UNCHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing `mkdir -p /logs/verifier` in all milestone test.sh | `steps/milestone_1/tests/test.sh:1-15` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `test_m1.py`, `test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` to reward.txt | `test.sh:11-14` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | `path_a_hex` 9-slot merge enforced but not in contract | `contract_m4.md:33`, `test_m1.py:63-64` |
| 28 | CHECK | Tests check for correctness, not just format | SHA-256 digest chains from fixture bytes | `test_m1.py:62-72` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | End-to-end CLI + JSON assertions | `test_m1.py:76-85` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Digest hashes are contract-defined exact values | `contract_m4.md:37-41` |
| 31 | CHECK | Tests have informative names or docstrings | 8/8 test methods documented | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3+ negatives per rubric block in report | `entire-report.txt:457-486` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All lines use ±1,2,3,5 | `entire-report.txt:457-486` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format consistent | `entire-report.txt:457-486` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific trace checks (bake, cln, tx_a/b/c) | `entire-report.txt:457-486` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Penalties use negative scores on bad behaviors | `entire-report.txt:464-466` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | References contract paths and source dirs only | `entire-report.txt:457-486` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | Points to `contract_m4.md` and `/app/...` paths | `entire-report.txt:458` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:457-486` |
| 40 | CHECK | All required files present | Dockerfile, steps/, task.toml, per-milestone tests/solutions | task layout |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task layout |
| 42 | CHECK | author_name and author_email fields present in task.toml | Set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, env, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `typescript`, `system-administration`, reverse-engineering tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`, worst-model 0% | `task.toml:6`, `entire-report.txt:22-23` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `task.toml:27-50` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | `solve1.sh`, `solve2.sh`, `solve3.sh` present | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | M1 c0 only; M2 variants; M3 repeat/cycle | test files |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes `tests/`, `steps/` | `environment/.dockerignore:1-3` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/tests excluded from image | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Digest chains require correct pipeline logic | `test_m1.py:62-72` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | 0% full pass both models | `entire-report.txt:22-23` |
| 55 | UNCHECK | Task is not too hard or unfair (not requiring unavailable info) | Hidden `path_a_hex` 9-slot merge semantics only in test oracle | `test_m1.py:48-59`, `contract_m4.md:33` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 24, 27, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Cleanup before graded matrix run | all tests `_prep()` | covered | `test_m1.py:13-15`, `contract_m4.md:9-17` |
| Rebuild after TS edits | all tests `_prep()` | covered | `test_m1.py:15` |
| Output `/app/output/graph_report.json` via `--matrix` | `test_m1_runner_exit_zero` | covered | `test_m1.py:76-85` |
| `schema_ver` = `m4` | `test_m1_c0_row_hash` | covered | `test_m1.py:95` |
| Retired key `a002` excluded from `node_tags` | `test_m1_c0_row_hash`, `test_m1_summary_trap` | covered | `test_m1.py:100,115` |
| `node_tags` cardinality < stub `alive_count` | `test_m1_summary_trap` | covered | `test_m1.py:103-114` |
| `path_a_hex` = sha256 of merged full tab slot map | `test_m1_c0_row_hash`, `test_m2_dual_path_hex` | **gap** | Contract `contract_m4.md:33` ambiguous; test `test_m1.py:48-59` enforces 9-slot merge |
| `path_b_hex`, `cross_link`, `row_digest` formulas | `test_m1_c0_row_hash`, `test_m2_link_derive_hex` | covered | `contract_m4.md:34-41`, `test_m1.py:65-72` |
| Variant clusters preserve tombstoned markers | `test_m2_marker_guard` | covered | `milestone_2/instruction.md:3`, `test_m2.py:99-110` |
| Distinct `path_a_hex` / `path_b_hex` per variant | `test_m2_dual_path_hex` | covered | `test_m2.py:112-123` |
| Repeat arms match paired arms on digest fields | `test_m3_second_pass_guard` | covered | `contract_m4.md:74-76`, `test_m3.py:24-30` |
| Second matrix without cleanup exits non-zero | `test_m3_no_prep_run_miss` | covered | `contract_m4.md:81`, `test_m3.py:47-54` |
| Stable `run_token` across consecutive clean runs | `test_m3_second_pass_guard` | covered | `contract_m4.md:80`, `test_m3.py:40-45` |
| Cluster tag prefix in `node_tags` | `test_m1_c0_row_hash`, `test_m2_marker_guard` | covered | `test_m1.py:99`, `test_m2.py:110` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `environment/docs/contract_m4.md` | Blocker 1, #7, #27, #55, spec alignment |
| `steps/milestone_1/tests/test_m1.py` | Blocker 1, digest oracle, #27 |
| `steps/milestone_2/tests/test_m2.py` | Blocker 1, variant digest tests |
| `steps/milestone_2/solution/solve2.sh` | Blocker 1 adjudication (oracle merge) |
| `environment/tx_b/anchor_b.ts` | Broken starter vs expected merge |
| `environment/tx_c/settle_c.ts` | `path_a` hashes full `layout.slots` |
| `environment/fixtures/tab_frag/fs0.tab` | 9-slot tab layout |
| `steps/milestone_*/instruction.md` | #1, #7, spec alignment |
| `steps/milestone_*/tests/test.sh` | #24 |
| `environment/Dockerfile` | #15, #20 |
| `task.toml` | #45, metadata |
| `entire-report.txt` | Agent stats, rubrics, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate mount-graph-reconciler/
Summary: 0 error(s), 4 warning(s)
- solution-hints warning on contract_m4.md (cleanup command prose — acceptable contract doc)
- informative_test_docstrings: module-level docstrings missing (test methods OK)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Partial rewards ~0.333 dominant |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Same digest-chain failure pattern |
| oracle | 100.0% (3/3) | Per external report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

**Per-test pass rates (from report):**

| Test | Pass rate |
|------|-----------|
| `test_m1_c0_row_hash` | 1/10 |
| `test_m2_dual_path_hex` | 1/10 |
| `test_m2_link_derive_hex` | 1/10 |
| `test_m3_second_pass_guard` | 10/10 |
| `test_m3_no_prep_run_miss` | 10/10 |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `mount-graph-reconciler` matches report; 3-milestone TypeScript task |
| 1 Instruction | ☑ | Per-milestone concise; `path_a_hex` scope gap in contract |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema, no tests/solution in image |
| 3 Oracle | ☑ | Progressive solveN.sh; derives via pipeline (report 100%) |
| 4 Verifiers | ☑ | Behavior tests; missing mkdir minor; digest oracle fair once spec fixed |
| 5 Metadata | ☑ | hard/category/tags consistent |
| 6 Rubric | ☑ | Portal rubrics in report pass format rules |
| 7 LLMaJ & agent evidence | ☑ | Agent failures systematic on `path_a_hex`; not agent-timeout issue |
| 8 Novelty & fairness | ☑ | Multi-step reverse-engineering; unfair only on undocumented merge |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, digest-pinned environment, milestone verifiers, anti-cheat design, rubrics, and Hard difficulty calibration (0% worst-model) look solid. The blocker is that `contract_m4.md` defines `path_a_hex` only as “sha256 hex of sorted key:marker slot map” without documenting the full-tab merge rule verifiers enforce (start from all `fs0.tab` slots, overlay alive GRF keys skipping tab tombstones, re-enforce tab `T` markers, then hash). Nine of ten agent trials failed the same digest-chain tests with a cluster-scoped interpretation. Add explicit merge pseudocode to the contract. Optional: add `mkdir -p /logs/verifier` to milestone `test.sh` files for canonical compliance.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
| Instruction Styling (contract doc) | yes | 1 |
