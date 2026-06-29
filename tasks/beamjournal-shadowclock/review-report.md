# Terminus Review Report: `beamjournal-shadowclock`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 3 warnings) |
| **Oracle** | pass (platform report 3/3; local harbor run errored — RuntimeError) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are strong — binary journal/plan spec, dynamic verifier with restart/live-rewrite checks, digest-pinned Dockerfile, and spec↔test alignment all hold. The only real blocker is the **platform rubric shape**: `number_of_milestones = 0` but the rubric is split into `# Rubric 1`, `# Rubric 2`, and `# Rubric 3`. Collapse to one flat non-milestone list (and trim positive total to ≤40 when merging). ChatGPT’s rubric finding is **confirmed**; automated `#54` / `#14` / `#31` failures are **false positives**.

**Insights (concise):**

- Platform rubric at `entire-report.txt:300–325` has three milestone-style headers; `task.toml:14` sets `number_of_milestones = 0` — violates `docs/guidelines/rubrics.md:64` and `docs/guidelines/submission-export-format.md:63–66`.
- Worst-model pass rate is **60%** (Claude 3/5), not 100%; `#54` passes. GPT-5.5 at 100% makes declared `hard` vs observed medium a calibration note only (`#45` UNCHECK, not a revision blocker).
- `#14` is a false positive: `environment/requirements.lock:1–10` pins `pytest==8.4.1` etc. with hashes; Dockerfile uses `--require-hashes -r`.
- `#31` passes on informative test name `test_folded_ledgers_survive_restarts_and_live_rewrites` even without docstrings.
- Instruction is long (~699 words, 10 blocks) but encodes the full binary spec required by tests; not treated as a revision blocker for this format-heavy task.
- Optional low: clarify 0x08 uses working-buffer length after 0x01/0x02 transforms (`instruction.md:11`; agent near-miss in report lines 46–55).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #34 | Non-milestone task uses milestone-style rubric blocks (`# Rubric 1`, `# Rubric 2`, `# Rubric 3`) | `task.toml:14` `number_of_milestones = 0`; `entire-report.txt:300–325` three `# Rubric N` headers | Collapse platform rubric into one flat `Agent …, ±N` list; remove `# Rubric 2+` headers. When merging, trim positive total to 10–40 (current sum 54). |

*No other High-severity blockers in task artifacts.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT High: platform rubric split into `# Rubric 1/2/3` on non-milestone task | **Agree** | `task.toml:14`; `entire-report.txt:300–325`; `docs/guidelines/rubrics.md:64` |
| 2 | ChatGPT Medium: none | **Agree** | No medium blockers found |
| 3 | ChatGPT Low: clarify 0x08 “payload” = working buffer after 0x01/0x02 | **Partially agree** | `instruction.md:11` uses `len(payload)`; near-miss in `entire-report.txt:46–55`; inferable from flag order — optional, not blocking |
| 4 | ChatGPT Decision: Needs Revision (rubric only) | **Agree** | Rubric format confirmed; task body otherwise solid |
| 5 | Automated review: #54 too easy (100% worst model) | **Disagree** | `entire-report.txt:20–21` Claude 60%, GPT 100%; worst = 60% < 80% |
| 6 | Automated review: #14 unpinned pip | **Disagree** | `environment/requirements.lock:1–10` `==` + hashes; `environment/Dockerfile:40` `--require-hashes` |
| 7 | Automated review: #31 missing docstrings | **Disagree** | `tests/test_outputs.py:348` informative name satisfies “names **or** docstrings” |
| 8 | Automated review: #1 instruction too long | **Partially agree** | `instruction.md` ~699 words / 10 blocks exceeds 3-paragraph guideline; full binary spec required — not a practical revision blocker |
| 9 | LLMaJ: behavior_in_task_description PASS | **Agree** | `entire-report.txt:73`; cross-checked instruction vs `tests/test_outputs.py` |
| 10 | LLMaJ: behavior_in_tests PASS | **Agree** | `entire-report.txt:74`; all major instruction reqs have test coverage |
| 11 | Harbor review: non-canonical Go builder base | **Partially agree** | `environment/Dockerfile:1` uses digest-pinned `golang:1.24-bookworm`; final stage canonical Python; justified multi-stage — not blocking |
| 12 | Harbor review: WORKDIR `/root` not `/app` | **Partially agree** | `environment/Dockerfile:20,57`; style only, tests use absolute paths |
| 13 | Test quality review: ACCEPT | **Agree** | `entire-report.txt:263–267`; reference impl + 3 cases + live rewrites |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Long (~699 words) but full binary spec required in instruction; not blocking for this task type | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Opens “hey, can you fix the beamjournal box?” | `instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, backticks only | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States requirements, not patch walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (endpoints, binary format), not HOW to debug | `instruction.md` |
| 6 | CHECK | No design doc style tables | No tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Endpoints, paths, JSON fields, binary formats fully specified | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic daemon/binary-format debugging | — |
| 9 | CHECK | Instruction is unique | Custom journal fold algorithm + Erlang glue | — |
| 10 | CHECK | All paths in instruction are absolute | `/output/beamjournal/`, `/var/lib/beamjournal/`, etc. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None detected | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | COPY local debs/task_file only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.lock` pins with `==` + hashes | `environment/requirements.lock:1–10`, `environment/Dockerfile:40` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Both stages digest-pinned | `environment/Dockerfile:1,28` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY from `debs/`, `task_file/` only | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken starter Go sources; REFERENCE.md is spec not answers | `environment/task_file/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; test.sh runs pytest only | `environment/Dockerfile:40–45`, `tests/test.sh:6` |
| 21 | CHECK | Oracle passes consistently | Platform oracle 100% (3/3) | `entire-report.txt:25` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Writes local Go sources to `/output/beamjournal/` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full Go implementations, not hardcoded digests | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical 0/1 block | `tests/test.sh:4–13` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` | `tests/test.sh:9–12` |
| 27 | CHECK | All tests are aligned with instructions | Every assertion traces to instruction req | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Reference impl + digest/bytes equality | `tests/test_outputs.py:333–344` |
| 29 | CHECK | Tests verify behavior, not implementation | HTTP/CLI output checks, no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact binary/digest equality required by spec | `tests/test_outputs.py:341–343` |
| 31 | CHECK | Tests have informative names or docstrings | Descriptive test method name | `tests/test_outputs.py:348` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives (-5, -3, -5) | `entire-report.txt:305,316,325` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:301–325` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | **Blocker:** milestone-style `# Rubric 2+` headers on non-milestone task | `task.toml:14`, `entire-report.txt:300–325` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific trace criteria | `entire-report.txt:301–325` |
| 36 | CHECK | Rubric criteria use positive language | Bad behavior uses negative scores | `entire-report.txt:305,316,325` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:301–325` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:301–325` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:301–325` |
| 40 | CHECK | All required files present | Dockerfile, instruction, solve, test.sh, test_outputs, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4–5` |
| 43 | CHECK | All other required metadata fields present | version, category, difficulty, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable | go/erlang/daemon/binary-format fit content | `task.toml:7–13` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 60% = medium tier | `task.toml:6`, `entire-report.txt:15–21` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — non-milestone | `task.toml:14` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:14` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:14` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:14` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Starter code is broken; no oracle output baked in | `environment/task_file/` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests write journal/plan at runtime | `tests/test_outputs.py:349–371` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 60% | `entire-report.txt:20–21` |
| 55 | CHECK | Task is not too hard or unfair | Spec complete; LLMaJ sufficiency PASS | `entire-report.txt:36–37` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 34, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|-----------------------------|---------|--------|-------|
| Daemon on 127.0.0.1:18444; GET /health → 200 ok | `wait_health`, restart loop | covered | `tests/test_outputs.py:352`, `instruction.md:3` |
| GET /ledger JSON fields ok/scope/epoch/digest/bytes/entries | `assert_scope` field check | covered | `tests/test_outputs.py:339–340` |
| epoch=41, digest=sha256(folded), bytes=len(folded) | `assert_scope` value check | covered | `tests/test_outputs.py:341–343` |
| beamjournal-fold output matches daemon | `helper` vs `expected` | covered | `tests/test_outputs.py:335–337` |
| Overrides under /output/beamjournal/ | supervisor picks overrides (oracle path) | covered | `instruction.md:5`, `solution/solve.sh:4` |
| Rendered service.toml values (bind, paths, epoch) | config line assertions after restart | covered | `tests/test_outputs.py:353–362` |
| Legacy + extended journal/plan binary formats | cases 1–3 generators + reference impl | covered | `tests/test_outputs.py:23–40`, `instruction.md:7–17` |
| Kind transforms 0–5, extended flags, plan actions 0–7 | reference `expected()` in tests | covered | `tests/test_outputs.py:66–220` |
| Scope `all`, disabled records, plan rule matching | case generators | covered | `instruction.md:9,15–16` |
| No stale data after live rewrites | case 3 then rewrite case 1 without restart | covered | `tests/test_outputs.py:366–371` |
| entries = enabled matching record count | `expected()` entries vs audit | covered | `tests/test_outputs.py:333–343`, `instruction.md:19` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #34 blocker, #45, milestone N/A |
| `instruction.md` | spec alignment, #1–12 |
| `environment/Dockerfile` | #14–20 |
| `environment/requirements.lock` | #14 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27–31, spec alignment |
| `solution/solve.sh` | #22–23 |
| `entire-report.txt` | rubric blocker, agent stats, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate beamjournal-shadowclock/
Summary: 0 error(s), 3 warning(s), 1 info
- WARN: test docstrings (module + test method)
- WARN: pinned_dependencies false positive on pip line
- INFO: non-milestone preferred milestone format
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst model |
| oracle | 100.0% (3/3) | Platform |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Report matches beamjournal task; regular layout |
| 1 Instruction | ☑ | Long but complete; natural tone |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; deps in image |
| 3 Oracle | ☑ | Platform 100%; local harbor errored |
| 4 Verifiers | ☑ | Dynamic cases; reward block canonical |
| 5 Metadata | ☑ | `number_of_milestones = 0`; tags fit |
| 6 Rubric | ☐ | **Blocker:** three `# Rubric N` blocks on non-milestone |
| 7 LLMaJ & agents | ☑ | Sufficiency PASS; 60% worst model |
| 8 Novelty & fairness | ☑ | Anti-cheat via runtime binary generation |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the binary journal/plan spec is thorough, the verifier exercises restarts and live rewrites well, and the anti-shortcut design looks good. One fix before accept: this is a non-milestone task (`number_of_milestones = 0`), but the platform rubric is split into `# Rubric 1`, `# Rubric 2`, and `# Rubric 3`. Please collapse it into one flat rubric list (no `# Rubric 2+` headers). When you merge, trim the positive point total to 10–40 — the three blocks currently sum to 54. Everything else in the zip looks ready.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
