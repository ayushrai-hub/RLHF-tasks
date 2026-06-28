# Terminus Review Report: `projectile-material-penetration-ricochet-pipeline`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Rust ballistics task with digest-pinned env, offline verifier, reference oracle, hidden fixtures, and seven `broken_lib` partial traps. One real blocker: `test_partial_digest_traversal_only_still_fails_prefix` enforces that `digest_traversal_only` must stay semantically broken — not stated in `instruction.md` or normative docs — so a thorough agent with correct `trace_digest` end-to-end can fail. Automated script blockers (#14, #20, #31, #54) are false positives on manual audit. Non-milestone rubric in platform report uses correct flat format (not milestone headers).

**Insights (concise):**

- ChatGPT High finding on the digest partial trap is **confirmed** with file evidence; LLMaJ instruction-sufficiency FAIL aligns.
- Other partial traps fairly inject `tests/broken_lib/*`; digest trap alone depends on agent-edited `digest.rs` staying wrong.
- `requirements.txt` pins `pytest==9.0.3`; pytest is baked into image via `/opt/verifier-venv` — #14/#20 pass.
- All 32 `test_*` functions have docstrings (`tests/test_outputs.py`); validator docstring warnings are false positives on parametrized tests.
- Agent rates: Claude 100% (5/5), GPT 5.5 60% (3/5); worst-model 60% = easy tier, not >80% rejected — #54 passes.
- `number_of_milestones = 0`; platform rubric is flat `Agent …, ±N` (no `# Rubric 2+`) — correct for non-milestone per `docs/guidelines/rubrics.md`.
- Oracle not run locally (Docker daemon unavailable); static review of `solution/solve.sh` + platform report (oracle 100%) supports pass.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | `test_partial_digest_traversal_only_still_fails_prefix` patches `export_stage.rs` to call `digest::digest_traversal_only` and asserts wrong digest; requires that helper stay broken even when agent correctly implements `digest_shot_export` and full export contract | `tests/test_outputs.py:420-450`; `environment/crates/ballcore/src/digest.rs:3-11` (comment: "Broken export helper"); `instruction.md:5` (API preservation only — no decoy-stay-broken rule); `environment/docs/replay-epoch.md:8` (specifies correct `trace_digest`, not decoy semantics); agent trial ySZGgUx 31/32 in `entire-report.txt:78-104` | Rewrite trap to inject broken digest via `tests/broken_lib/` (like other partial traps), **or** document in `instruction.md` that legacy `digest_traversal_only` / `digest_ids_before_replay` must remain incorrect and off the export hot path |

*No other High/Medium blockers found on manual audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `test_partial_digest_traversal_only_still_fails_prefix` depends on `digest_traversal_only` staying broken; thorough agents fixing both digest helpers fail despite correct export (ChatGPT High) | **Agree** | `tests/test_outputs.py:424-450` patches export to `digest_traversal_only` and asserts `got["trace_digest"] != exp["trace_digest"]`; `digest.rs:4-10` marks helper broken; `replay-epoch.md:8` requires `{replay_seq}\|{ids}` — not stated that decoy helpers must stay wrong; `entire-report.txt:92-94` trial ySZGgUx over-fixed helper |
| 2 | Non-canonical Rust base image (entire-report WARNING #1) | **Disagree** (not a blocker) | `environment/Dockerfile:1` digest-pinned `rust:1.85-slim`; tmux + asciinema installed; no canonical Rust image required for Revise |
| 3 | Category should be `software-engineering` not `data-processing` (entire-report WARNING #2) | **Partially agree** (informational) | `task.toml:7` `category = "data-processing"`; task is Rust module debugging — imprecise tag, not acceptance blocker |
| 4 | LLMaJ `behavior_in_task_description` PASS | **Agree** | `instruction.md` + `/app/docs/*.md` cover pipeline, staging, digest, materials, ricochet, batch |
| 5 | LLMaJ `behavior_in_tests` PASS | **Partially agree** | Broad coverage confirmed; exception is unstated decoy-digest constraint in blocker #1 |
| 6 | LLMaJ Task Instruction Sufficiency FAIL (digest decoy) | **Agree** | Same evidence as claim #1 |
| 7 | Test quality review ACCEPT | **Partially agree** | Suite is strong; digest partial trap is the one unfair edge |
| 8 | Automated review #14 unpinned pip | **Disagree** | `environment/requirements.txt:1-2` `pytest==9.0.3`, `pytest-json-ctrf==0.5.0`; installed at image build `Dockerfile:13-16` |
| 9 | Automated review #20 pytest not in image | **Disagree** | `Dockerfile:14-16` venv + pip install; `tests/test.sh:25-26` uses `/opt/verifier-venv/bin/python3 -m pytest` with no runtime install |
| 10 | Automated review #31 missing docstrings | **Disagree** | Every `def test_*` has docstring e.g. `tests/test_outputs.py:162-163`, `171-172`, `420-421` |
| 11 | Automated review #54 worst-model 100% too easy | **Disagree** | `entire-report.txt:20-21` GPT 60% (3/5), Claude 100%; worst = 60% (<80%) |
| 12 | Platform rubric uses milestone format on non-milestone task | **Disagree** | `task.toml:9` `number_of_milestones = 0`; `entire-report.txt:302-318` flat `Agent …, ±N` list with no `# Rubric 2+` — correct per `rubrics.md:60` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | Four short paragraphs, ~200 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem statement + doc pointers, not spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goals and rebuild rule, not per-bug steps | `instruction.md:7` |
| 5 | CHECK | No hints/solving strategies | WHAT + doc refs only | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Paths, pipeline, doc contracts named | `instruction.md` |
| 8 | CHECK | Interesting | Multi-module Rust physics debugging | — |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | No task name in instruction | Folder name absent | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline cargo; local fixtures | `environment/Dockerfile:31` |
| 14 | CHECK | Pip pinned with == | `pytest==9.0.3` in requirements | `environment/requirements.txt` |
| 15 | CHECK | FROM digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY from env only | `environment/Dockerfile:33-38` |
| 17 | CHECK | No ground truth in env | Golden sources in `solution/files/` only | `solution/solve.sh` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no install | Venv in Dockerfile; test.sh calls pytest only | `Dockerfile:14-16`, `tests/test.sh:25-26` |
| 21 | UNCHECK | Oracle passes consistently | Not executed — Docker unavailable locally | platform `entire-report.txt:25` oracle 100% |
| 22 | CHECK | Oracle no internet | `cargo build --offline` | `solution/solve.sh:22` |
| 23 | CHECK | Oracle derives via implementation | Copies golden `.rs`, builds ballctl | `solution/solve.sh:12-23` |
| 24 | CHECK | reward.txt canonical block | Writes 0 then 1 on pass | `tests/test.sh:4-34` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:30-33` |
| 27 | UNCHECK | Tests aligned with instructions | Digest partial trap tests unstated decoy semantics | blocker #1 |
| 28 | CHECK | Tests check correctness | `reference_ballistics` equality | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | CLI subprocess + JSON asserts | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string matching | Numeric/struct equality vs reference | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | All 32 tests documented | `tests/test_outputs.py` |
| 32 | CHECK | Rubric ≥3 negatives | Five negatives in platform rubric | `entire-report.txt:314-318` |
| 33 | CHECK | Rubric scores ∈ {1,2,3,5} | All lines use ±1,2,3 | `entire-report.txt:302-318` |
| 34 | CHECK | Rubric Agent format | Each line `Agent …, ±N` | `entire-report.txt:302-318` |
| 35 | CHECK | Rubric detailed | Task-specific physics/digest checks | `entire-report.txt:302-318` |
| 36 | CHECK | Rubric positive language | Penalties describe bad actions affirmatively | `entire-report.txt:314-318` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:302-318` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:302-318` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:302-318` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No stray parent files | Clean task folder | — |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, allow_internet, languages | `task.toml` |
| 44 | UNCHECK | Tags/category applicable | `data-processing` imprecise for Rust debugging task | `task.toml:7` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 60% = easy tier | `task.toml:6`, `entire-report.txt:20-21` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | Golden only under solution/ | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially mutate inputs | SHA256 fixture integrity test | `tests/test_outputs.py:162-167` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst model 60% | `entire-report.txt:20-21` |
| 55 | UNCHECK | Not unfair | Digest decoy trap penalizes correct full fixes | blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 21, 27, 44, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Two-step integrate-shot + export-shot | `test_shot_matches_reference`, `test_export_without_integrate_fails` | covered | `instruction.md:3`; `tests/test_outputs.py:171-199` |
| Staging snapshot `/app/state/shot-snapshot.json` | `test_staging_snapshot_written` | covered | `instruction.md:5`; `tests/test_outputs.py:341-362` |
| `trace_digest` = SHA256(`{replay_seq}\|{ids}`) traversal order | `test_trace_digest_traversal_order`, `test_hidden_digest_order_trap` | covered | `replay-epoch.md:8`; `tests/test_outputs.py:364-394` |
| `replay_seq` advances on re-integrate | `test_replay_seq_advances_second_integrate`, `test_hidden_replay_prefix_required_on_second_integrate` | covered | `replay-epoch.md:5-7`; `tests/test_outputs.py:311-417` |
| Material binding via `physics_id` | `test_material_id_trap_uses_physics_id` | covered | `material-binding.md`; `tests/test_outputs.py:216-227` |
| Falloff after traversal | `test_multi_layer_falloff_after_traversal` | covered | `penetration-contract.md`; `tests/test_outputs.py:229-240` |
| Single boundary debit per layer | `test_boundary_ledger_not_doubled` | covered | `tests/test_outputs.py:242-253` |
| Ricochet reflection angles | `test_ricochet_trap_stops_and_reflects` | covered | `ricochet-contract.md`; `tests/test_outputs.py:202-213` |
| Batch tick ordering | `test_batch_matches_reference`, `test_tick_order_trap_not_arrival_order` | covered | `batch-contract.md`; `tests/test_outputs.py:255-270` |
| Byte-identical repeated runs | `test_repeat_run_byte_identical` | covered | `instruction.md:7`; `tests/test_outputs.py:297-309` |
| Partial-fix: one module broken fails | `test_partial_*` (7 broken_lib traps) | covered | `instruction.md:5`; `tests/test_outputs.py:456-651` |
| Legacy digest helpers must stay broken when export patched | `test_partial_digest_traversal_only_still_fails_prefix` | **phantom** | Not in `instruction.md` or normative docs; `tests/test_outputs.py:420-450` |
| Preserve exported API names/signatures | compile-time across modules | covered | `instruction.md:5` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-8, #10-12, #27, blocker 1, spec alignment |
| `task.toml` | #42-46, #45, milestone N/A |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/requirements.txt` | #14 |
| `environment/crates/ballcore/src/digest.rs` | blocker 1, claim 1 |
| `environment/crates/ballcore/src/export_stage.rs` | blocker 1 |
| `environment/docs/replay-epoch.md` | spec alignment, claim 1 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, blocker 1, all partial traps |
| `tests/broken_lib/*` | contrast with digest trap design |
| `solution/solve.sh` | #22-23 |
| `solution/files/golden_digest.rs` | oracle replaces digest entirely |
| `entire-report.txt` | agent stats, rubric, LLMaJ, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate projectile-material-penetration-ricochet-pipeline/
Summary: 0 error(s), 28 warning(s), 2 info
Task type detected: regular
```

Warnings on docstrings and pip-install line are false positives on manual audit (docstrings present; requirements pinned).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100% (5/5) | `entire-report.txt:20` |
| terminus-gpt5-5 | 60% (3/5) | `entire-report.txt:21` |
| oracle | 100% (3/3) | platform report; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | easy (60–80% worst model) |
| Declared difficulty | hard (`task.toml:6`) |
| Tier match (#45) | no — informational only, not a revision blocker |

Per-test: `test_partial_digest_traversal_only_still_fails_prefix` 4/5 passes (`entire-report.txt:64`); one trial failed 31/32 after over-fixing digest helper.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; Rust ballistics; matches `entire-report.txt` |
| 1 Instruction | ☑ | Concise, absolute paths; missing decoy-digest rule |
| 2 Environment | ☑ | Digest-pinned Rust image; offline cargo; tmux/asciinema |
| 3 Oracle | ☐ | Docker unavailable; static review OK |
| 4 Verifiers | ☑ | 32 tests + reference; one unfair partial trap |
| 5 Metadata | ☑ | `number_of_milestones = 0`; category imprecise |
| 6 Rubric | ☑ | Platform flat rubric valid for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL on digest trap confirmed |
| 8 Novelty & fairness | ☑ | Strong anti-cheat; digest trap unfair edge |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the digest-pinned Rust workspace, hidden verifier fixtures, reference-ballistics checks, and the `broken_lib` partial traps are excellent anti-shortcut design. Instructions and normative docs clearly specify the two-step pipeline, staging snapshot, and `trace_digest` format. One fix before accept: `test_partial_digest_traversal_only_still_fails_prefix` assumes `digest_traversal_only` stays intentionally wrong when an agent patches export to call it, but nothing in the instructions or docs tells agents to leave those legacy digest helpers broken. A thorough fix (correct `digest_shot_export` plus cleaned-up helpers) can pass every behavioral test except this trap. Please either rewrite that trap to swap in a broken digest from `broken_lib` like the other partial tests, or state explicitly that off-hot-path digest decoys must not be corrected.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Metadata Issues | no | — (category imprecision informational only) |
| Task Difficulty | no | — (worst 60%, not >80%) |
| Milestones | no | — (correct non-milestone layout and rubric format) |
| Pinning Issues | no | — |
| Test Dependency Location | no | — |
| Environment | no | — |
