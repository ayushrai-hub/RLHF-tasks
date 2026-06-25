# Terminus Review Report: `commonmark-debug-rust`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** none

**Decision (concise):** Accept. The task is a well-crafted Rust CommonMark inline-debugging benchmark with digest-pinned Docker base, `allow_internet = false`, verifier deps baked into the image, tests/solution excluded from runtime, SHA-256 input integrity, and a 98-op held-out synthetic battery. Oracle passes (reward 1.0). GPT-5.5 at 20% supports declared `hard`; Claude at 80% sits at the easy-tier ceiling but does not exceed the 80% rejection threshold. No High-severity spec, env, oracle, or verifier gaps found on re-audit.

**Insights (concise):**

- Automated `#14` / `#45` failures are false positives: pip packages are `==`-pinned on continuation lines; GPT-5.5 at 20% justifies `difficulty = "hard"` per `docs/guidelines/difficulty.md`.
- Rubric content appears in `entire-report.txt` (portal submission, lines 255–272) with ≥3 negatives; no `rubric.txt` in task folder → portal rubric checkboxes N/A.
- `test_no_hardcoded_answers` lacks a docstring but has a descriptive name and a 6-line comment block above `SYNTH`; Low only.
- Agent failures trace to implementation errors (soft-break trim, emphasis rule-of-3), not instruction ambiguity — consistent with external agent analysis.
- Python-slim base with layered rustup is a credible dual-language pattern (verifier pytest + agent cargo).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

**Low (non-blocking):**

| Item | Proof | Note |
|------|-------|------|
| Missing docstring on `test_no_hardcoded_answers` | `tests/test_outputs.py:142` | Name + comment block suffice for #31; add docstring for style consistency |
| `.dockerignore` excludes `Cargo.lock` | `environment/.dockerignore:10` | Benign for std-only crate |
| Validator pip warning | `environment/Dockerfile:33-35` | False positive — packages pinned on next lines |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium/Low issues | Agree | Full artifact re-audit; no High gaps |
| 2 | ChatGPT: digest-pinned Docker, `allow_internet = false`, tests/solution excluded | Agree | `task.toml:23`, `environment/Dockerfile:1,38`, no `COPY tests/` |
| 3 | ChatGPT: strong held-out coverage and anti-cheating | Agree | `tests/test_outputs.py:132-165` (98 SYNTH ops), `CASES_SHA256` at `:20` |
| 4 | ChatGPT: visible rubric with task-specific positive/negative criteria | Partially agree | Rubric in `entire-report.txt:255-272` (portal); no `rubric.txt` in task folder — checkboxes #32–39 N/A |
| 5 | ChatGPT: appropriately calibrated as Hard | Agree | `entire-report.txt:7-9` GPT-5.5 20% ≤20% hard threshold per `difficulty.md:9,14` |
| 6 | entire-report: rubric absent is concrete blocker | Disagree | Rubric present in portal report (`entire-report.txt:255-272`); ≥3 negatives (`-5,-5,-3`); task folder need not contain `rubric.txt` |
| 7 | entire-report: Hard difficulty, solvable, oracle 100% | Agree | `task.toml:6`, `entire-report.txt:5-13`; local oracle `jobs/2026-06-21__17-15-50/result.json` reward 1.0 |
| 8 | entire-report: Claude 80%, GPT 20% | Agree | `entire-report.txt:7-9` |
| 9 | Quality: behavior_in_task_description PASS | Agree | `instruction.md:1-36` covers all tested constraints; docs referenced as contract |
| 10 | Quality: behavior_in_tests PASS | Agree | Parametrized cases + SYNTH + hash + deps + warnings tests |
| 11 | Quality: anti_cheating PASS | Agree | No tests in image; offline cargo; held-out battery |
| 12 | Quality: hardcoded_solution PASS | Agree | `solution/solve.sh:16+` writes `parse.rs`/`render.rs`/`text.rs`, then `cargo build` |
| 13 | Validation warning: unpinned pip | Disagree | `environment/Dockerfile:34-35` `pytest==8.3.4`, `pytest-json-ctrf==0.3.5` |
| 14 | Validation warning: missing docstring | Agree | `tests/test_outputs.py:142` — Low only |
| 15 | Validation: non-canonical Rust base | Partially agree | Python slim + rustup 1.82.0 (`Dockerfile:1,26`); justified dual-language need; not a blocker |
| 16 | Agent analysis: instruction sufficient, failures are agent errors | Agree | `entire-report.txt:59-60`; soft-break / emphasis patterns match SYNTH coverage |
| 17 | Test quality: ACCEPT, robust held-out battery | Agree | `tests/test_outputs.py:139` 98 synthetic tuples |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraphs, ~446 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Human engineer tone; no LLM scaffolding | `instruction.md:1-14` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | Describes problem + contract, not fix steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Points to docs as spec, not which files to edit | `instruction.md:15-25` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, outputs, constraints, doc contract | `instruction.md:1-36` |
| 8 | CHECK | Instruction is interesting | Realistic CommonMark parser debugging | — |
| 9 | CHECK | Instruction is unique | No duplicate found in corpus review | — |
| 10 | CHECK | All paths in instruction are absolute | Root `/app/task_file` stated; subpaths relative to it | `instruction.md:1,4,12,15` |
| 11 | CHECK | Task name does not appear in instruction.md | `commonmark-debug-rust` absent | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | rustup at build only; no runtime fetch | `environment/Dockerfile:25-28` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.3.4`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:33-35` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | `COPY task_file` only | `environment/Dockerfile:38` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Docs are normative spec; no solution leakage in src comments | `environment/task_file/src/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:32-35`, `tests/test.sh:15` |
| 21 | CHECK | Oracle passes consistently | Local oracle reward 1.0 | `jobs/2026-06-21__17-15-50/result.json` |
| 22 | CHECK | Oracle does not require internet | `cargo build --release` offline in solve.sh | `solution/solve.sh:14+` |
| 23 | CHECK | Oracle is reflective of instruction | Rewrites buggy source files, builds crate | `solution/solve.sh:16-738` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical block present | `tests/test.sh:7-21` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `tests/test.sh:17-20` |
| 27 | CHECK | All tests aligned with instructions | Every instruction req has test coverage | §5 table |
| 28 | CHECK | Tests check correctness, not just format | Exact HTML/JSON output vs reference | `tests/test_outputs.py:92-97` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs binary; no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact match required for HTML renderer contract | `tests/test_outputs.py:81-82` |
| 31 | CHECK | Tests have informative names or docstrings | `test_no_hardcoded_answers` name + comment block; others have docstrings | `tests/test_outputs.py:92-197` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — rubric via portal, not in task folder | `entire-report.txt:255-272` |
| 33 | UNCHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion one line Agent, score | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference /tests/ | N/A | — |
| 38 | UNCHECK | Rubric does not reference task.toml or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, verifier, agent, environment | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | rust/debugging/commonmark match content | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches observed agent pass rates | GPT-5.5 20% ≤20% earns Hard per difficulty.md | `task.toml:6`, `entire-report.txt:7-9` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:10` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests NOT baked into Docker image | No `COPY tests/` | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ not copied | `environment/Dockerfile:38` |
| 52 | CHECK | Agent cannot trivially modify input data | SHA-256 hash enforced | `tests/test_outputs.py:20,45-50` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst model 80% — not >80% | `entire-report.txt:7` |
| 55 | CHECK | Task not too hard or unfair | Thorough docs/ contract; failures are implementation gaps | `instruction.md:15-25`, agent analysis |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Emphasis / strong emphasis correct | `test_case[emphasis-basic]`, `test_case[emphasis-nesting]`, SYNTH | covered | `tests/test_outputs.py:88,139` |
| Code spans | `test_case[code-spans]`, SYNTH | covered | `tests/test_outputs.py:88` |
| Backslash escapes & entities | `test_case[escapes-entities]`, SYNTH | covered | `tests/test_outputs.py:88` |
| Line breaks (soft/hard) | `test_case[line-breaks]`, SYNTH | covered | `tests/test_outputs.py:88` |
| Links & images | `test_case[links]`, `test_case[images]`, SYNTH | covered | `tests/test_outputs.py:88` |
| Unknown op → error | `test_case[errors]` | covered | `tests/test_outputs.py:88` |
| Don't modify cases.json | SHA-256 check in `actual` fixture | covered | `tests/test_outputs.py:20,45-50` |
| Output deterministic, input order | `test_output_is_deterministic`, `test_case_ids_in_input_order` | covered | `tests/test_outputs.py:110-129` |
| Std-only, no external crates | `test_cargo_no_external_dependencies` | covered | `tests/test_outputs.py:168-193` |
| No build warnings | `test_build_has_no_warnings` | covered | `tests/test_outputs.py:196-211` |
| Held-out generalization | `test_no_hardcoded_answers` | covered | `tests/test_outputs.py:142-165` |
| All case ids present | `test_all_case_ids_present` | covered | `tests/test_outputs.py:100-107` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `task.toml` | #42-45, #54 |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/.dockerignore` | Low note |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `tests/conftest.py` | #20 build fixture |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #45, #54, adjudication, rubric |
| `jobs/2026-06-21__17-15-50/result.json` | #21 oracle |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: commonmark-debug-rust/ ===
Summary: 0 error(s), 2 warning(s), 2 info
- WARNING: pinned_dependencies (false positive — packages pinned on continuation lines)
- WARNING: informative_test_docstrings (test_no_hardcoded_answers — Low)
- INFO: non-milestone layout; trailing exit in test.sh (harmless)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Supports Hard tier |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Easy-tier ceiling |
| oracle | 100.0% (3/3 report; 1/1 local) | Consistent pass |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst) | easy (at boundary) |
| Best-model rate | 20.0% |
| Declared difficulty | hard |
| Tier match (#45) | yes (best model ≤20%) |

Per-test pass rates (`entire-report.txt:21-34`): `test_no_hardcoded_answers` 5/10 — primary differentiator; sample cases 7-10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `commonmark-debug-rust`; regular layout; Rust debugging task |
| 1 Instruction | ☑ | Clear contract via docs/; no hints or canary |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; offline cargo; no tests/solution in image |
| 3 Oracle | ☑ | Passes locally; derives fix from source rewrite |
| 4 Verifiers | ☑ | Canonical reward; behavior tests; 1 missing docstring (Low) |
| 5 Metadata | ☑ | Fields complete; hard justified by GPT-5.5 |
| 6 Rubric | N/A | Portal rubric in entire-report; task folder has no rubric.txt |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; agent failures are implementation errors |
| 8 Novelty & fairness | ☑ | Multi-file debugging; held-out battery closes cheating |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction establishes a clear contract via `docs/`, the environment uses a digest-pinned base with verifier dependencies baked into the image and tests/solution excluded from runtime, and the verifier combines shipped cases with a 98-op held-out synthetic battery plus integrity checks. Oracle passes consistently. GPT-5.5 at 20% supports declared hard difficulty; Claude at 80% is at the easy-tier boundary but does not exceed rejection threshold. Optional polish: add a docstring to `test_no_hardcoded_answers`.

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

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review commonmark-debug-rust/ --report entire-report.txt`; oracle run `./scripts/terminus oracle commonmark-debug-rust/`._
