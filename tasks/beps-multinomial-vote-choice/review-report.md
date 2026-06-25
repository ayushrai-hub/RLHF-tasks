# Terminus Review Report: beps-multinomial-vote-choice

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 2 warnings — both false positives on re-audit) |
| **Oracle** | pass (per `entire-report.txt`; not re-run locally — arm64 host cannot install amd64 R `.deb`) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** Re-audit confirms ChatGPT's sole High finding. `task.toml` declares `difficulty = "hard"` but agent evaluation places the task in the **medium** tier (Claude 40%, GPT-5.5 100%; worst-model 40%). Everything else is solid: digest-pinned Dockerfile with hash-pinned verifier venv, exemplary hidden-data anti-cheating, oracle 100% on platform, comprehensive D-series recomputation tests, and full spec↔test alignment per LLMaJ. Update `difficulty` to `"medium"` or rebalance until ≤20% on best or worst model.

**Insights (concise):**

- Automated blockers on #14, #20, #31, #54 are **false positives** — `requirements.txt` uses `==` + `--require-hashes`, pytest is baked in the image, all 42 `test_*` functions have docstrings, worst-model rate is 40% not 100%.
- Hidden-data harness (`generate_hidden_data.py` + second R run) is exemplary anti-cheating design.
- Instruction is long (900 words / 5 paragraphs) but every detail is tested; LLMaJ `behavior_in_task_description` PASS — length is not a revise driver.
- `test.sh` omits `--ctrf` and prewrite-0 — consistency gap only (Low), not a blocker.
- Plot tests check structure only; core statistics are fully recomputed in D-series — acceptable per test-quality review.
- Rubrics appear in external report only; no `rubric.txt` in task folder (portal UI submission).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but observed worst-model pass rate 40% → **medium** tier | `task.toml:7` `difficulty = "hard"`; `entire-report.txt:6–7` Claude 40% (2/5), GPT-5.5 100% (5/5); `docs/guidelines/difficulty.md` medium = 20–60% worst model | Set `difficulty = "medium"` in `task.toml`, or rebalance task until ≤20% on best or worst model |

*No other High-severity blockers confirmed on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` but evaluation is Medium — Claude 40%, GPT 100% (ChatGPT High) | **Agree** | `task.toml:7`; `entire-report.txt:1–7` |
| 2 | `test.sh` lacks `--ctrf` and prewrite `/logs/verifier/reward.txt` with 0 (ChatGPT Low) | **Agree** (Low only) | `tests/test.sh:1–46` — no `--ctrf`, no upfront `echo 0`; reward block at lines 41–46 works. Canonical shape in `docs/guidelines/writing-tests.md:19` — consistency, not blocker. |
| 3 | Non-canonical base image debian:bookworm-slim (`entire-report.txt` WARNING) | **Partially agree** | `environment/Dockerfile:1` debian slim; tmux+asciinema installed; R requires custom base — justified warning, no action required. |
| 4 | Starter `analysis.R` provides scaffolding (`entire-report.txt` WARNING) | **Partially agree** | `environment/analysis.R:1–13` loads libs/paths only; no computation leaked. Design choice, not blocker. |
| 5 | Plot tests structural only, not content (`entire-report.txt` test-quality) | **Agree** (minor) | `tests/test_outputs.py:71–79` color-count checks; D-series covers all numeric outputs. Not a revise driver. |
| 6 | `df=2` implicit not explicit in instruction (LLMaJ subtlety) | **Partially agree** | `test_B3_lr_tests_schema` asserts `df==2` (`test_outputs.py:108`); instruction describes 2-equation multinomial drop-one-term tests — implicit from model structure, fair. |
| 7 | LLMaJ quality checks all PASS | **Agree** | `entire-report.txt:127–136` — behavior_in_task_description, behavior_in_tests, anti_cheating, pinned_dependencies, hardcoded_solution all pass |
| 8 | Human review "READY TO USE" (`entire-report.txt:258–262`) | **Disagree** on accept | Overlooks difficulty metadata mismatch (#45). Otherwise accurate on task quality. |
| 9 | Automated review: unpinned pip (#14) | **Disagree** | `environment/requirements.txt:1–9` all `package==version --hash=sha256:…`; Dockerfile line 39 `--require-hashes -r` |
| 10 | Automated review: pytest not in Dockerfile (#20) | **Disagree** | `environment/requirements.txt:6` `pytest==8.4.1`; `tests/test.sh` runs venv pytest, no runtime install |
| 11 | Automated review: missing test docstrings (#31) | **Disagree** | All 42 `test_*` functions have docstrings; only module-level docstring missing (validator INFO) |
| 12 | Automated review: too easy worst-model 100% (#54) | **Disagree** | `entire-report.txt:6–7` worst model Claude 40%, not 100% |
| 13 | Agent failures are execution/silent-R, not spec gaps | **Agree** | `entire-report.txt:97–98` task_specification PASS; 7/10 agent runs pass all tests when R produces outputs |
| 14 | Instruction too long (#1 automated) | **Partially agree** | 900 words, 5 paragraphs vs 3-paragraph guideline (`instruction.md`); all content is tested. Not a revise blocker — condensing would risk spec-test gaps. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 900 words, 5 paragraph blocks exceed limit | `instruction.md` (wc: 900 words) |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Statistical analysis brief tone, not LLM preamble | `instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Specifies outputs/methods, not dev workflow | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Delta-method/Jacobian specs are tested requirements, not walkthrough hints | `instruction.md:3`, `test_D2` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | All file schemas, methods, paths, rounding specified | `instruction.md`; LLMaJ PASS |
| 8 | CHECK | Instruction is interesting | Real BEPS vote-choice multinomial analysis | — |
| 9 | UNCHECK | Instruction is unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time R `.deb` + CRAN packages only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Hash-pinned requirements | `environment/requirements.txt:1–9`, `Dockerfile:39` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only from `environment/` | `environment/Dockerfile:43–44` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | `data/reference/` has counts/distributions for orientation; no model coefficients or output values | `instruction.md:1`; `environment/data/reference/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | Venv + hash-pinned pip at build; test.sh only runs pytest | `environment/Dockerfile:37–39`, `tests/test.sh:17` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Platform oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes and runs R locally | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full multinom + delta-method + counterfactuals in R heredoc | `solution/solve.sh:6–280` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | mkdir + 0/1 reward block | `tests/test.sh:10–11,41–46` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` only | `tests/test.sh:43–45` |
| 27 | CHECK | All tests are aligned with instructions | LLMaJ PASS; full schema + recompute coverage | `entire-report.txt:127–128` |
| 28 | CHECK | Tests check for correctness, not just format | D-series independent R recomputation | `tests/test_outputs.py:164–228` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep; runs R outputs | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Numeric tolerances 1e-3–5e-2 | `tests/test_outputs.py:172–173` |
| 31 | CHECK | Tests have informative names or docstrings | 42/42 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no `rubric.txt` in task folder | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Regular layout complete | task root |
| 41 | CHECK | No unnecessary files in parent directory | No jobs/, README, stray artifacts | task root |
| 42 | CHECK | author_name and author_email fields present | `anonymous` / `anonymous` | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, languages | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable | `machine-learning`, `r`, multinomial-logit tags match content | `task.toml:6–12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared hard; worst-model 40% → medium | `task.toml:7`, `entire-report.txt:6–7` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | — |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | — |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | — |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Reference tables are descriptive stats only; tests recompute from data | `environment/data/reference/` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Hidden-data re-run with perturbed BEPS.csv | `tests/test.sh:24–35`, `generate_hidden_data.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate) | Worst-model 40% ≤ 80% | `entire-report.txt:6–7` |
| 55 | CHECK | Task is not too hard or unfair | Failures are silent R execution, not spec/env bugs | `entire-report.txt:97–98` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 9, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| coefficients.csv schema + 22 rows + sort | `test_B1_coefficients_schema` | covered | `test_outputs.py:82–89` |
| marginal_effects.csv schema + 27 rows | `test_B2_marginal_effects_schema` | covered | `test_outputs.py:92–99` |
| lr_tests.csv 8 terms, df=2 | `test_B3_lr_tests_schema` | covered | `test_outputs.py:102–109` |
| model_fit.json 11 keys | `test_B4_model_fit_keys` | covered | `test_outputs.py:112–116` |
| Six-decimal rounding, bare JSON numbers | `test_B5_six_decimal_rounding` | covered | `test_outputs.py:119–129` |
| Delta-method AME recompute | `test_D2_marginal_effects_recompute` | covered | `test_outputs.py:181–195` |
| Counterfactual interaction JSON (9 keys) | `test_D5_eki_recompute`, `test_B6_eki_keys` | covered | `test_outputs.py:340–372` |
| First-difference JSON (9 keys, endpoints 1/11) | `test_D6_efd_recompute`, `test_B7_efd_keys` | covered | `test_outputs.py:394–430` |
| Five PNG plots exist + non-blank | `test_A5`, `test_A6` | covered (structure) | `test_outputs.py:64–79` |
| Hidden-data generalization | `test.sh` second R run + `HIDDEN_VARIANT=1` | covered | `tests/test.sh:28–35` |
| Plot statistical content fidelity | — | gap (minor) | Only color-count checks; D-series covers numerics |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45 blocker, #42–44 |
| `instruction.md` | #1, #7, #10, spec alignment |
| `environment/Dockerfile` | #14–20, #50 |
| `environment/requirements.txt` | #14, #20 |
| `environment/analysis.R` | scaffolding review |
| `tests/test.sh` | #20, #24–26, anti-cheat |
| `tests/test_outputs.py` | #27–31, spec alignment |
| `tests/generate_hidden_data.py` | #52 |
| `solution/solve.sh` | #22–23 |
| `entire-report.txt` | #21, #45, #54, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate beps-multinomial-vote-choice/
Summary: 0 error(s), 2 warning(s), 2 info
- pinned_dependencies WARNING: false positive — requirements.txt uses == + hashes
- informative_test_docstrings WARNING: module-level only; all test functions documented
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | Above hard threshold |
| terminus-claude-opus-4-8 | 40% (2/5) | Sets worst-model tier |
| oracle | 100% (3/3) | Per platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular R task; report matches folder |
| 1 Instruction | ☑ | Long but complete; LLMaJ PASS |
| 2 Environment | ☑ | Digest-pinned; verifier venv baked; hidden-data design |
| 3 Oracle | ☑ | solve.sh derives computationally; platform 100% |
| 4 Verifiers | ☑ | 42 tests, D-series recompute, hidden variant |
| 5 Metadata | ☑ | **#45 mismatch** — only blocker |
| 6 Rubric | ☑ | N/A in folder; rubric text in external report only |
| 7 LLMaJ & agent evidence | ☑ | All quality checks PASS; difficulty MEDIUM |
| 8 Novelty & fairness | ☑ | Multi-step stats task; fair failures |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, Dockerfile pinning, hidden-data anti-cheating, and spec↔test alignment all look solid. The only blocking issue is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium tier (Claude 40%, GPT-5.5 100%). Update `difficulty` to `medium` or rebalance until the task qualifies as hard.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Instruction Styling | no (length noted, not blocking) | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | yes (difficulty field) | 1 |
| Pinning Issues | no | — |
| Rubric | N/A (no file in folder) | — |
