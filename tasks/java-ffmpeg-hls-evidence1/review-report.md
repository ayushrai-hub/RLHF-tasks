# Terminus Review Report: java-ffmpeg-hls-evidence1

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (3 false-positive errors on test.sh comments; see §7) |
| **Oracle** | not executed |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** Re-audit confirms three of four ChatGPT High findings are already fixed in the current tree (verifier venv in image, Docker-baked `_pristine_config.json`, remux `missing_segments` deny-audit assertion). The one real High blocker is metadata: `task.toml` declares `difficulty = "hard"` while agent evaluation shows 40% / 60% pass rates (worst-model 60% → **medium** tier). Update `difficulty` to `"medium"` or rebalance until ≤20% on best or worst model.

**Insights (concise):**

- `test.sh` files activate `/opt/test-venv` only — no runtime `pip install`; validate errors are comment false positives (`steps/milestone_*/tests/test.sh:10`).
- Dockerfile lines 98–104 bake `/app/fixtures/_pristine_config.json` at image build; `test_m1.py:62–73` requires it and never falls back to mutable `/app/data/recovery_config.json`.
- `test_remux_missing_segments` (`test_m3.py:137–170`) asserts `decision=deny` audit row on remux failure.
- Per-milestone `task.toml` layout is correct — no top-level `[agent]`/`[verifier]` per `docs/guidelines/milestones.md:99`.
- `eclipse-temurin:21-jdk-jammy` is in the sanctioned canonical list (`scripts/validate_task.py:69`).
- Medium follow-ups (not revise blockers alone): `/app/fixtures/expected_recovery_config.json` is agent-readable (#17/#51); Dockerfile `LABEL` line 3 is stale metadata.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but observed worst-model pass rate 60% → medium tier | `task.toml:7` `difficulty = "hard"`; `entire-report.txt:7–9` GPT-5.5 60% (3/5), Claude 40% (2/5) | Set `difficulty = "medium"` in `task.toml`, or rebalance task until ≤20% on best or worst model per `docs/guidelines/difficulty.md` |

*No other High-severity blockers confirmed on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` but evaluation is Medium (40%/60%) (ChatGPT) | **Agree** | `task.toml:7`; `entire-report.txt:7–9` |
| 2 | Verifier deps installed at runtime via `pip install` in every `test.sh` (ChatGPT) | **Disagree** | All three `test.sh` use `source /opt/test-venv/bin/activate` only (`steps/milestone_1/tests/test.sh:9–16`); Dockerfile installs deps at build (`environment/Dockerfile:31–41`). Validate false-positive matches comment text `pip install` on line 10. |
| 3 | M1 derives `_pristine_config.json` from mutable runtime state if missing (ChatGPT) | **Disagree** | Dockerfile bakes baseline: `environment/Dockerfile:98–104` `cp /app/data/recovery_config.json /app/fixtures/_pristine_config.json`; `test_m1.py:65–69` hard-fails if missing — no runtime fallback |
| 4 | M3 missing `decision=deny` audit assertion for `missing_segments` remux (ChatGPT) | **Disagree** | `test_m3.py:137–170` `test_remux_missing_segments` asserts row count +1, `action=remux`, `decision=deny` |
| 5 | Remove duplicate top-level `[verifier]`/`[agent]` in `task.toml` (ChatGPT) | **Disagree** | `task.toml` has only per-step `[steps.agent]`/`[steps.verifier]` (`task.toml:25–50`); `docs/guidelines/milestones.md:99` requires **no** top-level sections |
| 6 | Add root-level `[verifier]`/`[agent]` sections (`entire-report.txt` WARNING) | **Disagree** | Contradicts milestone schema in `docs/guidelines/milestones.md:59–99`; current layout matches milestone example |
| 7 | Non-canonical Docker base image (`entire-report.txt` CRITICAL) | **Disagree** | `eclipse-temurin:21-jdk-jammy@sha256:25d1276…` is listed in `CANONICAL_BASE_IMAGES` (`scripts/validate_task.py:69`) |
| 8 | Dockerfile has task/revision `LABEL` (ChatGPT Medium) | **Agree** | `environment/Dockerfile:3` `LABEL task=… rev=…` — cleanup only, not a revise blocker |
| 9 | Submitted zip includes stray `jobs/` artifacts (ChatGPT Medium) | **Disagree** | No `jobs/` directory in task folder (`glob java-ffmpeg-hls-evidence1/jobs/**` → 0 files) |
| 10 | Agent can bypass `recover-config` via `/app/fixtures/expected_recovery_config.json` (test-quality review) | **Partially agree** | `test_m1.py:210–216` compares output to readable fixture; `FixtureGen.java:99` writes it to `/app/fixtures/`. Medium anti-cheat gap — agent still must implement crypto/DB for M2/M3. Not a sole revise driver. |
| 11 | Combined instruction too long (#1 automated) | **Partially agree** | Combined ~1234 words across 3 milestones; per-milestone: M1 372w, M2 308w, M3 554w. Dense but doc-referenced; milestone delivery model makes combined threshold misleading. Not a revise blocker. |
| 12 | `test_mN.py` should use `class TestMilestoneN` (validate warning) | **Partially agree** | Uses domain classes (`TestBuildArtifacts`, `TestRemux`, etc.); `docs/guidelines/milestones.md:44` recommends `TestMilestoneN` — style warning only |
| 13 | Instruction says “eleven source files” (ChatGPT Low) | **Disagree** | 11 `.java` files under `environment/source/recovery/`; instruction correctly states eleven (`steps/milestone_1/instruction.md:11`) |
| 14 | Missing per-test docstrings (ChatGPT Low) | **Disagree** | All 44 `test_*` methods have docstrings (grep `steps/milestone_*/tests/test_m*.py`) |
| 15 | LLMaJ `behavior_in_tests` PASS — full spec coverage | **Agree** | `entire-report.txt:148`; confirmed remux deny audit, init/recover-config, decrypt chain, 24 validator cases |
| 16 | Agent failures are routing/timeout/edge-case, not spec gaps | **Agree** | `entire-report.txt:100–107` Pattern A/B/C; `task_specification: pass` all trials |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Combined 3-milestone text ~1234 words / 19 blocks exceeds automated threshold; per-milestone text is dense but doc-delegated | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer incident tone; defers schemas to `/app/docs/` | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Only `###` milestone headers; no tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Numbered flow in M2 describes API contract, not dev walkthrough | `steps/milestone_2/instruction.md:5` |
| 5 | CHECK | No hints or solving strategies | Requirements state WHAT; crypto details in docs | `steps/milestone_*/instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No markdown tables in instructions; pipe chars are HMAC canonical strings | `steps/milestone_1/instruction.md:9` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Measurable subcommands, paths, JSON contracts, error codes | `steps/milestone_*/instruction.md`, `environment/docs/` |
| 8 | CHECK | Instruction is interesting | Realistic body-cam HLS evidence recovery scenario | — |
| 9 | UNCHECK | Instruction is unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...`, `/opt/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No `java-ffmpeg-hls-evidence` string | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time Maven curl for H2 jar only | `environment/Dockerfile:44–47` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `JPype1==1.5.0`, etc. on install lines | `environment/Dockerfile:33–41` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only from `environment/` | `environment/Dockerfile` |
| 17 | UNCHECK | Environment does not contain solution or ground truth answers | `/app/fixtures/expected_recovery_config.json` is exact repair answer, agent-readable | `FixtureGen.java:99`, `test_m1.py:27` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | Venv activate only; deps in Dockerfile | `environment/Dockerfile:31–41`, `steps/milestone_*/tests/test.sh:9–11` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed in this review | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solveN.sh` writes Java source and compiles only | `steps/milestone_1/solution/solve1.sh` |
| 23 | UNCHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Manual spot-check only; scripts implement real crypto/DB logic | `steps/milestone_*/solution/solveN.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block all milestones | `steps/milestone_*/tests/test.sh:1–22` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | `echo 0` / `echo 1` only | `steps/milestone_*/tests/test.sh:18–21` |
| 27 | CHECK | All tests are aligned with instructions | LLMaJ PASS; remux deny, init sig, validator chain covered | `entire-report.txt:147–148` |
| 28 | CHECK | Tests check for correctness, not just format | HMAC re-derivation, SHA-256 plaintext checks, H2 row assertions | `test_m2.py:219–221`, `test_m3.py:394–395` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep; CLI + DB surface | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | JSON parse + crypto re-derive vs raw string grep | `test_m2.py`, `test_m3.py` |
| 31 | CHECK | Tests have informative names or docstrings | 44/44 `test_*` methods have docstrings | `steps/milestone_*/tests/test_m*.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no `rubric.txt` in task folder (rubric only in external report) | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Milestone layout complete | `task.toml`, `environment/`, `steps/milestone_*/` |
| 41 | CHECK | No unnecessary files in parent directory | No `jobs/`, README, or stray artifacts | task root listing |
| 42 | CHECK | author_name and author_email fields present | `anonymous` / `anonymous` | `task.toml:5–6` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, milestones | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable | `java`, `security`, `db_interaction`, H2/AES/HLS/ffmpeg | `task.toml:8–13` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared hard; worst-model 60% → medium | `task.toml:7`, `entire-report.txt:7–9` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `task.toml:17`, `steps/` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | M1 init/repair; M2 decrypt; M3 remux/validate/audit | `steps/milestone_*/tests/test_m*.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ in Dockerfile | `environment/Dockerfile` |
| 51 | UNCHECK | Solution or ground truth answers are not accessible in the environment | `expected_recovery_config.json`, `expected_decrypt.json`, `expected_validators.json` under `/app/fixtures/` | `environment/Dockerfile:89–95` |
| 52 | UNCHECK | Agent cannot modify input data to trivially pass tests | Crypto fixtures require real implementation; config copy shortcut exists for M1 only | `test_m1.py:210–216` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate) | Worst-model 60% ≤ 80% | `entire-report.txt:7–9` |
| 55 | CHECK | Task is not too hard or unfair | Failures are dispatch bugs, timeouts, single validator edge case — not env bugs | `entire-report.txt:100–107` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 22, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 53, 54, 55 |
| **UNCHECK** | 1, 9, 17, 21, 23, 32, 33, 34, 35, 36, 37, 38, 39, 45, 51, 52 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `init` creates 4 H2 tables + seeds wrapped keys | `test_init_creates_four_tables`, `test_seeded_wrapped_keys_match_json` | covered | `test_m1.py:134–158` |
| `init` rejects tampered `sig_hex` | `test_init_rejects_tampered_signature` | covered | `test_m1.py:168–193` |
| `recover-config` repairs 5 fields + idempotent | `test_repair_writes_all_corrections`, `test_repair_idempotent` | covered | `test_m1.py:195–237` |
| `decrypt` plaintext SHA-256 + audit chain HMAC | `test_decrypt_plaintext_matches_expected`, `test_audit_chain_entry_hash_recomputes` | covered | `test_m2.py:99–221` |
| `decrypt-all` partial failure exit 1 | `test_decrypt_all_exits_nonzero_on_partial_failure` | covered | `test_m2.py:150–197` |
| Deny audit on decrypt sig mismatch | `test_deny_row_written_on_tampered_sig` | covered | `test_m2.py:233–274` |
| `remux` MP4 + artifact row + allow audit | `test_remux_emits_mp4`, `test_remux_inserts_audit_row_with_allow` | covered | `test_m3.py:85–135` |
| `remux` `missing_segments` → deny audit row | `test_remux_missing_segments` | covered | `test_m3.py:137–170` |
| Six validator rules × valid/invalid cases | `TestValidators*` parametrized cases | covered | `test_m3.py:302–359` |
| Validator chain SHA-256 on cam001 | `test_six_rule_chain_against_cam001` | covered | `test_m3.py:394–415` |
| Scratch-path must not mutate cam001 chain | `test_invalid_byte_range_leaves_cam001_chain_unchanged` | covered | `test_m3.py:416–445` |
| `audit list` HMAC chain re-derivation | `test_audit_list_emits_chain` | covered | `test_m3.py:468–496` |
| `recover-config` stdout compact JSON + sorted keys | — | gap | M1 tests parse stdout but do not assert compactness (unlike `test_init_compact_json`) |
| `unwrap_failed` / `decrypt_failed` deny paths | — | gap | Only `sig_mismatch` deny path tested in M2 |
| `validator_sha256` in scratch-path JSON response | — | gap | Parametrized validator tests assert `valid` only (`test_m3.py:302–359`) |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, blocker 1 |
| `entire-report.txt` | Agent stats, external adjudication |
| `environment/Dockerfile` | #14–#16, #20, pristine baseline, venv |
| `steps/milestone_*/tests/test.sh` | #20, #24 (false-positive validate) |
| `steps/milestone_1/tests/test_m1.py` | Pristine config, recover-config tests |
| `steps/milestone_3/tests/test_m3.py` | Remux deny audit, validator coverage |
| `docs/guidelines/milestones.md` | task.toml layout adjudication |
| `docs/guidelines/difficulty.md` | Tier thresholds |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate java-ffmpeg-hls-evidence1/
ERROR: test.sh [steps/milestone_*/tests/test.sh]: Runtime network install not allowed: pip\s+install
  → FALSE POSITIVE: comment on line 10 contains "pip install"; no actual install command
WARNING: pinned_dependencies — same comment-line false positive on Dockerfile:23
WARNING: milestone — test_mN.py class naming (TestBuildArtifacts vs TestMilestoneN)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 partial-milestone failures |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Routing bug + timeout patterns |
| oracle | 100.0% (3/3) | Per report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `java-ffmpeg-hls-evidence1`; 3-milestone Java security task; report matches |
| 1 Instruction | ☑ | Well-specified; per-milestone delivery; dense M3 |
| 2 Environment | ☑ | Digest-pinned canonical JDK; tmux+asciinema; offline wheels+venv; pristine config baked |
| 3 Oracle | ☑ | Not executed; static review shows real implementations in solveN.sh |
| 4 Verifiers | ☑ | No runtime installs; deny audit present; 3 minor spec gaps (non-blocking) |
| 5 Metadata | ☑ | **Blocker:** difficulty mismatch |
| 6 Rubric | ☑ | N/A in task folder; external rubric in report looks compliant |
| 7 LLMaJ & agent evidence | ☑ | 60% worst-model medium; failures agent-side not spec-side |
| 8 Novelty & fairness | ☑ | Multi-step crypto/DB/HLS; M1 config-copy shortcut is medium concern |
| 9 Long context | ☐ | Not tagged `long_context` — N/A |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Verifier hygiene items from prior review are addressed: Python deps are in `/opt/test-venv` at image build, `_pristine_config.json` is Docker-baked, and `test_remux_missing_segments` asserts the `decision=deny` audit row. The remaining High blocker is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium (GPT-5.5 60%, Claude 40%). Update `difficulty` to `medium` or rebalance until the task qualifies as hard.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Test Dependency Location | no | — (fixed; validate false positive) |
| Test Alignment/Coverage Issues | no | — (deny audit present; minor gaps non-blocking) |
| Metadata Issues | no | — (difficulty counted under Task Difficulty) |
| Environment | no | — (LABEL is cleanup only) |
| Exposing Hints/Answers | no | — (expected_recovery_config readable; medium follow-up, not sole blocker) |
