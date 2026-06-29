# Terminus Review Report: `sklearn-pipeline-column-transform`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** Strong Java/C++ JNI debugging task with digest-pinned canonical `debian:bookworm-slim` base, offline verifier deps baked in the image, hidden reseed bundles, and cryptographic cross-artifact checks. ChatGPT’s High-severity base-image blocker is **false** — the exact digest used is on the approved canonical list. Automated review false positives on #20 (pytest in image), #31 (informative test names), and #54 (worst-model 60%, not 100%) are overturned. Platform rubric is correctly flat (non-milestone format). Oracle passes 1.0/1.0.

**Insights (concise):**

- `debian:bookworm-slim@sha256:4724b8cc…` is an **approved canonical base** per `docs/guidelines/dockerfxile.md:22` — identical digest to the task Dockerfile.
- Worst-model pass rate is **60%** (GPT-5.5), not 100%; observed tier is medium; declared `hard` in `task.toml` is optimistic but **not a revision blocker** per review policy.
- Platform rubric (`entire-report.txt:347-355`) is a **flat** `Agent …, ±N` list with no `# Rubric 2+` headers — correct for `number_of_milestones = 0`.
- `long_context` subcategory: corpus is ≥500k chars (gate + size met), but ~13k repetitive SK-section filler dominates; policy values are grepable from the first ~20 lines and duplicated in `output-contract.md` — borderline for true long-context reasoning, not a High blocker.
- Test docstrings missing (validate warns) but class/method names are highly descriptive (`test_manifest_oracle`, `test_cross_digest_chain`) — satisfies portal #31 “names **or** docstrings”.
- `portable_pipeline.json` checked for existence only in export test; parity-audit digest chain provides downstream coverage — Low polish only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical Docker base image — must switch to approved canonical or add exemption (ChatGPT High) | **Disagree** | `environment/Dockerfile:2,18` uses `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`; `docs/guidelines/dockerfxile.md:22` lists this exact image+digest as canonical |
| 2 | Task technically strong: hidden bundles, digest chain, JNI parity, pinned deps (ChatGPT Medium none) | **Agree** | `tests/test_outputs.py`, `tests/_refs.json`, `environment/Dockerfile`, `tests/verifier_fixtures/` |
| 3 | `portable_pipeline.json` only existence-checked (ChatGPT Low / test-quality review) | **Agree** (Low only) | `tests/test_outputs.py:89`; indirect coverage via `test_audit_oracle` + `test_cross_digest_chain` |
| 4 | Remove unchanged files from `solution/fixed/` (ChatGPT Low / Harbor warning) | **Agree** (Low only) | `solution/apply_fixes.py:9-14` copies all files under `fixed/`; Harbor report `entire-report.txt:162-178` |
| 5 | Add test docstrings (ChatGPT Low / Harbor suggestion) | **Agree** (Low only) | `tests/test_outputs.py` — 20 `test_*` without docstrings; validate warns; names are descriptive |
| 6 | Harbor review WARNING: non-canonical base (entire-report.txt:141-159) | **Disagree** | Same proof as claim 1 — digest is on canonical list |
| 7 | Harbor READY TO USE recommendation (entire-report.txt:233-237) | **Agree** | Artifacts support structural soundness; oracle pass confirms |
| 8 | LLMaJ `behavior_in_task_description` PASS (entire-report.txt:102) | **Agree** | `instruction.md:1-5` names all commands, outputs, sentinels; delegates schema to `output-contract.md` |
| 9 | LLMaJ `behavior_in_tests` PASS (entire-report.txt:103) | **Agree** | 18 tests across alpha/beta/hidden bundles in `tests/test_outputs.py` |
| 10 | Export-order corpus override ambiguity caused agent failure (entire-report.txt:77,85-99) | **Partially agree** (not a blocker) | Hidden appendix line 13603 sets `pipeline_reseed_47` override; primary alpha uses line 13 defaults; `output-contract.md:62` states corpus `export_order`; one agent misapplied override scope — near-miss, not systematic spec gap |
| 11 | Automated review #20 pytest not in Dockerfile | **Disagree** | `environment/Dockerfile:27-28` installs `requirements.lock` containing `pytest==8.4.1`; `tests/test.sh` has no pip/apt |
| 12 | Automated review #54 worst-model 100% too easy | **Disagree** | `entire-report.txt:26-27` GPT-5.5 60%, Claude 100%; worst = 60% (<80% rejection threshold) |
| 13 | Automated review #31 missing docstrings = fail | **Disagree** | Portal #31 allows informative names **or** docstrings; names like `test_rejects_short_corpus`, `test_native_required` are self-documenting |
| 14 | Non-milestone task uses milestone rubric format | **Disagree** | `entire-report.txt:347-355` flat list, no `# Rubric N` headers; `task.toml:10` `number_of_milestones = 0`; matches `docs/guidelines/rubrics.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 paragraphs, ~212 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer incident narrative, not spec dump | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcomes; points to contract doc | `instruction.md:3-5` |
| 5 | CHECK | No hints/solving strategies | No file-level fix walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Commands, outputs, sentinels named; schema in contract | `instruction.md:3`, `output-contract.md` |
| 8 | CHECK | Interesting | Realistic Java/C++/JNI pipeline debugging | task content |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md:1,3,5` |
| 11 | CHECK | Task name not in instruction | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | `allow_internet = false`; offline build | `task.toml:18`, `environment/Dockerfile` |
| 14 | CHECK | Pip deps pinned | `--require-hashes` + `pytest==8.4.1` in lockfile | `environment/Dockerfile:27-28`, `requirements.lock:13-15` |
| 15 | CHECK | FROM digest-pinned | Both stages pinned | `environment/Dockerfile:2,18` |
| 16 | CHECK | Context in environment/ only | `COPY app/` only | `environment/Dockerfile:12,31` |
| 17 | CHECK | No ground truth in env | Deliberate bugs only; refs in `tests/_refs.json` | `environment/`, `tests/_refs.json` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts safe | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest baked in Dockerfile | `environment/Dockerfile:27-28`, `tests/test.sh:10-11` |
| 21 | CHECK | Oracle passes consistently | Oracle 1.0/1.0 | `./scripts/terminus oracle` → Mean 1.000 |
| 22 | CHECK | Oracle no internet | Patch + local rebuild only | `solution/solve.sh:6-9` |
| 23 | CHECK | Oracle reflective | `apply_fixes.py` patches source, rebuilds native+JAR | `solution/apply_fixes.py`, `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical | Writes 0/1 on failure path | `tests/test.sh:4,12-16` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All four commands + outputs tested; LLMaJ PASS | `tests/test_outputs.py`, `entire-report.txt:102-103` |
| 28 | CHECK | Tests check correctness | Oracle digests, score vectors, error paths | `tests/reference_skct.py`, `tests/_refs.json` |
| 29 | CHECK | Behavior not implementation grep | Runs CLI, asserts JSON outputs | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact matching | Sentinels/digests specified in contract | `output-contract.md:11`, `tests/test_outputs.py` |
| 31 | CHECK | Informative test names or docstrings | Descriptive `test_*` names across 5 classes | `tests/test_outputs.py:21-136` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives (-5, -5, -3) | `entire-report.txt:353-355` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All valid | `entire-report.txt:347-355` |
| 34 | CHECK | Agent-line format | 9 flat `Agent …, ±N` lines | `entire-report.txt:347-355` |
| 35 | CHECK | Rubric detailed/precise | Task-specific pipeline/parity/hardcode criteria | `entire-report.txt:347-355` |
| 36 | CHECK | Positive rubric phrasing | Negatives use negative scores | `entire-report.txt:353-355` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:347-355` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:347-355` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:347-355` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | task tree |
| 42 | CHECK | author_name/email present | Both set | `task.toml:5-6` |
| 43 | CHECK | Other metadata fields present | version, timeouts, languages, tags | `task.toml` |
| 44 | CHECK | Tags/languages/categories applicable | java+cpp, machine-learning, column-transform tags match | `task.toml:8-13` |
| 45 | UNCHECK | Difficulty matches agent pass rates | Declared `hard`; worst-model 60% → medium tier | `task.toml:7`, `entire-report.txt:26-27`, `docs/guidelines/difficulty.md:7-12` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not baked in image | No `COPY tests/` | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not in env | Only `COPY app/` | `environment/Dockerfile:12,31` |
| 52 | CHECK | Agent cannot trivially modify inputs | Hidden bundle/corpus in `tests/verifier_fixtures/` only | `tests/conftest.py`, `tests/test_outputs.py:10-11` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 60% | `entire-report.txt:26-27` |
| 55 | CHECK | Not too hard/unfair | Instruction sufficiency PASS; failures were implementation bugs | `entire-report.txt:59,77-87` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `feature-ingest` emits `feature_manifest.json` with correct splits | `test_manifest_oracle`, `test_beta_generalization`, `test_hidden_reseed` | covered | `tests/test_outputs.py:27-48` |
| `FEATURE_INGEST_OK` sentinel | `test_ingest_sentinel` | covered | `tests/test_outputs.py:22-25` |
| Corpus gate rejects short corpus | `test_rejects_short_corpus`, `test_corpus_gate` | covered | `tests/test_outputs.py:32-36,125-127` |
| `column-transform-train` score vectors | `test_train_oracle`, `test_beta_train`, `test_hidden_train` | covered | `tests/test_outputs.py:56-69` |
| Native library required | `test_native_required` | covered | `tests/test_outputs.py:71-77` |
| `pipeline-export` digest + registry | `test_export_oracle`, `test_beta_export`, `test_hidden_export` | covered | `tests/test_outputs.py:85-99` |
| `portable_pipeline.json` produced | `test_export_oracle` (existence) | covered | `tests/test_outputs.py:89` |
| `parity-audit` Java vs C++ parity | `test_audit_oracle`, `test_hidden_audit` | covered | `tests/test_outputs.py:108-122` |
| Cross-artifact digest chain | `test_cross_digest_chain` | covered | `tests/test_outputs.py:129-135` |
| Holdout appendix override semantics | `test_hidden_reseed`, `test_hidden_train`, `test_hidden_export`, `test_hidden_audit` | covered | `tests/test_outputs.py` + `hidden_appendix.md:13603` |
| Schema/digest formulas | indirect via oracle refs | covered | `output-contract.md`, `tests/_refs.json` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-20, canonical base adjudication |
| `environment/requirements.lock` | #14, #20 |
| `docs/guidelines/dockerfxile.md` | Canonical base claim rebuttal |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `tests/reference_skct.py` | #28 |
| `tests/_refs.json` | oracle values, anti-cheat |
| `tests/verifier_fixtures/` | hidden bundle tests |
| `output-contract.md` | spec authority |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats |
| `docs/guidelines/rubrics.md` | rubric format (#32-39) |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: sklearn-pipeline-column-transform ===
Summary: 0 error(s), 20 warning(s), 2 info
Task type detected: regular
```

Warnings: missing test docstrings (informative names present); non-milestone preferred info.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 near-miss failures on audit/digest |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Full passes |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle Mean 1.000 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no — declared hard optimistic; not a revision blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) layout |
| 1 Instruction | ☑ | Concise; delegates schema to contract |
| 2 Environment | ☑ | Canonical digest-pinned debian; tmux+asciinema; pytest in image |
| 3 Oracle | ☑ | Passes 1.0 locally |
| 4 Verifiers | ☑ | 18 behavior tests; reward block canonical; no runtime installs |
| 5 Metadata | ☑ | java+cpp, ML category; `long_context` borderline |
| 6 Rubric | ☑ | Flat non-milestone format; 3 negatives; +28 total |
| 7 LLMaJ & agent evidence | ☑ | All quality checks PASS; agent failures implementation-level |
| 8 Novelty & fairness | ☑ | Multi-bug JNI+digest repair; hidden fixtures anti-cheat |
| 9 Long context | ☑ | ≥500k chars met; filler-heavy; policy grepable — note only |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the Java/C++ pipeline repair work is well scoped, the hidden reseed bundles and digest-chain verifiers make cheating impractical, and the environment is cleanly offline with pinned deps and a proper canonical base image. Oracle passes cleanly and agent rates look right for medium difficulty (60% on the weaker model). I didn’t find any blocking spec gaps. Optional polish if you want: add per-test docstrings, trim unchanged files from `solution/fixed/`, and consider whether the `long_context` tag still fits given how much of the corpus is repetitive filler versus the contract doc carrying the real rules.

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

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review sklearn-pipeline-column-transform --report entire-report.txt`._
