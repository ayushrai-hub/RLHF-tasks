# Terminus Review Report: exec-profile-cap-bound-drift1

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** Structure, environment, verifiers, and instruction spec are solid after the wrapped-sync `eff_post`/`stamp_code` clarification in `instruction.md:5`. Verifier deps are baked into the digest-pinned Dockerfile; `test.sh` has no runtime installs. The sole High blocker is metadata: `task.toml` declares `difficulty = "hard"` but agent evaluation shows worst-model 60% (GPT-5.5), which maps to **medium** per `docs/guidelines/difficulty.md`. Update `difficulty` to `"medium"` or rebalance until ≤20% on at least one model.

**Insights (concise):**

- Prior wrapped-sync spec gap (`gap_code`/`eff_post`/`stamp_code`) is fixed in current `instruction.md:5`; disagree with `entire-report.txt` line 1 blocker.
- Automated `./scripts/terminus review` false-flagged #14 (pip is `==`-pinned on following lines), #31 (validator regex misses `-> None:` return annotations), and #54 (script uses `max()` instead of `min()` for worst-model rate).
- Agent stats: Claude Opus 4.8 100% (5/5), GPT-5.5 60% (3/5); task is medium-tier, not too easy (#54 passes at 60% ≤ 80%).
- LLMaJ `behavior_in_task_description` and `behavior_in_tests` both pass; 18-test SHA-256 bundle resists shortcut solutions.
- Oracle not run locally (Docker daemon unavailable); static review of `solution/solve.sh` shows multi-file repair + rebuild + pipeline execution, not hardcoded JSON.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | `task.toml` declares `hard` but worst-model pass rate is 60% (medium tier) | `task.toml:6`; `entire-report.txt:4-9` | Set `difficulty = "medium"` in `task.toml`, or rebalance task until ≤20% on best or worst model |

*No other High blockers. Automated flags for #14, #31, #54 were false positives (see section 3).*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `difficulty = "hard"` but evaluation is Medium (100% Claude, 60% GPT-5.5) | **Agree** | `task.toml:6`; `entire-report.txt:7-9`; worst model = min(100, 60) = 60% → medium per `docs/guidelines/difficulty.md` |
| 2 | ChatGPT: prior wrapped-sync instruction issue fixed; Dockerfile digest-pinned; no compose issue | **Agree** | `instruction.md:5` now states `eff_post` gap/stamp rules; `environment/Dockerfile:1`; no `docker-compose.yaml` |
| 3 | `entire-report.txt` line 1: remaining blocker is wrapped-sync `gap_code`/`stamp_code` not in instruction | **Disagree** | `instruction.md:5`: "`gap_code` clears to `G0` when the `required` subset … is present in the post-merge effective mask (`eff_post`), not `eff_pre`, and `stamp_code` must equal `open_stamp` when the stage gate permits that subset" |
| 4 | `entire-report.txt` line 1: "Hard difficulty is supported by the 0% Claude result" | **Disagree** | `entire-report.txt:8`: Claude Opus 4.8 100.0% (5/5 runs) — contradicts line 1 |
| 5 | Agent failure analysis: NNP routing for `bound_set_hash` unstated in instruction (`test_c00`) | **Partially agree** | `instruction.md:5`: "published bounds always follow `base.dat`" but NNP merge formula `(eff&0xF0)\|(bnd&0x0F)` not spelled out; repair task expects code reading; `test_c00` 8/10 pass — not a High blocker |
| 6 | LLMaJ `behavior_in_task_description`: PASS | **Agree** | Cross-checked `instruction.md` vs `tests/test_outputs.py`; wrapped-sync, ambient merge, bridge inheritance, journal merge all stated |
| 7 | LLMaJ `pinned_dependencies`: PASS | **Agree** | `environment/Dockerfile:33-35`: `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 8 | Human report WARNING: debian base instead of gcc:13-bookworm | **Disagree as blocker** | `environment/Dockerfile:1` uses digest-pinned debian + `build-essential=12.9`; canonical list allows debian; Low/note only |
| 9 | Human report WARNING: dense single-paragraph instruction | **Partially agree** | `instruction.md` is 3 paragraphs (~403 words), normative but complete; styling note only, not High |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraph blocks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first tone; paragraph 3 is normative but standard for crypto-audit tasks | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | Plain paragraphs, inline backticks only | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Lists required CLI invocations and output schema, not bug-fix walkthrough | `instruction.md:3-5` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT to emit and repair scope, not which source lines to patch | `instruction.md:3-5` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Output path, schema, hash formulas, gap/stamp/bridge rules specified | `instruction.md:3-5` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Linux capability bounding-set debugging | `instruction.md:1` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Specialized cap-audit domain; not verified against full corpus but no duplicate signal in artifacts | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | All `/app/...` paths | `instruction.md:3-5` |
| 11 | CHECK | Task name does not appear in instruction.md | No "exec-profile-cap-bound-drift1" | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | apt only; no runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Packages pinned on continuation lines | `environment/Dockerfile:33-35` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only env subdirs | `environment/Dockerfile:37-48` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Intentional bugs in source, not final audit JSON | `environment/q2_auth/commit.sh`, `environment/q4_core/main_core.c` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh runs venv pytest only | `environment/Dockerfile:32-35`, `tests/test.sh:14-15` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed — Docker daemon unavailable | `./scripts/terminus oracle` exit 0 but 0 trials / RuntimeError |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh patches files, make, k9_round only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Writes corrected C/shell, rebuilds, runs full chain | `solution/solve.sh:4-620` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:6-22` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Writes 0 or 1 only | `tests/test.sh:18-21` |
| 27 | CHECK | All tests are aligned with instructions | Each test maps to stated requirement (see section 5) | `instruction.md:5`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | SHA-256 hash assertions on computed capability state | `tests/test_outputs.py:68-99` |
| 29 | CHECK | Tests verify behavior, not implementation | Invokes k9_round/m2_publish; no source grep | `tests/test_outputs.py:114-150` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Hash-based verification, not long static strings | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 18 `test_c*` functions have docstrings | `tests/test_outputs.py:186-414` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task folder |
| 41 | CHECK | No unnecessary files in parent directory | No jobs/, README.md, stray data | task folder |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, resources | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | security; bash+c; capabilities/PAM tags match content | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 60% → medium | `task.toml:6`, `entire-report.txt:7-9` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | No solution/ in image; `.dockerignore` excludes it | `environment/.dockerignore:8` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | `bundle_digest` SHA-256 binds all rows; must run pipeline | `tests/test_outputs.py:93-99` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 60% ≤ 80% | `entire-report.txt:8-9` |
| 55 | CHECK | Task is not too hard or unfair | Wrapped-sync rules now explicit; repair task with readable fixtures | `instruction.md:5` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 21, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Repair under `/app/environment`, rebuild, k9_round r0–r3, m2_publish | all tests via `_full_chain()` | covered | `instruction.md:3`, `tests/test_outputs.py:160-170` |
| Output `/app/output/cap_audit.json` schema + sorting | `test_c10_row_order_canonical` | covered | `instruction.md:5`, `tests/test_outputs.py:319-323` |
| `class_tag` from `auth_table` | `test_c01_auth_table_fidelity` | covered | `instruction.md:5`, `tests/test_outputs.py:198-214` |
| `bound_set_hash` over `cap_bound` bytes; bounds from `base.dat` | `test_c00`, `test_c03` | covered | `instruction.md:5`, `tests/test_outputs.py:186-195` |
| NNP bound routing (repair task; formula in code) | `test_c00_nnp_bound_route` | covered | `tests/test_outputs.py:179-195`; minor formula not in instruction text |
| Wrapped r1 `gap_code` G0 when subset in `eff_post` | `test_c02_gap_trace` | covered | `instruction.md:5`, `tests/test_outputs.py:216-224` |
| Wrapped r1 `stamp_code` = `open_stamp`; subset in effective hash | `test_c04`, `test_c17` | covered | `instruction.md:5`, `tests/test_outputs.py:237-246,413-430` |
| Ops `SCOPE=ops` ambient merge | `test_c08`, `test_c07` | covered | `instruction.md:5`, `tests/test_outputs.py:271-298` |
| R3 bridge inherits r2 ops direct effective view after `generation=1` | `test_c07`, `test_c11`, `test_c12`, `test_c16` | covered | `instruction.md:5`, `tests/test_outputs.py:271-356,403-410` |
| Latest `seq_code` on publish; journal merge | `test_c05`, `test_c13` | covered | `instruction.md:5`, `tests/test_outputs.py:249-257,358-368` |
| Rebuild from journal when store missing | `test_c14_journal_store_rebuild` | covered | `instruction.md:5`, `tests/test_outputs.py:371-387` |
| Byte-identical re-publish | `test_c06_warm_replay_stable` | covered | `instruction.md:5`, `tests/test_outputs.py:260-268` |
| `probe_side.sh` inert; writes `launch_probe.log` | `test_c15_launch_probe_side_inert` | covered | `instruction.md:3`, `tests/test_outputs.py:390-400` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, #55, blocker adjudication |
| `task.toml` | #42-45, blocker 1 |
| `environment/Dockerfile` | #13-20, #50, #53 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #45, #54, agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: exec-profile-cap-bound-drift1/ ===
Summary: 0 error(s), 19 warning(s), 2 info
Task type detected: regular
```

Warnings are false positives: pip `==` on continuation lines (`Dockerfile:34-35`); docstring regex misses `-> None:` annotations (`test_outputs.py:186+`).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Per report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

Per-test pass rates (`entire-report.txt:20-37`): systematic failures on c00/c02/c03/c04/c07/c08/c17 at 8/10 — consistent with partial repair, not current instruction gap on wrapped-sync.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; security/tool_specific |
| 1 Instruction | ☑ | 3 paragraphs; eff_post/stamp rules present; absolute paths |
| 2 Environment | ☑ | Digest-pinned debian; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☐ | Not executed (Docker unavailable); static review passes |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; 18 behavior tests with docstrings |
| 5 Metadata | ☑ | Complete except difficulty mismatch |
| 6 Rubric | N/A | No rubric.txt in task folder (rubric lines in report are portal-only) |
| 7 LLMaJ & agent evidence | ☑ | Reconciled contradictions in entire-report; ChatGPT difficulty claim verified |
| 8 Novelty & fairness | ☑ | Multi-step repair; SHA-256 anti-cheat; no contradictory reqs |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, and Dockerfile pinning look solid, and the prior wrapped-sync instruction gap is fixed (`eff_post`/`stamp_code` rules are now explicit in `instruction.md`). Verifier dependencies are baked into the image with no runtime installs. The remaining blocker is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium tier (GPT-5.5 60%, Claude 100%). Update `difficulty` to `medium` or rebalance until the task qualifies as hard.

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
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Rubric | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline generated by `./scripts/terminus review exec-profile-cap-bound-drift1/ --report entire-report.txt`._
