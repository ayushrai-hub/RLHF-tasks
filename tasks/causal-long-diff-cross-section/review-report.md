# Terminus Review Report: causal-long-diff-cross-section

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed (Docker unavailable in review environment) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Structure, anti-cheating, Dockerfile, and verifier deps are solid. One real High blocker: the estimand contract and platform rubric allow baseline-covariate (ANCOVA) adjustment, but the oracle and numeric truth fixtures require change-score / long-difference regression (`y_followup − y_baseline ~ d_treatment`). Agents reasonably chose ANCOVA and failed ~50% off on public/hidden data. Explicitly name the required estimator and align the rubric. Declared `hard` vs platform `medium` is informational only — not a blocker.

**Insights (concise):**

- Computed on public data: change-score 1.134 (0.5% error, passes 8% tol); ANCOVA 1.711 (~50% error, fails) vs truth 1.140.
- Hidden data: change-score passes; ANCOVA ~23% off — matches agent failure pattern in export.
- Synthetic stress case passes both estimators (by construction), so it does not disambiguate method choice.
- Platform rubric positive total 23/40 — under cap; `# Rubric 1` header alone is allowed for non-milestone tasks.
- All nine `test_*` functions have docstrings; automated #31 fail is a false positive (module-level docstring info only).
- `audit-report.md` in task dir is reviewer-generated artifact, not a submission defect.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues; Instruction Styling | #27, #55 | Verifier enforces change-score / long-difference estimator, but instruction + estimand contract only say “treatment effect on follow-up net of baseline,” which reasonably permits ANCOVA (`y_followup ~ d_treatment + y_baseline`). | `environment/docs/estimand_contract.md:1`; `solution/analysis_correct.R:3-4`; `tests/fixtures/public_truth.json` (`tol: 0.08`); computed public ANCOVA 1.711 vs change-score 1.134 vs truth 1.140; `entire-report.txt:56-59,69-74` | State explicitly: compute gain `y_followup − y_baseline` and estimate treatment effect on that change score (long-difference regression). |
| 2 | High | Rubric; Test Alignment/Coverage Issues | #27, #36 | Platform rubric awards +5 for “gain score … **or** including y_baseline as a covariate,” but covariate/ANCOVA fails public/hidden truth checks. | `entire-report.txt:273`; public/hidden ANCOVA vs change-score computation above | Rewrite rubric baseline-adjustment line to require gain-score / long-difference only (remove covariate alternative). |

*No other High or Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Estimand underspecified; tests require change-score not ANCOVA (ChatGPT High) | **Agree** | `estimand_contract.md:1` ambiguous; oracle `analysis_correct.R:3-4` uses gain score; ANCOVA 1.711 vs truth 1.140 (~50% rel err) on public data; agents failed identically per `entire-report.txt:56-59` |
| 2 | Rubric contradicts verifier by allowing covariate adjustment (ChatGPT High) | **Agree** | `entire-report.txt:273` “gain score … or including y_baseline as a covariate”; hidden ANCOVA 3.085 vs truth 2.500 (~23% rel err) |
| 3 | Align `task.toml` difficulty to medium (ChatGPT Medium) | **Disagree as blocker** | `task.toml:8` `difficulty = "hard"`; platform `entire-report.txt:19` MEDIUM; worst-model 60% → medium tier. Per `prompt.md` / `reviewer-checklist-ui.md`: declared vs platform mismatch **never blocks**; #45 CHECK when field present |
| 4 | Expand short `instruction.md` with estimator name (ChatGPT Low) | **Partially agree** | `instruction.md:1-3` is 4 lines, delegates to docs; fix is same as blocker 1 — optional polish after estimand fix |
| 5 | Remove redundant `r` tag (ChatGPT Low) | **Agree, non-blocking** | `task.toml:11-12` `languages = ["r"]` and tag `"r"` duplicate; style only |
| 6 | Dockerfile digest pinning OK (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…` |
| 7 | LLMaJ `behavior_in_task_description` PASS | **Partially agree** | Output paths/schema covered; **baseline-adjustment method not specified** — gap drives blocker 1 |
| 8 | LLMaJ `behavior_in_tests` PASS | **Agree** | I/O and schema tested; correctness tests exist but encode unstated estimator choice |
| 9 | Instruction sufficiency FAIL — ANCOVA ambiguity (export) | **Agree** | `entire-report.txt:46-89` systematic `task_specification: fail`; matches artifact analysis |
| 10 | Harbor review “READY TO USE” (export) | **Disagree** | Export `entire-report.txt:220-224` missed spec↔verifier estimator mismatch |
| 11 | Test quality review ACCEPT (export) | **Partially agree** | Anti-cheat and coverage strong; fairness issue on estimator ambiguity remains |
| 12 | Non-milestone task uses milestone rubric format | **Disagree as blocker** | `task.toml:10` `number_of_milestones = 0`; rubric has only `# Rubric 1` (23 pts). `docs/guidelines/rubrics.md:66`: “`# Rubric 1` optional; no `# Rubric 2+`” for non-milestone — compliant |
| 13 | Rubric positive total >40 | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 23/40 PASS |
| 14 | Audit #31 missing test docstrings | **Disagree** | All 9 `test_*` in `tests/test_outputs.py:135-196` have docstrings; validator INFO is module-level only |
| 15 | Audit #41 stray `audit-report.md` | **Disagree as task defect** | File created by local `./scripts/terminus audit`; not part of author submission |
| 16 | Audit #36 rubric positive language | **Partially agree, non-blocking alone** | `entire-report.txt:276-277` use “Agent does not …, +N” on positive lines; fix when editing rubric for blocker 2 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 4 lines, ~72 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Short engineer-style ask, not synthetic walkthrough | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | Points to contract doc, no algorithm leak | `instruction.md:1` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | UNCHECK | Well specified | Estimand method ambiguous vs verifier | `estimand_contract.md:1`; blocker 1 |
| 8 | CHECK | Interesting | Real causal-inference estimation task | task content |
| 9 | UNCHECK | Unique | Corpus dedup not verified | — |
| 10 | CHECK | Absolute paths | `/app/analysis.R`, `/app/estimate.json`, etc. | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No slug in prompt | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local data only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with == | `pytest==8.2.0`, `numpy==2.1.3` | `environment/Dockerfile:12` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY only env subtree | `environment/Dockerfile:16-23` |
| 17 | CHECK | No ground truth in env | Truth in `tests/fixtures/` only | `environment/README.md:3`; `.dockerignore` |
| 18 | CHECK | No privileged Docker | Standard RUN/COPY | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest/numpy in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:12`; `tests/test.sh:4` |
| 21 | UNCHECK | Oracle passes consistently | Docker unavailable locally; static oracle review only | `solution/analysis_correct.R` |
| 22 | CHECK | Oracle no network | `solve.sh` copies R script and runs Rscript | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | Computes gain score from CSV at runtime | `solution/analysis_correct.R:2-5` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail | `tests/test.sh:5-9` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Tests encode change-score; spec allows ANCOVA | blocker 1 |
| 28 | CHECK | Tests check correctness | Truth comparison, hidden seed, stress case | `tests/test_outputs.py:141-177` |
| 29 | CHECK | Behavior not implementation grep | Truth-based numeric checks; source scan limited to anti-cheat paths | `tests/test_outputs.py:141-177` |
| 30 | CHECK | No brittle string matching | Numeric tolerance checks | `tests/test_outputs.py:129-133` |
| 31 | CHECK | Informative test docstrings | All 9 tests documented | `tests/test_outputs.py:135-196` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:278-281` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines compliant | `entire-report.txt:270-281` |
| 34 | CHECK | Agent …, ±N format | 11 lines | `entire-report.txt:270-281` |
| 35 | CHECK | Rubric detailed; positive cap | 23 positive pts ≤40 | rubric-points output |
| 36 | UNCHECK | Positive language in rubric | Two + lines use “Agent does not …” | `entire-report.txt:276-277` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:270-281` |
| 38 | CHECK | Rubric no instruction.md refs | Clean | `entire-report.txt:270-281` |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | `entire-report.txt:270-281` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | No stray parent files | No jobs/, dev README in submission tree | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/category applicable | ML/causal tags fit content | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | hard declared; platform medium — informational | `task.toml:8`; `entire-report.txt:19` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — non-milestone | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile`; `.dockerignore` |
| 51 | CHECK | Solution not in env | solution/ excluded | `.dockerignore` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Tests use temp copies/shuffles | `tests/test_outputs.py:47-84` |
| 53 | CHECK | Git clones pinned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:24-25` |
| 55 | UNCHECK | Not unfair / unavailable info | Fair agents failed due to unstated estimator | blocker 1; `entire-report.txt:69-74` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 36, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Write `/app/analysis.R` | all tests via `_run_agent` | covered | `instruction.md:1`; `tests/test_outputs.py:29-44` |
| Read `main.csv`, `params.json` from `CAUSAL_DATA_DIR` | `_run_agent` sets env | covered | `instruction.md:1`; `tests/test_outputs.py:33` |
| Write `/app/estimate.json` with finite numeric `estimate` | `test_output_schema` | covered | `instruction.md:3`; `tests/test_outputs.py:135-138` |
| Estimand: effect on follow-up net of baseline | `test_estimate_matches_public_truth`, hidden/shuffle | **gap** | Wording allows ANCOVA; truth requires change-score |
| Change-score / long-difference estimator | oracle + truth fixtures | **phantom in spec** | `solution/analysis_correct.R:3-4`; not named in `estimand_contract.md` |
| No hardcoding / no `/tests` or `/solution` reads | `test_no_forbidden_access_or_public_constants` | covered | `instruction.md:3`; `tests/test_outputs.py:186-195` |
| Baseline adjustment required (not naive follow-up only) | `test_naive_estimator_fails` | covered | `tests/test_outputs.py:147-151` |
| Generalizes to hidden sample | `test_hidden_seed_generalizes` | covered | `tests/test_outputs.py:154-157` |
| Row-order invariant | `test_shuffled_rows_match_public_truth` | covered | `tests/test_outputs.py:160-163` |
| Synthetic stress correctness | `test_synthetic_stress_case_generalizes` | covered | `tests/test_outputs.py:166-169` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7 UNCHECK, spec alignment |
| `environment/docs/estimand_contract.md` | Blocker 1, claim 1 |
| `solution/analysis_correct.R` | Oracle method, blocker 1 |
| `tests/test_outputs.py` | Verifier behavior, #31 CHECK |
| `tests/fixtures/public_truth.json` | Tolerance, truth value |
| `tests/fixtures/hidden_truth.json` | Hidden validation |
| `task.toml` | Metadata, milestone N/A, difficulty |
| `environment/Dockerfile` | #15, #20 |
| `entire-report.txt` | Agent stats, rubric, sufficiency analysis |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate causal-long-diff-cross-section/
Summary: 0 error(s), 0 warning(s), 2 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60% (3/5) | Worst model |
| oracle | 100% (3/3) per export | Not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

Per-test: `test_estimate_matches_public_truth` and hidden/shuffle at 8/10 — consistent with ANCOVA failures.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular (non-milestone) layout |
| 1 Instruction | ☑ | Estimand ambiguity confirmed |
| 2 Environment | ☑ | Digest-pinned Python+R image; tmux/asciinema; offline |
| 3 Oracle | ☑ | Change-score derivation; Docker oracle not run |
| 4 Verifiers | ☑ | Strong anti-cheat; numeric truth enforcement |
| 5 Metadata | ☑ | difficulty mismatch non-blocking |
| 6 Rubric | ☑ | 23/40; covariate line contradicts verifier; `# Rubric 1` OK for non-milestone |
| 7 Agent evidence | ☑ | Sufficiency FAIL in export validated |
| 8 Fairness | ☑ | ANCOVA is reasonable misread — unfair without spec fix |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really nice work on the environment and anti-cheating design — hidden seed, naive-estimator trap, and the verifier suite are all strong. The main issue is the estimand wording: “effect on follow-up net of baseline” reads like it allows standard ANCOVA (`y_followup ~ d_treatment + y_baseline`), but your truth values only match change-score / long-difference regression (`y_gain = y_followup − y_baseline`, then regress on treatment). Agents that picked ANCOVA landed ~50% off on the public set and failed for good-faith reasons. Please name the long-difference estimator explicitly in the estimand contract (and ideally one line in `instruction.md`), and update the platform rubric line that currently rewards “gain score or baseline covariate” so it matches what the verifier actually checks.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
