# Terminus Review Report: claimtower_milestone_go_task_v13

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (submission export: 100% 3/3) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Strong three-milestone Go task with pinned offline env, correct milestone rubric layout, and robust M2/M3 verifiers. The only real blockers are Milestone 1 spec↔test gaps: required per-claim output fields are not value-asserted, and two documented ingestion rules (cancelled/canceled filtering, same-file source-line duplicate tie-break) have no targeted tests. Fix M1 assertions first; tag count (7) is advisory only.

**Insights (concise):**

- ChatGPT’s three M1 findings are confirmed in `test_m1.py`; LLMaJ `behavior_in_tests` overclaims M1 coverage for cancelled/canceled and claim source-line ties.
- Rubric correctly uses `# Rubric 1/2/3` milestone blocks (10/11/11 positive pts each, all ≤40); this is not a flat non-milestone rubric.
- Automated `#1` fail (combined 1101 words across three step instructions) is a false positive — each step instruction is one dense paragraph.
- Automated `#31` fail (module-level docstrings) is a false positive — all 17 test methods have informative docstrings.
- Automated `#36` fail triggers on negative line “Agent fails to emit…” — acceptable negative phrasing with `-3`, not a positive-criterion violation.
- Worst-model 60% (Claude Opus 4.8); declared `hard` vs platform `medium` is informational only.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #28 | M1 never asserts exact values for required per-claim fields `product`, `loss_date`, `severity`, `handler`, `source_line` (and per-claim `reserve`/`paid`); a solution can emit empty/wrong values and pass. | `steps/milestone_1/tests/test_m1.py:67-73` asserts only `revision`, `status`, `age_days`, `county`, `source_file` for sample claims; `steps/milestone_1/instruction.md:11` requires all 13 claim fields | Add exact assertions (e.g. CLM-001 `product=="auto"`, `loss_date=="2026-05-30"`, `severity==3`, `handler=="Uma"`, `source_line==4`; CLM-002 alias-resolved fields; CLM-TIE `source_line==1`) |
| 2 | High | Test Alignment/Coverage Issues | #27, #28 | M1 does not test `cancelled` / `canceled` status filtering — only `closed` is exercised. | `steps/milestone_1/instruction.md:9` requires ignoring closed/cancelled/canceled; `test_m1.py:50` only has `status: "closed"`; no cancelled/canceled rows | Add `cancelled` and `Canceled` rows; assert neither appears in output `claims` |
| 3 | High | Test Alignment/Coverage Issues | #27, #28 | M1 does not test same-file duplicate tie-break by lower `source_line` when revision and path tie. | `steps/milestone_1/instruction.md:9` three-level tie-break; `test_m1.py:53-57` CLM-TIE tests path tie across files only | Add two same-revision rows in one `.claim.jsonl` at different lines; assert lower-line row wins (e.g. by `reserve` or `handler`) |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M1 missing assertions for product, loss_date, severity, handler, source_line (ChatGPT / test-quality review) | **Agree** | `test_m1.py:67-73`; instruction `steps/milestone_1/instruction.md:11` |
| 2 | M1 missing cancelled/canceled filtering tests (ChatGPT / test-quality review) | **Agree** | `test_m1.py:50` only `closed`; instruction line 9 |
| 3 | M1 missing same-file source-line duplicate tie-break (ChatGPT / test-quality review) | **Agree** | `test_m1.py:53-72` path tie only; instruction line 9 |
| 4 | 7 tags above 3–6 recommended range (ChatGPT / Harbor review) | **Agree (Low only)** | `task.toml:12` has 7 tags; validate warns; not a Revise blocker per severity rules |
| 5 | LLMaJ `behavior_in_tests`: M1 covers cancelled/canceled and source-line ties (entire-report) | **Disagree** | `test_m1.py` lacks cancelled/canceled rows and same-file line tie scenario |
| 6 | Harbor RECOMMENDATION: READY TO USE (entire-report) | **Partially agree** | Env/oracle/M2/M3 strong; M1 vulnerable per artifacts |
| 7 | Non-canonical Go base image (Harbor review) | **Disagree as blocker** | `environment/Dockerfile:2` digest-pinned; `environment/docs/base-image-justification.md` documents Go toolchain need |
| 8 | Automated review `#1` instruction too long | **Disagree** | Each `steps/milestone_N/instruction.md` is one paragraph (~150–250 words); script incorrectly sums all three |
| 9 | Automated review `#31` missing docstrings | **Disagree** | All 17 `test_*` methods have docstrings; only module-level docstrings absent (validate warning) |
| 10 | Automated review `#36` rubric negative phrasing | **Disagree** | Negative criterion “Agent fails to emit backlog…” uses `-3`; positive criteria use affirmative phrasing |
| 11 | Rubric positive total 11 from script | **Disagree (parser artifact)** | Manual count: Rubric 1 = 10, Rubric 2 = 11, Rubric 3 = 11 (`entire-report.txt:539-565`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction is one paragraph; combined-word-count heuristic is N/A for milestone layout | `steps/milestone_1/instruction.md` (12 lines) |
| 2 | CHECK | Natural prompt tone | Conversational “Please finish…” framing, not audit-spec tone | `steps/milestone_1/instruction.md:3` |
| 3 | CHECK | No excessive markdown | Single `#` title per step; no tables/code blocks in instructions | step instruction files |
| 4 | CHECK | No step-by-step HOW | States commands and requirements, not dev workflow steps | step instruction files |
| 5 | CHECK | No hints/strategies | WHAT to build; algorithm left to agent + contract doc | step instruction files |
| 6 | CHECK | No design-doc I/O tables | No input→output mapping tables in instructions | step instruction files |
| 7 | CHECK | Well specified | CLI flags, schemas, tie-breaks, issue tokens specified | `claimtower-contract.md`, step instructions |
| 8 | CHECK | Interesting | Realistic insurance claim pipeline with optimization | task content |
| 9 | CHECK | Unique | Staged Go CLI with portfolio optimizer; no duplicate detected in review | — |
| 10 | CHECK | Absolute paths | `/workspace/...` throughout | step instruction files |
| 11 | CHECK | Task name not in instruction | No “claimtower_milestone” string in instructions | step instruction files |
| 12 | CHECK | No canary string | None found | step instruction files |
| 13 | CHECK | No web content fetch | Offline env; `allow_internet=false` | `task.toml:17`, Dockerfile |
| 14 | CHECK | Pinned pip deps | No pip in Dockerfile; apt only | `environment/Dockerfile` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452...` | `environment/Dockerfile:2` |
| 16 | CHECK | Context in environment/ | COPY limited to env subdirs | `environment/Dockerfile:22-28` |
| 17 | CHECK | No ground-truth answers | Contract is schema/rules; stub `app.go` only | `environment/internal/app/app.go` |
| 18 | CHECK | No dangerous Docker ops | Standard RUN apt; no privileged | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest via apt; test.sh no installs | Dockerfile + `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | Submission export: oracle 100% (3/3); local oracle not re-run | `entire-report.txt:25` |
| 22 | CHECK | Oracle offline | solve scripts use heredoc Go; no network | `steps/milestone_1/solution/solve1.sh` |
| 23 | CHECK | Oracle reflective | Full Go implementation in solveN.sh, not echoed outputs | `steps/milestone_1/solution/solve1.sh` |
| 24 | CHECK | reward.txt canonical | mkdir + binary 0/1 in each test.sh | `steps/milestone_1/tests/test.sh:3-16` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | test.sh + test_m*.py |
| 26 | CHECK | Binary rewards only | 0 or 1 only | test.sh files |
| 27 | UNCHECK | Tests aligned with instructions | M1 instruction requirements untested (fields, cancelled/canceled, line tie) | Blockers 1–3 |
| 28 | UNCHECK | Tests check correctness | M1 passes with wrong/empty values for 5+ required claim fields | `test_m1.py:67-73` |
| 29 | CHECK | Behavior not implementation | subprocess CLI + output assertions | test_m*.py |
| 30 | CHECK | Not brittle where avoidable | Exact asserts appropriate for deterministic TSV/JSON | test_m*.py |
| 31 | CHECK | Informative test names/docstrings | All 17 test methods have docstrings | test_m1.py, test_m2.py, test_m3.py |
| 32 | CHECK | ≥3 negative rubric criteria | 9 negatives (3 per block) | `entire-report.txt:544-564` |
| 33 | CHECK | Valid rubric scores | Only ±1,2,3,5 | rubric lines |
| 34 | CHECK | Agent line format | 18 Agent lines across 3 blocks | rubric lines |
| 35 | CHECK | Detailed rubric criteria | Task-specific ingestion/scoring/assignment behaviors | rubric lines |
| 36 | CHECK | Positive rubric phrasing | Positive criteria affirmative; “fails to” only on `-3` negatives | rubric lines |
| 37 | CHECK | Rubric no /tests/ refs | No pytest or /tests/ mentions | rubric lines |
| 38 | CHECK | Rubric no metadata refs | No task.toml or instruction.md | rubric lines |
| 39 | CHECK | Rubric no oracle/NOP | None | rubric lines |
| 40 | CHECK | Required files present | milestone layout: Dockerfile, step solve/test/instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, difficulty, milestones, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages applicable | go/cli/insurance/claims fit; 7 tags is count warning not applicability fail | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `difficulty=hard`; platform medium / 60% worst — informational | `task.toml:8`, `entire-report.txt:15` |
| 46 | CHECK | steps/ milestone layout | 3 milestones under `steps/` | task tree |
| 47 | CHECK | solveN.sh per milestone | solve1.sh, solve2.sh, solve3.sh + wrappers | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py, test_m2.py, test_m3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | M1=ingest only; M2=score; M3=assign | test file contents |
| 50 | CHECK | Tests not in image | No COPY steps/ or tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | steps/ not copied | Dockerfile |
| 52 | CHECK | Input not trivially mutable | Tests generate tmp_path inputs at runtime | test_m*.py |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | Dockerfile |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:20-21` |
| 55 | CHECK | Not unfair | Contract doc shipped; requirements testable; agents pass M1 universally | `entire-report.txt:66` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 27, 28 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Field aliases id/rev/line/lossOn/state | `test_ingest_aliases...` | covered | `test_m1.py:48-49` CLM-002 via aliases |
| Recursive plain + gzip JSONL | `test_ingest_aliases...` | covered | `test_m1.py:47-57` |
| Ignore closed claims | `test_ingest_aliases...` | covered | `test_m1.py:50`, claim_count==3 |
| Ignore cancelled/canceled claims | — | **gap** | instruction line 9; no test rows |
| Duplicate: highest revision | `test_ingest_aliases...` | covered | CLM-001 revision 3 wins |
| Duplicate: path tie-break | `test_ingest_aliases...` | covered | CLM-TIE keeps `a/tie.claim.jsonl` |
| Duplicate: same-file line tie-break | — | **gap** | instruction line 9; untested |
| All 13 claim output fields with values | `test_ingest_aliases...` | **gap** | only subset asserted lines 67-73 |
| invalid_claim detail tokens | `test_invalid_claim_rows...` | covered | `test_m1.py:100-107` |
| Recoverable bad rows + required flags | `test_invalid_claim_rows...` | covered | `test_m1.py:77-112` |
| M2 scoring formula + index schema | M2 tests (5) | covered | `test_m2.py` |
| M2 signal path/line tie (signals) | `test_score_same_revision...` | covered (signals) | `test_m2.py:245-271` path tie |
| M3 portfolio optimization + plan fatal | M3 tests (10) | covered | `test_m3.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/instruction.md` | Blockers 1–3, #27, #28, spec table |
| `steps/milestone_1/tests/test_m1.py` | Blockers 1–3, #27, #28, #31 |
| `steps/milestone_2/tests/test_m2.py` | #31, #49, M2 alignment |
| `steps/milestone_3/tests/test_m3.py` | #31, #49, M3 alignment |
| `task.toml` | #44, #45, #46, milestone metadata |
| `environment/Dockerfile` | #15, #20, #50 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ adjudication |
| `environment/docs/claimtower-contract.md` | #7, spec reference |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate claimtower_milestone_go_task_v13/
Summary: 0 error(s), 4 warning(s)
- tags 7 entries (recommended 3-6)
- module-level docstrings missing in test_m1/m2/m3.py (all test methods documented)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | |
| terminus-claude-opus-4-8 | 60.0% (3/5) | |
| oracle | 100.0% (3/3) | from submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | differ — informational only |

### Rubric (milestone format — correct)

| Block | Positive pts | Negatives | ≤40 cap |
|-------|-------------|-----------|---------|
| # Rubric 1 | 10 (+5+3+2) | 3 | PASS |
| # Rubric 2 | 11 (+5+3+3) | 3 | PASS |
| # Rubric 3 | 11 (+5+3+3) | 3 | PASS |

Task is a **milestone** task (`number_of_milestones=3`); platform rubric correctly uses three `# Rubric N` blocks — **not** a wrongly formatted flat non-milestone rubric.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; 3-milestone Go CLI |
| 1 Instruction | ☑ | Per-step instructions concise; contract referenced |
| 2 Environment | ☑ | Pinned Go image, tmux/asciinema, no test/solution COPY |
| 3 Oracle | ☑ | solveN.sh implement full logic; export 100% |
| 4 Verifiers | ☑ | M1 gaps only; M2/M3 robust |
| 5 Metadata | ☑ | 7 tags = Low warning |
| 6 Rubric | ☑ | Milestone blocks, ≤40 each, ≥3 negatives total |
| 7 LLMaJ & agents | ☑ | behavior_in_tests overclaims M1; 60% worst model |
| 8 Fairness | ☑ | No cheating paths found |
| 9 Long context | N/A | not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task overall — the staged Go CLI design, contract doc, pinned offline Dockerfile, and M2/M3 verifiers are in great shape, and the rubric is correctly split across three milestone blocks. The one thing to fix before accept: Milestone 1 tests don’t fully enforce the ingestion contract. Please add exact assertions for all required per-claim fields (product, loss_date, severity, handler, source_line, etc.), plus targeted rows for cancelled/canceled filtering and same-file duplicate tie-breaks by lower source line. Optional: trim one tag (e.g. `milestone`) to quiet the 7-tag warning.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 2, 3 |
| Metadata Issues | no (7 tags = Low advisory) | — |
| Rubric | no | — |
| Milestones | no | — |
| Instruction Styling | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
