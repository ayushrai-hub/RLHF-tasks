# Terminus Review Report: `grid-message-20260623-194717`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (per `entire-report.txt`; not executed locally — Harbor config error) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Test Build Issues

**Decision (concise):** Revise. Digest-pinned Zephyr/Ubuntu image, offline toolchain setup, tests/solution exclusion, portal rubrics, and 0% agent pass rate support declared `hard` difficulty. Blockers are real: M1 `grid_pll_update()` return-unit ambiguity (9/10 agent failures on plausible interpretation), non-canonical milestone `test.sh` shape (missing `$PWD` guard and prewrite-0), and M3 `test_no_message_format` omitting required `FRAMES_PROCESSED` output. Strengthen M3 word coverage and clarify M3 integration details as secondary fixes.

**Insights (concise):**

- `task.toml` validate error `number_of_milestones (3) != [[steps]] count (4)` is a **false positive**: comment on line 12 contains the literal `[[steps]]`, inflating the count.
- ChatGPT’s M3 “ORACLE is always selected” claim is **correct** (`random.seed(42)` → `ORACLE`), but severity is overstated: agents cannot read `/tests/`; this is weak coverage, not a direct cheating vector.
- `entire-report.txt` overall “READY TO USE” assessment **contradicts** its own LLMaJ `behavior_in_task_description` / `behavior_in_tests` failures and the M1 agent-failure analysis — artifacts win.
- Portal rubrics in `entire-report.txt` satisfy format rules (6 negatives total, `Agent …, ±N` lines); rubric line-wrapping rebuttal is valid.
- Automated #1 “concise” fail counts **combined** milestone instructions (9 blocks / ~697 words); each per-milestone file is individually borderline acceptable.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | M1 return contract ambiguous: instruction says agent “provide an update to the VCO frequency” while harness multiplies return value by `SAMPLES_PER_CYCLE` (2048) to set sampling rate — implying carrier Hz, not sample rate. Agents returning `f × 2048` is reasonable; 9/10 runs failed M1. | `steps/milestone_1/instruction.md:5`; `steps/milestone_1/tests/test_m1_runner.c:51-52`; `entire-report.txt:44-56` | Add explicit wording: “Return the estimated carrier frequency in Hz (~58–62); do not multiply by `SAMPLES_PER_CYCLE`.” |
| 2 | Medium | Test Build Issues | #24 | All three milestone `test.sh` files omit canonical `$PWD = /` guard and immediate `echo 0 > /logs/verifier/reward.txt` prewrite before pytest. Reward block, `--ctrf`, and `RC=$?` capture are present. | `steps/milestone_1/tests/test.sh:1-20`; `docs/guidelines/writing-tests.md:11-17`; `entire-report.txt:1` | Add PWD guard + prewrite-0 after `mkdir -p /logs/verifier` in each `steps/milestone_*/tests/test.sh`. |
| 3 | Medium | Test Alignment/Coverage Issues | #27, #28 | M3 `test_no_message_format` checks only `NO message found\n`; instruction requires `FRAMES_PROCESSED: %d` on the first line in all cases. Agent can skip frame counting on empty path and pass. | `steps/milestone_3/instruction.md:3-5`; `steps/milestone_3/tests/test_m3.py:112-114` | Assert `re.search(r"FRAMES_PROCESSED:\s*(\d+)", run_res.stdout)` in `test_no_message_format`. |
| 4 | Medium | Test Alignment/Coverage Issues | #27 | M3 positive path tests exactly one secret word (`random.seed(42)` → `ORACLE`); no variation in length/case across `WORD_BANK`. Decoder could overfit one word pattern. | `steps/milestone_3/tests/test_m3.py:26-27`; `WORD_BANK` lines 7-18 | Parameterize 2–3 deterministic words (varying length/case) or loop rebuild with `-DTEST_SECRET_WORD=…`. |
| 5 | Low | Instruction Styling | #1 | Combined milestone instructions = 9 paragraph blocks (~697 words), exceeding automated >8-block threshold. Each file individually is ~2–3 paragraphs. | `steps/milestone_*/instruction.md`; `scripts/review_checklist.py:274-276` | Optional trim of M1/M2 prose; not primary blocker if spec gaps fixed. |
| 6 | Low | Test Alignment/Coverage Issues | #31 | Three test modules lack module-level docstrings (functions have docstrings). | `steps/milestone_*/tests/test_m*.py`; validate `informative_test_docstrings` warnings | Add one-line module docstrings to `test_m1.py`, `test_m2.py`, `test_m3.py`. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Milestone `test.sh` not canonical: missing `/logs/verifier` prewrite-0, `$PWD` guard, standard reward block (ChatGPT High) | **Partially agree** | `mkdir`, `--ctrf`, `RC=$?`, binary block present (`test.sh:7-20`); missing PWD guard and prewrite-0 (`writing-tests.md:11-17`). Severity **Medium**, not missing reward entirely. |
| 2 | M1 return value ambiguous — test expects carrier Hz, not sampling frequency (ChatGPT High / entire-report §4) | **Agree** | `instruction.md:5`; `test_m1_runner.c:51-52`; agent analysis `entire-report.txt:44-56`; M1 pass 9/10 |
| 3 | M3 `random.seed(42)` always selects ORACLE — single hardcodable target (ChatGPT High) | **Partially agree** | `python3 -c "random.seed(42); …"` → `ORACLE`; `test_m3.py:26-27`. Word is deterministic but tests are agent-invisible; issue is **coverage**, not direct answer leakage. Medium. |
| 4 | `test_no_message_format` omits `FRAMES_PROCESSED` assertion (ChatGPT Medium / test-quality review) | **Agree** | `instruction.md:3-5`; `test_m3.py:112-114` asserts only `NO message found\n` |
| 5 | M3 instruction unclear on mock replacement, preamble, null UART byte, early exit (ChatGPT Medium) | **Partially agree** | `instruction.md` is sparse; `mock_adc.c:60-66` has 5s preamble + null in word; test copies `/tests/mock_adc.c` (`test_m3.py:24`). Clarify in instruction; Low–Medium styling gap. |
| 6 | Rubric lines must be single physical line (entire-report opener) | **Disagree** | Portal rubrics (`entire-report.txt:462-491`) follow `Agent …, ±N` format; UI wrapping ≠ multi-line criterion. Author rebuttal valid. |
| 7 | ORACLE in tests folder is cheating vector (author rebuttal context) | **Disagree** | `ORACLE` only in `/tests/mock_adc.c:23` fallback `#else`; positive test injects `-DTEST_SECRET_WORD=ORACLE` via CFLAGS (`test_m3.py:27-28`). Agents cannot read `/tests/`. |
| 8 | Task “READY TO USE” / no critical issues (entire-report overall assessment) | **Disagree** | Contradicts LLMaJ `behavior_in_tests` fail (`entire-report.txt:77-78`), M1 spec-gap analysis (`entire-report.txt:50-56`), and blockers 1–3 above |
| 9 | Difficulty `hard` / 0% agents / oracle 100% (entire-report) | **Agree** | `task.toml:8`; `entire-report.txt:12-22` |
| 10 | M2 preamble “4 bits” vs 180–240 frames mismatch (entire-report LLMaJ) | **Partially agree** | `instruction.md:1` says “4 bits”; line 3 also says “3 to 4 second idle period (continuous Mark)” matching `test_m2_runner.c:34` (`180 + rand()%61` frames). Wording inconsistent but tested behavior is described. Low. |
| 11 | Non-canonical Ubuntu base (entire-report warning) | **Partially agree** | `Dockerfile:1` digest-pinned Ubuntu; Zephyr SDK/west justify non-canonical base per `reviewer-checklist-full.md:44`. Acceptable with justification. |
| 12 | `number_of_milestones` mismatch (validate) | **Disagree** (false positive) | `task.toml:12` comment contains `[[steps]]`; actual blocks at lines 32, 42, 52 = 3 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Combined 9 blocks / ~697 words exceeds automated >8-block threshold | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | DSP engineering brief; no synthetic LLM patterns | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No `##` headers or tables in instructions | — |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes/APIs, not a solve script | — |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Measurable DSP contracts, not algorithm walkthrough | — |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No markdown tables | — |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Paths, APIs, tolerances, and output format stated (M1 return unit excepted) | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic embedded PLL/FSK/Zephyr integration | — |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Not verified against corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/grid_pll.c`, `/app/headers/…`, `/app/fsk_decoder.c` | `steps/milestone_1/instruction.md:3`; `steps/milestone_2/instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No `grid-message` string | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time Zephyr SDK/Maven-style fetches only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `west==1.2.0` | `environment/Dockerfile:25,45` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Ubuntu 24.04 digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | Named COPY from `environment/` only | `environment/Dockerfile:58-65` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Scaffold stubs only; env `mock_adc.c` is empty stub | `environment/mock_adc.c:20-23` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/sys_admin/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; no pip/apt in test.sh | `environment/Dockerfile:25`; `steps/milestone_*/tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Oracle 100% (3/3) per report | `entire-report.txt:22` |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solveN.sh` copies C sources only | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | PI PLL, FSK state machine, Zephyr main loop | `steps/milestone_1/solution/grid_pll.c`; `steps/milestone_3/solution/main.c` |
| 24 | UNCHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing canonical PWD guard and prewrite-0 | `steps/milestone_*/tests/test.sh`; `writing-tests.md:11-17` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 1` / `echo 0` only | `steps/milestone_*/tests/test.sh:16-19` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | M1 return-unit gap; M3 negative-path `FRAMES_PROCESSED` gap | Blockers #1, #3 |
| 28 | CHECK | Tests check for correctness, not just format | PLL lock tolerances, FSK decode across carriers, Zephyr integration | `test_m1_runner.c`; `test_m2_runner.c`; `test_m3.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Compiled C harnesses + stdout checks | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Format strings mandated by instruction (`DECODED:`, `FRAMES_PROCESSED:`) | `steps/milestone_3/instruction.md:5-7` |
| 31 | UNCHECK | Tests have informative names or docstrings | Module-level docstrings missing on all three test files | validate warnings |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 negatives in portal rubric | `entire-report.txt:467-491` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:462-491` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 29 `Agent …, ±N` lines | `entire-report.txt:462-491` |
| 35 | CHECK | Rubric criteria are detailed and precise | DSP/FSK/Zephyr-specific criteria | `entire-report.txt:462-491` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Penalties use negative scores | `entire-report.txt:467-491` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No pytest/`/tests/` refs | `entire-report.txt:462-491` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:462-491` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:462-491` |
| 40 | CHECK | All required files present | Milestone layout complete | `task.toml`, `steps/`, `environment/Dockerfile` |
| 41 | CHECK | No unnecessary files in parent directory | No `jobs/`, stray README | `grid-message-20260623-194717/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both present | `task.toml:6-7` |
| 43 | CHECK | All other required metadata fields present | 3 `[[steps]]` blocks with timeouts; validate false positive only | `task.toml:13,32-59` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `dsp`, `embedded`, `zephyr`, `c` match | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` declared; 0% worst-model | `task.toml:8`; `entire-report.txt:17-18` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `steps/milestone_{1,2,3}/` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | `TestMilestone1/2/3` per file | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | No `COPY tests/` in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Secret word injected at test time via CFLAGS only | `test_m3.py:27-28`; env `mock_adc.c` stub |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Must implement PLL/FSK algorithms | `test_m1_runner.c`, `test_m2_runner.c` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | Zephyr `v3.7.0` pinned | `environment/Dockerfile:46` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% | `entire-report.txt:17-18` |
| 55 | UNCHECK | Task is not too hard or unfair | M1 spec ambiguity caused systematic plausible misinterpretation (9/10 M1 failures) | `entire-report.txt:30,44-56` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 9, 24, 27, 31, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: track 58–62 Hz within 0.005 Hz in <350 frames, 10 consecutive locks | `test_pll_tracking` / `test_m1_runner.c` | covered | `test_m1_runner.c:23-66` |
| M1: `grid_pll_update` return drives sampling rate | `test_pll_tracking` | **gap** | Runner multiplies return by 2048 (`test_m1_runner.c:52`); instruction never says “return Hz not sample rate” (`instruction.md:5`) |
| M2: FSK 8N1 UART decode, ±0.05 Hz mark/space, variable bit timing | `test_fsk_decoder` / `test_m2_runner.c` | covered | `test_m2_runner.c:10-46` |
| M2: preamble before message | `test_fsk_decoder` | covered | `test_m2_runner.c:34-37` (180–240 mark frames) |
| M3: print `FRAMES_PROCESSED` always | `test_full_integration` | covered | `test_m3.py:74-75` |
| M3: print `FRAMES_PROCESSED` on empty path | `test_no_message_format` | **gap** | `test_m3.py:112-114` — no `FRAMES_PROCESSED` assert |
| M3: print `DECODED: %s` or `NO message found` | `test_full_integration`, `test_no_message_format` | covered | `test_m3.py:66-71,112-114` |
| M3: stop on null / early exit | `test_full_integration` | covered | `test_m3.py:73-87` frame upper bound |
| M3: decode secret word (agent-unknown) | `test_full_integration` | covered (single word) | `test_m3.py:26-28,66-71` |
| M3: generic decode across word bank | `test_full_integration` | **gap** | Only `ORACLE` tested at seed 42 |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/instruction.md` | Blocker #1, #5, #27, checkbox #1 |
| `steps/milestone_1/tests/test_m1_runner.c` | Blocker #1, spec alignment |
| `steps/milestone_1/tests/test.sh` | Blocker #2, checkbox #24 |
| `steps/milestone_2/instruction.md` | Spec alignment, checkbox #1 |
| `steps/milestone_2/tests/test_m2_runner.c` | Spec alignment M2 preamble |
| `steps/milestone_2/tests/test.sh` | Blocker #2 |
| `steps/milestone_3/instruction.md` | Blockers #3–#4, spec alignment |
| `steps/milestone_3/tests/test_m3.py` | Blockers #3–#4, #31 |
| `steps/milestone_3/tests/mock_adc.c` | Adjudication #3, #7 |
| `steps/milestone_3/tests/test.sh` | Blocker #2 |
| `environment/Dockerfile` | Checkboxes #13–#20, #50 |
| `environment/mock_adc.c` | Checkbox #17, #51 |
| `task.toml` | Checkboxes #42–#46, validate false positive |
| `docs/guidelines/writing-tests.md` | Blocker #2 canonical shape |
| `entire-report.txt` | Agent stats, rubrics, LLMaJ, adjudication |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml [task.toml]: number_of_milestones (3) != [[steps]] count (4)
WARNING: task.toml [task.toml]: Each [[steps]] block should have name = "milestone_N"
WARNING: informative_test_docstrings [steps/milestone_*/tests/test_m*.py]: Test file should have a module-level docstring
INFO: check_task_absolute_path [steps/milestone_3/instruction.md]: No absolute paths detected
```

Note: `[[steps]]` count error is false positive (`task.toml:12` comment). Step names `milestone_1/2/3` are correct.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | `entire-report.txt:17-18` |
| terminus-claude-opus-4-8 | 0.0% (0/5) | `entire-report.txt:17-18` |
| oracle | 100.0% (3/3) | `entire-report.txt:22` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test: M1 `test_pll_tracking` 9/10; M2 `test_fsk_decoder` 10/10 (`entire-report.txt:30-31`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone task `grid-message-20260623-194717`; 3 DSP/Zephyr milestones; report applies |
| 1 Instruction | ☑ | M1 return-unit ambiguity High; M3 sparse on mock/preamble |
| 2 Environment | ☑ | Digest-pinned Ubuntu + Zephyr SDK; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Real C implementations; 100% per report; not run locally |
| 4 Verifiers | ☑ | test.sh shape gaps; M3 negative-path gap; module docstrings |
| 5 Metadata | ☑ | Fields complete; validate false positive on steps count |
| 6 Rubric | ☑ | Portal rubrics in `entire-report.txt` pass all format rules |
| 7 LLMaJ & agent evidence | ☑ | 0% agents supports hard; M1 spec gap confirmed by 9/10 failure |
| 8 Novelty & fairness | ☑ | Multi-step embedded DSP; M1 ambiguity unfair |
| 9 Long context | ☐ | N/A — `subcategories = []` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The digest-pinned Zephyr environment, offline dependency setup, anti-leak mock design, portal rubrics, and 0% agent pass rate look solid. Fix first: clarify M1 that `grid_pll_update()` must return carrier frequency in Hz (not sample rate × 2048) — this caused 9/10 agent failures on a plausible reading. Second: bring all milestone `test.sh` files to canonical shape (PWD guard, prewrite reward 0, then pytest). Third: assert `FRAMES_PROCESSED` in M3 `test_no_message_format` and parameterize multiple secret words for coverage.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 5 |
| Test Alignment/Coverage Issues | yes | 1, 3, 4, 6 |
| Test Build Issues | yes | 2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
