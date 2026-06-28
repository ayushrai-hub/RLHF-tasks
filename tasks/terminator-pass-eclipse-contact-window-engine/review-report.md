# Terminus Review Report: `terminator-pass-eclipse-contact-window-engine`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; not re-run — Docker unavailable locally) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** The task is well-built: digest-pinned Go image with tmux/asciinema, verifier deps baked via hash-pinned `requirements.txt`, independent Python reference tests, and full spec↔test alignment on core orbital mechanics. The **only real blocker** is metadata: `task.toml` declares `difficulty = "hard"` but agent evaluation places worst-model (Claude Opus 4.8) at **40%** → **Medium** tier. Update `difficulty` to `"medium"` or rebalance until Hard (≤20% on best or worst model). Automated review false-positives on #14, #20, #31, and #54 were overturned on manual audit.

**Insights (concise):**

- ChatGPT’s single High finding (difficulty mismatch) is **confirmed**; all other ChatGPT positives hold on artifact review.
- `scripts/review_checklist.py` `worst_model_rate()` uses `max()` instead of `min()`, falsely flagging #45/#54 as trivial/too-easy; correct worst-model rate is **40%** (Claude), not 100%.
- Pip pinning (#14) and pytest-in-image (#20) **pass**: `environment/requirements.txt` uses `==` + SHA-256 hashes; Dockerfile installs via `--require-hashes`; `test.sh` has no runtime installs.
- Test docstring warnings are CI hygiene only; portal #31 passes on **informative test names** (`test_polar_dual_station_case`, etc.).
- Minor spec gaps (extra validation rules, JSON indent/newline) noted in test-quality review are **Low**, not blockers — core algorithm is thoroughly tested.
- Rubric content appears in `entire-report.txt` for portal UI; no `rubric.txt` in task folder → checkboxes #32–#39 are N/A.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | `task.toml` declares `hard` but worst-model pass rate is 40% (Medium tier) | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:15-21` Claude 40%, GPT-5.5 100%; `docs/guidelines/difficulty.md:7-14` | Set `difficulty = "medium"` **or** rebalance task until ≤20% on best or worst model |

*No other High-severity blockers found on manual re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Difficulty `hard` but evaluation is Medium — Claude 40%, GPT-5.5 100% (ChatGPT) | **Agree** | `task.toml:6`; `entire-report.txt:15-21`; worst = min(40,100)=40% → Medium per `difficulty.md:10` |
| 2 | Digest-pinned Dockerfile, reward/CTRF, tests/solution exclusion, oracle pass, HTTP contract, spec↔test alignment solid (ChatGPT) | **Agree** | `environment/Dockerfile:1,16-17`; `tests/test.sh:2-3,48-53`; no `COPY tests/`; `entire-report.txt:25` oracle 100%; `instruction.md:1-5` + `API_SPEC.md` |
| 3 | Non-canonical golang base image (entire-report WARN) | **Partially agree** | `environment/Dockerfile:1` uses digest-pinned `golang:1.24-bookworm`; acceptable when no canonical Go image exists; not a blocker |
| 4 | Test functions lack docstrings (entire-report SUGGESTION) | **Disagree as blocker** | `tests/test_outputs.py:439-557` — no docstrings, but names are descriptive; portal #31 is names **or** docstrings; CI warning only |
| 5 | Some input validation rules lack dedicated tests (test-quality review) | **Partially agree** | `API_SPEC.md:50-64` lists 11+ rules; `test_outputs.py:536-557` tests only perigee + zero sun vector; secondary gap, not High |
| 6 | Response two-space indent + trailing newline not asserted (test-quality review) | **Partially agree** | `tests/test_outputs.py:360-370` `post()` parses JSON only; Low gap — Go scaffold uses `SetIndent` |
| 7 | LLMaJ behavior_in_task_description / behavior_in_tests PASS (entire-report) | **Agree** | All 9 quality checks pass in `entire-report.txt:86-94`; cross-checked instruction ↔ API_SPEC ↔ tests |
| 8 | Hack check PASS; instruction sufficiency PASS (entire-report) | **Agree** | `entire-report.txt:64-70`; failures are implementation/agent-side |
| 9 | Automated review blockers #14, #20, #31, #54 (baseline script) | **Disagree** | #14: `requirements.txt:1-10` `==`+hashes; #20: pytest in requirements installed in Dockerfile; #31: informative names; #54: worst 40% not >80% |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 short paragraphs, ~80 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering brief tone; defers detail to API_SPEC | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States WHAT (complete solver, build, listen); no solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Points to normative spec; no algorithm hints | `instruction.md` |
| 6 | CHECK | No design doc style tables | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear deliverable: Go HTTP service on :8080, complete `model.go` per API_SPEC | `instruction.md:1-5` |
| 8 | CHECK | Instruction is interesting | Realistic orbital contact / eclipse / terminator problem | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app`, `/app/src/orbit/model.go`, `/app/docs/API_SPEC.md`, etc. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Folder name absent; only domain phrase “terminator-pass-aware” | `instruction.md:1` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.txt` pins `pytest==8.3.4` etc. with hashes; Dockerfile uses `--require-hashes` | `environment/requirements.txt:1-10`, `environment/Dockerfile:17` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY only `task_file/*` within environment | `environment/Dockerfile:19-22` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stub returns “not implemented”; API_SPEC is normative spec, not answers | `environment/task_file/src/orbit/model.go:90-92` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in requirements.txt → image; test.sh only runs pytest | `environment/Dockerfile:16-17`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:25` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes Go source + `make build` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full solver implementation in heredoc, not hardcoded HTTP responses | `solution/solve.sh:3+` |
| 24 | CHECK | test.sh writes reward.txt; mkdir; handles failure | Canonical reward + CTRF pattern | `tests/test.sh:2-3,48-53` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | Writes 0 or 1 | `tests/test.sh:51-53` |
| 27 | CHECK | All tests aligned with instructions | Every test maps to API_SPEC / instruction requirements | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | `compare()` checks numerical fields with tolerances | `tests/test_outputs.py:377-406` |
| 29 | CHECK | Tests verify behavior, not implementation | HTTP POST + reference oracle comparison | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Numeric tolerance asserts; no long string equality | `tests/test_outputs.py:373-406` |
| 31 | CHECK | Tests have informative names or docstrings | Descriptive `test_*` names cover each behavior | `tests/test_outputs.py:439-557` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no rubric file in task folder (portal UI submission) | — |
| 33 | UNCHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion one line starting with Agent | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference /tests/ | N/A | — |
| 38 | UNCHECK | Rubric does not reference task.toml or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, resources, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go/bash scientific-computing orbital task | `task.toml:6-11` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`, observed Medium (40% worst) | `task.toml:6`, `entire-report.txt:20-21` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | — |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | — |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | — |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | Stub only; solution/ not copied | `environment/Dockerfile`, `model.go:90-92` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Dynamic HTTP cases; reference oracle at test time | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 40% ≤ 80% | `entire-report.txt:20-21` |
| 55 | CHECK | Task is not too hard or unfair | Comprehensive API_SPEC; solvable (2/5 Claude, 5/5 GPT); 2 timeouts only | `entire-report.txt:17-31` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / API_SPEC) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| `GET /health` returns `{"ok": true}` | `test_health` | covered | `API_SPEC.md:9`; `test_outputs.py:439-441` |
| `POST /v1/contacts` full response (contacts, samples, eclipse, terminator, sensitivities) | `test_polar_dual_station_case`, `test_equatorial_midlatitude_case`, `test_seeded_contact_grid` | covered | `compare()` `test_outputs.py:377-406` |
| Terminator events ordered, classified ingress/egress | `test_terminator_events_are_ordered_and_classified` | covered | `test_outputs.py:493-505` |
| Terminator events when `require_sunlit=false` | `test_terminator_events_are_reported_when_sunlight_not_required` | covered | `test_outputs.py:508-517` |
| Sunlit clipping affects contacts not terminator events | `test_sunlit_clipping_changes_contacts_but_not_terminator_events` | covered | `test_outputs.py:520-533` |
| HTTP 400 perigee inside Earth | `test_invalid_perigee_inside_earth_rejected` | covered | `API_SPEC.md:59`; `test_outputs.py:536-545` |
| HTTP 400 zero sun vector | `test_invalid_zero_sun_vector_rejected` | covered | `API_SPEC.md:56`; `test_outputs.py:548-556` |
| Build with `make clean && make build`, listen :8080 | exercised in `test.sh` before pytest | covered | `instruction.md:3`; `tests/test.sh:18-46` |
| Additional validation rules (lat/lon bounds, station count, positive step_s, etc.) | — | gap (Low) | `API_SPEC.md:54-64` — only 2 of 11+ rules have dedicated tests |
| JSON two-space indent + trailing newline | — | gap (Low) | `API_SPEC.md` response format; `post()` parses only |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45 blocker, #42-44 |
| `instruction.md` | #1-12, #27 |
| `environment/Dockerfile` | #14-20, #50 |
| `environment/requirements.txt` | #14, #20 |
| `environment/task_file/docs/API_SPEC.md` | #27, §5 |
| `environment/task_file/src/orbit/model.go` | #17, #51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, §5 |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #21, #45, #54, §3 |
| `docs/guidelines/difficulty.md` | #45 tier rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate terminator-pass-eclipse-contact-window-engine/
Summary: 0 error(s), 11 warning(s), 2 info
```

Warnings are docstring-related and a false-positive pip-pinning heuristic (deps pinned in `requirements.txt`).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Worst model; 2 timeouts |
| oracle | 100.0% (3/3) | Per external report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | **40%** (Claude) |
| Observed tier | **medium** |
| Declared difficulty | **hard** |
| Tier match (#45) | **no** |
| Too easy (#54) | **no** (40% ≤ 80%) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task folder matches report; regular (non-milestone) Go HTTP task |
| 1 Instruction | ☑ | Concise, absolute paths, no hints; API_SPEC normative |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, hash-pinned pytest, no tests/solution COPY |
| 3 Oracle | ☑ | solve.sh writes full implementation; report 100% pass |
| 4 Verifiers | ☑ | Canonical test.sh; behavior tests vs Python reference |
| 5 Metadata | ☐ | **Blocker:** difficulty mismatch |
| 6 Rubric | ☑ | N/A in repo; rubric in report for portal |
| 7 Agent evidence | ☑ | Medium tier; not rejected; timeout gate OK (2/10) |
| 8 Novelty & fairness | ☑ | Multi-step orbital implementation; no cheating path found |
| 9 Long context | ☑ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, and Dockerfile pinning look solid. The remaining blocker is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium (GPT-5.5 100%, Claude 40% worst-model). Update `difficulty` to `medium` or rebalance until the task qualifies as hard.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no (Low gaps only) | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Test Build Issues | no | — |
| Oracle Solution Issues | no | — |
