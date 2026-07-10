# Terminus Review Report: `scala-sbt-schema-consumer-regeneration`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong offline JVM build-regeneration task with excellent verifier design (isolated worktrees, anti-static-artifact test, provenance SHA-256 checks). One real High blocker: `instruction.md` requires provenance with “SHA-256 digests” only, but `test_clean_publish_local_jar_contains_service_loader_index_and_provenance` also requires `input.<path>.bytes` for every declared input — a detail documented only in `environment/docs/output-schema.md`, which `instruction.md` never names as normative. Agent sufficiency analysis shows systematic failure on this gap (2/2 trials, `include_input_bytes=false`). Rubric format is correct for a non-milestone task (flat list, 27/40 positives); duplicate negative line is polish only, not a blocker.

**Insights (concise):**

- Verifier suite is robust: four behavior tests, fresh worktrees, no runtime package installs, canonical `reward.txt` block.
- `service-loader.properties` already exposes `provider_class=com.acme.generated.SchemaIndexProviderImpl` — ChatGPT’s ServiceLoader-class gap is overstated.
- Commented paths in `project/schema-index.inputs` make the four omitted authority files discoverable; “every authoritative file” covers them.
- Platform rubric is flat `Agent …, ±N` (no `# Rubric 2+`) — correct non-milestone format; 27 positive points ≤ 40 cap.
- `docs/output-schema.md` ships in the image and encodes verifier-expected keys/fixture IDs/test scenarios without an instruction link — tightens both #17 and #27.
- Oracle not run locally; export reports oracle 100% (3/3). Worst-model 60% — not too easy.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Provenance **byte-count** keys (`input.<rel>.bytes`) are verifier-required but not stated in `instruction.md` | `instruction.md:3` (“SHA-256 digests” only); `tests/test_outputs.py:166-172` asserts `input.{rel}.bytes` is digit; `environment/project/descriptor-provenance.policy:5` ships `include_input_bytes=false`; `entire-report.txt:51-53,71` — 2/2 agent trials failed on missing byte provenance | In `instruction.md`, state that provenance must record per-input SHA-256 **and byte counts** (or that `descriptor-provenance.policy` must enable `include_input_bytes=true`). Optionally name `/app/environment/docs/output-schema.md` as the normative output contract. |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27 | Normative output contract (`docs/output-schema.md`) is not linked from `instruction.md`; many jar/report field keys tested only there | `instruction.md` (no reference to `output-schema.md`); `environment/docs/output-schema.md:1-9` (descriptor keys, provenance key names, roundtrip JSON fields); `tests/test_outputs.py:136-155,188-211`; LLMaJ `behavior_in_task_description` fail in `entire-report.txt:103` | Add one sentence in `instruction.md` pointing agents to `/app/environment/docs/output-schema.md` for jar/report property contracts, **or** inline the missing provenance key names (`service.type`, `service.provider`, `index.resource`, `input.<path>.sha256`, `input.<path>.bytes`). |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Instruction lacks `input.<path>.bytes` provenance requirement (ChatGPT High; entire-report instruction sufficiency) | **Agree** | `instruction.md:3` vs `tests/test_outputs.py:166-172`; agent failures `entire-report.txt:51-53` |
| 2 | Instruction does not list `package-layout.properties`, `descriptor-provenance.policy`, both migration maps as required `schema-index.inputs` entries (ChatGPT High) | **Partially agree** | Instruction says “every authoritative file” (`instruction.md:3`); commented paths visible in `environment/project/schema-index.inputs:6-9`; rubric line 306 in `entire-report.txt` lists them explicitly — one trial omitted two files (`entire-report.txt:54`) but this is not the systematic failure mode |
| 3 | Exact ServiceLoader provider `com.acme.generated.SchemaIndexProviderImpl` not in instruction (ChatGPT; LLMaJ) | **Disagree** (not a blocker) | `environment/project/service-loader.properties:3` already names `provider_class=com.acme.generated.SchemaIndexProviderImpl`; test checks ServiceLoader file content (`tests/test_outputs.py:115`) |
| 4 | `docs/output-schema.md` should be normative but instruction does not identify it (ChatGPT High) | **Agree** | Grep: zero references to `output-schema` outside that file; doc contains provenance/roundtrip contracts (`output-schema.md:5-9`) |
| 5 | Tests are otherwise strong (ChatGPT Medium) | **Agree** | Four integration tests with worktrees (`tests/test_outputs.py`); test quality review ACCEPT in `entire-report.txt:261-265` |
| 6 | Duplicate rubric negative about writing to `target/` (ChatGPT Medium) | **Disagree** (not a blocker) | `entire-report.txt:313-314` duplicate `-5` line; still 6 distinct negatives ≥3; positive total 27 ≤ 40 |
| 7 | Rubric positive total within cap (ChatGPT) | **Agree** | `./scripts/terminus rubric-points entire-report.txt` → 27/40 PASS |
| 8 | `output-schema.md` leaks test oracle / anti-cheat detail (Harbor review `entire-report.txt:164-188`) | **Partially agree** | `output-schema.md:13-19` names incremental fixture, static-shortcut scenario, audit tooling — not a standalone Revise blocker when combined with blocker #2 (same doc should either be normative + linked, or trimmed) |
| 9 | Instruction is dense wall-of-text (Harbor review) | **Partially agree** | `instruction.md` is 3 dense paragraphs, no headings — style nit, not a Revise blocker |
| 10 | Non-canonical Docker base (Harbor review) | **Disagree** (not a blocker) | `environment/Dockerfile:1` digest-pinned Temurin 21 JDK; justified for offline Java/Scala compile |
| 11 | LLMaJ `behavior_in_tests` pass | **Agree** | Instruction behaviors that *are* stated are tested (`entire-report.txt:104`) |
| 12 | LLMaJ `structured_data_schema` pass — output-schema “clearly referenced” | **Disagree** | No file references `output-schema.md`; only shipped under `environment/docs/` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs, ~144 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer incident tone, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcomes, not edit sequence | `instruction.md` |
| 5 | CHECK | No hints in instruction | No walkthrough values in instruction body | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | UNCHECK | Well specified | Byte-count provenance and normative schema doc linkage missing | Blocker #1–2 |
| 8 | CHECK | Interesting | Realistic offline schema-index regeneration | Task content |
| 9 | UNCHECK | Unique | Cannot verify vs full TB corpus | — |
| 10 | CHECK | Absolute paths | All paths under `/app/environment/...` | `instruction.md` |
| 11 | CHECK | No task name in instruction | Absent | `instruction.md` |
| 12 | CHECK | No canary string | Absent | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline sbt; `allow_internet=false` | `task.toml:23`, `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:4` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context scoped | COPY only under `environment/` | `environment/Dockerfile:8-17` |
| 17 | UNCHECK | No ground-truth leakage in env | `output-schema.md` encodes expected descriptor keys, fixture IDs, audit scenarios | `environment/docs/output-schema.md:1-19` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; `test.sh` no installs | `environment/Dockerfile:4`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Docker unavailable); export shows 100% | `entire-report.txt:27` |
| 22 | CHECK | Oracle no internet | `solve.sh` uses local `sbt` only | `solution/solve.sh:50` |
| 23 | CHECK | Oracle reflective | Edits authority files then runs pipeline | `solution/solve.sh:7-50` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on all paths | `tests/test.sh:7-23` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instruction | Byte-count provenance tested but unstated in instruction | Blocker #1; `tests/test_outputs.py:166-172` |
| 28 | CHECK | Tests check correctness | Full `sbt` pipeline + jar/report assertions | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | Not unduly brittle | Exact strings match contractual outputs | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | All four `test_*` have docstrings | `tests/test_outputs.py:126-280` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 negatives (one duplicate) | `entire-report.txt:313-318` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | Verified | `entire-report.txt:305-318` |
| 34 | CHECK | `Agent …, ±N` format | 14 lines | `entire-report.txt:305-318` |
| 35 | CHECK | Rubric detailed; positive ≤40 | 27 positive points | `rubric-points` output |
| 36 | CHECK | Positive phrasing | No “Agent does not …, +N” | `entire-report.txt:305-318` |
| 37 | CHECK | No /tests/ references | None | `entire-report.txt:305-318` |
| 38 | CHECK | No instruction.md/task.toml refs | None | `entire-report.txt:305-318` |
| 39 | CHECK | No oracle/NOP mentions | None | `entire-report.txt:305-318` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | Task tree |
| 41 | CHECK | Clean parent directory | No stray submission files (local `audit-report.md` is reviewer-generated) | Task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | build-and-dependency-management; scala/java/bash | `task.toml:7-10` |
| 45 | CHECK | Difficulty field present | `difficulty=hard`; platform medium; worst-model 60% — informational only | `task.toml:6`, `entire-report.txt:17-23` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones=0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:12` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/tests | `environment/.dockerignore` |
| 52 | CHECK | No trivial input tampering | Worktree strips `target/`; rebuild required | `tests/test_outputs.py:13-26` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:22-23` |
| 55 | UNCHECK | Not unfair | Systematic agent failures on unstated byte-count provenance | `entire-report.txt:68-75`, blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 17, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Offline `sbt clean publishLocal consumerRoundTrip` | all four | covered | `instruction.md:1`; `tests/test_outputs.py:131,182,252,288` |
| Published jar at `target/local-ivy/schema-index.jar` | clean, consumer, incremental, static | covered | `instruction.md:1`; `tests/test_outputs.py:133,188` |
| ServiceLoader file `META-INF/services/com.acme.rift.SchemaIndexProvider` | clean, static | covered | `instruction.md:3`; `tests/test_outputs.py:110-115` |
| `schema-index.properties` in jar | clean, incremental, static | covered | `instruction.md:3`; `tests/test_outputs.py:116-140` |
| Provenance SHA-256 per input | clean | covered | `instruction.md:3`; `tests/test_outputs.py:165-174` |
| Provenance **byte count** per input | clean | **gap** | Not in `instruction.md`; `tests/test_outputs.py:166-172`; `output-schema.md:7` |
| Every authoritative `schema-index.inputs` entry | clean | covered | `instruction.md:3`; commented paths `schema-index.inputs:6-9`; `tests/test_outputs.py:156-164` |
| `acme.user.event.v1` → `acme.activity.event.v2` | clean, consumer | covered | `instruction.md:5`; `tests/test_outputs.py:140,195` |
| Consumer uses published local jar | consumer | covered | `instruction.md:5`; `tests/test_outputs.py:188` |
| Round-trip all legacy v1 + current v2 fixtures | consumer | covered | `instruction.md:5`; `tests/test_outputs.py:192-211` |
| Incremental ≡ clean after migration edit | incremental | covered | `instruction.md:3`; `tests/test_outputs.py:214-274` |
| Static generated patch overwritten | static | covered | `instruction.md:1`; `tests/test_outputs.py:277-295` |
| Roundtrip report JSON schema fields | consumer | partial gap | Fields in `output-schema.md:9`; not in `instruction.md` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers #1–2, #7, #27, #55 |
| `tests/test_outputs.py` | Blockers #1, spec alignment, #27–31 |
| `tests/test.sh` | #20, #24–26 |
| `environment/docs/output-schema.md` | Blockers #2, #17, adjudication #4,#8,#12 |
| `environment/project/schema-index.inputs` | Adjudication #2 |
| `environment/project/descriptor-provenance.policy` | Blocker #1 |
| `environment/project/service-loader.properties` | Adjudication #3 |
| `environment/Dockerfile` | #13–16, #20, #50 |
| `task.toml` | #45–46, metadata |
| `solution/solve.sh` | #22–23 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, instruction sufficiency |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate scala-sbt-schema-consumer-regeneration/
Summary: 0 error(s), 0 warning(s), 3 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | `entire-report.txt:23` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | `entire-report.txt:22` |
| oracle | 100.0% (3/3) | `entire-report.txt:27` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml:6`) |
| Platform classified | medium (`entire-report.txt:17`) |
| Tier match (#45) | informational only — CHECK #45 |

| Test | Pass rate | Notes |
|------|-----------|-------|
| `test_clean_publish_local_jar_contains_service_loader_index_and_provenance` | 8/10 | Byte provenance failures |
| `test_consumer_roundtrip_uses_published_local_jar_for_legacy_and_current_fixtures` | 10/10 | |
| `test_incremental_migration_map_change_matches_clean_regeneration` | 10/10 | |
| `test_static_generated_artifact_patch_is_overwritten_by_clean_rebuild` | 10/10 | |

### Rubric (non-milestone format check)

| Check | Result | Proof |
|-------|--------|-------|
| Flat `Agent …, ±N` list (no `# Rubric 2+`) | PASS | `entire-report.txt:305-318` — no milestone headers |
| Positive point total ≤ 40 | PASS (27) | `rubric-points` |
| ≥3 negatives | PASS (6) | Lines 313-318 |
| Duplicate negative line | Polish only | Lines 313-314 identical `-5` |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches export; regular layout; `number_of_milestones=0` |
| 1 Instruction | ☑ | Spec gap on byte provenance + missing normative doc link |
| 2 Environment | ☑ | Pinned JDK 21; tmux+asciinema; no tests/solution in image |
| 3 Oracle | ☑ | solve.sh derives via sbt; not run locally |
| 4 Verifiers | ☑ | Strong; one spec gap on bytes |
| 5 Metadata | ☑ | Consistent tags/category |
| 6 Rubric | ☑ | Non-milestone format correct; 27/40; duplicate line non-blocking |
| 7 Agent evidence | ☑ | Instruction sufficiency fail corroborates blocker |
| 8 Fairness | ☑ | Unfair only on unstated byte-count requirement |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid JVM regeneration task — the isolated worktree verifiers, anti-static-artifact test, and offline sbt pipeline are all well done. One fix before accept: `instruction.md` says provenance needs input paths and SHA-256 digests, but the jar test also requires `input.<path>.bytes` for every declared input (driven by `include_input_bytes` in the provenance policy). That byte-count requirement isn’t in the main instruction, and agents hit it systematically. Please add it explicitly to `instruction.md`, or point to `/app/environment/docs/output-schema.md` as the normative output contract and trim any test-audit narration from that doc. Optional polish: remove the duplicated “writes directly to target/” rubric negative (format is otherwise fine for a non-milestone rubric).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Rubric | no | — |
| Exposing Hints/Answers | no (insight only) | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Milestones | no | N/A |
| Task Difficulty | no | 60% worst-model |
| Oracle Solution Issues | no | not executed locally |
| All others | no | — |
