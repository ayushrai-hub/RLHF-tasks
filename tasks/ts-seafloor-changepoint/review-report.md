# Terminus Review Report: `ts-seafloor-changepoint`

**Generated:** 2026-06-19 (manual audit, table format v2)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/ts-seafloor-changepoint`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 2 warnings) |
| **Oracle** | not executed locally (Docker unavailable); report shows 100% (3/3) |
| **CHECK count** | 37 |
| **UNCHECK count** | 18 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Oracle Solution Issues, Other

**Decision (concise):** Revise. The task is well-engineered — strong CLI contract, digest-pinned env, hidden DB mutation anti-cheat, and hard difficulty (Claude 0%) are all solid. The blocking issue is a spec–verifier–oracle mismatch on detrending: the dossier normatively describes rolling 10-day quadratic detrend as the standard method, but the verifier and oracle use global linear detrend, causing dossier-faithful agents to fail hidden amplitude mutation checks by ~2%. Fix detrend alignment or normatize linear detrend in the instructions.

**Insights (concise):**

- `scripts/seed_db.py` is **not** agent-visible (excluded from image and submission zip) — ChatGPT's seed-leak claim is rejected.
- Hidden mutation tests (`TestHiddenMutations`) are well-designed; weakness is verifier pipeline divergence, not missing anti-cheat.
- Output JSON schema is in dossier Appendix H (`seismology_ops_dossier.md:1236-1242`); instruction defers to dossier — acceptable for `long_context` but increases parse burden.
- `test_one_event_per_station` enforces a selection rule not stated in `instruction.md` — secondary gap.
- Declared `hard` matches observed tier (worst model Claude 0% ≤ 20%).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | **High** | Test Alignment/Coverage Issues, Oracle Solution Issues | #27, #55 | Verifier/oracle use **global linear** detrend; dossier §9.3 states **rolling 10-day quadratic** is the standard production method. Agents following the dossier get ~2% displacement error on `test_mutated_amplitude_matches_reference_pipeline`. | `environment/docs/seismology_ops_dossier.md:332-334`; `tests/test_outputs.py:241-257`; `solution/solve.sh:234-244`; `entire-report.txt:72-88` | Align verifier + oracle to dossier standard **or** add explicit normative statement in `instruction.md` that catalog output must use global linear detrend over the full January window. |
| 2 | **Medium** | Instruction Styling, Test Alignment/Coverage Issues | #7, #27 | `test_one_event_per_station` requires exactly one highest-confidence event per station; rule not stated in `instruction.md` or a clearly cited dossier section. | `tests/test_outputs.py:556-559`; `tests/test_outputs.py:350-353`; `instruction.md:1-3` | Add one sentence to `instruction.md`: report single highest-confidence event per station (tie-break: longest duration). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `scripts/seed_db.py` exposes injected event windows/durations/amplitudes to agents (ChatGPT High) | **Disagree** | `scripts/seed_db.py:12-54` has anomaly params; `environment/Dockerfile` never COPYs `scripts/`; zip includes only `instruction.md`, `task.toml`, `environment`, `solution`, `tests` (`scripts/terminus:204`). Agents cannot read this file at runtime. |
| 2 | Detrending mismatch: dossier quadratic rolling vs verifier linear (ChatGPT High; `entire-report.txt:87-88`) | **Agree** | `seismology_ops_dossier.md:332-334` (standard = rolling quadratic); `test_outputs.py:241-257` + `solve.sh:234-244` (global linear). 6/8 trials fail amplitude mutation test with ~2% shortfall. |
| 3 | Hidden mutations too weak; lookup table can pass without pipeline (ChatGPT High) | **Partially agree** | Seed not agent-visible. Default-DB hardcoding blocked by `TestHiddenMutations` (`test_outputs.py:681-773`). Real weakness is detrend mismatch causing **false failures** for legitimate pipelines, not insufficient mutation coverage. |
| 4 | COAX01 deletion mutation (`entire-report.txt:4`) | **Partially agree** | COAX01 is **amplitude** mutation target (`_mutation_station(2)`); deletion targets JUAN01 (`_mutation_station(1)`). `test_outputs.py:686-687`, `708`. |
| 5 | Output schema not in `instruction.md` (LLMaJ `behavior_in_task_description` fail) | **Partially agree** | Full schema in dossier Appendix H (`seismology_ops_dossier.md:1236-1242`) and `environment/src/types.ts:53-58`. Instruction defers to dossier — OK for `long_context`; non-blocking alone. |
| 6 | Difficulty metadata wrong — hard vs medium (automated review script) | **Disagree** | Worst model = Claude **0%** ≤ 20% → hard tier per `docs/guidelines/difficulty.md`. `task.toml:6` correct. Script used max rate (40%) instead of min. |
| 7 | Non-canonical base image (`entire-report.txt:170-188`) | **Partially agree** | `environment/Dockerfile:2` uses ECR `node:22-bookworm-slim@sha256:…` — digest-pinned but not ghcr t-bench canonical. Acceptable for TypeScript until canonical Node 22 exists. Not a blocker. |
| 8 | Instruction brevity — one event per station untested in instruction (`entire-report.txt:239-255`) | **Agree** | `test_one_event_per_station` enforced; rule absent from `instruction.md`. Blocker #2. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1–3 paragraphs max) | 2 paragraphs, ~130 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone, not spec document | Engineering brief style | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States deliverable + paths only | `instruction.md` |
| 5 | CHECK | No hints/solving strategies (WHAT not HOW) | Pipeline stages named, not implementation steps | `instruction.md:3` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | UNCHECK | Instruction well specified | Detrend norm ambiguous; one-event-per-station unstated | Blockers #1–2 |
| 8 | CHECK | Instruction interesting | Realistic seafloor signal-processing task | task content |
| 9 | UNCHECK | Instruction unique | Not verified vs TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | All paths absolute | `/app/data/…`, `/app/output/…` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No folder name string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No urllib/curl in environment code | `environment/` |
| 14 | CHECK | Pinned pip deps with `==` | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18-20` |
| 15 | CHECK | Base image digest-pinned | `@sha256:f3a68c…` | `environment/Dockerfile:2` |
| 16 | CHECK | Build context in environment/ only | All COPY from environment subtree | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in environment | `seed_db.py` not in image; Appendix G disclaims GT | `environment/Dockerfile`; dossier Appendix G |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | task layout |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile`; `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not re-run locally (Docker daemon down) | oracle command output |
| 22 | CHECK | Oracle no internet | solve.sh writes TS, npm build, no downloads | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results (not hardcoded) | Full pipeline implementation | `solution/solve.sh:234-299` |
| 24 | CHECK | reward.txt canonical block | mkdir, pytest, binary 0/1 | `tests/test.sh:1-16` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:12-15` |
| 27 | UNCHECK | Tests aligned with instructions | Linear detrend tested vs dossier quadratic standard; one-event rule unstated | Blockers #1–2 |
| 28 | CHECK | Tests check correctness | Reference pipeline + mutation tracking | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string asserts | 40 min / 15% tolerance bands | `tests/test_outputs.py:434-451` |
| 31 | CHECK | Informative test docstrings | All classes + methods documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics ≥3 negatives | N/A — no rubric file in task | task layout |
| 33 | UNCHECK | Rubric score set | N/A | task layout |
| 34 | UNCHECK | Rubric Agent format | N/A | task layout |
| 35 | UNCHECK | Rubric criteria precise | N/A | task layout |
| 36 | UNCHECK | Rubric positive language | N/A | task layout |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | task layout |
| 38 | UNCHECK | Rubric no task.toml refs | N/A | task layout |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A | task layout |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh | task layout |
| 41 | UNCHECK | No unnecessary parent files | `scripts/seed_db.py` dev artifact in parent (excluded from zip) | `scripts/seed_db.py` |
| 42 | CHECK | author_name/email present | anonymous / anonymous | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | category, subcategories, timeouts | `task.toml` |
| 44 | CHECK | Tags/languages/category match | typescript, scientific-computing, sqlite | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches agent rates | `hard` declared; worst model 0% → hard | `task.toml:6`; `entire-report.txt:14-15` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth in env | seed excluded; `_MUTATION_KEY` verifier-only | `tests/test_outputs.py:35-36` |
| 52 | CHECK | Input data not trivially writable | Mutations copy DB to `/tmp` | `tests/test_outputs.py:627-714` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Neither model > 80% | `entire-report.txt:14-15` |
| 55 | UNCHECK | Not too hard/unfair | Dossier-faithful detrend systematically fails mutation displacement check | Blocker #1; `entire-report.txt:72-88` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 32, 33, 34, 35, 36, 37, 38, 39, 41, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| CLI `node dist/src/index.js --db --dossier --output` | `test_cli_entry_exists` | covered | `instruction.md:3`; `tests/test_outputs.py:539-543` |
| Read `/app/data/sensors.db` | Reference alignment tests | covered | `instruction.md:1`; `tests/test_outputs.py:356-402` |
| Apply calibration + detection pipeline | `TestReferenceAlignment`, `TestHiddenMutations` | covered | `instruction.md:3` |
| Write `/app/output/events.json` | `test_file_exists` | covered | `instruction.md:3`; `tests/test_outputs.py:483-485` |
| Dossier as source of truth for catalog fields | `test_event_schema`, `test_top_level_fields` | covered | Appendix H; `tests/test_outputs.py:493-528` |
| Maintenance window exclusion (JUAN01) | `test_juan01_event_in_maintenance_window` | covered | dossier §JUAN01; `tests/test_outputs.py:570-580` |
| Rolling quadratic 10-day detrend (dossier §9.3 standard) | Reference uses global linear | **gap** | `seismology_ops_dossier.md:332-334`; `test_outputs.py:241-257` |
| One primary event per station | `test_one_event_per_station` | **phantom** | `tests/test_outputs.py:556-559`; not in `instruction.md` |
| Derive results dynamically (no static catalog) | `TestHiddenMutations` | covered | `instruction.md:3`; `tests/test_outputs.py:681-773` |
| `generated_at` top-level field | `test_top_level_fields` | covered | Appendix H; `tests/test_outputs.py:495` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–6, #10–12, #27, blockers #1–2, claims 5/8 |
| `task.toml` | #42–45, #46–49 N/A |
| `environment/Dockerfile` | #13–20, #50, #53, claim 1 |
| `environment/docs/seismology_ops_dossier.md` | Blocker #1, claims 2/5, spec alignment |
| `environment/src/types.ts` | Claim 5 (schema mirror) |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #25–31, #27, #51–52, #55, blockers, claims 3–4 |
| `solution/solve.sh` | #22–23, blocker #1 |
| `scripts/seed_db.py` | Claim 1, #41, #51 |
| `entire-report.txt` | #45, #54–55, agent stats, claims 2/4/7 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: ts-seafloor-changepoint/ ===
INFO: submission-diversity — non-milestone not blocked
WARNING: solution-hints [dossier] — "first, run/edit/open/create/install" pattern (×2)
Summary: 0 error(s), 2 warning(s), 1 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 0.0% (0/5) | Sets hard tier floor |
| terminus-gpt5-5 | 40.0% (2/5) | Near-pass on visible tests; fails mutation |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (Claude) |
| Observed tier | hard |
| Declared difficulty | hard (`task.toml:6`) |
| Tier match (#45) | yes |

**Hidden mutation pass rates (from report):** deleted-station 8/10; amplitude 2/10; lookup guard 5/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular layout; scientific-computing + long_context + db_interaction |
| 1 Instruction | ☑ | Concise; defers schema/pipeline to dossier; gaps on detrend + one-event rule |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; sensors.db.gz; no tests/solution COPY |
| 3 Oracle | ☑ | Computational pipeline; global linear detrend matches verifier |
| 4 Verifiers | ☑ | Canonical reward; mutation anti-cheat; reference alignment |
| 5 Metadata | ☑ | Complete; hard difficulty appropriate |
| 6 Rubric | N/A | No rubric file in task folder |
| 7 LLMaJ & agent evidence | ☑ | All claims adjudicated in §3 |
| 8 Novelty & fairness | ☑ | seed not agent-visible; detrend mismatch = unfair |
| 9 Long context | ☑ | ~50k token dossier; verifier parses per-station params |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, CLI contract, Dockerfile pinning, hidden mutation tests, and hard difficulty calibration are strong. The blocker is spec–verifier alignment on detrending: the dossier's standard method is rolling 10-day quadratic detrend (Section 9.3), but the verifier reference and oracle use global linear detrend, causing dossier-faithful agents to fail hidden amplitude mutation checks by ~2%. Align the reference pipeline with the dossier standard or explicitly normatize global linear detrend in the instructions. Also state the one-primary-event-per-station rule tested by the verifier. `scripts/seed_db.py` is authoring-only and excluded from the image and submission zip — not an agent-facing leak.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | #2 |
| Test Alignment/Coverage Issues | yes | #1, #2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | yes | #1 |
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
| Other | yes | #41 (`scripts/seed_db.py` in parent dir, excluded from zip) |

---

_Report format v2 per `prompt.md`. Enriched after manual audit._
