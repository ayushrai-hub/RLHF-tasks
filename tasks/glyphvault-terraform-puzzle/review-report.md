# Terminus Review Report: glyphvault-terraform-puzzle

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally; submission export reports 100% oracle) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Exposing Hints/Answers

**Decision (concise):** Strong multi-layer integration task (C/SQLite/Terraform/PNG) with solid verifier design, correct non-milestone rubric format, and appropriate difficulty calibration. Two real High blockers: (1) eleven starter `.c` files contain explicit `BROKEN:` comments that spell out every intended fix; (2) tests/golden require rendering/scoring the starting `entry` room before the first solver move, but no contract doc states that initialization counts as entry. Fix those before accept.

**Insights (concise):**

- ChatGPT’s BROKEN-comment and entry-room claims are **confirmed** with file evidence; CLI-flag claim is **not** a blocker (`main.c` already implements `--db/--atlas/--moves/--out/--terraform`).
- Automated review false-positives on #14 (hash-pinned `requirements.lock`) and #20 (pytest baked via lockfile) — both pass on manual audit.
- Platform rubric is **flat** (no `# Rubric 2+` headers), 40 positive pts — correct for `number_of_milestones = 0`; not milestone-format misuse.
- Worst-model pass rate 60% (Claude Opus 4.8); GPT-5.5 at 80% is at cap but not >80% — not too easy.
- `test_novel_probe_moves` at 7/10 and score/rooms/glyph tests at 8/10 correlate with the entry-room spec gap (systematic 122 vs 134 failures).
- `long_context` subcategory relies on ~446KB incidents archive that self-labels as non-normative filler; normative contracts total ~4.5KB — note for author, not a separate blocker here.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Exposing Hints/Answers | #5, #17, #51 | Eleven broken C modules contain explicit `BROKEN:` comments naming the exact defect and errata reference — a complete repair map for agents | `environment/src/clue_query.c:6`, `meta_decoder.c:6`, `glyph_atlas.c:42`, `tf_output_reader.c:9`, `alias_resolver.c:6`, `direction_map.c:6`, `unlock_gate.c:7`, `score_engine.c:7`, `move_driver.c:23`, `room_engine.c:14`, `transcript_writer.c:6` | Remove or rewrite as neutral production comments (symptom/contract reference only, no “BROKEN:” + fix recipe) |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Starting room must be rendered, added to `rooms_visited`, and scored (10 + `hint_weight`) during initialization before replaying moves; golden expects `final_score=134` and `rooms_visited[0]=="entry"`, but contract docs only say rooms score when “entered” and never define init-as-entry | `tests/fixtures/transcript.golden.json:2-8,64`; `tests/fixtures/score.golden.json:2`; `tests/test_outputs.py:68-71,122-147`; `environment/docs/puzzle_handbook.md:17-18`; `environment/src/main.c:58`; oracle fix `solution/write_fixes.py:370` (`gv_render_current_room` before move loop); agent failures `entire-report.txt:84-85,91-92,104-105` | Add explicit normative rule (handbook and/or `output_contract.md`): analysis begins in canonical `entry`; render/score current room once at startup before applying solver moves |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Starting-room render/score at init is under-specified; agents fail at 122 not 134 (ChatGPT / `entire-report.txt` instruction sufficiency) | **Agree** | Golden `transcript.golden.json:2-8,64`; probe test `test_outputs.py:147` expects `["entry","hall","library"]`; handbook `puzzle_handbook.md:17` says “entered” only; no doc mandates init render; 2/3 agent trials failed identically per `entire-report.txt:84-85,91-92` |
| 2 | Starter C files expose intended fixes via `BROKEN:` comments (ChatGPT) | **Agree** | 11 files — see blocker #1 proof lines; e.g. `clue_query.c:6` `/* BROKEN: queries legacy clues table and clue_text column */` |
| 3 | Direct binary CLI (`build/glyphvault_analyze --db --atlas --moves --out --terraform`) tested but not documented in instruction (ChatGPT / LLMaJ `behavior_in_task_description`) | **Disagree** (not a blocker) | Flags implemented in shipped `environment/src/main.c:38-44`; demonstrated by `environment/bin/puzzle-analyze:6-11`; probe tests `test_outputs.py:126-138` exercise existing interface — agents need not discover flags from instruction alone |
| 4 | Optional JSON Schema validation missing (ChatGPT Low) | **Agree** (Low only) | Schema exists `share/schemas/solve_transcript.schema.json`; no `jsonschema` test in `test_outputs.py` — optional improvement |
| 5 | Dockerfile digest pinning (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…` |
| 6 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `task.toml:9` `number_of_milestones = 0`; platform rubric `entire-report.txt:330-352` is flat `Agent …, ±N` list with no `# Rubric 2+` headers; `./scripts/terminus rubric-points` → 40 pts block 0 — correct non-milestone format |
| 7 | Rubric positive total >40 (rules) | **Disagree** | `rubric-points` → **40** (cap 40; passes) |
| 8 | Automated review #14 unpinned pip | **Disagree** | `environment/requirements.lock:12-13` `pytest==8.4.1` with sha256; Dockerfile `24-26` uses `--require-hashes` |
| 9 | Automated review #20 pytest not in image | **Disagree** | `requirements.lock` includes pytest; installed at image build `Dockerfile:25` |
| 10 | Harbor automated review “READY TO USE” (`entire-report.txt` review report) | **Partially agree** | Structure/tests strong; entry-room spec gap and BROKEN comments override “ready” for Edition 2 High bar |
| 11 | LLMaJ `behavior_in_task_description` FAIL | **Partially agree** | CLI flags not in instruction but present in `main.c` — not blocking; entry-room gap is the substantive FAIL driver |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Two problem paragraphs + contract bullet list | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as operator brief, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | Single `#` title, one bullet list | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal and contract refs only | `instruction.md` |
| 5 | UNCHECK | No hints or solving strategies | `BROKEN:` comments are explicit fix hints in env source | `environment/src/*.c` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | UNCHECK | Well specified | Entry-room init behavior required by tests but absent from contracts | blocker #2 |
| 8 | CHECK | Interesting | Real C/systems integration puzzle | task design |
| 9 | CHECK | Unique | Distinct GlyphVault/Terraform/atlas domain | — |
| 10 | CHECK | Absolute paths | All `/app/environment/...` paths | `instruction.md:3-13` |
| 11 | CHECK | Task name not in instruction | Slug `glyphvault-terraform-puzzle` absent; “GlyphVault” is product name | `instruction.md` |
| 12 | CHECK | No canary in instruction | No canary string | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env code | Terraform curl at **build** only | `environment/Dockerfile:18-22` |
| 14 | CHECK | Pinned pip deps | Hash-locked `requirements.lock` with `==` | `environment/requirements.lock`, `Dockerfile:25` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY scoped to environment subdirs | `environment/Dockerfile:32-43` |
| 17 | UNCHECK | No ground truth in environment | `BROKEN:` comments leak repair map | 11× `environment/src/*.c` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest via lockfile; test.sh no installs | `Dockerfile:25`, `tests/test.sh:3` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Docker down) | oracle run failed |
| 22 | CHECK | Oracle no internet | `solve.sh` writes C + make + puzzle-analyze | `solution/solve.sh` |
| 23 | CHECK | Oracle not hardcoded | `write_fixes.py` generates working C sources | `solution/write_fixes.py` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 with mkdir | `tests/test.sh:5-29` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:25-28` |
| 27 | UNCHECK | Tests aligned with instructions | Entry-room init tested, not specified in contracts | blocker #2 |
| 28 | CHECK | Tests check correctness | Golden + dynamic probes | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Runs binary, checks outputs | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string matching | Structured JSON field asserts | `tests/test_outputs.py` |
| 31 | CHECK | Informative names or docstrings | All `test_*` names are descriptive | `tests/test_outputs.py:41-204` |
| 32 | CHECK | ≥3 negative rubric criteria | 10 negatives | `entire-report.txt:344-352` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | No ±4 | `entire-report.txt:330-352` |
| 34 | CHECK | Rubric `Agent …, ±N` format | 24 Agent lines | `entire-report.txt:330-352` |
| 35 | CHECK | Rubric detailed | Module-level repair trace criteria | `entire-report.txt:330-352` |
| 36 | CHECK | Positive rubric phrasing | Negatives penalize bad behavior | `entire-report.txt:344-352` |
| 37 | CHECK | Rubric no /tests/ refs | No pytest path refs | `entire-report.txt:330-352` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:330-352` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:330-352` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category match | c/sql/bash, games, tool_specific, long_context | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform classified medium — informational only | `task.toml:6`, `entire-report.txt:40` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | UNCHECK | No accessible ground truth in env | `BROKEN:` repair map in agent-visible src | `environment/src/*.c` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Verifier resets DB from seed each run | `tests/test.sh:13-14`, `instruction.md:15` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:45-46` |
| 55 | UNCHECK | Not unfair | Entry-room rule only in golden/probes, not contracts; systematic agent failures | blocker #2, `entire-report.txt:75-105` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 52, 53, 54 |
| **UNCHECK** | 5, 7, 17, 21, 27, 46, 47, 48, 49, 51, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Rebuild engine; `puzzle-analyze` exit 0 | `test_analyze_exit_zero` | covered | `instruction.md:5,15`; `test_outputs.py:41-43` |
| Write `solve_transcript.json` | `test_transcript_exists` | covered | `instruction.md:5`; `test_outputs.py:46-47` |
| Reach `vault` | `test_final_room_is_vault` | covered | `test_outputs.py:50-52` |
| `final_score` per scoring rules | `test_final_score_matches_golden` | **gap** (init entry scoring unstated) | `puzzle_handbook.md:17-19`; golden `score.golden.json:2` |
| SQLite `puzzle_state` matches transcript | `test_sqlite_score_matches_transcript` | covered | `output_contract.md:12`; `test_outputs.py:61-65` |
| `rooms_visited` order | `test_rooms_visited_sequence` | **gap** (entry at init unstated) | golden `transcript.golden.json:2-8`; `test_outputs.py:68-71` |
| `moves_applied` from solver script | `test_moves_applied_match_solver_script` | covered | `puzzle_handbook.md:13`; `test_outputs.py:74-77` |
| Glyph count and atlas chars | `test_glyphs_rendered_count`, `test_glyph_characters_match_atlas` | **gap** (entry glyph at init unstated) | golden `transcript.golden.json:10-17`; `test_outputs.py:80-94` |
| JSON key order `rooms_visited` before `glyphs_rendered` | `test_transcript_key_order` | covered | `output_contract.md:3-6`; `test_outputs.py:96-100` |
| `has_key` true after solver | `test_has_key_true` | covered | `test_outputs.py:103-105` |
| `room_exits` not hard-coded graph | `test_room_exits_table_used_not_hardcoded` | covered | `exit_table.md`; `test_outputs.py:108-112` |
| `room_clues.clue_blob` not legacy `clues` | `test_clue_blob_table_room_clues` | covered | `data_access.md`; `test_outputs.py:115-119` |
| Novel move replay (probe) | `test_novel_probe_moves` | covered (implies init entry) | `test_outputs.py:122-147` |
| CRLF trim on moves | `test_crlf_moves_trimmed` | covered | `puzzle_handbook.md:13`; `test_outputs.py:150-175` |
| UNLOCK without key fails | `test_unlock_requires_key` | covered | `puzzle_handbook.md:27`; `test_outputs.py:178-204` |
| Binary CLI `--db/--atlas/--moves/--out/--terraform` | probe tests | covered in source | `main.c:38-44`; `test_outputs.py:126-138` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, blocker 2 |
| `task.toml` | #44-49, #45 |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `environment/src/*.c` (11 modules) | blocker 1, #5, #17, #51 |
| `environment/src/main.c` | entry start room, CLI flags |
| `environment/docs/puzzle_handbook.md` | scoring, entry gap |
| `environment/docs/reference/output_contract.md` | transcript schema |
| `environment/bin/puzzle-analyze` | CLI demonstration |
| `solution/write_fixes.py` | oracle entry-room fix, #23 |
| `tests/test_outputs.py` | #27-31, all alignment rows |
| `tests/test.sh` | #20, #24, #52 |
| `tests/fixtures/transcript.golden.json` | blocker 2, golden values |
| `tests/fixtures/score.golden.json` | blocker 2 |
| `entire-report.txt` | agent stats, rubric, LLMaJ, instruction sufficiency |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate glyphvault-terraform-puzzle/
Summary: 0 error(s), 19 warning(s), 2 info
Task type detected: regular
```

Warnings are mostly missing per-test docstrings (mitigated by informative names for #31) and validate INFO on non-milestone preference.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | At easy-tier boundary, not >80% blocker |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst-model reference |
| oracle | 100.0% (3/3) | per submission export |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only (never blocks) |

Per-test: `test_final_score_matches_golden`, `test_rooms_visited_sequence`, `test_glyphs_rendered_count`, `test_glyph_characters_match_atlas` at 8/10; `test_novel_probe_moves` at 7/10 — consistent with entry-room init gap.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular task, `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise; contract refs OK; entry-room gap found |
| 2 Environment | ☑ | Digest-pinned base; BROKEN comments fail hint bar |
| 3 Oracle | ☑ | Static review pass; runtime not executed |
| 4 Verifiers | ☑ | Strong probes; spec gap on init entry |
| 5 Metadata | ☑ | Fields complete; long_context subcategory noted |
| 6 Rubric | ☑ | Flat format, 40 pts, ≥3 negatives — pass |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed for entry room |
| 8 Novelty & fairness | ☑ | Fair except undocumented init behavior |
| 9 Long context | ☑ | Archive is filler; normative docs small — author note |

---

## 9. Reviewer note (copy-paste to portal)

Really solid integration work here — the Terraform/SQLite/PNG atlas pipeline, dynamic probe tests, and anti-cheat design (DB reset, novel move files) are all in great shape. The rubric format is correct for a non-milestone task (flat list, 40 positive points).

Two things to fix before we can accept. First, the starter C sources have `BROKEN:` comments that literally name every defect and errata fix — please strip those or rewrite them as neutral production comments so agents aren’t handed the repair checklist. Second, the verifier and golden fixture expect the engine to render and score the starting `entry` room before any solver moves run (that’s why agents land on 122 instead of 134), but none of the contract docs say initialization counts as entering the room. Please add an explicit rule in the handbook or output contract.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 2 |
| Test Alignment/Coverage Issues | yes | 2 |
| Exposing Hints/Answers | yes | 1 |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Environment (Docker/pinning) | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
