# Terminus Review Report: `twamp-owd-marginalia2`

**Generated:** 2026-06-21 (manual re-audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/twamp-owd-marginalia2`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Exposing Hints/Answers, Environment

**Decision (concise):** Strong hard-tier debugging task with thorough verifiers, canonical digest-pinned Go base, and correct `difficulty = hard` (GPT-5.5 20% worst-model). One High blocker remains: agent-visible spec pages under `environment/app/` leak verifier infrastructure — `/tests/fixtures/alt_data/`, pytest references, and B-series test labels. Rewrite those as operator requirements. The ChatGPT/base-image claim and automated #14/#45 blockers are false positives on re-audit.

**Insights (concise):**

- `golang:1.24-bookworm@sha256:1a6d4452…` matches the sanctioned list in `scripts/validate_task.py` and `docs/guidelines/dockerfxile.md` — not a blocker.
- Pip packages are pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); validate warning is a multiline `pip install` false positive.
- Worst-model rate is GPT-5.5 at 20% (1/5) → hard tier; `task.toml` `difficulty = "hard"` is correct.
- Spec↔test alignment is strong; zero-emit and numeric-suffix ordering live in `verdict_ladder/` dossier pages referenced by `instruction.md`.
- Two tests grep Go source (`test_loader_no_float_fallback`, `test_digest_separator_correct`); digest pins make spoofing impractical but #29 stays unchecked.
- `environment/Dockerfile.pre-canonical-bak` is repo clutter only (not copied into image).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Exposing Hints/Answers, Environment | #17 (adjacent) | Agent-visible docs reference verifier paths, pytest, and test-series labels | `environment/app/run_recipe/build_targets.md:22-23,38`; `environment/app/run_recipe/output_exclusivity.md:43-51`; `environment/app/verdict_ladder/zero_emit_invariants.txt:5`; `environment/app/verdict_ladder/enum_set.md:35`; `environment/app/digest_workshop/worked_example.md:47-56`; `environment/app/BRIEFING.md:42` | Rewrite as normal operator/spec language: describe alt-data override via env vars without `/tests/` paths; replace B1–B5 labels with plain determinism requirements; remove "verifier"/"pytest" references |

*No other High-severity blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-sanctioned Go runtime base without exemption (ChatGPT / entire-report L1) | **Disagree** | `environment/Dockerfile:1` uses `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` — exact match in `scripts/validate_task.py:67` CANONICAL_BASE_IMAGES and `docs/guidelines/dockerfxile.md:11` |
| 2 | Agent docs leak `/tests/fixtures/alt_data/` and verifier re-run details (ChatGPT / entire-report L1) | **Agree** | `environment/app/run_recipe/build_targets.md:22-23`: "The verifier uses these to re-invoke the binary against the alt fixture under `/tests/fixtures/alt_data/`" |
| 3 | `output_exclusivity.md` names B-series planted cleanup checks (ChatGPT) | **Agree** | `environment/app/run_recipe/output_exclusivity.md:43-51`: labels `B1` idempotency, `B2` exclusivity, `B3` stale removal, `B4` clean build, `B5` module-aware |
| 4 | Update difficulty hard → medium (entire-report portal feedback L334, auto-review #45) | **Disagree** | `entire-report.txt:4-9`: GPT-5.5 20% (1/5), Claude 60%; worst-model 20% → hard per `docs/reviewer-checklist-ui.md:52-57`; `task.toml:6` `difficulty = "hard"` matches |
| 5 | Use golang:1.21-bookworm (portal feedback L335) | **Disagree** | Stale reference; active `environment/Dockerfile:1` is `golang:1.24-bookworm`; backup at `environment/Dockerfile.pre-canonical-bak:1` is not used |
| 6 | Remove API_REFERENCE.md / OPERATIONS.md verifier leaks (portal feedback L335) | **Partially agree** | Those filenames absent; equivalent leaks exist in `build_targets.md`, `output_exclusivity.md`, `zero_emit_invariants.txt`, `enum_set.md`, `worked_example.md` |
| 7 | Unpinned pip dependencies (#14 auto-blocker) | **Disagree** | `environment/Dockerfile:16-18`: `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` — validator flags first line of multiline RUN only |
| 8 | Instruction sufficiency fail for zero-emit / numeric-suffix (entire-report L79-147) | **Partially agree** | Requirements exist in `verdict_ladder/zero_emit_invariants.txt`, `enum_set.md`, `allocator_pages/tiebreak_direction.md`; discoverability is weak but spec-complete — not a High blocker |
| 9 | Leftover backup Dockerfile (entire-report L210-228) | **Agree (Low)** | `environment/Dockerfile.pre-canonical-bak` present; not COPY'd into image (`environment/Dockerfile:22` copies `app/` only) — cosmetic cleanup |
| 10 | Test quality robust / ACCEPT (entire-report L287-329) | **Agree** | 54 tests cover primary + alt fixtures, anti-cheat digests, dynamic mutation; behavior_in_tests PASS in report |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Three short paragraphs, ~198 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer handoff tone, no spec headers | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no tables/headers in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States goal and paths, not a fix script | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Instruction names outputs/rules; dossier is normative spec for debugging task | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Paths, binary, build command, key behavioral rules stated | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic TWAMP OWD forensics debugging | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | TWAMP/RFC5357 distributed-spec Go debug pattern; no duplicate found in repo | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No "twamp-owd-marginalia2" string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Offline Go build (`GOPROXY=off`); no runtime fetch | `environment/Dockerfile:29-31,86` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Both packages pinned on continuation lines | `environment/Dockerfile:16-18` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Full digest on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY app/ /app/` only | `environment/Dockerfile:22` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Buggy source is intentional setup; no report digests or oracle output in env | `environment/app/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:16-18`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed locally (Harbor blocked) | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | Static file overwrites + `make build`; GOPROXY=off | `solution/solve.sh:1-35` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Overwrites six Go packages with corrected logic, rebuilds, runs binary | `solution/solve.sh:37+` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Defaults 0, writes 1/0 after pytest | `tests/test.sh:4-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py`, `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary reward block | `tests/test.sh:16-19` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Every assertion traces to instruction + linked dossier pages | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Exact counts, OWD values, cascade thresholds, digests | `tests/test_outputs.py` |
| 29 | UNCHECK | Tests verify behavior, not implementation (no grepping source code) | `test_loader_no_float_fallback`, `test_digest_separator_correct` read `.go` source | `tests/test_outputs.py:608-619` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact JSON/digest pins intentional for deterministic auditor task | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 54 tests documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Only standard task layout (+ `.pre-canonical-bak` in environment/) | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | go/bash debugging TWAMP task | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | hard declared; worst-model 20% → hard | `task.toml:6`, `entire-report.txt:4-9` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not copied; digests only in tests | `environment/Dockerfile:22` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Input tree digests + dynamic mutation test | `tests/test_outputs.py:151-157,575-603` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% | `entire-report.txt:7-9` |
| 55 | CHECK | Task is not too hard or unfair | Agents reached 49–50/54; failures are spec-execution not missing info | `entire-report.txt:79-136` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 21, 29, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output at `/app/output/report.json`, binary `/app/bin/auditor` | `test_output_directory_exclusive`, `test_elf_magic` | covered | `instruction.md`; `tests/test_outputs.py:207-216` |
| Deterministic idempotent output | `test_idempotent_byte_identical` | covered | `instruction.md`; `tests/test_outputs.py:197-205` |
| Input tree immutable | `test_input_files_immutable_post_run`, digests | covered | `instruction.md`; `tests/test_outputs.py:151-157,240-245` |
| Output exclusivity (only report.json) | `test_stale_file_removed`, `test_stale_directory_removed` | covered | `run_recipe/output_exclusivity.md`; `tests/test_outputs.py:213-228` |
| Canonical OWD formula | `test_p2_owd_anomaly_canonical`, `test_p6_owd_anomaly_after_cascade` | covered | `owd_fieldbook/formula.md`; `tests/test_outputs.py:388-427` |
| send_ts magnitude routing | `test_p3_magnitude_routing` | covered | `probe_intake/canonicalize.txt`; `tests/test_outputs.py:396-403` |
| Earliest record wins dedup | `test_p5_dedup_earliest_wins` | covered | `instruction.md`; `tests/test_outputs.py:412-419` |
| Cascade compounds / clean reset | `test_cycle_thresholds_cascade`, `test_p4_loss_detected` | covered | `cycle_journal/cascade_walk.md`; `tests/test_outputs.py:405-480` |
| Quiet-period mutes exactly one | `test_p12_quiet_suppressed` | covered | `cycle_journal/quiet_period_oneshot.md`; `tests/test_outputs.py:436-441` |
| Numeric-suffix sorting | `test_probes_sorted_by_numeric_suffix`, `test_jitter_share_numeric_suffix_order` | covered | `instruction.md`; `tests/test_outputs.py:306-313,535-547` |
| Closed seven-key by_verdict (zero emit) | `test_closed_enum_set`, `test_by_verdict_counts_exact` | covered | `verdict_ladder/enum_set.md`, `zero_emit_invariants.txt`; `tests/test_outputs.py:268-360` |
| Digest separator `\n##\n` | `test_report_digest_exact`, `test_digest_separator_correct` | covered | `digest_workshop/canonical_bytes.md`; `tests/test_outputs.py:321-327,615-619` |
| Alt tiebreak direction flip | `test_alt_descending_tiebreak`, `test_alt_report_digest` | covered | `allocator_pages/tiebreak_direction.md`; `tests/test_outputs.py:549-573` |
| Strict-int gating | `test_pr1_strict_int_reject`, `test_loader_no_float_fallback` | covered | `probe_intake/strict_int_table.md`; `tests/test_outputs.py:443-447,608-612` |
| Dynamic processing (not static blob) | `test_dynamic_mutation_changes_output` | covered | —; `tests/test_outputs.py:575-603` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, #7, §5 |
| `task.toml` | #42–45, #46–49 N/A |
| `environment/Dockerfile` | #13–20, blocker adjudication #1 |
| `environment/app/run_recipe/build_targets.md` | Blocker 1, adjudication #2 |
| `environment/app/run_recipe/output_exclusivity.md` | Blocker 1, adjudication #3 |
| `environment/app/verdict_ladder/` | Blocker 1, §5 zero-emit |
| `environment/app/digest_workshop/worked_example.md` | Blocker 1 |
| `environment/app/BRIEFING.md` | Blocker 1 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #25–31, §5 |
| `solution/solve.sh` | #22–23 |
| `scripts/validate_task.py` | Adjudication #1 (canonical base list) |
| `docs/guidelines/dockerfxile.md` | Adjudication #1 |
| `entire-report.txt` | §7 agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: twamp-owd-marginalia2/ ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — multiline pip false positive (packages ARE pinned)
INFO: milestone preference, test.sh trailing exit
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 1 timeout |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `twamp-owd-marginalia2`; regular layout; debugging/go |
| 1 Instruction | ☑ | Concise, absolute paths, dossier pointers |
| 2 Environment | ☑ | Canonical Go base; verifier leak in app docs → blocker |
| 3 Oracle | ☐ | Not executed; static review of solve.sh passes |
| 4 Verifiers | ☑ | 54 tests; reward block canonical; 2 source-grep tests |
| 5 Metadata | ☑ | difficulty hard correct |
| 6 Rubric | N/A | No rubric file in repo |
| 7 LLMaJ & agent evidence | ☑ | Report matches task; adjudicated all claims |
| 8 Novelty & fairness | ☑ | Multi-file Go debug; agents near 93% on best runs |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Verifiers, pinning, canonical Go base, and hard difficulty calibration (GPT-5.5 20%) all look solid. The remaining blocker is agent-visible dossier pages that leak verifier infrastructure: `build_targets.md` names `/tests/fixtures/alt_data/` and pytest; `output_exclusivity.md` uses B1–B5 test labels; several verdict/digest pages say "verifier." Rewrite those as normal operator requirements without `/tests/`, verifier, or test-label references. Optional cleanup: delete `environment/Dockerfile.pre-canonical-bak`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Exposing Hints/Answers | yes | 1 |
| Environment | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Pinning Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |

---

_Generated by `./scripts/terminus review` baseline + manual re-audit per `prompt.md`._
