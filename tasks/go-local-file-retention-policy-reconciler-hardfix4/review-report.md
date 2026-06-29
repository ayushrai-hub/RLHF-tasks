# Terminus Review Report: `go-local-file-retention-policy-reconciler-hardfix4`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | pass (local Docker: 9/9 tests, reward=1) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** none

**Decision (concise):** Accept the task artifacts. The Go retention reconciler has a complete contract in `/app/docs/local-retention-contract.md`, nine behavioral tests with dynamic anti-hardcoding scenarios, a digest-pinned canonical `golang:1.24-bookworm` base, oracle pass, and NOP fail (0/9). Manual audit found **no real blockers** in the task folder. The supplied `entire-report.txt` is an **iscsi-multipath-path-loss-recovery / pathfb-sweep** export (wrong task) — do not use its agent stats or rubric for this submission; portal rubric (#32–39) and difficulty (#45, #54) stay unchecked until a matching export is available.

**Insights (concise):**

- `entire-report.txt` references `path_failback_report.json`, `test_pf01_*`, `caplog/ledger.go`, and pathfb-sweep — none appear in this task (`grep` across task folder; report lines 66–123, 326–341).
- Oracle verified locally: `solution/solve.sh` → 9/9 pytest pass, `REWARD=1`; starter stub alone → 9/9 fail, `REWARD=0`.
- `golang:1.24-bookworm@sha256:1a6d4452…` is canonical per `scripts/validate_task.py:67`; ChatGPT base-image claim **Agree**.
- Platform rubric **shape** in export is flat `Agent …, ±N` (no `# Rubric 2+`) — correct **format** for `number_of_milestones = 0`, but **content** is for the wrong task.
- ChatGPT Accept on contract/tests/oracle/Dockerfile **Agree**; optional `solution/reconcile.go` cleanup and `difficulty = "hard"` vs ~40% worst-model are not blockers.
- All nine tests have docstrings; bundled + seven dynamic tests cover duplicate tie-breaks, exception boundaries, malformed rows, class aliases, cleanup blocks, retention groups, dependency cycles, and byte budgets.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

*Note:* If the **platform rubric** currently matches `entire-report.txt:326–341` (pathfb-sweep patch lines), replace it with retention-reconciler trace criteria before portal rubric sign-off. That is a platform-side rubric fix, not a defect in the task zip reviewed here.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT High: none | **Agree** | Manual spec↔test audit; no untested enforced semantics found |
| 2 | ChatGPT Medium: `solution/reconcile.go` exposure | **Disagree** | `environment/.dockerignore:15` excludes `solution/`; `environment/Dockerfile` copies only `app/*`; no runtime exposure |
| 3 | ChatGPT Low: remove redundant `solution/reconcile.go` | **Partially agree** | Duplicate of oracle embedded in `solution/solve.sh`; optional cleanup only |
| 4 | ChatGPT Low: `difficulty = "hard"` vs Medium ~40% worst model | **Partially agree** | `task.toml:6` hard; not a revision blocker per review policy |
| 5 | ChatGPT: digest-pinned `golang:1.24-bookworm` canonical | **Agree** | `environment/Dockerfile:1`; `scripts/validate_task.py:67` |
| 6 | ChatGPT Decision: Accept | **Agree** | Artifacts pass manual audit |
| 7 | `entire-report.txt` agent stats (Claude 100%, GPT 40%, oracle 100%) | **Disagree (wrong task)** | Report tests are `test_pf01_six_scenario_envelope` etc. (`entire-report.txt:48–63`); this task has `test_bundled_fixture_*` / `test_dynamic_*` (`tests/test_outputs.py`) |
| 8 | `entire-report.txt` LLMaJ quality checks (path_failback_report.json) | **Disagree (wrong task)** | `entire-report.txt:122–123` references path failback output; this task outputs `retention_report.json` / `cleanup_plan.json` / `warnings.json` (`instruction.md:1–3`) |
| 9 | `entire-report.txt` Harbor CRITICAL: non-canonical Ubuntu base | **Disagree (wrong task)** | Report cites `ubuntu:24.04` (`entire-report.txt:170`); this task uses `golang:1.24-bookworm` (`environment/Dockerfile:1`) |
| 10 | `entire-report.txt` instruction sufficiency FAIL (`flush_bump` / `registration_order`) | **Disagree (wrong task)** | Gap describes `epoch/loader.go` (`entire-report.txt:75–94`); not in this task |
| 11 | `entire-report.txt` platform rubric (caplog, segplay, pathfb-sweep) | **Disagree (wrong task)** | `entire-report.txt:326–341` references `/app/environment/caplog/ledger.go`, `pathfb-sweep`; this task is `local-retention-reconciler` under `/app/src/reconcile.go` |
| 12 | User concern: non-milestone task in milestone rubric format | **Disagree (no format issue)** | Export rubric is flat `Agent …, ±N` with no `# Rubric 2+` headers (`entire-report.txt:326–341`); correct shape per `docs/guidelines/rubrics.md:64` — but content belongs to a different task |
| 13 | Automated `terminus review`: #54 too easy (100% worst) | **Disagree** | Misread Claude 100% from wrong-task export; no verified stats for this task; ChatGPT cites 40% GPT-5.5 (would pass #54 if confirmed) |
| 14 | Automated `terminus review`: #36 rubric negative phrasing | **N/A (wrong rubric)** | Rubric lines in export are for pathfb-sweep, not this task |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two short paragraphs | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer repair request tone | `instruction.md:1–3` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, backticks only for paths/commands | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal + contract pointer, not patch walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (regenerate documented outputs), not HOW to implement | `instruction.md:1–3` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | CLI command, paths, output files, contract reference | `instruction.md:1–3` |
| 8 | CHECK | Instruction is interesting | Real retention-policy reconciliation scenario | — |
| 9 | CHECK | Instruction is unique | Distinct local file retention reconciler with wave budgets / group holds | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY app files only | `environment/Dockerfile:13–19` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | No pip install; apt `python3-pytest` only | `environment/Dockerfile:9` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | Individual COPY from `app/` | `environment/Dockerfile:13–19` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Starter stub writes empty JSON only | `environment/app/src/reconcile.go:33–43` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | `python3-pytest` in image; test.sh runs pytest only | `environment/Dockerfile:9`, `tests/test.sh:14` |
| 21 | CHECK | Oracle passes consistently | Local Docker oracle 9/9 pass | Docker run 2026-06-29 |
| 22 | CHECK | Oracle does not require internet or downloading packages | Embeds Go oracle + `go run`; no network | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full reconciler algorithm in solve.sh heredoc | `solution/solve.sh:5–1168` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Writes 0 on start; 0/1 after pytest | `tests/test.sh:4–20` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` | `tests/test.sh:5,17–19` |
| 27 | CHECK | All tests aligned with instructions | Assertions trace to `local-retention-contract.md` rules cited in instruction | `instruction.md:3`, contract + `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Field-level status, warnings, waves, summaries | `tests/test_outputs.py:47–898` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs CLI, compares JSON outputs | `tests/test_outputs.py:11–27` |
| 30 | CHECK | No brittle exact string matching | Exact strings match contract-mandated detail templates; dynamic tmp_path scenarios | `local-retention-contract.md:228–238`, `tests/test_outputs.py:207–898` |
| 31 | CHECK | Tests have informative names or docstrings | All 9 tests named `test_*` with docstrings | `tests/test_outputs.py:47–815` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Export rubric is for pathfb-sweep, not this task | `entire-report.txt:326–341` |
| 33 | UNCHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | Unverified — wrong-task rubric in export | `entire-report.txt:326–341` |
| 34 | UNCHECK | Each rubric criterion one line starting with Agent | Unverified — wrong-task rubric in export | `entire-report.txt:326–341` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | Unverified — need retention-specific platform rubric | — |
| 36 | UNCHECK | Rubric criteria use positive language | Unverified — wrong-task rubric in export | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ | Unverified — wrong-task rubric in export | — |
| 38 | UNCHECK | Rubric does not reference metadata or instruction.md | Unverified — wrong-task rubric in export | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | Unverified — wrong-task rubric in export | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go file-retention policy audit; system-administration | `task.toml:7–12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; no verified stats for this task in export | `task.toml:6`; export mismatch |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | `solution/` in `.dockerignore`; not COPY'd | `environment/.dockerignore:15` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Seven dynamic tmp_path scenarios + bundled cross-checks | `tests/test_outputs.py:207–898` |
| 53 | CHECK | Git repos pinned (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | UNCHECK | Task is not too easy (>80% worst model) | No verified agent stats for this task in export; ChatGPT cites 40% (not confirmed here) | export mismatch |
| 55 | CHECK | Task is not too hard or unfair | Full contract documents all tested semantics | `environment/app/docs/local-retention-contract.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 54 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Regenerate retention_report, cleanup_plan, warnings | `test_bundled_fixture_reconciles_*` | covered | `tests/test_outputs.py:47–137` |
| Warning codes, severities, detail templates, sort order | `test_bundled_warnings_are_documented_*` | covered | `tests/test_outputs.py:140–204` |
| Duplicate tie-break + stale `.json` cleanup on rerun | `test_dynamic_duplicate_tie_breakers_*` | covered | `tests/test_outputs.py:207–256` |
| Exception window start inclusive / end exclusive + allow_mode | `test_dynamic_exception_windows_*` | covered | `tests/test_outputs.py:259–344` |
| Malformed JSONL + invalid rows preserve valid peers | `test_dynamic_malformed_rows_*` | covered | `tests/test_outputs.py:346–422` |
| Class aliases + cleanup blocks + cross-output consistency | `test_dynamic_class_aliases_cleanup_blocks_*` | covered | `tests/test_outputs.py:426–533` |
| Retention-group holds after cleanup blocks | `test_dynamic_retention_group_holds_*` | covered | `tests/test_outputs.py:537–669` |
| Cleanup dependency cycles + per-action wave capacity | `test_dynamic_cleanup_dependency_cycles_*` | covered | `tests/test_outputs.py:673–811` |
| Byte budgets with dependency readiness | `test_dynamic_cleanup_byte_budgets_*` | covered | `tests/test_outputs.py:814–898` |
| Manifest discovery, sorting, permission checks (bundled) | bundled tests | covered | `tests/test_outputs.py:47–137`, contract §Manifest |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, #27, spec alignment |
| `environment/Dockerfile` | #13–20, #50, canonical base |
| `environment/.dockerignore` | #51 |
| `environment/app/docs/local-retention-contract.md` | #27, #55, spec alignment |
| `environment/app/src/reconcile.go` | #17 starter stub |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, spec alignment |
| `solution/solve.sh` | #21–23, oracle |
| `task.toml` | #43–45, milestones N/A |
| `entire-report.txt` | Wrong-task adjudication (#32–39, #45, #54) |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate go-local-file-retention-policy-reconciler-hardfix4/
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Oracle (local Docker)

```
solution/solve.sh → pytest 9 passed → REWARD=1
starter stub only → pytest 9 failed → REWARD=0
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | unverified | ChatGPT cites 40% (2/5) — not in valid export for this task |
| terminus-claude-opus-4-8 | unverified | Export shows 100% but belongs to pathfb-sweep task |
| oracle | 100% (local) | 9/9 tests pass after solve.sh |
| nop | 0% (local) | 0/9 tests pass on starter stub |

| Metric | Value |
|--------|-------|
| Worst-model rate | unverified (ChatGPT: 40%) |
| Observed tier | unverified (ChatGPT: medium) |
| Declared difficulty | hard (`task.toml:6`) |
| Tier match (#45) | unverified — not a revision blocker alone |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `number_of_milestones = 0`; export is wrong task |
| 1 Instruction | ☑ | Concise; delegates to contract; absolute paths |
| 2 Environment | ☑ | Canonical golang base; tmux+asciinema; no solution/tests in image |
| 3 Oracle | ☑ | Passes 9/9 locally; algorithmic, not hardcoded JSON |
| 4 Verifiers | ☑ | reward.txt; no runtime installs; behavior tests + docstrings |
| 5 Metadata | ☑ | Complete; Go/system-administration tags fit |
| 6 Rubric | ☐ | Export rubric is pathfb-sweep content — verify retention rubric on platform |
| 7 LLMaJ & agent evidence | ☐ | Export inadmissible for this task |
| 8 Novelty & fairness | ☑ | Multi-rule reconciler; dynamic scenarios; contract complete |
| 9 Long context | — | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one. The retention contract is thorough, the verifier exercises real policy behavior end to end (duplicates, exception windows, group holds, dependency waves, byte budgets), and the dynamic scenarios make hardcoding impractical. Oracle passes cleanly on a local run and the starter stub correctly fails everything. The Go base image is digest-pinned and canonical. I didn't find any spec gaps or cheating paths in the task itself. Before sign-off, please confirm the platform rubric is retention-reconciler-specific (flat `Agent …, ±N` format is fine — just make sure it references this CLI/contract, not pathfb-sweep). The attached export looked like a different task, so I couldn't tick rubric or difficulty boxes from it.

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
| Rubric | no (task zip) | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
