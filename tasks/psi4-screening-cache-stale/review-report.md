# Terminus Review Report: psi4-screening-cache-stale

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed |
| **CHECK count** | 38 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Test Build Issues

**Decision (concise):** Strong C++ replay verifier and anti-cheat design, but three High gaps block acceptance: checkpoint seal 32-bit truncation is tested but not stated in `instruction.md`; `p7_inspect` stdout must use literal `screen=` / `swap=` / `delta=` tokens but instruction only says “screen-side and swap-side”; `tests/test.sh` omits canonical `mkdir -p /logs/verifier`. Canonical `gcc:13-bookworm` digest is approved; rubric format/points are fine for a non-milestone task.

**Insights (concise):**

- Both GPT-5.5 failures trace to unstated verifier contracts (uint64 seal widening; optional `screen-side=` rename) — not core debugging inability.
- LLMaJ `behavior_in_task_description` claim that `screen= swap= delta=` is in `instruction.md` is **false**; only `p7_contract.md` mentions counters in prose.
- `gcc:13-bookworm@sha256:930f2ebe…` matches the sanctioned digest in `docs/guidelines/dockerfxile.md` — not an Environment blocker.
- Platform rubric uses optional `# Rubric 1` header only (allowed for non-milestone); 23 positive pts ≤ 40 cap.
- `test_u19` uses `1e-4` vs instruction “one part per million” — Low only; still catches the seeded bug.
- Oracle not run locally (Docker daemon unavailable); static review of `solve.sh` + `oracle.patch` shows derive-via-rebuild workflow.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Checkpoint seal bit-width/truncation untested in spec but enforced in verifier | `instruction.md:5` says seal is “one integer combining the sum of WAL line checksum fields with hex mixing term BEEF…” — no `uint32_t`, 32-bit, or `& 0xFFFFFFFF`. `tests/test_outputs.py:108-113` masks each sum with `& 0xFFFFFFFF`; `test_u16_cross_scope_monotone` asserts seal equals that masked recompute. `entire-report.txt:67-68,80-84` documents both agent trials failing `test_u16` after widening seal to `uint64_t`. | State explicitly that seal arithmetic is 32-bit (`uint32_t`), with overflow masked to `0xFFFFFFFF` at each addition step (CRC sum and BEEF mix). |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #30, #55 | `p7_inspect` stdout token format tested but not specified | `instruction.md:3` says p7_inspect “reports screen-side and swap-side generation counters” — no `screen=`/`swap=`/`delta=` tokens. `tests/test_outputs.py:121-126` parses only `screen=`, `swap=`, `delta=` prefixes. `environment/src/engine.cpp:102-103` emits `screen=N swap=N delta=N`. `entire-report.txt:69` — agent renamed to `screen-side=` and failed `test_u17_sync_gen_alignment`. | Document exact stdout format: space-separated tokens `screen=<int> swap=<int> delta=<int>` (labels must be literal, not “screen-side”). |
| 3 | High | Test Build Issues | #24 | `test.sh` missing canonical `mkdir -p /logs/verifier` | `tests/test.sh:1-15` writes `/logs/verifier/reward.txt` but never creates `/logs/verifier`. Canonical pattern in `docs/guidelines/writing-tests.md:11` requires `mkdir -p /logs/verifier` before reward write. | Add `mkdir -p /logs/verifier` (and prefer `set -uo pipefail`) per canonical `test.sh` template. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Checkpoint seal rule under-specified; tests require 32-bit `& 0xFFFFFFFF` masking (ChatGPT / `entire-report.txt` agent analysis) | **Agree** | `instruction.md:5` vs `tests/test_outputs.py:108-113,327-328`; agent failure narrative `entire-report.txt:67-84` |
| 2 | Exact `p7_inspect` stdout format (`screen=`/`swap=`/`delta=`) not documented (ChatGPT) | **Agree** | `instruction.md:3` uses “screen-side and swap-side”; parser at `tests/test_outputs.py:121-126`; failure `entire-report.txt:69` |
| 3 | `gcc:13-bookworm` base needs canonical-status resolution (ChatGPT / Harbor review warning #1) | **Disagree** | `environment/Dockerfile:1` digest `sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` matches sanctioned `gcc:13-bookworm` in `docs/guidelines/dockerfxile.md:14` |
| 4 | Instruction readability — dense wall of text needs section headers (Harbor review warning #2; ChatGPT Low) | **Partially agree** | `instruction.md` is 3 paragraph blocks but ~600+ words with no headings; content is complete. Severity **Low/Medium** — not a standalone blocker given explicit spec gaps above |
| 5 | `test_u19` uses `1e-4` while instruction says 1 ppm (`entire-report.txt` test-quality review) | **Partially agree** | `instruction.md:5` “one part per million”; `tests/test_outputs.py:366` `<= 1e-4`. Looser but still catches seeded `PUBLISH_BEFORE_SWAP_CLOSE` offset; **Low** only |
| 6 | LLMaJ: instruction documents `p7_inspect` format `screen= swap= delta=` (`entire-report.txt:111`) | **Disagree** | `grep` on `instruction.md` finds no `screen=`/`swap=`/`delta=` tokens; only `p7_contract.md:35` mentions counters in prose |
| 7 | Non-milestone task uses milestone rubric format (`# Rubric 1` header) | **Disagree** (not a blocker) | `task.toml:9` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:66` allows `# Rubric 1` optional on non-milestone; only one block, no `# Rubric 2+` |
| 8 | Rubric positive points exceed cap | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 23/40 PASS |
| 9 | Instruction sufficiency FAIL — systematic spec gaps (`entire-report.txt:55,80-84`) | **Agree** | Aligns with blockers 1–2; agents reached 18–19/20 tests before seal/inspect regressions |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three paragraph blocks; structural limit met | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense continuous prose reads like a protocol spec, not a conversational engineer prompt | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes/tools, not click-by-click solve path | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (WAL/seal/trace contracts), not module-level HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input→output tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Seal bit-width and `p7_inspect` token format are tested but unstated | Blockers 1–2 |
| 8 | CHECK | Instruction is interesting | Realistic multi-module C++ replay/debugging scenario | Task content |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus in this audit | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/p7_trace.json`, etc. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No “psi4-screening-cache-stale” string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content (other than packages) | Build-time `curl` for `nlohmann/json` header only | `environment/Dockerfile:25-26` |
| 14 | CHECK | Python/pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18` |
| 15 | CHECK | Base image digest-pinned | `FROM gcc:13-bookworm@sha256:930f2ebe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | `COPY . /app/environment/` only | `environment/Dockerfile:22` |
| 17 | CHECK | Environment has no solution/ground truth | No `oracle.patch` or solution copied; buggy starter sources only | `environment/Dockerfile`, `solution/` separate |
| 18 | CHECK | No dangerous Docker capabilities | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in image; `test.sh` runs pytest only | `environment/Dockerfile:17-18`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Docker daemon unavailable; oracle not executed locally | Oracle run failed |
| 22 | CHECK | Oracle needs no internet at runtime | `solve.sh` patches, rebuilds, replays locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction (not hardcoded output) | Applies `oracle.patch`, `cmake --build`, `p7_run --cold`, `p7_emit` | `solution/solve.sh:12-20` |
| 24 | UNCHECK | test.sh reward.txt + mkdir + failure path | Missing `mkdir -p /logs/verifier` | `tests/test.sh` vs `writing-tests.md:11` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | Writes `0` or `1` to reward.txt | `tests/test.sh:11-15` |
| 27 | UNCHECK | Tests aligned with instructions | Tests enforce unstated seal masking and inspect token labels | Blockers 1–2 |
| 28 | CHECK | Tests check correctness | Reruns C++ pipeline; recomputes digest/seal/generations | `tests/test_outputs.py` |
| 29 | CHECK | Behavior tests, not implementation grep | No source-code pattern asserts | `tests/test_outputs.py` |
| 30 | UNCHECK | No brittle exact string matching | `inspect_counters()` requires exact `screen=`/`swap=`/`delta=` without instruction spec | `tests/test_outputs.py:121-126` |
| 31 | CHECK | Informative test docstrings | All 20 `test_u*` functions documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives in platform rubric | `entire-report.txt:330-333` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | All lines use allowed magnitudes | `entire-report.txt:319-333` |
| 34 | CHECK | Rubric lines start with Agent, comma, score | 14 Agent lines | `entire-report.txt:319-333` |
| 35 | CHECK | Rubric detailed and precise; positive cap OK | 23 positive pts ≤ 40 | `rubric-points` output |
| 36 | CHECK | Rubric positive phrasing for negatives | Bad behaviors stated as “Agent hand-writes…”, “Agent patches only…” | `entire-report.txt:330-333` |
| 37 | CHECK | Rubric no /tests/ references | No pytest/test path refs | `entire-report.txt:319-333` |
| 38 | CHECK | Rubric no task.toml/instruction.md refs | No metadata refs | `entire-report.txt:319-333` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None present | `entire-report.txt:319-333` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | Task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | Task tree |
| 42 | CHECK | author_name/email present | `anonymous` fields | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | version, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | C++ scientific replay; `languages = ["cpp","bash"]` | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform classified medium — informational only | `task.toml:6`, `entire-report.txt:16` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A — non-milestone | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A — non-milestone | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped | N/A — non-milestone | `task.toml:9` |
| 50 | CHECK | Tests not baked into image | No `COPY tests/` in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | Solution only under `/solution` at runtime mount | `environment/Dockerfile:22` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Fixture anchors in `/app/cases/seq`; verifier reruns compiled tools | `tests/test_outputs.py` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst-model GPT-5.5 60% ≤ 80% | `entire-report.txt:21-22` |
| 55 | UNCHECK | Not too hard/unfair | Unstated seal width and inspect labels caused systematic near-miss failures | `entire-report.txt:55-84`, blockers 1–2 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 2, 7, 9, 21, 24, 27, 30, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/p7_trace.json` via pipeline | all `test_u*` | covered | `instruction.md:3`, autouse fixture |
| Cold/warm s0 parity | `test_u00_cold_warm_parity` | covered | `instruction.md:3` |
| WAL `bust_w3` before `screen_ok` | `test_u03_delta_bust` | covered | `instruction.md:5` |
| WAL seq strictly increasing | `test_u04_chain_monotone`, `test_u15_s4_late_wrap` | covered | `instruction.md:5` |
| Checkpoint seal = CRC sum + BEEF per pair | `test_u16_cross_scope_monotone` | **gap** | Instruction omits 32-bit mask; test `seal_from_wal` uses `& 0xFFFFFFFF` |
| `p7_inspect` cross-authority counters | `test_u17_sync_gen_alignment` | **gap** | Instruction says “screen-side/swap-side”; test needs `screen=`/`swap=`/`delta=` |
| s0 block_rms narrow T7 tolerance (1 ppm) | `test_u19_narrow_block_rms` | partial | Instruction 1e-6 implied; test `<= 1e-4` |
| s3 deny code 9 | `test_u09_denied_case` | covered | `instruction.md:5` |
| s4 readopt clears denies | `test_u14_s4_readopt_after_deny` | covered | `instruction.md:5` |
| Partial replay s0–s3 excludes s4 | `test_u12_partial_seal_rejected` | covered | `instruction.md:5` |
| Invalid WAL checksum rejected | `test_u13_delayed_shift` | covered | `instruction.md:5` |
| body_digest sha256 canonical JSON | `test_u05_hash_parity` | covered | `instruction.md:3,5` |
| Fixture-grounded screen_gen | `test_u05_hash_parity` | covered | `instruction.md:5` |
| Repeat emit idempotent | `test_u06_repeat_stable` | covered | `instruction.md:5` |
| p7_recover idempotent | `test_u11_double_rebuild_stable` | covered | `instruction.md:5` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers 1–2, #7, #27, #55, spec table |
| `tests/test_outputs.py` | Blockers 1–2, #27, #30, spec table |
| `tests/test.sh` | Blocker 3, #24 |
| `environment/Dockerfile` | #13–#20, canonical base adjudication |
| `environment/src/engine.cpp` | Blocker 2 (canonical inspect format) |
| `environment/src/wal.cpp` | Blocker 1 (reference uint32 implementation) |
| `task.toml` | #45–#49, metadata |
| `solution/solve.sh` | #22, #23 |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |
| `docs/guidelines/writing-tests.md` | Blocker 3 |
| `docs/guidelines/rubrics.md` | Rubric format adjudication |
| `entire-report.txt` | Agent stats, LLMaJ, platform rubric, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate psi4-screening-cache-stale/
=== Terminus Validation: psi4-screening-cache-stale/ ===
Summary: 0 error(s), 0 warning(s), 1 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures on seal/inspect regressions per export |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) per export | Not re-run locally (Docker unavailable) |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | informational only — not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `psi4-screening-cache-stale`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Dense but complete except seal width + inspect format |
| 2 Environment | ☑ | Canonical gcc digest; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Static review OK; runtime oracle not executed |
| 4 Verifiers | ☑ | Strong behavioral tests; `test.sh` mkdir gap; two spec-test gaps |
| 5 Metadata | ☑ | Fields complete; tags at upper bound (6) — Low note only |
| 6 Rubric | ☑ | `# Rubric 1` only — valid non-milestone; 23 pts; 4 negatives |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL aligns with seal/inspect gaps |
| 8 Novelty & fairness | ☑ | Multi-module C++; cheating paths closed |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid C++ replay task — the verifier reruns the real pipeline, the multi-module bugs are well layered, and the Dockerfile base/digest setup looks good. Three things to fix before accept: (1) spell out in `instruction.md` that checkpoint seal math is 32-bit with masking to `0xFFFFFFFF` (both agents widened to uint64 and failed `test_u16`); (2) document the exact `p7_inspect` stdout as `screen=<n> swap=<n> delta=<n>` — one run failed after renaming labels to `screen-side=`; (3) add `mkdir -p /logs/verifier` to `tests/test.sh` per the canonical template. Optional polish: loosen instruction/test mismatch on `test_u19` tolerance (1 ppm vs 1e-4) and break up the dense instruction prose.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Test Build Issues | yes | 3 |
| Environment | no | — |
| Rubric | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
