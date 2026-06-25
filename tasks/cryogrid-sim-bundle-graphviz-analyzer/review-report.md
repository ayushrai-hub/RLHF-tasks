# Terminus Review Report: `cryogrid-sim-bundle-graphviz-analyzer`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Test Alignment/Coverage Issues, Exposing Hints/Answers, Environment, Metadata Issues

**Decision (concise):** Revise. Hard calibration is supported (GPT-5.5 0%, Claude 100%; worst-model 0% matches `difficulty = hard`). Dockerfile is digest-pinned on the canonical `gcc:13-bookworm` base, oracle solution is algorithmic, and substantive C++/variance/loop logic is well tested. Blockers: DOT tests require unquoted bare node/edge identifiers never stated in instruction or SECTION 72 (systematic 5/10 failures on two DOT tests); hidden verifier bundle JSON is baked into the agent image at `/opt/verifier-fixtures/bundles/`; `subcategories` omits `long_context` despite a 280k-char memo and `test_memo_is_long_context`.

**Insights (concise):**

- All five GPT-5.5 runs failed only `test_baseline_dot_pipeline_order_and_annotations` and `test_dot_graph_has_all_edges` (5/10 each); all other logic tests passed 10/10 — classic unstated-format gap, not implementation failure.
- `gcc:13-bookworm@sha256:930f2ebe…` is listed as a canonical C++ base in `docs/guidelines/dockerfxile.md` — ChatGPT’s non-canonical-base claim is incorrect.
- Automated `terminus review` falsely flagged #14, #20, #31, #45, #54 (pip uses `--require-hashes`, pytest is in image, docstrings exist, worst model is 0% not 100%).
- Hidden fixtures are readable but do not leak computed answers; tests derive expectations via `reference_variances()` / `reference_loops()`. Still undermines “hidden integration” intent.
- Rubric text in `entire-report.txt` (portal submission) meets format/negative-count rules; not stored in task folder.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #30, #55 | DOT verifier enforces unquoted bare node IDs and edges; instruction + SECTION 72 never require unquoted identifiers. Quoted DOT is valid Graphviz. | `tests/test_outputs.py:165-168` uses `f"  {sid} ["`; `tests/test_outputs.py:246` uses `f"  {dep} -> {stage['id']};"`; `generate_validation_memo.py:40-44` SECTION 72 omits quoting; `entire-report.txt:20-21,40-42` 5/10 on both DOT tests | Add “node IDs and edge endpoints must be unquoted bare identifiers” to SECTION 72 and/or `instruction.md`, **or** relax tests to accept valid quoted DOT (e.g. parse with graphviz or normalize). |
| 2 | Medium | Exposing Hints/Answers, Environment | #51 | Hidden verifier bundles copied into agent runtime image; agents can read integration inputs before verifier runs. | `environment/Dockerfile:34` `COPY verifier-fixtures/bundles/ /opt/verifier-fixtures/bundles/`; `instruction.md:5` mentions hidden checks; fixtures at `environment/verifier-fixtures/bundles/*.json` | Mount or inject verifier bundles at test time only (Harbor `/tests` side or runtime copy in `test.sh`), not in agent image. |
| 3 | Medium | Metadata Issues | #44 | Task depends on ~280k-char validation memo and asserts long-context threshold in tests, but `subcategories = []`. | `task.toml:8`; `generate_validation_memo.py:9` `TARGET_CHARS = 280_000`; `tests/test_outputs.py:133-139` `test_memo_is_long_context` | Set `subcategories = ["long_context"]` and confirm memo meets `docs/guidelines/long-context-checklist.md` (grep-solvable SECTION blocks are a risk). |

*No other High-severity blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | DOT verifier enforces unquoted IDs but docs do not; quoted DOT is valid; all agents failed same two DOT tests (ChatGPT) | **Agree** | `test_outputs.py:165-168,246`; SECTION 72 in `generate_validation_memo.py:40-44` silent on quoting; `entire-report.txt:20-21,40-66` |
| 2 | Dockerfile copies verifier-fixtures into runtime image exposing hidden inputs (ChatGPT / LLMaJ) | **Agree** | `Dockerfile:34`; contradicts `entire-report.txt:227-228` (“invisible to agent”) |
| 3 | `gcc:13-bookworm` is non-canonical without exemption (ChatGPT / entire-report §CRITICAL) | **Disagree** | `docs/guidelines/dockerfxile.md:14` lists exact image+digest used in `Dockerfile:1` |
| 4 | Missing `long_context` subcategory (ChatGPT / entire-report WARNING) | **Agree** | `task.toml:8`; `test_memo_is_long_context`; `TARGET_CHARS = 280_000` |
| 5 | Difficulty mismatch / task too easy — worst model 100% (automated `terminus review`) | **Disagree** | `entire-report.txt:6-7` GPT 0%, Claude 100%; worst model = 0% ≤20% → hard tier per `docs/guidelines/difficulty.md` |
| 6 | pytest not in Dockerfile / unpinned pip (#14, #20 automated blockers) | **Disagree** | `requirements.lock:9-10` pins pytest with hash; `Dockerfile:19-21` installs via `--require-hashes`; `test.sh:30` uses baked venv only |
| 7 | Tests missing docstrings (#31 automated) | **Disagree** | Every `test_*` in `test_outputs.py` has one-line docstring (e.g. `:133-134`, `:158-159`) |
| 8 | COUPLER formula / memo length not in instruction (LLMaJ `behavior_in_task_description`) | **Partially agree** | COUPLER in SECTION 37 (`generate_validation_memo.py:28-29`); instruction delegates to memo (`instruction.md:1-3`). Env-only `test_memo_is_long_context` is not an agent requirement — Low, not blocking. |
| 9 | Hidden fixtures are excellent anti-cheat because invisible (entire-report strengths) | **Disagree** | Same as claim #2 — fixtures are on disk at `/opt/verifier-fixtures/bundles/` |
| 10 | DOT six-decimal `var=` check is global not per-node (test-quality review) | **Partially agree** | `test_outputs.py:169` searches whole DOT once per loop iteration; Low severity — numeric tests catch wrong values |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 short paragraphs | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer task framing, not LLM role-play | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes only | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No file-level fix walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | DOT bare-ID format unstated vs enforced tests | Blocker #1 |
| 8 | CHECK | Instruction is interesting | Realistic C++/scientific pipeline debugging | — |
| 9 | CHECK | Instruction is unique | CryoGrid bundle analyzer not a common TB duplicate | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `requirements.lock` uses `==` + hashes | `environment/requirements.lock`, `Dockerfile:21` |
| 15 | CHECK | Base Docker image is pinned by digest | Canonical gcc digest | `Dockerfile:1`, `dockerfxile.md:14` |
| 16 | CHECK | Environment does not use context from outside environment/ | Self-contained | `environment/` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Starter bugs only; no answer file | `environment/src/`, `environment/README.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in image venv; test.sh no apt/pip | `Dockerfile:19-21`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not run in this audit | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | Copies C++ + cmake build | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Algorithmic C++ modules | `solution/files/*.cpp` |
| 24 | CHECK | test.sh writes reward.txt; handles failure | Canonical reward block | `tests/test.sh:5-7,33-37` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0/1 in test.sh | `tests/test.sh:33-37` |
| 27 | UNCHECK | All tests aligned with instructions | Unquoted DOT IDs tested, not specified | Blocker #1 |
| 28 | CHECK | Tests check for correctness, not just format | Reference implementations + numeric tolerance | `tests/test_outputs.py:48-130,142-155` |
| 29 | CHECK | Tests verify behavior, not implementation | CLI output only | `tests/test_outputs.py` |
| 30 | UNCHECK | No brittle exact string matching where flexible checks would work | DOT substring checks on unstated bare-ID format | `tests/test_outputs.py:165-168,246` |
| 31 | CHECK | Tests have informative names or docstrings | All 12 tests named + docstring | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 5 negatives in portal rubric | `entire-report.txt:329` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All scores valid | `entire-report.txt:329` |
| 34 | CHECK | Each rubric criterion one line Agent, score | Format matches | `entire-report.txt:329` |
| 35 | CHECK | Rubric criteria detailed and precise | Specific behaviors referenced | `entire-report.txt:329` |
| 36 | CHECK | Rubric uses positive language with negative scores | “Agent hardcodes…, -3” pattern | `entire-report.txt:329` |
| 37 | CHECK | Rubric does not reference /tests/ | No pytest paths | `entire-report.txt:329` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | References memo SECTIONs only | `entire-report.txt:329` |
| 39 | CHECK | Rubric does not mention oracle or NOP | None | `entire-report.txt:329` |
| 40 | CHECK | All required files present | Regular layout complete | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Set in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | timeouts, allow_internet=false | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories applicable | Missing `long_context` subcategory | Blocker #3 |
| 45 | CHECK | Difficulty matches observed agent pass rates | hard + worst model 0% | `task.toml:6`, `entire-report.txt:6-7` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — regular task | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | UNCHECK | Solution or ground truth not accessible in environment | Hidden verifier bundles readable at `/opt/verifier-fixtures/` | Blocker #2 |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Tests use reference math; hidden bundles still need correct logic | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model 0% | `entire-report.txt:6-7` |
| 55 | UNCHECK | Task is not too hard or unfair | Unstated DOT quoting caused deterministic GPT failures | `entire-report.txt:35-66` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 30, 44, 46, 47, 48, 49, 51, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Load bundle JSON; propagate variance per memo SECTION 37 | `test_baseline_metrics_match_reference`, `test_coupler_stage_variance`, `test_permafrost_sink_passes_variance` | covered | `instruction.md:1-3`; `test_outputs.py:142-155,222-235,261-278` |
| Frozen soil epsilon floor SECTION 58 | `test_hidden_frozen_soil_epsilon_floor` | covered | `generate_validation_memo.py:34-38`; `test_outputs.py:187-201` |
| Unstable feedback loops SECTION 91 | `test_hidden_unstable_feedback_loop`, `test_hidden_feedback_bundle_id` | covered | `test_outputs.py:172-184,282-288` |
| DOT pipeline order + var/class annotations SECTION 72 | `test_baseline_dot_pipeline_order_and_annotations`, `test_dot_graph_has_all_edges` | gap | SECTION 72 lacks unquoted-ID rule; tests require bare IDs |
| JSON metrics schema fields | `test_metrics_schema_fields`, `test_stage_order_matches_pipeline_array` | covered | `metrics-schema.md`; `test_outputs.py:204-213,249-258` |
| CLI `--spec` / `--out-dir`; binary exists | `test_analyzer_binary_exists` | covered | `instruction.md:3`; `test_outputs.py:215-219` |
| Smoke with `/app/fixtures/cryo-baseline.json` | `test_baseline_*` | covered | `instruction.md:5` |
| Memo ≥200k chars (environment) | `test_memo_is_long_context` | phantom (env check) | Not an agent requirement; prebuilt at `Dockerfile:37-38` |
| Unquoted DOT node/edge identifiers | `test_baseline_dot_pipeline_order_and_annotations`, `test_dot_graph_has_all_edges` | phantom | Not in instruction or SECTION 72 |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blocker 1, spec alignment |
| `task.toml` | #44, #45, blocker 3 |
| `environment/Dockerfile` | #15, #20, blocker 2 |
| `environment/requirements.lock` | #14 |
| `environment/scripts/generate_validation_memo.py` | SECTION 72, long-context, blocker 1 |
| `environment/verifier-fixtures/bundles/*.json` | blocker 2 |
| `tests/test_outputs.py` | #27, #30, #31, blockers 1–2 |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh`, `solution/files/dot_emitter.cpp` | #23, oracle DOT format |
| `docs/guidelines/dockerfxile.md` | adjudication claim 3 |
| `entire-report.txt` | agent stats, rubric, DOT failure pattern |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate cryogrid-sim-bundle-graphviz-analyzer/
Summary: 0 error(s), 13 warning(s), 2 info
```

Warnings: informative_test_docstrings (false positive — docstrings exist); pip pin heuristic (false positive — `--require-hashes`).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All runs 10/12 tests; DOT quoting only |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Full pass |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test (from report): `test_baseline_dot_pipeline_order_and_annotations` 5/10; `test_dot_graph_has_all_edges` 5/10; all others 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular C++ task; folder matches report |
| 1 Instruction | ☑ | Concise; DOT quoting gap |
| 2 Environment | ☑ | Canonical gcc base; verifier fixtures in image |
| 3 Oracle | ☐ | Not executed (Docker/Harbor unavailable) |
| 4 Verifiers | ☑ | Strong reference tests; DOT format gap |
| 5 Metadata | ☑ | Missing long_context tag |
| 6 Rubric | ☑ | Evaluated from `entire-report.txt` portal text |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated contradictions in report |
| 8 Novelty & fairness | ☑ | Multi-bug C++ task; unfair DOT quoting |
| 9 Long context | ☑ | Memo size qualifies; grep-solvable SECTIONs weak for LC bar |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Hard calibration is fine (GPT-5.5 0%, Claude 100%) and the canonical digest-pinned `gcc:13-bookworm` base is correct. Fix first: DOT tests require unquoted bare node/edge IDs but SECTION 72 and `instruction.md` never state that — quoted Graphviz DOT is valid and caused all GPT failures on the two DOT tests. Also move verifier bundles out of the agent image (`/opt/verifier-fixtures/bundles/` is readable) and add `long_context` to `subcategories` if the 280k memo is intentional.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Exposing Hints/Answers | yes | 2 |
| Environment | yes | 2 |
| Metadata Issues | yes | 3 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review cryogrid-sim-bundle-graphviz-analyzer/ --report entire-report.txt`._
