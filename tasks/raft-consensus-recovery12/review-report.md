# Terminus Review Report: raft-consensus-recovery

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Raft forensic-repair task with digest-pinned Node image, comprehensive rejection tests, and oracle pass (1.0). **Only confirmed High blockers are rubric-related:** platform positive total is 42 (>40 cap) and one criterion references `instruction.md`. Category mislabel and artifact/test gaps cited by ChatGPT are real notes but **not** High blockers under Terminus severity rules. Non-milestone `# Rubric 1` header is allowed; point cap is the rubric issue, not milestone-format misuse.

**Insights (concise):**

- Oracle passes all 21 tests (`./scripts/terminus oracle`, reward 1.0).
- Agent calibration is appropriate: 0% worst-model on hard tier; not too easy (#54 passes).
- `tests/test_outputs.py` functions all have one-line docstrings; validate warnings on docstrings are false positives.
- `errors.js` PRIORITY mismatch in environment is intentional broken state; oracle patch fixes it (`solution/raft_mesh.patch:115-148`); no test exercises `bad_encoding` vs `rpc_term_stale` tie-break.
- Phantom test thresholds (`commands_committed >= 4`, `> 200`, `> 3000`) are not in `instruction.md` — Medium #27 gap, not a Revise driver alone.
- Pressure-bundle `raft_split_brain` expectation is inferable from default partition structure in generated bundles; solution `triage.js` hardcodes classification token for all accepted runs.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric positive total **42** exceeds non-milestone cap **40** | `entire-report.txt:457-473` (+2+3+5+3+3+3+3+2+2+3+3+2+1+3+2+2=42); `./scripts/terminus rubric-points entire-report.txt` → FAIL | Trim ≥2 positive points (e.g. merge related parser/normalization lines or drop +1 `stableJson` line) so sum ≤40 |
| 2 | High | Rubric | #38 | Rubric references `instruction.md` | `entire-report.txt:472`: `Agent ensures config files under /app/config/ are never modified (constraint from instructions), +2` | Rephrase without citing instructions, e.g. `Agent never modifies files under /app/config/, +2` |

*No other High-severity blockers confirmed in artifacts.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Output artifact coverage incomplete for `term_timeline.csv` / `wal_digest.txt` (ChatGPT High) | **Disagree** (as blocker) | `tests/test_outputs.py:236-244` checks CSV header, `before,`/`after,` rows; `wal_digest.txt` sorted lines plus `cluster_policy_changed=false`, `linearizability_digest=`, `simulation_seed=`. Full row-type parsing absent but schemas are in `environment/docs/consensus_contract.md:78-82` and integration tests validate recovery behavior. Low improvement, not High blocker. |
| 2 | Pressure-bundle / generic split-brain triage under-specified (ChatGPT High) | **Partially agree** (not blocker) | `instruction.md:9` and `consensus_contract.md:84` specify `raft_split_brain` for **default** bundle only. `test_pressure_bundle_restores_consensus` (`test_outputs.py:247-257`) asserts `classification == raft_split_brain` on generated bundle with default partition events (`write_bundle` lines 119-123). Agents failed 9/10 trials per `entire-report.txt:107-108` due to hardcoding, not missing spec text alone. Recommend clarifying generic rule — Medium fairness note, not Revise driver. |
| 3 | Metadata category wrong: `system-administration` (ChatGPT Medium) | **Agree** (not blocker) | `task.toml:8` `category = "system-administration"`; task is Node.js Raft code repair under `/app/raft_mesh/`. `docs/task-type-taxonomy.md:27-28` → `software-engineering` or `debugging`. Single Medium per `docs/reviewer-checklist-full.md:12` → accept-with-note, not Revise alone. |
| 4 | Rubric positive total above ≤40 cap (ChatGPT / `entire-report.txt:7-8`) | **Agree** | Sum = **42** (not 43); `./scripts/terminus rubric-points` confirms FAIL. Lines `entire-report.txt:457-473`. |
| 5 | Rubric references “task instructions” / mirrored negative on `consensus_contract.md` (ChatGPT Medium) | **Partially agree** | `(constraint from instructions)` at `entire-report.txt:472` violates rubric meta-reference rule. **No** mirrored `-2` for skipping `consensus_contract.md` in rubric (`entire-report.txt:474-477` negatives are distinct). |
| 6 | Optional: stronger `rejected_causes` assertions (ChatGPT Low) | **Agree** (Low) | `instruction.md:9`, `consensus_contract.md:12` require `election_timeout_spike` / `snapshot_lag_display_bug`; no assertion in `test_outputs.py:209-244`. LLMaJ `entire-report.txt:169` same. Low — triage behavior partially tested via classification path. |
| 7 | `errors.js` PRIORITY contradicts contract; oracle doesn't fix (Harbor review Critical) | **Disagree** | Env `environment/raft_mesh/errors.js:6-7` has `bad_encoding: 4` (intentional drift). Oracle patch `solution/raft_mesh.patch:115-148` reorders to match `consensus_contract.md:56`. No test triggers `bad_encoding`∩`rpc_term_stale` conflict. Ambiguous doc, not oracle failure. |
| 8 | `commands_committed >= 4` undocumented (LLMaJ / `entire-report.txt:136-137`) | **Agree** (Medium) | `test_outputs.py:229` asserts `>= 4`; `instruction.md:9` only requires `after.commands_lost == 0`. Phantom threshold — #27 UNCHECK, not High blocker. |
| 9 | Non-milestone task in milestone rubric format (`entire-report.txt:7-8`) | **Disagree** (format violation) | `task.toml:12` `number_of_milestones = 0`. `docs/guidelines/rubrics.md:66`: non-milestone may use flat list; `# Rubric 1` optional, no `# Rubric 2+`. Only issue is **42 > 40**, not milestone layout. |
| 10 | Dockerfile digest pinning (ChatGPT) | **Agree** | `environment/Dockerfile:1` `node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~3 prose paragraphs + requirement bullets; not spec-bloat | `instruction.md` |
| 2 | CHECK | Natural prompt tone | On-call incident framing; human tone | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | No `##`/tables in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal/outputs, defers detail to contract docs | `instruction.md` |
| 5 | CHECK | No hints/strategies | No module-by-module fix walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | Bullet output list only | `instruction.md:11-17` |
| 7 | CHECK | Well specified | Paths, schemas, rejection behavior, contract refs | `instruction.md`, `consensus_contract.md` |
| 8 | CHECK | Interesting | Distributed consensus forensic repair | — |
| 9 | CHECK | Unique | Raft replay + 20-tier rejection priority uncommon | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name absent | No `raft-consensus-recovery` string | `instruction.md` |
| 12 | CHECK | No canary | None found | `instruction.md` |
| 13 | CHECK | No web fetch in env | Local bundle replay only | `environment/` |
| 14 | CHECK | Pinned pip in image | `pytest==8.4.1`, etc. | `environment/Dockerfile:19-22` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:f3a68cf...` | `environment/Dockerfile:1` |
| 16 | CHECK | Env self-contained | COPY only under environment | `environment/Dockerfile:24-29` |
| 17 | CHECK | No ground truth in env | Broken stubs + red herrings only | `environment/raft_mesh/`, `forensics_notes.txt` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts clean | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:19-22`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | reward 1.0 | `./scripts/terminus oracle` |
| 22 | CHECK | Oracle no internet | patch + local replay | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded output | Patch derives replay; triage token fixed for split-brain scenario | `solution/raft_mesh.patch`, `solution/raft_mesh/triage.js` |
| 24 | CHECK | reward.txt + failure path | Writes 0/1 on pytest exit | `tests/test.sh:8-14` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:10-14` |
| 27 | UNCHECK | Tests aligned with instructions | Phantom `commands_committed` floors not in instruction | `test_outputs.py:229,255,440` vs `instruction.md:9` |
| 28 | CHECK | Tests check correctness | Replay outcomes, rejection codes, invariants | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | CLI integration only | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle where avoidable | Exact tokens required by spec (`raft_split_brain`, error codes) | `instruction.md`, tests |
| 31 | CHECK | Informative docstrings | All 21 `test_*` have one-line docstrings | `tests/test_outputs.py:209+` |
| 32 | CHECK | ≥3 negatives | 4 negatives | `entire-report.txt:474-477` |
| 33 | CHECK | Scores in ±1,2,3,5 | All lines comply | `entire-report.txt:457-477` |
| 34 | CHECK | Agent …, ±N format | 20 Agent lines | `entire-report.txt:457-477` |
| 35 | UNCHECK | Rubric detailed/precise | Positive total 42 > 40 cap | `entire-report.txt:457-473` |
| 36 | CHECK | Positive phrasing | Negatives describe bad actions with − scores | `entire-report.txt:474-477` |
| 37 | CHECK | No /tests/ refs | None in rubric | `entire-report.txt:457-477` |
| 38 | UNCHECK | No instruction.md refs | `(constraint from instructions)` | `entire-report.txt:472` |
| 39 | CHECK | No oracle/NOP refs | None | `entire-report.txt:457-477` |
| 40 | CHECK | Required files | All present | task tree |
| 41 | CHECK | Clean parent dir | No stray README/jobs in task dir | — |
| 42 | CHECK | author fields | Present | `task.toml:5-6` |
| 43 | CHECK | Other metadata | Complete | `task.toml` |
| 44 | UNCHECK | Tags/category match | `system-administration` mismatches code-repair work | `task.toml:8`, taxonomy |
| 45 | CHECK | Difficulty present | `hard`; worst-model 0% | `task.toml:7`, `entire-report.txt:39-45` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | `environment/.dockerignore:1-2` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution | `environment/.dockerignore:2` |
| 52 | CHECK | Input not trivially mutable | Dynamic bundles in tmp_path; golden config checked | `test_outputs.py:213-218` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:44-45` |
| 55 | CHECK | Not unfair | Contract docs authoritative; 0% reflects difficulty not missing env | `consensus_contract.md`, agent stats |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 27, 35, 38, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Default bundle `raft_split_brain`, `primary_node=n1` | `test_consensus_split_brain_recovery_on_default_partition` | covered | `test_outputs.py:222-224` |
| `after.split_brain_detected == false`, `commands_lost == 0` | same + pressure tests | covered | `test_outputs.py:226-227,254` |
| `rejected_causes` includes election/snapshot signals | — | **gap** (Low) | `instruction.md:9`; no assert |
| `term_timeline.csv` schema | default partition test | partial | `test_outputs.py:236-239` header + phase rows |
| `wal_digest.txt` manifest keys | default partition test | partial | `test_outputs.py:240-244` |
| `commands_committed >= 4` after recovery | default partition test | **phantom** | `test_outputs.py:229`; not in instruction |
| Pressure bundle `commands_committed > 200` | `test_pressure_bundle_restores_consensus` | **phantom** | `test_outputs.py:255` |
| 4000-command efficiency `commands_committed > 3000` | `test_large_pressure_trace_efficient` | **phantom** | `test_outputs.py:440` |
| 20 rejection codes + priority | rejection tests | covered | `test_outputs.py:293-477` |
| Config unchanged | default + integrity | covered | `test_outputs.py:217-218` |
| Rejection writes only `consensus_report.json` | rejection tests | covered | `test_outputs.py:307` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, #44 category, milestone N/A |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/.dockerignore` | #50-51 |
| `environment/raft_mesh/errors.js` | adjudication claim 7 |
| `environment/docs/consensus_contract.md` | #7, spec alignment, claim 7 |
| `tests/test.sh` | #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/raft_mesh.patch` | #21-23, claim 7 |
| `solution/raft_mesh/triage.js` | claim 2, #23 |
| `entire-report.txt` | #32-39, #45, #54, rubric, agent stats |
| `docs/task-type-taxonomy.md` | #44 |
| `docs/guidelines/rubrics.md` | #35, milestone format |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate raft-consensus-recovery/
Summary: 0 error(s), 22 warning(s), 1 info
Task type detected: regular
```

Docstring warnings are false positives — all test functions include docstrings.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | `entire-report.txt:45` |
| terminus-claude-opus-4-8 | 0.0% (0/5) | `entire-report.txt:44` |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle run 2026-07-03 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches `task.toml` name; regular non-milestone layout |
| 1 Instruction | ☑ | Concise; contract-backed; no canary |
| 2 Environment | ☑ | Digest-pinned Node; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Passes 1.0; patch fixes errors.js priority |
| 4 Verifiers | ☑ | 21 behavior tests; phantom commit thresholds noted |
| 5 Metadata | ☑ | Category mislabel Medium only |
| 6 Rubric | ☑ | 42>40 + instruction ref = blockers |
| 7 LLMaJ & agents | ☑ | Pressure-bundle failures = agent hardcoding, not env flake |
| 8 Novelty & fairness | ☑ | Anti-cheat solid; dynamic bundles |
| 9 Long context | ☐ | N/A — no `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Raft recovery task — the pinned Node environment, layered rejection tests, and dynamic bundle generation are all in great shape, and the oracle passes cleanly. Two rubric fixes before accept: trim the positive criteria so the total is 40 or less (it's 42 right now), and rephrase the config-immutability line so it doesn't say "constraint from instructions." Worth also relabeling `category` from `system-administration` to `software-engineering` or `debugging`, and optionally documenting the `commands_committed` floors the tests already enforce.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1, 2 |
| Metadata Issues | no (Medium only) | — |
| Test Alignment/Coverage Issues | no (Medium/Low gaps only) | — |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Milestones | no | — |
