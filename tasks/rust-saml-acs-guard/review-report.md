# Terminus Review Report: rust-saml-acs-guard

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 4 warnings) |
| **Oracle** | pass (platform: 100% 3/3; local not run — Docker unavailable) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Test Build Issues

**Decision (concise):** The SAML spec, environment, oracle design, and hidden Rust graded suite are strong, and agent calibration looks right (worst model 0%). The single real High blocker is verifier structure: `test_outputs.py` is one pytest wrapper that copies `hidden_tests.rs` and runs `cargo test`, so all 40 graded assertions live in Rust instead of separate Python tests per `writing-tests.md` / `task-requirements.md` and prior portal feedback. Automated script flags on #10, #14, and #20 are false positives on manual audit. Rubric uses allowed non-milestone format (`# Rubric 1` only, 37/40 pts); one negative line uses “fails to” phrasing (#36, Medium only).

**Insights (concise):**

- Prior portal feedback (`entire-report.txt:1-6`) and ChatGPT High finding are **confirmed** — not a false positive.
- `hidden_tests.rs` has **40** `#[test]` functions; pytest reports only `test_saml_acs_security_contract` (binary cliff at 39/40 vs 35/40).
- Rubric is **not** in wrong milestone format: single optional `# Rubric 1` block, no `# Rubric 2+` (`rubrics.md:66`).
- `#10` relative-path fail is regex false positive on `<Signature .../>` ellipsis (`instruction.md:3`).
- `#14` / `#20` pass: `requirements.lock` pins `pytest==8.4.1` with hashes; Dockerfile installs via `--require-hashes` (`environment/Dockerfile:19-21`).
- Agent stats: Claude Opus 4.8 0% (0/5), GPT-5.5 80% (4/5); worst 0% → hard tier; #54 passes.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Test Build Issues | #27, #31 | Verifier delegates all graded logic to a hidden Rust suite via one opaque pytest wrapper; does not meet “Python pytest with separate test functions / one test per requirement” | `tests/test_outputs.py:10-26` (single `test_saml_acs_security_contract`, copies `hidden_tests.rs`, runs `cargo test`); `tests/hidden_tests.rs` (40 `#[test]` functions, all assertions in Rust); `docs/guidelines/writing-tests.md:34-49` (“Verifier = Python pytest”, “One test per requirement minimum”); `docs/task-requirements.md:93-96`; `entire-report.txt:1-6` (prior portal feedback) | Port requirement checks into multiple `test_*` functions in `test_outputs.py` with Python assertions (e.g. subprocess + parsed output, or per-test `cargo test` filters with distinct pytest functions and docstrings). Do not rely on one wrapper over an opaque Rust file as the sole graded surface. |

*No other High-severity blockers on manual audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier must not delegate to hidden Rust suite; move logic to Python `test_outputs.py` with per-requirement functions (portal feedback `entire-report.txt:1-6`; ChatGPT High) | **Agree** | `tests/test_outputs.py:10-26`; `tests/hidden_tests.rs` (40 tests); `writing-tests.md:49`; `task-requirements.md:96` |
| 2 | SAML contract strong; good coverage of parsing, signatures, ordering, audit (ChatGPT Medium none) | **Agree** | `environment/task_file/docs/SPEC.md`; `hidden_tests.rs` test names cover parser, wrapping, gates, audit, summary |
| 3 | Optional denial-reason applicability table in SPEC.md (ChatGPT Low) | **Agree** (Low only) | `entire-report.txt:88-91`; `SPEC.md:42-68` describes gates but no response vs assertion table — polish, not blocker |
| 4 | Dockerfile digest-pinned Rust base OK (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:9f841bbe…` |
| 5 | Harbor: non-canonical Rust base image (`entire-report.txt:151-173`) | **Disagree** as blocker | No Rust image in t-bench registry; digest-pinned ECR Rust is justified (`reviewer-checklist-full.md:44`) |
| 6 | Harbor: generic directory name `tbench-task` (`entire-report.txt:176-189`) | **Disagree** as blocker | Folder is `rust-saml-acs-guard`; naming is Low/cosmetic only |
| 7 | Harbor: single pytest function suggestion (`entire-report.txt:196-212`) | **Agree** (same root cause as blocker #1) | `tests/test_outputs.py:10` |
| 8 | LLMaJ `behavior_in_tests` PASS (`entire-report.txt:116`) | **Agree** on coverage; does not override verifier-structure rule | Hidden suite is comprehensive; structure still non-compliant |
| 9 | LLMaJ `informative_test_structure` PASS on Rust tests (`entire-report.txt:117`) | **Partially agree** | Rust `#[test]` names are descriptive; pytest layer lacks module/test docstrings and granularity |
| 10 | Instruction sufficiency FAIL on agent analysis (`entire-report.txt:41-112`) | **Disagree** as revision blocker | Failures are agent edge-case bugs (ID chars, assertion-level issuer, signature propagation); spec is detailed; optional table is Low |
| 11 | Non-milestone task uses milestone rubric format (user query) | **Disagree** | `task.toml:11` `number_of_milestones = 0`; rubric has only `# Rubric 1` (optional for non-milestone); no `# Rubric 2+` (`rubrics.md:66`) |
| 12 | Automated review #10 relative paths | **Disagree** | `../` matched inside `<Signature .../>` XML example, not a path (`instruction.md:3`) |
| 13 | Automated review #14 unpinned pip | **Disagree** | `requirements.lock` uses `pytest==8.4.1` + hashes; Dockerfile `--require-hashes` (`Dockerfile:19-21`) |
| 14 | Automated review #20 pytest not in Dockerfile | **Disagree** | pytest installed from locked requirements in image; `test.sh` has no runtime installs (`tests/test.sh:17`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Concise instruction | 2 paragraphs, ~247 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer-facing problem statement, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | No `##` / tables / code fences | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements via SPEC reference, no solve script | `instruction.md` |
| 5 | CHECK | No hints/strategies | Contract details are WHAT, not implementation steps | `instruction.md` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Clear crate, paths, SPEC contract, constraints | `instruction.md`, `SPEC.md` |
| 8 | CHECK | Interesting | Real SAML ACS security problem | — |
| 9 | CHECK | Unique | SAML+Rust signature-validation task; not duplicate-checked in corpus | — |
| 10 | CHECK | Absolute paths only | All paths `/app/...`; `../` hit is XML ellipsis false positive | `instruction.md:1,3` |
| 11 | CHECK | Task name not in instruction | No `rust-saml-acs-guard` string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web fetch in env | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Pinned Python deps | Hash-locked `requirements.lock` with `==` | `environment/requirements.lock:11-14`, `Dockerfile:19-21` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:` on Rust base | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY only `task_file`, `requirements.lock` | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in env | Broken stub `lib.rs`; SPEC is normative contract | `environment/task_file/src/lib.rs` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in venv from lock; no runtime install in test.sh | `Dockerfile:19-21`, `tests/test.sh:17` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle no internet | Writes `lib.rs`, runs `cargo test` locally | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | Full algorithmic implementation | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical | mkdir + 0/1 write after pytest | `tests/test.sh:14-23` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:19-22` |
| 27 | UNCHECK | Tests aligned with instructions | Blocker #1: structure violates Python verifier guidelines despite good SPEC coverage | `tests/test_outputs.py`, blocker #1 |
| 28 | CHECK | Tests check correctness | Hidden Rust tests assert exact decisions, reasons, audit strings | `tests/hidden_tests.rs` |
| 29 | CHECK | Behavior not implementation grep | No source grepping in verifier | `tests/test_outputs.py` |
| 30 | CHECK | No brittle matching (given spec) | Exact denial-reason strings required by SPEC | `SPEC.md:42-58` |
| 31 | UNCHECK | Informative test docstrings | Missing module docstring and `test_saml_acs_security_contract` docstring | `tests/test_outputs.py:1-10` |
| 32 | CHECK | ≥3 negative rubric criteria | Three negatives (-5, -3, -2) | `entire-report.txt:313-315` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:293-315` |
| 34 | CHECK | Rubric format `Agent …, ±N` | 22 Agent lines | `entire-report.txt:294-315` |
| 35 | CHECK | Rubric detailed; positive cap | 37/40 positive pts (≤40) | `entire-report.txt:293-315` |
| 36 | UNCHECK | Positive rubric phrasing | “Agent fails to handle…” uses negative phrasing | `entire-report.txt:315` |
| 37 | CHECK | Rubric no /tests/ refs | References `visible_tests.rs`, not `/tests/` | `entire-report.txt:296` |
| 38 | CHECK | Rubric no instruction.md refs | References SPEC.md, lib.rs only | `entire-report.txt:294-311` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:293-315` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust, security, saml; category security | `task.toml:7-9` |
| 45 | CHECK | Difficulty field present | `hard`; platform hard; worst-model 0% | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:11` |
| 50 | CHECK | Tests not baked in image | `.dockerignore` excludes `tests/` | `environment/.dockerignore:6` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:5` |
| 52 | CHECK | Agent cannot trivially cheat | Hidden tests injected at verify time; complex SAML logic | `tests/test_outputs.py:11-15` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:26-27` |
| 55 | CHECK | Not unfair | Detailed SPEC; agents score 35–39/40 hidden; visible tests pass | `entire-report.txt:47-54` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 27, 31, 36, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / SPEC) | Test(s) | Status | Proof |
|----------------------------------|---------|--------|-------|
| Parse six tag types; signatures inside assertions on `SamlResponse.signatures` | `parser_handles_nested_assertions_signatures_attributes_and_comments` | covered | `hidden_tests.rs:65` |
| Parse errors: structure, unknown tags, illegal ID chars | `parser_reports_precise_errors_for_structure_and_attributes`, `parser_rejects_unknown_tags_and_ids_with_illegal_chars` | covered | `hidden_tests.rs:98,503` |
| Signature wrapping / exact target matching | `signature_wrapping_uses_signed_assertion_target_not_first_assertion`, `signature_target_matching_is_exact_not_prefix_suffix_or_case_insensitive` | covered | `hidden_tests.rs:126,811` |
| Terminal gates: malformed-time, duplicate-id before signatures | `duplicate_ids_are_denied_before_signature_checks`, `malformed_calendar_times_are_rejected_before_other_checks` | covered | `hidden_tests.rs:151,263` |
| Response-level denials before assertion checks | `global_denials_are_reported_in_documented_order` | covered | `hidden_tests.rs:209` |
| Clock skew inclusive/exclusive windows | `validity_window_honors_skew_and_exclusive_not_on_or_after` | covered | `hidden_tests.rs:227` |
| Covered-assertion selection logic | `valid_later_covered_assertion_can_be_selected_after_invalid_covered_assertion` | covered | `hidden_tests.rs:297` |
| Zero assertions → `assertion-signature-required` | `no_assertions_are_denied_even_when_assertion_signing_is_not_required` | covered | `hidden_tests.rs:847` |
| Audit finding order and formats | `audit_reports_duplicate_ids_missing_targets_unsigned_objects_weak_algs_and_empty_subjects` | covered | `hidden_tests.rs:384` |
| `summary_lines` deterministic format | `summary_lines_are_deterministic` | covered | `hidden_tests.rs:407` |
| Verifier exposes requirements as separate Python tests | — | **gap** | `tests/test_outputs.py:10` (single wrapper) |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #10 false positive, spec alignment |
| `task.toml` | #44-45, #46-49 N/A |
| `environment/Dockerfile` | #14-15, #20 |
| `environment/requirements.lock` | #14 |
| `environment/.dockerignore` | #50-51 |
| `environment/task_file/docs/SPEC.md` | #7, spec alignment |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | Blocker #1, #27, #31 |
| `tests/hidden_tests.rs` | Blocker #1, #28, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | Portal feedback, rubric, agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate rust-saml-acs-guard/
Summary: 0 error(s), 4 warning(s), 2 info
Warnings: relative paths (false positive), pip line heuristic, missing docstrings, trailing exit info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | One failure |
| terminus-claude-opus-4-8 | 0.0% (0/5) | All failed hidden suite |
| oracle | 100.0% (3/3) | Platform |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

### Rubric positive points

| Field | Value |
|-------|-------|
| Positive point total | 37 |
| Cap | 40 |
| Status | PASS (37/40) |
| Format | Single `# Rubric 1` — valid for non-milestone |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Rust security task; report matches folder |
| 1 Instruction | ☑ | Strong SPEC-backed prompt; #10 false positive cleared |
| 2 Environment | ☑ | Digest-pinned Rust, tmux/asciinema, hash-locked pytest; #14/#20 cleared |
| 3 Oracle | ☑ | Platform 100%; derives full lib.rs implementation |
| 4 Verifiers | ☑ | **Blocker:** single pytest → hidden Rust suite pattern |
| 5 Metadata | ☑ | Fields complete; `number_of_milestones = 0` |
| 6 Rubric | ☑ | 37/40 pts; not milestone-format error; #36 minor phrasing |
| 7 LLMaJ & agent evidence | ☑ | Coverage PASS; structure conflict adjudicated for artifacts |
| 8 Novelty & fairness | ☑ | Multi-step SAML implementation; anti-cheat sound |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really strong work on the SAML contract and the hidden graded scenarios — SPEC.md is thorough, the Dockerfile is clean with a pinned base and offline verifier deps, and difficulty calibration looks spot-on (agents get close but rarely sweep all 40 checks). The one thing blocking acceptance is verifier structure: `test_outputs.py` is a single pytest function that copies `hidden_tests.rs` and runs `cargo test`, so pytest only reports one pass/fail and all assertion logic lives in Rust. Please split this into separate Python `test_*` functions that map to individual requirements (with docstrings), verifying behavior directly in Python or via named per-requirement invocations — not one opaque Cargo wrapper. While you’re in there, add the missing module/test docstrings, and optionally rephrase the rubric line “Agent fails to handle the zero-assertions case” to positive phrasing (e.g. “Agent leaves zero-assertions case unhandled, -2”).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Test Build Issues | yes | 1 |
| Instruction Styling | no | — |
| Rubric | no | — (37/40; #36 Medium only) |
| Environment | no | — |
| Pinning Issues | no | — |
| Milestones | no | — (correct non-milestone layout) |
