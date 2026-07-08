# Terminus Review Report: `glassreef-planner-hardened-v2`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (platform report 3/3; local oracle not run — Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** No blocking spec, verifier, rubric, or environment issues found. Instruction delegates to five `/app/docs` contracts that fully cover tested behavior (last-row-wins CSV, greedy scheduling, C helpers, digest). Platform rubric is a flat non-milestone list at 33 positive points (≤40 cap) with three negatives. Worst-model pass rate is 60% (medium tier), not >80%. Harbor “non-canonical base” warning is a false positive — digest matches canonical `debian:bookworm-slim`.

**Insights (concise):**

- Multi-language task (Rust/C/Lua/Bash) with strong anti-hardcoding: four of six tests mutate live inputs and compare against an independent reference model.
- `instruction.md` is terse but explicitly names `/app/docs` as source of truth; all algorithm semantics tested are documented there.
- Platform rubric uses correct **flat** format for `number_of_milestones = 0` — no `# Rubric 2+` headers; 33/+11 positives, 3 negatives.
- Agent failures on dynamic override tests are implementation bugs (ship re-ranking), not hidden verifier semantics — documented in `cable_network_contract.md` and `repair_weather_policy.md`.
- `task.toml` declares `hard` while platform classifies `medium` — informational only, not a blocker per difficulty policy.
- Optional polish: use ECR canonical path for debian base, expand instruction by 1–2 sentences, fix stale test name in one rubric line.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High/Medium blockers; Accept | Agree | Full artifact audit; rubric 33/40; docs cover tested semantics; oracle 100% in report |
| 2 | ChatGPT: Terse instruction acceptable because `/app/docs` is source of truth | Agree | `instruction.md:1-3`; docs at `environment/app/docs/*.md` specify schema, last-row-wins, scoring, digest |
| 3 | ChatGPT: Non-canonical base acceptable with multi-language justification | Agree | `environment/Dockerfile:1-2` comment + digest `sha256:4724b8cc…` matches canonical `debian:bookworm-slim` in `docs/guidelines/dockerfxile.md:22` |
| 4 | ChatGPT: Optional `set -e` in test.sh | Agree (Low only) | `tests/test.sh:2` uses `set -uo pipefail`; explicit `rc=$?` check at `:10-15` — works without `-e` |
| 5 | ChatGPT: Metadata hard vs platform medium not blocking | Agree | `task.toml:6` `hard`; `entire-report.txt:20` `MEDIUM`; worst-model 60% — per `prompt.md` declared-vs-platform never blocks |
| 6 | Harbor REVIEW REPORT: Non-canonical Docker base → NEEDS REVISION | Disagree | Same digest as canonical debian bookworm-slim; Dockerfile justification present; only registry prefix differs (`debian:` vs `public.ecr.aws/...`) |
| 7 | Harbor REVIEW REPORT: Instruction too terse → borderline underspecified | Partially agree | Terse (`instruction.md` ~4 lines) but docs delegation is explicit and contracts are complete — Low polish, not Medium |
| 8 | LLMaJ `behavior_in_task_description`: FAIL then “this is a pass” | Disagree with FAIL | Docs referenced as normative spec; last-row-wins at `cable_network_contract.md:3`; digest at `digest_notes.md:3` |
| 9 | LLMaJ/agent analysis: Dynamic override failures are spec gaps | Disagree | `cable_network_contract.md:3` last-row-wins; `repair_weather_policy.md:13` greedy ranking; agent bugs not missing spec |
| 10 | Audit #44: category `scientific-computing` mismatch → debugging | Partially agree | Primary activity is repair/debugging, but ocean modeling, numerical C helpers, and graph scheduling fit `scientific-computing` — Low metadata polish, not blocker |
| 11 | Audit #27 phantom threshold `[1000]` | Disagree as gap | `tests/test_outputs.py:398` `score > 1000` is mutation-test sanity check after profile priority 404 patch, not a global spec requirement |
| 12 | User concern: non-milestone task in milestone rubric format | Disagree (no issue) | `entire-report.txt:313-326` flat `Agent …, ±N` list; no `# Rubric N` headers; `task.toml:9` `number_of_milestones = 0` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 2 paragraphs, ~108 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational repair request, not spec dump | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Describes goal + doc reference only | `instruction.md` |
| 5 | CHECK | No hints/strategies | No solve walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, output path, doc contracts named | `instruction.md:1-3` |
| 8 | CHECK | Interesting | Realistic multi-language ops/planning scenario | task content |
| 9 | UNCHECK | Unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | No task name in instruction | No folder/slug name | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local COPY only | `environment/Dockerfile:10` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:8` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:4724b8cc…` | `environment/Dockerfile:2` |
| 16 | CHECK | Build context scoped | `COPY app/ /app/` only | `environment/Dockerfile:10` |
| 17 | CHECK | No ground truth in env | Stub planner only; docs are contracts not golden output | `environment/app/src/bin/glassreef_planner.rs:14-15` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:8`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:30` |
| 22 | CHECK | Oracle offline | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | 377-line Rust planner, not hardcoded JSON | `solution/source/glassreef_planner.rs` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on failure and success | `tests/test.sh:6-15` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:11-14` |
| 27 | CHECK | Tests aligned with instruction/docs | All assertions trace to `/app/docs` contracts | §5 below |
| 28 | CHECK | Tests check correctness | Full-plan equality vs reference model | `tests/test_outputs.py:318-323` |
| 29 | CHECK | Behavior not implementation grep | Runs planner, compares output | `tests/test_outputs.py:18-32` |
| 30 | CHECK | No brittle string matching | Structural JSON/model comparison | `tests/test_outputs.py:318-323` |
| 31 | CHECK | Informative test docstrings | All 6 tests documented | `tests/test_outputs.py:326-404` |
| 32 | CHECK | ≥3 rubric negatives | 3 negatives (-5, -3, -3) | `entire-report.txt:324-326` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines valid | `entire-report.txt:313-326` |
| 34 | CHECK | Rubric Agent format | 14 properly formatted lines | `entire-report.txt:313-326` |
| 35 | CHECK | Rubric detailed; positive cap | 33 positive pts ≤ 40 | `./scripts/terminus rubric-points` |
| 36 | CHECK | Positive rubric language | No “Agent does not X, +N” positives | `entire-report.txt:313-326` |
| 37 | CHECK | Rubric no /tests/ refs | No `/tests/` or pytest refs | `entire-report.txt:313-326` |
| 38 | CHECK | Rubric no metadata/instruction refs | No task.toml/instruction.md | `entire-report.txt:313-326` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:313-326` |
| 40 | CHECK | Required files present | All standard paths exist | task tree |
| 41 | CHECK | No stray parent files | Clean task root | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Rust/C/Lua/Bash; ocean/graph/scheduling tags fit | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; platform medium informational | `task.toml:6`, `entire-report.txt:20` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore` |
| 51 | CHECK | Solution not accessible | `.dockerignore` excludes solution/ | `environment/.dockerignore:6` |
| 52 | CHECK | Agent cannot trivially cheat | Mutation tests + reference model prevent hardcoding | `tests/test_outputs.py:354-401` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:26` |
| 55 | CHECK | Not unfair | Edge cases documented; failures are implementation precision | `entire-report.txt:79-80`, docs |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/repair_plan.json` deterministic | `test_report_is_deterministic_and_inputs_are_not_mutated` | covered | `instruction.md:1`; `tests/test_outputs.py:403-419` |
| JSON schema + digest format | `test_schema_and_digest_are_valid` | covered | `repair_report_schema.md`; `digest_notes.md`; `tests/test_outputs.py:326-345` |
| Last-row-wins CSV duplicate keys | `test_dynamic_feed_overrides_lua_rules_and_hazards_are_live_inputs` | covered | `cable_network_contract.md:3`; `tests/test_outputs.py:354-367` |
| Graph reachability + restored stations | `test_repair_plan_matches_graph_weather_current_splice_hazard_duration_and_mission_policy` | covered | `cable_network_contract.md:7-9`; `tests/test_outputs.py:348-352` |
| C drift helper authoritative | `test_compiled_current_helper_is_authoritative` | covered | `repair_weather_policy.md:5`; `tests/test_outputs.py:370-376` |
| C duration + mission cooldown/blackouts | `test_duration_helper_profiles_and_mission_constraints_are_authoritative` | covered | `repair_weather_policy.md:7-9`; `tests/test_outputs.py:379-400` |
| Greedy scheduling + tie-breaks | `test_repair_plan_matches_*` | covered | `repair_weather_policy.md:13`; `repair_report_schema.md:5` |
| Rejection reason hierarchy | `test_schema_and_digest_are_valid`, full-model test | covered | `repair_report_schema.md:7`; `tests/test_outputs.py:343-345` |
| Live Lua splice rules + hazards | `test_dynamic_feed_overrides_*` | covered | `splice_compatibility_rules.md`; `instruction.md:3` |
| Station profile overlays | `test_duration_helper_profiles_*` | covered | `cable_network_contract.md:5`; `tests/test_outputs.py:382-388` |
| Do not hand-write JSON for default dataset | all tests via `assert_matches_contract` | covered | `instruction.md:3`; `tests/test_outputs.py:318-323` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #42-45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #13-20, base image adjudication |
| `environment/.dockerignore` | #50-51 |
| `environment/app/docs/*.md` | #17, #27, #55, spec alignment |
| `environment/app/src/bin/glassreef_planner.rs` | #17 stub env |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #22-23 |
| `solution/source/glassreef_planner.rs` | #23 |
| `entire-report.txt` | #21, #32-39, #45, #54, rubric format, agent stats |
| `docs/guidelines/dockerfxile.md` | base image canonical digest |
| `docs/guidelines/rubrics.md` | rubric cap + non-milestone format rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate glassreef-planner-hardened-v2/
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

```
./scripts/terminus audit glassreef-planner-hardened-v2/ --report entire-report.txt
Verdict: APPROVED WITH WARNINGS (category heuristic only)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Failures on dynamic override tests |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | yes (field present; mismatch informational) |

### Rubric (platform)

| Field | Value |
|-------|-------|
| Format | Flat list — **not** milestone blocks |
| Positive total | 33 (cap 40) |
| Negative count | 3 |
| `# Rubric N` headers | None — correct for non-milestone |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; Rust/C/Lua/Bash |
| 1 Instruction | ☑ | Terse but doc-delegated; absolute paths |
| 2 Environment | ☑ | tmux+asciinema; digest pin; no tests/solution COPY |
| 3 Oracle | ☑ | Full Rust implementation; platform 100% |
| 4 Verifiers | ☑ | 6 behavior tests; reference model; mutation anti-cheat |
| 5 Metadata | ☑ | Category borderline but applicable; timeouts plausible |
| 6 Rubric | ☑ | Flat non-milestone format; 33 pts; 3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Failures are implementation bugs, not spec gaps |
| 8 Novelty & fairness | ☑ | Multi-step; cheating paths closed |
| 9 Long context | ☐ N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — it's a strong multi-language planning task with excellent anti-cheating design. The contract docs under `/app/docs` fully cover what the verifiers check (CSV last-row-wins, greedy scheduling, C helper authority, digest rules), and the mutation tests plus independent reference model make hardcoding impractical. Oracle passes cleanly and agent rates look right for medium difficulty. I didn't find blocking spec gaps or rubric issues — the platform rubric is correctly formatted as a flat list (not milestone blocks) at 33 positive points. Optional polish: expand `instruction.md` by a sentence or two pointing at the key doc filenames, and consider switching the Dockerfile `FROM` to the ECR canonical debian path (same digest you already use).

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
