# Terminus Review Report: git-repository-integrity-verifier

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 41 warnings) |
| **Oracle** | pass (1/1, reward 1.0) |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Git-forensics task with policy-driven outputs, reference-solver verification, digest-pinned canonical Debian base, and passing oracle. One real High blocker: `history_reconstruction.md` requires resolving `{author_date}` from the commit graph via reflog `new_sha`, but neither `instruction.md` nor `integrity_policy.json` states that join — agents hit 39/40 failures on it. ChatGPT/Harbor claims on non-canonical base image, test.sh oracle execution, and milestone rubric format are not blockers on re-audit.

**Insights (concise):**

- `integrity_policy.json` `repository_scope` already names all input filenames; instruction delegates to policy as authoritative — filename gap is overstated.
- `tests/test.sh` running `/app/solution/solve.sh` is correct: deliverable is the script; Harbor does not mount reference `solution/` during agent runs.
- Debian `bookworm-slim` digest is on the canonical list (`docs/guidelines/dockerfxile.md`); preferring `golang:1.24-bookworm` is advisory, not a rule violation.
- Platform rubric uses optional `# Rubric 1` only (no `# Rubric 2+`) — valid non-milestone format per `docs/guidelines/rubrics.md`.
- `#14` pip pinning is a false positive: `requirements.lock` pins with `==` and hashes.
- Worst-model 80% is at easy-tier boundary but not >80%; declared `hard` vs observed tier is informational only (#45).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `history_reconstruction.md` `{author_date}` must be resolved by joining each reflog entry's `new_sha` to `commit_graph.json` commits — not stated in instruction or policy | `integrity_policy.json:104-106` (`line_template`, `event_sort` use `author_date`); `reflog_snapshots.json:4-7` (no `author_date` field); `commit_graph.json:11` (`author_date` on commits); `reference_solver.py:242-243`; `instruction.md:1-3` (no join rule); agent trial ZDpBFNx 39/40 in `entire-report.txt:85-108` | Document in `instruction.md` and/or `integrity_policy.json` that history `author_date` comes from `commit_graph.json[commit].author_date` keyed by reflog `new_sha` |

*No other High-severity blockers confirmed on re-audit.*

**Not blockers (adjudicated):**

| Claim | Verdict | Why |
|-------|---------|-----|
| Non-canonical Debian base for Go task | Disagree | `environment/Dockerfile:1` uses digest on canonical `debian:bookworm-slim` list entry |
| test.sh runs solve.sh before pytest | Disagree | `tests/test.sh:19-23` executes agent/oracle script — deliverable is `/app/solution/solve.sh` |
| Input filenames absent from instruction | Partially agree (Low) | `integrity_policy.json:2-8` `repository_scope` + instruction policy authority |
| Missing per-test docstrings (#31) | Medium (non-blocking alone) | `tests/test_outputs.py` module docstring only; CI warning, not spec gap |
| Rubric milestone format on non-milestone task | Disagree | `# Rubric 1` only — allowed per `rubrics.md:64` |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical Debian base; need golang image or justification (ChatGPT / Harbor §2) | **Disagree** | `environment/Dockerfile:1` digest matches canonical `debian:bookworm-slim` in `docs/guidelines/dockerfxile.md:22`; `validate_task.py` canonical check passes |
| 2 | Input filenames/JSON keys not in instruction.md (ChatGPT High) | **Partially agree** (Low) | `instruction.md:1` lists conceptual inputs; exact names in `integrity_policy.json:2-8`; keys inferable from `branch_refs.json`, `reflog_snapshots.json` |
| 3 | `author_date` requires reflog→graph join; undocumented (ChatGPT High) | **Agree** | See blocker #1; `reference_solver.py:242-243` vs `reflog_snapshots.json` |
| 4 | Derivation rules implicit from fixtures (ChatGPT Medium) | **Partially agree** (Low) | Policy covers algorithms (`merge_base`, `supersession_inference`); only `author_date` source is truly hidden |
| 5 | Markdown lacks exact-match tests (ChatGPT / Test Quality Low) | **Agree** (Low) | `test_outputs.py` uses substring/count checks for markdown; JSON has `test_divergence_matches_reference` |
| 6 | Reference solver epsilon rounding (ChatGPT Low) | **Agree** (Low) | `reference_solver.py:15-17` `1e-9`; scores are 100.0 for this dataset |
| 7 | test.sh executes oracle before tests (Harbor Warning §1) | **Disagree** | `tests/test.sh:19-23` runs agent's `solve.sh`; standard for script-deliverable tasks; solution not in image (`Dockerfile:25`) |
| 8 | behavior_in_task_description FAIL (LLMaJ) | **Partially agree** | Orphan count=3 / specific subjects are data-derived via policy+reference; `author_date` join is the real gap |
| 9 | anti_cheating FAIL — solution accessible (LLMaJ) | **Disagree** | `Dockerfile` has no `COPY solution/`; Harbor agent isolation; standard pattern |
| 10 | Instruction sufficiency FAIL (export) | **Partially agree** | Dominated by `author_date` join; filename timeout trial is agent exploration, not missing spec |
| 11 | Non-milestone rubric uses `# Rubric 1` header (user ask) | **Disagree** (not a defect) | `entire-report.txt:417`; `rubrics.md:64` allows `# Rubric 1` optional, forbids `# Rubric 2+` only |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 2 paragraphs, ~107 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer scenario, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only | `instruction.md` |
| 5 | CHECK | No hints/strategies | Policy-driven WHAT | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | UNCHECK | Well specified | `author_date` join unstated | Blocker #1 |
| 8 | CHECK | Interesting | Real Git forensics use case | task content |
| 9 | CHECK | Unique | Git integrity verifier; no duplicate found in repo | — |
| 10 | CHECK | Absolute paths | `/app/data/`, `/app/solution/solve.sh` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No folder name | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No web content fetch | Local data only | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `requirements.lock` uses `==` + hashes | `environment/requirements.lock:1-12` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | COPY only `data/`, `requirements.lock` | `environment/Dockerfile` |
| 17 | CHECK | No ground truth in env | Input snapshots only | `environment/data/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `environment/Dockerfile:18-20`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | 1/1 reward 1.0 | oracle run 2026-06-29 |
| 22 | CHECK | Oracle offline | No network in solve.sh | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results | Full Go pipeline | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 + ctrf | `tests/test.sh:6-31` |
| 25 | CHECK | Same verifier logic | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:27-30` |
| 27 | UNCHECK | Tests aligned with instruction | `author_date` join tested but unstated | Blocker #1 |
| 28 | CHECK | Tests check correctness | Reference solver exact JSON match | `test_outputs.py:104-106,145-146` |
| 29 | CHECK | Behavior not implementation | Output file checks only | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle where flexible | Reference-based JSON; policy templates | `tests/test_outputs.py` |
| 31 | UNCHECK | Informative docstrings | 40 test functions lack docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives | `entire-report.txt:430-434` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All valid | `entire-report.txt:418-434` |
| 34 | CHECK | Agent …, ±N format | 17 lines | `entire-report.txt:418-434` |
| 35 | CHECK | Rubric detailed | Task-specific Git checks | `entire-report.txt:418-434` |
| 36 | CHECK | Positive-language rubric | Negatives use − scores | `entire-report.txt:430` (−3, not +1) |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:418-434` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:418-434` |
| 39 | CHECK | Rubric no oracle/NOP | None | `entire-report.txt:418-434` |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | — |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category match | go/bash, git tags, system-admin | `task.toml:7-18` |
| 45 | UNCHECK | Difficulty matches agent rates | Declared `hard`; worst 80% → easy tier | `task.toml:6`, `entire-report.txt:19-21`; not revision blocker |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth | Data is input, not answers | `environment/` |
| 52 | CHECK | Input not trivially mutable | Reference solver validates computed outputs | `tests/reference_solver.py` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst model 80% (at boundary, not above) | `entire-report.txt:19-21` |
| 55 | UNCHECK | Not unfair | Undocumented `author_date` join caused systematic near-miss | `entire-report.txt:85-108` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 31, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / policy) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Four output files under `/app/` | `test_*_exists` ×4 | covered | `instruction.md:3`, `test_outputs.py:49-62` |
| Policy-authoritative JSON schemas | `test_divergence_*`, `test_orphan_*` | covered | `integrity_policy.json:65-75`, `test_outputs.py:76-96` |
| Exact JSON vs policy implementation | `test_divergence_matches_reference`, `test_orphan_matches_reference` | covered | `test_outputs.py:104-106,145-146` |
| Report sections/templates from policy | `test_report_*` | covered | `test_outputs.py:169-224` |
| History title/template/filter/sort | `test_history_*` | covered | `test_outputs.py:230-276` |
| **`author_date` from commit graph via `new_sha`** | `test_history_lines_use_policy_template`, `test_history_event_count_matches_reference` | **gap** | Policy lacks source mapping; reflog has no `author_date` |
| Orphan count/reasons (data-derived) | `test_orphan_count_is_three`, `test_orphan_reasons_*` | covered | Enforced via reference solver + policy rules |
| Deterministic re-run | `test_rerun_produces_identical_divergence` | covered | `test_outputs.py:282-289` |
| Input filenames via policy | implicit via `load_json` in tests | covered | `integrity_policy.json:2-8` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #27, blocker 1, claims 2-3 |
| `integrity_policy.json` | Blocker 1, spec alignment, filenames |
| `environment/Dockerfile` | #14-15, canonical base adjudication |
| `environment/requirements.lock` | #14 false-positive rebuttal |
| `environment/data/reflog_snapshots.json` | Blocker 1 — no author_date |
| `environment/data/commit_graph.json` | Blocker 1 — author_date on commits |
| `tests/test.sh` | solve.sh execution adjudication |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `tests/reference_solver.py` | author_date join, epsilon |
| `solution/solve.sh` | #23, oracle |
| `task.toml` | #45-49, metadata |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, prior reviews |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate git-repository-integrity-verifier/
Summary: 0 error(s), 41 warning(s), 2 info
Task type: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | 1 other failure |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 1 timeout, 1 other |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle pass confirmed |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (at 80% boundary) |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only, not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; report matches folder |
| 1 Instruction | ☑ | One High gap: author_date join |
| 2 Environment | ☑ | Canonical debian digest; deps pinned |
| 3 Oracle | ☑ | Passes locally |
| 4 Verifiers | ☑ | solve.sh pattern OK; docstrings missing |
| 5 Metadata | ☑ | Non-milestone; tags valid |
| 6 Rubric | ☑ | `# Rubric 1` only — valid non-milestone format |
| 7 LLMaJ & agent evidence | ☑ | author_date failure pattern confirmed |
| 8 Novelty & fairness | ☑ | Fair after author_date doc fix |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Git-forensics task — the policy-driven design, reference-solver tests, and oracle all look great, and the environment is cleanly set up. One fix before accept: `history_reconstruction.md` uses `{author_date}` in the policy template, but reflog rows don't carry that field. Please document (in `instruction.md` and/or `integrity_policy.json`) that `author_date` must be looked up from `commit_graph.json` using each reflog entry's `new_sha`. Agents are failing 39/40 on exactly that missing join. Optional polish: add per-test docstrings and consider the canonical `golang:1.24-bookworm` base instead of apt `golang-go` on Debian.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Other | no | — |
