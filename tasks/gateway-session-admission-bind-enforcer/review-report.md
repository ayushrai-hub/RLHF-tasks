# Terminus Review Report: gateway-session-admission-bind-enforcer

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 64 warnings — mostly false-positive docstring detector) |
| **Oracle** | pass (report: 100% 3/3; local oracle not re-run — Harbor config error) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Metadata Issues

**Decision (concise):** Milestone layout, digest-pinned canonical Go Dockerfile, offline verifier venv, tests/solution exclusion, oracle pass rate, Hard difficulty calibration (Claude 20% worst model), and spec-to-test alignment are solid. The only real blocker is metadata: `task.toml` lists 7 tags but the spec allows 3–6. Remove one tag (e.g. `go`, already in `languages`). Automated review false positives on pip pinning (#14), verifier deps (#20), docstrings (#31), and difficulty (#45) are rejected below.

**Insights (concise):**

- ChatGPT’s sole High finding (7 tags) is confirmed; all other automated blockers are false positives on manual re-audit.
- Every `test_*` in `test_m1.py` and `test_m2.py` has an informative docstring; validate warnings are a detector bug.
- `requirements.lock` pins pytest with `==` and `--hash=sha256:`; Dockerfile installs via `--require-hashes` at build time — #14 passes.
- Claude Opus 4.8 at 20% (worst model) satisfies Hard tier (≤20%); GPT-5.5 at 60% does not override worst-model floor.
- M1 `scope_gen=0` vs M2 `scope_gen` bump is intentional milestone progression documented in instructions and `deferred-reload.md` — not a harness contradiction.
- LLMaJ `behavior_in_task_description` fail is advisory; normative contracts live in shipped `/app/docs/` per milestone-task design.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | Medium | Metadata Issues | #44 | `tags` array has 7 entries; `task.toml` spec allows 3–6 | `task.toml:12` — `["edge-gateway", "admission-control", "session-integrity", "tamper-evidence", "policy-reload", "rate-limiting", "go"]`; `docs/task-requirements.md:28`; `./scripts/terminus validate` warns | Remove one tag (recommend dropping `go` since `languages` already includes it) |

*No other High or Medium blockers found on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Tags array exceeds 3–6 maximum (ChatGPT / entire-report §2) | **Agree** | `task.toml:12` (7 tags); `docs/task-requirements.md:28` |
| 2 | Milestone layout, Dockerfile pinning, offline verifier, anti-cheat, oracle, Hard calibration solid (ChatGPT) | **Agree** | `environment/Dockerfile:1,25–27`; `environment/.dockerignore:11–12`; `entire-report.txt:1–11` (oracle 100%, Claude 20%) |
| 3 | Instructions extremely terse; lack explicit success criteria (entire-report warning §1) | **Disagree** as blocker | `steps/milestone_1/instruction.md:1–5` names broken subsystems + doc paths; `steps/milestone_2/instruction.md:3` states M2 behavioral deltas; appropriate for hard debugging task |
| 4 | Non-canonical Docker base image (entire-report warning §3) | **Disagree** | `environment/Dockerfile:1` uses canonical `golang:1.24-bookworm@sha256:1a6d4452…` per `docs/guidelines/dockerfxile.md:11` |
| 5 | `behavior_in_task_description` FAIL — behaviors only in referenced docs (entire-report LLMaJ) | **Disagree** as blocker | Instructions name normative `/app/docs/*.md` contracts; M1/M2 bullets state scope_gen, queue_reload, digest rules; `docs/guidelines/prompt-styling.md:49–52` allows milestone doc references |
| 6 | M1 visible harness contradicts M2 `scope_gen` bump — environment design flaw (entire-report agent analysis §4) | **Disagree** | `steps/milestone_1/instruction.md:5` (`scope_gen` stays 0); `steps/milestone_2/instruction.md:3` (`fresh_start bumps scope_gen`); `environment/docs/deferred-reload.md:11–14`; M2 `test.sh:28` runs only `test_m2.py` |
| 7 | Automated review blocker #14 unpinned pip | **Disagree** | `environment/requirements.lock:5–15` (`pytest==9.0.3` + hashes); `environment/Dockerfile:27` (`--require-hashes`) |
| 8 | Automated review blocker #20 pytest not in Dockerfile | **Disagree** | `environment/Dockerfile:26–27` builds `/opt/verifier-venv`; `steps/milestone_1/tests/test.sh` has no `pip install` |
| 9 | Automated review blocker #31 missing docstrings | **Disagree** | All 38 M1 + 23 M2 `test_*` functions have docstrings, e.g. `test_m1.py:242–243`, `test_m2.py:210–211` |
| 10 | Automated review blocker #45 difficulty mismatch | **Disagree** | `task.toml:6` `hard`; `entire-report.txt:6–7` Claude 20% = worst model ≤20% → Hard per `docs/guidelines/difficulty.md:9–14` |
| 11 | Test quality ROBUST for both milestones (entire-report) | **Agree** | Independent reference digests; hidden TB3 fixtures staged at runtime in M2 `test.sh:21–23` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | M1/M2 each ≤3 problem paragraphs | `steps/milestone_1/instruction.md`; `steps/milestone_2/instruction.md` |
| 2 | CHECK | Natural prompt tone | Terse engineering voice, not LLM spec dump | milestone instructions |
| 3 | CHECK | No excessive markdown | Plain prose, no ##/tables | milestone instructions |
| 4 | CHECK | No step-by-step HOW | States WHAT + doc contracts; no solve walkthrough | milestone instructions |
| 5 | CHECK | No hints/strategies | No leaked bug locations or fix recipes | milestone instructions |
| 6 | CHECK | No design-doc tables | None in instructions | milestone instructions |
| 7 | CHECK | Well specified | Milestone bullets + normative `/app/docs/` | `steps/milestone_2/instruction.md:3`; `environment/docs/` |
| 8 | CHECK | Interesting | Real edge-gateway admission-control debugging | task scope |
| 9 | CHECK | Unique | No duplicate found in review corpus | manual assessment |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/docs/…` throughout | milestone instructions |
| 11 | CHECK | Task name not in instruction | Folder name absent | milestone instructions |
| 12 | CHECK | No canary string | None detected | milestone instructions |
| 13 | CHECK | No web fetch in env | Offline Go driver + local docs | `environment/` |
| 14 | CHECK | Pinned pip deps | `==` versions + sha256 hashes in lockfile | `environment/requirements.lock`; `environment/Dockerfile:27` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY limited to env subdirs | `environment/Dockerfile:31–36` |
| 17 | CHECK | No ground truth in env | Intentional bugs, not answer keys | `environment/session/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest venv baked; test.sh no installs | `environment/Dockerfile:26–27`; `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle offline | `go build` only in solve scripts | `steps/milestone_1/solution/solve1.sh:27` |
| 23 | CHECK | Oracle not hardcoded | Copies corrected Go sources + builds | `steps/milestone_1/solution/solve1.sh:9–27` |
| 24 | CHECK | reward.txt canonical | mkdir + pytest + 0/1 write | `steps/milestone_1/tests/test.sh:6–29` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | test.sh files |
| 26 | CHECK | Binary rewards | 0 or 1 only | test.sh files |
| 27 | CHECK | Tests aligned with instructions | M1/M2 scope_gen split documented | `deferred-reload.md:11–14`; milestone instructions |
| 28 | CHECK | Tests check correctness | Crypto seals, token counts, state machine | `test_m1.py`; `test_m2.py` |
| 29 | CHECK | Behavior not implementation grep | Black-box `go run main.go` | `test_m1.py:38–42` |
| 30 | CHECK | Not brittle string match | Exact hashes required by spec | test design |
| 31 | CHECK | Informative docstrings | All `test_*` documented | `test_m1.py:242+`; `test_m2.py:210+` |
| 32 | UNCHECK | ≥3 negative rubric criteria | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Valid rubric scores | N/A — no rubric file in task folder | — |
| 34 | UNCHECK | Rubric format | N/A — no rubric file in task folder | — |
| 35 | UNCHECK | Rubric precise | N/A — no rubric file in task folder | — |
| 36 | UNCHECK | Positive rubric phrasing | N/A — no rubric file in task folder | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A — no rubric file in task folder | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A — no rubric file in task folder | — |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A — no rubric file in task folder | — |
| 40 | CHECK | Required files present | Milestone layout complete | `task.toml`; `steps/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task folder |
| 42 | CHECK | author fields | Present | `task.toml:4–5` |
| 43 | CHECK | Metadata complete | version, category, timeouts, milestones | `task.toml` |
| 44 | UNCHECK | Tags/languages/category fit | 7 tags exceeds 3–6 limit | `task.toml:12` — Blocker #1 |
| 45 | CHECK | Difficulty matches rates | `hard` vs Claude 20% worst model | `entire-report.txt:6–7` |
| 46 | CHECK | steps/ milestone layout | 2 milestones under `steps/` | `task.toml:24–40` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh, solve2.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py, test_m2.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Per-milestone scope | M1 immediate reload; M2 deferred replay | test file headers + scope |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests/ | `environment/.dockerignore:12` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/ | `environment/.dockerignore:11` |
| 52 | CHECK | Input not trivially mutable | Hidden TB3 fixtures chmod 700 at test time | `steps/milestone_2/tests/test.sh:21–23` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 20% ≤80% | `entire-report.txt:6–7` |
| 55 | CHECK | Not unfair | M1/M2 scope split is documented; agent near-misses are reading/stub errors | `entire-report.txt:100–121` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 44 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: `scope_gen` stays 0 on `fresh_start` | `test_m1_fresh_start_keeps_scope_gen_zero` | covered | `steps/milestone_1/instruction.md:5`; `test_m1.py:552–553` |
| M2: `fresh_start` bumps `scope_gen` | `test_fresh_start_increments_scope_gen` | covered | `steps/milestone_2/instruction.md:3`; `test_m2.py:386–387` |
| M1: refill before consume | `test_refill_applies_before_consume_same_run` | covered | `test_m1.py:375` |
| M1: weighted round-robin when backend empty | `test_weighted_backend_selection` | covered | `test_m1.py:604` |
| M1: admit_seal / ledger sealing | `test_ledger_admit_seal_matches_reference` | covered | `test_m1.py:283` |
| M1: checkpoint chain genesis/archive/verify | `test_checkpoint_chain_*` | covered | `test_m1.py:707–771` |
| M1: admission-bind scope_epoch | `test_bind_scope_epoch_tracks_token_levels` | covered | `test_m1.py:821` |
| M2: FIFO `replay_pending` | `test_replay_applies_multiple_queued_configs_in_order` | covered | `test_m2.py:318` |
| M2: stale `reload_scope` skips replay | `test_stale_reload_scope_skips_queued_replay` | covered | `test_m2.py:371` |
| M2: digest `pending_reload_count=0` when scope stale | `test_digest_excludes_stale_pending_reload_count` | covered | `steps/milestone_2/instruction.md:3`; `test_m2.py:412` |
| M2: `state_digest` from ledger-sealed fields | `test_state_digest_matches_persisted_files` | covered | `test_m2.py:444` |
| M2: hidden TB3 edge fixtures | `test_tb3_replay_queue_applies_enqueue_order` | covered | `test_m2.py:499` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker #1, #44, #45 |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | #14 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/deferred-reload.md` | #27, adjudication #6 |
| `steps/milestone_1/instruction.md` | #1, #7, #10, spec alignment |
| `steps/milestone_2/instruction.md` | #7, spec alignment |
| `steps/milestone_1/tests/test_m1.py` | #31, spec alignment |
| `steps/milestone_2/tests/test_m2.py` | #31, spec alignment |
| `steps/milestone_1/tests/test.sh` | #20, #24 |
| `steps/milestone_2/tests/test.sh` | #20, #52 |
| `entire-report.txt` | #21, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate gateway-session-admission-bind-enforcer/
Summary: 0 error(s), 64 warning(s), 2 info
Notable real warning: tags 7 > 6 (task.toml:12)
False-positive warnings: 61× informative_test_docstrings (all tests have docstrings on manual inspection)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Medium tier individually |
| terminus-claude-opus-4-8 | 20.0% (1/5) | Worst model; Hard tier boundary |
| oracle | 100.0% (3/3) | Per report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; 2-milestone Go security task |
| 1 Instruction | ☑ | Terse but complete with doc references; M1/M2 scope rules explicit |
| 2 Environment | ☑ | Canonical digest-pinned Go base; tmux+asciinema; verifier venv baked |
| 3 Oracle | ☑ | solve1/2 copy fixes + `go build`; report 100% |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; all docstrings present |
| 5 Metadata | ☐ | 7 tags — Blocker #1 |
| 6 Rubric | ☑ | N/A — rubric only in portal report, not task folder |
| 7 LLMaJ & agent evidence | ☑ | Reconciled; harness contradiction rejected |
| 8 Novelty & fairness | ☑ | Multi-file Go debugging; anti-cheat solid |
| 9 Long context | ☑ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, digest-pinned Go Dockerfile, offline verifier setup, tests/solution exclusion, oracle pass rate, Hard difficulty calibration, and spec-to-test alignment all look solid. The only blocker is metadata: `task.toml` has 7 tags (allowed range 3–6). Remove one tag — recommend dropping `go` since it is already captured in `languages`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |
