# Terminus Review Report: `nftables-atomic-rollback-journal.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 2 warnings) |
| **Oracle** | not executed (Harbor/Docker unavailable locally; platform report: 100% 3/3) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Go journal-replay task with solid fixtures, anti-cheat design, and verifier depth. One real High blocker: instruction describes “profile owner” residue filtering but never names the JSON field `profile` that tests and the oracle use — 5/6 agent runs failed systematically on this. Secondary fix: document lowercase `epoch.json` schema (`epoch`, `counter`, `tag`) for persisted seals. External report’s non-canonical base-image claim is false (`debian:bookworm-slim` is canonical). Rubric `# Rubric 1` header alone is valid for a non-milestone task.

**Insights (concise):**

- Verifier recomputes expected reports independently; 7 behavioral tests cover crash residue, spill ordering, owner isolation, lane-probe trap, and idempotent replay.
- Fixture rows never include a `profile` field; only tests inject `profile="gate"` — agents reasonably invented `owner` or omitted the field.
- `manifest/layout.json` already shows lowercase `epoch`/`counter`/`tag`; epoch seal gap is weaker than the profile-field gap (1/6 agent failures vs 5/6).
- Platform rubric is flat (one optional `# Rubric 1` header), 36 positive pts, 3 negatives — correct non-milestone format.
- Automated `#14` / `#31` failures are false positives: pip packages are `==`-pinned; all seven `test_*` functions have docstrings.
- Worst-model 80% at rejection threshold; best-model 0% supports declared `hard`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #7, #27, #55 | Profile-owner filtering uses JSON field `profile`, but instruction only says “profile owner” without naming the field. Verifier ignores alien rows via `rec.get("profile")`; fixtures omit the field entirely. | `instruction.md:5` (“Some recovered rows may carry a profile owner…”); `tests/test_outputs.py:46-47` (`owner = rec.get("profile")`); `tests/test_outputs.py:292,301,379` (injects `profile="gate"`/`"yard"`); `entire-report.txt:55-55` (5/6 trials failed on wrong field name); fixtures e.g. `environment/fixtures/gate_rules/batch_001.json:1-7` (no `profile` key) | Add explicit requirement: cross-profile residue rows carry `"profile": "<profile_name>"`; rows where `profile` is non-empty and ≠ active profile must be excluded before dedup, epoch, counter, checkpoint, and entry computation. |
| 2 | Medium | Test Alignment/Coverage Issues, Instruction Styling | #27 | Persisted epoch seal file schema is tested but not stated in instruction. `EpochMeta` lacks JSON tags; verifier expects lowercase keys in `/app/output/state/<profile>/epoch.json`. | `environment/model/types.go:51-55` (no `json` tags on `EpochMeta`); `tests/test_outputs.py:178-181` (`seal["epoch"]`, `seal["counter"]`); `instruction.md:5` (“updates … persisted epoch metadata” — no file schema); `entire-report.txt:57-57` (1/6 trial capitalized keys); mitigating: `environment/manifest/layout.json:1-5` (lowercase schema example) | Document that persisted `epoch.json` must serialize as lowercase JSON keys `epoch`, `counter`, and optional `tag`, matching the layout manifest format. |

*No other High-severity blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Profile-owner JSON field must be documented as `"profile"` (ChatGPT / entire-report instruction sufficiency) | **Agree** | See blocker 1 proof |
| 2 | Persisted `epoch.json` must use lowercase keys `epoch`, `counter`, `tag` (ChatGPT / entire-report) | **Partially agree** | Test enforces lowercase (`test_outputs.py:178-181`); instruction silent; `layout.json` shows schema — Medium, not standalone High |
| 3 | Non-canonical base image requires ghcr.io golang base (Harbor REVIEW REPORT) | **Disagree** | `environment/Dockerfile:1` uses `debian:bookworm-slim@sha256:4724b8cc…`; listed canonical in `docs/guidelines/dockerfxile.md:22` and `scripts/validate_task.py` `CANONICAL_BASE_IMAGES` |
| 4 | Dense instruction formatting is unfair (Harbor REVIEW REPORT warning) | **Disagree** (Low only) | `instruction.md` is dense but within 3 paragraphs; readability polish, not a spec blocker |
| 5 | LLMaJ `behavior_in_task_description` PASS | **Partially agree** | Passes most fields; fails on undocumented `profile` JSON key and `epoch.json` seal schema |
| 6 | LLMaJ `behavior_in_tests` PASS | **Agree** | Seven tests map to instruction behaviors; owner-filter gap is instruction-side |
| 7 | Test quality ACCEPT | **Agree** | Full equality vs reference impl; no shortcut paths |
| 8 | Rubric uses milestone `# Rubric 1` header on non-milestone task | **Disagree** (not a blocker) | `task.toml:9` `number_of_milestones = 0`; `docs/guidelines/rubrics.md:64` allows optional `# Rubric 1`; no `# Rubric 2+` |
| 9 | Automated `#14` unpinned pip | **Disagree** | `environment/Dockerfile:23-25` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; validator false positive on multiline `pip install` |
| 10 | Automated `#31` missing test docstrings | **Disagree** | All seven `test_*` at `tests/test_outputs.py:233-399` have docstrings; only module-level docstring absent (Low) |
| 11 | Automated `#36` rubric negative phrasing | **Disagree** | `entire-report.txt:367` “Agent fails to run…” is a `-1` penalty for bad behavior — acceptable per `docs/guidelines/rubrics.md:38-39` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose paragraphs | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first prose, no numbered solve script | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal and command, not file-by-file edits | `instruction.md:1-2` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT (fix pipeline, regenerate report) | `instruction.md:1` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Profile JSON field name unstated (blocker 1) | `instruction.md:5`, `tests/test_outputs.py:46` |
| 8 | CHECK | Instruction is interesting | Real nftables journal/audit recovery scenario | `instruction.md:1` |
| 9 | CHECK | Instruction is unique | Journal replay + epoch seal + lane-probe trap combo | task content |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/audit_report.json` | `instruction.md:1-2` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:23-25` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | All COPY from env subdirs | `environment/Dockerfile:27-43` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken stubs only; no final report | `environment/ledger/writer.go:51-52`, `environment/emit/builder.go` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:22-25`, `tests/test.sh:14` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Not run locally; platform shows 100% 3/3 | `entire-report.txt:29` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Patches Go sources, local build | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Rewrites ledger/phaseconv/windowfuse/emit; runs audit | `solution/solve.sh:51-365` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:6-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py`, `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 only | `tests/test.sh:17-19` |
| 27 | UNCHECK | All tests are aligned with instructions | Tests enforce `profile` key and lowercase `epoch.json` not fully specified | blockers 1–2 |
| 28 | CHECK | Tests check for correctness, not just format | Full `report == _expected_report(profile)` | `tests/test_outputs.py:238,263,278` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep; runs binary and checks output | `tests/test_outputs.py:159-170` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Deep equality appropriate for deterministic JSON report | `tests/test_outputs.py:108-156` |
| 31 | CHECK | Tests have informative names or docstrings | All 7 `test_*` have docstrings | `tests/test_outputs.py:233-399` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives (-5, -2, -1) | `entire-report.txt:365-367` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:351-367` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 17 Agent lines | `entire-report.txt:351-367` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific stub/pipeline checks | `entire-report.txt:351-367` |
| 36 | CHECK | Rubric criteria use positive language | `-1` line describes bad behavior to penalize | `entire-report.txt:367` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:350-367` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:350-367` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:350-367` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task dir |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | task dir |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | Go/bash, system-administration, nftables | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 0%, worst 80% at ≤80% cap | `entire-report.txt:19-25`, `task.toml:6` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution outside image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Must fix Go pipeline; expected report recomputed | `tests/test_outputs.py:108-156` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 80% ≤ 80% | `entire-report.txt:24-25` |
| 55 | UNCHECK | Task is not too hard or unfair | Undocumented `profile` field caused systematic 5/6 failures | `entire-report.txt:55-55`, blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/audit_report.json` via audit command | all tests | covered | `instruction.md:1-2`, `tests/test_outputs.py:159-170` |
| Report top-level schema (profile, epoch, counter, runs, entries, checkpoints) | all tests | covered | `instruction.md:3`, `tests/test_outputs.py:185-216` |
| Duplicate replay rows idempotent | `test_duplicate_replay_is_idempotent` | covered | `instruction.md:5`, `tests/test_outputs.py:349-367` |
| Malformed primary + companion journals | `test_corrupt_primary_batch_uses_replay_companions` | covered | `instruction.md:5`, `tests/test_outputs.py:245-263` |
| Spill row ordering before hashing | `test_spill_rows_are_ordered_before_hashing` | covered | `instruction.md:5`, `tests/test_outputs.py:266-279` |
| Cross-profile owner residue ignored | `test_interleaved_profile_owners_and_epoch_seals_are_namespaced`, `test_primary_loss_companion_rows_keep_empty_phase_deterministic` | **gap** | `instruction.md:5` (concept only); `tests/test_outputs.py:46-47` uses `"profile"` key |
| Epoch/counter from layout + persisted + rows | multiple | covered | `instruction.md:5`, `tests/test_outputs.py:108-113` |
| Persisted epoch seal updated after audit | `test_interleaved…`, `test_laneprobe…`, `test_primary_loss…` | **gap** | `instruction.md:5`; `tests/test_outputs.py:178-181` expects lowercase keys |
| Lane probe advisory only | `test_laneprobe_green_does_not_prevent_reseal_from_new_journal_rows` | covered | `instruction.md:5`, `tests/test_outputs.py:318-346` |
| Empty phase segments zero spans | `test_primary_loss_companion_rows_keep_empty_phase_deterministic` | covered | `instruction.md:5`, `tests/test_outputs.py:386-397` |
| Undo rows replace rule state | gate equality | covered | `instruction.md:5`, gate fixtures with undo actions |
| sha256 64 lowercase hex hashes | all tests | covered | `instruction.md:3`, `environment/docs/overview.md:38`, `tests/test_outputs.py:13` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | blockers 1–2, #7, #27, #55 |
| `tests/test_outputs.py` | blockers 1–2, #27-31, spec alignment |
| `environment/model/types.go` | blocker 2, EpochMeta tags |
| `environment/manifest/layout.json` | blocker 2 mitigation, epoch schema hint |
| `environment/Dockerfile` | #14-20, canonical base adjudication |
| `environment/fixtures/gate_rules/batch_001.json` | blocker 1 (no profile field in fixtures) |
| `solution/solve.sh` | #23, oracle behavior |
| `task.toml` | #45-49, metadata |
| `entire-report.txt` | agent stats, rubric, external claims |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `docs/guidelines/rubrics.md` | rubric format (#32-39) |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate nftables-atomic-rollback-journal./
Summary: 0 error(s), 2 warning(s), 2 info
```

Warnings: multiline pip false-positive; missing module-level test docstring (all test functions documented).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | At easy-tier ceiling |
| terminus-claude-opus-4-8 | 0.0% (0/5) | All failed |
| oracle | 100.0% (3/3) | Platform report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (at 80% cap) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% supports hard) |

Per-test pass rates (`entire-report.txt:37-43`): owner/epoch tests 4/10; core replay tests 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches report; regular (non-milestone) Go task |
| 1 Instruction | ☑ | Profile field gap confirmed |
| 2 Environment | ☑ | Canonical debian base; digest-pinned; tmux/asciinema present |
| 3 Oracle | ☑ | solve.sh patches pipeline; not run locally |
| 4 Verifiers | ☑ | 7 tests; reward block canonical; no runtime installs |
| 5 Metadata | ☑ | hard, system-administration, tool_specific |
| 6 Rubric | ☑ | Non-milestone flat list; `# Rubric 1` optional; 36 pts, 3 negatives |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed for profile field |
| 8 Novelty & fairness | ☑ | Unfair hidden `profile` key name |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid journal-replay task — the durable batch fixtures, phase-scoped replay, duplicate-row handling, checkpoint checks, lane-probe trap, and offline verifier setup are all in great shape. Two spec gaps to fix before accept: (1) instruction says rows may carry a “profile owner” but never names the JSON field — tests filter on `"profile"`, and agents consistently used `owner` or omitted the field; please document that cross-profile residue uses `"profile": "<name>"` and must be ignored before epoch/counter/checkpoint work. (2) Optionally clarify that persisted `/app/output/state/<profile>/epoch.json` must use lowercase keys `epoch`, `counter`, `tag` (layout manifest already shows the pattern). Rubric format is fine for a non-milestone task.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
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
