# Terminus Review Report: `mp9`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (per `entire-report.txt`; not re-run — Docker unavailable locally) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Uses Internet, Test Alignment/Coverage Issues, Metadata Issues

**Decision (concise):** Strong Go MVS tooling task with clean scaffold, gofmt/go-vet enforcement, comprehensive verifiers, and a well-formed rubric (36/40 positive). Two real blockers prevent acceptance: `allow_internet = true` violates Edition 2 offline-runtime policy while instruction, spec, and tests all require live `proxy.golang.org` calls; and `test_quote_prerelease_ordering` pins the exact full live version list for `rsc.io/quote`, making the verifier brittle if a new tag ships. Category `data-processing` is a weaker fit than `software-engineering` or `build-and-dependency-management` but is secondary.

**Insights (concise):**

- `allow_internet = true` fails `./scripts/terminus validate` and conflicts with `docs/task-requirements.md` mandatory `false`.
- Instruction (`instruction.md:3`), spec (`docs/spec.md:5-6`), and every test docstring assert live-proxy dependency — redesign needs bundled/frozen proxy fixtures.
- `test_quote_prerelease_ordering` (`tests/test_outputs.py:112-124`) is the only versions test still pinning a full exact list; `test_sampler_versions_sorted` already uses the resilient ordering+subset pattern.
- Platform rubric uses optional `# Rubric 1` header on a non-milestone task — format is valid; 36 positive points ≤ 40 cap.
- Prior reviewer notes on missing gofmt/vet tests and `workdir` field are stale — both are fixed in current artifacts.
- Pip packages in Dockerfile are pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); automated #14 fail is a multiline-line false positive.
- Agent calibration looks appropriate: worst-model 0%, oracle 100%, declared `hard`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Uses Internet, Environment | #43, #55 | `allow_internet = true`; task requires live `proxy.golang.org` at runtime | `task.toml:17`; `instruction.md:3`; `docs/spec.md:5-6`; `tests/test_outputs.py:1-3`; validate error | Set `allow_internet = false`; bundle frozen proxy responses (or local stub server) so verifiers run offline; update instruction/spec accordingly |
| 2 | Medium | Test Alignment/Coverage Issues | #30 | `test_quote_prerelease_ordering` asserts exact full live version list — breaks if `rsc.io/quote` publishes a new tag | `tests/test_outputs.py:112-124` | Convert to ordering-property + stable known-subset pattern (same as `test_sampler_versions_sorted:90-105`) |
| 3 | Medium | Metadata Issues | #44 | Category `data-processing` mismatches primary activity (Go CLI / MVS / semver tooling) | `task.toml:7`; `docs/task-type-taxonomy.md:11-13,27` | Change to `software-engineering` or `build-and-dependency-management` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Runtime internet dependency is a blocker (`allow_internet = true`, live `proxy.golang.org`) (ChatGPT) | **Agree** | `task.toml:17`; `instruction.md:3`; validate: `allow_internet = false is required` |
| 2 | `test_quote_prerelease_ordering` pins exact live version list and is fragile (ChatGPT / `entire-report.txt` review) | **Agree** | `tests/test_outputs.py:112-124` exact equality on 11 versions |
| 3 | Category should be software-engineering, not data-processing (ChatGPT) | **Agree** | `task.toml:7` = `data-processing`; task implements Go semver/MVS/go.mod tooling per taxonomy |
| 4 | Rubric uses non-milestone flat format with positive total under 40 — no rubric blocker (ChatGPT) | **Agree** | `entire-report.txt:351-370`; `./scripts/terminus rubric-points` → 36/40; `docs/guidelines/rubrics.md:66` allows optional `# Rubric 1` on non-milestone |
| 5 | Non-milestone task is in milestone rubric format (`# Rubric 1` header) (user query) | **Disagree** | `entire-report.txt:351` has only `# Rubric 1` (no `# Rubric 2+`); `rubrics.md:66`: "`# Rubric 1` optional; no `# Rubric 2+`" on non-milestone — compliant |
| 6 | gofmt/go vet not enforced by verifier (prior `Reviewer Feedback`) | **Disagree** (stale) | `tests/test_outputs.py:64-86` `test_sources_are_gofmt_clean`, `test_go_vet_clean`; 10/10 pass in `entire-report.txt:56-57` |
| 7 | Remove `workdir` field from task.toml (prior `Reviewer Feedback`) | **Disagree** (already fixed) | `task.toml` has no `workdir` field |
| 8 | `build-and-dependency-management` is not a valid category (prior `Reviewer Feedback`) | **Disagree** | `docs/task-type-taxonomy.md:10` lists it as valid; current value is `data-processing` anyway |
| 9 | Dockerfile FROM not digest-pinned (ChatGPT short note) | **Disagree** | `environment/Dockerfile:1` has `@sha256:1a6d4452…` |
| 10 | Pip deps unpinned (#14 audit fail) | **Disagree** (false positive) | `environment/Dockerfile:13-15` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` on continuation lines |
| 11 | Rest of task strong: scaffold, coverage, oracle, NOP, rubric (ChatGPT) | **Agree** | `entire-report.txt:38-48` oracle 100%, nop 0%; 21 tests with docstrings; rubric 7 negatives |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose blocks, ~229 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Conversational engineer tone; defers detail to `/app/docs/spec.md` | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States WHAT (finish stubs, build binary), not algorithm steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, build command, spec reference | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic Go module-proxy tooling exercise | `instruction.md`, `docs/spec.md` |
| 9 | UNCHECK | Instruction is unique | Corpus uniqueness not verified from artifacts | — |
| 10 | CHECK | All paths in instruction are absolute | `/app`, `/app/gomvs`, `/app/docs/spec.md` | `instruction.md:1,4` |
| 11 | CHECK | Task name does not appear in instruction.md | No `mp9` reference | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build only apt/pip/COPY local scaffold | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:13-15` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | golang:1.24-bookworm digest-pinned | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only `gomvs-app/` | `environment/Dockerfile:20` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Fixtures/README disclaim no expected answers; stubs return `not_implemented` | `fixtures/README.md:3-5` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:13-15`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report: oracle 100% (3/3) | `entire-report.txt:48` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes Go sources and builds; no curl/pip in solve | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | solve.sh implements EscapePath, semver, parser, MVS BFS | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Writes 0 upfront, 1/0 after pytest | `tests/test.sh:3-11` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | Binary reward pattern | `tests/test.sh:8-11` |
| 27 | CHECK | All tests are aligned with instructions | Tests follow `/app/docs/spec.md` contract referenced in instruction | `instruction.md:4`, `docs/spec.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Asserts computed MVS lists, semver order, parsed go.mod lines | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Subprocess on built binary stdout; no source grep | `tests/test_outputs.py:31-33` |
| 30 | UNCHECK | No brittle exact string matching where flexible checks would work | `test_quote_prerelease_ordering` pins full exact 11-version list | `tests/test_outputs.py:112-124` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 7 negatives | `entire-report.txt:364-370` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:351-370` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 19 properly formatted lines | `entire-report.txt:351-370` |
| 35 | CHECK | Rubric criteria are detailed and precise | 36 positive pts ≤ 40 cap | `entire-report.txt:351-370` |
| 36 | CHECK | Rubric criteria use positive language | Bad behaviors use negative scores | `entire-report.txt:364-370` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:351-370` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:351-370` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:351-370` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | `mp9/` |
| 41 | CHECK | No unnecessary files in parent directory | No jobs/, stray README at task root | `mp9/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both present | `task.toml:4-5` |
| 43 | UNCHECK | All other required metadata fields present | `allow_internet = true` — must be `false` | `task.toml:17`; `docs/task-requirements.md:30` |
| 44 | UNCHECK | Tags, languages, categories are applicable to the task | `data-processing` mismatches Go tooling/MVS focus | `task.toml:7` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard` present; worst-model 0% | `task.toml:6`, `entire-report.txt:38-44` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A — not a milestone task | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A — not a milestone task | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A — not a milestone task | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile:20` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Stubs only; no solution COPY | `environment/Dockerfile`, stub files |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Must implement four cores and build working binary | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate) | Worst-model 0% ≤ 80% | `entire-report.txt:43-44` |
| 55 | UNCHECK | Task is not too hard or unfair | Live-proxy requirement conflicts with offline runtime policy | `task.toml:17`, `instruction.md:3` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 30, 43, 44, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build with `go build -o /app/gomvs .` | autouse `build_binary` fixture | covered | `instruction.md:1`; `tests/test_outputs.py:18-28` |
| gofmt-clean code | `test_sources_are_gofmt_clean` | covered | `instruction.md:3`; `tests/test_outputs.py:64-74` |
| go vet-clean code | `test_go_vet_clean` | covered | `instruction.md:3`; `tests/test_outputs.py:76-86` |
| `versions` — semver ascending order | `TestVersions` (4 tests) | covered | `docs/spec.md:28-30`; `tests/test_outputs.py:89-150` |
| Proxy path escaping for uppercase paths | `test_uppercase_path_is_escaped` | covered | `docs/spec.md:22-24`; `tests/test_outputs.py:128-135` |
| `gomod` — parse quoted/block/replace/exclude | `TestGoMod` (4 tests) | covered | `docs/spec.md:32-53`; `tests/test_outputs.py:153-209` |
| `mvs` — MVS build list, replace, exclude target | `TestMVS` (6 tests) | covered | `docs/spec.md:55-62`; `tests/test_outputs.py:212-265` |
| `resolve` — version or `not_found` | `TestResolve` (5 tests) | covered | `docs/spec.md:64-67`; `tests/test_outputs.py:268-301` |
| Main-module replace pins replacement version in output | `test_main_module_replace_forces_version` | covered | `docs/spec.md:60-61`; `tests/test_outputs.py:293-301` |
| Live proxy reads (instruction claim) | all command tests | covered (but blocked by policy) | `instruction.md:3`; offline runtime requires bundled fixtures instead |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blockers 1, 3; #43, #44, #45 |
| `instruction.md` | Blocker 1; #1-12, #27 |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/gomvs-app/docs/spec.md` | Blocker 1; spec alignment |
| `tests/test_outputs.py` | Blockers 1-2; #27-31 |
| `tests/test.sh` | #24-26 |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | Agent stats, rubric, prior feedback adjudication |
| `docs/task-requirements.md` | Blocker 1 policy |
| `docs/guidelines/rubrics.md` | Rubric format adjudication |
| `docs/task-type-taxonomy.md` | Blocker 3 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: mp9/ ===
ERROR: task.toml [task.toml]: allow_internet = false is required in [environment]
WARNING: pinned_dependencies [environment/Dockerfile]: Pin pip packages with == versions: RUN python3 -m pip install ...
INFO: submission-diversity [task.toml]: Milestone tasks are preferred for new submissions (non-milestone not blocked)
INFO: test.sh [tests/test.sh]: Trailing exit after reward block is unnecessary (not an error)

Summary: 1 error(s), 1 warning(s), 2 info
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All runs failed |
| terminus-claude-opus-4-8 | 60.0% (3/5) | |
| oracle | 100.0% (3/3) | |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task folder `mp9/`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise, natural, points to spec.md |
| 2 Environment | ☑ | Digest-pinned Go base; tmux/asciinema; pip pinned; **allow_internet blocker** |
| 3 Oracle | ☑ | Real implementation in solve.sh; 100% per report |
| 4 Verifiers | ☑ | 21 tests, docstrings, reward path; one brittle exact-list test |
| 5 Metadata | ☑ | **allow_internet** and **category** issues |
| 6 Rubric | ☑ | 36/40 positives; 7 negatives; `# Rubric 1` optional on non-milestone — OK |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency PASS; consistent replace-map failure pattern |
| 8 Novelty & fairness | ☑ | Multi-step Go tooling; live-proxy design unfair under offline policy |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Go MVS task — the scaffold is clean, the verifier covers escaping, semver ordering, go.mod parsing, MVS graph traversal, and replace semantics well, and the gofmt/go-vet checks match what the instructions ask for. The rubric looks good too. Two things to fix before we can accept: the task still requires live calls to `proxy.golang.org` (`allow_internet` is true and nothing is bundled), so please switch to frozen/bundled proxy fixtures and set `allow_internet = false`. Also change `test_quote_prerelease_ordering` to use the ordering-plus-known-subset pattern you already use for sampler instead of pinning the full exact version list. While you're at it, `software-engineering` or `build-and-dependency-management` fits the work better than `data-processing`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Uses Internet | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2 |
| Metadata Issues | yes | 3 |
| Environment | yes | 1 |
| Instruction Styling | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
