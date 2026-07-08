# Terminus Review Report: `geosynth-ai-subsurface-discovery-reasoning-engine`

**Generated:** 2026-07-04 21:22 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/geosynth-ai-subsurface-discovery-reasoning-engine`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling, Other

**Decision (concise):** Strong multi-stage Rust/Python pipeline with solid anti-cheat and difficulty calibration, but public contracts omit verifier-critical digest and JSON schema details that agents cannot infer without reading tests. `formation_compose_digest` requires an undocumented `compose\|epoch\|<epoch_digest>` seed line and full `evidence_kind` mapping; guard/compose ledger field names are test-only. Remove stray `jobs/` directory before resubmit.

**Insights (concise):**

- `test_gs_compose_digest_matches_kit_reference` fails 4/10 agent runs — systematic spec gap, not luck (`entire-report.txt` lines 79–80, 65).
- `discovery-report-contract.md` describes digest intent but not canonical line templates; reference math in `tests/conftest.py:182–185` adds hidden inputs.
- `hypothesis-guard-contract.md` is three sentences — tests assert `blocked_count`, `blocked_pairs`, `accepted_pairs` keys not named in any contract.
- Platform rubric is **flat** (24 positive pts, 4 negatives) — correct for `number_of_milestones = 0`; not milestone-block format.
- Worst-model 20% (GPT-5.5) with Claude 100% — hard tier, not too easy.
- Empty `jobs/` at task root fails #41; unrelated to task content.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | `formation_compose_digest` verifier prepends undocumented seed line `compose\|epoch\|<epoch_digest>` before sorted compose step lines | `discovery-report-contract.md:18` says only "sorted compose lines built from depth epochs"; `tests/conftest.py:182–185` builds `lines = [f"compose\|epoch\|{ed}"]` then appends `compose\|<block>\|<step>\|<sample>\|<evidence_kind>`; same in fixed `environment/geokit/qrvn_f7br/splitter.py:56–60`; `test_gs_compose_digest_matches_kit_reference` at `tests/test_hypothesis_ranking.py:118–124`; 6/10 agent failures on this test (`entire-report.txt:65`) | Document exact digest inputs in `discovery-report-contract.md`: seed line `compose\|epoch\|<epoch_digest>` (epoch_digest = depth-epoch ledger fingerprint) plus per-step lines `compose\|<block_id>\|<step>\|<sample_id>\|<evidence_kind>`; clarify sort-then-sha256 algorithm |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Full `source → evidence_kind` mapping required for compose digest is not in public contracts (only one bundled example) | `instruction.md:7` and `discovery-report-contract.md:20` mention only `tr-gc-001 → pathfinder-spike`; `tests/conftest.py:27–34` maps all six modalities; digest test hashes every trace's kind (`test_hypothesis_ranking.py:118–124`) | Add authoritative mapping table to `discovery-report-contract.md` (seismic→wave-anomaly, gravity→density-deficit, magnetic→susceptibility-peak, borehole→lithology-break, geochem→pathfinder-spike, hyperspectral→alteration-halo) |
| 3 | Medium | Test Alignment/Coverage Issues, Instruction Styling | #27 | `hypothesis-guard-ledger.json` JSON schema field names tested but not specified in contracts | `hypothesis-guard-contract.md:1–5` has no JSON keys; `tests/test_hypothesis_ranking.py:51–69` asserts `blocked_count`, `blocked_pairs`, `accepted_pairs` | Document ledger top-level fields and pair object shape (`left`, `right`, `reason`) in `hypothesis-guard-contract.md` |
| 4 | Medium | Test Alignment/Coverage Issues, Instruction Styling | #27 | `formation-compose-staging.json` branch object uses `steps` array key — tested, not in contract | `discovery-report-contract.md:16–20` omits branch schema; `tests/test_hypothesis_ranking.py:114–115` reads `copper["steps"][0]`; bundled code uses `"steps"` at `environment/geokit/qrvn_f7br/splitter.py:54` | Document compose branch JSON: `{block_id, steps: [{step, sample_id, evidence_kind}]}` |
| 5 | Medium | Other | #41 | Stray empty `jobs/` directory at task root | `geosynth-ai-subsurface-discovery-reasoning-engine/jobs/` exists (empty); audit #41 FAIL | Delete `jobs/` before submission |

*Block pair enumeration order (BTreeSet) is **not** a blocker — tests use sets for pair membership (`tests/test_hypothesis_ranking.py:66–67, 183–186`), not list order.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier-enforced `compose\|epoch\|<epoch_digest>` seed line not documented (ChatGPT High) | **Agree** | `discovery-report-contract.md:18` vs `tests/conftest.py:182–185`; 6/10 failures `entire-report.txt:65` |
| 2 | Guard ledger field names only in tests (ChatGPT High) | **Agree** | `hypothesis-guard-contract.md:1–5` vs `tests/test_hypothesis_ranking.py:51–69` |
| 3 | Block-pair ordering (BTreeSet) undocumented (ChatGPT High) | **Disagree** | No test asserts pair list order; assertions use sets or single blocked row content |
| 4 | Compose branch key `steps` undocumented (ChatGPT High) | **Partially agree** | Gap exists (`discovery-report-contract.md` vs `test_hypothesis_ranking.py:114`); severity Medium — inferable from bundled `splitter.py` but should be in contract |
| 5 | Canonical `evidence_kind` values undocumented (entire-report) | **Agree** | Only `pathfinder-spike` example in contracts; full map in `tests/conftest.py:27–34` drives digest |
| 6 | Dockerfile digest-pinned Rust base acceptable (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:9f841…`; not a blocker |
| 7 | Rubric positive cap / format issues (user concern) | **Disagree** | Flat `Agent …, ±N` list in `entire-report.txt:355–368`; no `# Rubric 2+`; 24 pts ≤ 40; `task.toml:10` `number_of_milestones = 0` |
| 8 | Non-milestone task in milestone rubric format (user) | **Disagree** | Platform rubric is single flat block; milestone headers would be `# Rubric 1` / `# Rubric 2` per `docs/guidelines/rubrics.md:55–66` |
| 9 | LLMaJ `behavior_in_task_description` PASS (entire-report:138) | **Partially agree** | Passes for high-level behaviors; contradicts on digest seed line and JSON schemas — artifacts win |
| 10 | Instruction sufficiency FAIL on compose seed (entire-report:68–110) | **Agree** | Matches artifact proof for blocker #1 |
| 11 | Harbor review "READY TO USE" (entire-report:304) | **Disagree** | Misses contract gaps confirmed above; warnings on base image/tags are non-blocking |
| 12 | Optional: pytest `/tests/` dir vs `test_outputs.py` (entire-report:244) | **Agree (Low only)** | `tests/test.sh:19` targets `test_outputs.py`; works via re-export; not a blocker |
| 13 | Tags at upper bound (entire-report:218) | **Disagree as blocker** | 6 tags within 3–6 range; `task.toml:12` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~258 words, 5 prose blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as engineering brief, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no heavy formatting | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Points to contracts, no solve script | `instruction.md` |
| 5 | CHECK | No hints/strategies | Describes pipeline outputs, not patch recipes | `instruction.md` |
| 6 | CHECK | No design-doc tables in instruction | No I/O mapping tables in instruction | `instruction.md` |
| 7 | UNCHECK | Well specified | Contract gaps on digest lines and JSON schemas (blockers #1–4) | `discovery-report-contract.md`, `hypothesis-guard-contract.md` |
| 8 | CHECK | Interesting | Realistic multi-language pipeline debugging scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify against full TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | Absolute paths | All paths `/app/...` | `instruction.md` |
| 11 | CHECK | No task name in instruction | Task slug absent | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline data and contracts | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` | `environment/Dockerfile:14` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:9f841…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY only under environment | `environment/Dockerfile` |
| 17 | CHECK | No ground-truth leakage | Contracts specify formats; buggy baseline expected | `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:13–14`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle run not completed in this review | — |
| 22 | CHECK | Oracle no internet | solve.sh patches and rebuilds locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Patches sources, rebuilds, runs pipeline | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 with failure path | `tests/test.sh:4–25` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Undocumented digest seed, evidence map, JSON schemas (blockers #1–4) | §2, §5 |
| 28 | CHECK | Tests check correctness | Independent digest recomputation, hidden overlays | `tests/conftest.py`, `tests/test_hypothesis_ranking.py` |
| 29 | CHECK | Behavior not implementation grep | Subprocess pipeline + artifact assertions | `tests/test_survey_ingest.py`, `tests/test_hypothesis_ranking.py` |
| 30 | CHECK | No brittle string matching | Digest and structural checks dominate | tests |
| 31 | CHECK | Informative test docstrings | All `test_gs_*` have docstrings | tests |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:365–368` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:355–368` |
| 34 | CHECK | Agent-line rubric format | 14 `Agent …, ±N` lines | `entire-report.txt:355–368` |
| 35 | CHECK | Rubric detailed; positive cap | 24 positive pts ≤ 40 | `entire-report.txt:355–368` |
| 36 | CHECK | Positive rubric language | No "does not" with +score | rubric text |
| 37 | CHECK | Rubric no /tests/ refs | Clean | rubric text |
| 38 | CHECK | Rubric no metadata/instruction refs | Clean | rubric text |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | rubric text |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | UNCHECK | No stray parent files | Empty `jobs/` directory | `geosynth-ai-subsurface-discovery-reasoning-engine/jobs/` |
| 42 | CHECK | author_name/email | Present | `task.toml:4–5` |
| 43 | CHECK | Other metadata | category, difficulty, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages applicable | rust+python data-processing task | `task.toml:6–12` |
| 45 | CHECK | Difficulty in task.toml | `hard`; worst-model 20% → hard tier | `task.toml:8`, `entire-report.txt:24–30` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | .dockerignore excludes solution | `environment/.dockerignore` |
| 52 | CHECK | No trivial input mutation cheat | Hidden policy overlays; digest chain | `tests/test_hypothesis_ranking.py:172–204` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:29–30` |
| 55 | UNCHECK | Not unfair | Agents failed systematically on undocumented verifier semantics | `entire-report.txt:68–110`, blockers #1–4 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 41, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Catalog sorted by sample_id | `test_gs_catalog_sorted_by_sample_id` | covered | `survey-ingest-contract.md:9–10` |
| catalog_digest geo line format | `test_gs_catalog_sha256_canonical_fingerprint` | covered | `survey-ingest-contract.md:26–28` |
| Forward voxel pairs (i<j) | `test_gs_voxel_graph_includes_non_adjacent_forward_pair` | covered | `voxel-fusion-contract.md` (referenced in instruction) |
| Guard blocks copper vs shale | `test_gs_guard_blocks_copper_shale_exactly` | covered | `hypothesis-guard-contract.md:5` |
| Guard ledger JSON keys | `test_gs_guard_blocks_copper_shale_exactly`, `test_gs_guard_accepts_unguarded_block_pairs` | **gap** | Contract silent; tests `test_hypothesis_ranking.py:51–69` |
| confidence_floor capping | `test_gs_confidence_floor_applied` | covered | `confidence-witness-math.md:3–13` |
| compose array hypothesis_priority order | `test_gs_verifier_swap_compose_priority_puts_shale_first` | covered | `discovery-report-contract.md:9–14` |
| tr-gc-001 pathfinder-spike | `test_gs_compose_branch_starts_with_pathfinder_on_tr_gc_001` | covered | `discovery-report-contract.md:20` |
| Full evidence_kind map for digest | `test_gs_compose_digest_matches_kit_reference` | **gap** | Only one example in contract; full map `conftest.py:27–34` |
| `compose\|epoch\|<epoch_digest>` digest seed | `test_gs_compose_digest_matches_kit_reference` | **gap** | `conftest.py:182`; absent from `discovery-report-contract.md` |
| Compose branch `steps` key | `test_gs_compose_branch_starts_with_pathfinder_on_tr_gc_001` | **gap** | `test_hypothesis_ranking.py:114`; not in contract |
| discovery_fingerprint from chain lines | `test_gs_discovery_report_chain_fingerprint` | covered | `discovery-report-contract.md:24` |
| Hidden policy overlays | `test_gs_verifier_swap_*` | covered | `verifier-overlay-contract.md` |
| Decoy quarantine | `test_gs_decoy_formation_never_merges_exploration_blocks` | covered | `instruction.md:9`, `survey-ingest-contract.md:42` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #27, blockers |
| `task.toml` | #45, #46–49 N/A, rubric format |
| `environment/Dockerfile` | #14–16, #20, #50 |
| `environment/docs/discovery-report-contract.md` | Blockers #1, #2, #4 |
| `environment/docs/hypothesis-guard-contract.md` | Blocker #3 |
| `environment/geokit/qrvn_f7br/splitter.py` | Blocker #1 (implementation reference) |
| `tests/conftest.py` | Blockers #1–2 (verifier reference math) |
| `tests/test_hypothesis_ranking.py` | Blockers #1–4, #27, #55 |
| `entire-report.txt` | Agent stats, rubric, instruction sufficiency |
| `geosynth-ai-subsurface-discovery-reasoning-engine/jobs/` | Blocker #5, #41 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: geosynth-ai-subsurface-discovery-reasoning-engine/ ===
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: regular
WARNING: tests [tests/test_outputs.py]: No test functions found in test_outputs.py
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Per submission export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | hard (`entire-report.txt:24`) |
| Tier match (#45) | yes (informational) |

**Notable per-test failures:** `test_gs_compose_digest_matches_kit_reference` 6/10; guard tests 8–9/10 (`entire-report.txt:41–65`).

### Rubric (platform)

| Field | Value |
|-------|-------|
| Positive points | 24 (cap 40) |
| Negative criteria | 4 |
| Format | Flat non-milestone list (no `# Rubric 2+`) |
| Status | PASS |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `number_of_milestones = 0`; report matches folder |
| 1 Instruction | ☑ | Concise; contract refs authoritative; digest/schema gaps |
| 2 Environment | ☑ | Digest-pinned Rust; tmux/asciinema; offline; no tests/solution COPY |
| 3 Oracle | ☐ | Not executed locally (Docker build timeout) |
| 4 Verifiers | ☑ | Canonical reward block; independent reference math; hidden overlays |
| 5 Metadata | ☑ | hard/data-processing; 6 tags valid |
| 6 Rubric | ☑ | 24 pts; flat format correct for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL aligns with blockers; quality checks partially stale |
| 8 Novelty & fairness | ☑ | Multi-stage; anti-cheat strong; unfair hidden digest inputs |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on the GeoSynth pipeline — the multi-stage Rust/Python design, hidden policy overlays, and independent digest verification are all strong, and difficulty looks well calibrated. Before we can accept, the public contracts need a few verifier-critical details that agents are currently missing: document the `compose|epoch|<epoch_digest>` seed line and full per-step `compose|…` digest format in discovery-report-contract.md, add the complete source→evidence_kind mapping (not just the tr-gc-001 example), and spell out the JSON shapes for hypothesis-guard-ledger.json and formation-compose-staging.json (`blocked_count`, `blocked_pairs`, `accepted_pairs`, and the `steps` array). Also delete the empty `jobs/` folder at the task root.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2, 3, 4 |
| Test Alignment/Coverage Issues | yes | 1, 2, 3, 4 |
| Other | yes | 5 |
| Rubric | no | — |
| Milestones | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |

---

_Generated by `./scripts/terminus review` and enriched after manual artifact audit per `prompt.md`._
