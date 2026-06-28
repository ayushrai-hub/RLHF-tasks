# Terminus Review Report: `gsqt-importable-config-training-submission-21`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (100% per platform report; not re-run locally) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Milestones, Metadata Issues, Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong 5-milestone GSQT refactor with pinned offline env, fake-DB anti-cheat, 0% agent pass rate, and oracle stability. Real blockers: invalid `task.toml` milestone layout (top-level `[agent]`/`[verifier]`), and milestone 5 instruction↔test gaps on `claim_next_ready` success return shape and `event_metadata` exactness that caused 6/9 trials to stall at 0.8. Milestone 5 also does not verify `BEGIN IMMEDIATE`, race-retry, or non-zero `lease_version` increment despite explicit instruction text.

**Insights (concise):**

- Platform rubrics in submission use correct **milestone** format (`# Rubric 1`–`# Rubric 5`), not flat non-milestone layout; ≥3 negatives and 10–40 pts per block.
- Automated validate warnings on docstrings (#31) and unpinned pip (#14) are **false positives** — tests have docstrings; `requirements.lock` uses `==` + `--require-hashes`.
- ChatGPT/LLMaJ M5 findings are **confirmed** with file evidence; entire-report “READY TO USE” and `behavior_in_task_description` PASS contradict agent failure analysis on M5 return/metadata.
- Milestone 4 has secondary untested requirements (invalid JSON resilience, in-window `deletion_date` row) — not primary revision drivers given 9–10/10 per-test pass rates.
- `#45` difficulty metadata matches 0% worst-model; not a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Milestones, Metadata Issues | #43, #46 | Milestone `task.toml` has forbidden top-level `[agent]` and `[verifier]`; per-milestone timeouts must live only under `[[steps]]` | `task.toml:25-29` vs `docs/guidelines/milestones.md:99`; `./scripts/terminus validate` ERROR | Remove lines 25–29; rely on existing `[steps.agent]` / `[steps.verifier]` blocks only |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #30, #55 | `claim_next_ready` success return shape unspecified; tests require dict subscript `first["id"]` | `steps/milestone_5/instruction.md:11` (“select the first id”, only documents `(None, True)` empty case); `test_m5.py:147` `first["id"]`; oracle `recovery_replay.py:82,147` returns `dict(row), False`; `entire-report.txt:90-91` 6 trials `TypeError: 'int' object is not subscriptable` | State success return is the claimed row as a dict (sqlite3.Row-like with `"id"` key), e.g. `(row_dict, False)` |
| 3 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #30 | `event_metadata` / `metadata_json` wording says “at least” but tests require exact parsed objects with no extra keys | `instruction.md:11` “containing at least `{\"source\": ...}`”; `test_m5.py:90-93,181-184` exact `==`; oracle `_metadata_rows` `recovery_replay.py:52-54` emits only two keys; `entire-report.txt:92-93` agents failed on extra fields | Specify `event_metadata` is the list of `json.loads(metadata_json)` values, each exactly `{"source": "recovery_replay", "ready_before": [...]}` with no other keys |
| 4 | High | Test Alignment/Coverage Issues | #27 | `BEGIN IMMEDIATE`, race-retry loop, and true `lease_version` increment are instructed but not verified in M5 tests | `instruction.md:11` mandates all three; `test_m5.py` has no trace/race proxy (contrast `test_m2.py:192-211` `RacingClaimConnection`); `test_m5.py:148-151` only asserts `lease_version == 1` from baseline 0; `entire-report.txt:600-707` | Add M5 tests: SQL trace or race proxy for `BEGIN IMMEDIATE` + retry after `rowcount==0`; seed `lease_version > 0` before claim |

*No other High blockers found in env, oracle, pinning, anti-cheat, or difficulty.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M5 `claim_next_ready` return type mismatch: instruction implies id/int, test needs dict (ChatGPT / entire-report §4) | **Agree** | `instruction.md:11`; `test_m5.py:147`; `recovery_replay.py:147`; agent failures `entire-report.txt:90-91,108-109` |
| 2 | M5 `event_metadata` “at least” vs exact equality (ChatGPT / entire-report §4) | **Agree** | `instruction.md:11`; `test_m5.py:90-93`; `entire-report.txt:92-93,110-111` |
| 3 | M5 verifier does not test `BEGIN IMMEDIATE`, race retry, non-zero `lease_version` (ChatGPT / entire-report test-quality M5) | **Agree** | `instruction.md:11`; no matching assertions in `test_m5.py`; M2 has race test at `test_m2.py:680+` |
| 4 | Digest-pinned env, offline setup, milestone layout, oracle, Hard calibration are strong (ChatGPT summary) | **Agree** | `Dockerfile:1,9-12`; `allow_internet = false` `task.toml:18`; oracle 100% `entire-report.txt:31`; 0% agents `entire-report.txt:26-27` |
| 5 | entire-report “READY TO USE” / LLMaJ `behavior_in_task_description` PASS | **Disagree** (for M5) | Same M5 gaps as rows 1–3; 6/9 trials at 0.8 failing only M5 `entire-report.txt:77-82` |
| 6 | M4 invalid JSON payload untested (entire-report test-quality M4) | **Agree** (secondary) | `instruction.md:13`; no malformed `payload_json` in `test_m4.py` seed data |
| 7 | M4 in-window `deletion_date` exclusion untested (entire-report test-quality M4) | **Agree** (secondary) | `instruction.md:11`; no seeded in-window deleted row in `test_m4.py` |
| 8 | Rubric should use milestone format, not flat non-milestone format (user) | **Agree — passes** | `entire-report.txt:714-784` uses `# Rubric 1`…`# Rubric 5`; 31–39 positives per block; negatives in every block |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise | M3 ~788 words / M2 ~501 words exceed 3-paragraph guidance | `steps/milestone_3/instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads like engineering task briefs | milestone instructions |
| 3 | CHECK | No excessive markdown | No heavy ##/tables in instructions | milestone instructions |
| 4 | CHECK | No step-by-step dev steps | Requirements only | milestone instructions |
| 5 | CHECK | No hints/solving strategies | Describes contracts not algorithms | milestone instructions |
| 6 | CHECK | No design-doc I/O tables | None present | — |
| 7 | CHECK | Well specified | Goals and schemas explicit | milestone instructions |
| 8 | CHECK | Interesting | Real DI/refactor scenario | task content |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `src/...` module paths from `/app` | milestone instructions |
| 11 | CHECK | Task name not in instruction | No folder name in text | milestone instructions |
| 12 | CHECK | No canary string | None found | milestone instructions |
| 13 | CHECK | No web content fetch | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Pinned pip deps | `requirements.lock` uses `==` + hashes | `environment/Dockerfile:9-12` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367a0...` | `Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | `COPY app/` only | `Dockerfile:15` |
| 17 | CHECK | No ground truth in env | Broken starter code only | `environment/app/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest via `requirements.lock` in Dockerfile | `Dockerfile:9-12`; `test.sh` no pip install |
| 21 | CHECK | Oracle passes | 100% (3/3) per platform | `entire-report.txt:31` |
| 22 | CHECK | Oracle offline | `solveN.sh` copies files only | `steps/milestone_*/solution/` |
| 23 | CHECK | Oracle not hardcoded | Real Python implementations | `recovery_replay.py` etc. |
| 24 | CHECK | reward.txt canonical block | All milestone `test.sh` | `steps/milestone_5/tests/test.sh:11-23` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | milestone `test.sh` |
| 26 | CHECK | Binary rewards | 0/1 only | milestone `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M5 return/metadata gaps; untested concurrency | §2 blockers 2–4 |
| 28 | CHECK | Tests check correctness | Real SQLite behavior tests | `test_m1.py`–`test_m5.py` |
| 29 | CHECK | Behavior not implementation grep | AST import check enforces stated M5 ban | `test_m5.py:36-58` + `instruction.md:15` |
| 30 | UNCHECK | No brittle exact matching | `event_metadata` exact `==` vs “at least” wording | `test_m5.py:90-93` |
| 31 | CHECK | Informative docstrings | All `test_*` have docstrings | e.g. `test_m5.py:26,98,156` |
| 32 | CHECK | ≥3 negative rubric criteria | 10 negatives across 5 blocks | `entire-report.txt:725-784` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | No ±4 in submission rubric | `entire-report.txt:714-784` |
| 34 | CHECK | Rubric `Agent …, ±N` format | All lines conform | `entire-report.txt:714-784` |
| 35 | CHECK | Rubric detailed/precise | Task-specific criteria per milestone | `entire-report.txt:714-784` |
| 36 | CHECK | Positive language for negatives | Bad behavior uses `-N` suffix | rubric lines |
| 37 | CHECK | Rubric no /tests/ refs | No pytest/test path refs | rubric scan |
| 38 | CHECK | Rubric no instruction.md refs | None | rubric scan |
| 39 | CHECK | Rubric no oracle/NOP refs | None | rubric scan |
| 40 | CHECK | Required files present | Milestone layout: env + per-step instruction/tests/solution | `steps/milestone_*` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author fields | Present | `task.toml:5-6` |
| 43 | UNCHECK | Required metadata complete | Validation errors on `task.toml` structure | `task.toml:25-29` |
| 44 | CHECK | Tags/category match | python/sqlite/DI task | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches rates | `hard` + 0% worst-model | `entire-report.txt:21,26-27` |
| 46 | CHECK | steps/ milestone layout | 5 milestones under `steps/` | `task.toml:31-74` |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`…`solve5.sh` present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | `test_m1.py`…`test_m5.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | Each file tests one milestone | test class names |
| 50 | CHECK | Tests not in image | `COPY app/` only | `Dockerfile:15` |
| 51 | CHECK | No solution in env | tests/solution not copied | `Dockerfile` |
| 52 | CHECK | No trivial input tamper | Dynamic monkeypatch anti-cheat | `test_m3.py`, `test_m5.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | 0% worst-model | `entire-report.txt:26-27` |
| 55 | UNCHECK | Not unfair | M5 spec ambiguities caused systematic 0.8 stalls | `entire-report.txt:77-82,120-125` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 9, 27, 30, 43, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| M5 `claim_next_ready` success return shape | `test_file_backed_recovery_claims_do_not_double_claim` | **gap** | `instruction.md:11` vs `test_m5.py:147` |
| M5 `event_metadata` exact JSON shape | `test_recovery_replay_claims_dynamic_scenario_without_hardcoding` | **gap** | `instruction.md:11` “at least” vs `test_m5.py:90-93` `==` |
| M5 `BEGIN IMMEDIATE` | — | **gap** | `instruction.md:11`; no test |
| M5 retry after concurrent modification | — | **gap** | `instruction.md:11`; `test_m5.py:95-151` sequential only |
| M5 increment `lease_version` (not set to 1) | `test_file_backed...` | **gap** | `test_m5.py:148-151` baseline 0 only |
| M4 invalid JSON does not crash/pause | — | **gap** (secondary) | `milestone_4/instruction.md:13` |
| M4 in-window `deletion_date` excluded | — | **gap** (secondary) | `milestone_4/instruction.md:11` |
| M2 race retry | `test_scheduler_retries_next_candidate_after_row_locked_during_claim` | covered | `test_m2.py` |
| Lazy accessors, DSN change, URI | M1 tests | covered | `test_m1.py` |
| Recovery report keys/rules | M4 tests | covered | `test_m4.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker 1, #43, #45 |
| `steps/milestone_5/instruction.md` | Blockers 2–4, #27, #30, #55 |
| `steps/milestone_5/tests/test_m5.py` | Blockers 2–4 |
| `steps/milestone_5/solution/files/src/devtools/recovery_replay.py` | Blockers 2–3 (oracle contract) |
| `steps/milestone_2/tests/test_m2.py` | Blocker 4 (race pattern reference) |
| `steps/milestone_4/instruction.md` | Adjudication M4 secondary gaps |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `entire-report.txt` | Agent stats, rubric format, external claims |
| `docs/guidelines/milestones.md` | Blocker 1 |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
INFO: Python tasks must achieve hard model difficulty (≤20% worst-model)
WARNING: informative_test_docstrings (false positive — docstrings present)
WARNING: pinned_dependencies Dockerfile line (false positive — requirements.lock pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | |
| terminus-claude-opus-4-8 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

M5 per-test pass rates lowest (3–4/9), consistent with spec gaps not logic difficulty alone.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 5-milestone Python GSQT task; matches submission folder |
| 1 Instruction | ☑ | M5 return/metadata gaps confirmed |
| 2 Environment | ☑ | Pinned, offline, tmux/asciinema OK |
| 3 Oracle | ☑ | Derives from implementation; 100% platform |
| 4 Verifiers | ☑ | M5 concurrency coverage gaps |
| 5 Metadata | ☑ | `task.toml` structure errors |
| 6 Rubric | ☑ | Platform rubric uses correct milestone `# Rubric N` format |
| 7 LLMaJ & agent evidence | ☑ | Contradictions resolved in favor of artifacts |
| 8 Novelty & fairness | ☑ | M5 unfairness via unstated return shape |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work overall — the five-milestone progression, fake-database anti-cheat, digest-pinned offline image, and 0% agent pass rate with a clean oracle all look great. Two things to fix before accept: remove the top-level `[agent]` and `[verifier]` sections from `task.toml` (milestones already define per-step timeouts). For milestone 5, please spell out that `claim_next_ready` returns the claimed row as a dict on success (tests use `first["id"]`), and that `event_metadata` must be exactly the parsed `metadata_json` objects with only `source` and `ready_before` — the current “at least” wording tripped most agents who otherwise nailed milestones 1–4. Adding verifier coverage for `BEGIN IMMEDIATE`, the race-retry path, and incrementing a non-zero `lease_version` would close the remaining concurrency gap.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Milestones | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | yes | 2, 3 |
| Test Alignment/Coverage Issues | yes | 2, 3, 4 |
| Instruction Styling (concise) | no (UNCHECK #1 only; not revision driver) | — |
| Rubric | no | Platform rubric passes milestone format |
| Pinning Issues | no | False positive on validate |
| Environment | no | |
| Oracle Solution Issues | no | |
| Task Difficulty | no | 0% pass rate |
