# Terminus Review Report: `go-cookie-scope-auditor`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per submission report; local Docker unavailable) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Rubric, Instruction Styling

**Decision (concise):** Task artifacts are strong — canonical digest-pinned Go base, offline verifier deps, reference-based tests, and spec↔test alignment are solid. ChatGPT’s Accept call misses one mandatory blocker: the platform rubric sums to **49 positive points** (>40 cap for non-milestone). Instruction length also fails the conciseness rule (~1635 words / 40 prose blocks). Non-milestone `# Rubric 1` header alone is allowed; this is not milestone-format misuse.

**Insights (concise):**

- Platform rubric positive total is **49** (`entire-report.txt` L317–336); `./scripts/terminus rubric-points` confirms FAIL (>40).
- `# Rubric 1` on a non-milestone task is **optional and valid** per `docs/guidelines/rubrics.md` — only `# Rubric 2+` would be wrong.
- Dockerfile pip deps **are** pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); automated #14 is a false positive.
- Base image digest matches canonical `golang:1.24-bookworm` in `docs/guidelines/dockerfile.md:11`.
- All 45 `test_*` functions have docstrings (AST); automated #31 is a false positive.
- Worst-model pass rate 40% (Opus); GPT-5.5 100% — not too easy (#54 passes).
- Agent failures concentrated on one composite duplicate-attribute test; instruction rules cover the behavior (`instruction.md:5,11`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #35 | Platform rubric positive total **49** exceeds non-milestone cap **40** | `entire-report.txt:317–331` (+5+3+3+3+5+3+2+3+3+5+3+2+3+2+2+2=49); `task.toml:14` `number_of_milestones = 0` | Merge or trim positive criteria until sum ≤40 (e.g. combine parsing/normalization lines, drop redundant +2 items) |
| 2 | High | Instruction Styling | #1 | Instruction is ~1635 words across 40 prose blocks; exceeds “1 sentence to 3 paragraphs” | `instruction.md` (40 lines, `wc -w` → 1635); `docs/guidelines/prompt-styling.md:7` | Trim opening context to ≤3 paragraphs; move exhaustive schema detail into shipped normative docs under `/app/` if needed, without splitting tested requirements out of agent-visible spec |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High severity issues | **Disagree** | Rubric +49 > +40 cap (`entire-report.txt:317–331`; `rubrics.md:35`) |
| 2 | ChatGPT: Rubric positive ~49 above ≤40 is Low only | **Disagree** | `rubrics.md:35` and `reviewer-checklist-full.md:85` — **>40 is main blocker (High), not Low** |
| 3 | ChatGPT: Accept — strong verifier, no spec gaps | **Partially agree** | Spec↔tests aligned via Python reference (`tests/test_outputs.py`); rubric cap and instruction length block Accept |
| 4 | ChatGPT: Oracle passes, NOP fails | **Agree** | `entire-report.txt:28–29` oracle 100% (3/3), nop 0% |
| 5 | ChatGPT: Digest-pinned Go base OK | **Agree** | `environment/Dockerfile:1` digest `1a6d4452…` = `docs/guidelines/dockerfile.md:11` |
| 6 | Harbor REVIEW: Non-canonical Docker base | **Disagree** | Same canonical digest as sanctioned list |
| 7 | Harbor REVIEW: Generic directory name cosmetic | **Agree** | Folder is `go-cookie-scope-auditor`; not acceptance-blocking |
| 8 | Harbor TEST QUALITY: ACCEPT — reference impl robust | **Agree** | `tests/test_outputs.py` reference + 45 behavioral tests |
| 9 | Instruction sufficiency: PASS — agent failure is implementation | **Agree** | `entire-report.txt:122–128`; rules at `instruction.md:5,11,9` cover duplicate-attribute pipeline |
| 10 | Automated audit #14: unpinned pip | **Disagree** | `environment/Dockerfile:19–20` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 11 | Automated audit #31: missing test docstrings | **Disagree** | AST: 45/45 `test_*` have docstrings |
| 12 | Automated audit #36: rubric negative phrasing | **Disagree** | Negatives (`hard-codes`, `ignores`) carry `-N` scores; positives use affirmative phrasing (`entire-report.txt:317–331`) |
| 13 | Automated audit #41: stray `audit-report.md` | **Disagree** | Reviewer-generated artifact, not part of submission |
| 14 | Automated audit #27: phantom numeric thresholds | **Disagree** | Literals like `> 5`, `timeout=20` are test harness bounds, not unstated spec (`tests/test_outputs.py:616,990`) |
| 15 | Automated audit #44: wrong category `security` | **Disagree** | Cookie-scope security auditor; `task.toml:7` `category = "security"` fits `docs/task-type-taxonomy.md` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction concise (1–3 paragraphs) | ~1635 words, 40 prose blocks | `instruction.md`; `prompt-styling.md:7` |
| 2 | CHECK | Natural prompt tone | Dense spec assignment, not step-by-step walkthrough | `instruction.md:1–39` |
| 3 | CHECK | No excessive markdown | Plain prose, no ##/tables | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | Requirements only | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | WHAT to build, not HOW | `instruction.md` |
| 6 | CHECK | No design-doc tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Complete JSON schema + cookie rules | `instruction.md:7–39` |
| 8 | CHECK | Interesting | Real cookie-security engineering problem | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify from artifacts alone | — |
| 10 | CHECK | Absolute paths only | `/app/task_file/...` throughout | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No slug/canary | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures only | `environment/` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:19–20` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | `COPY app/` only | `environment/Dockerfile:24` |
| 17 | CHECK | No ground truth in env | Stub `main.go` only | `environment/app/task_file/main.go:18–19` |
| 18 | CHECK | No privileged/docker.sock | Standard RUN apt | `environment/Dockerfile` |
| 19 | CHECK | Compose does not conflict mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest pre-baked | `Dockerfile:17–21`, `tests/test.sh:15–16` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) in submission | `entire-report.txt:29` |
| 22 | CHECK | Oracle no internet | Heredoc Go build only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives implementation | Full Go program written in solve.sh | `solution/solve.sh:4+` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail | `tests/test.sh:12–22` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards 0/1 | `echo 0` / `echo 1` only | `tests/test.sh:18–21` |
| 27 | CHECK | Tests aligned with instructions | Reference implements instruction spec | `tests/test_outputs.py`; `instruction.md` |
| 28 | CHECK | Tests check correctness | Deep equality vs Python reference | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Output comparison, anti-shortcut scan | `test_solution_does_not_use_shortcuts_or_embed_fixtures` |
| 30 | CHECK | No brittle exact-string overreach | Field-level deep equality appropriate | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | 45/45 tests documented | AST verification |
| 32 | CHECK | ≥3 negative rubric penalties | 4 negatives (-5,-3,-3,-5) | `entire-report.txt:333–336` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | All lines valid | `entire-report.txt:317–336` |
| 34 | CHECK | Rubric format `Agent …, ±N` | 20 properly formatted lines | `entire-report.txt:317–336` |
| 35 | UNCHECK | Rubric detailed/precise (≤40 cap) | **49 positive pts > 40** | `entire-report.txt:317–331` |
| 36 | CHECK | Positive phrasing on + criteria | Affirmative +lines; bad-behavior -lines | `entire-report.txt:317–336` |
| 37 | CHECK | No /tests/ references in rubric | None | `entire-report.txt:317–336` |
| 38 | CHECK | No task.toml/instruction refs | None | `entire-report.txt:317–336` |
| 39 | CHECK | No oracle/NOP mentions | None | `entire-report.txt:317–336` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, toml | task tree |
| 41 | CHECK | Clean parent directory | No jobs/README in task folder | task tree |
| 42 | CHECK | author_name/email present | Set in toml | `task.toml:4–5` |
| 43 | CHECK | Other metadata complete | timeouts, tags, languages | `task.toml` |
| 44 | CHECK | Tags/category match content | `security`, `go`, cookie tags fit | `task.toml:7–13` |
| 45 | CHECK | Difficulty field present | `hard` in toml; platform `medium` — informational only | `task.toml:6`, `entire-report.txt:19` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:14` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:14` |
| 49 | UNCHECK | Per-milestone test scope | N/A | `task.toml:14` |
| 50 | CHECK | Tests not baked in image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:4–7` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes solution/ | `environment/.dockerignore:6–7` |
| 52 | CHECK | Agent cannot trivially tamper inputs | `test_public_inputs_are_unchanged` hash check | `tests/test_outputs.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst 40% ≤ 80% | `entire-report.txt:24` |
| 55 | CHECK | Not unfair/too hard | 44/45 agent tests; spec covers failure mode | `entire-report.txt:87–128` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 9, 35, 46, 47, 48, 49 |

### Non-milestone rubric format note

`task.toml:14` sets `number_of_milestones = 0`. The platform rubric uses a single `# Rubric 1` header with a flat 20-line criteria list (`entire-report.txt:316–336`). Per `docs/guidelines/rubrics.md:66`, `# Rubric 1` is **optional** on non-milestone tasks; milestone-format violation would require `# Rubric 2+` blocks. **Not a blocker.**

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Later duplicate attribute wins | `test_duplicate_attribute_last_value_*`, `test_duplicate_final_attributes_and_rejection_priority_composite` | covered | `instruction.md:5`; `test_outputs.py:1618+` |
| Rejection priority ordering | `test_rejection_priority_and_attribute_normalization`, composite duplicate test | covered | `instruction.md:9`; `test_outputs.py` |
| Max-Age deletion / never count accepted | `test_prefix_deletion_default_path_and_samesite_edges`, lifecycle tests | covered | `instruction.md:11`; `test_outputs.py` |
| UTF-8 byte header limit | `test_header_limit_uses_utf8_byte_counts`, `test_zero_budget_blocks_all_eligible_and_tracks_truncation` | covered | `instruction.md:19`; `test_outputs.py` |
| Prefix case sensitivity | `test_case_sensitive_names_and_prefix_near_misses` | covered | `instruction.md:15`; `test_outputs.py` |
| 10 top-level JSON keys + audit sections | `test_public_audit_report_matches_reference`, schema asserts | covered | `instruction.md:23–39`; `test_outputs.py` |
| Fixtures unchanged | `test_public_inputs_are_unchanged` | covered | `instruction.md:1`; `test_outputs.py` |
| Build command documented | `test_builds_with_documented_command` | covered | `instruction.md:1`; `test_outputs.py` |
| Anti-shortcut / no embedded fixtures | `test_solution_does_not_use_shortcuts_or_embed_fixtures` | covered | `tests/test_outputs.py` |

No phantom instruction requirements or untested High-severity behaviors found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, #27, blockers, spec alignment |
| `task.toml` | #14, #35, #44, #45, milestone N/A |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/task_file/main.go` | #17 |
| `tests/test.sh` | #20, #24, #25 |
| `tests/test_outputs.py` | #27–31, spec alignment |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | #21, #32–39, #45, #54, rubric cap, agent stats |
| `docs/guidelines/dockerfile.md` | #15 canonical base |
| `docs/guidelines/rubrics.md` | #35, rubric format |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-cookie-scope-auditor/ ===
Summary: 0 error(s), 1 warning(s), 3 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Worst model |
| oracle | 100.0% (3/3) | Submission report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml:6`) |
| Platform classified | medium (`entire-report.txt:19`) |
| Tier match (#45) | informational only — not a blocker |

Single systematic failure: `test_duplicate_final_attributes_and_rejection_priority_composite` (7/10 runs).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `go-cookie-scope-auditor`; regular layout; report matches task |
| 1 Instruction | ☑ | Detailed spec; fails conciseness (#1); well specified |
| 2 Environment | ☑ | Canonical pinned Go base; tmux+asciinema; offline |
| 3 Oracle | ☑ | Full Go impl in solve.sh; 100% per report |
| 4 Verifiers | ☑ | Reference tests; reward block; no runtime installs |
| 5 Metadata | ☑ | security/go tags appropriate |
| 6 Rubric | ☑ | **Blocker:** +49 > +40; `# Rubric 1` alone OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Spec sufficient; 40% worst model |
| 8 Novelty & fairness | ☑ | Multi-step Go impl; anti-cheat strong |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong work on the cookie auditor — the offline Go environment, reference-based tests, and the level of spec detail for parsing, SameSite, header limits, lifecycle, and diagnostics are all in great shape. Oracle passes cleanly and agent difficulty looks about right. Two things to fix before accept: trim the platform rubric positive criteria from 49 down to 40 or below (merge a few of the smaller +2/+3 parsing lines), and shorten the instruction opening so it reads more like a short problem statement rather than a 40-paragraph spec dump. The single `# Rubric 1` header on a non-milestone task is fine — no need to restructure into milestone blocks.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | yes | 2 |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |
