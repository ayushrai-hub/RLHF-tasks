# Terminus Review Report: elixir-goldsmith-atelier-api

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Elixir API task with thorough docs, live integration tests, pinned offline setup, and solid anti-cheat posture. Two real blockers: (1) lineage-grade ancestor objects lack an explicit `piece_id` field in SPEC.md/EXAMPLES.md while `test_210` requires it — caused a documented 108/109 agent failure; (2) platform rubric uses milestone-style `# Rubric 1`–`# Rubric 5` blocks on a non-milestone task (`number_of_milestones = 0`) with 79 positive points (cap 40). Fix rubric format/points first; add lineage-grade response schema second.

**Insights (concise):**

- Automated audit false-positives on #13 (localhost health probe in `start.sh`) and #14 (pip packages are `==`-pinned in Dockerfile) — not blockers.
- Difficulty metadata vs time estimates (medium vs 270 min expert) is informational only — never blocks per policy.
- `missing_assay` and cast-active open-window preconditions are untested but minor; not blockers.
- Worst-model pass rate 60% (GPT-5.5); best 80% (Claude Opus 4.8) — within medium band, not too easy.
- LLMaJ `structured_data_schema` PASS is overstated for lineage-grade; that endpoint is the sole spec↔test gap.
- Docker digest-pinned Debian base is acceptable for Elixir; no base-image blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Non-milestone task (`number_of_milestones = 0`) has platform rubric split into `# Rubric 1`–`# Rubric 5` (milestone format forbidden). Positive total 79 exceeds 40 cap. | `task.toml:11`; `entire-report.txt:455-497`; `./scripts/terminus rubric-points entire-report.txt` → 79 pts, blocks {1:15, 2:15, 3:16, 4:20, 5:13}; `docs/guidelines/rubrics.md:31-36,66-67` | Flatten to a single non-milestone rubric list (no `# Rubric 2+`). Trim positive criteria to ≤40 total. Keep ≥3 distinct negatives. |
| 2 | High | Test Alignment/Coverage Issues | #27, #55 | Lineage-grade `ancestors[]` object field names undocumented. SPEC describes algorithm and mentions `depth`, `mean_letter`, `weight` but never names the piece identifier field. Test requires `piece_id`; agent trial used `ancestor_id` and failed 108/109. | `environment/task_file/docs/SPEC.md:315-341` (no JSON example, no `piece_id` in ancestors); contrast `SPEC.md:140-141` (provenance), `SPEC.md:165-170` (contribution), `SPEC.md:366-373` (mass-attribution); `tests/test_outputs.py:1409`; `solution/solve.sh:1224`; `entire-report.txt:171,188-193` | Add explicit response schema/example for `GET /pieces/:id/lineage-grade`, e.g. `{"piece_id": N, "lineage_grade": …, "ancestors": [{"piece_id", "depth", "mean_letter", "weight", …}]}` in SPEC.md (and optionally EXAMPLES.md). |

*No other High/Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Lineage-grade response schema incomplete; ancestor field should be `piece_id` (ChatGPT / entire-report instruction sufficiency) | **Agree** | `SPEC.md:315-341` omits ancestor identifier; `test_outputs.py:1409` asserts `a["piece_id"]`; agent used `ancestor_id` per `entire-report.txt:171` |
| 2 | Rubric uses milestone format on non-milestone task; >40 positive points (ChatGPT) | **Agree** | `task.toml:11` `number_of_milestones = 0`; `entire-report.txt:455-497` has `# Rubric 1`–`# Rubric 5`; rubric-points total 79 |
| 3 | Dockerfile FROM digest-pinned — acceptable for Elixir (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:4724b8cc…`; no canonical Elixir base required |
| 4 | Difficulty medium vs expert 270 min suggests hard (ChatGPT / Harbor review) | **Disagree** (not a blocker) | `prompt.md:477-484`, `reviewer-checklist-ui.md:81-85` — metadata mismatch never blocks; worst-model 60% supports medium |
| 5 | missing_assay / cast-active open-window preconditions untested (test quality review) | **Agree** (Low only) | `entire-report.txt:365-445`; no `test_135`/`test_136` in `test_outputs.py` — minor gap, not blocking |
| 6 | LLMaJ `behavior_in_task_description` FAIL — instruction too terse (entire-report) | **Disagree** | `instruction.md:1-7` delegates to `/app/docs`; `SPEC.md` normatively specifies endpoints; pattern valid for stub-completion tasks. Exception: lineage-grade ancestor schema |
| 7 | LLMaJ `structured_data_schema` PASS — all endpoints have schemas (entire-report) | **Partially agree** | Most endpoints have JSON examples in `SPEC.md`; lineage-grade (`SPEC.md:315-341`) lacks ancestor object field names |
| 8 | Non-canonical base image needs revision (Harbor review report) | **Disagree** | Digest-pinned Debian justified for Elixir; tmux/asciinema present (`Dockerfile:15-16`) |
| 9 | Automated audit #13 runtime web fetch in start.sh | **Disagree** | `start.sh:31` hits `http://127.0.0.1:8080/health` — localhost readiness probe, not external fetch |
| 10 | Automated audit #14 unpinned pip | **Disagree** | `Dockerfile:23-26` pins `pytest==8.2.0`, `requests==2.32.3`, etc. |
| 11 | Automated audit #41 stray audit-report.md | **Disagree** | Generated by reviewer tooling, not part of submission package |
| 12 | Category `data-processing` mismatch (audit #44) | **Partially agree** (advisory) | `task.toml:7` `data-processing`; API implementation fits `software-engineering` better per taxonomy — not a Revise driver |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~127 words, 4 blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational stub-completion framing | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Describes goal, not dev steps | `instruction.md` |
| 5 | CHECK | No hints/answers | Points to docs, no walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal + `/app/docs` authority | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Realistic API/state-machine task | task content |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app`, `/app/docs`, `/app/start.sh` | `instruction.md` |
| 11 | CHECK | No task name in instruction | Task name absent | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch | `start.sh` only probes localhost :8080 | `start.sh:31` |
| 14 | CHECK | Pip pinned with == | All verifier deps pinned | `Dockerfile:23-26` |
| 15 | CHECK | FROM digest-pinned | `@sha256:4724b8cc…` | `Dockerfile:1` |
| 16 | CHECK | No outside build context | COPY only `task_file/` | `Dockerfile:43` |
| 17 | CHECK | No ground-truth leakage | Seed/schema docs intentional; no oracle answers | `environment/task_file/docs/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `Dockerfile` |
| 19 | CHECK | Compose mounts safe | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh clean | `Dockerfile:21-26`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Docker unavailable; oracle not executed locally | oracle run failed |
| 22 | CHECK | Oracle no internet | solve.sh writes handlers, no network | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Real algorithmic Elixir implementations | `solution/solve.sh:1193-1232` |
| 24 | CHECK | reward.txt on failure | Canonical block present | `tests/test.sh` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Lineage-grade ancestor `piece_id` tested but undocumented | Blocker #2 |
| 28 | CHECK | Tests check correctness | Live API + computed values (trend, hashes, grades) | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | No source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching | Numeric tolerances where needed | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | Numbered classes + docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives in platform rubric | `entire-report.txt:462,471,479,496` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:455-497` |
| 34 | CHECK | Rubric Agent format | 34 properly formatted lines | `entire-report.txt:455-497` |
| 35 | UNCHECK | Rubric detailed/precise | 79 positive pts > 40 cap on non-milestone | Blocker #1 |
| 36 | CHECK | Positive rubric phrasing | Negatives use "fails to"/"does not"; positives affirmative | `entire-report.txt:455-497` |
| 37 | CHECK | Rubric no /tests/ refs | None | platform rubric |
| 38 | CHECK | Rubric no metadata refs | None | platform rubric |
| 39 | CHECK | Rubric no oracle/NOP refs | None | platform rubric |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | No stray parent files | Clean submission layout | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Present | `task.toml` |
| 44 | UNCHECK | Tags/languages/category applicable | `data-processing` debatable; `elixir`/`db_interaction` fit | `task.toml:7-10` |
| 45 | CHECK | Difficulty field present | `difficulty = "medium"` | `task.toml:6` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone scope isolation | N/A | `task.toml:11` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile` |
| 51 | CHECK | Solution not in environment | Only `task_file/` copied | `Dockerfile:43` |
| 52 | CHECK | Input not trivially mutable | Tests use live DB mutations; seed reset via helpers | `tests/test_outputs.py` |
| 53 | CHECK | Git pins if used | No git clone | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:28-29` |
| 55 | UNCHECK | Not too hard/unfair | Lineage-grade field-name gap unfair to careful agents | Blocker #2; `entire-report.txt:188-193` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 21, 27, 35, 44, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Lineage-grade algorithm (depth weights, mean_letter, rounding) | `test_210_piece_10_grade_3_333333` | covered | `SPEC.md:321-339`; `test_outputs.py:1405-1408` |
| Lineage-grade ancestor `piece_id` field | `test_210_piece_10_grade_3_333333` | **gap** | `test_outputs.py:1409`; absent from `SPEC.md:315-341` |
| Lineage-grade `empty_lineage` | `test_211`, `test_212` | covered | `SPEC.md:332-333`; `ERRORS.md:29` |
| Provenance chain `piece_id` in chain objects | `test_050`–`test_052` | covered | `SPEC.md:140-141` |
| Mass-attribution `root_attributions` schema | `test_220`–`test_223` | covered | `SPEC.md:366-373` |
| Bulk-cast dup_in_batch precedes row validation | `test_153` | covered | `SPEC.md:108` |
| Audit SHA-256 chain format | `test_182` | covered | `SPEC.md:284-287`; `EXAMPLES.md:76-87` |
| missing_assay precondition (ingot_selected→assayed) | — | gap (minor) | Documented in state machine; no negative test |
| cast_active→cast_complete with open window | — | gap (minor) | Documented; no negative test |
| All other major endpoints/errors | respective `test_*` classes | covered | 109 tests in `entire-report.txt:41-149` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #7, #27 |
| `task.toml` | #42-45, #46-49, rubric milestone check |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/task_file/start.sh` | #13 adjudication |
| `environment/task_file/docs/SPEC.md` | Blocker #2, spec alignment |
| `environment/task_file/docs/EXAMPLES.md` | Lineage-grade gap (no example) |
| `tests/test_outputs.py` | #27-31, Blocker #2 |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh` | #22-23, lineage oracle field names |
| `entire-report.txt` | #45, #54, rubric, agent stats, external claims |
| `docs/guidelines/rubrics.md` | Blocker #1 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate elixir-goldsmith-atelier-api/
Summary: 0 error(s), 3 warning(s), 2 info
Task type detected: regular
Warnings: pip pin heuristic (false positive — Dockerfile uses ==), solution-hints in SPEC.md (informational)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Best model |
| oracle | 100.0% (3/3) | Per submission export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | medium |
| Platform classified | medium |
| Tier match (#45) | yes (informational) |

**Per-test signal:** `test_210_piece_10_grade_3_333333` at 8/10 — aligns with lineage `piece_id` ambiguity.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular layout; Elixir API |
| 1 Instruction | ☑ | Concise delegation to `/app/docs` — valid |
| 2 Environment | ☑ | Digest-pinned; offline; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | solve.sh implements real handlers; not run (no Docker) |
| 4 Verifiers | ☑ | 109 live API tests; canonical test.sh; docstrings |
| 5 Metadata | ☑ | `number_of_milestones = 0`; timeouts plausible |
| 6 Rubric | ☑ | **Blocker:** milestone-format rubric, 79 pts |
| 7 LLMaJ & agent evidence | ☑ | Lineage spec gap confirmed; difficulty OK |
| 8 Novelty & fairness | ☑ | Multi-endpoint; anti-cheat solid; one unfair field gap |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this Elixir atelier API — the docs are thorough, the live integration tests are comprehensive, and the offline Docker setup is clean. Two things to fix before accept: flatten the platform rubric into a single non-milestone list and trim positive points to 40 or fewer (it's currently split across five milestone-style blocks totaling 79). Also add an explicit lineage-grade response example in SPEC.md naming `piece_id` (and related fields) inside each `ancestors[]` object — the algorithm is documented but the ancestor field names aren't, and that gap caused a capable agent run to miss one test using `ancestor_id` instead.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | yes | 2 |
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
| Rubric | yes | 1 |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
