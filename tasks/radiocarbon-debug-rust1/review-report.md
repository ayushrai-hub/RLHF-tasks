# Terminus Review Report: `radiocarbon-debug-rust1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Metadata Issues

**Decision (concise):** Technically strong Rust radiocarbon debugging task — digest-pinned offline env, held-out Python-reference tests, anti-cheat SHA-256 guard, valid flat rubric (35/40 positive pts), and hard-tier agent calibration (0% GPT-5.5, 60% Claude Opus 4.8). **Real blockers are metadata only:** `category` should be `debugging` (not `scientific-computing`) and `codebase_size` must be lowercase `small`. Automated audit failures on pip pinning (#14), pytest-in-image (#20), and `audit-report.md` stray file (#41) are **false positives** overturned on manual proof. Test docstrings, LICENSE removal, docs polish, and rubric phrasing are **recommended polish, not Revise drivers**.

**Insights (concise):**

- Platform rubric uses optional single `# Rubric 1` header — correct for `number_of_milestones = 0`; **not** a milestone-format violation (`docs/guidelines/rubrics.md:66`, `submission-export-format.md:63`).
- `pytest==8.3.4` baked into image via hash-locked `requirements.lock`; `test.sh` does not install at runtime.
- All 13 `test_*` functions have highly descriptive names satisfying portal #31 OR clause; docstrings are CI polish (`validate` warns) but not a fairness blocker.
- Baseline emits one `unused variable: reservoir_shift` warning (`calibrate.rs:843`) — this is the bug under test; `instruction.md:3` requires warning-free builds.
- Oracle applies algorithmic patches (`calibrate.patch`, `main.patch`) — not hardcoded answers.
- LLMaJ instruction-sufficiency FAIL is informational; linked docs are declared the full contract per `instruction.md:3`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | Medium | Metadata Issues | #44 | `category` is `scientific-computing` but primary activity is Rust bug-fixing against a documented contract | `task.toml:7` `category = "scientific-computing"`; folder `radiocarbon-debug-rust1`; `instruction.md:1` "scientific model and validation behavior do not fully match the documented contract"; `docs/task-type-taxonomy.md:29` "Finding/fixing bugs → debugging"; author difficulty text "Rust debugging" (`entire-report.txt:6`) | Set `category = "debugging"` |
| 2 | Medium | Metadata Issues | #44 | `codebase_size` uses non-canonical title-case | `task.toml:14` `codebase_size = "Small"`; `docs/task-requirements.md:26,42` enum values are lowercase `minimal` / `small` / `large`; 25 files under `environment/task_file/` → `small` tier (20+) | Change to `codebase_size = "small"` |

*Two Medium findings in metadata → Revise per severity rules.*

**Not blockers (polish only):**

| Item | Severity | Why not blocking |
|------|----------|------------------|
| 13 test docstrings missing | Low | Portal #31 passes on informative names (`test_heldout_precision_and_tie_breaking_rules`, etc.); `writing-tests.md:47` recommends docstrings but OR clause governs checkbox |
| `environment/task_file/LICENSE` | Low | No Terminus doc rule forbids LICENSE; 1-line fixture file; portal reviewer preference only |
| Instruction/docs styling | Low | Accurate API-contract docs; subjective tone concern, not spec-test gap |
| Rubric "does not add external dependencies" phrasing | Low | Single Medium rubric-style item (#36); 35/40 pts valid; rephrase optional |
| `# Rubric 1` header on non-milestone task | — | Explicitly allowed: optional single header when `number_of_milestones = 0` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `category` should be `debugging` not `scientific-computing` (ChatGPT / portal reviewer / `entire-report.txt:1`) | **Agree** | `task.toml:7`; task name `radiocarbon-debug-rust1`; taxonomy primary activity = finding/fixing bugs; scientific domain is context, not primary category |
| 2 | `codebase_size` should be lowercase `small` (ChatGPT / Harbor review / `entire-report.txt:142-157`) | **Agree** | `task.toml:14` `codebase_size = "Small"`; schema example `codebase_size = "minimal"` at `task-requirements.md:42` |
| 3 | All 13 tests missing docstrings (ChatGPT Medium) | **Partially agree (Low only)** | `tests/test_outputs.py:1272+` — no `"""` after any `def test_`; `./scripts/terminus validate` warns on all 13; but names like `test_heldout_curve_mixture_sequence_conditioning` satisfy portal #31 OR clause |
| 4 | Remove LICENSE from small codebase (ChatGPT / portal reviewer) | **Partially agree (Low only)** | `environment/task_file/LICENSE` exists (1 line); no rule in `docs/`; cleanup preference, not a Terminus blocker |
| 5 | README/instruction docs polish (ChatGPT Medium) | **Partially agree (Low only)** | `environment/task_file/README.md` is 4 lines; `instruction.md` is terse but points to `docs/SPEC.md`; accurate, not unfair |
| 6 | Rubric rephrase "does not add external dependencies" (ChatGPT Low) | **Agree (Low only)** | `entire-report.txt:296` `Agent does not add external dependencies to Cargo.toml…, +2` |
| 7 | Rubric shape fine: 35 pts, ≥3 negatives (ChatGPT) | **Agree** | `./scripts/terminus rubric-points entire-report.txt` → 35 positive, 4 negatives (-3,-5,-3,-5) |
| 8 | Non-milestone task in milestone rubric format (`# Rubric 1`) (user query) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; `rubrics.md:66` "Non-milestone: flat list (`# Rubric 1` optional; no `# Rubric 2+`)"; export has only `# Rubric 1`, no `# Rubric 2` |
| 9 | Dockerfile FROM not canonical (Harbor review `entire-report.txt:164-183`) | **Disagree as blocker** | `environment/Dockerfile:1` digest-pinned `rust:1.85-slim@sha256:9f841…`; tmux + asciinema present; functional offline Rust build |
| 10 | pytest not in Dockerfile (automated audit #20) | **Disagree** | `environment/requirements.lock:9` `pytest==8.3.4` + sha256 hash; `Dockerfile:17` `--require-hashes --no-deps`; `test.sh:14` runs pytest only |
| 11 | pip deps unpinned (automated audit #14) | **Disagree** | `requirements.lock` uses `package==version` + `--hash=sha256:` per line; `Dockerfile:17` `--require-hashes --no-deps` |
| 12 | `audit-report.md` stray file (#41 automated review) | **Disagree** | `audit-report.md` is local reviewer output from `./scripts/terminus audit`, not a task submission artifact |
| 13 | Instruction sufficiency FAIL — pre-existing warning unfair (entire-report `entire-report.txt:85`) | **Disagree as spec gap** | `cargo build` emits `warning: unused variable: reservoir_shift` at `calibrate.rs:843`; `instruction.md:3` requires "finish without warnings"; fixing this IS the reservoir-wiggle bug |
| 14 | Task NEEDS REVISION per Harbor review (codebase_size only) | **Partially agree** | Harbor correctly flags casing; category fix also needed; core task quality is high |
| 15 | Test quality ACCEPT (entire-report `entire-report.txt:249`) | **Agree** | Held-out reference tests, tight tolerances, comprehensive operation coverage |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 2 paragraphs, ~124 words | `instruction.md` |
| 2 | UNCHECK | Natural prompt tone | Terse instruction; 11 fragmented operation docs read synthetic | `instruction.md`, `docs/` |
| 3 | CHECK | No excessive markdown | Plain prose in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step | No walkthrough patterns | `instruction.md` |
| 5 | CHECK | No hints/strategies | WHAT not HOW | `instruction.md` |
| 6 | CHECK | No design-doc tables | No input→output tables in instruction | `instruction.md` |
| 7 | UNCHECK | Well specified | Goal clear but debugging context thin vs doc depth | `instruction.md` |
| 8 | CHECK | Interesting | Real radiocarbon calibration debugging | task content |
| 9 | UNCHECK | Unique | Cannot verify vs corpus | — |
| 10 | CHECK | Absolute paths | `/app/task_file/...` throughout | `instruction.md:1,3` |
| 11 | CHECK | No task name in instruction | Name absent | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline env; `CARGO_NET_OFFLINE=true` | `Dockerfile:22` |
| 14 | CHECK | Pinned pip deps | Hash-locked requirements.lock | `environment/requirements.lock`, `Dockerfile:17` |
| 15 | CHECK | FROM digest-pinned | `@sha256:9f841…` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context only | COPY task_file only | `environment/Dockerfile:20` |
| 17 | CHECK | No ground truth in env | Bugs in source, not answer keys | `environment/task_file/src/` |
| 18 | CHECK | No dangerous Docker | No privileged/SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in requirements.lock; test.sh no install | `Dockerfile:17`, `test.sh:14` |
| 21 | UNCHECK | Oracle passes | Docker unavailable locally; not executed | oracle run failed |
| 22 | CHECK | Oracle no internet | patch + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Patches fix algorithms, no echo | `solution/patches/` |
| 24 | CHECK | reward.txt canonical | Writes 0 then 1/0 after pytest | `tests/test.sh:11-19` |
| 25 | CHECK | Same verifier logic | No /oracle branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned | All 11 ops + CLI + Cargo contract tested | `tests/test_outputs.py`, LLMaJ pass |
| 28 | CHECK | Tests check correctness | Python reference implementation comparison | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | Runs binary, compares JSON output | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string match | Numeric tolerance checks | `tests/test_outputs.py` |
| 31 | CHECK | Test docstrings or names | 13 descriptive `test_*` names | `tests/test_outputs.py:1272+` |
| 32 | CHECK | ≥3 rubric negatives | 4 negatives | `entire-report.txt:297-300` |
| 33 | CHECK | Rubric scores in set | All ±1,2,3,5 | `entire-report.txt:281-300` |
| 34 | CHECK | Rubric format | 20 `Agent …, ±N` lines | `entire-report.txt:281-300` |
| 35 | CHECK | Rubric detailed; ≤40 pts | 35 positive pts | `./scripts/terminus rubric-points` |
| 36 | UNCHECK | Positive rubric phrasing | One "does not add" line with +2 | `entire-report.txt:296` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:281-300` |
| 38 | CHECK | Rubric no instruction.md refs | References env docs, not instruction.md | `entire-report.txt:281` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:281-300` |
| 40 | CHECK | Required files | All present | task tree |
| 41 | UNCHECK | Clean parent directory | LICENSE in small codebase (reviewer preference) | `environment/task_file/LICENSE` |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Present | `task.toml` |
| 44 | UNCHECK | Tags/category match | Wrong category; codebase_size case | `task.toml:7,14` |
| 45 | CHECK | Difficulty field | `hard` in task.toml | `task.toml:6` |
| 46 | UNCHECK | Milestone layout | N/A | `task.toml:10` |
| 47 | UNCHECK | solveN.sh | N/A | — |
| 48 | UNCHECK | test_mN.py | N/A | — |
| 49 | UNCHECK | Milestone scope | N/A | — |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible | .dockerignore excludes solution/tests | `environment/.dockerignore:17-20` |
| 52 | CHECK | Input not trivially mutable | SHA256 enforced | `tests/test_outputs.py:12,1275` |
| 53 | CHECK | Git pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:25-26` |
| 55 | UNCHECK | Not unfair | Hard tier; fully documented in linked docs but very punishing all-or-nothing reward | agent stats, `instruction.md:3` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 42, 43, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 2, 7, 9, 21, 36, 41, 44, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| All 11 operations per SPEC.md | `test_sample_cases_match_documented_model`, held-out tests | covered | `tests/test_outputs.py` |
| cases.json SHA-256 immutable | `test_sample_cases_match_documented_model` | covered | `test_outputs.py:1275` |
| CLI rejects extra positional args | `test_cli_rejects_extra_positional_arguments` | covered | `test_outputs.py:1281` |
| std-only Cargo.toml | `test_cargo_toml_keeps_std_only_contract` | covered | `test_outputs.py:2466` |
| Build without warnings | `build_binary()` in all build tests | covered | `test_outputs.py:1213` |
| Numeric tolerance 2e-8 | all comparison tests | covered | `ATOL`/`RTOL` at `test_outputs.py:14-15` |
| Error handling per-op | `test_heldout_error_handling_and_incoherent_replicates` | covered | `test_outputs.py:2007` |
| HPD / tie-breaking | `test_heldout_precision_and_tie_breaking_rules` | covered | `test_outputs.py:2426` |
| Phase sequence / scale | `test_heldout_scale_stress_sequence_and_phase` | covered | `test_outputs.py:2191` |
| curve_mixture_sequence (missing op) | `test_heldout_curve_mixture_sequence_conditioning` | covered | `test_outputs.py:1550` |
| phase_sequence (missing op) | `test_heldout_ordered_phase_sequence_boundaries` | covered | `test_outputs.py:1856` |

No spec-test gaps found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | blockers 1–2, #44, #45 |
| `instruction.md` | #1–7, spec alignment |
| `environment/Dockerfile` | #14–#15, #20 |
| `environment/requirements.lock` | #14, #20 |
| `environment/task_file/LICENSE` | #41 (polish) |
| `environment/task_file/src/calibrate.rs` | warning proof, spec alignment |
| `environment/task_file/docs/SPEC.md` | spec alignment |
| `tests/test_outputs.py` | #27–#31, spec alignment |
| `tests/test.sh` | #20, #24–#26 |
| `solution/solve.sh` | #22–#23 |
| `entire-report.txt` | rubric, agent stats, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate radiocarbon-debug-rust1/
Summary: 0 error(s), 14 warning(s), 3 info
All 14 warnings: missing test docstrings (13 functions) + module docstring
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | 1 timeout, 4 other |
| terminus-claude-opus-4-8 | 60.0% (3/5) | hard tier |
| oracle | 100.0% (3/3) | per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test pass rates lowest on `test_heldout_scale_stress_sequence_and_phase` (4/10) — edge-case hardness, not spec gap.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `radiocarbon-debug-rust1`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise; points to SPEC.md contract; absolute paths |
| 2 Environment | ☑ | Digest-pinned Rust; tmux/asciinema; hash-locked pytest venv; no tests/solution COPY |
| 3 Oracle | ☑ | Patch-based; not hardcoded; Docker unavailable for local run |
| 4 Verifiers | ☑ | 13 tests; reference implementation; reward block canonical; no runtime installs |
| 5 Metadata | ☐ | **Blockers:** category + codebase_size casing |
| 6 Rubric | ☑ | 35/40 pts; 4 negatives; optional `# Rubric 1`; one phrasing polish item |
| 7 LLMaJ & agent evidence | ☑ | Hard tier appropriate; instruction sufficiency FAIL is informational |
| 8 Novelty & fairness | ☑ | Multi-bug Rust debug; anti-cheat solid; warning-free build is stated requirement |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the offline Rust setup, held-out reference tests, and anti-cheat design are in great shape, and the difficulty calibration looks right for hard tier. Two quick metadata fixes before we can accept: set `category = "debugging"` (this is primarily a bug-fix task, not pure scientific computing) and change `codebase_size = "Small"` to lowercase `"small"`. While you're in there, optional polish: add one-line docstrings to the 13 test functions, drop the extra LICENSE fixture, and rephrase the rubric line about external dependencies into affirmative wording. None of those polish items block the core task quality.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1, 2 |
| Instruction Styling | no (polish only) | — |
| Test Alignment/Coverage Issues | no | — |
| Rubric | no (>40 cap passes; phrasing is Low) | — |
| Pinning Issues | no (#14 false positive) | — |
| Environment | no (#20 false positive) | — |
| Milestones | no (N/A) | — |
| Task Difficulty | no (0% worst model) | — |
