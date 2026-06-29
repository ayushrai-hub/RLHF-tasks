# Terminus Review Report: go-dns-cname-chain-risk-auditor-fixed-v4

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | Medium |
| **Validation** | warn |
| **Oracle** | pass (platform report 3/3; local run blocked — Docker daemon unavailable) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** No High or Medium blockers. Instruction, contract, tests, oracle behavior, anti-cheat fixtures, and platform rubric align. True worst-model pass rate is 40% (Claude Opus 4.8), not >80%. Declared `difficulty = hard` is informational only (#45 UNCHECK). Two optional test-coverage polish gaps (chain-array sort assertion, `retired_at` date negative) are Low severity and do not block acceptance.

**Insights (concise):**

- Non-milestone rubric is correctly formatted as a flat `Agent …, ±N` list (no `# Rubric 2+` headers); 23 positive points, 4 distinct negatives.
- `instruction.md` and contract both name `cname_chain_report.json` / `warnings.json`; the LLMaJ filename-mismatch claim is not supported by artifacts.
- Automated `./scripts/terminus review` incorrectly flagged #54 using `max()` agent rate (100% GPT-5.5); per `difficulty.md` worst model is `min()` = 40%.
- Chain sort order is specified in contract (`cname-chain-audit-contract.md:163`) but only indirectly covered by tests (findings/warnings sort asserted; chains keyed via dict).
- Go base image is digest-pinned and justified; pytest via apt is advisory only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High/Medium blockers; Accept | Agree | Full artifact audit; no High/Medium gaps found |
| 2 | ChatGPT: Output filename concern (cname-chains.json vs cname_chain_report.json) not a blocker | Agree | `instruction.md:1` defers to contract; `cname-chain-audit-contract.md:87-88` names `cname_chain_report.json`, `warnings.json`; `test_outputs.py:22-23` reads same names; no `cname-chains.json` in task tree |
| 3 | ChatGPT: Dockerfile digest-pinned; non-canonical Go base justified | Agree | `environment/Dockerfile:1` `@sha256:1a6d4452…`; Go task with no canonical alternative listed |
| 4 | ChatGPT: Chain sort / retired_at negative cases are polish only | Agree | `cname-chain-audit-contract.md:163-167`; `test_outputs.py:32-33,93-96` — findings/warnings sort asserted, chains via `by_chain()` dict; no `retired_at > as_of` fixture |
| 5 | ChatGPT: `codebase_size = minimal` could be `small` | Agree (Low) | `task.toml:10`; suggestion only, not a blocker |
| 6 | entire-report: Instruction Sufficiency FAIL — output filename mismatch | Disagree | Trial narrative only; actual `instruction.md` + contract + tests aligned (see row 2) |
| 7 | entire-report: Instruction Sufficiency FAIL — Go not in instruction.md | Partially agree (Low) | `task.toml:11` `languages = ["go"]`; env has `app/cmd/auditor/main.go`; not a spec/test blocker |
| 8 | entire-report: Agent failures from terminal/heredoc instability | Agree (context) | `entire-report.txt:56-60`; fairness (#55) still passes — failures are agent/env execution, not missing spec |
| 9 | entire-report LLMaJ: all `behavior_in_*` pass | Agree | Cross-checked instruction ↔ contract ↔ tests; aligned |
| 10 | entire-report REVIEW REPORT: unpinned pytest via apt | Agree (Low) | `environment/Dockerfile:11` `python3-pytest`; apt exempt per quality-guidelines; advisory warning |
| 11 | entire-report REVIEW REPORT: non-canonical base image | Agree (Low) | Digest-pinned; Go requirement justifies choice |
| 12 | entire-report TEST QUALITY: chain sort only indirect | Agree | `test_outputs.py:32-33`; Low coverage gap, not Accept blocker |
| 13 | entire-report TEST QUALITY: no retired_at > as_of negative | Agree | `cname-chain-audit-contract.md:31`; Low coverage gap |
| 14 | entire-report: Difficulty MEDIUM, Claude 40%, GPT-5.5 100% | Agree | `entire-report.txt:20-22`; true worst = 40% |
| 15 | Automated review: #54 fail (100% worst model) | Disagree | Script `worst_model_rate()` uses `max()`; correct worst per `difficulty.md:14` is Claude 40% |
| 16 | Automated review: #31 fail (missing docstrings) | Disagree | All 10 `test_*` functions have docstrings; validator WARNING is module-level only (`validate_task.py:548-554`) |
| 17 | User: non-milestone task in milestone rubric format | Disagree | Platform rubric (`entire-report.txt:342-352`) is flat `Agent …, ±N` with no `# Rubric 2+` headers — correct per `docs/guidelines/rubrics.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 2 short paragraphs, ~89 words | `instruction.md:1-5` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem statement + contract pointer; no spec tables in instruction | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose only | `instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Defers normative rules to contract doc (WHAT) | `instruction.md:3-5` |
| 6 | CHECK | No design doc style tables in instruction | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | CLI command, paths, contract reference, deterministic outputs | `instruction.md:1-5` |
| 8 | CHECK | Instruction is interesting | Realistic DNS/CNAME chain-risk auditing | task domain |
| 9 | UNCHECK | Instruction is unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md:1,3` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder/task name string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | No pip install; apt packages only | `environment/Dockerfile:11` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context outside environment/ | COPY limited to `app/` subtree | `environment/Dockerfile:13-18` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stub emits empty chains; contract is public spec | `environment/app/cmd/auditor/main.go:88-90` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | task root |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:11`, `tests/test.sh:14` |
| 21 | CHECK | Oracle passes consistently | Platform: oracle 100% (3/3) | `entire-report.txt:26` |
| 22 | CHECK | Oracle does not require internet | solve.sh writes local Go; no network fetch | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full parser/chain resolver written to main.go | `solution/solve.sh:3-533` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Writes 0 upfront; 1/0 after pytest | `tests/test.sh:5,17-20` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 only | `tests/test.sh:17-20` |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to contract rules | §5 table |
| 28 | CHECK | Tests check correctness, not just format | Chain targets, findings, suppression, dynamic fixtures | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Invokes public CLI only | `tests/test_outputs.py:10-24` |
| 30 | CHECK | No brittle exact matching beyond contract | Long strings match mandated detail formats | `cname-chain-audit-contract.md:151-159` |
| 31 | CHECK | Tests have informative names or docstrings | All 10 `test_*` have docstrings | `tests/test_outputs.py:36-337` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negatives | `entire-report.txt:349-352` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use ±1,2,3,5 | `entire-report.txt:342-352` |
| 34 | CHECK | Each rubric criterion one Agent line with score | 11 valid Agent lines | `entire-report.txt:342-352` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific DNS/CNAME behaviors | `entire-report.txt:342-352` |
| 36 | CHECK | Rubric uses positive language for negatives | e.g. "Agent hardcodes…", not "does not" | `entire-report.txt:349-352` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | `entire-report.txt:342-352` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:342-352` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP lines | `entire-report.txt:342-352` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both `anonymous` | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, timeouts, environment | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go DNS/sysadmin task | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; true worst-model 40% → medium tier; not defensible as hard per `difficulty.md` — informational, not revision blocker | `task.toml:6`, `entire-report.txt:20-22` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore:16` excludes tests/; no COPY tests | `environment/.dockerignore`, `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | solution/ in .dockerignore | `environment/.dockerignore:15` |
| 52 | CHECK | Agent cannot trivially cheat via input mutation | 5 dynamic fixture tests with tmp_path inputs | `tests/test_outputs.py:151-344` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | True worst model Claude 40% ≤ 80% | `entire-report.txt:21` |
| 55 | CHECK | Task is not too hard or unfair | Agent failures are implementation/timeout, not missing spec | `entire-report.txt:46-95` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| CLI flags and output dir `/app/out` | all via `run_cli` | covered | `instruction.md:1`, `test_outputs.py:10-24` |
| Output files `cname_chain_report.json`, `warnings.json` | all | covered | `cname-chain-audit-contract.md:87-88`, `test_outputs.py:22-23` |
| Stale output cleanup on rerun | `test_rerun_removes_stale_outputs_and_is_byte_stable` | covered | `test_outputs.py:129-143` |
| Report schema and summary counts | `test_bundled_report_summarizes_chains_findings_warnings_and_schema` | covered | `test_outputs.py:36-70` |
| Duplicate tiebreaker priority/path/line | `test_duplicate_tiebreaker…`, `test_dynamic_duplicate_source_line…` | covered | `test_outputs.py:73-96,229-261` |
| Malformed JSON/CNAME preserve valid peers | `test_malformed_rows…`, dynamic tests | covered | `test_outputs.py:99-126,151-187` |
| Loop detection and suppression | `test_loop_suppresses…`, dynamic loop tests | covered | `test_outputs.py:264-276,168-187` |
| Max hops stopping | `test_dynamic_max_hops_stops_before_terminal_resolution` | covered | `test_outputs.py:190-226` |
| Hidden path exclusion | `test_dynamic_hidden_zone_paths_are_excluded_without_warnings` | covered | `test_outputs.py:279-312` |
| Service alias precedence | `test_dynamic_service_aliases_take_precedence_over_catalog_domains` | covered | `test_outputs.py:315-344` |
| Stale service (retired status/date) | bundled + dynamic stale assertions | covered | `test_outputs.py:68,186` |
| Ownership gaps (blank owner, unknown terminal) | bundled + dynamic | covered | `test_outputs.py:69-70,220-225` |
| Findings sort order | `test_duplicate_tiebreaker…` | covered | `test_outputs.py:95-96` |
| Warnings sort order | `test_duplicate_tiebreaker…` | covered | `test_outputs.py:93-94` |
| Chains array sort order | byte stability only (indirect) | gap (Low) | `cname-chain-audit-contract.md:163`, `test_outputs.py:32-33` |
| `retired_at` after `as_of` → not stale | none | gap (Low) | `cname-chain-audit-contract.md:31` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, claims 2/6 |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/docs/cname-chain-audit-contract.md` | #27, §5, claims 2/12/13 |
| `environment/app/cmd/auditor/main.go` | #17 |
| `solution/solve.sh` | #21-23 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `entire-report.txt` | #21, #45, #54, §3, §7, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate go-dns-cname-chain-risk-auditor-fixed-v4/
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: informative_test_docstrings — module-level docstring missing (all test functions documented)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | 3 timeouts; true worst model |
| oracle | 100.0% (3/3) | Platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Go DNS task; folder matches report |
| 1 Instruction | ☑ | Concise; contract-backed; absolute paths |
| 2 Environment | ☑ | Digest-pinned Go base; tmux/asciinema; no solution/tests in image |
| 3 Oracle | ☑ | Derives via full Go implementation; platform 3/3 pass |
| 4 Verifiers | ☑ | 10 behavior tests; dynamic anti-cheat; canonical reward block |
| 5 Metadata | ☑ | Complete; `number_of_milestones = 0` |
| 6 Rubric | ☑ | Flat non-milestone format; 23 pos / 4 neg; compliant |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated; filename mismatch claim rejected |
| 8 Novelty & fairness | ☑ | Multi-rule graph task; no cheating path found |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The contract doc is thorough, the verifier suite mixes bundled and dynamic fixtures well, and the environment is set up cleanly with a digest-pinned Go image and deps baked in. Oracle behavior and test alignment look solid for the main CNAME chain rules — loops, duplicates, suppression, aliases, and stale-service detection are all exercised end to end. I’d optionally add an explicit chains-array sort assertion and a `retired_at > as_of` negative fixture later, but those are polish items. Consider updating `difficulty` in task.toml to `medium` to match the 40% Claude pass rate, though that’s metadata calibration rather than a functional issue.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no (Low gaps only) | — |
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
