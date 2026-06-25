# Terminus Review Report: `Task152_Tracefold_V1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per report; local run blocked by Harbor image-name casing) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** Well-crafted Rust trace-fold debugging task with digest-pinned images, verifier deps baked into the Dockerfile, strong anti-cheating (test-only alt/trap seeds + runtime-generated scenarios), and full contract↔test alignment. The sole High blocker is metadata calibration: `task.toml` declares `hard` but worst-model pass rate is 60% (GPT-5.5), which maps to **Medium** per `docs/guidelines/difficulty.md`. Update `difficulty = "medium"` or rebalance until worst-model ≤20%.

**Insights (concise):**

- Automated `terminus review` falsely flagged #14 (pip is pinned), #31 (all tests have docstrings), and #54 (used max agent rate 100% instead of worst-model min 60%).
- Portal rubric in `entire-report.txt` has **three** distinct negatives (−5, −3, −5) — prior “only two negatives” note is obsolete.
- `environment/Dockerfile:18-19` pins `pytest==8.4.1` and `pytest-json-ctrf==0.3.5`; unpinned `apt-get` packages are Low polish only.
- LLMaJ quality checks (`behavior_in_task_description`, `behavior_in_tests`, `anti_cheating_measures`) all pass with file evidence.
- Agent failures cluster on numeric exactness (codec rotations, hex constants) — fair, not instruction gaps.
- Oracle applies `oracle.patch` then builds/runs — derives output; `entire-report.txt` reports 100% (3/3).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared `hard` but observed worst-model tier is Medium | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:14,19-20` GPT-5.5 60% (3/5), Claude 100% (5/5); worst = 60% → Medium per `docs/guidelines/difficulty.md:10` | Set `difficulty = "medium"` in `task.toml`, **or** add harder edge cases / rebalance until worst-model ≤20% |

*No other High blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `task.toml` declares `hard` but evaluation classifies Medium; GPT 60%, Claude 100% (ChatGPT) | **Partially agree** | Worst model = min(60%, 100%) = **60%** → Medium tier (`docs/guidelines/difficulty.md:10`); `task.toml:6` says `hard` — mismatch confirmed. ChatGPT also implied #54 “too easy” at 100%; worst model is 60%, so #54 passes. |
| 2 | Dockerfile unpinned apt packages and copy-before-build layer volatility (ChatGPT Low) | **Agree** (Low only) | `environment/Dockerfile:10-15` apt packages unpinned; `Dockerfile:26-35` COPY src before `cargo build` — cosmetic, non-blocking |
| 3 | Rubric has only two negative criteria (entire-report human note L5-7) | **Disagree** | Portal rubric `entire-report.txt:319-321` lists three negatives: −5, −3, −5 |
| 4 | Unpinned pip / missing requirements.txt (entire-report L1-3) | **Disagree** | `environment/Dockerfile:18-19` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; Rust deps locked via `Cargo.lock` + `--locked` |
| 5 | CursorReport missing `lineage_digest`/`discard_digest` is instruction ambiguity (entire-report WARNING L156-180) | **Partially agree** (Low) | `environment/src/session/hold.rs:27-39` omits fields intentionally; `report_contract.md:54-56` and `instruction.md:3` require audit digests — sufficient for careful agents |
| 6 | Tags array at upper bound / overlap (entire-report WARNING L182-198) | **Agree** (informational) | `task.toml:12` has 6 tags; acceptable, no action |
| 7 | `test.sh` pre-build redundancy (entire-report SUGGESTION L204-223) | **Agree** (polish) | `tests/test.sh:14` pre-builds; `tests/test_outputs.py:216-221` also builds — intentional early compile surfacing |
| 8 | Test quality ROBUST / ACCEPT (entire-report L257-268) | **Agree** | Multiple scenario sources, reference pipeline in `tests/test_outputs.py`, runtime-generated seeds |
| 9 | LLMaJ behavior_in_tests / anti_cheating PASS (entire-report L119-128) | **Agree** | Alt/trap JSON in `tests/data/` only; `environment/Dockerfile:26-32` copies no tests/solution |
| 10 | Automated blockers #14 pip, #31 docstrings, #54 too-easy (review script) | **Disagree** | Pip pinned `Dockerfile:18-19`; all 10 `test_*` functions have docstrings `tests/test_outputs.py:264-405`; worst model 60% ≤ 80% |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering brief referencing contract, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States repair goal + contract path + env vars | `instruction.md:1-5` |
| 5 | CHECK | No hints / solving strategies | Names contract requirements, not bug locations | `instruction.md:3-5` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Contract is normative for all fields, codec rules, digests | `instruction.md:3`, `environment/data/docs/report_contract.md` |
| 8 | CHECK | Interesting | Multi-file Rust debugging: projection, probes, audit digests | task content |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app`, `/app/data/docs/report_contract.md` | `instruction.md:1,3` |
| 11 | CHECK | Task name not in instruction | No `Task152_Tracefold_V1` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No urllib/curl in environment code | `environment/` |
| 14 | CHECK | Pip deps pinned | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18-19` |
| 15 | CHECK | Base image digest-pinned | Both `FROM` lines use `@sha256:` | `environment/Dockerfile:1,3` |
| 16 | CHECK | Context in environment/ only | COPY limited to Cargo, src, g1-g3, data, config | `environment/Dockerfile:26-32` |
| 17 | CHECK | No ground-truth answers in env | Contract is intentional spec; no solution catalog | `environment/Dockerfile`, `report_contract.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs cargo + pytest only | `environment/Dockerfile:17-19`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3); local oracle blocked by Harbor image-name casing | `entire-report.txt:24` |
| 22 | CHECK | Oracle no internet | `patch` + `cargo build --offline` + run binary | `solution/solve.sh:30-34` |
| 23 | CHECK | Oracle derives results | Multi-bug patch then compile/run, not hardcoded JSON | `solution/solve.sh`, `solution/oracle.patch` |
| 24 | CHECK | reward.txt canonical block | mkdir, initial 0, pytest, 0/1 on result | `tests/test.sh:7-21` |
| 25 | CHECK | Same verifier logic for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:17-20` |
| 27 | CHECK | Tests aligned with instructions | All assertions trace to `report_contract.md` | `tests/test_outputs.py:236-254`, `report_contract.md` |
| 28 | CHECK | Tests check correctness | Reference projection + exact digest/invariant checks | `tests/test_outputs.py:145-254` |
| 29 | CHECK | Behavior not implementation grep | Runs binary, compares JSON output | `tests/test_outputs.py:216-228` |
| 30 | CHECK | No brittle exact strings | Exact hex required by contract; numeric equality is spec-driven | `report_contract.md:68`, `tests/test_outputs.py:241-242` |
| 31 | CHECK | Informative test docstrings | All 10 `test_*` functions documented | `tests/test_outputs.py:264-405` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no `rubric.txt` in task folder (portal rubric in report has 3 negatives) | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh, tests | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, timeouts, `allow_internet=false` | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust, security, event-folding tags fit content | `task.toml:6-12` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; worst model 60% → Medium | `task.toml:6`, `entire-report.txt:19-20`, blocker #1 |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible | solution/ not in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Alt/trap seeds test-only; runtime seeds generated in verifier | `tests/test_outputs.py:16-18,312-405` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% threshold | `entire-report.txt:19-20` |
| 55 | CHECK | Not unfair | Failures are implementation precision; contract fully specifies behavior | `entire-report.txt:49-116`, `report_contract.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Canonical projection (lane, epoch, seq, winner tiebreak) | `test_paths_match_canonical_projection`, `_assert_scenario` | covered | `report_contract.md:5-17`, `tests/test_outputs.py:145-192,264-267` |
| Codec arithmetic (delta rotation, flags XOR, cursor_fold) | `_projection`, `_fold`, scenario tests | covered | `report_contract.md:20-36`, `tests/test_outputs.py:51-61,183-191` |
| `lineage_digest` / `discard_digest` | `test_audit_digests_cover_delivery_and_discards` | covered | `report_contract.md:54-73`, `tests/test_outputs.py:122-144,269-273` |
| Eight boolean invariants | `test_cursor_invariant` (parametrized) | covered | `report_contract.md:75-86`, `tests/test_outputs.py:274-289` |
| `line_source` label from executing worker | `test_line_names_executing_worker` | covered | `report_contract.md:86+`, `tests/test_outputs.py:291-296` |
| Deterministic emit | `test_emit_determinism` | covered | `tests/test_outputs.py:298-300` |
| Alternate epoch / tombstone scenarios | `test_alternate_epoch_and_tombstones` | covered | `tests/data/alt_scenarios.json`, `tests/test_outputs.py:302-305` |
| Same-epoch boundary trap | `test_same_epoch_boundary_trap` | covered | `tests/data/trap_scenarios.json`, `tests/test_outputs.py:307-310` |
| Permutation / barrier stability | `test_runtime_ties_barriers_and_permutation` | covered | `tests/test_outputs.py:312-363` |
| Ignored rows affect discard digest only | `test_runtime_ignored_rows_still_change_discard_digest` | covered | `tests/test_outputs.py:365-402` |
| Losing revision in discard, not projection | `test_runtime_losing_revision_is_discarded_but_not_projected` | covered | `tests/test_outputs.py:404-441` |
| Output via `TRACEFOLD_OUT` | `_build_and_emit` | covered | `instruction.md:3`, `tests/test_outputs.py:14,226` |
| Do not hard-code scenario outputs | runtime-generated seeds | covered | `instruction.md:3`, `tests/test_outputs.py:312-441` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, spec alignment |
| `task.toml` | #42-45, blocker #1 |
| `environment/Dockerfile` | #13-20, #50-53 |
| `environment/data/docs/report_contract.md` | #7, #27, spec alignment |
| `environment/src/session/hold.rs` | adjudication #5 (intentional missing fields) |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `tests/data/alt_scenarios.json` | anti-cheating |
| `tests/data/trap_scenarios.json` | anti-cheating |
| `solution/solve.sh` | #21-23 |
| `solution/oracle.patch` | #23 |
| `entire-report.txt` | #45, #54, agent stats, rubric, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate Task152_Tracefold_V1/
Summary: 0 error(s), 11 warning(s), 1 info
```

Warnings are false positives on docstrings (present) and pip line-continuation parsing. Info: non-milestone layout (acceptable).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | **Worst model** |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) | `entire-report.txt:24` |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

Per-test pass rates (`entire-report.txt:31-47`): hardest tests `test_paths_match_canonical_projection` (8/10), digest/runtime scenarios (8/10); invariant tests 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `Task152_Tracefold_V1`, regular layout, Rust/security |
| 1 Instruction | ☑ | Concise, contract-referenced, absolute paths |
| 2 Environment | ☑ | Digest-pinned, tmux+asciinema, no tests/solution COPY |
| 3 Oracle | ☑ | Patch-based; 100% per report; local Harbor casing error |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, behavior tests, docstrings |
| 5 Metadata | ☑ | Blocker: difficulty mismatch |
| 6 Rubric | N/A | Portal-only in `entire-report.txt`; 3 negatives verified |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; GPT 60% worst |
| 8 Novelty & fairness | ☑ | Multi-file debugging; fair numeric failures |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, Dockerfile pinning, and contract↔test alignment are solid — digest-pinned bases, verifier deps in the image, no tests/solution in the runtime image, and strong anti-cheating with test-only and runtime-generated scenarios. The remaining blocker is difficulty metadata: `task.toml` lists `hard` but worst-model pass rate is 60% (GPT-5.5), which is Medium tier. Update `difficulty` to `medium`, or rebalance the task until worst-model ≤20%.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — (portal rubric OK; N/A in task folder) |
| Pinning Issues | no | — |
| Environment | no | — (Low apt polish only) |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review Task152_Tracefold_V1/ --report entire-report.txt`._
