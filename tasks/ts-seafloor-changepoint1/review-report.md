# Terminus Review Report: `ts-seafloor-changepoint1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong long-context signal-processing task with excellent anti-cheating mutation tests, digest-pinned canonical Node base, and Hard-tier calibration (GPT-5.5 20%, Claude 100%). The remaining High blocker is a spec↔verifier gap: the reference pipeline enforces fixed-sample-count detrend window edge clamping (`half_window = 720`, 1440-sample window) that dossier §9.3 describes only as a time-centered 10-day window. Agents implementing literal time-centered windows pass 25/26 tests but fail `test_uncalibrated_lookup_table_fails_hidden_mutation` by a consistent ~25% displacement margin.

**Insights (concise):**

- `instruction.md` now correctly mandates Section 9.3 quadratic detrend and one-event-per-station selection; prior global-linear-detrend concern is obsolete.
- Dockerfile uses the canonical `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf4…` from `docs/guidelines/dockerfxile.md` — not a blocker.
- Automated `terminus review` incorrectly flagged #45/#54 (uses `max` agent rate instead of worst-model `min`; actual worst model GPT-5.5 = 20% → Hard).
- Four GPT-5.5 failures all hit the same hidden mutation test with displacement −0.048 vs reference −0.0384 (~25% rel error, threshold 15%).
- `scripts/seed_db.py` is authoring-only and not copied into the image — not an answer leak.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Detrend window boundary behavior enforced by verifier/oracle but not specified in instruction or dossier §9.3 | `tests/test_outputs.py:289-303`, `environment/docs/seismology_ops_dossier.md:332`, `entire-report.txt:56-60` | Add explicit rule to `instruction.md` and/or dossier §9.3: 10-day window = 1440 samples at 10-minute cadence; `half_window = 720`; at series edges clamp to a fixed 1440-sample window (re-anchor `start = max(0, end - 1440)`). |

*No other High blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Detrend boundary underspecified: verifier uses fixed sample-count window with `half_window=720` and edge clamping; time-centered implementations fail hidden amplitude mutation (ChatGPT) | **Agree** | `tests/test_outputs.py:33,294-299`; dossier §9.3 (`seismology_ops_dossier.md:332`) says "centered on the time point" only; `entire-report.txt:56-60,74-77` documents 4/4 GPT-5.5 trials at 25/26 with consistent displacement error on `test_uncalibrated_lookup_table_fails_hidden_mutation` |
| 2 | Verifier uses global linear detrend while dossier specifies quadratic rolling window (`entire-report.txt:1`) | **Disagree** | `instruction.md:3` requires "Section 9.3 rolling 10-day quadratic detrend"; `_detrend` uses `_quadratic_trend_at` (`tests/test_outputs.py:262-303`); oracle `detrend()` matches (`solution/solve.sh:283-296`) |
| 3 | One-primary-event-per-station rule missing from prompt (ChatGPT prior note) | **Disagree** | `instruction.md:3` states one candidate per station, highest `confidence_score`, tiebreak by longer `duration_hours`; enforced by `test_one_event_per_station` and `_select_primary_event` (`tests/test_outputs.py:396-399,602-605`) |
| 4 | Non-canonical base image must use `ghcr.io/laude-institute/t-bench/` (`entire-report.txt:125-150`) | **Disagree** | `environment/Dockerfile:2` matches canonical table in `docs/guidelines/dockerfxile.md:10` (same image + digest) |
| 5 | `test.sh` missing shebang (`entire-report.txt:156-177`) | **Disagree** | `tests/test.sh:1` has `#!/bin/bash` |
| 6 | Difficulty mismatch / too easy — worst model 100% (`review-report` auto + #45/#54) | **Disagree** | `entire-report.txt:7-9`: GPT-5.5 20% (1/5), Claude 100% (5/5); worst model = 20% → Hard per `docs/guidelines/difficulty.md`; `task.toml:6` declares `hard` |
| 7 | `scripts/seed_db.py` is answer leakage (`entire-report.txt:3`) | **Disagree** | `environment/Dockerfile:28-35` copies only `src/`, `data/`, `docs/` — no `scripts/`; `scripts/seed_db.py` is parent authoring artifact |
| 8 | Instruction sufficiency FAIL on detrend ambiguity (`entire-report.txt:70-74`) | **Partially agree** | 10-minute cadence is in dossier (`seismology_ops_dossier.md:48`) so 1440 samples is derivable; edge-clamping semantics remain unstated and drive systematic mutation-test failures |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 2 short paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as engineering brief, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States deliverable + dossier reference only | `instruction.md` |
| 5 | CHECK | No hints / solving strategies | Names dossier sections as requirements, not implementation steps | `instruction.md:3` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | UNCHECK | Well specified | Detrend edge-clamping rule unstated | `seismology_ops_dossier.md:332`, `tests/test_outputs.py:294-299` |
| 8 | CHECK | Interesting | Realistic seafloor signal-processing + DB task | — |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app/data/sensors.db`, `/app/output/events.json`, etc. | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No `ts-seafloor-changepoint1` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No urllib/curl in environment code | `environment/` |
| 14 | CHECK | Pip deps pinned | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18-20` |
| 15 | CHECK | Base image digest-pinned | `@sha256:f3a68cf4…` | `environment/Dockerfile:2` |
| 16 | CHECK | Context in environment/ only | COPY limited to environment subtree | `environment/Dockerfile` |
| 17 | CHECK | No ground-truth answers in env | Dossier is intentional long-context source; no solution catalog | `environment/Dockerfile`, `environment/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:18-20`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | `./scripts/terminus oracle` → reward 1.0 (1/1 trial) | `jobs/2026-06-21__16-23-46/result.json` |
| 22 | CHECK | Oracle no internet | solve.sh writes TS + npm build; no network fetch | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results | Full pipeline implementation, not hardcoded JSON | `solution/solve.sh:283-370` |
| 24 | CHECK | reward.txt canonical block | mkdir + pytest + 0/1 reward | `tests/test.sh:1-16` |
| 25 | CHECK | Same verifier logic for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:12-16` |
| 27 | UNCHECK | Tests aligned with instructions | Hidden mutation enforces undisclosed detrend edge clamping | `tests/test_outputs.py:785-807`, blocker #1 |
| 28 | CHECK | Tests check correctness | Reference pipeline + tolerance checks on displacement/timing | `tests/test_outputs.py:480-502,607-614` |
| 29 | CHECK | Behavior not implementation grep | CLI output vs reference pipeline | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | 15% displacement tolerance; flexible maintenance-term check | `tests/test_outputs.py:457-477,492-496` |
| 31 | CHECK | Informative test docstrings | All test classes/methods documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — rubric in portal only (`entire-report.txt:257-274`) | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh, tests | task root |
| 41 | CHECK | Clean parent directory | `scripts/seed_db.py` is authoring-only, not shipped | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, subcategories, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | typescript, scientific-computing, long_context, db_interaction | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches pass rates | Worst model GPT-5.5 20% → Hard; declared hard | `entire-report.txt:7-9`, `task.toml:6` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible | solution/ not in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Mutation tests copy DB to /tmp; hidden key verifier-only | `tests/test_outputs.py:667-793` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:7-9` |
| 55 | UNCHECK | Not unfair | Undisclosed detrend boundary semantics cause systematic hidden-test failures | `entire-report.txt:56-60`, blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 27, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output at `/app/output/events.json` | `test_file_exists` | covered | `instruction.md:3`, `tests/test_outputs.py:25,529-531` |
| CLI `node dist/src/index.js --db --dossier --output` | `test_cli_entry_exists`, `run_cli` | covered | `instruction.md:3`, `tests/test_outputs.py:59-76` |
| Section 9.3 quadratic rolling 10-day detrend | reference pipeline + mutation tests | **gap** (edge clamping) | dossier `332`; verifier `289-303`; blocker #1 |
| Robust Z-scores (MAD, 1.4826) | reference pipeline | covered | dossier `344`; `tests/test_outputs.py:321-326` |
| Bayesian change-point scoring → confidence_score | `test_confidence_scores_in_range` | covered | dossier `350+`; `tests/test_outputs.py:328-337` |
| One event per station; highest confidence; duration tiebreak | `test_one_event_per_station`, `test_station_event_matches_reference` | covered | `instruction.md:3`; `tests/test_outputs.py:396-399,602-605` |
| Maintenance-window exclusion (JUAN01 Jan 8–12) | `test_juan01_event_in_maintenance_window` | covered | dossier station sections; `tests/test_outputs.py:616-626` |
| Per-station calibration from dossier | `test_station_event_matches_reference[*]` | covered | dossier §§2–7; `tests/test_outputs.py:84-237` |
| Catalog schema (generated_at, events[], excluded) | `TestCatalogStructure` | covered | dossier §9.7; `tests/test_outputs.py:526-574` |
| Derive from inputs, not static catalog | `TestHiddenMutations` | covered | `instruction.md:3`; `tests/test_outputs.py:727-820` |
| Quality-flag exclusion in detrend windows (dossier §9.3) | — | untested (low impact for Jan 2024 fixture) | `seismology_ops_dossier.md:336`; verifier does not filter flags |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #5, #10, blocker 1, spec alignment |
| `environment/Dockerfile` | #15, #20, #50, adjudication #4 |
| `environment/docs/seismology_ops_dossier.md` | blocker 1, spec alignment, long_context |
| `environment/src/config.ts` | `DETREND_WINDOW_SAMPLES` constant |
| `tests/test_outputs.py` | blocker 1, #27-31, #52, spec alignment |
| `tests/test.sh` | #24, adjudication #5 |
| `solution/solve.sh` | #23, detrend oracle match |
| `task.toml` | #43-45 |
| `entire-report.txt` | agent stats, adjudication, failure pattern |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: ts-seafloor-changepoint1/ ===
Summary: 0 error(s), 2 warning(s), 1 info
Warnings: solution-hints pattern in dossier (benign procedural prose)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | 4/4 failures: 25/26 tests; all fail `test_uncalibrated_lookup_table_fails_hidden_mutation` |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Full pass |
| oracle | 100.0% (3/3) | per report |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `ts-seafloor-changepoint1`; regular layout; TypeScript scientific-computing + long_context |
| 1 Instruction | ☑ | Concise; quadratic detrend named; one-event rule present; detrend boundary gap |
| 2 Environment | ☑ | Canonical digest-pinned Node; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | `./scripts/terminus oracle` pass — reward 1.0 (1/1) |
| 4 Verifiers | ☑ | Canonical reward block; reference pipeline; strong mutation tests; boundary gap |
| 5 Metadata | ☑ | hard difficulty matches 20% worst model |
| 6 Rubric | ☑ | Portal-only rubric in report; ≥3 negatives present |
| 7 LLMaJ & agent evidence | ☑ | Reconciled detrend claims; difficulty auto-parse error identified |
| 8 Novelty & fairness | ☑ | Multi-step pipeline; mutation anti-cheat; unfair hidden boundary semantics |
| 9 Long context | ☑ | Dossier ~230 KB / ~33k words; requires deep reading for calibration params |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, CLI contract, hidden mutation tests, Dockerfile pinning, and Hard difficulty calibration look strong, and the one-event-per-station rule is now stated in `instruction.md`. The remaining blocker is that the verifier enforces fixed-sample-count detrend window edge clamping (`half_window = 720`, 1440-sample window at 10-minute cadence) that dossier §9.3 does not document — only "centered on the time point." GPT-5.5 agents pass 25/26 tests but fail the hidden amplitude mutation by a consistent ~25% displacement margin. Add the sample-count and edge-clamping rule explicitly to `instruction.md` or dossier §9.3.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
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
