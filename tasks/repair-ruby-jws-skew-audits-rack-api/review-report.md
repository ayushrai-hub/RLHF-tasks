# Terminus Review Report: repair-ruby-jws-skew-audits-rack-api

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Harbor local error); report shows 100% (3/3) |
| **CHECK count** | 52 |
| **UNCHECK count** | 3 |

**Error categories (internal):** none

**Decision (concise):** This is a well-built 3-milestone Ruby JWS repair task with strong behavior tests, pinned offline deps, correct milestone `task.toml` layout, and a properly formatted platform rubric (three `# Rubric N` blocks, each ≤40 positive pts). External “Needs Revision” claims (missing root-level timeouts, difficulty mismatch, mandatory source-string test, verifier source-grep) do not hold against Edition 2 rules. No High or Medium blockers found.

**Insights (concise):**

- Milestone `task.toml` correctly uses per-step `[steps.agent]` / `[steps.verifier]` only; root-level sections are **not** required (`docs/guidelines/milestones.md:99`, `docs/task-requirements.md:107`).
- Platform rubric uses correct milestone format; per-block positives are 25 / 24 / 21 (all ≤40). Total 70 is expected for 3 milestones.
- `validate_task.py` flags `curl` in `test.sh`, but it is a localhost `/health` probe (not `pip`/`apt`); deps are baked in the Dockerfile (`reviewer-checklist-ui.md` #20 note).
- Tests do **not** grep `policy_client.rb`; the deprecated-path rule exists only in `api-reference.md` and rubric trace grading.
- Prior reviewer claim that agent docs leak per-`asrt-*` decisions is unsupported — environment docs state rules generically; spot-checks live in tests/rubric only.
- Worst-model pass rate 40% (GPT-5.5) fits medium tier; `difficulty = "hard"` in `task.toml` is informational only, not a blocker.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Missing root-level `[verifier]` / `[agent]` in `task.toml` (ChatGPT / Harbor review WARNING) | **Disagree** | `task.toml:24-49` has per-step timeouts only. Milestone rule: “**No** top-level `[agent]` or `[verifier]`” (`docs/guidelines/milestones.md:99`, `docs/task-requirements.md:107`). |
| 2 | Align `difficulty` to medium (ChatGPT Medium) | **Disagree** (not a blocker) | `task.toml:6` `difficulty = "hard"`; report L20–26 shows platform MEDIUM, worst-model 40%. `prompt.md:477-484` — declared vs platform mismatch never blocks. |
| 3 | `api-reference.md` requires `policy_client.rb` must not contain `/api/v2/jwks` even in comments; remove or soften (ChatGPT Medium) | **Partially agree** (Low only) | `environment/workspace/docs/api-reference.md:56` states rule; `steps/milestone_1/tests/test_m1.py` has no source read/grep; rubric L508 penalizes in trace only. Not tested behavior — optional doc/rubric cleanup, not Revise. |
| 4 | Remove or deprecate unused Flask `app.py` (ChatGPT / Harbor WARNING) | **Agree** (Low only) | `environment/workspace/stampgate-api/app.py` exists; `start-stampgate-api.sh` launches `app.rb`. Agent confusion risk only — optional cleanup. |
| 5 | Verifier reads `policy_client.rb` and checks forbidden route string (prior Reviewer Feedback) | **Disagree** | Grep across `steps/**/test*.py`: no `policy_client.rb` or `/api/v2/jwks` assertions. Only `test_m1.py:101` `read_text(POLICY_PATH)` on output JSON. |
| 6 | Agent-facing docs give away exact `asrt-*` outcomes (prior Reviewer Feedback) | **Disagree** | Environment docs (`policy-handbook.md`, `operations-chronicle.md`, `api-reference.md`) describe rules generically. No per-row decision table in agent docs. `asrt-*` expectations appear in `test_m2.py` / `test_m3.py` and platform rubric trace lines only. |
| 7 | Milestone write-ups split into too many sections with command blocks (prior Reviewer Feedback) | **Disagree** | `steps/milestone_1/instruction.md` (6 lines), `milestone_2` (7 lines), `milestone_3` (7 lines) — concise, no `##` headers or command walkthroughs. |
| 8 | Rubric positive total 70 exceeds 40 → Revise (automated `rubric-points` script) | **Disagree** | Milestone task (`task.toml:9` `number_of_milestones = 3`). Cap is **per `# Rubric N` block** (`docs/guidelines/rubrics.md:31-33`): blocks 25, 24, 21 — all ≤40. |
| 9 | `test.sh` runtime network install (`curl`) fails validation | **Partially agree** (validator only) | All three `test.sh` files L14: `curl -sf http://127.0.0.1:8966/health` — localhost probe, not package install. `environment/Dockerfile:11` installs `curl`. `#20` intent: deps in image, no `pip`/`apt` in test.sh (`reviewer-checklist-ui.md:28-32`). |
| 10 | LLMaJ / instruction sufficiency: systematic spec gaps | **Disagree** | `entire-report.txt` L179–180 behavior_in_task_description PASS; L109–161 agent failures attributed to crypto implementation, not missing spec. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Three milestone prompts, ~4–7 sentences each; no long spec dumps | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer ticket style (“X is broken. Repair…”) | `steps/milestone_1/instruction.md:1` |
| 3 | CHECK | No excessive markdown | No `##`/tables/code blocks in milestone instructions | milestone `instruction.md` files |
| 4 | CHECK | No step-by-step HOW | Requirements only; points to docs/schemas | milestone `instruction.md` files |
| 5 | CHECK | No hints/solving strategies | WHAT to produce, not repair steps | milestone `instruction.md` files |
| 6 | CHECK | No design-doc I/O tables in prompt | Tables only in environment API docs | milestone `instruction.md` files |
| 7 | CHECK | Well specified | Absolute paths, schemas, env guards, output files named | milestone `instruction.md` files |
| 8 | CHECK | Interesting | Realistic JWS/crypto/Rack repair scenario | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3 index from artifacts | — |
| 10 | CHECK | Absolute paths | `/workspace/...` throughout instructions | milestone `instruction.md` files |
| 11 | CHECK | Task name not in instruction | No folder name in prompts | milestone `instruction.md` files |
| 12 | CHECK | No canary string | None detected | milestone `instruction.md` files |
| 13 | CHECK | No runtime web fetch in env code | Fixtures generated at build; API local | `environment/Dockerfile`, `generate_stampgate.py` |
| 14 | CHECK | Pinned pip deps | Hash-pinned lockfile install | `environment/Dockerfile:19-21`, `requirements.lock` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367…` | `environment/Dockerfile:2` |
| 16 | CHECK | Build context scoped | COPY only from `environment/` | `environment/Dockerfile:23-24` |
| 17 | CHECK | No ground-truth leakage in env | Docs state rules; no per-row answer tables | `environment/workspace/docs/*.md` |
| 18 | CHECK | No privileged Docker | Standard sandbox | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no package installs | pytest/cryptography in image; `curl` is localhost health only | `environment/Dockerfile`, `steps/*/tests/test.sh:14-18` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3); static solve runs real CLI | `entire-report.txt` L30; `solve1.sh:13-15` |
| 22 | CHECK | Oracle no internet/downloads | Oracle uses local API + copied Ruby sources | `solve1.sh:6-15` |
| 23 | CHECK | Oracle derives answers | Copies modules, invokes `stampgate-audit` subcommands | `solve1.sh`, `solve2.sh`, `solve3.sh` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 with failure path | `steps/milestone_1/tests/test.sh:4-25` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | all `test_*.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `test.sh` reward blocks |
| 27 | CHECK | Tests aligned with instructions | Counts/thresholds derivable from ledger/docs; full reference comparisons | `test_m2.py:64-77`, `policy-handbook.md:66`, `generate_stampgate.py:24` |
| 28 | CHECK | Tests check correctness | Reference solver + schema + crypto decisions | `audit_reference.py`, `test_m2_decisions_match_reference` |
| 29 | CHECK | Behavior not implementation grep | No Ruby source inspection in tests | `steps/milestone_1/tests/test_m1.py` |
| 30 | CHECK | No brittle string-only checks | Primary gate is reference parity | `test_m2_decisions_match_reference` |
| 31 | CHECK | Informative test docstrings | All `test_*` documented | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 11 negatives across 3 blocks | `entire-report.txt` L494-538 |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines compliant | `entire-report.txt` L494-538 |
| 34 | CHECK | `Agent …, ±N` one-line format | 40 formatted lines | `entire-report.txt` L494-538 |
| 35 | CHECK | Rubric detailed; positive cap OK | Per-block 25/24/21 ≤40 | `entire-report.txt` L494-538 |
| 36 | CHECK | Positive rubric language | No “Agent does not …, +N” | rubric lines |
| 37 | CHECK | Rubric no /tests/ refs | None | rubric lines |
| 38 | CHECK | Rubric no instruction.md refs | None | rubric lines |
| 39 | CHECK | Rubric no oracle/NOP refs | None | rubric lines |
| 40 | CHECK | Required milestone files present | `environment/`, `steps/milestone_N/{instruction,tests,solution}`, `task.toml` | task tree |
| 41 | CHECK | No unnecessary parent files | No stray `jobs/`, dev notes in task dir | task root |
| 42 | CHECK | author_name / author_email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, milestones, timeouts, estimates | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | security, ruby, api_integration, db_interaction | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard` declared; platform medium — informational | `task.toml:6`, `entire-report.txt` L20 |
| 46 | CHECK | steps/ milestone layout | 3 milestones under `steps/` | `task.toml:24-49` |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | Present with `TestMilestoneN` | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone tests scoped | Each file tests only its subcommand artifact | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | environment build |
| 51 | CHECK | Solution not in image | `.dockerignore` excludes solution | environment build |
| 52 | CHECK | Agent cannot trivially cheat inputs | Decisions from live crypto + API + ledger | `audit_reference.py`, LLMaJ anti_cheat PASS |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt` L25-26 |
| 55 | UNCHECK | Not too hard/unfair | Subjective; partial agent success suggests fairness but borderline Ed25519 difficulty | `entire-report.txt` L109-161 |
| — | UNCHECK | Milestone rubric format check (user ask) | N/A — task **is** milestone (`number_of_milestones=3`); `# Rubric 1/2/3` format is correct, not a non-milestone misformat | `task.toml:9`, `entire-report.txt` L494-538 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: `policy-cache.json` from live API | `test_m1_policy_command_exits_zero`, `test_m1_global_policy_fields` | covered | `test_m1.py:32-58` |
| M1: schema validation | `test_m1_schema_valid` | covered | `test_m1.py:49-53` |
| M1: `STAMPGATE_USE_STATIC_POLICY` guard | `test_m1_static_policy_env_rejects` | covered | `test_m1.py:124-137` |
| M1: exclude pending `hotel` | `test_m1_excludes_pending_hotel` | covered | `test_m1.py:104-107` |
| M2: detached JWS window check all ledger rows | `test_m2_event_count`, `test_m2_decisions_match_reference` | covered | `test_m2.py:64-77` |
| M2: nonce guard / no nonce writes | `test_m2_verify_rejects_nonempty_nonce_cache`, `test_m2_skip_nonce_guard_rejects` | covered | `test_m2.py` |
| M2: do not overwrite policy cache | `test_m2_policy_cache_unchanged` | covered | `test_m2.py` |
| M3: clear `nonce_seen`, record tuples | `test_m3_nonce_cache_rows`, `test_m3_nonce_schema_columns` | covered | `test_m3.py:95-97`, `169-174` |
| M3: replay decisions | `test_m3_asrt007_replay`, `test_m3_decisions_match_reference` | covered | `test_m3.py:70-78`, `80-83` |
| M3: `STAMPGATE_SKIP_NONCE_CLEAR` guard | `test_m3_skip_nonce_clear_rejects` | covered | `test_m3.py:202-215` |
| M3: `recorded_at` = ledger `observed_at_utc` | `test_m3_nonce_recorded_at` | covered | `test_m3.py:158-167`, `policy-handbook.md:66` |
| Doc-only: `policy_client.rb` must not contain `/api/v2/jwks` string | — | phantom (doc/rubric only) | `api-reference.md:56`; no test |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, #46, milestone timeout layout, rubric format context |
| `steps/milestone_*/instruction.md` | #1–#7, #10–#12 |
| `steps/milestone_*/tests/test.sh` | #20, #24, curl adjudication |
| `steps/milestone_*/tests/test_m1.py` | #27, #29, M1 alignment |
| `steps/milestone_*/tests/test_m2.py` | #27, #28, M2 alignment |
| `steps/milestone_*/tests/test_m3.py` | #27, #28, M3 alignment |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/workspace/docs/api-reference.md` | external claim #3, phantom doc rule |
| `environment/workspace/docs/assertion-ledger-format.md` | ledger row count note (says “thirty”, fixture has 35 — doc typo, Low) |
| `docs/guidelines/milestones.md` | root-level timeout adjudication |
| `entire-report.txt` | agent stats, rubric, LLMaJ, prior feedback |

---

## 7. Validation & agent performance

### Validation

```
ERROR: test.sh [steps/milestone_1/tests/test.sh]: Runtime network install not allowed: curl\s+
ERROR: test.sh [steps/milestone_2/tests/test.sh]: Runtime network install not allowed: curl\s+
ERROR: test.sh [steps/milestone_3/tests/test.sh]: Runtime network install not allowed: curl\s+
```

Validator heuristic only — `curl` used for localhost `/health`, not package install. Not treated as a portal blocker (#20).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40% (2/5) | Dominant M2/M3 crypto gaps |
| terminus-claude-opus-4-8 | 100% (5/5) | |
| oracle | 100% (3/3) | from report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | informational only (not blocker) |

### Rubric (milestone)

| Block | Positive pts | Cap | Status |
|-------|-------------|-----|--------|
| # Rubric 1 | 25 | 40 | PASS |
| # Rubric 2 | 24 | 40 | PASS |
| # Rubric 3 | 21 | 40 | PASS |
| **Total** | **70** | N×10–40 expected for 3 milestones | PASS |

Format: milestone task correctly uses `# Rubric 1/2/3` headers — **not** a non-milestone task misformatted into milestone rubric.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone Ruby JWS task; report matches folder |
| 1 Instruction | ☑ | Concise per-milestone prompts; no step-by-step |
| 2 Environment | ☑ | Digest-pinned base, tmux/asciinema, pinned pytest stack |
| 3 Oracle | ☑ | Static review + report 100%; local oracle run failed (Harbor config) |
| 4 Verifiers | ☑ | Behavior/reference tests; reward block OK |
| 5 Metadata | ☑ | Per-step timeouts correct for milestones |
| 6 Rubric | ☑ | Milestone blocks, caps OK, ≥3 negatives |
| 7 LLMaJ & agents | ☑ | Spec sufficient; 40% worst-model |
| 8 Fairness | ☑ | Failures are implementation, not hidden semantics |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task. The three prompts are tight, the Dockerfile and pinned verifier stack are in good shape, and the pytest suites exercise real JWS verification, skew rules, and replay behavior end to end — not source greps. Oracle and agent stats look right for the difficulty band. I don’t see any blocking spec-test gaps. Optional polish if you want it later: drop or mark the unused Flask `app.py` so agents aren’t tempted by a dead server, and either remove the “must not contain `/api/v2/jwks` in source” line from `api-reference.md` or accept it as rubric-only trace grading since tests don’t enforce it.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
| Other | no | — |
