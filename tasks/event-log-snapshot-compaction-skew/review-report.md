# Terminus Review Report: event-log-snapshot-compaction-skew

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per submission export 3/3; local oracle not run — Docker unavailable) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Rust recovery task with excellent branch-parity coverage, independent reference oracle, regression traps, and compliant Dockerfile/rubric. One real blocker: `checkpoint_bytes` is graded against a hidden line-based wire format in `tests/ledger_ref.py` that is never specified in `instruction.md` or `/app/environment/docs/*`. Agents can fix structural bugs and still fail byte-count checks. Document the exact checkpoint payload format in env docs (or stop testing unstated byte semantics).

**Insights (concise):**

- ChatGPT High-severity claim on `checkpoint_bytes` wire format is **confirmed** with file evidence; this is the only acceptance blocker.
- Instruction-sufficiency analysis in `entire-report.txt` (both GPT-5.5 trials failed 4/20 on byte-count tests while passing 16/20) corroborates the spec gap.
- Platform rubric uses only `# Rubric 1` (40 positive pts) — **correct** for `number_of_milestones = 0`; not milestone-format misuse.
- Harbor automated review “READY TO USE” and LLMaJ `behavior_in_task_description: pass` are **overstated** — they miss the hidden serialization contract.
- `tests/test_outputs.py` **does** have per-test docstrings; validate/review false-positives on `-> None` return annotations.
- `tests/test.sh` omits canonical `mkdir -p /logs/verifier` — minor compliance gap, not an acceptance blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues; Instruction Styling | #7, #27, #55 | `checkpoint_bytes` exact payload wire format is tested against hidden `ledger_ref.seal_v()` but not documented in instruction or env docs | `instruction.md:7` describes byte length only; `report_schema.md:9`, `state_notes.md:7`, `architecture.md:7` omit row tags/order/newlines; `tests/ledger_ref.py:137-146` defines `v1\|{seq}`, `p,{acct},{bal}` (pots ascending), `r,{acct}` (retired ascending), `s,{src},{dst},{amt}` (staging order), trailing `\n`; `tests/test_outputs.py:214-233` (`test_z03`), `:177-198` (`test_z01`), `:419-440` (`test_z17`) assert against reference; `entire-report.txt:72-100` both agent trials failed only checkpoint-byte tests | Add normative checkpoint payload spec to `/app/environment/docs/` (e.g. `report_schema.md` or new `checkpoint_format.md`) covering header, row tags, sort order, staging rows, newline rules; reference from `instruction.md` |

*No other High/Medium acceptance blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `checkpoint_bytes` serialization under-specified; agents fail byte-count oracle (ChatGPT High) | **Agree** | See blocker #1; `codec/frame.rs:5-15` shows partial `v1\|`, `p,`, `r,` hints but omits staging rows and uses reverse pot sort — insufficient for byte-exact grading |
| 2 | Instruction dense; needs headed sections (ChatGPT Medium) | **Partially agree** | `instruction.md:1-7` is one dense prose block; readability issue only — not an acceptance blocker alone |
| 3 | Expand shell-delegated test docstrings (ChatGPT Low) | **Disagree as blocker** | `tests/test_outputs.py:280-371` already has one-line docstrings on `test_z06`–`test_z13`; optional polish only |
| 4 | Dockerfile digest-pinned; no pinning blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…`; `rust-toolchain.toml` 1.81.0; `pytest==8.4.1` |
| 5 | Non-canonical base image warning (Harbor review) | **Disagree as blocker** | `environment/Dockerfile:9-20` installs `tmux` + `asciinema`; digest-pinned; functional compliance met |
| 6 | Harbor review “READY TO USE” / no critical issues | **Disagree** | Checkpoint wire-format gap is critical per `entire-report.txt:85-100` agent failure analysis |
| 7 | LLMaJ `behavior_in_task_description: pass` | **Partially agree** | Branch-parity fields are described; `checkpoint_bytes` **byte semantics** are not |
| 8 | Instruction sufficiency FAIL on checkpoint serialization | **Agree** | `entire-report.txt:63-100` |
| 9 | Rubric positive cap / format issues | **Disagree** | `# Rubric 1` only, 40 pts — `docs/guidelines/rubrics.md:66` allows optional `# Rubric 1` on non-milestone tasks |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three short prose blocks | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Prose requirements, no RFC tables | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code fences | `instruction.md` |
| 4 | CHECK | No step by step instructions | No developer walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes recovery contract, not fix steps | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | `checkpoint_bytes` wire format unstated | Blocker #1 |
| 8 | CHECK | Instruction is interesting | Realistic WAL/snapshot/compaction debugging | Task content |
| 9 | CHECK | Instruction is unique | Distinct seglog branch-parity scenario set | `config/bundles.toml` |
| 10 | CHECK | All paths are absolute | `/app/environment/...`, `/app/output/...` | `instruction.md:1,5,7` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder name in prompt | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary in prompt | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab runtime web content | Build-time rustup only | `environment/Dockerfile` |
| 14 | CHECK | Python/pip deps pinned with == | `pytest==8.4.1` | `environment/Dockerfile:23` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment self-contained | COPY only under environment/ | `environment/Dockerfile:28-40` |
| 17 | CHECK | No solution/ground truth in environment | `.dockerignore:10-11` excludes solution/tests | `environment/.dockerignore` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in image; test.sh runs pytest only | `environment/Dockerfile:22-23`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per export | `entire-report.txt:35` |
| 22 | CHECK | Oracle no internet | solve.sh local cp + probes | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective of instruction | Repairs source via probes, not hardcoded JSON | `solution/solve.sh:31-41` |
| 24 | UNCHECK | test.sh reward.txt + mkdir + failure path | Missing `mkdir -p /logs/verifier`; reward path present | `tests/test.sh:11-15` vs `docs/guidelines/writing-tests.md:11` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | `echo 0/1` | `tests/test.sh:11-15` |
| 27 | UNCHECK | Tests aligned with instructions | Byte-exact checkpoint format tested but unstated | Blocker #1 |
| 28 | CHECK | Tests check correctness | Regenerates report; reference oracle | `tests/test_outputs.py:109-120` |
| 29 | CHECK | Behavior tests, not source grep | Runs matrix/probes, compares outputs | `tests/test_outputs.py` |
| 30 | CHECK | No brittle format-only checks | Digest/stream invariants are instructed | `instruction.md:7` |
| 31 | CHECK | Informative test names/docstrings | All `test_z01`–`test_z20` have docstrings | `tests/test_outputs.py:177-492` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives | `entire-report.txt:316-318` |
| 33 | CHECK | Rubric scores in ±{1,2,3,5} | All lines valid | `entire-report.txt:304-318` |
| 34 | CHECK | Rubric lines start with Agent, ±N | 15 Agent lines | `entire-report.txt:304-318` |
| 35 | CHECK | Rubric detailed and precise | 40 positive pts at cap | `./scripts/terminus rubric-points` |
| 36 | CHECK | Positive rubric language | Positives describe actions; negatives penalize bad acts | `entire-report.txt:304-318` |
| 37 | CHECK | Rubric no /tests/ references | None | `entire-report.txt:304-318` |
| 38 | CHECK | Rubric no task.toml/instruction.md refs | None | `entire-report.txt:304-318` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:304-318` |
| 40 | CHECK | Required files present | All core paths exist | Task tree |
| 41 | CHECK | No stray parent junk | Clean task folder | Task tree |
| 42 | CHECK | author_name/email present | Set in task.toml | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | timeouts, output path, category | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | rust / data-processing / recovery tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard` declared; platform `medium`; worst-model 60% — informational only | `task.toml:6`, `entire-report.txt:25-31` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:13` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:13` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone-scoped tests | N/A | `task.toml:13` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:11` |
| 51 | CHECK | Solution not accessible in env | Excluded from image | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Report regenerated each run; probes trap partial fixes | `tests/test_outputs.py:109-120`, `test_z06` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst-model 60% | `entire-report.txt:31` |
| 55 | UNCHECK | Not too hard/unfair | Hidden checkpoint byte contract unavailable to agents | Blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 24, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/ledger_report.json` via `run_matrix.sh` | all `test_z*` via `_run_report()` | covered | `instruction.md:1`; `tests/test_outputs.py:109-120` |
| Three branches agree on digests, entries, seq_high_water | `test_z01`, `test_z02`, `test_z07` | covered | `instruction.md:7`; `tests/test_outputs.py:177-299` |
| `checkpoint_bytes` same on forced branches | `test_z03`, `test_z01`, `test_z17` | **gap** | Instructed as byte length (`instruction.md:7`) but exact payload encoding only in `tests/ledger_ref.py:137-146` |
| `fold_records` window `(save_at, compact_at]` | `test_z18`, `test_z08` | covered | `instruction.md:7`; `tests/test_outputs.py:302-316,443-456` |
| Byte-stable double run | `test_z04` | covered | `instruction.md:7`; `tests/test_outputs.py:236-247` |
| `matrix_regress.sh` must pass | `test_z06` | covered | `instruction.md:7`; `tests/test_outputs.py:280-286` |
| Staging checkpoint round-trip | `test_z12` | covered | `state_notes.md:7`; `tests/test_outputs.py:352-360` |
| Entry monotonicity / no duplicate (seq, acct) | `test_z19` | covered | `instruction.md:7`; `tests/test_outputs.py:459-468` |
| Xfer balance neutrality per step | `test_z09` | covered | `instruction.md:7`; `tests/test_outputs.py:318-327` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #27, #55, blocker 1 |
| `environment/docs/report_schema.md` | Blocker 1, spec alignment |
| `environment/docs/state_notes.md` | Checkpoint semantics (no wire format) |
| `environment/codec/frame.rs` | Partial in-env codec hints |
| `tests/ledger_ref.py` | Hidden reference wire format |
| `tests/test_outputs.py` | Verifier assertions |
| `tests/test.sh` | #24 |
| `task.toml` | Metadata, milestones N/A |
| `environment/Dockerfile` | #15, #20 |
| `entire-report.txt` | Agent stats, rubric, sufficiency analysis |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate event-log-snapshot-compaction-skew/
Summary: 0 error(s), 20 warning(s), 1 info
(Warnings: false-positive missing docstrings — tests use `-> None` annotations)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60% (3/5) | 2 failures on checkpoint_bytes tests only per export |
| terminus-claude-opus-4-8 | 100% (5/5) | — |
| oracle | 100% (3/3) | per `entire-report.txt` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | informational only — never blocks |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Rust repair task |
| 1 Instruction | ☑ | Dense but complete except checkpoint wire format |
| 2 Environment | ☑ | Digest-pinned, offline, tmux/asciinema |
| 3 Oracle | ☑ | solve.sh repairs five modules; export 3/3 |
| 4 Verifiers | ☑ | 20 behavior tests + reference oracle; mkdir minor gap |
| 5 Metadata | ☑ | `number_of_milestones = 0`, category fits |
| 6 Rubric | ☑ | `# Rubric 1` only, 40 pts, 3 negatives — non-milestone format OK |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL aligns with blocker |
| 8 Novelty & fairness | ☑ | Strong task; unfair byte oracle without spec |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the branch-parity tests, independent reference oracle, regression traps, and Dockerfile setup are all in great shape, and the Rust bugs are genuinely tricky across five modules. The one thing blocking acceptance is the checkpoint payload format: tests grade exact `checkpoint_bytes` against a specific line-based encoding (`v1|seq`, sorted `p`/`r` rows, `s` staging rows, newline rules) that lives only in the hidden verifier reference, not in `instruction.md` or the env docs. Both GPT-5.5 failures hit exactly that gap while passing everything else. Please document the wire format normatively in `/app/environment/docs/` (and point to it from the instruction) so agents can match byte counts without reverse-engineering the test oracle.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no | — |
| Milestones | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
