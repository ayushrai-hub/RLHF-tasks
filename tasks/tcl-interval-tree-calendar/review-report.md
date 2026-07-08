# Terminus Review Report: `tcl-interval-tree-calendar.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Tcl analytics task — digest-pinned offline env, comprehensive SPEC.md (§8–§29), conftest service lifecycle, and ~193 oracle-backed HTTP tests covering all 21 analytics endpoints. The sole real blocker is the platform rubric: it grades pre-built CRUD/BST endpoints (`POST /events`, `/stab`, `/overlap`, `/stats`, etc.) that the agent does not implement, while omitting all 22 analytics procedures in `/app/src/analytics.tcl` that instruction.md and the verifier actually target. Positive rubric total (35) is under the 40 cap; `# Rubric 1` on a non-milestone task is allowed per guidelines.

**Insights (concise):**

- `instruction.md:1` states the calendar HTTP service is **pre-built**; agent work is only `analytics.tcl` (22 procedures, §8–§29).
- Platform rubric (`entire-report.txt:451–469`) has **zero** criteria for `/peak`, `/schedule`, `/coloring`, `read_events_se`, or any analytics endpoint.
- `tests/conftest.py:14–26` starts/resets the service — LLMaJ/Harbor warning about missing conftest is **stale/false**.
- `requirements.lock` pins all pip deps with `==`; audit #14 flag is a **false positive** (installs from lockfile).
- `driver.py` only calls `http://127.0.0.1:8080` — audit #13 web-fetch flag is a **false positive**.
- Worst-model pass rate 60% (GPT-5.5) → medium tier; Claude 100% does not block (#54).
- Oracle not run locally (Docker daemon unavailable); static review of `solve.sh` shows it copies a full `analytics.tcl` implementation.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric grades the wrong scope of work: pre-built event CRUD/BST/query endpoints instead of the 22 analytics procedures the agent must implement | `instruction.md:1-5` — pre-built service; implement `analytics.tcl` only; `environment/app/src/analytics.tcl:1-8` — all procs stubbed `not implemented`; `solution/solve.sh:5` — oracle only copies `analytics.tcl`; `entire-report.txt:451-463` — all 13 positive rubric lines reward `POST /events`, BST links, `/stab`, `/overlap`, PUT/DELETE, `/stats`; no line mentions `peak_concurrency`, `compute_coloring`, `read_events_se`, or any §8–§29 endpoint | Rewrite platform rubric around analytics procedures and HTTP endpoints actually tested: `/peak`, `/schedule`, `/gaps`, `/coverage`, `/longest_gap`, `/density`, `/timeline`, `/conflicts`, `/heatmap`, `/merge`, `/event_concurrency`, `/free_slots`, `/weighted_schedule`, `/coloring`, `/concurrency_runs`, `/interval_cover`, `/earliest_available`, `/room_schedule`, `/overlap_components`, `/depth_profile`, `/window_stats`, plus `read_events_se` helper behavior and sort/tie-break rules from SPEC §8–§29 |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Rubric is for wrong scope — grades CRUD/BST not analytics (ChatGPT High) | **Agree** | `instruction.md:1-5`; `entire-report.txt:451-469` vs `tests/test_outputs.py:121+` (§8–§29 tests); zero rubric lines for analytics |
| 2 | Task itself is strong; service-startup warning not a blocker (ChatGPT Medium None) | **Agree** | `tests/conftest.py:14-26` autostarts service; `tests/test.sh:15` runs pytest only |
| 3 | Optional: update `test_outputs.py` header (six endpoints only) (ChatGPT Low) | **Agree (Low only)** | `tests/test_outputs.py:1-8` lists six endpoints; suite now covers §8–§29 |
| 4 | Optional: one-line endpoint inventory in instruction (ChatGPT Low) | **Agree (Low only)** | `instruction.md` is 7 lines; `SPEC.md` §8–§29 has full detail |
| 5 | Dockerfile digest-pinned; no base-image blocker (ChatGPT) | **Agree** | `environment/Dockerfile:3` — `python:3.13-slim-bookworm@sha256:01f42367…`; Tcl via apt; pytest venv justified |
| 6 | Non-canonical Docker base warning (entire-report WARNING #1) | **Disagree as blocker** | Digest-pinned official Python image; Tcl installed offline — standard pattern |
| 7 | Instruction brevity relies on SPEC.md (entire-report WARNING #2) | **Disagree as blocker** | `instruction.md:5` explicitly delegates to `/app/SPEC.md` §8–§29; LLMaJ `behavior_in_task_description: pass` |
| 8 | Missing conftest.py / no service startup (entire-report WARNING/SUGGESTION) | **Disagree** | `tests/conftest.py` exists; session fixture stops, resets DB, starts service |
| 9 | `#13` runtime web fetch in driver.py (auto audit) | **Disagree** | `environment/app/scripts/driver.py:12-22` — localhost `requests` only; no external URL fetch |
| 10 | `#14` unpinned pip (auto audit) | **Disagree** | `environment/requirements.lock:1-12` — all `==`; Dockerfile installs lockfile |
| 11 | `#41` stray `audit-report.md` (auto review) | **Disagree** | Reviewer-generated by `./scripts/terminus audit`, not author submission |
| 12 | `#27` phantom numeric thresholds (auto audit) | **Disagree** | Thresholds are test window parameters; normative behavior in `SPEC.md` §8–§29 referenced by `instruction.md:5` |
| 13 | `#28` format-heavy tests (auto audit) | **Disagree** | Tests use independent Python oracles and algorithmic discriminators (`test_schedule_defeats_greedy_by_start`, `test_coloring_three_way_clique_needs_three_colors`, etc.) |
| 14 | Non-milestone task uses milestone rubric format (`# Rubric 1`) (user question) | **Disagree as blocker** | `task.toml:9` `number_of_milestones = 0`; `entire-report.txt:450` has only `# Rubric 1` (no `# Rubric 2+`); `docs/guidelines/rubrics.md:66` — `# Rubric 1` optional on non-milestone tasks |
| 15 | Rubric positive total >40 (user concern) | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 35/40 PASS |
| 16 | Instruction sufficiency PASS; failures are agent errors (entire-report LLMaJ) | **Agree** | `entire-report.txt:271-272`; agents 189–190/193 tests passed; coloring/heatmap edge cases |
| 17 | Test quality ACCEPT (entire-report) | **Agree** | ~193 tests; oracle cross-checks per endpoint; `tests/test_outputs.py` section headers §8–§29 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~105 words, 4 prose blocks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt | Conversational task framing, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose only | `instruction.md` |
| 4 | CHECK | No step by step instructions | No HOW walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States WHAT; algorithms in SPEC only | `instruction.md:5` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal + SPEC reference for all contracts | `instruction.md:1-5`, `SPEC.md` §8–§29 |
| 8 | CHECK | Instruction is interesting | Deep Tcl interval analytics; realistic calendar API | task content |
| 9 | UNCHECK | Instruction is unique | Cannot verify vs TB2/TB3 corpus | — |
| 10 | CHECK | All paths absolute | `/app/src/analytics.tcl`, `/app/SPEC.md` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | Dockerfile no web content grab | No runtime external fetch | `environment/Dockerfile`, `driver.py` |
| 14 | CHECK | Python deps pinned | `requests==2.32.3`, etc. in lockfile | `environment/requirements.lock` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:3` |
| 16 | CHECK | Environment context scoped | `COPY app/` only | `environment/Dockerfile:23` |
| 17 | CHECK | No solution/ground truth in env | Stub `analytics.tcl` raises not implemented | `environment/app/src/analytics.tcl:6-8` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest venv in Dockerfile; `test.sh` no installs | `Dockerfile:18-21`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Docker daemon unavailable locally | oracle run failed |
| 22 | CHECK | Oracle no internet | `solve.sh` copies local file only | `solution/solve.sh:5-7` |
| 23 | CHECK | Oracle reflective | Full algorithmic `analytics.tcl` (835 lines) | `solution/source/analytics.tcl`, `solve.sh` |
| 24 | CHECK | test.sh reward path | Writes `0` first; `1` on pytest success | `tests/test.sh:4-5,17-22` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0/1 via reward.txt | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | Instruction → SPEC §8–§29; tests cover all endpoints | `instruction.md:5`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness | Independent oracles + discriminators | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation | HTTP JSON asserts only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact matching | Algorithmic/numeric checks | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 negatives | `entire-report.txt:464-469` |
| 33 | CHECK | Rubric scores in allowed set | All ±1,2,3,5 | `entire-report.txt:451-469` |
| 34 | CHECK | Rubric Agent format | 19 properly formatted lines | `entire-report.txt:451-469` |
| 35 | UNCHECK | Rubric detailed and task-aligned | Criteria precise but grade wrong work (pre-built CRUD/BST, not analytics) | `entire-report.txt:451-469` vs `instruction.md:1-5` |
| 36 | CHECK | Rubric positive language | Negatives are penalty criteria; positives affirmative | `entire-report.txt:451-469` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:451-469` |
| 38 | CHECK | Rubric no metadata refs | None | `entire-report.txt:451-469` |
| 39 | CHECK | Rubric no oracle mentions | None | `entire-report.txt:451-469` |
| 40 | CHECK | Required files present | All core files exist | task tree |
| 41 | CHECK | No unnecessary parent files | No stray author files; `audit-report.md` is reviewer artifact | — |
| 42 | CHECK | author_name/email present | Set in task.toml | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, tags, timeouts, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | `tcl`, `data-processing`, analytics tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty present | `medium` in task.toml; worst-model 60% → medium tier | `task.toml:6`, `entire-report.txt:14-20` |
| 46 | UNCHECK | steps/ milestone layout | N/A — non-milestone task | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth | Solution not in image; stub in env | `environment/Dockerfile:23` |
| 52 | CHECK | Agent cannot trivially cheat | Dynamic DB state; oracle cross-checks | `tests/test_outputs.py`, `conftest.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:19-20` |
| 55 | CHECK | Not unfair | Comprehensive SPEC; service autostart; fair failures on hard algos | `SPEC.md`, `conftest.py`, agent stats |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 35, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Implement 22 analytics procs in `analytics.tcl` | All §8–§29 HTTP tests + implicit `read_events_se` via dependents | covered | `instruction.md:3-5`; `analytics.tcl:5-125` |
| `GET /peak` sweep-line concurrency (§8) | `test_peak_basic_max_and_instant`, `test_peak_earliest_tiebreak_on_equal_concurrency`, … | covered | `tests/test_outputs.py:121+`; `SPEC.md:402` |
| `GET /schedule` activity selection (§9) | `test_schedule_defeats_greedy_by_start`, `test_schedule_optimal_5_defeats_length_greedy`, … | covered | `tests/test_outputs.py:174+`; `SPEC.md:414` |
| `GET /gaps` free intervals (§10) | `test_gaps_basic_between_events`, `test_gaps_clips_and_merges_nested_and_overhang`, … | covered | `tests/test_outputs.py:230+`; `SPEC.md:420` |
| `GET /coverage` (§11) | `test_coverage_oracle_cross_check`, discriminators | covered | `tests/test_outputs.py:357+`; `SPEC.md:426` |
| `GET /longest_gap` (§12) | `test_longest_gap_tie_returns_earliest`, … | covered | `tests/test_outputs.py:480+`; `SPEC.md:430` |
| `GET /density` (§13) | `test_density_overlap_no_double_count`, … | covered | `tests/test_outputs.py:585+`; `SPEC.md:434` |
| `GET /timeline` (§15) | `test_timeline_oracle_cross_check`, … | covered | `tests/test_outputs.py:977+`; `SPEC.md:467` |
| `GET /conflicts` (§16) | `test_conflicts_sorted_by_start_ms_then_id`, … | covered | `tests/test_outputs.py:1082+`; `SPEC.md:471` |
| `GET /heatmap` (§17) | `test_heatmap_histogram_sums_to_slot_width`, … | covered | `tests/test_outputs.py` §17; `SPEC.md:542` |
| `GET /merge` (§18) | `test_merge_touching_not_merged`, … | covered | `SPEC.md:553` |
| `GET /weighted_schedule` (§21) | `test_weighted_schedule_oracle_cross_check`, … | covered | `SPEC.md:570` |
| `GET /coloring` (§22) | `test_coloring_three_way_clique_needs_three_colors`, … | covered | `SPEC.md:581` |
| `GET /room_schedule` (§26) | `test_room_schedule_two_rooms_defeats_single_room_greedy`, … | covered | `SPEC.md:664` |
| `GET /window_stats` (§29) | `test_window_stats_variance_population_discriminator`, … | covered | `SPEC.md:751` |
| Pre-built CRUD/BST endpoints (§4–§7) | Not directly tested (pre-built in `calendar_server.tcl`) | N/A — not agent scope | `instruction.md:1`; rubric incorrectly targets these |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, blocker 1, claims 1, 7, 14 |
| `task.toml` | #45, #46–49 N/A, claim 14 |
| `environment/Dockerfile` | #13–#15, #20, claims 5–6 |
| `environment/requirements.lock` | #14, claim 10 |
| `environment/app/SPEC.md` | #27, spec alignment §8–§29 |
| `environment/app/src/analytics.tcl` | #17, blocker 1 |
| `environment/app/src/calendar_server.tcl` | blocker 1 (pre-built service) |
| `tests/conftest.py` | claims 2, 8 |
| `tests/test.sh` | #20, #24–#26 |
| `tests/test_outputs.py` | #27–#31, spec alignment |
| `solution/solve.sh` | #22–#23 |
| `entire-report.txt` | #32–#39, #45, #54, rubric blocker, agent stats |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tcl-interval-tree-calendar.
Summary: 0 error(s), 4 warning(s), 2 info
Task type detected: regular
```

Warnings: solution-hint heuristics on SPEC.md/test_outputs.py (false-positive “first run” patterns); pip pin heuristic (lockfile is pinned).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Per platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | medium |
| Platform classified | medium |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `tcl-interval-tree-calendar.`; regular layout; Tcl analytics |
| 1 Instruction | ☑ | Brief, delegates to SPEC §8–§29; pre-built service stated |
| 2 Environment | ☑ | Digest-pinned Python+Tcl; tmux/asciinema; offline |
| 3 Oracle | ☑ | Static review OK; local run blocked (no Docker) |
| 4 Verifiers | ☑ | conftest autostart; reward block canonical; ~193 tests |
| 5 Metadata | ☑ | medium, data-processing, tcl tags fit |
| 6 Rubric | ☑ | **Blocker:** wrong scope; 35/40 pts; `# Rubric 1` format OK |
| 7 LLMaJ & agents | ☑ | Strong pass rates; coloring hardest failure mode |
| 8 Novelty & fairness | ☑ | Multi-algorithm Tcl task; anti-cheat solid |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the SPEC is thorough, the test suite with independent Python oracles is excellent, and the offline Dockerfile/conftest setup is solid. Agents are clearly being evaluated on the right hard problems (coloring, heatmap histograms, peak-duration runs). One fix needed before accept: the platform rubric still grades the pre-built CRUD/BST endpoints (`POST /events`, `/stab`, `/overlap`, `/stats`, etc.) even though instruction.md tells the agent the HTTP service is already built and their job is only the 22 analytics procedures in `/app/src/analytics.tcl`. Please rewrite the rubric around the analytics endpoints and helper behavior that the tests actually exercise — peak, schedule, gaps, coverage, coloring, room scheduling, overlap components, and the rest of §8–§29.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
