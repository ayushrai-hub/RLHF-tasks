# Terminus Review Report: `mount-propagation`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed locally (Docker unavailable); report 100% 3/3 |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** none

**Decision (concise):** Accept. Prior human-review blockers are fixed: `task.toml` now declares `medium` (matches GPT-5.5 worst-model 40%), and apt packages are unpinned by name only. Digest-pinned multi-stage Rust/Python environment, verifier rebuild anti-cheat, 31 behavior tests with docstrings, oracle approach, and spec↔test alignment are solid. Automated `review` script false-positives on #31 (module docstring warning) and #45 (`worst_model_rate` uses `max` instead of `min`) are overturned on manual audit.

**Insights (concise):**

- Correct worst-model rate is **40%** (GPT-5.5 2/5), not 80% (Claude) — tier **Medium**, matching `task.toml:6`.
- `rk_` marker prohibition is specified via “internal run-stamp aliases” in `instruction.md:9` and explicitly in referenced `r7_tier_rules.md:15`; not a spec gap.
- Apt revision pins from prior review are removed; `environment/Dockerfile:14-23` installs unpinned package names only.
- All 31 `test_kp_h*` functions have informative names and per-test docstrings; only module-level docstring is missing (validate WARNING, not a portal blocker).
- Platform rubric in `entire-report.txt:322-335` meets format, score-set, and ≥3-negative rules.
- Instruction is 5 dense paragraphs (~350 words) — exceeds 3-paragraph styling cap (#1) but content is necessary export-contract prose, not step-by-step hints; Low severity only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` but grader rated MEDIUM (entire-report.txt:1-3) | **Agree (fixed)** | Was true at review time; now `task.toml:6` `difficulty = "medium"`; GPT-5.5 40% + Claude 80% per `entire-report.txt:26-27` |
| 2 | Apt packages pinned to Debian revisions — build fragility (entire-report.txt:4-5) | **Agree (fixed)** | `environment/Dockerfile:14-23` uses unpinned names (`ca-certificates`, `libssl3`, etc.); no `=20230311+deb12u1` style pins |
| 3 | ChatGPT Accept — prior blockers addressed, spec/test alignment solid | **Agree** | Manual re-audit confirms fixes above; LLMaJ quality checks PASS at `entire-report.txt:143-152`; no untested High requirements found |
| 4 | Automated review #45 fail: worst-model 80% → easy | **Disagree** | `scripts/review_checklist.py:167-169` uses `max(agent_rates)`; correct worst model = min(40%, 80%) = **40%** → Medium per `docs/guidelines/difficulty.md:10-11`; matches declared `medium` |
| 5 | Automated review #31 fail: missing test docstrings | **Disagree** | All 31 `def test_kp_h*` have docstrings (`tests/test_outputs.py:187-542`); validate WARNING is module-level only (`validate_task.py:548-553`) |
| 6 | `rk_` marker prohibition not in instruction (entire-report.txt:112-116) | **Disagree** | `instruction.md:9` bans “internal run-stamp aliases”; `r7_tier_rules.md:15` explicitly bans `rk_` prefixes; instruction references that doc at `instruction.md:9` |
| 7 | Non-canonical Rust builder image (entire-report.txt:182-204) | **Agree (non-blocking)** | `environment/Dockerfile:1-2` digest-pinned `rust:1.85-slim` with justification comment; runtime stage uses canonical `python:3.13-slim-bookworm` |
| 8 | Decoy `r7_desk` layout derailed agent 2mQpxtN (entire-report.txt:97-98) | **Disagree** | No `r7_desk` path in task tree; only `mount-propagation-desk` in `environment/Cargo.toml:2`; agent confusion not reproducible from artifacts |
| 9 | LLMaJ `behavior_in_task_description` PASS | **Agree** | Instruction + referenced schema/docs cover output path, rebuild mandate, WAL bleed, markers, generation, mp_echo isolation |
| 10 | Test quality ACCEPT — rebuild-from-source anti-cheat (entire-report.txt:292-316) | **Agree** | `stage_release_binaries()` at `tests/test_outputs.py:47-59`; ELF check `test_kp_h0`; independent segment/checkpoint/chain_ref ground truth |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 5 dense body paragraphs exceed 3-paragraph cap | `instruction.md:3-11` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone describing broken desk exports | `instruction.md:3-7` |
| 3 | CHECK | No excessive markdown formatting | Title + prose only; no ##/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States outcomes and constraints, not debug workflow | `instruction.md:7-9` |
| 5 | CHECK | No hints or solving strategies | WHAT to fix (export invariants), not HOW to patch modules | `instruction.md:7-9` |
| 6 | CHECK | No design doc style I/O tables | Prose requirements only | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, referenced schema/docs | `instruction.md:7-11` |
| 8 | CHECK | Instruction is interesting | Realistic Rust stateful-pipeline debugging | — |
| 9 | UNCHECK | Instruction is unique | Cannot verify vs TB2/TB3 corpus from artifacts alone | — |
| 10 | CHECK | All paths are absolute | `/app/environment`, `/app/output/...`, etc. | `instruction.md:3-11` |
| 11 | CHECK | Task name not in instruction.md | No “mount-propagation” string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content (except packages) | No runtime fetch in env Rust/Python code | `environment/src/` |
| 14 | CHECK | Python/pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:25-27` |
| 15 | CHECK | Base image digest-pinned | Both stages `@sha256:…` | `environment/Dockerfile:2,10` |
| 16 | CHECK | Environment context stays in environment/ | Dockerfile COPY scoped to env build context | `environment/Dockerfile:6-8,36` |
| 17 | CHECK | Environment has no ground-truth answers | Intentional bugs + symptom hints only; no precomputed matrix | `environment/support/lane_persist.rs`, `state/mp_lane.json` |
| 18 | CHECK | No privileged/dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in image; test.sh only pytest | `environment/Dockerfile:25-27`, `tests/test.sh:11` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally (no Docker); report 100% 3/3 | `entire-report.txt:31` |
| 22 | CHECK | Oracle needs no internet | solve.sh patches sources + `cargo build --release --locked` | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction (not hardcoded output) | Rewrites ~10 Rust modules + patches; rebuilds binaries | `solution/solve.sh:9-616` |
| 24 | CHECK | test.sh reward.txt + failure path | Writes 0/1; initial 0; mkdir verifier dir | `tests/test.sh:3-17` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only (0 or 1) | `echo 0` / `echo 1` only | `tests/test.sh:14-16` |
| 27 | CHECK | Tests aligned with instructions | All assertions trace to instruction or referenced docs | §5 below |
| 28 | CHECK | Tests check correctness not format-only | Segment cells, checkpoint markers, chain_ref, byte identity | `tests/test_outputs.py:164-184` |
| 29 | CHECK | Tests verify behavior not implementation | No source-file grep; runs compiled binary | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string matching | Assertions derived from fixture/checkpoint data | `tests/test_outputs.py:164-179` |
| 31 | CHECK | Tests have informative names or docstrings | 31 `kp_h*` names + per-test docstrings | `tests/test_outputs.py:187-542` |
| 32 | CHECK | Rubric ≥3 negative penalties | 4 negatives (-5,-5,-3,-2) | `entire-report.txt:332-335` |
| 33 | CHECK | Rubric scores from {±1,2,3,5} | All scores valid | `entire-report.txt:322-335` |
| 34 | CHECK | Rubric format `Agent …, ±N` | One line per criterion | `entire-report.txt:322-335` |
| 35 | CHECK | Rubric criteria detailed and precise | Module-specific behavioral criteria | `entire-report.txt:322-331` |
| 36 | CHECK | Rubric positive language for negatives | “Agent hand-patches…, -5” style | `entire-report.txt:332-333` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path references | `entire-report.txt:322-335` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:322-335` |
| 39 | CHECK | Rubric does not mention oracle/NOP | None | `entire-report.txt:322-335` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary parent files | Clean task folder layout | task root |
| 42 | CHECK | author_name and author_email present | Both in metadata | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, allow_internet, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, category applicable | rust/bash; system-administration; mount/state tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed pass rates | `medium` declared; worst model GPT 40% → Medium | `task.toml:6`, `entire-report.txt:26-27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution/answers not accessible in environment | solution/ not copied; tests/ not in image | `environment/Dockerfile:36-39` |
| 52 | CHECK | Agent cannot trivially pass by mutating inputs | Cross-validates segments + checkpoints + chain_ref + bytes | `tests/test_outputs.py` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst model 40% ≤ 80% | `entire-report.txt:26-27` |
| 55 | CHECK | Task not too hard or unfair | Requirements in instruction + referenced docs; reproducible fixtures | `instruction.md:9`, `r7_tier_rules.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 9, 21, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Repair Rust sources; rebuild release binaries | `test_kp_h0` | covered | `instruction.md:7`; `tests/test_outputs.py:187-193` |
| Output at `/app/output/r7_matrix_record.json` | all tests via `read_record()` | covered | `instruction.md:3`; `tests/test_outputs.py:12,89-90` |
| Delete stale matrix → regenerate from sources | `test_kp_h1` | covered | `instruction.md:7`; `tests/test_outputs.py:196-205` |
| No `wal_replay` observations in final export | `test_kp_h5`, `h7`, `h18`, `h23`, `h29` | covered | `instruction.md:9`; `tests/test_outputs.py:182-184` |
| No stale `_cache_stale` book cells | `assert_rows_match_segment` | covered | `instruction.md:9`; `tests/test_outputs.py:167-168` |
| Markers match checkpoint seeds; no `compact_wave_`/`rk_` | `assert_markers_match_checkpoint` | covered | `instruction.md:9`; `r7_tier_rules.md:15`; `tests/test_outputs.py:171-179` |
| Generation advances on repeat runs | `test_kp_h8`, `h25` | covered | `instruction.md:9`; `tests/test_outputs.py:284-291` |
| Cross-slug isolation / byte-identical chains | `test_kp_h2`, `h13`, `h24`, `h26` | covered | `instruction.md:5,11`; `tests/test_outputs.py:208-225` |
| mp_echo matches isolated run after marathon | `test_kp_h9` | covered | `instruction.md:11`; `tests/test_outputs.py:294-303` |
| Corrupt/truncated lane state recovery | `test_kp_h4`, `h12`, `h29` | covered | `instruction.md:5`; `tests/test_outputs.py:237-247` |
| chain_hex order-invariant via chain_ref | `test_kp_h3`, `h27` | covered | `r7_tier_rules.md:8`; `tests/test_outputs.py:227-234` |
| Multi-cycle evidence retention (wave1/wave2) | `test_kp_h10`, `h11`, `h14`, `h19` | covered | `r7_tier_rules.md:23`; `tests/test_outputs.py:306-361` |
| Segment branch in observations | `test_kp_h28` | covered | `r7_tier_rules.md:10`; `tests/test_outputs.py:511-519` |
| Verifier rebuilds from agent sources | session fixture + `test_kp_h0` | covered | `instruction.md:7`; `tests/test_outputs.py:47-64` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27, spec alignment |
| `task.toml` | #42-45, difficulty adjudication |
| `environment/Dockerfile` | #14-20, apt-pin fix, pinning |
| `environment/docs/r7_tier_rules.md` | #27, rk_ adjudication |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, anti-cheat, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | agent stats, rubric, prior review claims |
| `scripts/review_checklist.py` | #45 false-positive explanation |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: mount-propagation/ ===
Summary: 0 error(s), 2 warning(s), 2 info
Warnings: missing module-level docstring (tests/test_outputs.py); missing .dockerignore
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Worst model — sets tier floor |
| terminus-claude-opus-4-8 | 80.0% (4/5) | 1 timeout |
| oracle | 100.0% (3/3) | Per external report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular Rust task; folder matches report |
| 1 Instruction | ☑ | Dense but testable; #1 length exceeds cap (Low) |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; apt unpinned; no tests/solution COPY |
| 3 Oracle | ☑ | solve.sh derives via source patches + cargo build; not run locally |
| 4 Verifiers | ☑ | Canonical reward block; rebuild fixture; 31 docstrings |
| 5 Metadata | ☑ | medium matches 40% worst model; allow_internet=false |
| 6 Rubric | ☑ | Platform rubric validated from entire-report.txt:322-335 |
| 7 LLMaJ & agent evidence | ☑ | All quality checks PASS; 1/10 timeouts (non-blocking) |
| 8 Novelty & fairness | ☑ | Multi-module Rust debugging; rk_ contract in referenced docs |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. Prior revision items are resolved: `task.toml` now declares `medium` (matching GPT-5.5 at 40% worst-model), and apt packages are no longer pinned to fragile Debian revision strings. The digest-pinned multi-stage environment rebuilds `ctl_r7` and `chain_ref` from agent sources before scoring, 31 behavior tests align with instruction and referenced tier rules (including `rk_`/WAL/generation invariants), and oracle evidence is 100% in the evaluation report. No High-severity spec gaps or cheating paths found on re-audit.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Time Based Tests | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus review mount-propagation/ --report entire-report.txt`._
