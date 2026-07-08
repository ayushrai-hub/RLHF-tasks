# Terminus Review Report: `columnar-encoding-correctness-validator`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3; local Docker unavailable) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Prior reviewer blockers are resolved: partial `decoded_row_count` behavior is documented, per-segment fault answer maps are removed from agent-visible specs, and `jobs/` / `.ruff_cache` are absent. Dockerfile deps are digest- and version-pinned, verifier is strong, oracle passes on platform, worst-model rate is 60%, and the flat non-milestone rubric (25 positive pts) is compliant. No High- or Medium-severity blockers remain.

**Insights (concise):**

- `REPORT_SPEC.md:49-57` now explicitly documents partial decode counts; prior reviewer item 1 is fixed.
- `REPORT_SPEC.md:101-113` lists fault codes only — no per-segment fixture→fault map; prior reviewer item 2 is fixed.
- Task tree has no `jobs/` or `.ruff_cache`; `.dockerignore:7,16` excludes them; prior reviewer item 3 is fixed.
- Automated audit #14 and #39 are false positives on manual re-read (pip `==` pins present; rubric “oracle constants” is anti-cheat wording).
- Platform rubric is a flat `Agent …, ±N` list (not milestone `# Rubric N` blocks); 25 positive pts ≤ 40 cap.
- `SCHEMA_EVOLUTION_GAP` trigger is inferable from `segment_13.json` + `schema_version` but not fully normative in spec — informational only; agents at 60–100% still pass.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: No High severity; prior blockers fixed (partial decode, answer map, artifacts) | Agree | `REPORT_SPEC.md:57`; no fixture→fault table in spec; no `jobs/`/`.ruff_cache` in task tree |
| 2 | ChatGPT: Medium none; verifier aligned, oracle passes | Agree | `tests/test_outputs.py` 15 tests; `entire-report.txt:26` oracle 100% (3/3) |
| 3 | ChatGPT: Flat non-milestone rubric acceptable; 25 pts | Agree | `entire-report.txt:339-356` flat list, no `# Rubric 2+`; `./scripts/terminus rubric-points` → 25 |
| 4 | ChatGPT: Accept recommendation | Agree | No artifact-backed High/Medium blockers after manual audit |
| 5 | ChatGPT: Dockerfile digest-pinned Go base OK | Agree | `environment/Dockerfile:2` `@sha256:1a6d4452…` |
| 6 | Prior reviewer #1: Clarify partial `decoded_row_count` | Agree (fixed) | `REPORT_SPEC.md:57` “Partial decode counts are expected…” |
| 7 | Prior reviewer #2: Remove per-segment fault answer map from agent docs | Agree (fixed) | `REPORT_SPEC.md:101-108` names only; signatures live in `tests/test_outputs.py:52-71` |
| 8 | Prior reviewer #3: Remove `jobs/`, `.ruff_cache` from ZIP | Agree (fixed) | `find` empty; `.dockerignore:7,16` |
| 9 | `entire-report.txt` instruction sufficiency: `SCHEMA_EVOLUTION_GAP` suppresses `STATS_DRIFT` undocumented | Partially agree | `segment_13.json` has `schema_version:2`, stats only for column `a`; test expects `["SCHEMA_EVOLUTION_GAP"]` only (`test_outputs.py:247`). Spec does not spell mutual exclusivity, but `STATS_DRIFT` naturally applies only to columns present in `statistics` (`solution/reconcile.go:106-114`). Low/informational — not a Revise blocker at 60% worst-model. |
| 10 | Harbor review: non-canonical Go base image | Disagree as blocker | Digest-pinned `golang:1.24-bookworm`; no canonical Go image required; acceptable per `docs/guidelines/dockerfile.md` |
| 11 | Harbor review: instruction brevity warning | Disagree as blocker | `instruction.md` points to normative `REPORT_SPEC.md` / `SEGMENT_FORMAT.md`; advisory only |
| 12 | Test quality review: weak `COLUMNAR_FIXTURE_DIR` post-condition | Disagree as blocker | `test_outputs.py:291-331` asserts 20 segments, excludes `segment_99`; fingerprint test covers default path; suggestion only |
| 13 | Automated audit #14: unpinned pip | Disagree | `environment/Dockerfile:18-20` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `pyyaml==6.0.2` |
| 14 | Automated audit #39: rubric mentions oracle | Disagree | `entire-report.txt:351` “verifier oracle constants” = anti-cheat fingerprint wording, not oracle/NOP run criteria |
| 15 | Automated audit #41: stray `audit-report.md` | Disagree as submission issue | Reviewer-generated artifact; not in author submission; no `jobs/`, `README.md`, or dev notes in task tree |
| 16 | Automated audit #27: phantom thresholds 4, 18, 20 | Disagree | `instruction.md:1` “twenty bundled”; `203-204` asserts derived summary counts after reconciliation — not independent phantom requirements |
| 17 | LLMaJ `behavior_in_*` all pass | Agree | Cross-checked instruction ↔ tests ↔ `REPORT_SPEC.md` / `SEGMENT_FORMAT.md` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 prose blocks, ~103 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineering brief, not synthetic spec | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States deliverable + spec refs, not build walkthrough | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | WHAT to build; normative detail in `/app/spec/` | `instruction.md` |
| 6 | CHECK | No design-doc tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, output file, encodings, fault families named | `instruction.md:1-5` |
| 8 | CHECK | Interesting | Realistic columnar storage / encoding validation scenario | task content |
| 9 | CHECK | Unique | No duplicate signal in repo; corpus check N/A from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task slug in body | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Static COPY build | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip `==` versions | All three packages pinned | `environment/Dockerfile:18-20` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:2` |
| 16 | CHECK | Env context self-contained | COPY only from `environment/` | `environment/Dockerfile:26-35` |
| 17 | CHECK | No ground truth in environment | Specs define rules, not per-segment answers | `environment/spec/REPORT_SPEC.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No `docker-compose.yaml` | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:17-20`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3); local Docker daemon unavailable | `entire-report.txt:26` |
| 22 | CHECK | Oracle no internet | `solve.sh` copies, builds, runs locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Full `reconcile.go` compile + validator execution | `solution/solve.sh:7-16` |
| 24 | CHECK | test.sh reward.txt + failure path | Writes 0/1; mkdir verifier | `tests/test.sh:6,18-22` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:18-22` |
| 27 | CHECK | Tests aligned with instructions | All assertions trace to `instruction.md` + `REPORT_SPEC.md` + `SEGMENT_FORMAT.md` | §5 below |
| 28 | CHECK | Tests check correctness | Fault signatures, fingerprint, determinism, schema | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Runs binary; anti-cheat is constant-presence only | `tests/test_outputs.py:99-131` |
| 30 | CHECK | Not brittle where flexible works | Fingerprint appropriate for deterministic JSON contract | `REPORT_SPEC.md:4` |
| 31 | CHECK | Informative test docstrings | All 15 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 8 negatives | `entire-report.txt:349-356` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | All lines valid | `entire-report.txt:339-356` |
| 34 | CHECK | `Agent …, ±N` format | 18 Agent lines | `entire-report.txt:339-356` |
| 35 | CHECK | Rubric detailed; positive ≤40 | 25 positive pts | `rubric-points` output |
| 36 | CHECK | Positive-language rubric | No `Agent does not …, +N` | `entire-report.txt:339-356` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:339-356` |
| 38 | CHECK | Rubric no instruction.md/task.toml refs | None | `entire-report.txt:339-356` |
| 39 | CHECK | Rubric no oracle/NOP run refs | “oracle constants” = embedded fingerprint anti-cheat, not run grading | `entire-report.txt:351` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | No unnecessary parent files | No jobs/, README, dev notes in submission | task tree; `.dockerignore:16` |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | Complete | `task.toml` |
| 44 | CHECK | Tags/category/language match | `go`, `bash`, `data-processing`, columnar tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; platform `medium`; mismatch not a blocker | `task.toml:6`, `entire-report.txt:16` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone-scoped tests | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | `.dockerignore:18`; no COPY tests | `environment/.dockerignore`, `Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore:17` excludes `solution/` | `environment/.dockerignore` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Fixture SHA256 locks + instruction forbids edits | `tests/test_outputs.py:148-157`, `instruction.md:3` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:21-22` |
| 55 | CHECK | Not too hard/unfair | Specs shipped; Go in image; 60–100% agent success | `entire-report.txt:20-22` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Implement `reconcile.go`; stub must be replaced | `prepare_verifier_artifacts` | covered | `test_outputs.py:101-102` |
| `make build`; binary > 2048 bytes | `prepare_verifier_artifacts` | covered | `test_outputs.py:104-117`, `instruction.md:1` |
| Output `/app/output/encoding_integrity_report.json` | all tests via `_load_report` | covered | `test_outputs.py:14`, `instruction.md:3` |
| REPORT_SPEC schema + key order + trailing newline | `test_report_schema_key_order_and_trailing_newline` | covered | `test_outputs.py:172-183`, `REPORT_SPEC.md:17-27` |
| Twenty fixtures immutable | `test_bundled_fixtures_immutable_and_complete` | covered | `test_outputs.py:148-157` |
| Do not modify spec/rules | `test_shipped_docs_and_policy_immutable` | covered | `test_outputs.py:160-169` |
| No embedded checksum/fingerprint in Go | `test_shipped_docs_and_policy_immutable` | covered | `test_outputs.py:168-169` |
| Five encodings + integrity checks | fault-signature tests + fingerprint | covered | `test_outputs.py:219-271` |
| Partial `decoded_row_count` | `test_dictionary_and_rle_fault_signatures` | covered | `REPORT_SPEC.md:57`, `test_outputs.py:224-225` |
| `COLUMNAR_FIXTURE_DIR` override | `test_deterministic_reruns_and_columnar_fixture_dir_isolation` | covered | `test_outputs.py:291-331`, `instruction.md:3` |
| Ignore extra `segment_*.json` beyond 01–20 | isolation test | covered | `REPORT_SPEC.md:44-45`, `test_outputs.py:329-331` |
| Deterministic byte-identical reruns | isolation test | covered | `REPORT_SPEC.md:4`, `test_outputs.py:293-294` |
| Summary counts reconcile | `test_summary_counts_reconcile_with_segment_rows` | covered | `test_outputs.py:186-204`, `REPORT_SPEC.md:40` |
| Clean segments empty `fault_codes` | `test_clean_segments_pass_without_null_fault_lists` | covered | `test_outputs.py:207-216`, `REPORT_SPEC.md:27` |
| Per-segment fault signatures (16 codes) | grouped signature tests + fingerprint | covered | `test_outputs.py:219-271`, `285-288` |
| `SCHEMA_EVOLUTION_GAP` on evolved schema missing stats | `test_decode_divergence_and_schema_evolution` | covered | `test_outputs.py:243-249`, `segment_13.json` |
| Segment order segment_01–segment_20 | `test_segment_order_and_ids_match_fixture_basenames` | covered | `test_outputs.py:274-282` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, §5 |
| `task.toml` | #42-45, #46-49 N/A |
| `environment/Dockerfile` | #13-16, #20, #50 |
| `environment/.dockerignore` | #41, #50-51 |
| `environment/spec/REPORT_SPEC.md` | §3 claims 6-7, §5, prior reviewer fixes |
| `environment/spec/SEGMENT_FORMAT.md` | §5 encoding rules |
| `environment/rules/encoding_policy.yaml` | §5 policy rules |
| `environment/fixtures/segment_13.json` | §3 claim 9 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | §5 all tests, anti-cheat |
| `solution/solve.sh` | #21-23 |
| `solution/reconcile.go` | #23 oracle logic |
| `entire-report.txt` | §3, §7 agent stats, platform rubric |
| `audit-report.md` | §3 automated false positives |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate columnar-encoding-correctness-validator/
=== Terminus Validation: columnar-encoding-correctness-validator/ ===
Summary: 0 error(s), 1 warning(s), 1 info
INFO: submission-diversity — non-milestone not blocked
WARNING: pinned_dependencies — false positive on pip line continuation (packages use ==)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | best model |
| oracle | 100.0% (3/3) | platform |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

### Rubric (non-milestone format check)

| Check | Result | Proof |
|-------|--------|-------|
| Flat `Agent …, ±N` list (no `# Rubric 2+`) | PASS | `entire-report.txt:339-356` |
| `rubric-validate --milestones 0` | PASS | 0 errors |
| Positive point total | 25 / 40 cap | `./scripts/terminus rubric-points` |
| Negative count | 8 (≥3) | `entire-report.txt:349-356` |
| Milestone rubric headers misused | No | `number_of_milestones = 0`; no per-milestone blocks |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular layout; Go/bash data-processing |
| 1 Instruction | ☑ | Concise; spec-backed; prior brevity warning advisory only |
| 2 Environment | ☑ | Digest-pinned Go; tmux+asciinema; `allow_internet=false`; no tests/solution COPY |
| 3 Oracle | ☑ | Platform pass; solve.sh builds real binary |
| 4 Verifiers | ☑ | 15 behavior tests; reward 0/1; no runtime installs |
| 5 Metadata | ☑ | Complete; milestone count 0 |
| 6 Rubric | ☑ | Flat non-milestone format; 25 pts; 8 negatives |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated in §3; SCHEMA_EVOLUTION note informational |
| 8 Novelty & fairness | ☑ | Multi-encoding reconciler; anti-cheat strong |
| 9 Long context | ☐ N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on the revision — the partial decode rules in REPORT_SPEC read clearly now, and pulling the per-segment fault map out of the agent-visible docs was the right call. The environment is solid (pinned Go base, offline, strong fixture checksums and fingerprint checks), the oracle passes, and agent rates look right for medium difficulty. The rubric is in the correct flat format for a non-milestone task. I didn’t find any blockers on this pass.

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
