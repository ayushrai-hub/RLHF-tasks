# Terminus Review Report: numba-parfors-combine-seam

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** Sophisticated Rust replay/WAL debugging task with digest-pinned offline env, end-to-end rebuild verifiers, and oracle pass. ChatGPT’s “undocumented invariant” claims are overstated: `r8_contract.md` covers s0 write-bump, s3 sync gap, action codes, bust order, and seal semantics; exact seal/slot checks live in agent-visible `/app/docs/r8_session.py` (baked in image). Non-milestone rubric uses optional `# Rubric 1` header only — correct format. No High blockers; optional doc polish only.

**Insights (concise):**

- Oracle 1.0 (`./scripts/terminus oracle`, 2026-06-29); worst-model 20% matches `hard`.
- Automated `#14`/`#20`/`#31` failures are false positives — hashed pip lockfile, pytest in image, all 19 tests have docstrings.
- `order_seal` bust path uses `+0xBEEF` in `r8_session.py:224` and `broken_order_seal()` at `:250-268`; contract describes distinct bust mix at `r8_contract.md:61-63`.
- `verify_digest_slot_keys()` at `r8_session.py:346-352`; broken `key_mat` hints `basename-only` in `d3/d3_b.rs:2-4`; solution uses digest in key (`solve.sh:41-47`).
- Platform instruction-sufficiency FAIL reflects agent ceiling, not missing normative docs; LLMaJ `behavior_in_task_description` PASS.
- Rubric: single `# Rubric 1` block, 32 positive pts, 6 negatives — valid non-milestone layout.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier enforces `order_seal` `+0xBEEF` bust formula not in instruction/contract (ChatGPT High) | **Partially agree** (doc polish only, not blocker) | Qualitative rule `r8_contract.md:61-63`; exact impl `environment/docs/r8_session.py:211-229`; agent-visible at `/app/docs`; `broken_order_seal()` `:250-268` shows wrong path; instruction cites contract for seal recompute `instruction.md:7` |
| 2 | `.slot` filenames must embed `i0.tab` digest — undocumented (ChatGPT / export §2) | **Partially agree** (doc polish only) | Test `verify_digest_slot_keys()` `r8_session.py:346-352`; not prose in contract; broken hint `d3/d3_b.rs:2-4` `basename-only`; oracle fix embeds digest `solution/solve.sh:41-47`; encode-store lineage `r8_contract.md:89-91` |
| 3 | s0 generation baseline/write-bump ambiguous (ChatGPT / export §2) | **Disagree** | Contract: write bump + emitted gen `r8_contract.md:15-16`; s0 preservation `r8_contract.md:75`; helper `shipped_gen()` `r8_session.py:174-175` (`WRITE_BUMP=1`); s0 fixture `gen=10` → expected 11 `cases/seq/s0/a0.arr:1` |
| 4 | 11/19 agent ceiling proves spec gap (export instruction sufficiency) | **Partially agree** | 7/9 trials at 11/19 `entire-report.txt:67-77`; failures trace to seal/slot Rust fixes agents didn’t complete; Opus 20% (1/5) shows solvable; helpers available in image |
| 5 | `live_gen > feed_gen` by ≥2 for s3 undocumented (export §4) | **Disagree** | `r8_contract.md:85` “live_gen two steps above feed_gen”; test `test_q10_abs_shift` `test_outputs.py:184-192` |
| 6 | WAL must stay at `wal/chain.wal` (export §4) | **Disagree** (agent error) | Path in helper `r8_session.py:89`, driver `driver_notes.md:24`, engine `internal/wal.rs:30-31`; trial `d2yqjxL` path change is agent mistake |
| 7 | `action_code` / `crl_epoch` / emit refusal undocumented (export §4) | **Disagree** | action_code 5/6/9 `r8_contract.md:79,87`; crl_epoch `r8_contract.md:103`; emit gate `r8_contract.md:105-107` |
| 8 | Non-canonical Rust base image is blocker (export review warning) | **Disagree** | Digest-pinned `environment/Dockerfile:1`; no Rust canonical image exists; justified for Rust toolchain |
| 9 | `broken_order_seal()` in agent docs weakens task (ChatGPT Low / Harbor warning) | **Agree** (non-blocking) | `r8_session.py:250-268`; debugging-task design choice; does not leak final trace JSON |
| 10 | Non-milestone task wrongly uses milestone rubric format (user ask) | **Disagree** | `task.toml:11` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:64` allows `# Rubric 1` optional, forbids `# Rubric 2+` only; export has single `# Rubric 1` block `entire-report.txt:332-348` |
| 11 | Automated validate `#14` unpinned pip | **Disagree** | `requirements.lock` uses `==` + hashes; installed `--require-hashes` `Dockerfile:25-27` |
| 12 | Automated validate `#20` pytest not in image | **Disagree** | venv + lockfile install `Dockerfile:25-27`; `test.sh` has no pip/apt `tests/test.sh:1-20` |
| 13 | Automated validate `#31` missing docstrings | **Disagree** | All 19 `test_q*` functions have docstrings e.g. `test_outputs.py:51,64,80` |
| 14 | Harbor REVIEW REPORT: READY TO USE | **Agree** | Structurally sound; warnings on base image and exposed helpers are non-blocking |
| 15 | Test-quality ROBUST | **Agree** | Rebuild-from-source, wipe state, pipeline re-run; no shortcut path |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 7 paragraphs, ~340 words — exceeds 3-paragraph / ~200-word styling target | `instruction.md`; `docs/guidelines/prompt-styling.md:7-8` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Incident-report tone, not synthetic spec dump | `instruction.md:3` |
| 3 | CHECK | No excessive markdown formatting | Title + prose only, no tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT/outcomes, not dev walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No detection guidance; contract refs only | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, tools, contract ref | `instruction.md:5-7` |
| 8 | CHECK | Instruction is interesting | Realistic Rust replay/WAL debugging | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/...`, etc. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Folder name absent | grep `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | — |
| 13 | CHECK | Dockerfile does not grab content from the web | Local COPY only; `cargo fetch` at build | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1` etc. in lockfile | `environment/requirements.lock:16-21`; `Dockerfile:25-27` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:9f841bbe...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY scoped to environment/ | `environment/Dockerfile:34-43` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken stubs + reference helpers, no final JSON | `environment/internal/wal.rs:122-124`; no `solution/` COPY |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in venv; test.sh pytest only | `Dockerfile:25-27`; `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Oracle mean 1.0, 1 trial | `./scripts/terminus oracle` 2026-06-29 |
| 22 | CHECK | Oracle does not require internet | cargo build + local pipeline | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Multi-file Rust fixes, recompile, pipeline | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir; failure path | Canonical block | `tests/test.sh:3-20` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`; `conftest.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0/1 only | `tests/test.sh:16-19` |
| 27 | CHECK | All tests aligned with instructions | Behaviors in instruction + `r8_contract.md` + `/app/docs` helpers | §5 alignment table |
| 28 | CHECK | Tests check for correctness | WAL seals, cross-view policy, digest, recovery | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation grep | CLI subprocess + JSON/WAL assertions | `tests/test_outputs.py`; `conftest.py:17-19` |
| 30 | CHECK | No brittle exact string matching | Structural/contract checks, not long literals | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | `test_q00`–`test_q18` with contract docstrings | `tests/test_outputs.py:50-286` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 negatives | `entire-report.txt:343-348` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores valid | `entire-report.txt:332-348` |
| 34 | CHECK | Each rubric criterion: Agent …, ±N | 16 Agent lines | `entire-report.txt:332-348` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific replay/WAL behaviors | rubric section |
| 36 | CHECK | Rubric uses positive language for negatives | Bad behavior scored `-N` | rubric section |
| 37 | CHECK | Rubric does not reference /tests/ | None | rubric section |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | None | rubric section |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | rubric section |
| 40 | CHECK | All required files present | Standard layout | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | task tree |
| 42 | CHECK | author_name and author_email present | anonymous fields | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, outputs, category | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | rust/bash, scientific-computing | `task.toml:7-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | hard; worst 20% | `entire-report.txt:20-26`; `task.toml:6` |
| 46 | UNCHECK | steps/ layout present | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | No solution COPY; helpers ≠ answers | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Verifier rebuilds + reruns pipeline | `conftest.py:17-19`; `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst 20% | `entire-report.txt:25-26` |
| 55 | CHECK | Task is not too hard or unfair | Normative docs + agent-visible helpers available | `environment/docs/`; §3 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/r8_trace.json` with epochs + body_digest | `test_q05_hash_parity` | covered | `instruction.md:7`; `test_outputs.py:116-128` |
| Cross-authority generation agreement (except deny) | `test_q05`, `test_q02` | covered | `instruction.md:9`; `r8_contract.md:69-75`; `verify_cross_view_policy` |
| Monotonic WAL seq s0–s4, no reset | `test_q04`, `test_q15` | covered | `instruction.md:11`; `r8_contract.md:53-55` |
| Bust before success s1+ | `test_q03`, `test_q04`, `test_q16` | covered | `instruction.md:11`; `r8_contract.md:31-33` |
| s1 sync aligned feed/live gen | `test_q17` | covered | `r8_contract.md:39-43`; `test_outputs.py:267-273` |
| s0 baseline survives later scenarios | `test_q00`, `test_q07` | covered | `r8_contract.md:75`; `verify_s0_generations` `r8_session.py:299-303` |
| Write bump on shipped gen | `test_q00`, `test_q05`, `test_q07` | covered | `r8_contract.md:15-16`; `shipped_gen()` `r8_session.py:174-175` |
| order_seal bust-completion mix | `test_q06`, `test_q11`, `test_q16` | covered | `r8_contract.md:61-63`; `order_seal_from_wal` `r8_session.py:211-229` |
| Encode-store slot keys include include digest | `test_q01`, `test_q03` | covered | `verify_digest_slot_keys` `r8_session.py:346-352`; lineage `r8_contract.md:89-91` |
| s3 deny action_code 9; live_gen ≥ feed_gen+2 | `test_q09`, `test_q10` | covered | `r8_contract.md:85-87`; `test_outputs.py:169-196` |
| s4 readopt action_code 6 | `test_q14` | covered | `r8_contract.md:87`; `test_outputs.py:240-250` |
| CRC invalid → emit refuses | `test_q13` | covered | `r8_contract.md:105-107`; `test_outputs.py:226-237` |
| R8 narrow band reduce/promote | `test_q18` | covered | `r8_contract.md:23-25`; `verify_r8_narrow_report` |
| Idempotent emit / recovery | `test_q06`, `test_q08` | covered | `r8_contract.md:93-99`; `test_outputs.py:131-166` |
| crl_epoch in last_metrics.json | `test_q01`, `test_q05`, `test_q09`, `test_q14` | covered | `r8_contract.md:101-103`; `verify_metrics_epoch` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27 |
| `environment/docs/r8_contract.md` | #27, #55, blockers adjudication |
| `environment/docs/r8_session.py` | #27, #55, seal/slot claims |
| `environment/docs/driver_notes.md` | WAL path, tool usage |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/d3/d3_b.rs` | slot-key claim |
| `environment/internal/wal.rs` | intentional order_seal/lineage bugs |
| `tests/test_outputs.py` | #27, #28, #31 |
| `tests/test.sh` | #20, #24 |
| `tests/conftest.py` | #20, #29 |
| `solution/solve.sh` | #21, #23 |
| `task.toml` | #43, #45, #46-49 |
| `entire-report.txt` | #32-39, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate numba-parfors-combine-seam/
Summary: 0 error(s), 20 warning(s), 2 info
```

Warnings on `#31` docstrings and `#14` pip display are false positives on manual audit.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 20.0% (1/5) | Solvable |
| terminus-gpt5-5 | 0.0% (0/5) | Hard |
| oracle | 100.0% (3/3 report; 1/1 local) | Deterministic |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `numba-parfors-combine-seam`; regular task; report matches |
| 1 Instruction | ☑ | 7 paragraphs (UNCHECK #1); contract delegated |
| 2 Environment | ☑ | Digest-pinned Rust base; tmux/asciinema; offline |
| 3 Oracle | ☑ | Pass 1.0 local |
| 4 Verifiers | ☑ | Canonical test.sh; rebuild each run; docstrings present |
| 5 Metadata | ☑ | hard, scientific-computing, rust/bash |
| 6 Rubric | ☑ | Single `# Rubric 1` — valid non-milestone format |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL overstated; behavior_in_tests PASS |
| 8 Novelty & fairness | ☑ | Multi-file bugs; anti-cheat via pipeline rebuild |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust replay task — the pinned offline env, end-to-end rebuild verifiers, and multi-module bug surface are all in great shape, and oracle passes cleanly. Agent pass rates look right for hard difficulty. The main optional polish: `r8_contract.md` could spell out the exact bust-completion `order_seal` mix (`+0xBEEF`) and encode-store slot-key naming so agents leaning only on the contract prose don’t have to discover those details in `/app/docs/r8_session.py`. That’s not blocking acceptance from my side. Instruction is a touch long (seven paragraphs); trimming to three problem paragraphs would align better with styling norms.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
