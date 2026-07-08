# Terminus Review Report: `repair-python-oci-build-graph-analysis-with-graphviz-1783444588`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Go depmap repair task — pinned offline env, thorough pytest suite, DB-only anti-cheat, rubric at 38/40 pts with correct non-milestone format, and calibrated difficulty (worst-model 20%). One High blocker remains: `/app/README.md` documents only the three-component `~=` example (`~= 1.4.2` → `< 1.5.0`) while fixtures and tests require two-component `~=` (`~= 3.20` → `>= 3.20.0, < 4.0.0`). Agent trial i5SBXzw failed plausibly on this gap (37/41). Add an explicit two-component rule or example before accept.

**Insights (concise):**

- Instruction delegates constraint grammar to `/app/README.md` (`instruction.md:9`); README is normative but incomplete on `~=` two-component upper bounds (`environment/app/README.md:34`).
- `test_compatible_release_constraint_resolution` enforces `~= 3.20` / `~= 4.0` semantics not stated in README (`tests/test_outputs.py:1273-1287`; fixtures `rpc-gateway.json:6`, `packages.lock.json:476,485`).
- Platform rubric: 38 positive pts (≤40 cap), 7 negatives, `# Rubric 1` only — valid for `number_of_milestones = 0` (`entire-report.txt:319-340`; `task.toml:11`).
- Prior reviewer note about rubric line starting with `Agent's` is **stale** — current line 332 reads `Agent produces byte-identical…` (`entire-report.txt:332`).
- Automated audit #27 false positive on `[4, 5, 72]` — those are resolution output counts (63 nodes, 72 edges), not unstated thresholds (`tests/test_outputs.py:297-298`).
- Oracle not run locally (Docker daemon unavailable); static review of `solution/solve.sh` shows full derived implementation with documented `compatUpper` for both `~=` forms (`solution/solve.sh:283-285`).
- Difficulty: declared `medium`, platform `hard`, worst-model 20% — informational only, not a blocker (`task.toml:10`; `entire-report.txt:15-21`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Two-component compatible-release (`~= X.Y`) upper-bound semantics are tested but not documented in the normative README. Only `~= 1.4.2` → `>= 1.4.2, < 1.5.0` is given; fixtures use `~= 3.20` and `~= 4.0` requiring `>= X.Y.0, < (X+1).0.0`. Agent i5SBXzw implemented `>=` only (no upper bound), a plausible misread. | `environment/app/README.md:34`; `environment/app/data/specs/rpc-gateway.json:6`; `environment/app/data/locks/packages.lock.json:476,485`; `tests/test_outputs.py:1273-1287`; `entire-report.txt:100-108` | Add explicit rule and/or example in `/app/README.md`, e.g. `~= 3.20` means `>= 3.20.0, < 4.0.0` (or general rule: N-component `~=` fixes all but the last segment and allows the final segment to vary). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High: `~=` two-component behavior under-documented; tests need `~= 3.20` → `>= 3.20.0, < 4.0.0` but README only shows three-component example (ChatGPT) | **Agree** | `environment/app/README.md:34` vs `tests/test_outputs.py:1275-1287`; agent failure `entire-report.txt:86,100-108` |
| 2 | Medium: rubric determinism line starts with `Agent's` not `Agent` (prior reviewer feedback in `entire-report.txt:342`) | **Disagree** (fixed) | Current rubric line: `Agent produces byte-identical build-plan.json and depgraph.dot outputs across repeated runs…, +2` (`entire-report.txt:332`) |
| 3 | Low: set `codebase_size = "large"` since main.go is 353 lines (ChatGPT) | **Partially agree** (optional) | `environment/app/main.go` is 353 lines; `task.toml:12` says `small` — cosmetic metadata only, not a blocker |
| 4 | Low: remove unused `source "$HOME/.local/bin/env"` from test.sh (Harbor review / ChatGPT) | **Agree** (optional) | `tests/test.sh:2` — harmless leftover, not a blocker |
| 5 | Dockerfile FROM digest-pinned and appropriate for Go task (ChatGPT) | **Agree** | `environment/Dockerfile:3` — `@sha256:1a6d4452…` with go 1.24 justification comment |
| 6 | Non-canonical base image warning (Harbor review `entire-report.txt:165-187`) | **Disagree** as blocker | Dockerfile comment documents sanctioned Go base choice; digest-pinned; no swap required |
| 7 | Dockerfile pre-creates `/logs/verifier` and `/logs/agent` (Harbor review `entire-report.txt:190-211`) | **Agree** (cosmetic) | `environment/Dockerfile:30` — harmless, not a blocker |
| 8 | Instruction sufficiency FAIL for `~=` gap (`entire-report.txt:77-108`) | **Agree** | Same evidence as claim 1; other trials passed `task_specification` |
| 9 | LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:126`) | **Partially agree** | README chain covers most behaviors; `~=` two-component upper bound is the exception |
| 10 | LLMaJ `behavior_in_tests` PASS (`entire-report.txt:127`) | **Agree** | 41 tests cover instruction + README behaviors comprehensively |
| 11 | Rubric positive total >40 (non-milestone) | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 38/40 PASS |
| 12 | Non-milestone task uses milestone rubric format (`# Rubric 1` header) | **Disagree** as blocker | `rubrics.md:66` — `# Rubric 1` optional on non-milestone; no `# Rubric 2+` present (`entire-report.txt:319-340`; `task.toml:11`) |
| 13 | Automated audit #27 FAIL on numeric thresholds `[4, 5, 72]` | **Disagree** | False positive — 63/72 are expected node/edge counts from resolution (`tests/test_outputs.py:297-298`), not instruction thresholds |
| 14 | Automated review #36 FAIL (negative rubric phrasing) | **Disagree** | Negatives use bad-behavior descriptions with `-N` scores per `rubrics.md:39-41` (`entire-report.txt:333-339`); audit #36 PASS |
| 15 | Automated review #41 FAIL (stray `audit-report.md`) | **Disagree** | `audit-report.md` is reviewer-tool output, not part of task submission |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~16 lines, problem-first; command bullets are interface spec not steps | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer brief tone, no synthetic preamble | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No heavy headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States WHAT (repair plan/graph), not HOW to code solver | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | No algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Subcommands, paths, outputs, node-id formats, determinism all named | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic container build-graph / dep-resolution scenario | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct Go depmap + SQLite constraint-solver repair; no duplicate found in review | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md:3-15` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:22` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned golang:1.24-bookworm | `environment/Dockerfile:3` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY app/ /app/` only | `environment/Dockerfile:25` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | README defines grammar/contracts; fixtures are inputs not answers | `environment/app/README.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only rebuilds depmap + runs pytest | `environment/Dockerfile:22`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed — Docker daemon unavailable locally | oracle run exit 0 trials=0 |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes code and builds locally | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full constraint solver via heredoc; derives plan/graph from DB | `solution/solve.sh:6-1218` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block with failure path | `tests/test.sh:4-21` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifiers apply binary rewards only (0 or 1) | Binary 0/1 reward | `tests/test.sh:17-20` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | `~=` two-component upper bound tested but not in README | blocker 1 |
| 28 | CHECK | Tests check for correctness, not just format | Exact version selection, build order, backtracking scenarios | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Runs binary + asserts outputs/DB | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact values appropriate for deterministic constraint solver | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` have docstrings (AST-verified) | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 7 negative lines | `entire-report.txt:333-339` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All ±1,2,3,5 | `entire-report.txt:320-339` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 20 Agent lines; determinism line fixed (no `Agent's`) | `entire-report.txt:320-339` |
| 35 | CHECK | Rubric criteria are detailed and precise | 38 positive pts ≤40 cap | `entire-report.txt:320-331` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Negatives describe bad behavior with `-N` | `entire-report.txt:333-339` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:320-339` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:320-339` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:320-339` |
| 40 | CHECK | All required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh, test_outputs.py | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean submission layout (audit-report.md is reviewer-generated) | task tree |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both `anonymous` | `task.toml:15-16` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | Go/SQLite/build-graph tags match content | `task.toml:6-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty` present; worst-model 20% → hard tier; declared vs platform differ — informational only | `task.toml:10`; `entire-report.txt:15-21` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/; `.dockerignore` excludes tests | `environment/Dockerfile:25`; `environment/.dockerignore:3` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | `.dockerignore` excludes solution/ and tests/ | `environment/.dockerignore:2-3` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests rebuild binary and assert computed resolution; hardcoded constants not in env | `tests/test.sh:11-15` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% ≤80% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Task is not too hard or unfair (not requiring unavailable info) | `~=` two-component semantics required by tests but absent from normative README | blocker 1; `entire-report.txt:100-108` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Three subcommands with exact flags | `test_outputs_exist` | covered | `instruction.md:5-7` |
| Import loads fixtures into SQLite | `test_build_db_schema`, `test_build_db_imported_full_lock` | covered | `instruction.md:9` |
| Plan/graph work from DB only | `test_plan_and_graph_use_only_the_db` | covered | `instruction.md:9` |
| Constraint grammar (README) | most resolver tests | covered | `instruction.md:9`; `environment/app/README.md` |
| `~=` compatible release (two-component) | `test_compatible_release_constraint_resolution` | **gap** | README only 3-component example (`README.md:34`); test needs `~= 3.20` → `< 4.0.0` (`test_outputs.py:1275-1287`) |
| Version comparison as integers | `test_integer_version_comparison` | covered | `README.md:37-38` |
| Epoch dominance | `test_epoch_version_comparison` | covered | `README.md:39-42` |
| Backtracking / prefer higher versions | `test_version_backtracking`, `test_cascading_backtracking_across_specs` | covered | `instruction.md:11` |
| Conditional markers | `test_conditional_conflict_resolution`, `test_conditional_dependency_membership` | covered | `README.md:49-55` |
| Virtual packages | `test_virtual_package_provider_resolution` | covered | `README.md:57-62` |
| Extras | `test_extras_resolution`, `test_transitive_extras_backtracking` | covered | `README.md:64-68` |
| Spec ordering | `test_spec_ordering_constraints` | covered | `README.md:70-73` |
| Node id formats + topological order | `test_exact_build_order`, `test_topological_order` | covered | `instruction.md:13-14` |
| build-plan.json schema (`depends_on` array not null) | `test_plan_structure`, `test_depends_on_sorted_and_valid` | covered | `instruction.md:15` |
| depgraph.dot format + determinism | `test_dot_*`, `test_plan_deterministic` | covered | `instruction.md:15` |
| Exact closure size (63 nodes, 72 edges) | `test_node_and_edge_counts`, `test_closure_packages_exact` | covered | Derived from fixtures + rules; not phantom thresholds |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, spec alignment |
| `environment/app/README.md` | blocker 1, spec alignment |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/data/specs/rpc-gateway.json` | blocker 1 (`~= 3.20`) |
| `environment/app/data/locks/packages.lock.json` | blocker 1 (`~= 3.20`, `~= 4.0`) |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment, blocker 1 |
| `solution/solve.sh` | #22-23, oracle static review |
| `task.toml` | #42-45, milestone N/A |
| `entire-report.txt` | #32-39, #45, #54, agent stats, rubric, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate repair-python-oci-build-graph-analysis-with-graphviz-1783444588/
Summary: 0 error(s), 0 warning(s), 2 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | 1 non-timeout failure |
| terminus-claude-opus-4-8 | 20.0% (1/5) | 4 timeouts |
| oracle | 100.0% (3/3) | per platform report |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | medium |
| Platform classified | hard |
| Tier match (#45) | informational only — CHECK #45 |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task folder matches report; regular layout; Go depmap repair |
| 1 Instruction | ☑ | Concise engineer brief; README chain for grammar |
| 2 Environment | ☑ | Digest-pinned Go base; tmux+asciinema; offline; no tests/solution in image |
| 3 Oracle | ☐ | Not executed (Docker unavailable); static review PASS |
| 4 Verifiers | ☑ | Canonical test.sh; 41 behavioral tests; binary reward |
| 5 Metadata | ☑ | Complete; non-milestone; allow_internet=false |
| 6 Rubric | ☑ | 38/40 pts; 7 negatives; `# Rubric 1` only OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL on `~=` confirmed; timeout gate OK |
| 8 Novelty & fairness | ☑ | Multi-step solver; anti-cheat strong; `~=` doc gap unfair |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid depmap repair task — the stubbed prototype is clear, the offline Go/SQLite setup is clean, and the test suite is exceptionally thorough (rebuilds the agent binary, enforces DB-only plan/graph, and exercises backtracking, markers, virtuals, extras, and deterministic ordering). The rubric looks good now too (38 points, determinism line correctly starts with “Agent”). One fix before we can accept: `/app/README.md` only documents the three-component `~=` example (`~= 1.4.2` → `< 1.5.0`), but the fixtures and tests also rely on two-component `~=` like `~= 3.20` meaning `>= 3.20.0, < 4.0.0`. Please add that rule or a concrete two-component example so the upper-bound behavior isn’t ambiguous.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
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
