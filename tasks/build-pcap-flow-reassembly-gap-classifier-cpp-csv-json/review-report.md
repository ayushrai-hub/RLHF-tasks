# Terminus Review Report: `build-pcap-flow-reassembly-gap-classifier-cpp-csv-json`

**Generated:** 2026-07-04 17:20 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/build-pcap-flow-reassembly-gap-classifier-cpp-csv-json`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 1 false-positive pip warning) |
| **Oracle** | pass (submission export 3/3; local run blocked — Docker unavailable) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** No real blockers found after manual re-audit. The task has a clear instruction + normative contract, digest-pinned offline environment, runtime-generated CSV verification via an independent reference model, and well-calibrated difficulty (0% Claude / 100% GPT-5.5). Automated audit flags for #14 (pip pinning) and #31 (docstrings) are false positives. The platform rubric uses an optional `# Rubric 1` header on a non-milestone task — allowed per docs; 28 positive points and 4 distinct negatives pass all rubric rules.

**Insights (concise):**

- Reset-combination rule (`PR` → `invalid flags`) is specified in `flowgap_contract.md` lines 10, 15, 47 and referenced by `instruction.md`; agent 8/10 failures are implementation misses, not hidden verifier behavior.
- Platform rubric shape is valid: single `# Rubric 1` block only (no `# Rubric 2+`); 28/40 positive points; 4 negatives.
- `#14` FAIL from automated audit is a multiline-RUN heuristic bug — `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are pinned on continuation lines.
- All 10 `test_*` functions have docstrings; only the module-level docstring is absent (INFO, not required).
- Optional polish only: explicit `PR`/`SR` invalid-flags example in contract; doubled-quote RFC-4180 test case.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept — no High/Medium blockers | **Agree** | Full artifact re-audit; no spec-test gaps, rubric cap OK, env compliant |
| 2 | ChatGPT: Reset/PR miss is implementation error, not spec gap | **Agree** | `flowgap_contract.md:10,15,47`; `instruction.md:4` lists invalid TCP flags in `rows_skipped`; `tests/test_outputs.py:484,514` use `PR` → `invalid flags` |
| 3 | ChatGPT: Optional PR/SR invalid-flags sentence in contract | **Agree** (Low only) | Rule is derivable but agents uniformly missed it; clarity polish only |
| 4 | ChatGPT: Optional doubled-quote CSV edge case | **Agree** (Low only) | `flowgap_contract.md:1` requires doubled quotes; no test generates embedded quotes; `tests/test_outputs.py:478-479` only comma-in-field |
| 5 | ChatGPT: Tags at 6-tag limit, no action needed | **Agree** | `task.toml:11` — 6 tags within 3–6 range |
| 6 | ChatGPT: Dockerfile digest-pinned, canonical base OK for C++ | **Agree** | `environment/Dockerfile:1` `@sha256:4724b8cc…`; no canonical C++ base required |
| 7 | entire-report: Instruction Sufficiency FAIL (PR reset ambiguity) | **Disagree** as blocker | Contract + instruction cover invalid flags; reference `valid_flags()` at `tests/test_outputs.py:49-50` mirrors contract |
| 8 | entire-report: All agents 8/10 on same two tests | **Agree** (fact) | `entire-report.txt:52-55`; `test_quoted_csv_blank_lines_and_new_diagnostics`, `test_empty_stream_filter_preserves_global_diagnostics` |
| 9 | Harbor REVIEW REPORT: Non-canonical base image warning | **Agree** non-blocking | Debian slim digest-pinned; appropriate for C++/CMake toolchain |
| 10 | Harbor REVIEW REPORT: Tags at upper bound | **Agree** non-blocking | `task.toml:11` |
| 11 | TEST QUALITY: No doubled-quote RFC-4180 test | **Agree** (Low only) | Minor coverage gap; quoted-comma test already forces real CSV parsing |
| 12 | Automated audit #14: Unpinned pip | **Disagree** | `environment/Dockerfile:18-20` — packages pinned with `==` on continuation lines; heuristic only checks first line |
| 13 | Automated review #31: Missing test docstrings | **Disagree** | All 10 `test_*` functions have docstrings (`tests/test_outputs.py:336-575`); only module-level docstring absent (INFO) |
| 14 | Automated audit #27: Phantom numeric thresholds [6,8,20] | **Disagree** as blocker | Counts are derived consequences of contract-validated CSV rows, verified via `assert actual == expected_payload(...)` |
| 15 | User concern: Non-milestone task uses milestone rubric format | **Disagree** as blocker | Single `# Rubric 1` header only; `docs/guidelines/submission-export-format.md:63` — optional for non-milestone; no `# Rubric 2+` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 4 prose paragraphs, ~382 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as incident-triage scenario, not synthetic spec | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Describes outcome and contract ref, not build steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | WHAT to build; contract is normative reference | `instruction.md:4` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Binary path, CLI, contract path, behaviors enumerated | `instruction.md:1-4` |
| 8 | CHECK | Interesting | Real TCP flow/gap triage from CSV metadata | `instruction.md:1` |
| 9 | CHECK | Unique | C++ interval-accounting + RFC-4180 CSV + compact JSON schema; corpus dup not verified | — |
| 10 | CHECK | Absolute paths | `/app/bin/flowgap`, `/app/docs/flowgap_contract.md`, etc. | `instruction.md:1-4` |
| 11 | CHECK | Task name absent | No folder slug in instruction | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch | Offline env; apt at build only | `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18-20` |
| 15 | CHECK | FROM digest-pinned | `@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` | `environment/Dockerfile:1` |
| 16 | CHECK | Env self-contained | COPY only from environment/ | `environment/Dockerfile:24-29` |
| 17 | CHECK | No ground-truth leakage | Docs are educational; starter `main.cpp` is intentionally broken | `environment/docs/`, `environment/src/main.cpp` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts OK | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:18-20`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Export: oracle 100% (3/3); solve.sh builds + smoke-checks | `entire-report.txt:26`, `solution/solve.sh` |
| 22 | CHECK | Oracle offline | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results | Copies fixed C++ source, builds, validates fixture + runtime CSV | `solution/solve.sh:4-69` |
| 24 | CHECK | reward.txt canonical | Writes 0/1; mkdir /logs/verifier | `tests/test.sh:4-19` |
| 25 | CHECK | Same verifier for agent/oracle | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:15-18` |
| 27 | CHECK | Tests aligned with spec | Every assertion traces to instruction or contract | §5 below |
| 28 | CHECK | Tests check correctness | Deep equality vs independent reference model | `tests/test_outputs.py:243-268,363` |
| 29 | CHECK | Behavior not implementation | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle beyond spec | Exact stderr/JSON keys match documented contract strings | `flowgap_contract.md:47`, `tests/test_outputs.py:536,566` |
| 31 | CHECK | Informative test docstrings | All 10 `test_*` have docstrings | `tests/test_outputs.py:336-575` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives (-5,-5,-3,-3) | `entire-report.txt:320-323` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use ±3 or ±5 | `entire-report.txt:312-323` |
| 34 | CHECK | Agent …, ±N format | 12 properly formatted lines | `entire-report.txt:312-323` |
| 35 | CHECK | Rubric detailed; positive cap | 28 positive pts (≤40) | `./scripts/terminus rubric-points entire-report.txt` |
| 36 | CHECK | Positive rubric language | Criteria describe desired behavior on + lines | `entire-report.txt:312-319` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:312-323` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:312-323` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:312-323` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No stray parent files | Clean task directory | task root |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | cpp, csv, json, tcp, data-processing | `task.toml:7-11` |
| 45 | CHECK | Difficulty field present | hard; worst-model 0% → hard tier | `task.toml:6`, `entire-report.txt:16-22` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:14` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:14` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:14` |
| 50 | CHECK | Tests not in image | No COPY tests/; .dockerignore excludes | `environment/Dockerfile`, `environment/.dockerignore:16-17` |
| 51 | CHECK | Solution not in env | .dockerignore excludes solution/ | `environment/.dockerignore:16` |
| 52 | CHECK | No trivial input cheat | Runtime CSV with random stream names | `tests/test_outputs.py:290-317` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:21-22` |
| 55 | CHECK | Not unfair | Contract fully specifies behavior; agent miss is documented rule combination | `flowgap_contract.md:10,15,47` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Binary at `/app/bin/flowgap`; build via `/app/scripts/build.sh` | all (setUpModule) | covered | `tests/test_outputs.py:21-22` |
| CLI `--csv/--out` absolute paths; status 2 + stderr | `test_absolute_path_validation` | covered | `instruction.md:2`; `tests/test_outputs.py:557-575` |
| Usage/unknown-flag errors | `test_invalid_header_and_flag_errors` | covered | `instruction.md:2`; `tests/test_outputs.py:538-554` |
| Invalid CSV header → non-zero + `invalid csv header` | `test_invalid_header_and_flag_errors` | covered | `flowgap_contract.md:14`; `tests/test_outputs.py:527-536` |
| RFC-4180 CSV; blank lines; physical row diagnostics | `test_quoted_csv_blank_lines_and_new_diagnostics` | covered | `flowgap_contract.md:1,13`; `tests/test_outputs.py:475-502` |
| Segment statuses (6 types) | `test_fixture_*`, `test_runtime_*` | covered | `flowgap_contract.md:29-37`; `tests/test_outputs.py:336-370` |
| Gap lifecycle filled/open/abandoned | cascade, reset, bidirectional tests | covered | `flowgap_contract.md:39-41`; `tests/test_outputs.py:390-472` |
| Bidirectional independent state | `test_bidirectional_state_and_reset_abandons_direction_gap` | covered | `flowgap_contract.md:23`; `tests/test_outputs.py:417-445` |
| Reset abandons direction gaps only | reset + bidirectional tests | covered | `flowgap_contract.md:12,33`; `tests/test_outputs.py:448-472` |
| `--stream` filter; global diagnostics preserved | `test_stream_filter_*`, `test_empty_stream_filter_*` | covered | `flowgap_contract.md:45`; `tests/test_outputs.py:372-387,505-522` |
| Invalid flags incl. R-combo (PR) | quoted CSV tests | covered | `flowgap_contract.md:10,15,47`; `tests/test_outputs.py:484,514,498` |
| Compact JSON key order + trailing newline | all via `run_flowgap` | covered | `flowgap_contract.md:17-45`; `tests/test_outputs.py:30-33,320-333` |
| Runtime-generated CSV (anti-fixture-memorization) | `test_runtime_generated_csv_classification` | covered | `instruction.md:4`; `tests/test_outputs.py:357-369` |
| Doubled-quote inside quoted fields | — | gap (Low) | Spec at `flowgap_contract.md:1`; no test row with embedded `"` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–7, #10–11, #27, spec alignment |
| `task.toml` | #14, #42–45, milestone N/A |
| `environment/Dockerfile` | #13–16, #20, #50, #14 adjudication |
| `environment/docs/flowgap_contract.md` | #17, #27, #55, PR-flag adjudication |
| `environment/.dockerignore` | #50–51 |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, spec alignment |
| `solution/solve.sh` | #21–23 |
| `entire-report.txt` | #32–39, #45, #54, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate build-pcap-flow-reassembly-gap-classifier-cpp-csv-json/
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: regular
```

Warning on pip pinning is a false positive (multiline RUN heuristic).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | All tests pass |
| terminus-claude-opus-4-8 | 0% (0/5) | Uniform 8/10 — PR invalid-flags miss |
| oracle | 100% (3/3) | Per submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test: `test_quoted_csv_blank_lines_and_new_diagnostics` and `test_empty_stream_filter_preserves_global_diagnostics` at 5/10 — both hinge on `PR` → `invalid flags` rule.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular layout; C++/data-processing |
| 1 Instruction | ☑ | Concise; contract-referenced; absolute paths |
| 2 Environment | ☑ | Digest-pinned Debian; tmux+asciinema; pytest pinned; no tests/solution COPY |
| 3 Oracle | ☑ | Real C++ implementation; export 3/3 pass |
| 4 Verifiers | ☑ | Reference model; runtime CSV; binary reward; all test docstrings |
| 5 Metadata | ☑ | hard; allow_internet=false; 6 tags OK |
| 6 Rubric | ☑ | 28 pts; 4 negatives; single `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency debate resolved — spec complete |
| 8 Novelty & fairness | ☑ | Multi-step C++ algorithm; no cheat paths |
| 9 Long context | ☐ N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The flow-reassembly problem is well framed, the contract doc gives agents everything they need for CSV parsing, gap lifecycle, resets, and compact JSON output, and the verifier strategy — fresh runtime CSVs compared against an independent reference — is solid. Oracle passes cleanly and the difficulty spread (GPT strong, Claude struggling on one narrow flag-validation rule) looks right for hard. I didn't find any blocking spec gaps; the common miss on `PR`/`SR`-style flags is covered by combining the reset-validity and invalid-flags rules in the contract. Optional polish if you want: one explicit invalid-flags example for mixed-R combos, and a doubled-quote CSV row in tests.

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
| Milestones | no | — |
| Uses Internet | no | — |
| Agent Timeout | no | — |
| Wrong Coding Language | no | — |
| Canary Strings | no | — |
| Rubric | no | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review build-pcap-flow-reassembly-gap-classifier-cpp-csv-json/ --report entire-report.txt`._
