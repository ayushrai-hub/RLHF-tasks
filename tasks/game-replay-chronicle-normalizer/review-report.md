# Terminus Review Report: `game-replay-chronicle-normalizer`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** Manual re-audit confirms this is a solid Go/Bash replay-normalization debugging task with digest-pinned canonical base, offline verifier deps, hidden fixtures, reference-based tests, and a passing oracle. ChatGPT’s Accept call is supported. The automated `./scripts/terminus review` blockers on #14, #31, and #54 are false positives; no High-severity gaps remain.

**Insights (concise):**

- Platform rubric is correctly formatted as a flat non-milestone list (no `# Rubric 2+` headers); 35 positive pts, 6 distinct negatives.
- Worst-model pass rate is **40%** (Claude Opus 4.8), not 100% — automated review used `max()` instead of `min()` across agent rates.
- All 23 `test_*` functions in `tests/test_outputs.py` have docstrings; validate warnings are stale.
- `pytest==9.0.3` and `pytest-json-ctrf==0.5.0` are pinned in the Dockerfile; #14 fail was a multiline `pip install` parsing false positive.
- Golang base image matches the canonical digest in `docs/guidelines/dockerfxile.md`.
- Optional polish only: task folder name in rebuild-script path (#11), declared `hard` vs observed medium (#45), explicit corrupt-shard exit wording, validate+TB3_FIXTURE_ROOT test.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium blockers | Agree | Full artifact audit; oracle pass; spec↔test alignment in §5 |
| 2 | ChatGPT: corrupt-shard exit ambiguity is polish only | Agree | `environment/docs/replay-format.md:27` — “Reject shards whose magic is not `GRSH`…”; `tests/test_outputs.py:206-213` asserts `returncode != 0` |
| 3 | ChatGPT: consider `difficulty = "medium"` | Partially agree | `entire-report.txt:20-21` worst 40% → medium tier; informational #45 only, not a revision blocker per `prompt.md` |
| 4 | ChatGPT: Dockerfile digest-pinned, canonical check inconclusive | Disagree | `environment/Dockerfile:1` digest matches `docs/guidelines/dockerfxile.md:11` exactly |
| 5 | Harbor REVIEW: Revise — instruction says “Implement” not “fix bugs” | Disagree | `instruction.md:3-7` names existing CLI path, rebuild script, and four normative docs; scaffold with intentional bugs ships in image (`environment/internal/parse/reader.go:30` wrong magic). Agent rewrite risk is Low, not High |
| 6 | Harbor REVIEW: non-canonical Golang base | Disagree | Same digest as canonical list (`dockerfxile.md:11`) |
| 7 | LLMaJ instruction sufficiency FAIL (corrupt-shard ambiguity) | Partially agree | One trial skipped corrupt shards; spec “Reject” plus CRC tests imply non-zero exit — polish only, not blocker |
| 8 | Test quality: TB3_FIXTURE_ROOT untested for validate | Agree | `instruction.md:5` requires both subcommands; `tests/test_outputs.py:311-323` tests normalize only; `environment/cmd/replay-chronicle/main.go:66-67` scaffold implements both |
| 9 | Test quality: no byte-level GRPL structure assertion | Partially agree | `test_pack_unpack_roundtrip` + `test_reference_pack_matches_unpack` + `test_pack_header_crc_enforced_on_unpack` jointly enforce format; hardening only |
| 10 | Automated review: #14 unpinned pip blocker | Disagree | `environment/Dockerfile:15-17` — `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` |
| 11 | Automated review: #31 missing docstrings blocker | Disagree | All 23 tests have docstrings, e.g. `tests/test_outputs.py:141-142` |
| 12 | Automated review: #54 worst-model 100% too easy | Disagree | `entire-report.txt:20-21` — Claude 40% is worst model; GPT-5.5 100% is best model |
| 13 | Automated review: #11 task name in instruction | Agree | `instruction.md:7` — `rebuild-game-replay-chronicle-normalizer` contains folder name; Medium, single-item, not Revise driver |
| 14 | Platform rubric uses milestone `# Rubric N` headers on non-milestone task | Disagree | `entire-report.txt:366-381` — flat `Agent …, ±N` list, no `# Rubric 2+`; correct per `docs/guidelines/rubrics.md:64` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 4 short paragraphs, ~138 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Human engineering tone; no LLM boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Title + prose only | `instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT + normative doc pointers only | `instruction.md:5` |
| 6 | CHECK | No design doc style tables in instruction | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | CLI paths, subcommands, env override, four spec docs named | `instruction.md:3-7` |
| 8 | CHECK | Instruction is interesting | Real binary replay normalization problem | — |
| 9 | CHECK | Instruction is unique | GRSH/GRPL chronicle pipeline not seen in TB2 corpus sample | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/bin/...`, `/app/docs/...`, `/opt/verifier-scripts/...` | `instruction.md` |
| 11 | UNCHECK | Task name does not appear in instruction.md | Rebuild script path embeds folder slug | `instruction.md:7` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content (other than packages) | No runtime fetch | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies pinned with == | `pytest==9.0.3`, `pytest-json-ctrf==0.5.0` | `environment/Dockerfile:15-17` |
| 15 | CHECK | Base Docker image pinned by digest | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | All COPY from build context | `environment/Dockerfile:25-34` |
| 17 | CHECK | Environment has no ground-truth answers | Intentional bugs are scaffold, not leaked solution | `environment/internal/parse/reader.go` |
| 18 | CHECK | No dangerous Docker operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter reserved mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:14-17`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | `./scripts/terminus oracle` → reward 1.0 | oracle run 2026-06-29 |
| 22 | CHECK | Oracle does not require internet | Patch + `go build` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective (not hardcoded output) | Copies corrected source patches, rebuilds binary | `solution/solve.sh:8-18` |
| 24 | CHECK | test.sh writes reward.txt on pass and fail | Canonical reward block | `tests/test.sh:7-8,36-40` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only (0 or 1) | `echo 0` / `echo 1` | `tests/test.sh:36-40` |
| 27 | CHECK | Tests aligned with instructions | No phantom requirements; minor validate+TB3 coverage gap only | §5 |
| 28 | CHECK | Tests check correctness | Reference `_reference_normalize` comparisons | `tests/test_outputs.py:43-101` |
| 29 | CHECK | Tests verify behavior not implementation | CLI/subprocess behavioral checks | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string matching | Semantic JSON/event comparisons | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 23 tests documented | `tests/test_outputs.py:141+` |
| 32 | CHECK | Rubric has ≥3 negative penalties | 6 negatives | `entire-report.txt:376-381` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All lines use ±1,2,3,5 | `entire-report.txt:366-381` |
| 34 | CHECK | Each rubric line: Agent …, ±N | 16 Agent lines, flat format | `entire-report.txt:366-381` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific GRSH/GRPL behaviors | `entire-report.txt:366-381` |
| 36 | CHECK | Rubric uses positive phrasing with negative scores for bad behavior | e.g. “Agent skips footer CRC…, -3” | `entire-report.txt:379` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path refs | `entire-report.txt:366-381` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:366-381` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP refs | `entire-report.txt:366-381` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary parent files | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both in task.toml | `task.toml:4-5` |
| 43 | CHECK | Other required metadata present | version, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, category applicable | data-processing, go, bash, replay tags fit | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 40% → medium; not a revision blocker | `task.toml:6`, `entire-report.txt:20-21` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | solution/ excluded via .dockerignore | `environment/.dockerignore:11-12` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Hidden fixtures copied at test runtime | `tests/test.sh:19-23` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst-model 40% ≤ 80% | `entire-report.txt:20-21` |
| 55 | CHECK | Task not too hard or unfair | Spec docs cover all tested behavior; oracle passes | §5, oracle run |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 11, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| GRSH magic/version/CRC rejection | `test_rejects_bad_magic_shard`, `test_rejects_corrupted_crc_shard`, `test_hidden_corrupted_footer_rejected` | covered | `tests/test_outputs.py:206-213,325-333`; `replay-format.md:27` |
| Drift subtraction (tick = raw − drift_ms, floor 0) | `test_normalize_drift_subtraction`, `test_hidden_cross_shard_drift_and_dup` | covered | `tests/test_outputs.py:181-187,297-309`; `drift-policy.md` |
| Sort (tick, seq) then dedup first read-order | `test_normalize_out_of_order_seq`, `test_normalize_duplicate_frames_deduped` | covered | `tests/test_outputs.py:159-179`; `chronicle-schema.md:26-27` |
| Integrity SHA-256 digest | `test_validate_accepts_good_chronicle`, `test_validate_rejects_tampered_integrity` | covered | `tests/test_outputs.py:189-204`; `chronicle-schema.md:37-47` |
| shards metadata sorted by shard_id, wire keys | `test_multi_shard_sort_by_shard_id_in_meta`, `test_normalize_basic_two_shards` | covered | `tests/test_outputs.py:141-157,368-380`; `chronicle-schema.md:14-19` |
| normalize + validate CLI | `test_validate_*`, `test_normalize_*` | covered | `tests/test_outputs.py` |
| GRPL pack/unpack round-trip | `test_pack_unpack_roundtrip`, `test_hidden_pack_roundtrip_integrity` | covered | `tests/test_outputs.py:238-248,335-344` |
| GRPL header CRC enforcement | `test_pack_header_crc_enforced_on_unpack`, `test_unpack_rejects_bad_magic` | covered | `tests/test_outputs.py:250-273` |
| TB3_FIXTURE_ROOT for normalize | `test_hidden_tb3_fixture_root_override` | covered | `tests/test_outputs.py:311-323`; `instruction.md:5` |
| TB3_FIXTURE_ROOT for validate | — | gap | `instruction.md:5`; scaffold in `main.go:66-67` but no test |
| normalize exits non-zero on invalid shard | `test_rejects_*`, `test_hidden_corrupted_footer_rejected` | covered | `tests/test_outputs.py:206-213,325-333` |
| Staging buffer before export | `test_staging_snapshot_matches_export` | covered | `tests/test_outputs.py:289-295` |
| Same-tick distinct seq preserved | `test_hidden_same_tick_different_seq_preserved` | covered | `tests/test_outputs.py:346-354` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #5, #7, #10, #11, §5 TB3 gap |
| `task.toml` | #43, #44, #45, #46-49 N/A |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/.dockerignore` | #51 |
| `environment/docs/replay-format.md` | §5 CRC rejection, claim 2 |
| `environment/docs/chronicle-schema.md` | §5 sort/dedup/integrity |
| `environment/cmd/replay-chronicle/main.go` | §5 TB3 validate scaffold |
| `environment/internal/parse/reader.go` | #17, claim 5 (intentional bugs) |
| `tests/test.sh` | #20, #24, #52 |
| `tests/test_outputs.py` | #27-31, §5 all tests |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | §3, §7 agent stats, §4 rubric #32-39 |
| `docs/guidelines/dockerfxile.md` | claim 4, claim 6 |
| `docs/guidelines/rubrics.md` | claim 14 rubric format |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: game-replay-chronicle-normalizer/ ===
Summary: 0 error(s), 24 warning(s), 2 info
```

Warnings are stale docstring hits (all tests now have docstrings) and multiline pip false positive.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | worst model |
| oracle | 100.0% (3/3) | local oracle 1/1 pass |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; name matches report |
| 1 Instruction | ☑ | Concise; normative docs referenced; #11 minor slug leak |
| 2 Environment | ☑ | Canonical golang digest; tmux/asciinema; pinned deps |
| 3 Oracle | ☑ | Passes; patch-based rebuild |
| 4 Verifiers | ☑ | 23 behavioral tests; hidden fixtures; reference impl |
| 5 Metadata | ☑ | allow_internet=false; category fits; #45 tier note |
| 6 Rubric | ☑ | Flat non-milestone format; 35/+ pts; 6 negatives |
| 7 LLMaJ & agent evidence | ☑ | Claude 40% supports medium/hard band; no >80% reject |
| 8 Novelty & fairness | ☑ | Multi-file binary debugging; anti-cheat via hidden fixtures |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The four normative spec docs, hidden verifier fixtures, and reference-based tests give agents a fair but challenging debugging surface across Go and Bash. Oracle passes cleanly, the Dockerfile uses the canonical pinned Go base with offline pytest deps, and the platform rubric is correctly formatted as a flat non-milestone list with solid negatives. I didn’t find any blocking spec-test gaps. Optional polish: rename the rebuild script reference so the task folder slug isn’t in `instruction.md`, consider calibrating difficulty to medium given the 40% worst-model rate, and optionally add an explicit “reject invalid shards with non-zero exit” sentence plus a validate+TB3_FIXTURE_ROOT test.

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

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review game-replay-chronicle-normalizer/ --report entire-report.txt`._
