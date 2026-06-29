# Terminus Review Report: setup-sccache-minio-rust

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (report: 100% 3/3) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric, Exposing Hints/Answers

**Decision (concise):** The sccache/MinIO workflow, digest-pinned Rust environment, and anti-cheat verifiers are strong. Revision is required because agent-visible docs contradict the verifier on fractional timing, `compilations` counter mapping, and replay-stat session semantics — causing universal agent failures on those assertions. The platform rubric also needs cleanup: non-milestone task uses a `# Rubric 1` milestone header, Snorkel CI reports parse failures, and one criterion references `/tests`.

**Insights (concise):**

- All 5 agent trials passed 10–12/13 tests; failures cluster on three spec gaps, not environment bugs.
- Top-level `/app/docs/*.md` actively mislead (integer timing, Compile requests executed); authoritative semantics live only in `/app/docs/internal/release/` which instruction.md does not point to.
- Local `./scripts/terminus rubric-validate` passes the exported rubric text; Snorkel platform CI still reports formatting/milestone-block failures — likely `# Rubric 1` on a `number_of_milestones = 0` task.
- Dockerfile uses digest `9f841bbe…` matching canonical `rust:1.85-slim` — not a pinning/canonical blocker.
- Worst-model pass rate 80% is at (not above) the rejection threshold; `hard` is defensible via best-model 20%.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Visible docs say integer-second `date +%s` is sufficient and warm may round to zero; verifier requires `warm_seconds >= 0.001` (fractional, non-zero). `instruction.md` is silent on sub-second timing. | `environment/docs/duration-thresholds.md:3`, `environment/docs/benchmark-output.md:5`, `environment/docs/benchmark-report-spec.md:17`, `tests/test_outputs.py:173-174` | State fractional-second timing in `instruction.md`; remove or correct all top-level docs that claim integer seconds are sufficient. |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Agent-visible docs map `compilations` → **Compile requests executed**; verifier expects **Non-cacheable compilations** (`warm.compilations == 0`, `post_clean.hits > post_clean.compilations`). `instruction.md` does not specify the mapping. | `environment/docs/counter-semantics.md:9`, `environment/docs/benchmark-output.md:5`, `environment/docs/internal/release/stat-mapping.md:9`, `tests/test_outputs.py:210-211,220-221`, `solution/solve.sh:175` | Specify in `instruction.md` that `compilations` = Non-cacheable compilations; fix or remove conflicting top-level docs. |
| 3 | High | Test Alignment/Coverage Issues | #27, #55 | Replay stats test requires `live_misses == 0` in captured `sccache --show-stats`; cumulative session stats fail. Instruction says capture stats “in the same session” but never requires resetting/restarting sccache before the post-clean verification build. Oracle restarts sccache before replay (`solve.sh:307`). | `instruction.md:3`, `tests/test_outputs.py:262-264`, `solution/solve.sh:307-310`, `environment/docs/internal/release/benchmark-metrics.md:7-9` (no reset stated) | Clarify in `instruction.md` that sccache stats must be reset (stop/restart server) immediately before the post-clean verification build so replay stats reflect only that build. |
| 4 | High | Rubric | #37 | Platform rubric negative criterion references the `/tests` directory. | `entire-report.txt:338` — `Agent deletes, renames, or disables files under /tests to bypass verification, -5` | Rephrase without naming `/tests` (e.g. “modifies verifier-mounted files to bypass grading”). |
| 5 | High | Rubric | #32–#36 | Snorkel platform reports **Rubric Formatting FAIL** (invalid scores on all lines) and **Max Cumulative Score FAIL** (“No rubric blocks found”). Task is non-milestone (`number_of_milestones = 0`) but rubric uses `# Rubric 1` milestone header. Local `rubric-validate` passes; platform parser does not. | `entire-report.txt:12-17`, `task.toml:10`, `entire-report.txt:324-339`, `./scripts/terminus rubric-validate` → 0 errors | Remove `# Rubric 1` header for flat non-milestone rubric; re-submit on platform until Rubric Formatting + Max Cumulative Score pass. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Integer-second timing docs conflict with fractional verifier (ChatGPT / entire-report / LLMaJ) | **Agree** | `duration-thresholds.md:3`, `benchmark-output.md:5` vs `test_outputs.py:173-174` |
| 2 | `compilations` maps to Compile requests executed in visible docs but tests use Non-cacheable compilations (ChatGPT / entire-report / LLMaJ) | **Agree** | `counter-semantics.md:9` vs `stat-mapping.md:9`, `test_outputs.py:210-211` |
| 3 | Replay stats need daemon reset before post-clean verification build (ChatGPT / entire-report) | **Agree** | `test_outputs.py:262-264`, `solve.sh:307-310`; instruction omits reset |
| 4 | Platform rubric formatting / max-score calculation failures (entire-report lines 12–17) | **Partially agree** | Platform CI fails; exported rubric text passes local `rubric-validate`. Root cause likely `# Rubric 1` on non-milestone task + platform parser mismatch. |
| 5 | Non-milestone task in milestone rubric format (`# Rubric 1`) (user query) | **Agree** | `task.toml:10` (`number_of_milestones = 0`); `entire-report.txt:324` has `# Rubric 1`; platform: “No rubric blocks found”. Per `docs/guidelines/rubrics.md:64`, `# Rubric 1` is optional locally but triggers milestone-block validation on platform. |
| 6 | Non-canonical Rust base image is a main blocker (Harbor review / ChatGPT Low) | **Disagree** | `environment/Dockerfile:1` digest `9f841bbe…` matches canonical `rust:1.85-slim` in `scripts/validate_task.py:68`. Image name differs; digest is sanctioned. |
| 7 | `#14` unpinned pip dependencies (automated review) | **Disagree** | `environment/Dockerfile:47-48` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` are `==`-pinned. |
| 8 | Misleading legacy nested schema is intentional difficulty (Harbor review) | **Partially agree** | `test_report_does_not_use_legacy_layout` enforces flat schema; `instruction.md:3` warns legacy docs outdated. Fair as difficulty. **Does not** excuse timing/compilations/replay contradictions in non-legacy top-level docs. |
| 9 | Task too easy / >80% worst model (difficulty policy) | **Disagree as blocker** | Worst model 80.0% is ≤80% threshold (`docs/guidelines/difficulty.md:12`). Not rejected tier. |
| 10 | `behavior_in_tests` PASS means no spec gaps (LLMaJ) | **Disagree** | LLMaJ `behavior_in_task_description` FAIL at `entire-report.txt:127-135` is correct; tests cover behaviors not fully stated in instruction. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two short paragraphs, ~95 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | CI-ticket tone, no spec boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goals/outputs, not wiring steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies in instruction | Instruction does not embed HOW-to steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No tables in instruction | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Missing fractional timing, compilations mapping, replay reset | Blockers 1–3 |
| 8 | CHECK | Instruction is interesting | Realistic CI cache plumbing | — |
| 9 | CHECK | Instruction is unique | sccache+MinIO+Rust benchmark task | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` paths only | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time package downloads only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | pytest pinned with == | `environment/Dockerfile:47-48` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | FROM has @sha256 digest | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY scoped to environment/ | `environment/Dockerfile` |
| 17 | UNCHECK | Environment does not contain solution or ground truth answers | `/app/docs/internal/release/` contains authoritative test semantics (stat mapping, timing bounds) | `stat-mapping.md`, `timing-bounds.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh no pip/apt | `environment/Dockerfile:45-48`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:43` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh uses pre-installed tools | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Derives timings/stats from real builds | `solution/solve.sh:200,307-310` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block present | `tests/test.sh:10,192` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | reward.txt 0/1 only | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions | Three unstated verifier requirements (timing, compilations, replay reset) | Blockers 1–3 |
| 28 | CHECK | Tests check for correctness, not just format | MinIO objects, git diff, live stats, timing ratios | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | No source-code grep asserts | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Legacy-field rejection is intentional schema guard | `tests/test_outputs.py:307-308` |
| 31 | CHECK | Tests have informative names or docstrings | All 13 tests documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Platform Rubric Formatting FAIL reported | `entire-report.txt:12-13` |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Platform reports invalid scores on all lines | `entire-report.txt:14` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | Platform parse failure | `entire-report.txt:12-14` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Blocked by platform formatting failure; fix format first | `entire-report.txt:12-17` |
| 36 | CHECK | Rubric criteria use positive language | No “does not” phrasing in rubric | `entire-report.txt:325-339` |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | Criterion names `/tests` | `entire-report.txt:338` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No such references | `entire-report.txt:325-339` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None found | `entire-report.txt:325-339` |
| 40 | CHECK | All required files present | Standard layout complete | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | Complete | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | rust/sccache/minio match content | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 20% ≤20% | `entire-report.txt:37-38`, `difficulty.md` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — not a milestone task | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Git integrity + live MinIO/stats checks | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | Seeded git in image; no runtime clone | `environment/Dockerfile:60-64` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 80% — not above 80% | `entire-report.txt:39` |
| 55 | UNCHECK | Task is not too hard or unfair | Systematic doc↔test contradictions misled all agents | `entire-report.txt:77-96`, blockers 1–3 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 36, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 17, 27, 32, 33, 34, 35, 37, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Publish `/app/reports/sccache-benchmark.json` flat schema | `test_report_file_exists`, `test_report_contains_required_schema` | covered | `instruction.md:3`, `test_outputs.py:132-161` |
| Phase objects with `hits`, `misses`, `compilations` | `test_report_contains_required_schema` | gap | instruction silent on Non-cacheable mapping |
| `compilations` = Non-cacheable compilations | `test_warm_build_avoids_new_compilation_work`, `test_post_clean_rebuild_relies_on_cache` | gap | `counter-semantics.md:9` contradicts test |
| Fractional sub-second `warm_seconds` | `test_warm_build_is_faster_than_cold` | gap | `duration-thresholds.md:3` contradicts test |
| Cold ≥ several seconds; warm < 50% cold | `test_warm_build_is_faster_than_cold` | phantom in instruction | Only in `timing-bounds.md`, not instruction |
| Post-clean timing > warm, ≥ 1s | `test_post_clean_timing_reflects_target_rebuild` | phantom in instruction | `timing-bounds.md` only |
| Cold hits=0, misses>0 | `test_cold_build_populated_the_cache` | covered | aligns with `timing-bounds.md:5` |
| Warm misses=0 | `test_warm_build_avoids_new_compilation_work` | covered | — |
| Remote MinIO objects persist | `test_remote_cache_store_contains_objects` | covered | — |
| Replay stats: full raw `sccache --show-stats`, zero misses | `test_post_clean_replay_confirms_remote_cache` | gap | instruction lacks reset requirement |
| `rustc-wrapper = "sccache"` in `.cargo/config.toml` | `test_sccache_is_wired_into_cargo` | covered | `instruction.md:1` |
| Binary `/app/target/debug/meridian-cli` | `test_workspace_binary_exists` | covered | `instruction.md:3` |
| Do not edit `/app/crates` | `test_crate_sources_were_not_modified` | covered | `instruction.md:3` |
| Avoid legacy nested schema | `test_report_does_not_use_legacy_layout` | covered | `instruction.md:3` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #27, #55, blockers 1–3 |
| `tests/test_outputs.py` | Blockers 1–3, #27, #28 |
| `environment/docs/counter-semantics.md` | Blocker 2, adjudication #2 |
| `environment/docs/duration-thresholds.md` | Blocker 1 |
| `environment/docs/benchmark-output.md` | Blockers 1–2 |
| `environment/docs/internal/release/stat-mapping.md` | Blocker 2 (authoritative mapping) |
| `environment/docs/internal/release/timing-bounds.md` | Blocker 1 (authoritative timing) |
| `solution/solve.sh` | Blocker 3, #23 |
| `environment/Dockerfile` | #14, #15, canonical digest |
| `task.toml` | #45, rubric milestone format |
| `entire-report.txt` | Agent stats, platform rubric CI, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate setup-sccache-minio-rust/
Summary: 0 error(s), 2 warning(s), 2 info
```

Warnings: non-milestone preference (info); false-positive pip line-wrap warning; solution-hint pattern (info).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | 1 failure |
| terminus-claude-opus-4-8 | 20.0% (1/5) | 4 failures |
| oracle | 100.0% (3/3) | per export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (at boundary) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model ≤20% justifies hard) |

Per-test pass rates (`entire-report.txt:50-63`): universal failures on `test_warm_build_is_faster_than_cold` (6/10), `test_post_clean_rebuild_relies_on_cache` (5/10), `test_post_clean_replay_confirms_remote_cache` (8/10).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task folder matches export; regular non-milestone layout |
| 1 Instruction | ☑ | Concise but under-specified on timing/counters/replay |
| 2 Environment | ☑ | Digest-pinned Rust; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Not run locally; export 100%; solve.sh uses correct semantics |
| 4 Verifiers | ☑ | 13 behavior tests; reward block OK; timing ratio checks on self-reported JSON |
| 5 Metadata | ☑ | category/tags match; `number_of_milestones = 0` |
| 6 Rubric | ☑ | Platform CI fail; `# Rubric 1` on non-milestone; `/tests` reference |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed in artifacts |
| 8 Novelty & fairness | ☑ | Doc conflicts cause unfair near-miss failures |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on the sccache + MinIO integration — the environment is well pinned, the verifiers check real cache state (MinIO objects, authentic stats, git integrity), and agent pass rates look reasonable for a hard task. Before we can accept, please fix instruction/test alignment: several top-level docs under `/app/docs/` still say integer-second timing is fine and map `compilations` to “Compile requests executed,” but the verifier expects fractional `warm_seconds` (non-zero sub-second) and Non-cacheable compilations. Also spell out that sccache stats must be reset before the post-clean verification build so replay stats show zero misses. On the rubric side, drop the `# Rubric 1` header (this is a flat non-milestone task), make sure platform Rubric Formatting passes, and rephrase the negative that mentions `/tests`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2, 3 |
| Rubric | yes | 4, 5 |
| Exposing Hints/Answers | yes | — (#17: internal/release docs are ground truth) |
| Pinning Issues | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
| Time Based Tests | no | — (self-reported plausibility ratios; noted only) |
| Milestones | no | — |
