# Terminus Review Report: quic-ack-coalescer

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Exposing Hints/Answers, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Go debugging task with excellent verifier depth, digest-pinned offline env, and defensible hard calibration (GPT-5.5 20%). Four High blockers remain from the prior review: agent-visible walkthrough docs name buggy patterns with CORRECT vs WRONG fix guidance, the runbook ships a golden-output diff shortcut, `test_sample_harness_byte_matches_expected` trusts a mutable in-image golden file, and the platform rubric assigns negative scores to required correct behaviors while supplying only one genuine penalty.

**Insights (concise):**

- `coalescer_walkthrough.rst:87-157` is a per-bug debugging guide, not a normative spec — it names `FORWARD-default bug`, `right-exclusive coalesce`, and `factor falls through to 1000` with byte-level discriminators.
- `ack_operator_drills.md:27-29` tells agents to `diff` against `/app/quic_atrium/ack_workshop/golden_run.json`, the same bytes `test_sample_harness_byte_matches_expected` asserts.
- Primary-fixture digests are correctly baked in `tests/test_outputs.py:23-24`; only the sample-harness golden is agent-writable.
- Platform rubric is flat (correct for `number_of_milestones = 0`), not milestone-block format — but has invalid negative criteria.
- Automated `#14` pip warning is a false positive: `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are `==`-pinned in `environment/Dockerfile:13-15`.
- Oracle not run locally (Docker daemon unavailable); static review shows `solve.sh` copies `oracle_src`, builds, and executes — no hardcoded output echo.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Exposing Hints/Answers | #5, #17 | `coalescer_walkthrough.rst` contains worked CORRECT vs WRONG smoking-gun sections that name each scaffold bug pattern and the exact byte fields that flip | `environment/app/quic_atrium/coalescer_walkthrough.rst:84-85` (`FORWARD-default bug`); `:97-109` (CORRECT REVERSE vs WRONG FORWARD with basis_points); `:115-133` (`right-exclusive coalesce — the obvious read`); `:135-157` (`factor falls through to 1000 — agent forgot the per-tier map`) | Rewrite as normative requirement spec only; remove CORRECT/WRONG bug-fix walkthroughs and byte-discriminator guidance from the agent-visible tree |
| 2 | High | Exposing Hints/Answers | #17, #51 | Runbook hands agents the exact command to diff live output against shipped golden bytes | `environment/app/quic_atrium/ack_operator_drills.md:27-29` (`diff -u /app/quic_atrium/ack_workshop/golden_run.json /tmp/qack-sample/report.json`); `coalescer_walkthrough.rst:63` (byte-match golden) | Remove golden diff self-check from operator runbook; document sample-harness usage without exposing expected output bytes |
| 3 | High | Test Alignment/Coverage Issues, Exposing Hints/Answers | #51 | Verifier expected bytes for sample harness come from agent-writable path under `/app/quic_atrium` | `tests/test_outputs.py:539-550` (`expected_path = DOCS / "ack_workshop" / "golden_run.json"`); `environment/Dockerfile:28` (`COPY app/ /app/` includes golden); agent can overwrite golden to match buggy output and pass this assertion | Move expected sample output under `/tests/fixtures/` or embed expected digest/bytes in `test_outputs.py`; do not read ground truth from `/app` |
| 4 | High | Rubric | #32, #36 | Platform rubric penalizes correct required behavior; only one genuine negative remains | `entire-report.txt:433-435` (`Agent emits a self binding report digest…, -3`; `Agent leaves the input data tree byte identical…, -3`; only `Agent introduces nondeterminism…, -1` is a real penalty); `docs/guidelines/rubrics.md:33` (≥3 distinct negatives) | Reword digest emission and input immutability as `+N` positives; add ≥2 more distinct negatives (e.g., wrong digest, writing to `/app/ack_trove`, hardcoding golden output, bypassing compiled binary) |

*No other High-severity blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `coalescer_walkthrough.rst` exposes CORRECT vs WRONG bug-fix guidance (ChatGPT / prior reviewer / `entire-report.txt:413`) | **Agree** | `coalescer_walkthrough.rst:87-157` — three "Worked smoking-gun" sections with CORRECT/WRONG blocks naming scaffold bug patterns |
| 2 | `quic_critical_traps.md` self-describes as cheat sheet naming traps (ChatGPT / `entire-report.txt:415`) | **Partially agree** | `quic_critical_traps.md:59-60` (`This is the cheat sheet. It names the traps`); body is mostly normative spec duplicated across docs — problematic framing, not standalone blocker, but reinforces hinting concern with walkthrough |
| 3 | `ack_operator_drills.md` ships golden diff shortcut (prior reviewer / `entire-report.txt:417`) | **Agree** | `ack_operator_drills.md:27-29` |
| 4 | `test_sample_harness_byte_matches_expected` reads mutable in-image golden (ChatGPT / `entire-report.txt:419`) | **Agree** | `test_outputs.py:542-550`; golden at `environment/app/quic_atrium/ack_workshop/golden_run.json` copied to `/app` |
| 5 | Rubric assigns `-3` to correct digest emission and input immutability; only one real negative (ChatGPT / `entire-report.txt:421`) | **Agree** | `entire-report.txt:423-435` — lines 10-11 describe required pass behavior with negative scores; line 12 is sole genuine penalty |
| 6 | `docs/sample/expected_output.json` exposes verifier-checked output (prior reviewer comment `entire-report.txt:407`) | **Disagree** | No `expected_output.json` anywhere under `quic-ack-coalescer/`; actual leakage is `golden_run.json` (claims 3-4) |
| 7 | Non-milestone task uses milestone rubric format (user query) | **Disagree** | Platform rubric in `entire-report.txt:423-435` is a flat `Agent …, ±N` list with no `# Rubric 2+` headers; matches `docs/guidelines/rubrics.md:60` for non-milestone tasks |
| 8 | `#14` unpinned pip dependencies (automated validate warning) | **Disagree** | `environment/Dockerfile:13-15` pins `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` |
| 9 | `instruction.md` never mentions `QACK_DATA_DIR`/`QACK_OUT_DIR` — tests unpassable from spec alone (agent analysis `entire-report.txt:121`) | **Partially agree** | `instruction.md` omits env vars; `ack_operator_drills.md:27-28` documents them; scaffold `cmd/qack/main.go:11-15` already reads them; not a High blocker when instruction defers to `/app/quic_atrium` and docs cover behavior |
| 10 | Hamilton direction wording in `instruction.md` contradicts oracle (automated review `entire-report.txt:200-204`) | **Disagree** | `instruction.md:18-19` (`descending by default, ascending when urgent`) aligns with `quic_critical_traps.md:40-43` and oracle tests `test_hamilton_direction_default_reverse` / `test_hamilton_direction_flips_forward_when_urgent_on_alt` |
| 11 | Non-canonical Go base image (automated review `entire-report.txt:219-240`) | **Disagree as blocker** | `environment/Dockerfile:1` digest-pinned `golang:1.24-bookworm@sha256:1a6d44…`; justified exception when no canonical Go image exists |
| 12 | strictInt `42.0` edge untested (test quality `entire-report.txt:344-372`) | **Agree (Low only)** | `test_type_invalid_float_ack_ts_zeros_numerics` covers fractional float only; not revision-blocking per severity rules |
| 13 | LLMaJ `behavior_in_task_description` PASS (quality check `entire-report.txt:150`) | **Agree** | Instruction + `/app/quic_atrium` docs (`ack_record_layout.md`, `quic_critical_traps.md`) cover schema, windows, Hamilton, digest |
| 14 | Prior review "three blocking issues remain unaddressed" (reviewer feedback `entire-report.txt:411`) | **Agree** | Walkthrough, golden verifier path, and rubric negatives all still present in current artifacts — no remediation observed |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three short paragraphs | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense jargon-heavy shorthand reads like a compressed spec, not a conversational engineer prompt | `instruction.md:1-23` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No step-by-step in instruction | `instruction.md` |
| 5 | UNCHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Env walkthrough names HOW to fix each bug (CORRECT vs WRONG) | `coalescer_walkthrough.rst:87-157` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Clear goal: fix scaffold, build, emit report; defers rules to `/app/quic_atrium` | `instruction.md:1-3,22-23` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic QUIC trace coalescer debugging | task design |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | QUIC ACK coalescer domain; not verified against full corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/internal`, `/app/cmd/qack`, `/app/output/report.json`, `/app/quic_atrium`, `/app/ack_trove` | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:13-15` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | `@sha256:1a6d4452…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY app/ /app/` only | `environment/Dockerfile:28` |
| 17 | UNCHECK | Environment does not contain solution or ground truth answers | Golden output + bug-fix walkthrough + diff command in agent-visible tree | `golden_run.json`, `coalescer_walkthrough.rst:87-157`, `ack_operator_drills.md:29` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:13-15`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed — Docker daemon unavailable locally | oracle run attempted 2026-06-27 |
| 22 | CHECK | Oracle does not require internet or downloading packages | `GOPROXY=off`; solve.sh copies local oracle_src and `go build` | `solution/solve.sh`, `environment/Dockerfile:24` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Copies oracle Go source, builds binary, runs it | `solution/solve.sh:8-18` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block with default 0 | `tests/test.sh:4-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 0` / `echo 1` only | `tests/test.sh:6-19` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Instruction defers to `/app/quic_atrium`; docs cover schema, windows, Hamilton, digest, env vars | `instruction.md:22`, `ack_record_layout.md`, `ack_operator_drills.md` |
| 28 | CHECK | Tests check for correctness, not just format | Exact verdict counts, boundary events, Hamilton distribution, digest self-consistency | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Runs compiled binary; source checks limited to anti-cheat presence | `tests/test_outputs.py:55-90` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact bytes/counts required by normative JSON schema | `ack_record_layout.md` |
| 31 | CHECK | Tests have informative names or docstrings | All 47 `test_*` functions have docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Platform rubric has only 1 genuine negative after invalid lines | `entire-report.txt:433-435` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ∈ {+5,+3,+2,-3,-1} | `entire-report.txt:423-435` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | All lines match `Agent …, ±N` | `entire-report.txt:423-435` |
| 35 | CHECK | Rubric criteria are detailed and precise | Criteria name concrete behaviors (coalesce boundary, Hamilton, markers) | `entire-report.txt:423-435` |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Two lines describe correct pass behavior with negative scores | `entire-report.txt:433-434` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No `/tests/` or pytest references | `entire-report.txt:423-435` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata/instruction refs | `entire-report.txt:423-435` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP refs | `entire-report.txt:423-435` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml present | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both `anonymous` | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, languages, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `go`, `quic`, `data-processing` match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`; best-model 20% supports hard per calibration rules; worst-model 80% noted | `entire-report.txt:22-24`, `task.toml:6` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not a milestone task | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not a milestone task | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not a milestone task | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image | No `COPY tests/` in Dockerfile | `environment/Dockerfile` |
| 51 | UNCHECK | Solution or ground truth answers are not accessible in the environment | `golden_run.json` + walkthrough answer key in `/app/quic_atrium` | `ack_workshop/golden_run.json`, `coalescer_walkthrough.rst` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | `test_a1_input_data_digest` locks primary fixture SHA-256 | `test_outputs.py:23-24,112-114` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 80.0% — at threshold, not >80% | `entire-report.txt:22-24` |
| 55 | CHECK | Task is not too hard or unfair | Rules documented in quic_atrium; agents reach 70-87% partial pass; 1/10 timeout | `entire-report.txt:35,130-138` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 52, 53, 54, 55 |
| **UNCHECK** | 2, 5, 17, 21, 32, 36, 46, 47, 48, 49, 51 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build via `make build`, run `/app/bin/qack` | `test_b4_build_from_clean`, setup `_build` | covered | `test_outputs.py:55-66,223-228` |
| Output `/app/output/report.json` | all report tests | covered | `instruction.md:2`, `test_outputs.py:93-94` |
| Seven-verdict closed enum, all keys at zero | `test_c6_closed_enum_*` | covered | `test_outputs.py:246-257` |
| Right-inclusive coalesce / left-exclusive reorder | `test_window_boundary_*` | covered | `test_outputs.py:355-376` |
| CRITICAL tier halves coalesce window | `test_critical_tier_halves_coalesce_window` | covered | `test_outputs.py:383-390` |
| Anchor tiebreak: larger `packet_number` | `test_anchor_uses_larger_packet_number_on_tie` | covered | `test_outputs.py:342-353` |
| Strict-int rejection zeros numerics | `test_type_invalid_float_*`, `test_type_invalid_int_ack_eliciting_*` | covered | `test_outputs.py:392-415` |
| Hamilton REVERSE default / FORWARD when urgent | `test_hamilton_direction_default_reverse`, `test_hamilton_direction_flips_forward_when_urgent_on_alt` | covered | `test_outputs.py:467-504` |
| Self-binding digest with field blanked | `test_c12_self_binding_digest_self_consistent` | covered | `test_outputs.py:324-340` |
| Input tree immutability | `test_a3_input_immutability` | covered | `test_outputs.py:117-120` |
| Alt fixture via `QACK_DATA_DIR` | `test_a5_alt_fixture_produces_different_digest_and_direction` | covered | `ack_operator_drills.md:27-28`, `test_outputs.py:147-162` |
| Sample harness byte match | `test_sample_harness_byte_matches_expected` | covered (anti-cheat flaw) | `coalescer_walkthrough.rst:63`, `test_outputs.py:539-550` |
| `QACK_DATA_DIR` / `QACK_OUT_DIR` env support | `test_a4`, `test_a5`, `test_sample_harness_*` | covered | `cmd/qack/main.go:11-15`, `test_outputs.py:69-72` |
| Integer-valued float `42.0` → TYPE_INVALID | — | gap (Low) | Spec in `quic_critical_traps.md:18`; no fixture row with `42.0` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, spec alignment |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/app/quic_atrium/coalescer_walkthrough.rst` | Blockers 1-2, #5, #17, #51 |
| `environment/app/quic_atrium/ack_operator_drills.md` | Blockers 2-3, #51 |
| `environment/app/quic_atrium/quic_critical_traps.md` | Adjudication #2, spec alignment |
| `environment/app/quic_atrium/ack_record_layout.md` | #27, spec alignment |
| `environment/app/quic_atrium/ack_workshop/golden_run.json` | Blockers 2-3, #51 |
| `tests/test_outputs.py` | Blocker 3, #27-31, spec alignment |
| `tests/test.sh` | #24-26 |
| `solution/solve.sh` | #22-23 |
| `task.toml` | #42-45, #46-49 N/A |
| `entire-report.txt` | Agent stats, platform rubric, prior reviewer claims |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: quic-ack-coalescer ===
Summary: 0 error(s), 6 warning(s), 2 info
Task type detected: regular
```

Warnings include false-positive pip pin (#14) and `coalescer_run_notes.md` step-pattern hits (normative algorithm walk, not solve script).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Supports hard tier |
| terminus-claude-opus-4-8 | 80.0% (4/5) | 1 timeout |
| oracle | 100.0% (3/3) | Platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst model) | easy (at 80% boundary) |
| Declared difficulty | hard |
| Tier match (#45) | yes — defensible via best-model ≤20% rule |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `number_of_milestones = 0`; matches report |
| 1 Instruction | ☑ | Terse but complete with quic_atrium deferral |
| 2 Environment | ☑ | Digest-pinned Go image; tmux/asciinema; offline; hint leakage in docs |
| 3 Oracle | ☐ | Not executed (no Docker); static review passes |
| 4 Verifiers | ☑ | 47 tests, reward block canonical, no runtime installs |
| 5 Metadata | ☑ | `hard`, `go`, `data-processing` appropriate |
| 6 Rubric | ☑ | Flat non-milestone format correct; content invalid negatives |
| 7 LLMaJ & agent evidence | ☑ | Reconciled agent-analysis instruction gaps vs doc deferral |
| 8 Novelty & fairness | ☑ | Multi-bug scaffold; golden-file cheat path remains |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really interesting QUIC coalescer task — the digest-pinned Go environment, comprehensive verifier suite, and anti-cheat on the primary fixture are all in great shape, and the difficulty calibration looks right for GPT-5.5. The same four issues from the prior review are still present though. `coalescer_walkthrough.rst` is written as a bug-fix walkthrough with CORRECT vs WRONG examples that name the exact scaffold mistakes; please rewrite it as plain spec. The runbook also tells agents to diff against `golden_run.json`, and the verifier reads that same mutable file from `/app/quic_atrium` for the sample-harness test — move expected bytes to `/tests` or bake them into the verifier. Finally, the rubric still assigns `-3` to correct digest emission and input immutability, leaving only one real negative penalty; flip those to positives and add at least two more genuine negatives.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Exposing Hints/Answers | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 3 |
| Rubric | yes | 4 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
