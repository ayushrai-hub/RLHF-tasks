# Terminus Review Report: tbrain-process-kettle-cycle

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Strong Rust state-machine / anti-short-cycle control task with a digest-pinned canonical offline environment, normative `docs/spec.md`, 14 curated boundary fixtures, 80 boundary-biased differential tests, and malformed-input coverage. Oracle passes cleanly (1.000). Agent rates (GPT 0%, Claude 40%) support declared `hard` difficulty. Automated baseline blockers on #14 and #20 are false positives — deps are hash-pinned via `requirements.lock` and baked into the image. Platform rubric uses correct **flat non-milestone format** (no `# Rubric 2+` headers). No High-severity blockers found.

**Insights (concise):**

- ChatGPT Accept verdict and Harbor READY TO USE recommendation are **supported** by artifact review; no spec-test gaps or environment compliance issues found.
- Automated `#14` / `#20` fails are **wrong**: pip uses `--require-hashes -r requirements.lock` with `pytest==8.4.1`; test.sh does not install packages at runtime.
- Non-milestone rubric is **not** in milestone format — flat `Agent …, ±N` list with no `# Rubric N` section headers (`entire-report.txt:443-461`).
- Platform rubric positive total is **43 pts** (3 over the 10–40 non-milestone guideline) — **Low** severity only; not a Revise driver.
- File-path CLI mode (`kettleheat log.json`) is specified but untested — minor coverage gap; existing `main.rs` already implements it and agents are not asked to change I/O.
- Niche tags (`process-kettle`, `element-cycle`) are discoverability notes only (Low).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept — no High/Medium blockers (ChatGPT) | **Agree** | Full artifact audit; oracle 1.000; spec↔test alignment in §5 |
| 2 | Tags are niche; optional broader tags (ChatGPT / Harbor `entire-report.txt:240-262`) | **Agree** (Low only) | `task.toml:12` — 6 domain-specific tags; advisory discoverability |
| 3 | Non-canonical Rust base image warning (Harbor `entire-report.txt:265-282`) | **Disagree** | `environment/Dockerfile:4` uses `rust:1.85-slim@sha256:9f841bbe…` — exact match to canonical list in `docs/guidelines/dockerfxile.md:12` |
| 4 | test.sh should add `set -e` (Harbor suggestion `entire-report.txt:289-331`) | **Agree** (Low only) | `tests/test.sh:2` uses `set -uo pipefail`; reward.txt written on all paths (`tests/test.sh:8-24`); suggestion not a blocker |
| 5 | File-path CLI argument never tested (Harbor test quality `entire-report.txt:407-439`) | **Agree** (Low only) | `tests/test_outputs.py:38-47` feeds stdin only; `environment/repo/src/main.rs:15-23` implements file path; instruction says preserve CLI |
| 6 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` PASS | **Agree** | `entire-report.txt:203-204`; spot-checked deferral, freeze, horizon, error paths |
| 7 | Instruction sufficiency PASS — agent failures are implementation bugs | **Agree** | `entire-report.txt:148-178`; curated fixture names mirror spec sections; agents reached 93–98% test pass |
| 8 | Difficulty HARD with GPT 0% / Claude 40% | **Agree** | `entire-report.txt:25-27`; best-model ≤20% supports `hard` per `docs/guidelines/difficulty.md` |
| 9 | `#14` unpinned pip (automated baseline) | **Disagree** | `environment/requirements.lock:1-12` — all packages `==` with `--hash=`; Dockerfile installs via `--require-hashes -r requirements.lock` |
| 10 | `#20` pytest not in Dockerfile (automated baseline) | **Disagree** | `requirements.lock:9-10` includes `pytest==8.4.1`; baked at image build (`environment/Dockerfile:23-27`); `tests/test.sh:18` only runs pytest |
| 11 | `#36` rubric negative phrasing fail (automated baseline) | **Disagree** | `entire-report.txt:456-461` — negatives use `-N` with active bad-behavior verbs (`keeps`, `evaluates`, `lets`, `hard-codes`); no `Agent does not …, +1` pattern |
| 12 | Non-milestone task uses milestone rubric format | **Disagree** | `task.toml:9` `number_of_milestones = 0`; rubric is flat list with **no** `# Rubric N` headers (`entire-report.txt:443-461`); per `docs/guidelines/submission-export-format.md:63-64` this is correct |
| 13 | Rubric positive total exceeds 40-pt non-milestone cap | **Agree** (Low only) | Sum of positives in `entire-report.txt:443-455` = 43; `docs/guidelines/rubrics.md:31` recommends 10–40; Low severity |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 2 prose paragraphs + compact schema/bullets | `instruction.md:1-23` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Conversational task framing; defers detail to linked spec | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | One JSON code block; no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT to fix, not edit order | `instruction.md:1-3` |
| 5 | CHECK | No hints or solving strategies | No walkthrough; spec is normative contract | `instruction.md:3` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, output schema, error contract, spec pointer | `instruction.md:1-23` |
| 8 | CHECK | Instruction is interesting | Real control-logic / state-machine engineering | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app`, `/app/docs/spec.md`, `/app/src` | `instruction.md:1-3` |
| 11 | CHECK | Task name does not appear in instruction.md | `tbrain-process-kettle-cycle` absent | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1` etc. in lockfile with hashes | `environment/requirements.lock:1-12`, `environment/Dockerfile:23-27` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Canonical rust digest | `environment/Dockerfile:4` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY limited to env paths | `environment/Dockerfile:6-7,34` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken stub in control.rs; spec is contract not answer key | `environment/repo/src/control.rs:37-80` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in lockfile; test.sh runs pytest only | `environment/Dockerfile:23-27`, `tests/test.sh:18` |
| 21 | CHECK | Oracle passes consistently | Mean reward 1.000 (1/1) | Harbor oracle run 2026-06-28 |
| 22 | CHECK | Oracle does not require internet | Local patch + cargo build | `solution/solve.sh:1-6` |
| 23 | CHECK | Oracle is reflective of instruction | Patches control.rs, rebuilds binary | `solution/solve.sh:4-6`, `solution/fix.patch` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical 0/1 block + WORKDIR guard | `tests/test.sh:4-24` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | Writes 0 or 1 | `tests/test.sh:20-24` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to instruction/spec | §5 below; `entire-report.txt:203-204` |
| 28 | CHECK | Tests check correctness, not just format | Exact ledger equality + differential reference | `tests/test_outputs.py:448-601` |
| 29 | CHECK | Tests verify behavior, not implementation | Black-box binary invocation | `tests/test_outputs.py:38-47` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact JSON ledger match is spec-required deterministic output | `tests/test_outputs.py:455` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` documented | `tests/test_outputs.py:448-601` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 negatives | `entire-report.txt:456-461` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use ±1,2,3,5 | `entire-report.txt:443-461` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 19 Agent lines | `entire-report.txt:443-461` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific control-law trace checks | `entire-report.txt:443-455` |
| 36 | CHECK | Rubric criteria use positive language | Negatives use `-N` for bad behavior | `entire-report.txt:456-461` |
| 37 | CHECK | Rubric does not reference /tests/ or pytest | No test refs | `entire-report.txt:443-461` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No metadata refs | `entire-report.txt:443-461` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:443-461` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean layout | task root |
| 42 | CHECK | author_name and author_email present | Both set | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | difficulty, category, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Rust control/simulation task | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best 0%, worst 40% | `entire-report.txt:25-27` |
| 46 | UNCHECK | steps/ layout present (milestone) | N/A — regular task | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:5` |
| 51 | CHECK | Solution not accessible in environment | solution/ excluded | `environment/.dockerignore:4` |
| 52 | CHECK | Agent cannot trivially modify input data | Inputs are runtime JSON via stdin | `tests/test_outputs.py:38-47` |
| 53 | CHECK | Git repos pinned to specific commit | No unpinned git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model 40% | `entire-report.txt:26-27` |
| 55 | CHECK | Task is not too hard or unfair | Comprehensive spec; agents reached 93–98% on tests | `entire-report.txt:148-194` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / spec) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Deferred turn-off at `lastOn + minRun` | `test_curated_fixture[deferred_turn_off_fires]` | covered | `tests/test_outputs.py:315-318,390-393` |
| Boundary-exact sample at deferral boundary | `boundary_exact_sample_*`, `deferred_turn_off_boundary_exact_off` | covered | `tests/test_outputs.py:321-324,358-366` |
| Deferred turn-on at `lastOff + minRest` | `deferred_turn_on_fires` | covered | `tests/test_outputs.py:326-329` |
| `off` mode overrides `minRun` | `off_mode_overrides_min_run` | covered | `tests/test_outputs.py:331-334` |
| Freeze suppresses switching; clocks restart at `endfreeze` | `freeze_restart_clocks` | covered | `tests/test_outputs.py:336-340` |
| `off` during freeze applies at `endfreeze` | `off_during_freeze_applies_at_endfreeze` | covered | `tests/test_outputs.py:342-346` |
| Deferral cancellation mid-pulse | `off_deferral_cancelled_*`, `on_deferral_cancelled_*` | covered | `tests/test_outputs.py:348-356` |
| Horizon truncation + `final` semantics | `horizon_truncates_open_interval` | covered | `tests/test_outputs.py:368-371` |
| `off` then `on` re-enable respects `minRest` | `off_then_on_reenable_respects_min_rest` | covered | `tests/test_outputs.py:373-376` |
| Zero-length intervals not emitted | differential + curated shape checks | covered | `tests/test_outputs.py:74`, `ref_run` L284-294 |
| Malformed input → stderr error, empty stdout, nonzero | `test_error_inputs[*]` | covered | `tests/test_outputs.py:464-498` |
| Random valid logs match reference | `test_differential_random[*]` | covered | `tests/test_outputs.py:573-601` |
| CLI file-path argument mode | — | gap (minor) | `instruction.md:1`; `main.rs:15-23`; no test exercises file arg |
| Output schema (`intervals`, `ontime`, `final`) | `assert_ledger_shape` on all curated tests | covered | `tests/test_outputs.py:67-81,454` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #11, §5 |
| `task.toml` | #42-45, #46-49 N/A, rubric format |
| `environment/Dockerfile` | #14-15, #20, canonical base |
| `environment/requirements.lock` | #14, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/repo/docs/spec.md` | §5, #17, #27 |
| `environment/repo/src/control.rs` | #17 (broken stub) |
| `environment/repo/src/main.rs` | §5 file-path gap |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | §3, §7, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tbrain-process-kettle-cycle
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — pip install line lacks inline == (false positive; lockfile pins)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Supports hard tier |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Worst model |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle 1.000 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium (worst) / hard (best ≤20%) |
| Declared difficulty | hard |
| Tier match (#45) | yes — defensible under difficulty.md best-model rule |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; name matches export |
| 1 Instruction | ☑ | Concise; absolute paths; spec pointer |
| 2 Environment | ☑ | Canonical digest-pinned Rust; tmux/asciinema; hash-pinned wheels |
| 3 Oracle | ☑ | Patch + rebuild; oracle 1.000 |
| 4 Verifiers | ☑ | reward.txt canonical; no runtime installs; behavior tests |
| 5 Metadata | ☑ | `number_of_milestones = 0`; tags applicable |
| 6 Rubric | ☑ | Flat non-milestone format; 6 negatives; 43 positive pts (Low note) |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency PASS; no cheating |
| 8 Novelty & fairness | ☑ | Multi-step control logic; anti-cheat closed |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The offline Rust environment is well set up, the spec in `docs/spec.md` is thorough on the hard corners (deferred boundaries, freeze semantics, horizon truncation), and the verifier design is excellent — curated fixtures pin each edge case and the randomized differential against an independent reference makes shortcut solutions very unlikely. Oracle passes cleanly and agent pass rates look right for hard difficulty. I didn't find any blocking spec gaps, environment issues, or rubric format problems. Optional polish if you revisit later: broaden a couple of niche tags for discoverability, trim rubric positives from 43 to ≤40, or add one test that exercises the file-path CLI argument.

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
