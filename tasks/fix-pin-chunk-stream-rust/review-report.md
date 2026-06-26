# Terminus Review Report: `fix-pin-chunk-stream-rust`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (report); not re-run locally (Docker unavailable) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** Environment, oracle design, anti-cheat, and verifier logic are sound. Digest-pinned canonical `rust:1.85-slim` base, offline Cargo.lock builds, and independent Python FNV oracle are correct. The only confirmed High blocker is metadata: `task.toml` declares `difficulty = "hard"` but calibrated worst-model pass rate is Claude 60% (medium tier). ChatGPT’s instruction and monolithic-test findings are quality notes, not acceptance blockers under current pass rates and doc-driven task design.

**Insights (concise):**

- Worst model = **minimum** agent pass rate (Claude 60%), not GPT-5.5 80%; automated `terminus review` uses `max()` and mis-tiers #45/#54.
- `environment/Dockerfile:1` matches canonical `rust:1.85-slim@sha256:9f841bbe…` in `docs/guidelines/dockerfxile.md:12` — non-canonical-base claim is false.
- `#14` / `#31` automated fails are false positives: pip packages are `==`-pinned on continuation lines; test has a docstring but multiline `def` breaks the crude regex.
- Instruction delegates normative contract to `/app/docs/` (e.g. `export-catalog.md:3` names `catalog.json`); 60–80% pass rates show this is workable, not systematically unfair.
- Monolithic `test_chunk_replay_matches_contract` is a Medium diagnostic note only; single Medium ≠ Revise per severity rules.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but worst-model pass rate is 60% → **medium** tier | `task.toml:8` `difficulty = "hard"`; `entire-report.txt:23-24` Claude 60% (3/5), GPT-5.5 80% (4/5); `docs/guidelines/difficulty.md:9-12` medium = 20–60% on worst model | Set `difficulty = "medium"` in `task.toml`, or rebalance task until worst-model ≤20% for hard |

*No other High blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` mismatches observed medium/easy tier (ChatGPT High; `entire-report.txt:18`) | **Agree** | `task.toml:8`; worst model = min(60%, 80%) = 60% → medium per `docs/guidelines/difficulty.md:10-11`; neither model ≤20% for hard |
| 2 | Instruction too terse; must name `catalog.json`, CLI commands, active docs (ChatGPT High; `entire-report.txt:92,101`) | **Partially agree** | `instruction.md:1` is one sentence; `export-catalog.md:3-7` names `/app/data/replay_out/catalog.json`, soak, `make release`; `offset-semantics.md:7` names `probe-one`/`replay-one`. Improvement optional; 60–80% pass rates (`entire-report.txt:23-24`) show not systematically unfair. Not a High blocker. |
| 3 | Monolithic test function hurts diagnostics (ChatGPT Medium; `entire-report.txt:94,209-242`) | **Agree (non-blocking)** | `tests/test_outputs.py:109-149` single `test_chunk_replay_matches_contract` covers 6+ concerns. Medium severity; single Medium → accept-with-note per `docs/reviewer-checklist-full.md:12-13` |
| 4 | `behavior_in_task_description` / `file_reference_mentioned` LLMaJ fails (`entire-report.txt:92,101`) | **Partially agree** | Instruction omits exact `catalog.json` path and `cargo test`; covered by “match in-tree export docs” + `export-catalog.md`. Phantom fixture-count asserts at `test_outputs.py:118-120` not in instruction. Not High given doc delegation + pass rates. |
| 5 | Instruction sufficiency 0/3 trials; agents misread task as static JSON edit (`entire-report.txt:39-71`) | **Partially agree** | 3-trial probe shows misdirection risk; main calibration 60–80% (`entire-report.txt:23-24`) contradicts systematic failure. One trial stuck in PS2 (`entire-report.txt:89`). Fairness note, not blocker. |
| 6 | Non-canonical base image (`entire-report.txt:184-205`) | **Disagree** | `environment/Dockerfile:1` = `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` — exact match `docs/guidelines/dockerfxile.md:12` |
| 7 | Unpinned pip / missing docstrings (automated `terminus review` blockers #14, #31) | **Disagree** | `environment/Dockerfile:15-17` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; `test_outputs.py:113` docstring present — regex in `scripts/validate_task.py:558` fails on multiline signatures |
| 8 | Test quality review ACCEPT (`entire-report.txt:306-333`) | **Agree** | Independent Python FNV oracle at `test_outputs.py:27-48`; compares all traces; soak determinism checked |
| 9 | Architecture preservation not tested (`entire-report.txt:340-372`) | **Agree (observation only)** | Output-behavior tests only; acceptable per test-quality review — not a blocker |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | One sentence, ~34 words | `instruction.md:1` |
| 2 | CHECK | Natural prompt tone | Reads as internal bug ticket, not spec dump | `instruction.md:1` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States outcome + doc reference only | `instruction.md:1` |
| 5 | CHECK | No hints / solving strategies | No module-level fix walkthrough | `instruction.md:1` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal: fix catalog export to match normative `/app/docs/` | `instruction.md:1`, `export-catalog.md:1-9` |
| 8 | CHECK | Interesting | Realistic Rust pin/buffer streaming debug task | task design |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app/data`, `/app/bin/streamd`, etc. | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No `fix-pin-chunk-stream-rust` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No urllib/curl in app code | `environment/app/` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15-17` |
| 15 | CHECK | Base image digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | `COPY app/ /app/` | `environment/Dockerfile:21` |
| 17 | CHECK | No ground-truth answers in env | Docs define contracts; bugs in source, not answer keys | `environment/app/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:15-17`, `tests/test.sh:14-15` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:28` |
| 22 | CHECK | Oracle no internet | solve.sh writes Rust sources + cargo build | `solution/solve.sh:6-273` |
| 23 | CHECK | Oracle derives results | Fixes lend-core modules, builds binary | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir + pytest + 0/1 reward | `tests/test.sh:3-21` |
| 25 | CHECK | Same verifier logic for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:17-20` |
| 27 | CHECK | Tests aligned with instructions | All major behaviors trace to instruction + export docs; minor fixture-count asserts are sanity-only | `instruction.md:1`, `export-catalog.md`, `test_outputs.py:109-149` |
| 28 | CHECK | Tests check correctness | Independent FNV oracle vs streamd output | `test_outputs.py:27-48,142-145` |
| 29 | CHECK | Behavior not implementation grep | CLI + catalog output only | `test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Expected digests computed from bytes | `test_outputs.py:59-64` |
| 31 | CHECK | Informative test docstrings | Module + test docstrings present | `test_outputs.py:1`, `test_outputs.py:113` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — rubric in portal only | `entire-report.txt:376-393` |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, tests | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust, data-processing, tool_specific | `task.toml:8-17` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; worst model 60% → medium | `task.toml:8`, `entire-report.txt:23-24`, blocker #1 |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:13` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:13` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:13` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests/; no COPY tests/ | `environment/.dockerignore:11`, `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible | solution/ in .dockerignore | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially modify inputs | Instruction forbids editing traces/config; verifier reads fixtures | `instruction.md:1` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% (not >80%) | `entire-report.txt:23-24`, `docs/reviewer-checklist-ui.md:56-60` |
| 55 | CHECK | Not unfair | 60–80% pass; failures are partial Rust fixes, not missing spec | `entire-report.txt:23-24,75-83` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Fix catalog JSON under `/app/data` | `test_chunk_replay_matches_contract` catalog asserts | covered | `instruction.md:1`, `export-catalog.md:3`, `test_outputs.py:142-145` |
| Match in-tree export docs (digest FNV-8, offsets) | catalog + probe/replay alignment | covered | `chunk-contract.md:7-13`, `digest-format.md:1-15`, `test_outputs.py:126-145` |
| Build `/app/bin/streamd` via `make release` | `_release_build` fixture | covered | `instruction.md:1`, `test_outputs.py:88-94,124` |
| Keep soak from drifting | soak script assert | covered | `export-catalog.md:7`, `test_outputs.py:148-149` |
| `cargo test` still passes (“Tests still pass”) | cargo test assert | covered | `instruction.md:1`, `test_outputs.py:122-123` |
| Config/traces off limits | not directly tested (rubric penalty) | gap (acceptable) | `instruction.md:1`, `entire-report.txt:389` |
| `replay-one` / `probe-one` offset alignment | per-trace loop | covered | `offset-semantics.md:7`, `test_outputs.py:126-140` |
| Fixture tree has ≥8 traces with qa/ subset | trace count asserts | phantom (sanity) | `test_outputs.py:118-120` — pre-shipped fixtures, not agent action |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, blocker #1, #43-44 |
| `instruction.md` | #1-7, #10-12, #27, spec alignment |
| `environment/Dockerfile` | #14-16, #20, #50 |
| `environment/.dockerignore` | #50-51 |
| `environment/app/docs/export-catalog.md` | spec alignment, claim #2 |
| `environment/app/docs/chunk-contract.md` | spec alignment |
| `environment/app/docs/offset-semantics.md` | spec alignment |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `tests/test.sh` | #20, #24-26 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, agent stats, oracle rate |
| `docs/guidelines/difficulty.md` | blocker #1 tier rules |
| `docs/guidelines/dockerfxile.md` | claim #6 canonical base |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate fix-pin-chunk-stream-rust/
Summary: 0 error(s), 3 warning(s), 2 info
```

Warnings: long_context subtype (not tagged), pip pin line-split false positive, docstring regex false positive.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 60.0% (3/5) | **worst model** |
| terminus-gpt5-5 | 80.0% (4/5) | at easy-tier upper bound |
| oracle | 100.0% (3/3) | `entire-report.txt:28` |
| nop | 0.0% (0/1) | `entire-report.txt:27` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% (Claude) |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) Rust task |
| 1 Instruction | ☑ | Terse but doc-delegated; not a High blocker |
| 2 Environment | ☑ | Canonical digest-pinned Rust base; tmux+asciinema; offline |
| 3 Oracle | ☑ | Derives fix via source patches; report 100% pass |
| 4 Verifiers | ☑ | Canonical reward block; behavior tests; monolithic but OK |
| 5 Metadata | ☑ | **Blocker:** difficulty mismatch |
| 6 Rubric | ☑ | Portal-only; N/A file checks |
| 7 Agent evidence | ☑ | 60% worst → medium; solvable per report |
| 8 Novelty & fairness | ☑ | Multi-bug Rust debug; fair at observed rates |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Environment, oracle, anti-cheat, and verifier design are solid — digest-pinned canonical Rust base, independent Python FNV oracle, and doc-driven export contract all check out. The only High blocker is difficulty metadata: `task.toml` declares `hard` but worst-model pass rate is Claude 60% (medium tier per Edition 2 rules). Update `difficulty` to `medium` or rebalance until worst-model ≤20%. Optional improvements: name `/app/data/replay_out/catalog.json` in `instruction.md` and split the monolithic pytest for clearer failure signals — neither is required for acceptance.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
