# Terminus Review Report: `java-ffmpeg-hls-evidence`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Test Dependency Location, Metadata Issues, Instruction Styling, Milestones

**Decision (concise):** Revise. Digest-pinned JDK image, offline wheel staging, fixture generation, oracle pass (3/3), and 0% agent pass rate support declared `hard` difficulty. Blockers are real: M1 `stash_pristine` can snapshot an already-repaired config as the broken baseline; M3 `test_remux_missing_segments` omits the required `decision=deny` audit assertion; all milestone `test.sh` files run `pip install` at verifier time despite wheels only being downloaded (not installed) in the image; `task.toml` duplicates top-level `[agent]`/`[verifier]` on a milestone task. Fix those first; also correct the “nine source files” wording (11 Java stubs ship) and add test docstrings.

**Insights (concise):**

- Oracle inserts the deny audit row on `missing_segments` (`solve3.sh:529-530`) but the verifier never asserts it — a spec-test gap, not an oracle gap.
- Portal rubrics in `entire-report.txt` have **6** distinct negatives (2 per milestone block), satisfying the ≥3-total rule; ChatGPT misread “per block” as “total.”
- `test_remux_keys_alpha_sorted` is **not** phantom: `/app/docs/API_SPEC.md` requires ASCII-ascending JSON keys on all responses.
- Automated #6 “design-doc tables” is a false positive from `|` inside HMAC canonical strings (`playlist_id|key_version|...`).
- `jobs/` is dev artifact noise (#41); remove before submit. M1 raw JSON indent/newline is only parsed-level checked (minor gap, not blocking).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Milestones | #27, #55 | `stash_pristine` copies `/app/data/recovery_config.json` at first test import; if the agent already ran `recover-config`, the “pristine” baseline is the repaired file, breaking idempotency/repair tests unfairly. | `steps/milestone_1/tests/test_m1.py:62-68`, `178-217`; `FixtureGen.java:83-99` (no pre-baked `_pristine_config.json`) | Pre-bake broken config to `/app/fixtures/_pristine_config.json` in Dockerfile/FixtureGen; never derive pristine from mutable runtime state. |
| 2 | High | Test Alignment/Coverage Issues | #27 | Instruction requires `decision=deny` audit row on `missing_segments`; test checks only exit 1 and stderr JSON. | `steps/milestone_3/instruction.md:5`; `steps/milestone_3/tests/test_m3.py:132-146` | Add `_query` assertion for `audit_log` row with `action='remux'`, `target='cam001'`, `decision='deny'`. |
| 3 | High | Test Dependency Location | #20 | All three milestone `test.sh` run `pip install` at verifier runtime (`--no-index` from `/opt/test-wheels`); wheels are downloaded in Dockerfile but not installed into the image. | `steps/milestone_1/tests/test.sh:9-10`; `environment/Dockerfile:22-30` | `pip install` pytest/JPype1/jaydebeapi into image at build; remove runtime `pip install` from `test.sh`. |
| 4 | Medium | Metadata Issues | #43 | Milestone task has forbidden top-level `[agent]` and `[verifier]` sections (must use `[steps.agent]` / `[steps.verifier]` only). | `task.toml:25-29`; validate output | Remove top-level `[agent]` and `[verifier]` blocks. |
| 5 | Medium | Instruction Styling | #1 | Instructions say “nine source files”; environment ships **11** `.java` stubs. | `steps/milestone_1/instruction.md:11`; `steps/milestone_2/instruction.md:11`; `environment/source/recovery/*.java` (11 files) | Update count/wording to match actual tree (or justify which two are “helpers” excluded from count). |
| 6 | Medium | Test Alignment/Coverage Issues | #31 | 44 test functions lack docstrings (validator warns on every `test_*`). | `steps/milestone_*/tests/test_m*.py`; validate `informative_test_docstrings` | Add one-line docstrings per `test_*` (module docstrings exist). |
| 7 | Low | Task Structure | #41 | Stray `jobs/` directory with oracle/agent run logs in task parent. | `java-ffmpeg-hls-evidence/jobs/` | Delete `jobs/` before submission. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M1 `stash_pristine` derives broken config from mutable runtime state (ChatGPT / entire-report §4) | **Agree** | `test_m1.py:62-68` copies `CONFIG_JSON` only if `_pristine_config.json` missing; `FixtureGen.java` writes broken config to `/app/data/` only, not `_pristine_config.json` |
| 2 | M3 missing `decision=deny` audit assertion on `missing_segments` (ChatGPT / entire-report M3 critical gap) | **Agree** | `instruction.md:5` requires deny row; `test_m3.py:142-144` assert exit + `error` only |
| 3 | Portal rubrics need ≥3 negatives **per** rubric block (ChatGPT) | **Disagree** | `docs/guidelines/rubrics.md:33` requires ≥3 negatives **total**; portal rubrics (`entire-report.txt:662-695`) have 6 negatives (2 per block), exceeding both ≥3 total and ≥1 per block |
| 4 | Instructions say nine source files but tree has 11 (ChatGPT / entire-report typos check) | **Agree** | `instruction.md:11`; 11 files under `environment/source/recovery/` |
| 5 | `test_remux_keys_alpha_sorted` is phantom spec (entire-report M3 observation #3) | **Disagree** | `API_SPEC.md:9-11` mandates ASCII-ascending keys on all JSON bodies; `test_m3.py:94-97` aligns |
| 6 | M3 default `playlist_id=cam001` when omitted is untested (entire-report) | **Partially agree** | `instruction.md:7` states default; no `validate <rule>` without playlist_id in `test_m3.py` — secondary gap, not blocking (all cases pass explicit id) |
| 7 | M1 config raw formatting (two-space indent, trailing newline) only parsed-level (entire-report) | **Agree** | `test_m1.py:195-197` uses `json.loads` compare; `instruction.md:7` mandates formatting — Low severity, not blocking |
| 8 | Task “READY TO USE” / no blockers (entire-report overall assessment) | **Disagree** | Blockers 1–3 above are High spec/harness issues missed by that summary |
| 9 | Difficulty hard / 0% agents (entire-report) | **Agree** | `task.toml:7`; report lines 4-7: 0/5 both models; oracle 100% 3/3 |
| 10 | `pip` wheels pinned offline (entire-report pinned_dependencies pass) | **Partially agree** | Versions pinned and wheels staged (`Dockerfile:25-30`); runtime `pip install` in `test.sh` still violates E2 verifier-deps rule (#20) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Combined milestone instructions ~1234 words / 19 blocks; each file is dense spec prose borderline over limit | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering dossier referencing normative docs; no synthetic LLM patterns | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown formatting | One `###` header per milestone only; no tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States outcomes/contracts, not a solve walkthrough | — |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Exact argv/schema are measurable requirements, not strategy hints | — |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No markdown tables; auto-fail was false positive on `\|` in HMAC strings | `instruction.md:9` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Subcommands, paths, schemas, and doc refs are explicit | `steps/milestone_*/instruction.md`, `environment/docs/` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic encrypted HLS evidence-recovery integration task | — |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Unverified against corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...`, `/opt/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No `java-ffmpeg-hls-evidence` string | — |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time Maven curl for H2 jar only; no runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, etc. in Dockerfile download and test.sh | `environment/Dockerfile:27-30` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | `eclipse-temurin:21-jdk-jammy@sha256:25d1...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only from `environment/` | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No `solution/` or `tests/` in image; fixture answers require runtime master key | `environment/Dockerfile` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/sys_admin/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | UNCHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | `pip install` in all milestone `test.sh` | `steps/milestone_1/tests/test.sh:9-10` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Oracle 100% (3/3) per agent report | `entire-report.txt:11`; `jobs/` trial logs |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve*.sh` write Java sources and `javac`; no curl/pip | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Full crypto/DB/ffmpeg Java implementations in oracle scripts | `steps/milestone_3/solution/solve3.sh:522-557` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block present | `steps/milestone_*/tests/test.sh` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 1` / `echo 0` only | `steps/milestone_*/tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Gaps: deny audit on remux error; unfair M1 pristine fixture | Blockers #1–2 |
| 28 | CHECK | Tests check for correctness, not just format | HMAC re-derivation, SHA-256 plaintext checks, DB queries | `test_m2.py`, `test_m3.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | CLI + JDBC surface only | `steps/milestone_*/tests/test_m*.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Assertions on structured JSON/DB/crypto, not long prose | `test_m*.py` |
| 31 | UNCHECK | Tests have informative names or docstrings | 44 functions missing per-function docstrings | validate warnings |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 6 negatives in portal rubric (`entire-report.txt:670-694`) | `entire-report.txt:662-695` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores ±1,2,3,5 | `entire-report.txt:662-695` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 29 `Agent …, ±N` lines across 3 blocks | `entire-report.txt:662-695` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific crypto/audit/ffmpeg criteria | `entire-report.txt:662-695` |
| 36 | CHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Penalties use negative scores on bad behavior | `entire-report.txt:670-694` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No pytest/`/tests/` refs | `entire-report.txt:662-695` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:662-695` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:662-695` |
| 40 | CHECK | All required files present | Milestone layout: Dockerfile, steps, task.toml | `task.toml`, `steps/` |
| 41 | UNCHECK | No unnecessary files in parent directory (jobs/, README.md, data/, dev notes) | `jobs/` present with local run artifacts | `java-ffmpeg-hls-evidence/jobs/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Both present | `task.toml:5-6` |
| 43 | UNCHECK | All other required metadata fields present | Top-level `[agent]`/`[verifier]` invalid on milestone task | `task.toml:25-29`; validate errors |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `java`, `security`, `h2`, `ffmpeg`, `aes-128` match content | `task.toml:7-13` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` declared; 0% worst-model | `task.toml:7`; `entire-report.txt:4-7` |
| 46 | CHECK | steps/ layout present with per-milestone files | 3 milestones under `steps/` | `task.toml:31-56` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file is scoped only to that milestone | M1/M2/M3 classes map to milestone scope | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests are NOT baked into Docker image | No `COPY tests/` in Dockerfile | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Master key generated at build; FixtureGen source removed | `environment/Dockerfile:38-45,73` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Crypto/chain checks require real implementation | `test_m2.py`, `test_m3.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% | `entire-report.txt:4-7` |
| 55 | UNCHECK | Task is not too hard or unfair | M1 pristine fixture can fail agents who legitimately tested `recover-config` | `test_m1.py:62-68`; report §4 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 9, 20, 27, 31, 41, 43, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `init` creates 4 tables, seeds wrapped keys, idempotent | `TestInit::*` | covered | `test_m1.py:100-174` |
| `init` rejects tampered sig, no rows seeded | `test_init_rejects_tampered_signature` | covered | `test_m1.py:152-174` |
| `recover-config` repairs 5 fields, sorted `repaired` list | `TestRecoverConfig::*` | covered | `test_m1.py:177-217` |
| Broken config baseline stable across repair tests | `stash_pristine` + `_restore_config` | **gap** | `test_m1.py:62-68` — runtime copy |
| `decrypt` plaintext SHA-256 + audit chain | `TestDecryptSingle`, `TestAuditChainAfterDecrypt` | covered | `test_m2.py` |
| `decrypt` deny row on sig mismatch | `test_deny_row_written_on_tampered_sig` | covered | `test_m2.py` |
| `remux` success: MP4, artifact row, allow audit | `TestRemux::test_remux_*` | covered | `test_m3.py:85-130` |
| `remux` missing_segments: exit 1, error JSON, **deny audit** | `test_remux_missing_segments` | **gap** (deny) | `test_m3.py:132-146`; `instruction.md:5` |
| Six validator rules, 24 cases | `TestValidators*` | covered | `test_m3.py:275+` |
| Canonical chain pin on cam001 | `test_six_rule_chain_against_cam001` | covered | `test_m3.py` |
| Scratch path must not mutate cam001 chain | `TestInvalidValidatorDoesNotMutateCam001Chain` | covered | `test_m3.py` |
| `validate` defaults playlist_id to `cam001` | — | gap (minor) | `instruction.md:7`; no omit-id test |
| Success JSON keys ASCII-ascending | `test_*_keys_alpha_sorted` | covered | `API_SPEC.md:9-11`; `test_m3.py:94-97` |
| Config file two-space indent + trailing newline | `test_repair_file_matches_expected` | partial | `test_m1.py:195-197` — parsed only |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/tests/test_m1.py` | Blocker #1, #27, #55, claim 1 |
| `steps/milestone_3/tests/test_m3.py` | Blocker #2, claim 2, spec alignment |
| `steps/milestone_3/instruction.md` | Blocker #2, deny audit requirement |
| `steps/milestone_1/instruction.md` | Blocker #5, nine-files claim |
| `steps/milestone_2/instruction.md` | Blocker #5 |
| `environment/source/recovery/*.java` | Blocker #5 (11 files) |
| `environment/Dockerfile` | #14-17, #20, blocker #3 |
| `steps/milestone_*/tests/test.sh` | Blocker #3, #20 |
| `task.toml` | Blocker #4, #43, #45 |
| `environment/docs/API_SPEC.md` | Claim 5 (alpha keys) |
| `environment/source/fixturegen/FixtureGen.java` | Blocker #1 (no pre-baked pristine) |
| `steps/milestone_3/solution/solve3.sh` | Oracle deny row exists; claim 2 |
| `entire-report.txt` | Agent stats, rubrics, external claims |
| `java-ffmpeg-hls-evidence/jobs/` | #41 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate java-ffmpeg-hls-evidence/
ERROR: task.toml — Milestone tasks must not have top-level [agent] / [verifier]
ERROR: steps/milestone_*/tests/test.sh — Runtime network install not allowed: pip install
WARNING: 44× informative_test_docstrings; milestone TestMilestoneN class naming
Summary: 5 error(s), 47 warning(s)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | No full 3/3 completion |
| terminus-claude-opus-4-8 | 0.0% (0/5) | No full 3/3 completion |
| oracle | 100.0% (3/3) | All milestones pass |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

Per-test: M2/M3 subtests largely 7–10/10 when reached; M1 `test_repair_writes_all_corrections` only 2/10 — mix of implementation bugs and pristine-fixture contamination (`entire-report.txt:35-36,107`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Milestone Java HLS evidence task; report matches folder |
| 1 Instruction | ☑ | Dense but testable; nine-files typo; not overly hintful |
| 2 Environment | ☑ | Digest-pinned JDK, tmux/asciinema, offline wheels staged; runtime pip still required |
| 3 Oracle | ☑ | Derives via Java compile; 3/3 pass; inserts deny on missing_segments |
| 4 Verifiers | ☑ | Strong crypto/DB coverage; two High gaps + docstrings + pip install |
| 5 Metadata | ☑ | `hard` OK; top-level agent/verifier duplicate invalid |
| 6 Rubric | ☑ | Portal rubric meets ≥3 negatives; not in-repo `rubric.txt` |
| 7 LLMaJ & agent evidence | ☑ | 0% agents; M1 bottleneck; infra timeouts noted in report |
| 8 Novelty & fairness | ☑ | Multi-step crypto task; stash_pristine unfairness confirmed |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Digest-pinned JDK image, offline wheel staging, fixture generation, oracle pass, and 0% agent pass rates look solid for declared `hard` difficulty. Blockers: (1) pre-bake `/app/fixtures/_pristine_config.json` instead of copying mutable `recovery_config.json` at test time — agents who test `recover-config` during development can fail repair/idempotency tests unfairly; (2) add a DB assertion for the required `decision=deny` audit row on the `missing_segments` remux path; (3) install verifier Python deps in the Docker image and remove runtime `pip install` from milestone `test.sh`. Also remove duplicate top-level `[agent]`/`[verifier]` from `task.toml`, fix the “nine source files” count (11 ship), add per-test docstrings, and delete stray `jobs/`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 2, 6 |
| Test Dependency Location | yes | 3 |
| Metadata Issues | yes | 4 |
| Instruction Styling | yes | 5 |
| Milestones | yes | 1 |
| Rubric | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
