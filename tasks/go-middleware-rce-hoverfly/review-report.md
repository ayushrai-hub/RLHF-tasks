# Terminus Review Report: go-middleware-rce-hoverfly

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 100% 3/3; local Docker unavailable) |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** Rubric

**Decision (concise):** Strong Go security-audit task: digest-pinned offline environment, exploit/fuzz verifier coverage, anti-shortcut checks, and clear `security_notes.md` requirement. ChatGPT’s rubric cap finding is confirmed (+47 > 40). Automated audit failures for #14 pip pinning, #20 verifier deps, #31 docstrings, and #41 stray files are false positives on manual re-audit. Non-milestone rubric uses optional single `# Rubric 1` header only — not wrongly formatted as multi-milestone.

**Insights (concise):**

- Platform rubric positive total **47** (12 +lines: +2+5+5+3+5+5+5+5+3+3+3+3); cap is 40 — sole High blocker.
- 4 distinct negative rubric criteria (-5, -3, -5, -5); format, scores, and no `/tests/` refs all pass.
- `number_of_milestones = 0`; rubric has `# Rubric 1` only (allowed per non-milestone rules; no `# Rubric 2+`).
- `environment/requirements.txt` pins pytest==8.4.1 with hashes; Dockerfile bakes venv at build time; `test.sh` does not install packages.
- 26 `test_*` functions lack docstrings but names are fully descriptive (`test_fuzz_token_normalization_rejected`, etc.) — satisfies #31 via names.
- Worst-model 60% (GPT-5.5); Claude Opus 4.8 100%; tier medium — not too easy (#54 passes). `task.toml` `difficulty = "hard"` vs platform MEDIUM is informational only.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric positive total 47 exceeds 40 cap for non-milestone task | `entire-report.txt:284-296` — sum of 12 `+N` lines = 47 | Trim ≥7 positive points (e.g. reduce several +5 security-fix items to +4 or +3 while keeping relative priorities) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Rubric positive total 47 > 40 cap — Needs Revision (ChatGPT High) | **Agree** | `entire-report.txt:285-296`; verified sum = 47 via `scripts/rubric_points.py` logic |
| 2 | Task itself strong: clear security domains, exploit/fuzz coverage, tests/solution excluded, security_notes explicit (ChatGPT Medium none) | **Agree** | `instruction.md:7-23`; `environment/Dockerfile:23-27`; `.dockerignore:10-11`; `tests/test_outputs.py:90-132` |
| 3 | Optional: align `task.toml` difficulty hard → medium (ChatGPT Low) | **Agree (Low only)** | `task.toml:14`; `entire-report.txt:1` MEDIUM; per `prompt.md` never blocks |
| 4 | Dockerfile digest-pinned Go base appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:1a6d4452…` |
| 5 | Harbor REVIEW REPORT: non-canonical base image warning | **Disagree as blocker** | Go toolchain required for `build_cli` fixture (`tests/test_outputs.py:17-29`); digest-pinned; justified |
| 6 | Harbor TEST QUALITY: ACCEPT / robust | **Agree** | `entire-report.txt:251-280`; 26 tests with fuzz/variant coverage verified |
| 7 | LLMaJ behavior_in_task_description / behavior_in_tests PASS | **Agree** | `entire-report.txt:84-85`; cross-checked instruction vs `tests/test_outputs.py` |
| 8 | Instruction sufficiency FAIL then systematic issues none (export) | **Partially agree** | Agents missed `security_notes.md` path (`entire-report.txt:52-53`); requirement explicit at `instruction.md:23` — agent execution, not spec gap |
| 9 | Audit #14 unpinned pip | **Disagree** | `environment/requirements.txt:6` `pytest==8.4.1 --hash=…`; `Dockerfile:19-21` `--require-hashes` |
| 10 | Audit #20 pytest not in Dockerfile | **Disagree** | `Dockerfile:19-21` installs requirements into `/opt/verifier-venv`; `tests/test.sh:11` runs venv pytest only |
| 11 | Audit #31 26 tests missing docstrings | **Disagree as blocker** | Checkbox #31: "informative names **or** docstrings"; all 26 names are descriptive (`test_exploit_binary_rejected`, etc.) |
| 12 | Review script #1 instruction too long | **Disagree as blocker** | 2 prose paragraphs + requirement bullets (`instruction.md:1-23`); standard security-task pattern; LLMaJ concise checks pass |
| 13 | Review script #41 stray `audit-report.md` | **Disagree as task defect** | File created by local `./scripts/terminus audit`; not author submission content |
| 14 | Non-milestone task in milestone rubric format (user concern) | **Disagree** | `task.toml:16` `number_of_milestones = 0`; rubric has single `# Rubric 1` only — allowed per `docs/guidelines/rubrics.md:66` ("`# Rubric 1` optional; no `# Rubric 2+`") |
| 15 | Review script #38 rubric references instruction.md | **Disagree** | `entire-report.txt:297` says "prohibited by the instructions" — no `instruction.md` path reference |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 2 prose paragraphs + enumerated requirements; ~414 words appropriate for 4-domain security audit | `instruction.md:1-23` |
| 2 | CHECK | Natural prompt tone | Engineer problem statement, not synthetic walkthrough | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | `## Requirements` + bullets; not design-doc tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States WHAT to fix; no patch recipe | `instruction.md` |
| 5 | CHECK | No hints/strategies | Diagnostic vocabulary is specified requirement, not solve hints | `instruction.md:9-14` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Four vulnerability domains, paths, vocabulary, security_notes schema | `instruction.md:7-23` |
| 8 | CHECK | Interesting | Realistic Go middleware RCE/ACL audit | task content |
| 9 | UNCHECK | Unique | Corpus dedup not verifiable from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/environment/security_notes.md` | `instruction.md:23` |
| 11 | CHECK | Task name not in instruction | Clean | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local testdata only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with == | All packages `==` with hashes in requirements.txt | `environment/requirements.txt:1-9`; `Dockerfile:21` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY only env subtree | `environment/Dockerfile:23-27` |
| 17 | CHECK | No ground truth in env | Vulnerable code is task input, not oracle answers | `environment/src/` |
| 18 | CHECK | No privileged Docker | Standard RUN/COPY | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile venv; test.sh runs venv pytest only | `Dockerfile:19-21`; `tests/test.sh:11` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle no network | Patches + `go build` only | `solution/solve.sh:5-37` |
| 23 | CHECK | Oracle derives answer | Applies patches, copies notes, rebuilds | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail | `tests/test.sh:9-16` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary reward | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All graded behaviors map to instruction reqs | `instruction.md:7-23`; LLMaJ PASS `entire-report.txt:84` |
| 28 | CHECK | Tests check correctness | CLI exit codes + stderr domain keywords + fuzz | `tests/test_outputs.py:44-58,90-112` |
| 29 | CHECK | Behavior not implementation grep | Primary checks run CLI; source reads only for anti-cheat (`cmd/` unchanged, no hardcoded exploit IDs) | `tests/test_outputs.py:135-151` |
| 30 | CHECK | No brittle string matching | Domain keywords from instruction vocabulary; flexible `any(kw in err_lower)` | `instruction.md:11-14`; `tests/test_outputs.py:55-57` |
| 31 | CHECK | Informative test names or docstrings | 26 descriptive `test_*` names | `tests/test_outputs.py:82-518` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:297-300` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines compliant | `entire-report.txt:285-300` |
| 34 | CHECK | Agent …, ±N format | 16 Agent lines | `entire-report.txt:285-300` |
| 35 | UNCHECK | Rubric detailed; positive cap | **47 positive pts > 40 cap** | `entire-report.txt:285-296` |
| 36 | CHECK | Positive language in rubric | Bad behavior on negative lines | `entire-report.txt:297-300` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:285-300` |
| 38 | CHECK | Rubric no instruction.md refs | No file-path reference to instruction.md | `entire-report.txt:297` |
| 39 | CHECK | Rubric no oracle/NOP mentions | Clean | `entire-report.txt:285-300` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray author files (audit-report.md is reviewer-generated) | task tree |
| 42 | CHECK | author_name/email present | Set in task.toml | `task.toml:10-11` |
| 43 | CHECK | Other metadata fields present | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | security, go, command-injection | `task.toml:12-18` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; platform MEDIUM — informational only | `task.toml:14`; `entire-report.txt:1` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:16` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:16` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:16` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:16` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile`; `.dockerignore:11` |
| 51 | CHECK | Solution not accessible | .dockerignore excludes solution/ | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially cheat inputs | Agent edits src/ by design; testdata read-only fixtures; fuzz prevents hardcoding | `tests/test_outputs.py:147-151,314+` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:6-7` |
| 55 | CHECK | Not too hard/unfair | Clear spec; agents reach 25/26 tests; failures are execution not spec | `entire-report.txt:45-72` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 35, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Fix under `src/` only; do not modify `cmd/` | `test_no_shortcut_modifications` | covered | `instruction.md:7`; `tests/test_outputs.py:135-144` |
| Rebuild binaries after fixes | `build_cli` fixture (session) | covered | `instruction.md:7`; `tests/test_outputs.py:17-29` |
| `testdata/valid/` exit 0 | `test_valid_configs_all_pass` | covered | `instruction.md:9`; `tests/test_outputs.py:82-87` |
| `testdata/exploits/` rejected with domain stderr | `test_exploit_*_rejected` | covered | `instruction.md:9-14`; `tests/test_outputs.py:90-112` |
| General fixes, not fixture hardcodes | `test_no_hardcoded_exploit_keywords`, fuzz tests | covered | `instruction.md:16`; `tests/test_outputs.py:147-151,314+` |
| Exact token match; API enabled guard | `test_hidden_token_variants_*`, `test_api_disabled_blocks_*` | covered | `instruction.md:20`; `tests/test_outputs.py` |
| Remote path confinement via normalization | `test_remote_path_traversal_rejected`, hidden variants | covered | `instruction.md:21`; `tests/test_outputs.py:222-251` |
| `security_notes.md` at `/app/environment/` referencing ≥3 files | `test_security_notes_exists` | covered | `instruction.md:23`; `tests/test_outputs.py:115-132` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27, spec alignment |
| `task.toml` | #45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.txt` | #14 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | #35 rubric, agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate go-middleware-rce-hoverfly/
Summary: 0 error(s), 27 warning(s), 3 info
```

Warnings are docstring-related (informative names satisfy #31) and non-milestone preference info — not blockers.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | MEDIUM (`entire-report.txt:1`) |
| Tier match (#45) | informational only — never blocks |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches export; regular layout; Go security audit |
| 1 Instruction | ☑ | Clear 4-domain spec; absolute paths; no canary |
| 2 Environment | ☑ | Digest-pinned Go image; tmux+asciinema; deps baked; allow_internet=false |
| 3 Oracle | ☑ | Patch-based solve; platform 100%; local Docker unavailable |
| 4 Verifiers | ☑ | 26 behavioral tests + fuzz; reward block canonical; no runtime installs |
| 5 Metadata | ☑ | category=security; number_of_milestones=0 |
| 6 Rubric | ☑ | **Blocker:** 47 positive pts; format otherwise good; single `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | LLMaJ PASS; worst-model 60%; security_notes miss is agent execution |
| 8 Novelty & fairness | ☑ | Multi-file security reasoning; anti-cheat closed |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Go security task — the vulnerable middleware codebase, exploit fixtures, fuzz/variant tests, and anti-shortcut guards are all well done, and the offline Dockerfile setup looks correct. The only thing blocking acceptance is the platform rubric: the positive criteria add up to 47 points and need to come down to 40 or below. I'd trim at least 7 points — for example, drop a few of the +5 security-fix lines to +3 or +4 while keeping the most important fixes at the top of the scale.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
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
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
