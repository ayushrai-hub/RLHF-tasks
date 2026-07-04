# Terminus Review Report: incarceration-trends-cleaning

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 100% 3/3; local Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Strong R data-cleaning task with a normative `OUTPUT_CONTRACT.md`, independent R verifier recomputation on public and hidden data, digest-pinned offline environment, and rubric within cap (28 positive pts). ChatGPT Accept is supported. Harbor export “NEEDS REVISION” for agent timeout and automated audit failures (#14 pip, #31 docstrings, #41 stray file) are false positives on manual re-audit. Non-milestone rubric is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — not wrongly formatted as a multi-milestone rubric.

**Insights (concise):**

- Platform rubric: 28/40 positive pts, 8 distinct negatives, flat non-milestone format (no `# Rubric N` headers).
- Automated audit #14 fails multiline `pip install` despite `pytest==8.4.1` / `pytest-json-ctrf==0.3.5` on continuation lines.
- All 16 `test_*` functions have docstrings; automated #31 fail is false positive.
- Worst-model 60% (GPT-5.5); Claude Opus 4.8 100%; timeout gate 1/10 — not too easy (#54 passes).
- `task.toml` `difficulty = "hard"` vs platform `MEDIUM` is informational only — never blocks (#45 CHECK).
- Optional polish only: trim tags from 7→6; consider raising agent timeout above verifier (900s vs 1200s) — not blocking.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High/Medium severity; structurally strong; Accept (ChatGPT) | **Agree** | `task.toml:27` `allow_internet=false`; `environment/Dockerfile:1` digest-pinned; `.dockerignore:16-17` excludes solution/tests; `tests/test_outputs.py:196-292` independent recomputation D1/D2; hidden variant `tests/test.sh:28-48` |
| 2 | Output contract detailed including reconciliation, FIPS, DL pooling (ChatGPT) | **Agree** | `environment/OUTPUT_CONTRACT.md:9-98`; `instruction.md:5` normative reference |
| 3 | Rubric 28 positive pts, ≥3 negatives (ChatGPT) | **Agree** | `entire-report.txt:296-315`; sum +lines = 28; 8 negative lines |
| 4 | Optional: trim tags 7→6 (ChatGPT Low) | **Agree (Low only)** | `task.toml:12` seven tags; validator WARNING only — not a blocker |
| 5 | Optional: agent timeout 900s < verifier 1200s (ChatGPT Low) | **Agree (Low only)** | `task.toml:17-20`; `entire-report.txt:38` timeout gate ✅ 1/10; not blocking per difficulty gate |
| 6 | Dockerfile digest-pinned canonical Python + R via apt (ChatGPT) | **Agree** | `environment/Dockerfile:1-10` `@sha256:01f42367…`; comment on line 1 |
| 7 | Harbor REVIEW REPORT: NEEDS REVISION — increase agent timeout (export) | **Disagree as blocker** | `entire-report.txt:238-242`; 1/10 agent timeout under gate; other Terminus reviews treat verifier>agent as informational when gate passes |
| 8 | Harbor: tags exceed 6 (export WARNING) | **Agree (Low only)** | `task.toml:12`; `docs/task-requirements.md` 3–6 recommended — validator WARNING, not error |
| 9 | Test quality review ACCEPT / robust (export) | **Agree** | `entire-report.txt:249-281`; hidden-data + full recomputation verified in `tests/test_outputs.py` |
| 10 | LLMaJ behavior_in_task_description / behavior_in_tests PASS | **Agree** | `entire-report.txt:99-100`; cross-checked `OUTPUT_CONTRACT.md` vs verifier checks A1–H2 |
| 11 | Instruction sufficiency PASS — agent failures are bugs not spec gaps (export) | **Agree** | `entire-report.txt:63-95`; failures on state normalization order / terminal wedging, not missing spec |
| 12 | Audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:12-14` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; auditor line-scans `RUN pip install` without continuation lines |
| 13 | Review script #31 missing test docstrings | **Disagree** | All 16 `test_*` at `tests/test_outputs.py:429-506` have docstrings |
| 14 | Review script #41 stray `audit-report.md` | **Disagree as task defect** | File created by local `./scripts/terminus audit`; not author submission content |
| 15 | Non-milestone task uses milestone rubric format (user concern) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; platform rubric has no `# Rubric N` headers — flat list per `docs/guidelines/rubrics.md:66` |
| 16 | Rubric line “group mean” vs DerSimonian–Laird in contract (manual) | **Partially agree (Low only)** | `entire-report.txt:304` says “group mean”; `OUTPUT_CONTRACT.md:57-85` specifies DL pooling — rubric trace imprecision, not pytest/spec blocker |
| 17 | Author fixed rounding basis in OUTPUT_CONTRACT (Comments for Reviewer) | **Agree** | `OUTPUT_CONTRACT.md:93-95` “formed from the study estimates that are themselves built on the already rounded panel rates”; matches verifier `tests/test_outputs.py:101-102,147` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 paragraphs, ~196 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer-style problem statement, not synthetic walkthrough | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal + contract pointer | `instruction.md` |
| 5 | CHECK | No hints/strategies | No algorithm walkthrough; contract in separate env doc | `instruction.md:5` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Goal + normative `OUTPUT_CONTRACT.md` with schemas, algorithms, rounding | `instruction.md:5`; `OUTPUT_CONTRACT.md` |
| 8 | CHECK | Interesting | Real county incarceration panel cleaning + meta-analysis | task content |
| 9 | UNCHECK | Unique | Corpus dedup not verifiable from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/environment/...` throughout | `instruction.md:1,3,5` |
| 11 | CHECK | Task name not in instruction | Clean | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local CSV data only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:12-14` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY only env subtree | `environment/Dockerfile:19-21` |
| 17 | CHECK | No ground truth in env | Contract is spec; no expected CSVs in image | `environment/Dockerfile`; `.dockerignore` |
| 18 | CHECK | No privileged Docker | Standard RUN/COPY | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest/Rscript only | `environment/Dockerfile:12-14`; `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:32` |
| 22 | CHECK | Oracle no network | `solve.sh` writes R script and runs Rscript | `solution/solve.sh:152-153` |
| 23 | CHECK | Oracle derives answer | Reads state CSVs, reconciles, DL-pools at runtime | `solution/solve.sh:14-149` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail | `tests/test.sh:56-61` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All graded behaviors in instruction + OUTPUT_CONTRACT | `OUTPUT_CONTRACT.md`; checks A1–H2 |
| 28 | CHECK | Tests check correctness | D1/D2 full recomputation match | `tests/test_outputs.py:265-292` |
| 29 | CHECK | Behavior not implementation grep | Correctness via recomputation; H2 anti-cheat only on public pass | `tests/test_outputs.py:325-331` |
| 30 | CHECK | No brittle string matching | Numeric tolerance `same_num` 1e-6 | `tests/test_outputs.py:179-181` |
| 31 | CHECK | Informative test docstrings | All 16 tests documented | `tests/test_outputs.py:429-506` |
| 32 | CHECK | ≥3 negative rubric criteria | 8 negatives | `entire-report.txt:308-315` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines compliant | `entire-report.txt:296-315` |
| 34 | CHECK | Agent …, ±N format | 20 Agent lines | `entire-report.txt:296-315` |
| 35 | CHECK | Rubric detailed; positive cap | 28 positive pts ≤40 | rubric sum |
| 36 | CHECK | Positive language in rubric | Bad behavior on negative lines; good on positive lines | `entire-report.txt:296-315` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:296-315` |
| 38 | CHECK | Rubric no instruction.md refs | Clean | `entire-report.txt:296-315` |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | `entire-report.txt:296-315` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | No stray parent files | No jobs/, dev README in submission tree | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/category applicable | data-processing + R tags fit; 7 tags is style warning only | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | hard declared; platform medium — informational | `task.toml:8`; `entire-report.txt:22` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — non-milestone | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile`; `.dockerignore:17` |
| 51 | CHECK | Solution not in env | solution/ excluded | `.dockerignore:16` |
| 52 | CHECK | Agent cannot trivially hardcode | Hidden data variant + H2 embed scan + D1/D2 recompute | `tests/test.sh:28-48`; `tests/generate_hidden_data.py` |
| 53 | CHECK | Git clones pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:27-28` |
| 55 | CHECK | Not too hard/unfair | Instruction sufficiency PASS; failures are implementation/terminal bugs | `entire-report.txt:63-95` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Two output CSVs in `/app/environment/outputs` | A1 / `test_output_files_exist` | covered | `OUTPUT_CONTRACT.md:3-5`; `tests/test_outputs.py:198-202` |
| Panel column order and schema | B1 / `test_panel_columns` | covered | `OUTPUT_CONTRACT.md:31-35`; `tests/test_outputs.py:204-208` |
| Summary column order and schema | B2 / `test_summary_columns` | covered | `OUTPUT_CONTRACT.md:47-49`; `tests/test_outputs.py:210-214` |
| FIPS five-digit zero-padded text | B3 / `test_fips_format` | covered | `OUTPUT_CONTRACT.md:37`; `tests/test_outputs.py:216-219` |
| One row per county-year | B6 / `test_one_row_per_county_year` | covered | `OUTPUT_CONTRACT.md:31`; `tests/test_outputs.py:233-237` |
| Latest non-blank field reconciliation | D1, G1 | covered | `OUTPUT_CONTRACT.md:9-17`; `tests/test_outputs.py:54-66,305-309` |
| Per-county urbanicity mode + canonical labels | B5, G2 | covered | `OUTPUT_CONTRACT.md:19-27`; `tests/test_outputs.py:226-231,305-313` |
| Rate formula, blanks, one-decimal rounding | C1, D1 | covered | `OUTPUT_CONTRACT.md:40-42,93-94`; `tests/test_outputs.py:34-37,239-247` |
| Truncated integer counts, blanks preserved | C1, D1 | covered | `OUTPUT_CONTRACT.md:38-39`; `tests/test_outputs.py:242-243` |
| DerSimonian–Laird pooling by state | D2, C2 | covered | `OUTPUT_CONTRACT.md:53-89`; `tests/test_outputs.py:117-156,250-263,282-292` |
| Summary counts sum to panel | E1 / `test_outputs_internally_consistent` | covered | `OUTPUT_CONTRACT.md:51`; `tests/test_outputs.py:294-303` |
| No hardcoded public totals in analysis.R | H2 / `test_no_embedded_answers` | covered | public pass only; `tests/test_outputs.py:325-331` |
| Generalization beyond public corpus | hidden variant D1/D2 | covered | `tests/test.sh:28-48`; `tests/generate_hidden_data.py` |
| State two-letter uppercase format | B4 / `test_state_format` | covered | implied by source data (`CA.csv`); enforced consistently in verifier `trimws(r_state)` + D1 exact match |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, spec alignment |
| `environment/OUTPUT_CONTRACT.md` | #7, #17, #27, spec alignment |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `task.toml` | #43, #44, #45, tags/timeout |
| `solution/solve.sh` | #21, #23, oracle |
| `tests/test.sh` | #20, #24, hidden variant |
| `tests/test_outputs.py` | #27-31, verifier logic |
| `tests/generate_hidden_data.py` | #52, anti-cheat |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate incarceration-trends-cleaning/
Summary: 0 error(s), 2 warning(s), 3 info
Warnings: tags 7 (recommended 3-6); pip pin heuristic on multiline RUN
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100.0% (5/5) | |
| terminus-gpt5-5 | 60.0% (3/5) | 1 timeout, 1 other |
| oracle | 100.0% (3/3) | platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — CHECK |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone R task; report matches folder |
| 1 Instruction | ☑ | Concise prompt + normative OUTPUT_CONTRACT in env |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema, no tests/solution in image |
| 3 Oracle | ☑ | Derives outputs; platform 100%; static review confirms |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, hidden variant, full recompute |
| 5 Metadata | ☑ | Complete; 7 tags warning only |
| 6 Rubric | ☑ | Flat non-milestone format; 28/40; 8 negatives |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency PASS; timeout gate PASS; no >80% easy |
| 8 Novelty & fairness | ☑ | Multi-step R pipeline; anti-cheat closed |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The split between a short instruction and the detailed `OUTPUT_CONTRACT.md` works well, the Dockerfile is pinned and offline-safe, and the verifier independently recomputes both outputs on public and hidden data — that anti-cheating design is solid. Oracle passes cleanly and agent rates look right for the difficulty band. I didn’t find any spec gaps or blocking issues. Optional polish if you want: drop one tag to get back to six, and consider bumping the agent timeout above the verifier window on this R-heavy task.

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

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review incarceration-trends-cleaning/ --report entire-report.txt`._
