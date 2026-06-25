# Terminus Review Report: go-service-mesh-traffic-split-repair

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** No High-severity blockers found on re-audit. Instruction, routing contract, verifiers, oracle, digest-pinned canonical Go base, and anti-cheat layers align. Prior `matchHeaders` coupling is resolved — injected Go tests exercise exported `RouteRequests` behavior. Worst-model pass rate is 60% (Claude), matching declared `medium`. Recommend Accept; optional metadata tweak: `category` fits `debugging` better than `data-processing`.

**Insights (concise):**

- Dockerfile uses the **canonical** `golang:1.24-bookworm` digest from `docs/guidelines/dockerfxile.md` — external “non-canonical base” warning is incorrect.
- Injected Go tests call `RouteRequests` with fresh configs; they do **not** reference internal `matchHeaders` (prior reviewer concern fixed).
- `routing_contract.txt` normatively covers every tested behavior (`enabled`, `mode`, raw weights, case-insensitive names, schema).
- Oracle pass confirmed locally (`Mean: 1.000`, 1 trial).
- Wrong-category metadata (`data-processing` vs `debugging`) is Medium-only — not a Revise blocker.
- ELF/mtime rebuild check is implicit in “rebuild binary from Go source”; Dockerfile pre-builds ELF via `go build`.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Prior reviewer: verifier depends on undocumented internal `matchHeaders` helper (entire-report.txt L1–3) | Disagree (resolved) | Injected tests call `RouteRequests` only: `tests/test_outputs.py:249,264,275,316,329`; `matchHeaders` appears only in env/solution Go sources, not verifiers |
| 2 | ChatGPT: Accept — behavior validated via exported routing API (user) | Agree | Same as #1; tests inject `routing_contract_extra_test.go` / `routing_contract_modes_test.go` exercising `RouteRequests` |
| 3 | Failure analysis: injected tests reference undocumented `models.SplitConfig` type names (entire-report.txt L71–73) | Disagree | Types ship in `environment/splitter/models/models.go`; module path `github.com/terminal-bench/splitter` in `go.mod`; contract documents `enabled`/`mode` fields used in injected literals |
| 4 | Failure analysis: ELF requirement unstated in instruction (entire-report.txt L74, L98) | Partially agree | `test_binary_was_rebuilt_from_go_sources` checks `b"\x7fELF"` at `tests/test_outputs.py:190–191`; instruction says “rebuild `/app/bin/splitter` from that source tree” (`instruction.md:1`) — implicit but reasonable in Go context; Low severity, not Revise |
| 5 | Failure analysis: Go toolchain missing at standard PATH (entire-report.txt L84–94) | Disagree | `environment/Dockerfile:6` sets `ENV PATH="/usr/local/go/bin:${PATH}"`; agent failure was discovery error, not env defect |
| 6 | Automated report: non-canonical Dockerfile base (entire-report.txt L138–157) | Disagree | `environment/Dockerfile:1` matches canonical digest in `docs/guidelines/dockerfxile.md:11` |
| 7 | Portal note: golang:1.23 non-canonical without justification (entire-report.txt L296–298) | Disagree | Stale — task uses `golang:1.24-bookworm@sha256:1a6d4452…` which **is** canonical |
| 8 | Quality checks: behavior_in_task_description PASS (entire-report.txt L102) | Agree | `routing_contract.txt:8–57` documents all tested semantics; instruction points to contract as source of truth |
| 9 | Quality checks: behavior_in_tests PASS (entire-report.txt L103) | Agree | 22 pytest functions cover schema, fixture routing, rebuild/rerun, injected Go modes |
| 10 | Difficulty MEDIUM, solvable (entire-report.txt L6–8) | Agree | Claude 60%, GPT 80%; worst 60% → medium tier per `docs/guidelines/difficulty.md` |
| 11 | Automated review script: #45 fail — worst-model 80% (review-report baseline) | Disagree | Worst model is Claude **60%**, not GPT 80%; declared `medium` in `task.toml:6` is correct |
| 12 | Test quality: contains-token/absent only in injected Go tests (entire-report.txt L260–264) | Agree (non-blocking) | Modes documented in contract; injected tests at `tests/test_outputs.py:296–341` close shortcut gap |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two short paragraphs, ~83 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer repair request, not LLM spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal + contract reference only | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT (repair, rebuild, regenerate), not HOW to fix bugs | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input/output mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear paths, contract, output file, rebuild requirement | `instruction.md:1–3` |
| 8 | CHECK | Instruction is interesting | Realistic Go service-mesh routing repair | — |
| 9 | CHECK | Instruction is unique | Distinct Go traffic-split repair with contract-driven debugging | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment/...`, `/app/bin/splitter`, `/app/output/...` | `instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in body | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Full digest on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only env subdirs | `environment/Dockerfile:20–24` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Contract is behavioral spec, not answers; no solution leakage | `environment/docs/routing_contract.txt` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:18`, `tests/test.sh:15` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Local oracle Mean 1.000 | `./scripts/terminus oracle` 2026-06-24 |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh patches Go, go build, runs binary | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Fixes splitter/models, rebuilds, runs SEED=7 | `solution/solve.sh:51–186` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical 0/1 block | `tests/test.sh:12–23` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary reward | `tests/test.sh:19–22` |
| 27 | CHECK | All tests are aligned with instructions | Every assertion traces to instruction or routing_contract.txt | See §5 |
| 28 | CHECK | Tests check for correctness, not just format | Routing behavior, weights, header modes, rebuild | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | JSON output checks + `RouteRequests` API tests, no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Schema/behavior checks; fixture uses contract constants | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 22 tests have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | Six negatives in portal rubric | `entire-report.txt:289–293` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Uses ±1,2,3,5 only | `entire-report.txt:283–293` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | Format matches | `entire-report.txt:283–293` |
| 35 | CHECK | Rubric criteria are detailed and precise | Behavior-specific routing criteria | `entire-report.txt:283–293` |
| 36 | CHECK | Rubric criteria use positive language | “Agent implements…”, “Agent hardcodes…”, negatives use -N | `entire-report.txt:283–293` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:283–293` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata/instruction refs | `entire-report.txt:283–293` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP | `entire-report.txt:283–293` |
| 40 | CHECK | All required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh, test_outputs.py | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both anonymous | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts, allow_internet=false | `task.toml` |
| 44 | UNCHECK | Tags, languages, categories are applicable to the task | `category = "data-processing"` — primary activity is Go bug repair (`debugging`/`software-engineering` per taxonomy) | `task.toml:7`, `docs/task-type-taxonomy.md:15–29` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared medium; worst-model Claude 60% → medium tier (20–60%) | `task.toml:6`, `entire-report.txt:10–11` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:12` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests/; no COPY tests | `environment/.dockerignore:13`, `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ and tests/ in .dockerignore | `environment/.dockerignore:12–13` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Verifier reruns binary, injected Go tests use novel configs | `tests/test_outputs.py:199–341` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% < 80% | `entire-report.txt:10–11` |
| 55 | CHECK | Task is not too hard or unfair | Go on PATH, complete contract, fair API-level injected tests | `environment/Dockerfile:6`, `routing_contract.txt` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/routing_result.json` | `test_output_file_exists` | covered | `instruction.md:1`, `tests/test_outputs.py:49–51` |
| Output schema (`routed_requests`, `summary` fields) | `test_output_has_routed_requests_and_summary`, `test_routed_request_schema_and_order`, `test_summary_schema_and_types` | covered | `routing_contract.txt:51–57`, `tests/test_outputs.py:59–90` |
| Preserve input order | `test_routed_request_schema_and_order` | covered | `routing_contract.txt:52`, `tests/test_outputs.py:73` |
| Exclude disabled backends | `test_disabled_backend_is_never_selected`, injected `TestExtraDisabledBackendNeverWins` | covered | `routing_contract.txt:12`, `tests/test_outputs.py:119–124,239–252` |
| Raw-weight weighted choice | `test_expected_weights_report_enabled_config_weights`, `TestExtraRawWeightSequenceMatchesReference` | covered | `routing_contract.txt:30–32`, `tests/test_outputs.py:136–140,269–283` |
| Case-insensitive header names | `test_case_insensitive_header_names_enable_canary_v2` | covered | `routing_contract.txt:20`, `tests/test_outputs.py:161–168` |
| exact / contains-token / absent modes | `TestExtraContainsTokenMode…`, `TestExtraAbsentMode…` | covered | `routing_contract.txt:17–23`, `tests/test_outputs.py:308–331` |
| canary-v3 requires Authorization | `test_v3_requires_authorization_token`, `TestExtraAuthorizedV3…` | covered | `routing_contract.txt:25`, `tests/test_outputs.py:171–181,255–266` |
| Rebuild `/app/bin/splitter` from source | `test_binary_was_rebuilt_from_go_sources` | covered | `instruction.md:1`, `tests/test_outputs.py:187–196` |
| Binary rerunnable (anti static JSON) | `test_binary_rerun_is_valid_and_overwrites_output`, `test_seeded_rerun_preserves_disabled_and_fallback_contracts` | covered | `instruction.md:3`, `tests/test_outputs.py:199–218` |
| No fallback for supplied fixture | `test_no_fallback_for_supplied_requests` | covered | `routing_contract.txt:29`, `tests/test_outputs.py:143–146` |
| `balanced` diagnostic only (type, not routing value) | `test_summary_schema_and_types` | covered | `routing_contract.txt:57`, `tests/test_outputs.py:88` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, #27, spec alignment |
| `task.toml` | #42–45, #46–49 |
| `environment/Dockerfile` | #13–20, canonical base, oracle env |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/routing_contract.txt` | #17, #27, spec alignment |
| `environment/splitter/splitter/splitter.go` | Buggy baseline, `RouteRequests` API |
| `environment/splitter/models/models.go` | Shipped type definitions |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, injected Go tests, anti-cheat |
| `solution/solve.sh` | #21–23, oracle path |
| `entire-report.txt` | Agent stats, rubric, external adjudication |
| `docs/guidelines/dockerfxile.md` | Canonical base proof |
| `docs/guidelines/difficulty.md` | #45, #54 tier rules |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-service-mesh-traffic-split-repair ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | `entire-report.txt:11` |
| terminus-claude-opus-4-8 | 60.0% (3/5) | `entire-report.txt:10` |
| oracle | 100.0% (3/3) | `entire-report.txt:15`; local run 1/1 pass |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | medium |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; Go repair task |
| 1 Instruction | ☑ | Concise, absolute paths, contract reference, no hints |
| 2 Environment | ☑ | Canonical digest-pinned Go base; tmux+asciinema; .dockerignore; 132K |
| 3 Oracle | ☑ | Passes locally; programmatic fix + rebuild |
| 4 Verifiers | ☑ | reward.txt canonical; no runtime installs; behavior + API tests |
| 5 Metadata | ☑ | allow_internet=false; category mis-tagged (Medium, non-blocking) |
| 6 Rubric | ☑ | Portal rubric in report meets format/negatives |
| 7 LLMaJ & agent evidence | ☑ | Quality checks pass; prior matchHeaders issue resolved |
| 8 Novelty & fairness | ☑ | Multi-bug Go repair; anti-cheat closed; Go on PATH |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The instruction is concise and points to `routing_contract.txt` as the behavioral source of truth; tests cover schema, fixture routing, binary rebuild/rerun, and injected Go API tests via `RouteRequests` (the prior `matchHeaders` coupling is resolved). The environment uses the canonical digest-pinned `golang:1.24-bookworm` base with verifier deps baked in, oracle passes, and worst-model pass rate (Claude 60%) matches declared medium difficulty. Optional polish: change `category` from `data-processing` to `debugging`.

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
