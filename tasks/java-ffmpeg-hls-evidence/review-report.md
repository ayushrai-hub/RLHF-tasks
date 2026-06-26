# Terminus Review Report: `java-ffmpeg-hls-evidence`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (per `entire-report.txt`; local oracle CLI not runnable) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Test Dependency Location, Task Difficulty, Metadata Issues, Test Alignment/Coverage Issues

**Decision (concise):** ChatGPT’s Accept verdict is not supported by artifacts. Three High blockers remain: all three `test.sh` files run `pip install` at verifier runtime (wheels are only downloaded at build, not installed into the image); `task.toml` still declares `difficulty = "hard"` while worst-model pass rate is 60% (medium tier); and milestone `task.toml` illegally includes top-level `[agent]` / `[verifier]` sections (validate ERROR). Prior-revision claims (`medium` difficulty, `/opt/test-venv`, baked `_pristine_config.json`, `decision=deny` on `test_remux_missing_segments`) are not true in the current tree.

**Insights (concise):**

- Cryptographic anti-cheat (build-time master key, HMAC re-derivation in tests) and milestone structure are strong; oracle/solution quality is high.
- Agent stats (GPT-5.5 60%, Claude 80%, worst 60%) support **medium** tier, not hard; task is not too easy (#54 passes at 60% worst).
- `test_remux_missing_segments` still omits the instructed `decision=deny` audit assertion (M2 deny path is covered elsewhere).
- `_pristine_config.json` is created by the test fixture at runtime, not baked in the Dockerfile.
- External report’s recommendation to *add* top-level `[agent]`/`[verifier]` contradicts `validate_task.py` (milestone tasks must use per-step sections only).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Dependency Location | #20 | All milestone `test.sh` scripts run `pip install` at verifier runtime | `steps/milestone_1/tests/test.sh:9-10`, `steps/milestone_2/tests/test.sh:9-10`, `steps/milestone_3/tests/test.sh:9-10`; `environment/Dockerfile:22-30` only `pip download`s wheels to `/opt/test-wheels`, no venv install | `RUN python3 -m venv /opt/test-venv && /opt/test-venv/bin/pip install ...` in Dockerfile; `test.sh` activates venv only — no `pip install` |
| 2 | High | Task Difficulty | #45 | Declared `hard` but observed worst-model 60% → medium tier | `task.toml:7` `difficulty = "hard"`; `entire-report.txt:6-11` GPT 60%, Claude 80%, classified MEDIUM | Set `difficulty = "medium"` or rebalance until worst-model ≤20% |
| 3 | High | Metadata Issues | #43 | Milestone task has forbidden top-level `[agent]` and `[verifier]` | `task.toml:25-29`; `./scripts/terminus validate` ERROR | Remove lines 25–29; keep only `[steps.agent]` / `[steps.verifier]` per milestone |
| 4 | Medium | Test Alignment/Coverage Issues | #27 | `remux` missing-segments path requires `decision=deny` audit row; test does not assert it | `steps/milestone_3/instruction.md:5`; `steps/milestone_3/tests/test_m3.py:132-146` checks exit 1 + `missing_segments` only | Add SQL assertion for `action='remux'`, `decision='deny'` after failed remux (mirror `test_deny_row_written_on_tampered_sig` in M2) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept; prior revision items addressed | **Disagree** | `task.toml:7` still `hard`; `test.sh` still `pip install`; blockers 1–3 above |
| 2 | ChatGPT: `difficulty = "medium"` matching evaluation | **Disagree** | `task.toml:7` `difficulty = "hard"` |
| 3 | ChatGPT / prior feedback: Python deps in `/opt/test-venv` at image build | **Disagree** | No `/opt/test-venv` in `environment/Dockerfile`; wheels at `/opt/test-wheels` only; runtime `pip install` in `test.sh` |
| 4 | ChatGPT / prior feedback: `_pristine_config.json` baked in image | **Disagree** | Not in `FixtureGen.java` or Dockerfile; `test_m1.py:66-68` creates at test runtime via `stash_pristine` fixture |
| 5 | ChatGPT / prior feedback: `test_remux_missing_segments` asserts `decision=deny` | **Disagree** | `test_m3.py:132-146` — no audit_log query for deny |
| 6 | `entire-report.txt` reviewer: difficulty metadata High blocker | **Agree** | `task.toml:7` vs `entire-report.txt:10-11` |
| 7 | `entire-report.txt` validate warning: add top-level `[agent]`/`[verifier]` | **Disagree** | `validate_task.py:246-258` forbids top-level sections on milestone tasks; current file has them (wrong) |
| 8 | `entire-report.txt` LLMaJ: behavior_in_tests PASS | **Agree** | Broad coverage across M1–M3; minor gaps only (deny on remux missing, `db` field, decrypt-all order) |
| 9 | `entire-report.txt` oracle 100% (3/3) | **Agree** | `entire-report.txt:15`; local `./scripts/terminus oracle` failed (Harbor config), jobs show prior oracle passes |
| 10 | `entire-report.txt` non-canonical Java base | **Partially agree** | `environment/Dockerfile:1` eclipse-temurin digest-pinned; justified for JDK — not a blocker |
| 11 | Test quality: `db` field in init response untested | **Agree** | `test_m1.py:104-106` asserts `status`, `seeded_keys` only; `steps/milestone_1/instruction.md:7` requires `db` key — Low/Medium gap |
| 12 | Test quality: decrypt-all segment order untested | **Agree** | `steps/milestone_2/instruction.md:7`; `test_m2.py` chain tests don't assert target order — Low/Medium |
| 13 | Test quality: ffmpeg argv not verified | **Agree** | `steps/milestone_3/instruction.md:5`; `test_m3.py:85-92` checks MP4 + SHA only — Low |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Per-milestone instructions are 4–5 short paragraphs; normative detail in `/app/docs/` | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Forensics scenario reads human; no LLM anti-patterns | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | `###` headers only; no tables/code fences | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step-by-step solve script | Numbered crypto flow is API contract, not build walkthrough | `steps/milestone_2/instruction.md:5` |
| 5 | CHECK | No hints/strategies | `javac` line is required interface spec | `steps/milestone_1/instruction.md:5` |
| 6 | CHECK | No design-doc I/O tables | No markdown tables; pipe chars are HMAC field separators | `steps/milestone_*/instruction.md` |
| 7 | CHECK | Well specified | Goals, paths, schemas in `/app/docs/` are testable | `environment/docs/API_SPEC.md` |
| 8 | CHECK | Interesting | Realistic security/forensics Java + crypto + ffmpeg pipeline | — |
| 9 | UNCHECK | Unique vs corpus | Not verified against TB2/TB3/Edition 1 | — |
| 10 | CHECK | Absolute paths only | `/app/...`, `/opt/...` throughout | `steps/milestone_1/instruction.md:3-7` |
| 11 | CHECK | Task name not in instruction | No `java-ffmpeg-hls-evidence` string | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string | None found | — |
| 13 | CHECK | No runtime web fetch in env | H2 jar fetched at build only | `environment/Dockerfile:33-36` |
| 14 | CHECK | Pinned pip versions | `pytest==8.4.1`, etc. in Dockerfile download | `environment/Dockerfile:27-30` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:25d12765...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY from `source/`, `docs/` only | `environment/Dockerfile` |
| 17 | CHECK | No solution in environment | No `solve.sh` in image; stubs only | `environment/Dockerfile:95-108` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose.yaml | — |
| 20 | UNCHECK | Verifier deps baked; no runtime install | `pip install` in all three `test.sh` | `steps/milestone_1/tests/test.sh:9-10` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:15` |
| 22 | CHECK | Oracle no runtime downloads | solve scripts compile Java only | `steps/milestone_*/solution/solveN.sh` |
| 23 | CHECK | Oracle reflective implementation | Full Java crypto via heredocs + `javac` | `steps/milestone_1/solution/solve1.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir + pytest + 0/1 reward | `steps/milestone_1/tests/test.sh:1-21` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `steps/milestone_*/tests/test_*.py` |
| 26 | CHECK | Binary rewards only | `echo 0` / `echo 1` only | `steps/milestone_1/tests/test.sh:17-20` |
| 27 | CHECK | Tests aligned with instructions | One Medium gap: remux deny audit | `test_m3.py:132-146` |
| 28 | CHECK | Tests check correctness | SHA-256, HMAC re-derivation, SQL state | `test_m2.py`, `test_m3.py` |
| 29 | CHECK | Behavior not implementation grep | CLI subprocess + JDBC only | `test_m1.py:30-34` |
| 30 | CHECK | No brittle exact strings | Crypto hashes + structured JSON | `test_m2.py` |
| 31 | CHECK | Informative names or docstrings | Names like `test_init_rejects_tampered_signature`; module docstrings | `test_m1.py:1-8`, `test_m1.py:152` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no `rubric.txt` in task folder (platform UI only) | — |
| 33 | UNCHECK | Rubric valid scores | N/A | — |
| 34 | UNCHECK | Rubric Agent format | N/A | — |
| 35 | UNCHECK | Rubric detailed criteria | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Milestone layout complete | `steps/milestone_*/` |
| 41 | UNCHECK | Clean parent directory | `jobs/` artifact dir present | `tasks/java-ffmpeg-hls-evidence/jobs/` |
| 42 | CHECK | author_name/email | Present | `task.toml:5-6` |
| 43 | UNCHECK | Required metadata fields | Forbidden top-level `[agent]`/`[verifier]` on milestone task | `task.toml:25-29` |
| 44 | CHECK | Tags/languages/category match | `java`, `security`, `db_interaction` | `task.toml:8-13` |
| 45 | UNCHECK | Difficulty matches pass rates | `hard` vs 60% worst → medium | `task.toml:7`, `entire-report.txt:10-11` |
| 46 | CHECK | steps/ milestone layout | 3 milestones, no root tests/solution | `steps/milestone_{1,2,3}/` |
| 47 | CHECK | solveN.sh per milestone | `solve1.sh`, `solve2.sh`, `solve3.sh` | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | `test_m1.py`, `test_m2.py`, `test_m3.py` | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone-scoped tests | Each file tests only its milestone surface | `test_m2.py` header |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground-truth cheat | Random master key; HMAC must be computed | `environment/Dockerfile:43-45` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Encrypted segments + HMAC signatures | `test_m1.py:152-170` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:10-11` |
| 55 | CHECK | Not too hard/unfair | Failures are integration/build wiring, not spec gaps | `entire-report.txt:121-124` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 42, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 20, 32, 33, 34, 35, 36, 37, 38, 39, 41, 43, 45 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1 `init` creates 4 tables + seeds wrapped keys | `test_init_creates_four_tables`, `test_seeded_wrapped_keys_match_json` | covered | `test_m1.py:122-143` |
| M1 `init` rejects tampered `sig_hex` | `test_init_rejects_tampered_signature` | covered | `test_m1.py:152-170` |
| M1 `init` body includes `db` path | — | gap | `instruction.md:7` vs `test_m1.py:104-106` |
| M1 `recover-config` repairs 5 fields | `test_repair_writes_all_corrections`, `test_repair_file_matches_expected` | covered | `test_m1.py:177-197` |
| M2 decrypt + audit chain HMAC | `test_audit_chain_entry_hash_recomputes`, `test_deny_row_written_on_tampered_sig` | covered | `test_m2.py:191-253` |
| M2 `decrypt-all` in segment_index order | — | gap | `instruction.md:7`; no target-order assert |
| M3 remux MP4 + SHA-256 + artifact row | `test_remux_sha_matches_file_bytes`, `test_remux_inserts_artifact_row` | covered | `test_m3.py:99-109` |
| M3 remux missing segments → deny audit | `test_remux_missing_segments` | gap | `instruction.md:5` vs `test_m3.py:132-146` |
| M3 six validator rules × 4 cases | `TestValidators*` parametrized classes | covered | `test_m3.py:232+` |
| M3 scratch-path chain immutability | `test_invalid_byte_range_leaves_cam001_chain_unchanged` | covered | `test_m3.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #43, #45, blockers 2–3 |
| `environment/Dockerfile` | #14, #15, #20, blocker 1 |
| `steps/milestone_*/tests/test.sh` | #20, blocker 1 |
| `steps/milestone_3/instruction.md` | blocker 4, spec gap |
| `steps/milestone_3/tests/test_m3.py` | blocker 4, #27 |
| `steps/milestone_1/tests/test_m1.py` | #31, `_pristine_config` adjudication |
| `entire-report.txt` | #21, #45, #54, agent stats |
| `scripts/validate_task.py` | #43 adjudication claim 7 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate tasks/java-ffmpeg-hls-evidence/
Summary: 5 error(s), 47 warning(s)
ERROR: task.toml — Milestone tasks must not have top-level [agent]
ERROR: task.toml — Milestone tasks must not have top-level [verifier]
ERROR: test.sh (×3) — Runtime network install not allowed: pip install
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | `entire-report.txt:11` |
| terminus-claude-opus-4-8 | 80.0% (4/5) | `entire-report.txt:10` |
| oracle | 100.0% (3/3) | `entire-report.txt:15` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `java-ffmpeg-hls-evidence` matches report; 3-milestone Java security task |
| 1 Instruction | ☑ | Per-milestone instructions + `/app/docs/` dossier |
| 2 Environment | ☑ | Digest-pinned JDK, tmux/asciinema, offline wheels — but not installed |
| 3 Oracle | ☑ | solve1/2/3.sh implement real Java crypto |
| 4 Verifiers | ☑ | Strong behavior tests; runtime pip + one deny gap |
| 5 Metadata | ☑ | difficulty + milestone toml structure fail |
| 6 Rubric | ☑ | N/A in repo (platform UI content in report only) |
| 7 LLMaJ & agent evidence | ☑ | Cross-checked `entire-report.txt` vs files |
| 8 Novelty & fairness | ☑ | Multi-step, fair failures |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Verifier hygiene is not fixed: all three `test.sh` files still run `pip install` at runtime (wheels are only downloaded in the Dockerfile, not installed into a build-time venv). `task.toml` still lists `difficulty = "hard"` while worst-model pass rate is 60% (medium tier). Remove the forbidden top-level `[agent]` and `[verifier]` blocks from milestone `task.toml` (per-step timeouts are already present). Also add a `decision=deny` audit assertion to `test_remux_missing_segments`. ChatGPT Accept and prior-revision claims are not reflected in the current artifacts.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Dependency Location | yes | 1 |
| Task Difficulty | yes | 2 |
| Metadata Issues | yes | 3 |
| Test Alignment/Coverage Issues | yes (Medium) | 4 |
| Instruction Styling | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
