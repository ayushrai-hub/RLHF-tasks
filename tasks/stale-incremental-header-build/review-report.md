# Terminus Review Report: `stale-incremental-header-build`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors; pip-pin warning is false positive — `requirements.lock` uses `==` + hashes) |
| **Oracle** | pass (platform report: 100% / 3 runs; local harbor oracle not executed) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Milestone layout, offline C/CMake environment, digest-pinned Dockerfile, oracle design, platform rubric format, and matrix-law verifiers are strong. Three confirmed High test-coverage gaps block acceptance: M1 `slot_ring_audit.json` can be fabricated without reading `gen_ring.bin`; M2/M3 ring checks never validate the documented `(mtime XOR size) mod 2^32` live header tag; M2 never asserts quick rebuild compiles fewer units than pristine despite explicit instruction and `trace_contract.md` requirements.

**Insights (concise):**

- ChatGPT’s three High-severity test-alignment claims are **confirmed** with file evidence; LLMaJ `behavior_in_tests: pass` in `entire-report.txt` is contradicted by artifact review.
- Automated `#14` / `#20` failures are **false positives** — pytest is hash-pinned in `requirements.lock` and baked into the image via `/opt/verifier-venv`; milestone `test.sh` files do not install packages at runtime.
- Platform rubric (`entire-report.txt:723–767`) correctly uses milestone format (`# Rubric 1`–`# Rubric 3`) matching `number_of_milestones = 3`; this is **not** the scala-course-scheduler inverted-rubric problem.
- Worst-model pass rate is exactly **80.0%** (GPT-5.5) — at the easy-tier ceiling but not **>80%**; not a rejection blocker (#54 passes).
- M1 `expected_ring_audit()` at `trace_helpers.py:136–141` already implements the correct oracle but is never invoked by any test.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #28, #55 | M1 `slot_ring_audit.json` tests only check structural self-consistency; `stored_gen` / `live_gen` integers are never compared to `gen_ring.bin` or header stat. Fabricated JSON passes. | `test_m1.py:42–53`, `test_m1.py:66–74`; `expected_ring_audit()` defined at `trace_helpers.py:136–141` but unused; `read_ring_entries()` at `trace_helpers.py:94–118` parses binary correctly | In `test_chk_m1_a2` and/or `test_chk_m1_a4`, add `assert agent_doc == expected_ring_audit()` (or equivalent live-oracle comparison) |
| 2 | High | Test Alignment/Coverage Issues | #27, #28 | M2/M3 ring assertions only require homogeneous tags (`ring_gens_homogeneous`), not the live header formula from instructions and `trace_contract.md`. Any shared constant (e.g. `0`) satisfies tests. | `milestone_2/instruction.md:7`; `milestone_3/instruction.md:7`; `trace_contract.md:52–56`; `m2/trace_helpers.py:142–152`, `m3/trace_helpers.py:145–155` | Add `live_hdr_gen()` helper (as in M1) and assert every ring entry’s `stored_gen == (st_mtime XOR st_size) & 0xFFFFFFFF` |
| 3 | High | Test Alignment/Coverage Issues | #27, #28 | M2 instruction and `trace_contract.md` require quick rebuild to compile **fewer** units than pristine for the header-bump sequence; no test compares compile counts. | `milestone_2/instruction.md:3`; `trace_contract.md:67`; `m2/trace_helpers.py:109–119` (`header_bump_compiles_main` checks main.c compile + mtime only) | Count pristine-mode compiles vs fast-mode compiles for the same cap-bump sequence; assert `fast_count < pristine_count` |

*Not listed as blockers (verified non-issues):* `#14`/`#20` automated fails; non-canonical Debian base (justified for C/CMake-only agent workspace); M1 instruction length (#1 UNCHECK only); declared `hard` vs 80% easy (#45 informational); platform rubric milestone format is correct.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M1 `slot_ring_audit.json` checks too weak; `expected_ring_audit()` never used (ChatGPT High) | **Agree** | `test_m1.py:42–53` asserts `any_stale_gen`, `.bin` suffix, internal `gen_aligned` consistency only; `trace_helpers.py:136–141` oracle unused |
| 2 | M2/M3 do not enforce live ring-generation contract; M3 empty ring vacuously passes (ChatGPT High) | **Partially agree** | Homogeneity-only checks confirmed at `m2/trace_helpers.py:142–152`, `m3/trace_helpers.py:145–148`; empty-ring `return True` confirmed; `cap_rollback_manual_ring_stable` at `m3/trace_helpers.py:72–76` lacks non-empty assert (mitigated by `triple_incremental_stable` at `m3/trace_helpers.py:166–168`) — live-formula gap is the real blocker |
| 3 | M2 does not test quick-vs-pristine compile-count requirement (ChatGPT High) | **Agree** | `milestone_2/instruction.md:3`; `trace_contract.md:67`; `header_bump_compiles_main()` at `m2/trace_helpers.py:109–119` has no count comparison |
| 4 | LLMaJ `behavior_in_tests: pass` (`entire-report.txt:127`) | **Disagree** | Same gaps as claims 1–3; test-quality review in same file (`entire-report.txt:298–374`, `379–469`, `567–648`) flags all three milestones VULNERABLE |
| 5 | Automated `#1` instruction too long (847 words) | **Partially agree** | Sum spans three milestone files (`wc`: M1 338, M2 295, M3 214 words); per-milestone schema spec is dense but intentional — not a revision blocker |
| 6 | Automated `#14` unpinned pip / `#20` pytest missing from Dockerfile | **Disagree** | `requirements.lock:4–21` pins `pytest==8.4.1` etc. with hashes; `Dockerfile:25–28` installs via `--require-hashes`; `milestone_1/tests/test.sh:13–14` uses venv pytest, no runtime install |
| 7 | Non-canonical Debian base (`entire-report.txt:184–205`) | **Disagree (blocker)** | C/CMake task with Python only for verifier venv; digest-pinned `debian@sha256:4724…`; credible exception per report rationale |
| 8 | Platform rubric should use milestone format | **Agree — passes** | `task.toml:11` `number_of_milestones = 3`; rubric at `entire-report.txt:723–767` uses `# Rubric 1`–`# Rubric 3`, ≥3 distinct negatives per block, 18/38/25 positive pts (within 10–40 each) |
| 9 | M3 helper must not wipe artifact tree — untested | **Partially agree** | `milestone_3/instruction.md:3`; no direct mid-sequence tree assertion; compile-log skip checks partially guard — **Low**, not listed as blocker |
| 10 | M2 ring invalidation on re-render not directly tested | **Partially agree** | `milestone_2/instruction.md:7`; `header_bump_ring_recovered` lacks pre/post gen comparison — unlikely exploitable given cap label changes; **not a standalone blocker** |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | M1 alone ~338 words / 9 blocks; exceeds 3-paragraph cap per file | `steps/milestone_1/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering incident tone; contract refs not LLM boilerplate | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No ##/tables/code blocks in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes and artifacts, not patch steps | `steps/milestone_*/instruction.md` |
| 5 | CHECK | No hints or solving strategies | M2/M3 describe required behavior, not C edit locations | `steps/milestone_2/instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instructions | — |
| 7 | CHECK | Instruction is well specified | Paths, schemas, matrix law, ring formula specified | `steps/milestone_*/instruction.md`, `trace_contract.md` |
| 8 | CHECK | Instruction is interesting | Real incremental-build stale-object bug class | `task.toml:32–35` |
| 9 | CHECK | Instruction is unique | Stale-header + ring-generation offline C driver; not verified against full corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instructions | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | apt only; offline env | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Hash-pinned lock file | `requirements.lock:4–21` |
| 15 | CHECK | Base Docker image is pinned by digest | `debian@sha256:4724…` | `Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY scoped to environment | `Dockerfile:25–31` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are contracts; fix frontier guarded in M1 tests | `environment/docs/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv pytest in Dockerfile; test.sh runs pytest only | `Dockerfile:25–28`, `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform: oracle 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Offline shell + local tools | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Derives JSON from trace_host, ring binary, compile log | `steps/milestone_1/solution/solve1.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical block in each milestone test.sh | `steps/milestone_1/tests/test.sh:5–20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | milestone `test.sh` files |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward pattern | milestone `test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | Ring audit, live-gen formula, compile-count gaps | blockers 1–3 |
| 28 | UNCHECK | Tests check for correctness, not just format | M1 ring audit is structural/format-only | `test_m1.py:42–53` |
| 29 | CHECK | Tests verify behavior, not implementation | Live bld_host/trace_host execution; no source grep | `test_m*.py`, `trace_helpers.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Digest/matrix/oracle equality checks appropriate | `trace_helpers.py` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_chk_m*_a*` have docstrings | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | ≥4 negatives per rubric block on platform | `entire-report.txt:731–767` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All lines use ±1/2/3/5 | `entire-report.txt:723–767` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format compliant | `entire-report.txt:723–767` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific trace/ring/build checks | `entire-report.txt:723–767` |
| 36 | CHECK | Rubric criteria use positive language | Bad behavior uses negative scores | `entire-report.txt:731–767` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:723–767` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:723–767` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:723–767` |
| 40 | CHECK | All required files present | Milestone layout: Dockerfile, steps/, task.toml | `task.toml`, `steps/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | task folder |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | version, category, steps, env | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | C/cmake/build-and-dependency-management | `task.toml:7–12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 80% → easy tier | `task.toml:6`, `entire-report.txt:25–26` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `task.toml:11`, `steps/` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | solve1.sh, solve2.sh, solve3.sh | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | TestMilestoneN classes; M1 no repair checks | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:15–16` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ excluded from image | `environment/.dockerignore:15` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | M1 fix-frontier SHA-256; live trace regeneration | `m1/trace_helpers.py:22–44`, `run_trace()` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 80.0% — not >80% | `entire-report.txt:25–26` |
| 55 | CHECK | Task is not too hard or unfair | Spec complete; M1 failures are agent output-limit issues | `entire-report.txt:57–100` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 27, 28, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: `quick_full_delta.json` matches live trace | `test_chk_m1_a0`, `test_chk_m1_a1` | covered | `test_m1.py:25–40`; `expected_quick_full_delta()` |
| M1: `journal_surfaces.json` from live compile log | `test_chk_m1_a3` | covered | `test_m1.py:55–64`; `expected_journal_surfaces()` |
| M1: `rebuild_trace.json` matches live trace_host | `run_trace()` in all M1 tests using trace | covered | `m1/trace_helpers.py:47–61` |
| M1: inspect `gen_ring.bin` against live header generation | `test_chk_m1_a2`, `test_chk_m1_a4` | **gap** | Structural checks only; `expected_ring_audit()` unused |
| M1: stale main.o vs fresh header mtime | `test_chk_m1_a5` | covered | `test_m1.py:76–82` |
| M2: matrix law header_bump / cap_rollback | `test_chk_m2_a0`, `test_chk_m2_a2` | covered | `test_m2.py:16–29` |
| M2: unchanged_control app_v1 matches header_bump | `test_chk_m2_a1` | covered | `test_m2.py:21–24` |
| M2: three incremental-only passes compile nothing | `test_chk_m2_a3` | covered | `test_m2.py:31–33` |
| M2: quick rebuild compiles **fewer** units than pristine | — | **gap** | `milestone_2/instruction.md:3`; no count test |
| M2: main.c recompiled; main.o ≥ header mtime | `test_chk_m2_a5` | covered | `test_m2.py:39–41` |
| M2: ring tags follow live header formula | `test_chk_m2_a4` | **gap** | Homogeneity only at `m2/trace_helpers.py:142–160` |
| M3: same_second_seq matrix law | `test_chk_m3_a0` | covered | `test_m3.py:18–22` |
| M3: ring entries carry live header tag | `test_chk_m3_a3`, `test_chk_m3_a5` | **gap** | Homogeneity only at `m3/trace_helpers.py:145–169` |
| M3: trace byte stability / incremental reuse | `test_chk_m3_a1`, `test_chk_m3_a4` | covered | `test_m3.py:24–43` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/tests/test_m1.py` | Blocker 1, claims 1, #27, #28 |
| `steps/milestone_1/tests/trace_helpers.py` | Blocker 1, `expected_ring_audit()` |
| `steps/milestone_2/tests/trace_helpers.py` | Blockers 2–3, claims 2–3 |
| `steps/milestone_3/tests/trace_helpers.py` | Blocker 2, claim 2 |
| `steps/milestone_2/instruction.md` | Blocker 3, spec alignment |
| `environment/docs/trace_contract.md` | Blockers 2–3, ring formula |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | #14 |
| `task.toml` | Milestone metadata, rubric format |
| `entire-report.txt` | Agent stats, platform rubric, LLMaJ adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate stale-incremental-header-build/
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: milestone
Warning: pip pin false positive (requirements.lock uses == + hashes)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | At easy-tier ceiling |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Medium tier |
| oracle | 100.0% (3/3) | Platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (at 80% boundary) |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only, not a revision blocker |

M1 systematically failed in agent trials due to output/token limits (`entire-report.txt:74–80`), not spec gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone C/CMake task; report matches folder |
| 1 Instruction | ☑ | Well-specified; M1 long but schema-dense |
| 2 Environment | ☑ | Digest-pinned Debian; tmux/asciinema; offline |
| 3 Oracle | ☑ | Derives outputs; platform 100% pass |
| 4 Verifiers | ☑ | Three real test-coverage blockers confirmed |
| 5 Metadata | ☑ | `number_of_milestones=3`; tags match |
| 6 Rubric | ☑ | Platform rubric uses correct milestone format |
| 7 LLMaJ & agent evidence | ☑ | Contradicted LLMaJ behavior_in_tests on ring/compile gaps |
| 8 Novelty & fairness | ☑ | Strong anti-cheat; M1 overflow is agent-side |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the three-milestone progression, offline C/CMake environment, digest-pinned image, and live trace/matrix-law verifiers are all in great shape, and the platform rubric correctly uses per-milestone blocks. Three test gaps need fixing before accept: (1) wire `expected_ring_audit()` into M1 so `slot_ring_audit.json` is compared against a live parse of `gen_ring.bin`, not just self-consistent fake integers; (2) assert ring entries match the documented live header tag `(mtime XOR size) mod 2^32` in M2/M3, not just mutual homogeneity; (3) add a compile-count comparison proving the header-bump quick path compiles fewer units than pristine, as your M2 instruction already requires.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 2, 3 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
| Rubric | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
