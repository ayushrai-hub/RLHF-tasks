# Terminus Review Report: `meson-rpath-reproducible-install`

**Generated:** 2026-06-30  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/meson-rpath-reproducible-install`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally; submission report 100% 3/3) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong C/Meson packaging task with solid pipeline tests, anti-cheat design, digest-pinned GCC image, and a correct flat (non-milestone) rubric at 20/40 positive points. Two real spec↔test gaps remain: `catalog_epoch` must equal the release profile string `release` but instruction never states that; tree `mode` must serialize as lowercase octal without a leading zero (e.g. `755`) but instruction only names the field. Prior reviewer feedback on missing `config` subfields is fixed in the current `instruction.md`.

**Insights (concise):**

- `instruction.md:9` now lists all `config` subfields (`header`, `sha256`, `version`, `package_id`, `source`, `provenance`, `profile`) — stale feedback at top of `entire-report.txt` is resolved.
- Tests enforce `catalog_epoch == "release"` at `tests/test_outputs.py:217` while instruction only names the field and separately documents profile `release` at `instruction.md:11`.
- Tests enforce `format(st_mode & 0o777, "o")` (e.g. `755`) at `tests/test_outputs.py:292,308`; agent trial `66KBtr8` failed on `0755` vs `755` per `entire-report.txt:66,87`.
- Platform rubric is flat `Agent …, ±N` lines (no `# Rubric 2+` headers); 20 positive points, 3 negatives — correct non-milestone format, not a blocker.
- Worst-model pass rate 40% (GPT-5.5); declared `hard` vs platform `medium` is informational only.
- Non-canonical `gcc:13-bookworm` base is digest-pinned and justified for C/Meson; not a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | `catalog_epoch` semantics under-specified: tests require the release profile string `release`, but instruction never equates `catalog_epoch` to the configured catalog/profile value. | `tests/test_outputs.py:18,217` (`EXPECTED_PROFILE = "release"`; `assert ledger["catalog_epoch"] == EXPECTED_PROFILE`); `instruction.md:9,11` (names `catalog_epoch` and profile `release` separately, no equality rule); `environment/scripts/audit_tree.sh:50` (`catalog_epoch=$(extract_define CAPSULE_CATALOG_PROFILE)` — discoverable in broken env only); `entire-report.txt:68,88-89` (agent used hash) | State explicitly in `instruction.md` (and optionally `operator_contract.md`) that manifest and sidecar `catalog_epoch` must equal the release catalog profile string, currently `release`. |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Tree `mode` serialization format not documented; verifier expects lowercase octal digits without leading zero (`mode & 0o777` formatted as `o`). | `tests/test_outputs.py:292,308` (`assert entry["mode"] == format(path.stat().st_mode & 0o777, "o")` → `755` not `0755`); `instruction.md:11` (lists `path`, `mode`, `sha256` only); `environment/docs/operator_contract.md` (no mode rule); `environment/docs/packaging_notes.md` (no mode rule); `entire-report.txt:66,87` (agent failure `0755` vs `755`) | Document exact tree `mode` format in instruction or referenced contract (e.g. lowercase octal permission bits masked to `0o777`, no leading zero, as produced by GNU `stat -c '%a'`). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `catalog_epoch` must equal profile string `release`, not a hash (ChatGPT High) | **Agree** | `tests/test_outputs.py:217`; `instruction.md:9,11`; `entire-report.txt:68,88-89` |
| 2 | Tree `mode` must be lowercase octal without leading zero, e.g. `755` (ChatGPT High) | **Agree** | `tests/test_outputs.py:292,308`; `instruction.md:11`; `entire-report.txt:66,87` |
| 3 | Config section missing subfields was fixed (ChatGPT Medium) | **Agree** | `instruction.md:9` lists `header`, `sha256`, `version`, `package_id`, `source`, `provenance`, `profile`; contrasts with stale note `entire-report.txt:1-2` |
| 4 | Optional: assert pkg-config `.pc` version metadata (ChatGPT Low / test quality review) | **Disagree as blocker** | `tests/test_outputs.py:285` checks presence + digest; gap is Low only per `entire-report.txt:281-336` |
| 5 | Optional: assert `compiled_package_id` directly (ChatGPT Low) | **Disagree as blocker** | `tests/test_outputs.py:377-391` checks linked fields; header define verified at `:273-274`; cosmetic gap only |
| 6 | Dockerfile FROM digest-pinned — no base-image blocker (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:930f2ebe…` |
| 7 | Non-canonical `gcc:13-bookworm` needs formal approval (Harbor review warning) | **Disagree as blocker** | Digest-pinned; C/Meson toolchain justified; `reviewer-checklist-full.md` allows credible non-canonical justification |
| 8 | Prior reviewer: config subfields not listed (`entire-report.txt:1-2`) | **Disagree (stale)** | Fixed in current `instruction.md:9` |
| 9 | LLMaJ: instruction mentions reconcile exit 6 for `catalog_epoch` (`entire-report.txt:105`) | **Disagree** | Current `instruction.md:11` documents exit 4 and 5 only; `solution/fix.patch:256-257` adds exit 6 in oracle reconcile but instruction does not |
| 10 | Non-milestone task uses milestone rubric format (user query) | **Disagree** | `task.toml:12` `number_of_milestones = 0`; `entire-report.txt:366-374` flat `Agent …, ±N` list with no `# Rubric 2+` headers; `docs/guidelines/rubrics.md:66` |
| 11 | Rubric positive total >40 (rules check) | **Disagree** | `rubric_points.py`: 20 positive points (6 +lines), cap 40 — PASS |
| 12 | Harbor / test-quality: READY TO USE / ACCEPT | **Partially agree** | Structure and tests are strong; spec gaps on `catalog_epoch` and `mode` block accept |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Six paragraph blocks (`instruction.md:1,3,5,7,9,11`) exceed three-paragraph guidance | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense schema/field enumeration reads as contract spec, not conversational prompt | `instruction.md:9-11` |
| 3 | CHECK | No excessive markdown formatting | No heavy markdown | `instruction.md` |
| 4 | CHECK | No step by step instructions | No step-by-step solve script | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States outcomes, not patch steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input/output tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Two tested fields (`catalog_epoch`, tree `mode` format) lack normative definitions | Blockers 1–2 |
| 8 | CHECK | Instruction is interesting | Realistic C/Meson release-packaging repair | Task content |
| 9 | CHECK | Instruction is unique | Distinct manifest/ledger/replay packaging domain | Task content |
| 10 | CHECK | All paths absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task slug in prompt | `instruction.md` |
| 12 | CHECK | No canary string | No canary patterns | `instruction.md` |
| 13 | CHECK | No web content fetch in env | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:6` |
| 15 | CHECK | Base image digest-pinned | `@sha256:930f2ebe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | COPY only env subtree | `environment/Dockerfile:10-21` |
| 17 | CHECK | No ground truth answers in env | Broken starter code only; no solution/tests COPY | `environment/Dockerfile`, `solution/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:6`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Submission report oracle 100% (3/3); static solve applies patch + `make package` | `entire-report.txt:30`, `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | patch + local make only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective of instruction | Multi-file patch + pipeline build, not static JSON echo | `solution/solve.sh`, `solution/fix.patch` |
| 24 | CHECK | test.sh reward.txt canonical block | mkdir, default 0, pytest, 0/1 write | `tests/test.sh:6-25` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | `catalog_epoch` and tree `mode` format tested but unstated | Blockers 1–2 |
| 28 | CHECK | Tests check correctness | Pipeline rebuild, digests, rpath, execution, exit codes | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle string matching (given spec) | Exact mode match is correct once format is documented | `tests/test_outputs.py:292` |
| 31 | CHECK | Informative test names/docstrings | All 19 `test_*` functions have docstrings | `tests/test_outputs.py:228-432` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives at -5, -5, -3 | `entire-report.txt:372-374` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use ±2,3,5 | `entire-report.txt:366-374` |
| 34 | CHECK | Rubric format Agent …, ±N | 9 Agent lines | `entire-report.txt:366-374` |
| 35 | CHECK | Rubric detailed and precise | Task-specific pipeline criteria | `entire-report.txt:366-374` |
| 36 | CHECK | Positive language with negative scores | Bad behaviors described affirmatively with `-N` | `entire-report.txt:372-374` |
| 37 | CHECK | Rubric no /tests/ refs | No pytest paths | `entire-report.txt:366-374` |
| 38 | CHECK | Rubric no task.toml/instruction refs | No metadata refs | `entire-report.txt:366-374` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None present | `entire-report.txt:366-374` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | Task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | Task tree |
| 42 | CHECK | author_name/email present | `anonymous` fields | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category match | build-and-dependency-management, meson/c/bash | `task.toml:7-10` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform medium / 40% worst-model informational | `task.toml:6`, `entire-report.txt:20-26` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A — regular task | `task.toml:12` |
| 48 | UNCHECK | test_mN.py per milestone | N/A — regular task | `task.toml:12` |
| 49 | UNCHECK | Milestone test scope | N/A — regular task | `task.toml:12` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Tests wipe output and rerun pipeline | `tests/test_outputs.py:51-56,394-399` |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:25-26` |
| 55 | UNCHECK | Not too hard/unfair | Hidden `catalog_epoch` and `mode` semantics caused systematic near-miss failures | `entire-report.txt:58-92`, blockers 1–2 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 2, 7, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Schema `capsule-install-manifest-v1`, prefix, build_system | `test_fresh_package_establishes_consistent_ledger` | covered | `tests/test_outputs.py:172-176` |
| Config subfields (header, sha256, version, package_id, source, provenance, profile) | `assert_release_values` | covered | `instruction.md:9`; `tests/test_outputs.py:211-216` |
| `catalog_epoch` equals release profile `release` | `assert_release_values` | **gap** | `tests/test_outputs.py:217`; not stated in `instruction.md` |
| Tree rows: path, mode, sha256 for all files | `test_manifest_tree_rows_match_installed_files` | partial | mode format **gap** at `:292` |
| Soname symlink rows use target digest/mode | `test_soname_symlink_rows_use_resolved_target_metadata` | partial | mode format **gap** at `:308` |
| `tree_root_sha256` derivation | `test_tree_root_digest_is_derived_from_manifest_tree_rows` | covered | `operator_contract.md:9`; `tests/test_outputs.py:159-169,314` |
| RPATH `$ORIGIN/../lib` | `test_installed_binaries_carry_relative_loader_paths` | covered | `packaging_notes.md:5`; `tests/test_outputs.py:239-248` |
| No LD_LIBRARY_PATH; linked origin `installed` | `test_installed_commands_run_without_loader_environment`, `test_release_audit_does_not_record_loader_shortcuts` | covered | `tests/test_outputs.py:251-261,370-374` |
| Config header from Meson not fallback | `test_config_header_is_generated_and_matches_manifest` | covered | `tests/test_outputs.py:264-274` |
| Replay preserves generation; fresh resets | `test_replay_preserves_ledger_generation`, `test_fresh_package_after_replay_resets_generation` | covered | `tests/test_outputs.py:317-350` |
| Reconcile exit 4 (generation), 5 (tree_root) | `test_reconcile_rejects_stale_sidecar_generation`, `test_reconcile_rejects_corrupted_tree_root` | covered | `instruction.md:11`; `tests/test_outputs.py:352-367` |
| Reconcile exit 6 (catalog_epoch) — oracle only | — | phantom in oracle | `solution/fix.patch:256-257`; not in `instruction.md` or tests |
| Smoke does not emit manifest/ledger | `test_smoke_build_does_not_emit_install_manifest` | covered | `tests/test_outputs.py:416-423` |
| pkg-config metadata agreement | — | minor gap | `instruction.md:11`; existence/digest only at `tests/test_outputs.py:285` |
| Release metadata across header, manifest, commands | `test_runtime_metadata_matches_diagnostic_and_consumer_output` | covered | `tests/test_outputs.py:377-391` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers 1–2, #1, #2, #7, #10, #27, #55 |
| `tests/test_outputs.py` | Blockers 1–2, #27, #28, #31, #55, spec alignment |
| `environment/docs/operator_contract.md` | `tree_root_sha256`; mode gap |
| `environment/docs/packaging_notes.md` | RPATH token |
| `environment/scripts/audit_tree.sh` | `catalog_epoch` derivation in broken env |
| `environment/Dockerfile` | #14–#20, #50 |
| `solution/solve.sh`, `solution/fix.patch` | #21–#23 |
| `task.toml` | #45, #46–49 N/A, metadata |
| `entire-report.txt` | Agent stats, rubric, external adjudication |
| `tests/test.sh` | #24–#26 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate meson-rpath-reproducible-install/
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
WARNING: informative_test_docstrings — module-level docstring missing (all 19 test functions have docstrings)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Best model |
| oracle | 100.0% (3/3) | From submission export |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | medium (`entire-report.txt:20`) |
| Tier match (#45) | informational only — not a blocker |

### Rubric positive points

| Field | Value |
|-------|-------|
| Positive point total | 20 |
| Positive line count | 6 |
| Cap | 40 |
| Status | PASS (20/40) |
| Format | Flat non-milestone (no `# Rubric 2+`) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `meson-rpath-reproducible-install`; regular layout; report applies |
| 1 Instruction | ☑ | Two spec gaps on `catalog_epoch` and tree `mode`; config subfields now complete |
| 2 Environment | ☑ | Digest-pinned GCC; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Static review pass; Docker oracle not re-run locally |
| 4 Verifiers | ☑ | 19 behavior tests; canonical reward block; no runtime installs |
| 5 Metadata | ☑ | `allow_internet=false`; category/tags fit |
| 6 Rubric | ☑ | 20/40 positives; 3 negatives; correct non-milestone flat format |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL aligns with mode/catalog_epoch gaps |
| 8 Novelty & fairness | ☑ | Strong anti-cheat; unfair only on undocumented fields |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid C/Meson packaging task — the end-to-end rebuild checks, RPATH validation, manifest/ledger reconciliation, and anti-static-output design are all in great shape, and the rubric format looks correct for a non-milestone submission. Two small contract gaps are blocking accept: please state explicitly that `catalog_epoch` must equal the release catalog profile string (`release`), not a content hash or other epoch, and document the exact tree `mode` serialization the verifier expects (lowercase octal permission bits masked to `0o777`, no leading zero — e.g. `755` not `0755`). The earlier feedback about missing `config` subfields looks addressed in the current instruction.

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
