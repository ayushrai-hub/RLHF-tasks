# Terminus Review Report: `java-buoy-wavelet-spectra-yaml-calibration`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt` 3/3; local oracle CLI timed out ~5 min) |
| **CHECK count** | 33 |
| **UNCHECK count** | 22 |

**Error categories (internal):** Task Difficulty, Exposing Hints/Answers, Test Alignment/Coverage Issues, Instruction Styling, Metadata Issues

**Decision (concise):** ChatGPT’s Revise verdict is supported on three High blockers: `difficulty = "hard"` while worst-model pass rate is 60% (medium tier); hidden probe CSV/manifests remain agent-readable at `/app/verifier-fixtures/buoy-spectra-probes/` after Dockerfile build; and the `pressure_hpa` CSV column name contradicts Pa-scale values and `corrected_pa` contract language, causing both GPT failures via a reasonable hPa→Pa conversion. Automated script false positives on #14, #20, and #54 are overturned after artifact review.

**Insights (concise):**

- Digest-pinned `eclipse-temurin:21-jdk-jammy` is canonical per `docs/guidelines/dockerfile.md`; not a blocker.
- Verifier deps (`pytest==9.0.3`, etc.) are correctly baked via `requirements.lock` in the Dockerfile; `test.sh` does not install packages.
- Oracle/solution design is sound: six Java file fixes, Maven rebuild, independent Python reference verifier.
- Task is **not** too easy (#54): worst model GPT-5.5 at 60% is below the 80% rejection threshold (automated review wrongly used `max` instead of `min` for worst-model rate).
- Nine tags exceed the 3–6 limit (Medium metadata); `subcategories` should include `long_context` given the >200k dossier test, but that is not a standalone High blocker.
- LLMaJ `behavior_in_task_description` failures on dossier size string, decoy jar check, and duplicate staging test are real spec↔test gaps (Medium, folded under #27).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but observed worst-model 60% → **medium** tier | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:16-22` Claude 100%, GPT-5.5 60%, classified MEDIUM; `docs/guidelines/difficulty.md` medium = 20–60% worst model | Set `difficulty = "medium"` or rebalance until worst-model ≤20% |
| 2 | High | Exposing Hints/Answers | #17, #51 | Hidden probe fixtures copied to `/opt/…` but **not removed** from agent workdir `/app/verifier-fixtures/` | `environment/build/gen_fixtures.py:13` writes `ROOT / "verifier-fixtures" / "buoy-spectra-probes"`; `environment/docker/install_probe_fixtures.sh:3-4` copies to `/opt/verifier-fixtures/…`; `environment/Dockerfile:36-42` runs both scripts, no `rm -rf /app/verifier-fixtures` | Delete `/app/verifier-fixtures` after install, or generate probes only outside `/app` |
| 3 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `pressure_hpa` column name implies hectopascals; values and reference treat them as **Pa** with no conversion | `gen_fixtures.py:36` `base = 101325.0`; `processing-contract.md:7,16` column `pressure_hpa` but formula uses `raw_pa`/`corrected_pa`; `reference_spectra.py:50,60` reads `pressure_hpa` without ×100; `entire-report.txt:67-90` both GPT failures converted hPa→Pa → ~100× Hs error | Rename column to `pressure_pa` (update Java/docs/fixtures) **or** add explicit contract note: values are already Pa; do not convert |
| 4 | Medium | Metadata Issues | #44 | Tags array has 9 entries (limit 3–6) | `task.toml:12` nine tags; `./scripts/terminus validate` warns | Trim to 3–6 high-signal tags |
| 5 | Medium | Test Alignment/Coverage Issues | #27, #30 | Tests assert requirements not stated in `instruction.md` | `test_outputs.py:110-115` requires `len > 200_000` and exact `'FINAL CALIBRATION MEMO'` — instruction cites dossier as authoritative but does not specify size or string; `test_outputs.py:158-166` requires decoy absent from jar — instruction never mentions decoy; `test_outputs.py:86-94` duplicates `test_hidden_probe_coarse_report` with unstated “staging snapshot” framing | Remove phantom assertions, move gates to build-only checks, or add matching instruction requirements |

*Automated script blockers #14 (pip pinning), #20 (pytest in image), and #54 (too easy at 100%) are **false positives** — see adjudication rows 8–10.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT High: `difficulty = "hard"` vs medium tier (Claude 100%, GPT 60%) | **Agree** | `task.toml:6`; `entire-report.txt:16-22`; `docs/guidelines/difficulty.md` |
| 2 | ChatGPT High: hidden probes exposed under `/app/verifier-fixtures/` | **Agree** | `gen_fixtures.py:13,109-153`; `install_probe_fixtures.sh:3-4`; `Dockerfile:36-42` — no cleanup of `/app/verifier-fixtures` |
| 3 | ChatGPT High: `pressure_hpa` unit ambiguity caused systematic GPT failures | **Agree** | `gen_fixtures.py:44,36`; `processing-contract.md:7,16`; `reference_spectra.py:50`; `entire-report.txt:67-90` |
| 4 | ChatGPT Medium: 9 tags exceed 3–6 limit | **Agree** | `task.toml:12`; validate warning |
| 5 | `entire-report.txt` LLMaJ: `behavior_in_task_description` fail (dossier size, decoy, staging test) | **Agree** | `test_outputs.py:110-115`, `158-166`, `86-94` vs `instruction.md` (no size/string/decoy/staging requirements) |
| 6 | `entire-report.txt` LLMaJ: `anti_cheating_measures` fail (probe exposure) | **Agree** | Same as claim 2 |
| 7 | `entire-report.txt` automated review: #14 pip unpinned | **Disagree** | `environment/requirements.lock:1-4` all `==`; Dockerfile installs from lockfile |
| 8 | `entire-report.txt` automated review: #20 pytest not in Dockerfile | **Disagree** | `Dockerfile:19-20` venv + `pip install -r requirements.lock`; `test.sh:30` uses `/opt/verifier-venv/bin/python -m pytest` only |
| 9 | `entire-report.txt` automated review: #54 too easy (100% worst) | **Disagree** | Worst agent model is GPT-5.5 at **60%** (`entire-report.txt:22`); script bug uses `max()` not `min()` in `review_checklist.py:167-169` |
| 10 | `entire-report.txt` warning: non-canonical `eclipse-temurin` base | **Disagree** | Listed canonical in `docs/guidelines/dockerfile.md:13` with matching digest |
| 11 | `entire-report.txt` suggestion: add `long_context` subcategory | **Partially agree** | `test_outputs.py:110-115` enforces >200k dossier; `task.toml:8` `subcategories = []` — metadata gap, not High blocker |
| 12 | `entire-report.txt` test-quality: ACCEPT | **Agree** | Independent `reference_spectra.py` + numeric tolerance design is strong; exposure/phantom issues are fixable |
| 13 | `entire-report.txt` overall: READY TO USE despite tag trim | **Disagree** | High blockers 1–3 outweigh tag-only fixes |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Three short paragraphs; normative detail in `/app/docs/` | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Coastal-engineering scenario; no LLM anti-patterns | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code fences | `instruction.md` |
| 4 | CHECK | No step-by-step solve script | States goal and contract refs, not file-by-file fix list | `instruction.md` |
| 5 | CHECK | No hints/strategies | Describes WHAT (match contracts), not HOW to patch each class | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | No markdown tables | `instruction.md` |
| 7 | UNCHECK | Well specified | `pressure_hpa` vs Pa contract is contradictory | `processing-contract.md:7,16`; `gen_fixtures.py:36,44` |
| 8 | CHECK | Interesting | Realistic Java/Maven signal-processing debug task | — |
| 9 | UNCHECK | Unique vs corpus | Not verified against TB2/TB3/Edition 1 | — |
| 10 | CHECK | Absolute paths only | `/app/...`, `/opt/verifier-fixtures/...` | `instruction.md:3-9` |
| 11 | CHECK | Task name not in instruction | No folder-name string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures; curl/httpie for local `file://` | `instruction.md:1`; `test_fetch_manifest_curl` |
| 14 | CHECK | Pinned pip versions | `pytest==9.0.3`, etc. in lockfile | `environment/requirements.lock:1-4` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:25d12765...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY limited to `environment/` subtree | `environment/Dockerfile:27-34` |
| 17 | UNCHECK | No ground truth in environment | Probe CSV/manifests readable at `/app/verifier-fixtures/` | `gen_fixtures.py:13`; `Dockerfile:36-42` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked; no runtime install | Venv + lockfile in image; test.sh only runs pytest | `Dockerfile:19-20`; `tests/test.sh:30` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per evaluation report | `entire-report.txt:25-26` |
| 22 | CHECK | Oracle no runtime downloads | Copies Java sources + `mvn package` only | `solution/solve.sh:8-17` |
| 23 | CHECK | Oracle reflective implementation | Replaces six Java files, rebuilds, runs pipeline | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir + pytest + 0/1 reward on all paths | `tests/test.sh:5-7,32-36` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | `echo 0` / `echo 1` only | `tests/test.sh:32-36` |
| 27 | UNCHECK | Tests aligned with instructions | Phantom dossier/decoy/staging assertions; pressure unit untested in spec | `test_outputs.py:86-94,110-115,158-166` |
| 28 | CHECK | Tests check correctness | Independent reference + numeric tolerance on Hs/Tp/COI/drift | `tests/reference_spectra.py`; `assert_report_close` |
| 29 | CHECK | Behavior not implementation grep | Subprocess CLI + `jar tf` anti-cheat only | `tests/test_outputs.py:22-28,158-166` |
| 30 | UNCHECK | No brittle exact strings | Exact `'FINAL CALIBRATION MEMO'` not in instruction | `test_outputs.py:114` |
| 31 | CHECK | Informative names or docstrings | All 23 tests have docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no `rubric.txt` in task folder (platform UI only) | `entire-report.txt:296-308` |
| 33 | UNCHECK | Rubric valid scores | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed criteria | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Regular layout complete | task root |
| 41 | CHECK | Clean parent directory | No stray `jobs/` or dev README at task root | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Required metadata fields | category, timeouts, allow_internet=false, etc. | `task.toml` |
| 44 | UNCHECK | Tags/languages/category match | 9 tags exceed 3–6 limit | `task.toml:12` |
| 45 | UNCHECK | Difficulty matches pass rates | `hard` vs 60% worst → medium | `task.toml:6`; `entire-report.txt:22` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | — |
| 48 | UNCHECK | test_mN.py per milestone | N/A | — |
| 49 | UNCHECK | Milestone-scoped tests | N/A | — |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/`; no COPY | `environment/.dockerignore:12`; `Dockerfile` |
| 51 | UNCHECK | No accessible ground-truth cheat | Hidden probe series/manifests under `/app/verifier-fixtures/` | `gen_fixtures.py:13`; `Dockerfile:36-38` |
| 52 | CHECK | Agent cannot trivially mutate inputs to pass | Numeric tests use independent reference recompute; hidden probes differ from bundled | `test_hidden_differs_from_bundled`; `reference_spectra.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:22` |
| 55 | UNCHECK | Not too hard/unfair | Systematic spec defect on pressure units drove both GPT failures | `entire-report.txt:79-90` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 31, 40, 41, 42, 43, 50, 52, 53, 54 |
| **UNCHECK** | 7, 9, 17, 27, 30, 32, 33, 34, 35, 36, 37, 38, 39, 44, 45, 46, 47, 48, 49, 51, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Run pipeline via `/app/scripts/run-spectra-pipeline.sh --manifest --output` | `test_jar_and_runner_exist`, pipeline tests | covered | `instruction.md:7-8`; `test_outputs.py:48-54` |
| Report matches `report-schema.md`; tolerance 0.001 on Hs/Tp/COI | `test_report_schema_fields`, `assert_report_close` | covered | `instruction.md:8-9`; `test_outputs.py:35-39` |
| Processing per `processing-contract.md` (drift, gaps, Morlet, COI, Hs) | bundled + hidden probe tests | covered | `instruction.md:8`; `reference_spectra.py` |
| TOML overlay wins over YAML drift rate | `test_toml_drift_precedence_reflected` | covered | `config-precedence.md`; `test_outputs.py:148-155` |
| Manifest `sample_rate_hz` hint ignored (profile wins) | `test_bundled_storm_beta_report` | covered | `storm-beta.json` has `"sample_rate_hz": 1.0`; `test_outputs.py:57-63` |
| Hidden probes under `/opt/verifier-fixtures/buoy-spectra-probes/` | `test_hidden_probe_*` | covered | `instruction.md:9`; `test_outputs.py:66-83` |
| Offline curl manifest fetch | `test_fetch_manifest_curl` | covered | `instruction.md:1`; `test_outputs.py:96-107` |
| Non-zero exit on missing manifest | `test_invalid_manifest_fails` | covered | `test_outputs.py:142-145` |
| Idempotent consecutive runs | `test_idempotent_pipeline_runs` | covered | `test_outputs.py:202-208` |
| Dossier authoritative when agreeing with contracts | `test_coastal_dossier_long_context` (partial) | gap | Instruction cites dossier; test adds >200k + exact memo string not in instruction |
| Decoy class must not ship in jar | `test_decoy_not_compiled` | phantom | `environment/decoy/SpectraShortcut.java` exists; instruction silent |
| Staging snapshot export concept | `test_staging_snapshot_export_after_manifest_ingest` | phantom | Duplicate of `test_hidden_probe_coarse_report`; term absent from instruction |
| Pressure CSV units (`pressure_hpa` vs Pa) | numeric tests (implicit) | gap | Column name implies hPa; values are Pa; no explicit contract statement |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #44, #45, blocker 1, 4 |
| `instruction.md` | #7, #10, #27, spec alignment |
| `environment/Dockerfile` | #15, #17, #20, #51, blocker 2 |
| `environment/build/gen_fixtures.py` | blocker 2, 3; pressure values |
| `environment/docker/install_probe_fixtures.sh` | blocker 2 |
| `environment/docs/processing-contract.md` | blocker 3; spec alignment |
| `environment/requirements.lock` | #14 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #30, #51, blockers 3, 5 |
| `tests/reference_spectra.py` | blocker 3; oracle alignment |
| `solution/solve.sh` | #21–#23 |
| `entire-report.txt` | agent stats, LLMaJ, failure analysis |
| `docs/guidelines/difficulty.md` | blocker 1, #45, #54 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: java-buoy-wavelet-spectra-yaml-calibration/ ===
WARNING: tags should have 3-6 entries (found 9)
WARNING: pinned_dependencies — pip install from lockfile (false alarm; lockfile uses ==)
Summary: 0 error(s), 2 warning(s), 2 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Both failures: hPa→Pa conversion → ~100× Hs |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) | per `entire-report.txt` |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% (GPT-5.5) |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) Java task |
| 1 Instruction | ☑ | Pressure-unit ambiguity is primary spec defect |
| 2 Environment | ☑ | Probe leak confirmed; canonical base OK; deps baked |
| 3 Oracle | ☑ | solve.sh derives via Java rebuild; 100% per report |
| 4 Verifiers | ☑ | reward block canonical; phantom tests flagged |
| 5 Metadata | ☑ | hard/medium mismatch; 9 tags |
| 6 Rubric | ☑ | N/A in repo; portal rubric in report has ≥3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated all external claims |
| 8 Novelty & fairness | ☑ | Multi-bug Java debug; unfair pressure naming |
| 9 Long context | ☑ | Dossier >200k tested but `long_context` not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The Java/Maven environment, digest pinning, offline verifier design, oracle pass rate, and independent reference tests are solid. Blockers: (1) `difficulty = "hard"` while worst-model pass rate is 60% (medium tier); (2) hidden probe fixtures remain readable at `/app/verifier-fixtures/buoy-spectra-probes/` after build; (3) `pressure_hpa` column name contradicts Pa-scale fixture values and caused both GPT failures via reasonable hPa→Pa conversion — rename to `pressure_pa` or state explicitly that values are already Pa. Also trim tags to 3–6 and resolve phantom dossier/decoy/staging test assertions.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Exposing Hints/Answers | yes | 2 |
| Instruction Styling | yes | 3 |
| Test Alignment/Coverage Issues | yes | 3, 5 |
| Metadata Issues | yes | 4 |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
| Rubric | no | — |
