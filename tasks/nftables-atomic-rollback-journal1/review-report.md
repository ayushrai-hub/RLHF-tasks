# Terminus Review Report: `nftables-atomic-rollback-journal1`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High (static audit); Medium on oracle/agent stats (Docker unavailable; wrong submission export) |
| **Validation** | warn (0 errors, 2 warnings) |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** none

**Decision (concise):** After full artifact audit, no High or Medium blockers remain. Prior revision gaps (`"profile"` JSON field and lowercase `epoch.json` keys) are fixed in `instruction.md`. ChatGPT’s non-canonical Docker base claim is false — `debian:bookworm-slim@sha256:4724b8cc…` is an approved canonical digest. Automated `#14` / `#31` failures are false positives. `entire-report.txt` describes a different task (Meson capsule packaging); its rubric and agent stats must not be applied to this submission.

**Insights (concise):**

- Seven pytest functions independently recompute expected audit reports and assert full equality — strong anti-cheat and spec coverage.
- Instruction now explicitly documents `"profile": "<name>"` residue filtering and `epoch.json` lowercase keys (`epoch`, `counter`, `tag`).
- Verifier deps (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`) are digest-pinned in the image; `test.sh` does not install packages at runtime.
- Oracle rewrites ledger/phaseconv/windowfuse/emit Go sources and runs real audits — not hardcoded JSON.
- `entire-report.txt` is for `meson-rpath-reproducible-install` / `tbench-task`, not nftables — rubric checkboxes #32–39 and difficulty gate #54 are unverified here.
- Optional polish only: add a module-level docstring to `tests/test_outputs.py`; consider `golang:1.24-bookworm` canonical image over `apt` Go 1.19 (not required while debian digest is canonical).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical base image: Debian + apt Go instead of canonical Go image (ChatGPT, High) | **Disagree** | `environment/Dockerfile:1` `FROM debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`; exact digest in `docs/guidelines/dockerfxile.md:22` and `scripts/validate_task.py:73` `CANONICAL_BASE_IMAGES`; `validate_task` emits no `check_sanctioned_base_images` warning |
| 2 | Cross-profile residue spec fixed: JSON field `"profile": "<name>"` and lowercase epoch state (ChatGPT, Medium → none) | **Agree** | `instruction.md:5` quotes `"profile": "<name>"` and requires lowercase `epoch`, `counter`, `tag` in `/app/output/state/<profile>/epoch.json` |
| 3 | Dense instruction could use section breaks (ChatGPT, Low) | **Agree** (Low only) | `instruction.md` is 3 paragraphs, ~445 words, no `##` headers — readable polish only, not a blocker |
| 4 | `entire-report.txt` agent stats (GPT 40%, Claude 80%, oracle 100%) apply to this task | **Disagree** | Export describes Meson capsule workflow (`install_manifest.json`, `make package`, `gcc:13-bookworm`); zero nftables/nfrd matches in `entire-report.txt` |
| 5 | LLMaJ `behavior_in_task_description` PASS (entire-report) | **N/A** | Quality checks in export reference Meson task artifacts, not `nftables-atomic-rollback-journal1/` |
| 6 | Harbor REVIEW REPORT “non-canonical gcc:13-bookworm” (entire-report) | **N/A** | Report targets `tbench-task` C/Meson task, not this Go journal task |
| 7 | Automated review blocker `#14` unpinned pip | **Disagree** | `environment/Dockerfile:23-25` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; multiline `pip install` triggers false positive in `review_checklist.py:578` |
| 8 | Automated review blocker `#31` missing test docstrings | **Disagree** | All seven `test_*` at `tests/test_outputs.py:233-399` have docstrings; only module-level docstring absent (`validate_task.py:551` info) |
| 9 | Non-milestone task must not use milestone rubric format (`# Rubric 2+`) | **N/A for this export** | No nftables rubric in `entire-report.txt`; sibling `journal.` rubric used optional `# Rubric 1` only — allowed per `docs/guidelines/rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose paragraphs, ~445 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first prose; no numbered solve script | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | No `##` / tables / code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal and commands, not file-by-file edits | `instruction.md:1-2` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (fix pipeline, regenerate report) | `instruction.md:1` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Profile field, epoch seal schema, report shape, dedup/hash rules documented | `instruction.md:3-5` |
| 8 | CHECK | Instruction is interesting | Real nftables journal audit / crash-recovery scenario | `instruction.md:1` |
| 9 | CHECK | Instruction is unique | Journal replay + profile isolation + lane-probe advisory trap | task content |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/audit_report.json`, etc. | `instruction.md:1-5` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Local COPY only; no runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:23-25` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | All COPY from env subdirs | `environment/Dockerfile:27-43` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken stubs only (`ledger/writer.go:51-52` loads batch.json only) | `environment/ledger/writer.go`, `environment/emit/builder.go` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:22-25`, `tests/test.sh:14` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Not run locally (Docker unavailable) | oracle run 2026-06-30 |
| 22 | CHECK | Oracle does not require internet or downloading packages | Rewrites Go sources, local `go build` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rebuilds ledger/phaseconv/windowfuse/emit; runs audits for gate/depot/yard | `solution/solve.sh:51-366` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:6-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py`, `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 only | `tests/test.sh:17-19` |
| 27 | CHECK | All tests are aligned with instructions | Each test maps to documented replay/dedup/profile/epoch behaviors | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Full `report == _expected_report(profile)` | `tests/test_outputs.py:238,263,278` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs `go run …/nfrd audit`; no source grep | `tests/test_outputs.py:159-170` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Deep equality appropriate for deterministic JSON report | `tests/test_outputs.py:108-156` |
| 31 | CHECK | Tests have informative names or docstrings | All 7 `test_*` have docstrings | `tests/test_outputs.py:233-399` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — `entire-report.txt` rubric is for Meson task, not nftables | `entire-report.txt` (meson capsule lines 366-373) |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A — no nftables platform rubric in export | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A — no nftables platform rubric in export | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A — no nftables platform rubric in export | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A — no nftables platform rubric in export | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A — no nftables platform rubric in export | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A — no nftables platform rubric in export | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A — no nftables platform rubric in export | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task dir |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | task dir |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | Go/bash, system-administration, nftables | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty = "hard"` present; agent stats unavailable (wrong export) — informational only per policy | `task.toml:6` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution outside image; `.dockerignore` excludes `solution/` | `environment/.dockerignore:14`, `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Must fix Go pipeline; expected report recomputed each run | `tests/test_outputs.py:108-156`, `159-161` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | UNCHECK | Task is not too easy (not >80% combined pass rate consistently) | No agent stats for this task in supplied export | `entire-report.txt` (wrong task) |
| 55 | CHECK | Task is not too hard or unfair | Spec documents profile field and epoch seal; tests match instruction | `instruction.md:5`, §5 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 55 |
| **UNCHECK** | 21, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 54 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/audit_report.json` via `nfrd audit` | all tests via `_run_audit` | covered | `tests/test_outputs.py:159-170` |
| Profiles gate, depot, yard exercised | gate, depot, yard in test names | covered | `tests/test_outputs.py:235,247,268,284,318,351,372` |
| Optional `laneprobe yard` | `test_laneprobe_green_does_not_prevent_reseal_from_new_journal_rows` | covered | `tests/test_outputs.py:318-327` |
| Report top-level keys and nested shapes | `_assert_report_shape` | covered | `tests/test_outputs.py:185-216` |
| No boolean verdict fields | `_assert_no_boolean_verdicts` | covered | `tests/test_outputs.py:219-230` |
| Duplicate replay dedup (epoch, source order) | `test_duplicate_replay_is_idempotent` | covered | `tests/test_outputs.py:349-367` |
| Malformed primary + companion journals | `test_corrupt_primary_batch_uses_replay_companions`, `test_primary_loss_companion_rows_keep_empty_phase_deterministic` | covered | `tests/test_outputs.py:245-264`, `370-398` |
| Out-of-order spill rows | `test_spill_rows_are_ordered_before_hashing` | covered | `tests/test_outputs.py:266-279` |
| `"profile": "<name>"` cross-profile residue ignored | `test_interleaved_profile_owners_and_epoch_seals_are_namespaced` | covered | `tests/test_outputs.py:282-315`, `instruction.md:5` |
| `epoch.json` lowercase `epoch`, `counter`, `tag` | `_assert_epoch_seal` | covered | `tests/test_outputs.py:178-182`, `instruction.md:5` |
| Lane probe advisory (does not block reseal) | `test_laneprobe_green_does_not_prevent_reseal_from_new_journal_rows` | covered | `tests/test_outputs.py:318-346` |
| Checkpoint spans / empty settle phases | `test_replay_checkpoint_contract`, `test_primary_loss_companion_rows_keep_empty_phase_deterministic` | covered | `tests/test_outputs.py:233-242`, `387-398` |
| Hash digest format (64-char hex) | `_assert_report_shape` + `_expected_report` | covered | `environment/docs/overview.md:38`, `tests/test_outputs.py:76-91` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, #27, blockers adjudication |
| `environment/Dockerfile` | #14, #15, #20, canonical base claim |
| `environment/docs/overview.md` | hash digest format |
| `environment/ledger/writer.go` | #17 broken baseline |
| `environment/model/types.go` | epoch seal / Record schema |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22, #23 |
| `task.toml` | #44, #45, #46-49 |
| `entire-report.txt` | wrong-task adjudication; not used for rubric/stats |
| `docs/guidelines/dockerfxile.md` | canonical base list |
| `docs/guidelines/rubrics.md` | non-milestone rubric format rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate nftables-atomic-rollback-journal1/
Summary: 0 error(s), 2 warning(s), 2 info
- WARNING: pinned_dependencies (multiline pip false positive)
- WARNING: informative_test_docstrings (module-level only)
- INFO: non-milestone task; milestone preferred
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | — | Not in export for this task |
| terminus-claude-opus-4-8 | — | Not in export for this task |
| oracle | not executed | Docker daemon unavailable locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | unverified (export is Meson task) |
| Observed tier | — |
| Declared difficulty | hard |
| Tier match (#45) | informational only |

**Rubric note:** `entire-report.txt` platform rubric (lines 366–373) references Meson `make package` / `audit_tree.sh` — **do not** score nftables submission against it. On platform, ensure non-milestone flat `Agent …, ±N` list (optional single `# Rubric 1` header per `rubrics.md`; no `# Rubric 2+`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task `nftables-atomic-rollback-journal1`; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | 3 paragraphs; profile + epoch seal documented; absolute paths |
| 2 Environment | ☑ | Canonical debian digest; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Real Go rewrites; not hardcoded (static read; not executed) |
| 4 Verifiers | ☑ | 7 behavioral tests; reward block canonical; deps in image |
| 5 Metadata | ☑ | category/tags/languages match |
| 6 Rubric | ☐ | No nftables rubric in supplied export — verify on platform |
| 7 LLMaJ & agent evidence | ☐ | Export is wrong task — stats/rubric inapplicable |
| 8 Novelty & fairness | ☑ | Multi-file Go repair; cheating paths closed |
| 9 Long context | N/A | `tool_specific` only |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this revision — the profile-owner and epoch-seal documentation fixes close the fairness gap from the prior cycle. The journal replay verifier is thorough (duplicate rows, corrupt primary batches, spill ordering, cross-profile residue, lane-probe advisory), the Dockerfile uses a digest-pinned canonical debian base with verifier deps baked in, and the oracle implements real Go repairs rather than hand-written JSON. I didn’t find any blocking spec-test gaps or environment issues. Please attach the correct platform rubric export for this task on resubmission so rubric checkboxes can be verified; optional polish: a one-line module docstring on the test file.

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
| Rubric | no | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
