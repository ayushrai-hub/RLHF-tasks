# Terminus Review Report: `sysadmin-bash-iptables-reachability-audit`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Harbor milestone oracle command failed locally) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong four-milestone iptables audit task with excellent traps, anti-cheat, and milestone-scoped rubric layout. Two real High spec-test gaps remain in milestone 4 (universal path recording before control-flow branching; lexicographic `probe_id` sort). Platform rubric still references `/tests/` in three milestone blocks. Prior-cycle fixes (Rubric 4, explanation fields) are confirmed. Stale M2/M3 test docstring counts are cosmetic only.

**Insights (concise):**

- Milestone rubric format is correct (`# Rubric 1`–`# Rubric 4`); per-block positive caps are 21/39/11/29 — all ≤40.
- ChatGPT High findings on M4 path recording and probe ordering are confirmed with file evidence; missing Rubric 4 and wrong explanations are fixed.
- Automated audit false-positives: pip deps are `==`-pinned in `environment/Dockerfile`; instruction-length heuristic wrongly summed all four milestone prompts; `#31` docstring miss is wrong (all `test_*` have docstrings).
- Agent stats: worst-model 0%, best 40% — appropriate hard/medium calibration; all M4 failures cluster on the two spec gaps above.
- `task.toml` correctly omits root `[agent]`/`[verifier]` per milestone-task schema (`docs/guidelines/milestones.md`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | M4 path/hop_count contract under-specified: only `non_terminal` and `unknown` say “record the rule”; verifier/oracle record **every** matched rule (including RETURN, terminal, jump, goto) in `path` before applying control flow. | `environment/app/docs/SCHEMA.md:136-141` vs `:149-150`; `steps/milestone_4/tests/helpers.py:472-476`; `steps/milestone_4/tests/test_m4.py:46-51` (t3 path includes `filter.LOGGING:2` RETURN); agent failure analysis in `entire-report.txt:147-167` | In SCHEMA.md traversal section, state explicitly that **every** first-match rule is appended to `path` (and counted in `hop_count`) before branching on `target_type`. Add a worked example with a RETURN in the path. |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | M4 probe row sort is lexicographic, not natural numeric: `t10` sorts between `t1` and `t2`, but public contract only says “`probe_id` ascending”. | `environment/app/docs/SCHEMA.md:152`; `steps/milestone_4/tests/test_m4.py:34-37` (`sorted(ids)`); `environment/app/api/contracts/probe_packets.tsv:7-16`; `entire-report.txt:128` (5/10 on `test_sorted_by_probe_id`) | State “lexicographic / string order (Python `sorted()` on `probe_id`)” in SCHEMA.md and M4 instruction, or change verifier to natural order. |
| 3 | Medium | Rubric | #37 | Platform rubric references forbidden `/tests/` path in three milestone negatives. | `entire-report.txt:547,563,571` (`or /tests/, -3`); `docs/guidelines/rubrics.md:24-25` | Rephrase negatives to protected paths only (`/app/api/`, `/app/db/schema.sql`) without naming `/tests/`. |

*Non-blockers noted:* stale M2 docstring (“8 filter + 3 nat = 11” vs assert 13 at `steps/milestone_2/tests/test_m2.py:55-57`); stale M3 docstring (“22 detail rows / 24 lines” vs 33 rules at `steps/milestone_3/tests/test_m3.py:30`); stray `__pycache__` under `steps/milestone_2/tests/` — fix while revising but do not block accept alone.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M4 path contract under-specified for RETURN/jump/goto/terminal rules (ChatGPT High) | **Agree** | `SCHEMA.md:136-141` records only `non_terminal`/`unknown`; oracle `helpers.py:472` appends all matches; `test_m4.py:51` expects RETURN in path |
| 2 | M4 probe sort is lexicographic, not natural ascending (ChatGPT High) | **Agree** | `SCHEMA.md:152`; `test_m4.py:37` uses `sorted(ids)`; probes include `t1`…`t10` |
| 3 | M2 docstring stale (8+3=11 chains) (ChatGPT Medium) | **Agree** | `test_m2.py:55` docstring vs `:56-57` assert `13` (10 filter + 3 nat) |
| 4 | M3 docstring stale (22 rows / 24 lines) (ChatGPT Medium) | **Agree** | `test_m3.py:30` docstring vs 33 rules in `steps/milestone_1/instruction.md:5` |
| 5 | Missing Rubric 4 block (prior Reviewer Feedback) | **Disagree** (fixed) | `entire-report.txt:573-584` has full `# Rubric 4` with 29 positive pts and 3 negatives |
| 6 | Explanation fields describe wrong task (prior Reviewer Feedback) | **Disagree** (fixed) | `entire-report.txt:13-26` now describe iptables/bash/sqlite milestones |
| 7 | Missing root `[agent]`/`[verifier]` in task.toml (Harbor review warning) | **Disagree** | `docs/guidelines/milestones.md:99` — milestone tasks use per-step timeouts only; `task.toml:24-58` is correct |
| 8 | Unpinned pip in Dockerfile (automated audit #14) | **Disagree** | `environment/Dockerfile:18-22` pins `Flask==3.0.3`, `pytest==8.4.1`, etc. |
| 9 | Instruction too long aggregated across milestones (audit #1) | **Disagree** as blocker | Each `steps/milestone_N/instruction.md` is 1–3 short paragraphs (~120–180 words); prompt-styling applies per milestone |
| 10 | Non-milestone task using milestone rubric headers (user question) | **Disagree** — N/A | `task.toml:9` `number_of_milestones = 4`; `# Rubric 1`–`# Rubric 4` is the required milestone format |
| 11 | Rubric positive total >40 (rubric-points script) | **Disagree** as blocker | Milestone cap is per block: {1:21, 2:39, 3:11, 4:29} — all ≤40 (`docs/guidelines/milestones.md:104-105`) |
| 12 | LLMaJ instruction sufficiency FAIL on M4 | **Partially agree** | Aligns with blockers 1–2; M1–M3 behavior is well specified |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | Each milestone prompt is 1–3 short paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineering voice; defers detail to SCHEMA.md | milestone instructions |
| 3 | CHECK | No excessive markdown | No heavy headers/tables in instructions | milestone instructions |
| 4 | CHECK | No step-by-step HOW | States WHAT; SCHEMA holds contracts | milestone instructions |
| 5 | CHECK | No hints/strategies | No walkthrough or answer leakage | milestone instructions |
| 6 | CHECK | No design-doc tables in prompt | None in instructions | — |
| 7 | CHECK | Well specified goal | Clear per-milestone deliverables and paths | milestone instructions |
| 8 | CHECK | Interesting | Realistic iptables audit pipeline | task content |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | milestone instructions |
| 11 | CHECK | No task name in instruction | Name absent from prompts | milestone instructions |
| 12 | CHECK | No canary strings | None detected | milestone instructions |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures + local API | `environment/` |
| 14 | CHECK | Pip pinned with == | All pip packages version-pinned | `environment/Dockerfile:18-22` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367...` | `environment/Dockerfile:1` |
| 16 | CHECK | No COPY outside environment | Only `COPY app/` | `environment/Dockerfile:24` |
| 17 | CHECK | No ground-truth answers in env | SCHEMA is contract; stubs are broken by design | `environment/app/lib/*.sh` |
| 18 | CHECK | No privileged Docker | Standard slim image | `environment/Dockerfile` |
| 19 | CHECK | No compose mount violations | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest baked in; test.sh no installs | `Dockerfile`, `steps/milestone_*/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Harbor oracle not executed locally | — |
| 22 | CHECK | Oracle no internet | solve scripts are offline bash/jq/sqlite | `steps/milestone_*/solution/` |
| 23 | CHECK | Oracle reflective | solveN.sh rewrites lib/*.sh with real algorithms | solution scripts |
| 24 | CHECK | reward.txt canonical block | All milestone test.sh write 0/1 | `steps/milestone_1/tests/test.sh:1-32` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | test.sh files |
| 26 | CHECK | Binary rewards | 0 or 1 only | test.sh files |
| 27 | UNCHECK | Tests aligned with instructions | M4 tests enforce path-recording and lex sort not fully stated in SCHEMA | blockers 1–2 |
| 28 | CHECK | Tests check correctness | Oracle recomputation + behavioral traps | `steps/milestone_*/tests/helpers.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | test_m*.py |
| 30 | CHECK | Not brittle where avoidable | Exact CSV/oracle match is intentional contract | test_m3.py, test_m4.py |
| 31 | CHECK | Informative test docstrings | All `test_*` methods have docstrings (AST-verified manually) | test_m1.py–test_m4.py |
| 32 | CHECK | ≥3 rubric negatives | 6 negatives across 4 blocks | `entire-report.txt:539-584` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt` |
| 34 | CHECK | Agent line format | 34 properly formatted lines | `entire-report.txt` |
| 35 | CHECK | Rubric detailed; per-block cap OK | Blocks 21/39/11/29 pts | `entire-report.txt` |
| 36 | UNCHECK | Positive rubric language | Lines use “Agent does NOT treat…” with +3/+5 | `entire-report.txt:557` |
| 37 | UNCHECK | Rubric no /tests/ refs | Three lines cite `/tests/` | `entire-report.txt:547,563,571` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt` |
| 40 | CHECK | Required files present | Dockerfile, task.toml, steps layout | task tree |
| 41 | CHECK | No stray parent files | No jobs/README in task root | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, tags, milestones, timeouts | `task.toml` |
| 44 | CHECK | Tags/category applicable | system-administration + bash/iptables/sqlite | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `medium` in task.toml; worst-model 0% → hard tier (informational only) | `task.toml:6`, `entire-report.txt:35-37` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/` | task tree |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve4.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m4.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | Each test_mN.py grades only milestone N outputs | test files |
| 50 | CHECK | Tests not in image | Dockerfile copies only `app/` | `environment/Dockerfile:24` |
| 51 | CHECK | Solution not in env | steps/ not COPY'd | `environment/Dockerfile` |
| 52 | CHECK | Input tamper resistance | SHA-256 protected-file guards in conftest | `steps/milestone_*/tests/conftest.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:35-37` |
| 55 | UNCHECK | Not unfair | M4 spec ambiguities caused systematic agent misses | blockers 1–2; `entire-report.txt:132-195` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 21, 27, 36, 37, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: normalized JSONL chain/rule shape + target_type | `test_m1.py` | covered | M1 instruction + SCHEMA.md |
| M2: four SQLite tables + reachability/dead-chain fixpoint | `test_m2.py` | covered | M2 instruction + SCHEMA.md |
| M3: CSV report sort + TOTAL row | `test_m3.py` | covered | M3 instruction + SCHEMA.md |
| M4: stack-machine traversal semantics | `test_m4.py` jump/goto/return tests | covered | M4 instruction + SCHEMA.md traversal section |
| M4: every matched rule in `path`/`hop_count` | `test_return_from_user_chain`, `test_traces_match_oracle` | **gap** | SCHEMA.md:136-141 vs helpers.py:472 |
| M4: detail rows sorted lexicographically by `probe_id` | `test_sorted_by_probe_id` | **gap** | SCHEMA.md:152 “ascending” vs sorted() lex order |
| M4: `rule_id` format `table.chain:position` | oracle + M1 tests | covered | SCHEMA.md:28 |
| Protected files immutable | all `conftest.py` | covered | helpers PROTECTED_FILE_HASHES |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `environment/app/docs/SCHEMA.md` | M4 blockers 1–2, #27, #55 |
| `steps/milestone_4/tests/test_m4.py` | M4 blockers, agent failure pattern |
| `steps/milestone_4/tests/helpers.py` | Oracle path-recording behavior |
| `environment/app/api/contracts/probe_packets.tsv` | Lexicographic sort proof |
| `entire-report.txt` | Rubric #32–39, agent stats, prior feedback adjudication |
| `task.toml` | Milestone metadata, #45, #46 |
| `environment/Dockerfile` | #14, #15, #20 |
| `steps/milestone_2/tests/test_m2.py` | Stale docstring (non-blocker) |
| `steps/milestone_3/tests/test_m3.py` | Stale docstring (non-blocker) |
| `docs/guidelines/milestones.md` | Milestone rubric/toml layout |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate sysadmin-bash-iptables-reachability-audit/
Summary: 0 error(s), 1 warning(s), 8 info
Task type detected: milestone
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Passes M1–M3; M4 failures on path/sort |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Uniform 0.75 reward (M4 zero) |
| oracle | 100.0% (3/3) | per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | medium |
| Tier match (#45) | informational only — not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone bash iptables audit; matches report |
| 1 Instruction | ☑ | Per-milestone prompts concise; M4 SCHEMA gaps flagged |
| 2 Environment | ☑ | Digest-pinned base; tmux/asciinema; offline |
| 3 Oracle | ☐ | Not executed locally; static review shows derived solutions |
| 4 Verifiers | ☑ | Strong oracles; M4 spec-test gaps confirmed |
| 5 Metadata | ☑ | Milestone task.toml correct |
| 6 Rubric | ☑ | Milestone format OK; `/tests/` refs block #37 |
| 7 LLMaJ & agent evidence | ☑ | M4 sufficiency FAIL aligns with manual findings |
| 8 Novelty & fairness | ☑ | Good traps; M4 ambiguity drives unfair misses |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work overall — the four-milestone structure, SCHEMA-driven contracts, anti-cheat hashes, and iptables traps (goto vs jump, local-policy override, fixpoint dead chains) are excellent. Rubric 4 and the explanation fields look fixed from the last round. Three things before accept: (1) in SCHEMA.md milestone-4 traversal, spell out that **every** matched rule — including RETURN, terminal, jump, and goto — is appended to `path` before control-flow handling (with a short worked example); (2) state that probe detail rows sort by **lexicographic** `probe_id` (so `t10` comes before `t2`), matching the verifier; (3) drop `/tests/` from the three rubric negative lines. Optional cleanup: fix the stale chain/row counts in the M2/M3 test docstrings and remove the `__pycache__` under milestone 2.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Rubric | yes | 3 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
