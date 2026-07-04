# Terminus Review Report: `deterministic-nbody-replay.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | not executed |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Test Dependency Location, Exposing Hints/Answers, Test Build Issues, Rubric, Test Alignment/Coverage Issues

**Decision (concise):** Strong milestone N-body task with digest-pinned GCC image, solid byte-level verifiers, and correct `# Rubric 1/2/3` milestone rubric layout. **Four real blockers:** runtime `pip3 install` in all milestone `test.sh` files (validation fails), starter C++ source leaks exact bug/fix hints, M3 verifier never rebuilds `/app/build/nbody` (unlike M1/M2), and platform rubric lines omit required `Agent …, ±N` format. Activation-step boundary wording is ambiguous vs tests and should be tightened (medium).

**Insights (concise):**

- `./scripts/terminus validate` fails on all three milestone `test.sh` files for `pip3 install` — confirmed blocker, not stylistic.
- `scenario.cpp`, `force_kernel.cpp`, and `main.cpp` contain explicit `BUG` comments naming omitted fixes (`canonical_index = i`, pointer comparator, `compute_forces()` misuse) — High **Exposing Hints/Answers**.
- M3 `test_m3.py` invokes `/app/build/nbody` with no cmake/build step; M1/M2 each have `test_m*_binary_*builds` — verifier can grade a stale binary after agent edits.
- Platform rubric uses correct milestone headers (`# Rubric 1/2/3`) and positive sums ≤40 per block (20/26/22); format violations are missing `Agent` prefix and inverted negative wording — not wrong non-milestone layout.
- Worst-model pass rate 60% (GPT-5.5); not too easy. Declared `hard` vs platform `medium` is informational only.
- Non-canonical GCC base is digest-pinned and justified for C++ toolchain — **not** a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Dependency Location | #20 | All milestone `test.sh` run `pip3 install` at verifier time | `steps/milestone_1/tests/test.sh:4`, `steps/milestone_2/tests/test.sh:4`, `steps/milestone_3/tests/test.sh:4`; validate output | `pip3 install pytest==9.1.1 pytest-json-ctrf==0.3.5` in `environment/Dockerfile`; remove pip line from all `test.sh` |
| 2 | High | Exposing Hints/Answers | #17 | Starter source names exact bugs and intended fixes | `environment/src/scenario.cpp:72-76`, `environment/src/force_kernel.cpp:7-11`, `environment/src/main.cpp:50-55` | Remove or rewrite `BUG` / fix-hint comments as neutral production comments |
| 3 | High | Test Build Issues | #28 | M3 verifier never rebuilds binary before tests | `steps/milestone_3/tests/test_m3.py:8` uses `NBODY = "/app/build/nbody"`; no build test (contrast `test_m1.py:26-48`, `test_m2.py:50-72`) | Add `test_m3_binary_still_builds` or shared build fixture so M3 always tests current source |
| 4 | Medium | Rubric | #34, #36 | Platform rubric lines lack `Agent` prefix; negatives describe desired state | `entire-report.txt:640-672` — e.g. `canonical_index is properly initialized…, +3`; `The physics constants… are not modified…, -5` | Prefix every line with `Agent …, ±N`; negatives penalize bad actions (e.g. `Agent modifies physics constants or output format, -5`) |
| 5 | Medium | Test Alignment/Coverage Issues | #27, #55 | “Frozen until activation_step” ambiguous vs test expectation | `steps/milestone_3/instruction.md:11`, `format.md:41`, `test_m3.py:225-239` checks frozen at step 199, motion at step 200; `entire-report.txt:99-103` | State explicitly: position record **at** `activation_step` must differ from step `activation_step - 1` |

*Five blockers — four High/Medium that must be fixed before accept; item 5 prevents unfair M3 fencepost failures.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier installs pytest in `test.sh` (ChatGPT / Harbor report / reviewer feedback) | **Agree** | `steps/milestone_*/tests/test.sh:4`; `environment/Dockerfile:14-17` only `pip3 download` to `/opt/test-deps/` |
| 2 | M3 can use stale/missing binary (ChatGPT / reviewer feedback) | **Agree** | `test_m3.py:8` — no build step; M1/M2 have explicit rebuild tests |
| 3 | Starter source exposes solution guidance via BUG comments (ChatGPT / reviewer feedback) | **Agree** | `scenario.cpp:72-76`, `force_kernel.cpp:7-11`, `main.cpp:50-55` |
| 4 | M3 activation boundary ambiguous; needs explicit step-200 motion rule (ChatGPT / entire-report instruction sufficiency) | **Agree** | Instruction + `format.md:41` say “until activation_step”; `test_m3.py:235-239` requires change at `ACTIVATION_STEP` (200) |
| 5 | M3 needs independent known-good trajectory check (ChatGPT) | **Partially agree** | `test_m3_body2_frozen_then_active` is independent ground-truth for activation; extend vs full-run is self-consistency. Strengthening optional, not a sole blocker |
| 6 | M1 lacks independent physics correctness (ChatGPT) | **Partially agree** | `test_m1.py:149-188` spot-checks velocity at step 500 only; byte-identical double-run + exact record count is strong. Quality gap, not Revise-alone |
| 7 | Rubric needs `Agent` prefix and negative wording cleanup (ChatGPT / reviewer feedback) | **Agree** | `entire-report.txt:640-672` — no line starts with `Agent` |
| 8 | Non-milestone task wrongly in milestone rubric format (user query) | **Disagree** | `task.toml:9` `number_of_milestones = 3`; rubric has `# Rubric 1/2/3` blocks — **correct** milestone format |
| 9 | Rubric positive total >40 (rules) | **Disagree** | Block sums: 20 + 26 + 22 = 68 total across blocks; each block ≤40 ✓ |
| 10 | Non-canonical Docker base is blocker (Harbor report warning) | **Disagree** | `environment/Dockerfile:1` digest-pinned `gcc:13-bookworm@sha256:930f2e…`; justified for C++ cmake toolchain |
| 11 | M2 should assert MXCSR == 0x9FC0 explicitly (test quality / ChatGPT Low) | **Partially agree** | `test_m2.py:44` parses `mxcsr` but never asserts value; `test_m2_ftz_denormal_segment` exercises functional effect. Low polish only |
| 12 | M3 step-0 extend test only checks liveness (test quality) | **Partially agree** | `test_m3.py:189-202` — size + first step counter only; medium coverage gap, not standalone blocker |
| 13 | M3 self-consistency cannot catch wrong physics (test quality) | **Partially agree** | True for extend/full compare; mitigated by `test_m3_body2_frozen_then_active` and M1/M2 regression |
| 14 | Instruction too long / step-by-step (#1, #4 automated) | **Disagree** | Each milestone instruction is 2–4 short paragraphs (~130–150 words); aggregate 443 words across 3 milestones is expected. “Build then run” in M1 is minimal necessary context |
| 15 | LLMaJ `behavior_in_*` all pass | **Agree** (with caveats) | `entire-report.txt:127-136` — cross-check confirms most; exceptions are pip-in-test.sh (#20) and env hints (#17) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction ≤3 paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as engineering brief, not synthetic spec | milestone instructions |
| 3 | CHECK | No excessive markdown | No ##/tables in instructions | milestone instructions |
| 4 | CHECK | No step-by-step solve script | Commands are required outputs, not debug walkthrough | M2/M3 command blocks |
| 5 | CHECK | No hints in instruction | WHAT-focused; points to `format.md` | milestone instructions |
| 6 | CHECK | No design-doc tables | None in instructions | — |
| 7 | CHECK | Well specified | Paths, filenames, byte-identical requirements clear | milestone instructions + `format.md` |
| 8 | CHECK | Interesting | Real FP determinism / checkpoint / activation problem | task content |
| 9 | CHECK | Unique | Distinctive multi-milestone n-body replay | — |
| 10 | CHECK | Absolute paths | All `/app/...` paths | milestone instructions |
| 11 | CHECK | Task name not in instruction | No task slug in text | — |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No runtime web fetch in env | Local scenarios only | `environment/` |
| 14 | CHECK | Pinned pip versions | `pytest==9.1.1`, `pytest-json-ctrf==0.3.5` in Dockerfile | `environment/Dockerfile:14-17` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:930f2ebe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context scoped | COPY only under `environment/` | `environment/Dockerfile:22-24` |
| 17 | UNCHECK | No solution/answer leakage in env | BUG comments name exact fixes | `scenario.cpp:72-76`, `force_kernel.cpp:7-11`, `main.cpp:50-55` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose | — |
| 20 | UNCHECK | Verifier deps in image; no runtime install | `pip3 install` in all milestone test.sh | `steps/milestone_*/tests/test.sh:4` |
| 21 | UNCHECK | Oracle passes | Not executed this review | — |
| 22 | CHECK | Oracle offline | solve scripts patch + cmake locally | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle reflective | Patches source, rebuilds, runs binary | `solve1.sh` pattern |
| 24 | CHECK | reward.txt canonical block | Present all milestones | `test.sh` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | tests |
| 26 | CHECK | Binary 0/1 reward | echo 0/1 pattern | `test.sh` |
| 27 | UNCHECK | Tests aligned with instruction | Activation boundary ambiguous | `instruction.md:11` vs `test_m3.py:235-239` |
| 28 | CHECK | Tests check correctness | Byte identity, CRC, frozen-body checks | `test_m*.py` |
| 29 | CHECK | Behavior not implementation grep | Runtime binary output only | tests |
| 30 | CHECK | Byte matching justified | Spec mandates byte-identical dumps | `format.md`, tests |
| 31 | CHECK | Informative test docstrings | All `test_*` documented | `test_m1.py`–`test_m3.py` |
| 32 | CHECK | ≥3 negative rubric criteria | Three negatives across blocks | `entire-report.txt:649,661,672` |
| 33 | CHECK | Valid rubric scores | Only ±1,2,3,5 used | `entire-report.txt:640-672` |
| 34 | UNCHECK | `Agent …, ±N` format | No line starts with `Agent` | `entire-report.txt:640-672` |
| 35 | CHECK | Detailed rubric criteria | Specific behaviors listed | platform rubric |
| 36 | UNCHECK | Positive language / proper negatives | Negatives state desired guarantees | e.g. `…are not modified…, -5` |
| 37 | CHECK | Rubric no /tests/ refs | None | platform rubric |
| 38 | CHECK | Rubric no instruction.md refs | None | platform rubric |
| 39 | CHECK | Rubric no oracle/NOP refs | None | platform rubric |
| 40 | CHECK | Required files present | Milestone layout complete | `task.toml`, `steps/`, `environment/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | task folder |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags/languages match | C++, scientific-computing | `task.toml` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform medium — not a blocker | `task.toml:6`, `entire-report.txt:23` |
| 46 | CHECK | steps/ milestone layout | 3 milestones with per-step files | `steps/milestone_*` |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | Present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | Each file tests only its milestone | `test_m1.py`–`test_m3.py` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No pre-baked ground-truth outputs | Scenarios generated at build; no answer trajectories in image | `gen_scenarios.py`, Dockerfile |
| 52 | CHECK | Input not trivially cheatable | Dynamic binary output required | test design |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | — |
| 54 | CHECK | Not too easy | Worst model 60% ≤80% | `entire-report.txt:28-29` |
| 55 | UNCHECK | Not unfair | Activation fencepost ambiguity caused agent failure | `entire-report.txt:84-85,99-103` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 17, 20, 21, 27, 34, 36, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: two runs byte-identical | `test_m1_two_runs_byte_identical` | covered | `test_m1.py:50-93` |
| M1: record count steps 0–N inclusive | `test_m1_dump_format_correctness` | covered | `test_m1.py:95-122` |
| M1: unsigned header parsing | `test_m1_header_signedness` | partial | reads file not runtime parser; size test间接 covers body_count |
| M1: nonzero velocities throughout | `test_m1_redherring_energy_unmodified` | partial | step 500 spot check only |
| M2: checkpoint byte-stable | `test_m2_checkpoint_byte_stable_across_runs` | covered | `test_m2.py` |
| M2: CRC32 canonical payload | `test_m2_checkpoint_crc_matches` | covered | `test_m2.py` |
| M2: resumed tail byte-identical | `test_m2_resume_tail_byte_identical` | covered | `test_m2.py` |
| M2: MXCSR/FTZ functional effect | `test_m2_ftz_denormal_segment` | covered | `test_m2.py` |
| M3: extend matches full run tail | `test_m3_extended_matches_reference` | covered | `test_m3.py:109-153` |
| M3: body frozen until activation | `test_m3_body2_frozen_then_active` | gap | frozen through step 199; motion at 200 — instruction “until” ambiguous |
| M3: step-0 extend no wraparound | `test_m3_step_gap_no_wraparound` | partial | liveness/size only, not byte compare |
| M3: rebuild before grade | — | gap | no M3 build test |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `environment/Dockerfile` | #14, #15, #20, blocker 1 |
| `steps/milestone_*/tests/test.sh` | #20, blocker 1 |
| `environment/src/scenario.cpp` | #17, blocker 2 |
| `environment/src/force_kernel.cpp` | #17, blocker 2 |
| `environment/src/main.cpp` | #17, blocker 2 |
| `steps/milestone_1/tests/test_m1.py` | blocker 3 contrast (build test) |
| `steps/milestone_2/tests/test_m2.py` | blocker 3 contrast |
| `steps/milestone_3/tests/test_m3.py` | blockers 3, 5 |
| `steps/milestone_3/instruction.md` | blocker 5 |
| `environment/data/spec/format.md` | blocker 5 |
| `entire-report.txt` | #32-39 rubric, agent stats, adjudication |
| `task.toml` | #45, #46, milestone layout |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: deterministic-nbody-replay./ ===
ERROR: test.sh [steps/milestone_1/tests/test.sh]: Runtime network install not allowed: pip3\s+install
ERROR: test.sh [steps/milestone_2/tests/test.sh]: Runtime network install not allowed: pip3\s+install
ERROR: test.sh [steps/milestone_3/tests/test.sh]: Runtime network install not allowed: pip3\s+install
Summary: 3 error(s), 0 warning(s), 0 info
Task type detected: milestone
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | |
| oracle | 100.0% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

M3 universal agent failure (0/3 trials) with M1/M2 mostly passing — consistent with hard M3 integrator semantics, not environment unreliability alone.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone C++ scientific-computing task; matches `entire-report.txt` |
| 1 Instruction | ☑ | Concise per milestone; activation boundary gap |
| 2 Environment | ☑ | Digest-pinned GCC; tmux/asciinema; hints in source |
| 3 Oracle | ☐ | Not executed; static review of solve scripts OK |
| 4 Verifiers | ☑ | pip install blocker; M3 build gap |
| 5 Metadata | ☑ | `task.toml` complete |
| 6 Rubric | ☑ | Milestone blocks correct; format violations |
| 7 LLMaJ & agents | ☑ | Stats parsed; instruction sufficiency fail on activation |
| 8 Novelty & fairness | ☑ | Strong anti-cheat; fencepost ambiguity |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the three-milestone progression, byte-level verifiers, and `format.md` contract are excellent, and difficulty calibration looks about right. A few fixes before accept: move pytest into the Dockerfile and drop the `pip3 install` lines from every milestone `test.sh` (validation currently fails on this); strip the explicit `BUG` comments in the starter C++ that name the exact fixes; add an M3 rebuild step like M1/M2 so the verifier always tests the binary the agent just built; tighten M3 wording so it’s explicit that body 2’s position record **at** `activation_step` must show motion (not still frozen through that record); and reformat the platform rubric so every line starts with `Agent …, ±N` with negatives phrased as penalties for wrong actions.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Dependency Location | yes | 1 |
| Exposing Hints/Answers | yes | 2 |
| Test Build Issues | yes | 3 |
| Rubric | yes | 4 |
| Test Alignment/Coverage Issues | yes | 5 |
| Environment | no | — (non-canonical base justified; digest OK) |
| Task Difficulty | no | — (60% worst model) |
| Metadata Issues | no | — (declared vs platform difficulty not blocking) |
| Milestones | no | — (layout correct) |
