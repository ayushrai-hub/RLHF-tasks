# Terminus Review Report: block_sealed_export_wal

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (2 errors, 129 warnings — most warnings are false positives) |
| **Oracle** | not executed (report: 100% 3/3) |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Milestones, Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong milestone crypto task with correct rubric block format, pinned offline env, and deep M2/M3 verifiers. Real blockers: `task.toml` violates milestone timeout layout (top-level `[agent]`/`[verifier]`), `manifest-and-seal.md` omits `compute_integrity_seal`/`verify_integrity_seal` public API names that M1 tests import (recurring agent failure), and M3 never tests the required `keygen` CLI. Fix those first; add M3 lineage-ordering and no-partial-stdout assertions as follow-ups.

**Insights (concise):**

- Rubric uses correct **milestone** format (`# Rubric 1–3`); per-block positives 21/23/28 (all ≤40) — not a rubric blocker.
- ChatGPT M1 staging-lineage / `export_builder` gap is **mitigated**: M1 defers full encrypt to M2; `test_staging_fingerprint_sidecar_written` and `test_export_metadata_includes_staging_fingerprint` cover sidecar + metadata in `test_m2.py:348–372`.
- Dockerfile pip packages are `==`-pinned (`environment/Dockerfile:10–15`); validator #14 warning is a false positive.
- All 127 `test_*` functions have docstrings (AST audit: 0 missing); #31 should CHECK.
- Worst-model 0% (Claude Opus 4.8) — difficulty calibration fine; undocumented seal API names likely drove near-miss M1 failures.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Milestones | #43, #46 | Milestone `task.toml` has forbidden top-level `[agent]` and `[verifier]` | `task.toml:27–31` duplicates per-step timeouts at `task.toml:36–56`; `./scripts/terminus validate` ERROR | Remove top-level `[agent]` / `[verifier]`; keep only `[steps.agent]` / `[steps.verifier]` per `docs/guidelines/milestones.md:99` |
| 2 | High | Instruction Styling | #7, #27, #55 | `integrity_seal.py` public function names not normatively documented; tests require exact imports | `environment/app/docs/manifest-and-seal.md:13–28` describes behavior only; `replay_journal` lists Public APIs at `:34–35` but integrity seal does not; `steps/milestone_1/tests/test_m1.py:311` imports `compute_integrity_seal`, `verify_integrity_seal`; `entire-report.txt:253` recurring agent failure | Add Public APIs block to `manifest-and-seal.md`: `compute_integrity_seal(export, master_key) -> str`, `verify_integrity_seal(export, master_key) -> bool` (return bool, do not raise) |
| 3 | High | Test Alignment/Coverage Issues | #27 | M3 requires `keygen` CLI; no verifier invokes it | `steps/milestone_3/instruction.md:5` "decrypt, rotate, and keygen"; `environment/app/docs/overview.md:24`; `grep keygen steps/milestone_3/tests/test_m3.py` → no matches | Add `test_cli_keygen_produces_valid_hex_key` (exit 0, stdout is 32-byte hex key) |

*Non-blockers (Medium — fix with revision but do not alone drive Decline):*

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 4 | Medium | Test Alignment/Coverage Issues | #27 | `rotation_preflight.assert_export_lineage` call/order not directly tested | `rotation-and-wal.md:7–9`; `export_validator.py:17–31` checks presence only; `rotation_preflight.py:8–23` checks manifest↔secrets; no `rotation_preflight` import in `test_m3.py` | Mock/track call order in `rotate_keys` or test manifest mismatch raises `ExportParseError` via lineage gate |
| 5 | Medium | Test Alignment/Coverage Issues | #27 | CLI failure tests omit "no partial output" on stdout | `steps/milestone_3/instruction.md:10`; `test_m3.py:433`, `:726`, `:806` assert `returncode != 0` only | Add `assert proc.stdout.strip() == ""` on decrypt/rotate failure paths |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `compute_integrity_seal` / `verify_integrity_seal` undocumented (ChatGPT High) | **Agree** | `manifest-and-seal.md` names `compute_manifest_digest` and journal APIs but not seal functions; tests import exact names at `test_m1.py:311`; agent report lines 253–254 |
| 2 | M1 lacks staging lineage / `export_builder` tests (ChatGPT / test-quality Critical) | **Partially agree** | `test_m1.py` has no `export_builder`/`staging_lineage` imports; **but** M1 defers encrypt at `milestone_1/instruction.md:5`; M2 covers via `test_m2.py:348–372` encrypt CLI + sidecar + metadata fingerprint |
| 3 | M3 `keygen` untested (ChatGPT High) | **Agree** | `milestone_3/instruction.md:5`; zero `keygen` in `test_m3.py` |
| 4 | `assert_export_lineage` ordering untested (ChatGPT High) | **Partially agree** | Function **is** named in `rotation-and-wal.md:7–8`; gap is verifier call-order / mismatch coverage, not missing spec — severity Medium |
| 5 | CLI failures should assert no partial stdout (ChatGPT Medium) | **Agree** | `milestone_3/instruction.md:10`; failure tests at `test_m3.py:433,726,806` check exit code only |
| 6 | Add `python` tag (ChatGPT Low) | **Agree (Low)** | `task.toml:14` tags omit `python`; `languages` already includes python — cosmetic only |
| 7 | Dockerfile FROM digest pinned (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…` |
| 8 | Rubric positive total 72 > 40 (rubric-points script) | **Disagree as blocker** | Milestone task: per-block caps apply (`#1=21, #2=23, #3=28` all ≤40); `docs/guidelines/milestones.md:104–106` |
| 9 | Rubric in wrong (non-milestone) format | **Disagree** | `entire-report.txt:853–887` uses `# Rubric 1`, `# Rubric 2`, `# Rubric 3` — correct milestone rubric layout |
| 10 | LLMaJ `behavior_in_tests` PASS | **Agree with caveat** | Broad coverage true; misses `keygen` and seal API doc gap |
| 11 | Automated review "READY TO USE" | **Disagree** | Missed `task.toml` milestone errors and seal API doc gap |
| 12 | 127 tests missing docstrings (auto review) | **Disagree** | AST scan: 0 `test_*` without docstrings across `test_m1.py`–`test_m3.py` |
| 13 | Instruction too long (#1 fail) | **Disagree** | Each `steps/milestone_N/instruction.md` is 1 short paragraph + bullets (~80–120 words); validator wrongly aggregates all milestones |
| 14 | Pip unpinned (#14 fail) | **Disagree** | `environment/Dockerfile:11–15` all use `==` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction ≤3 paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem-oriented engineering briefs, not audit spec | milestone instructions |
| 3 | CHECK | No excessive markdown | No heavy tables/headers in instructions | milestone instructions |
| 4 | CHECK | No step-by-step solve script | Points to normative `/app/docs/` only | milestone instructions |
| 5 | CHECK | No hints/solving strategies | WHAT via contracts, not HOW walkthrough | milestone instructions |
| 6 | CHECK | No design-doc I/O tables in instruction | Tables live in `/app/docs/` | milestone instructions |
| 7 | UNCHECK | Well specified | Seal public API names missing from normative doc | `manifest-and-seal.md:13–28` |
| 8 | CHECK | Interesting | Realistic sealed-export + rotation engineering | task scope |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | manual |
| 10 | CHECK | Absolute paths | `/app/docs/...` throughout | milestone instructions |
| 11 | CHECK | Task name not in instruction | No `block_sealed_export_wal` string | milestone instructions |
| 12 | CHECK | No canary string | None found | milestone instructions |
| 13 | CHECK | No web content fetch in env | Offline fixtures only | `environment/` |
| 14 | CHECK | Pip pinned with == | All packages pinned | `environment/Dockerfile:11–15` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context self-contained | COPY `app/` only | `environment/Dockerfile:18` |
| 17 | CHECK | No ground-truth answers in env | Broken stubs; solution not copied | `environment/app/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh clean | No runtime installs | `Dockerfile`, `steps/*/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not re-run locally | report oracle 100% |
| 22 | CHECK | Oracle no internet | solve scripts copy/patch files only | `steps/*/solution/` |
| 23 | CHECK | Oracle reflective | Implements algorithms, no echo answers | solution `files/` |
| 24 | CHECK | reward.txt canonical block | mkdir + 0/1 write | `steps/milestone_1/tests/test.sh:13–26` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | test files |
| 26 | CHECK | Binary rewards | 0/1 only | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | `keygen` required but untested; seal API doc gap | blockers 2–3 |
| 28 | CHECK | Tests check correctness | Crypto round-trips, tamper, WAL ordering | `test_m2.py`, `test_m3.py` |
| 29 | CHECK | Behavior not implementation grep | Functional/module tests | test files |
| 30 | CHECK | No brittle long-string asserts | Mostly structural/crypto checks | test files |
| 31 | CHECK | Informative names/docstrings | All `test_*` have docstrings | AST audit |
| 32 | CHECK | ≥3 negative rubric criteria | 8 negatives across blocks | `entire-report.txt:861–887` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | No ±4 | platform rubric |
| 34 | CHECK | Agent …, ±N format | 27 criteria lines | platform rubric |
| 35 | CHECK | Rubric detailed/precise | Task-specific crypto/rotation behaviors | platform rubric |
| 36 | CHECK | Positive phrasing | Negatives describe bad behavior with −N | platform rubric |
| 37 | CHECK | Rubric no /tests/ refs | None | platform rubric |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | platform rubric |
| 39 | CHECK | Rubric no oracle/NOP | None | platform rubric |
| 40 | CHECK | Required files present | Milestone layout: Dockerfile, per-step solve/test/instruction | `steps/` tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author fields | Present | `task.toml:4–5` |
| 43 | UNCHECK | Metadata complete | Top-level `[agent]`/`[verifier]` invalid for milestones | `task.toml:27–31` |
| 44 | CHECK | Tags/languages/category fit | security/python/crypto task | `task.toml` |
| 45 | CHECK | Difficulty vs agents | declared hard; worst-model 0%; platform hard | `task.toml`, `entire-report.txt:15–21` |
| 46 | UNCHECK | Milestone steps layout | `task.toml` milestone timeout violation | `task.toml:27–31` |
| 47 | CHECK | solveN.sh per milestone | solve1/2/3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/2/3.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone scope isolated | Each file tests own milestone class | test files |
| 50 | CHECK | Tests not in image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not in env | Comment + no COPY solution | `environment/Dockerfile:26` |
| 52 | CHECK | Input not trivially mutable | TB3 fixtures independent | `gen_verifier_fixtures.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:19–21` |
| 55 | UNCHECK | Not unfair | Undocumented seal API names caused recurring near-miss failures | `entire-report.txt:221–237,253` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 43, 46, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `compute_integrity_seal` / `verify_integrity_seal` APIs | `test_integrity_seal_*` | **gap (spec)** | Doc omits names; tests import at `test_m1.py:311` |
| Staging fingerprint sidecar (M1) | — in M1 | **gap M1 / covered M2** | M1 `test_staging_writes_flattened_fields` no sidecar; M2 `test_staging_fingerprint_sidecar_written` |
| `build_encrypted_export` / `export_builder` | M2 encrypt CLI tests | **covered M2** | `test_m2.py:340–372` |
| `staging_lineage.compute_staging_fingerprint` | M2 sidecar test | **covered M2** | `test_m2.py:361–364` recompute digest |
| HKDF info / AAD `kv{key_version}` | `test_hkdf_info_format`, `test_build_gcm_aad_binds_key_version` | covered | `test_m2.py` |
| `crypto_nonce_policy.next_nonce` | nonce uniqueness tests | **gap (name)** | Behavior tested; function name not imported |
| `export_validator.validate_export` before seal | `test_bad_schema_raises_export_parse_not_integrity` | covered | `test_m3.py:707–715` |
| `rotation_preflight.assert_export_lineage` ordering | — | **gap** | Named in `rotation-and-wal.md:7`; not mocked in tests |
| CLI `keygen` | — | **gap** | `milestone_3/instruction.md:5` |
| CLI decrypt/rotate no partial output on failure | partial | **gap** | `test_m3.py:433,726,806` exit code only |
| WAL pending before swap / completed after | `test_wal_completed_only_after_export_swap` | covered | `test_m3.py` |
| No plaintext during rotation | `test_no_plaintext_written_during_rotation` | covered | `test_m3.py` |
| TB3 hidden fixtures | `test_tb3_*` | covered | `test_m1.py`, `test_m3.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blockers 1; #43, #46, #45 |
| `environment/app/docs/manifest-and-seal.md` | Blocker 2; spec alignment |
| `environment/app/docs/rotation-and-wal.md` | Lineage spec; adjudication 4 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `steps/milestone_1/instruction.md` | M1 scope; #1 |
| `steps/milestone_3/instruction.md` | keygen; no partial output |
| `steps/milestone_1/tests/test_m1.py` | Seal imports; M1 staging |
| `steps/milestone_2/tests/test_m2.py` | Staging lineage M2 coverage |
| `steps/milestone_3/tests/test_m3.py` | keygen gap; CLI failures |
| `entire-report.txt` | Agent stats; rubric; external claims |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
(129 warnings: informative_test_docstrings false positives; long_context info N/A — subcategories empty)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20% (1/5) | |
| terminus-claude-opus-4-8 | 0% (0/5) | |
| oracle | 100% (3/3) | from report |
| nop | 0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone security/python task; name matches folder |
| 1 Instruction | ☑ | Seal API doc gap; per-milestone concise |
| 2 Environment | ☑ | Digest-pinned, offline, tmux+asciinema |
| 3 Oracle | ☐ | Not re-run; static review OK |
| 4 Verifiers | ☑ | keygen gap; reward block canonical |
| 5 Metadata | ☑ | task.toml milestone layout error |
| 6 Rubric | ☑ | Milestone blocks 21/23/28 pts; format correct |
| 7 LLMaJ & agents | ☑ | Recurring seal naming failures verified |
| 8 Novelty & fairness | ☑ | Near-miss pattern tied to doc gap |
| 9 Long context | N/A | `subcategories = []` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid milestone task — the three-step crypto/rotation arc, pinned Docker env, and M2/M3 verifiers (WAL ordering, crash recovery, no-plaintext checks) are in great shape. Three things to fix before accept: drop the top-level `[agent]`/`[verifier]` sections from `task.toml` (milestones should only use per-step timeouts), add explicit `compute_integrity_seal` and `verify_integrity_seal` public API names/signatures to `manifest-and-seal.md` (agents keep missing this — it's the main recurring failure), and add a M3 test that runs the `keygen` CLI subcommand. Optional polish: assert empty stdout on decrypt/rotate failures and directly verify `assert_export_lineage` runs before crypto during rotation.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Milestones | yes | 1 |
| Instruction Styling | yes | 2 |
| Test Alignment/Coverage Issues | yes | 3 (+4, 5 medium) |
| Rubric | no | — |
| Metadata Issues | yes (via milestone layout) | 1 |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
