# Terminus Review Report: go-game-record-dual-cause-adjudicator-closure-authoring

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Instruction Styling, Rubric

**Decision (concise):** Strong Go adjudication task — authority reconciliation, anti-cheat workflow regeneration, pinned offline environment, and oracle all pass. Two real High blockers remain: (1) `records` JSON container shape is ambiguous (“entries keyed by record id” reads like a dict; verifier expects an array), which caused systematic agent failures despite correct domain work; (2) platform rubric uses four `# Rubric N` blocks on a non-milestone task (`number_of_milestones = 0`). Prior reviewer claims about missing instruction detail and missing structural-defect wording are stale on the current artifacts.

**Insights (concise):**

- Oracle passes cleanly (reward 1.0); solve.sh repairs `.ggr` + `policy.json` then runs workflow — not hardcoded output.
- Worst-model pass rate is **60%** (GPT-5.5), not 100%; automated review misread Claude’s 100% as worst-model — **#54 CHECKs**.
- LLMaJ `behavior_in_task_description` PASS is correct for current `instruction.md`; prior portal feedback item #1 (unstated test details) does **not** apply to this revision.
- Agent failure analysis: both trials failed solely on `records` list-vs-dict shape after ~90% correct reconciliation work.
- Rubric has 50 positive points across four blocks; non-milestone cap is 10–40 when flattened (Low, secondary to format).
- Legacy `terminal_pass_move_numbers == [4, 5]` is stated in instruction but not asserted in tests — Low only, not a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling | #7, #55 | `records` container shape ambiguous — instruction says “entries keyed by record id,” which agents read as a JSON object; verifier and Go code require a JSON **array** of objects each with `record_id`. | `instruction.md:3` (“entries keyed by record id”); `proof-schema.md:5` (lists fields, never states array); `environment/internal/proof/proof.go:25` (`Records []RecordProof`); `tests/test_outputs.py:37-38` (`for item in report["records"]`); `entire-report.txt:57-71` (both agent trials failed list-vs-dict) | In `instruction.md` and `proof-schema.md`, state explicitly: **`records` must be a JSON array; each element is an object containing `record_id`**. Remove or replace “entries keyed by record id.” |
| 2 | High | Rubric | #35 | Non-milestone task uses four milestone rubric blocks (`# Rubric 1`–`# Rubric 4`); `number_of_milestones = 0`. | `task.toml:12` (`number_of_milestones = 0`); `entire-report.txt:301-331` (four `# Rubric N` headers); `docs/guidelines/rubrics.md:64` (“Non-milestone: flat … list; `# Rubric 1` optional; no `# Rubric 2+`”); `docs/reviewer-checklist-full.md:79` (format High) | Flatten platform rubric into one `Agent …, ±N` list (optional single `# Rubric 1` header only); trim positives to 10–40 total if needed. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Proof schema must state `records` is a JSON array, not object keyed by id (ChatGPT / `entire-report.txt` agent analysis) | **Agree** | `instruction.md:3`; `proof-schema.md:5`; `proof.go:25`; agent failure narrative `entire-report.txt:57-71` |
| 2 | Platform rubric has four `# Rubric` blocks on non-milestone task (ChatGPT) | **Agree** | `task.toml:12`; `entire-report.txt:301-331`; `rubrics.md:64` |
| 3 | Optional: assert legacy `terminal_pass_move_numbers == [4, 5]` (ChatGPT / test quality review) | **Agree (Low only)** | `instruction.md:5`; `tests/test_outputs.py:78-91` (no assertion on `terminal_pass_move_numbers`) |
| 4 | Instruction omits pass numbers, branch moves, record IDs, CLI flags, copy-test details (portal Reviewer Feedback #1) | **Disagree** | Current `instruction.md:3-7` specifies schema version, record IDs, ko-threat-read from move 4, E5/D5, passes 10/11, B+1.5/komi 6.5, legacy B+2.5 passes 4/5, dragon-cup-17-copy CLI contract, cache deletion; `proof-schema.md:3-9` documents CLI flags and copy filenames |
| 5 | Instruction must add structural-defect / endvariation repair wording (portal Reviewer Feedback #2) | **Disagree (already fixed)** | `instruction.md:1` already states input `.ggr` files may contain structural defects including missing `endvariation` |
| 6 | Non-canonical Go builder image is a blocker (Harbor review report) | **Disagree** | `environment/Dockerfile:1-2` — digest-pinned golang builder + canonical Python final stage; multi-runtime task; advisory only |
| 7 | Task too easy — worst model >80% (automated `terminus review`) | **Disagree** | `entire-report.txt:26-27` — GPT-5.5 60%, Claude 100%; worst model = 60% (Medium tier per `difficulty.md`) |
| 8 | Module-level docstring missing → #31 fail (automated validate) | **Disagree** | All five `test_*` functions have docstrings (`tests/test_outputs.py:43-131`); #31 requires informative names **or** docstrings |
| 9 | LLMaJ instruction sufficiency FAIL (agents failed on records shape) | **Partially agree** | Failure real and spec-driven, but root cause is ambiguous wording not missing behavioral requirements; fix blocker #1 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three paragraphs | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense field-level requirement prose | `instruction.md:3-7` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | Outcomes and authorities, not edit steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | References schema/contracts, not repair walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | `records` array vs object ambiguous | `instruction.md:3`, `proof-schema.md:5` |
| 8 | CHECK | Instruction is interesting | Real Go record adjudication reconciliation | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Absent | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies pinned with == | pytest==8.4.1 pytest-json-ctrf==0.3.5 | `environment/Dockerfile:12` |
| 15 | CHECK | Base Docker image pinned by digest | Both FROM lines @sha256 | `environment/Dockerfile:1-2` |
| 16 | CHECK | Environment does not use context outside environment/ | COPY only env paths | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken `policy.json` is intentional wrong state, not answer key | `environment/j/policy.json` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:12`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Oracle mean 1.000 | Harbor oracle run 2026-06-28 |
| 22 | CHECK | Oracle does not require internet | Local file edits + workflow | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Repairs authorities, runs workflow | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; handles failure | Canonical reward block | `tests/test.sh:6-24` |
| 25 | CHECK | Same verifier logic for oracle and agent | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only (0 or 1) | 0/1 reward.txt | `tests/test.sh` |
| 27 | CHECK | All tests aligned with instructions | Test assertions trace to instruction + proof-schema | §5 below |
| 28 | CHECK | Tests check correctness, not just format | Replay outcomes, hashes, adjudication agreement | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Workflow/CLI invocation, JSON outcomes | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Exact IDs/scores appropriate for adjudication contract | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | Five named tests, each with docstring | `tests/test_outputs.py:43-131` |
| 32 | CHECK | Rubrics contain ≥3 negative penalty criteria | 4 negatives | `entire-report.txt:301-331` |
| 33 | CHECK | Rubric scores from {±1,2,3,5} | All lines valid | `entire-report.txt:301-331` |
| 34 | CHECK | Each rubric line starts with Agent, comma, score | 25 Agent lines | `entire-report.txt:301-331` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Four milestone blocks on non-milestone task | `task.toml:12`, `entire-report.txt:301-331` |
| 36 | CHECK | Rubric uses positive language | Bad behavior scored negative | `entire-report.txt:301-331` |
| 37 | CHECK | Rubric does not reference /tests/ | Clean | `entire-report.txt:301-331` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | Clean | `entire-report.txt:301-331` |
| 39 | CHECK | Rubric does not mention oracle or NOP | Clean | `entire-report.txt:301-331` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Task folder clean | task root |
| 42 | CHECK | author_name and author_email present | Both anonymous | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | Complete | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | go/games/adjudication | `task.toml:7-10` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 60% → Medium | `task.toml:6`, `entire-report.txt:26-27` |
| 46 | UNCHECK | steps/ milestone layout | N/A — not a milestone task | `task.toml:12` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:17` |
| 51 | CHECK | Solution/answers not accessible in environment | solution/ tests/ excluded | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot trivially pass by mutating inputs alone | Must reconcile authorities; regenerate overwrites stale output | `tests/test_outputs.py:28-34` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model GPT-5.5 60% | `entire-report.txt:26-27` |
| 55 | UNCHECK | Task is not too hard or unfair | Records-shape ambiguity caused systematic failure on correct domain work | `entire-report.txt:57-77` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 2, 7, 9, 35, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/adjudication-proof.json` via workflow | `test_public_workflow_regenerates_current_proof` | covered | `instruction.md:1`; `tests/test_outputs.py:43-53` |
| `schema_version` `go-adjudication-proof-v1` | `test_public_workflow_regenerates_current_proof` | covered | `instruction.md:3`; `tests/test_outputs.py:46` |
| SHA-256 provenance for rulebook, policy, records | `test_public_workflow_regenerates_current_proof` | covered | `instruction.md:3`; `tests/test_outputs.py:48-53` |
| Record IDs `dragon-cup-17`, `sansei-legacy-1999` | all record tests | covered | `instruction.md:3`; `by_id()` calls |
| ko-threat-read from move 4; E5/D5; zero leakage; B+1.5; passes 10/11 | `test_dragon_variation_rollback_and_adjudicator_agreement` | covered | `instruction.md:3-4`; `tests/test_outputs.py:56-75` |
| Legacy notation; B+2.5; passes 4 and 5 | `test_legacy_archive_score_notation_remains_accepted` | gap (minor) | `instruction.md:5`; test checks winner/margin/passes_to_close but not `terminal_pass_move_numbers` |
| `records` JSON array of objects with `record_id` | all tests via `by_id()` | **spec gap** | Instruction ambiguous; tests assume array `tests/test_outputs.py:37-38` |
| dragon-cup-17-copy CLI contract | `test_record_copy_with_same_contract_is_not_hardcoded` | covered | `instruction.md:7`; `proof-schema.md:3,9`; `tests/test_outputs.py:94-127` |
| Deleting output/cache insufficient without authority fix | `test_deleting_generated_state_does_not_replace_authorities` | covered | `instruction.md:7`; `tests/test_outputs.py:130-138` |
| Repair structural `.ggr` defects (endvariation) | implicit via workflow pass | covered | `instruction.md:1`; broken fixture in env; all tests call `regenerate()` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker #1, #7, #55, §5 |
| `environment/docs/proof-schema.md` | Blocker #1, §5 |
| `environment/internal/proof/proof.go` | Blocker #1 adjudication |
| `environment/Dockerfile` | #14-20, oracle env |
| `environment/.dockerignore` | #50-51 |
| `environment/j/policy.json` | #17 anti-cheat |
| `tests/test_outputs.py` | #27-31, §5 |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh` | #21-23 |
| `task.toml` | Blocker #2, #45-49 |
| `entire-report.txt` | Agent stats, rubric, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-game-record-dual-cause-adjudicator-closure-authoring/ ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: informative_test_docstrings — module-level docstring missing (all test functions documented)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 structural JSON-shape failures |
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| oracle | 100.0% (1/1) | Mean reward 1.000 |

| Metric | Value |
|-------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no — declared hard vs observed medium; not a revision blocker alone |

Per-test (from export): all five tests 8/10 pass rate — failures concentrated on records list-vs-dict misinterpretation.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `go-game-record-dual-cause-adjudicator-closure-authoring`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Records container ambiguity is sole High instruction issue; structural-defect wording present |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Passes 1.0; authority reconciliation not hardcoded JSON |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests; minor legacy pass-number gap only |
| 5 Metadata | ☑ | Complete; difficulty metadata vs rates noted |
| 6 Rubric | ☑ | Four milestone blocks on non-milestone task — High blocker |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency fail traced to records shape; not missing behavioral spec |
| 8 Novelty & fairness | ☑ | Multi-step reconciliation; records ambiguity unfair |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

This is a strong task overall — the dual-authority reconciliation (broken `.ggr` structure plus wrong policy JSON), workflow regeneration anti-cheat, copy-record CLI test, and pinned offline environment are all well done, and the oracle passes cleanly. Two fixes before accept: (1) make the proof JSON shape explicit — `records` must be a **JSON array** where each element is an object with a `record_id` field (the phrase “entries keyed by record id” reads like a dict and both failed agent trials hit exactly that); update `instruction.md` and `proof-schema.md`. (2) Flatten the platform rubric into a single non-milestone `Agent …, ±N` list — four `# Rubric N` blocks are for milestone tasks only. Optional nice-to-have: add `terminal_pass_move_numbers == [4, 5]` to the legacy test.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Rubric | yes | 2 |
| Test Alignment/Coverage Issues | no | — (legacy pass numbers Low only) |
| Task Difficulty | no | — (#54 passes at 60% worst model) |
| Metadata Issues | no | — (#45 mismatch informational) |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Milestones | no | — |
