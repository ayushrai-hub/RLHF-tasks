# Terminus Review Report: `radiocarbon-debug-rust`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Metadata Issues, Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Technically strong Rust radiocarbon debugging task — digest-pinned offline env, held-out reference tests, valid flat rubric (35 positive pts), and appropriate hard-tier agent rates. Real blockers are compliance/cleanup: all 13 verifier tests lack required docstrings; `task.toml` category and `codebase_size` need fixes; remove `LICENSE` from the small codebase; soften over-fragmented docs and expand the terse instruction. Automated audit false-positives on pip pinning (#14) and pytest-in-image (#20) were overturned on manual proof.

**Insights (concise):**

- Platform rubric uses optional single `# Rubric 1` header — correct for `number_of_milestones = 0`; not a milestone-format violation.
- `pytest==8.3.4` is baked into the image via hash-locked `requirements.lock`; `test.sh` does not install at runtime.
- Worst-model pass rate 0% (GPT-5.5) with 60% (Claude Opus 4.8) — hard tier appropriate; not too easy.
- Oracle applies algorithmic patches (`calibrate.patch`, `main.patch`) — not hardcoded answers; Docker unavailable locally so oracle run not executed.
- LLMaJ instruction-sufficiency FAIL flags buried spec details (zero-prob grid padding, performance) — documented in linked docs per instruction contract; informational, not a standalone blocker.
- Non-canonical Rust base image is digest-pinned with tmux/asciinema; acceptable per guidelines.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #31 | All 13 `test_*` functions lack docstrings | `tests/test_outputs.py:1272,1281,1300,1428,1550,1704,1789,1856,2007,2191,2298,2426,2466` — no `"""` after any `def test_`; validator warns on all 13; `docs/guidelines/writing-tests.md:47` requires docstrings on every test | Add a one-line docstring to each `test_*` function |
| 2 | Medium | Metadata Issues | #44 | `category` is `scientific-computing` but primary activity is Rust bug-fixing | `task.toml:7` `category = "scientific-computing"`; folder `radiocarbon-debug-rust`; author difficulty text "Rust debugging"; portal reviewer feedback; `docs/task-type-taxonomy.md:15` debugging = "Find, diagnose, fix errors" | Set `category = "debugging"` |
| 3 | Medium | Metadata Issues | #44 | `codebase_size` capitalized | `task.toml:14` `codebase_size = "Small"`; `docs/task-requirements.md:42` example uses lowercase `"minimal"`; portal reviewer feedback | Change to `codebase_size = "small"` |
| 4 | Medium | Metadata Issues | #41 | LICENSE present in small codebase | `environment/task_file/LICENSE` exists (1-line fixture license); `codebase_size = "Small"`; portal reviewer feedback: "licenses should not be present for small/minimal codebase_size" | Delete `environment/task_file/LICENSE` |
| 5 | Medium | Instruction Styling | #2, #7 | Instruction is very terse; `/docs` set is hyper-fragmented and reads synthetic | `instruction.md` — 3 short paragraphs (~124 words); 11 separate operation docs (`CALIBRATE.md`, `HPD.md`, `WIGGLE.md`, …) each with JSON schema blocks; portal reviewer: "hyper-structured… reads like an LLM generated them" | Keep docs accurate but consolidate tone (fewer micro-files or more natural prose); add enough context in `instruction.md` for a debugging task without step-by-step hints |

*Rubric `# Rubric 1` on non-milestone task: **not a blocker** — `docs/guidelines/submission-export-format.md:63` allows optional single `# Rubric 1` when `number_of_milestones = 0`.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | category should be `debugging` not `scientific-computing` (ChatGPT / portal reviewer) | **Agree** | `task.toml:7`; zip name `radiocarbon-debug-rust`; taxonomy primary activity = finding/fixing bugs |
| 2 | `codebase_size` should be lowercase `small` (ChatGPT / entire-report / portal reviewer) | **Agree** | `task.toml:14` `codebase_size = "Small"` |
| 3 | Remove LICENSE for small/minimal codebase (portal reviewer) | **Agree** | `environment/task_file/LICENSE` present; `codebase_size` is small-tier |
| 4 | All 13 tests missing docstrings (ChatGPT) | **Agree** | `tests/test_outputs.py` — 13 `def test_*` with no following docstrings; `./scripts/terminus validate` warns on all 13 |
| 5 | Instruction/docs styling needs cleanup (ChatGPT / portal reviewer) | **Partially agree** | Docs are accurate API-contract style (`SPEC.md`, `CALIBRATE.md`) but 11 fragmented files + terse `instruction.md` create synthetic feel; not a spec-test gap |
| 6 | Author explanations should be 4–6 sentences (ChatGPT Low) | **Agree** | `entire-report.txt` lines 1–23 — explanations are 1–2 sentences each; portal form only |
| 7 | Rubric fine: 35 pts, ≥3 negatives (ChatGPT) | **Agree** | `entire-report.txt:367–387` — 16 positive lines sum to 35; 4 negatives (-3,-5,-3,-5) |
| 8 | Non-milestone task in milestone rubric format (`# Rubric 1`) (user query) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:66` "Non-milestone: flat list (`# Rubric 1` optional; no `# Rubric 2+`)"; export has only `# Rubric 1`, no `# Rubric 2` |
| 9 | Dockerfile FROM not canonical (entire-report warning) | **Disagree as blocker** | `environment/Dockerfile:1` digest-pinned `rust:1.85-slim@sha256:9f841…`; tmux + asciinema installed; functional offline build |
| 10 | pytest not in Dockerfile (automated audit #20) | **Disagree** | `environment/requirements.lock:9` `pytest==8.3.4` with hash; `Dockerfile:17` installs lock into `/opt/venv`; `test.sh:14` runs pytest only, no install |
| 11 | pip deps unpinned (automated audit #14) | **Disagree** | `requirements.lock` uses `package==version` + `--hash=sha256:`; `Dockerfile:17` `--require-hashes --no-deps` |
| 12 | Rubric positive phrasing violation (audit #36) | **Agree** | `entire-report.txt:383` `Agent does not add external dependencies to Cargo.toml…, +2` — negative phrasing with positive score |
| 13 | Instruction sufficiency FAIL — buried spec (entire-report LLMaJ) | **Partially agree** | Zero-prob grid padding in `PHASE.md`/`PHASE_SEQUENCE.md` not in top-level `SPEC.md`; but `instruction.md:3` declares linked docs as full contract; agents reach 9–10/13 tests — hard but documented |
| 14 | Task READY TO USE per Harbor review (entire-report) | **Partially agree** | Core task quality is high; metadata/docstring/styling fixes still required before accept |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 2 paragraphs, ~124 words | `instruction.md` |
| 2 | UNCHECK | Natural prompt tone | Terse instruction + synthetic fragmented docs | `instruction.md`, `docs/SPEC.md`, portal reviewer |
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
| 21 | UNCHECK | Oracle passes | Docker unavailable; not executed locally | oracle run failed |
| 22 | CHECK | Oracle no internet | patch + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Patches fix algorithms, no echo | `solution/patches/` |
| 24 | CHECK | reward.txt canonical | Writes 0 then 1/0 after pytest | `tests/test.sh:11-19` |
| 25 | CHECK | Same verifier logic | No /oracle branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned | All 11 ops + CLI + Cargo contract tested | `tests/test_outputs.py`, LLMaJ pass |
| 28 | CHECK | Tests check correctness | Python reference implementation comparison | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | Runs binary, compares JSON output | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string match | Numeric tolerance checks | `tests/test_outputs.py` |
| 31 | UNCHECK | Test docstrings | 13/13 missing | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 4 negatives | `entire-report.txt:384-387` |
| 33 | CHECK | Rubric scores in set | All ±1,2,3,5 | `entire-report.txt:368-387` |
| 34 | CHECK | Rubric format | 20 `Agent …, ±N` lines | `entire-report.txt:368-387` |
| 35 | CHECK | Rubric detailed; ≤40 pts | 35 positive pts | `entire-report.txt:368-383` |
| 36 | UNCHECK | Positive rubric phrasing | One "does not add" line with +2 | `entire-report.txt:383` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:368-387` |
| 38 | CHECK | Rubric no instruction.md refs | References `docs/SPEC.md` (env doc), not instruction.md | `entire-report.txt:368` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:368-387` |
| 40 | CHECK | Required files | All present | task tree |
| 41 | UNCHECK | Clean parent directory | `LICENSE` in small codebase per reviewer policy | `environment/task_file/LICENSE` |
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
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:31-32` |
| 55 | CHECK | Not unfair | Hard but fully documented in linked docs | `instruction.md:3`, agent stats |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34, 35, 37, 38, 39, 40, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 2, 7, 9, 21, 31, 36, 41, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| All 11 operations per SPEC.md | `test_sample_cases_match_documented_model`, held-out tests | covered | `tests/test_outputs.py` |
| cases.json SHA-256 immutable | `test_sample_cases_match_documented_model` | covered | `test_outputs.py:1275` |
| CLI rejects extra positional args | `test_cli_rejects_extra_positional_arguments` | covered | `test_outputs.py:1281` |
| std-only Cargo.toml | `test_cargo_toml_keeps_std_only_contract` | covered | `test_outputs.py:2466` |
| Numeric tolerance 2e-8 | all comparison tests | covered | reference `compare_results` |
| Error handling per-op | `test_heldout_error_handling_and_incoherent_replicates` | covered | `test_outputs.py:2007` |
| HPD / tie-breaking | `test_heldout_precision_and_tie_breaking_rules` | covered | `test_outputs.py:2426` |
| Phase sequence / scale | `test_heldout_scale_stress_sequence_and_phase` | covered | `test_outputs.py:2191` |
| Test function docstrings | — | **gap** | all 13 `test_*` lack docstrings |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | blockers 2–3, #44, #45 |
| `instruction.md` | blockers 5, #1–7 |
| `environment/Dockerfile` | #14–#15, #20 |
| `environment/requirements.lock` | #14, #20 |
| `environment/task_file/LICENSE` | blocker 4, #41 |
| `environment/task_file/docs/SPEC.md` | blocker 5, spec alignment |
| `tests/test_outputs.py` | blocker 1, #27–#31 |
| `tests/test.sh` | #20, #24–#26 |
| `solution/solve.sh` | #22–#23 |
| `entire-report.txt` | rubric, agent stats, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate radiocarbon-debug-rust/
Summary: 0 error(s), 14 warning(s), 3 info
All 14 warnings: missing test docstrings (13 functions) + module docstring
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | 5 other failures |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 timeouts |
| oracle | 100.0% (3/3) | per export; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `radiocarbon-debug-rust` matches export; regular layout |
| 1 Instruction | ☑ | Terse but valid; styling revision needed |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema, pytest baked |
| 3 Oracle | ☑ | Patch-based; not executed (no Docker) |
| 4 Verifiers | ☑ | Strong coverage; docstrings missing |
| 5 Metadata | ☑ | category, codebase_size, LICENSE issues |
| 6 Rubric | ☑ | 35 pts flat rubric; `# Rubric 1` OK; one phrasing issue |
| 7 LLMaJ & agent | ☑ | Hard tier appropriate; sufficiency concerns informational |
| 8 Novelty & fairness | ☑ | Multi-bug Rust debug; anti-cheat solid |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the offline Rust setup, held-out reference tests, and anti-cheat design are in great shape, and the difficulty calibration looks right for hard tier. Before we can accept, please add a one-line docstring to each of the 13 test functions, fix `task.toml` (`category = "debugging"`, `codebase_size = "small"`), remove the `LICENSE` file from the small codebase, and make the docs feel a bit more like natural project documentation while giving the instruction a little more debugging context. The rubric shape is fine for a non-milestone task; just rephrase the one positive line that says "does not add external dependencies" into affirmative wording.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 2, 3, 4 |
| Instruction Styling | yes | 5 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no (phrasing only; #36 UNCHECK, not disposition driver) | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
