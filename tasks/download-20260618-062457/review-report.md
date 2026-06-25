# Terminus Review Report: download-20260618-062457

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (report evidence; local oracle not executed) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** Test Alignment/Coverage Issues, Metadata Issues

**Decision (concise):** Milestone layout, digest-pinned Dockerfile, offline uvx verifier wheels, rubrics, and Hard difficulty calibration (worst-model 40%) are solid. Two blockers remain: (1) Milestone 6 never tests the required `blocked` + capability usage → `critical` risk branch, so a wrong implementation can pass; (2) `task.toml` has invalid top-level `[agent]`/`[verifier]` sections for a milestone task. Fix the M6 test gap first, then remove redundant top-level timeout blocks.

**Insights (concise):**

- ChatGPT's M6 coverage-gap finding is **confirmed** with file evidence; LLMaJ `behavior_in_tests: PASS` contradicts artifacts on this point.
- Auto-review false positives on #1 (aggregate word count), #20 (pytest wheels are baked via `/app/verifier-wheels`), and #31 (all 26 tests have docstrings).
- Static blocked bundles (`AcmeWallet`, `LegacyBridge`) have `.m` files but **no** capability markers; dynamic fixtures use profiles yielding `compliant` or `drift`, never `blocked` + capabilities.
- Oracle solution implements the missing branch correctly (`solve6.sh:74`); gap is verifier-only.
- Agent failures cluster on M6 `keychain_groups` normalization (5/10 on one test), not on the untested branch — but the branch is still a spec-enforced High gap.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27 | M6 `risk_level` rule requires `critical` when a **blocked** bundle has detected capability usage; no test creates that scenario | `steps/milestone_6/instruction.md:16`; `test_m6.py:132-137` (base blocked rows at `medium`, `bundles_with_source_usage: 0`); `test_m6.py:162-255` (`RiskProbe` is `compliant`); `test_m6.py:257-312` (`RiskDrift` is `drift`); static `WalletDelegate.m` / `BridgeAgent.m` have no markers | Add dynamic fixture: blocked profile (e.g. `adhoc-qa`) + `.m` with capability marker + entitlements backing usage → assert `status=="blocked"` and `risk_level=="critical"` |
| 2 | High | Metadata Issues | #43 | Milestone task has forbidden top-level `[agent]` and `[verifier]`; per-step blocks already exist | `task.toml:25-29` (top-level); `task.toml:34-83` (per-step); validate ERROR | Remove lines 25–29; keep only `[steps.agent]` / `[steps.verifier]` per milestone |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M6 blocked bundle + capability usage must be `critical` but is untested (ChatGPT High) | **Agree** | `instruction.md:16`; no test asserts `status=="blocked"` with non-empty `capabilities_used`; oracle implements branch at `solve6.sh:74` |
| 2 | Task structure, milestones, Dockerfile pinning, offline verifier, Hard calibration solid (ChatGPT note) | **Agree** | `Dockerfile:1`; `verifier-wheels/` under `environment/app/`; `task.toml:7` difficulty hard; agent 40%/20% pass rates in `entire-report.txt:6-7` |
| 3 | Rubric present with milestone criteria and ≥3 negatives (ChatGPT note) | **Agree** | `rubrics.txt` — 6 blocks, 6 negative criteria (`-3` to `-5`) |
| 4 | LLMaJ `behavior_in_tests: PASS` for M6 risk classification (entire-report.txt:117) | **Disagree** | Same gap as claim 1; LLMaJ overstates coverage for blocked+capability branch |
| 5 | M5 `selected_sidecar=null` untested (entire-report.txt:634-657) | **Partially agree** | `milestone_5/instruction.md` specifies null sidecar; no dynamic bundle without `*.entitlements` — **Low/Medium**, not revision-driving alone |
| 6 | M5 `blocked` boolean on legacy row untested (entire-report.txt:620-631) | **Partially agree** | Indirectly constrained via `status` and summary counts — **Low** impact |
| 7 | Evidence marker tiebreaker untested (entire-report.txt:756-793) | **Partially agree** | Secondary sort dimension; **Low** — not a standalone High blocker |
| 8 | Auto-review: instruction too long aggregate (#1) | **Disagree** | Per-milestone word counts: M1 187, M2 396, M3 209, M4 312, M5 312, M6 449; agent sees one milestone at a time per `prompt-styling.md` milestone rules |
| 9 | Auto-review: pytest not in Dockerfile (#20) | **Disagree** | `environment/app/verifier-wheels/` baked via `COPY app/`; `test.sh:24-28` uses offline `uvx -w pytest==8.4.1` with `UV_OFFLINE=1` — no runtime network install |
| 10 | Auto-review: 26 tests missing docstrings (#31) | **Disagree** | All 26 `test_*` methods have docstrings, e.g. `test_m6.py:121-122`, `test_m1.py:48-49` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Per-milestone instructions; longest M6 is 449w schema contract, not aggregate spec dump | `steps/milestone_*/instruction.md` word counts |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer task tone; no ## headers or API dumps | `steps/milestone_1/instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no heavy markdown | all `instruction.md` |
| 4 | CHECK | No step by step instructions | No "first run ls" patterns | all `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT (schemas/CLI), not HOW | all `instruction.md` |
| 6 | CHECK | No design doc style tables | No input→output tables | all `instruction.md` |
| 7 | CHECK | Instruction is well specified | Exact CLI, paths, JSON fields per milestone | all `instruction.md` |
| 8 | CHECK | Instruction is interesting | Real iOS/macOS entitlement audit scenario | `category = "security"` |
| 9 | CHECK | Instruction is unique | Multi-milestone entitlement CLI; not generic CRUD | task scope |
| 10 | CHECK | All paths absolute | `/app/...` throughout | all `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task folder name in text | all `instruction.md` |
| 12 | CHECK | No canary string | No canary patterns | all `instruction.md` |
| 13 | CHECK | Dockerfile no web content fetch | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | Pinned Python/pip deps | `pytest==8.4.1` in test.sh wheels | `test.sh:26-27` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367...` | `Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | COPY only from environment | `Dockerfile:19` |
| 17 | CHECK | No ground truth in environment | Stub CLI + fixtures only | `entitlement_audit.py:17-36` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose doesn't alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked; test.sh no runtime installs | Wheels in image; offline uvx only | `app/verifier-wheels/`, `test.sh:12-28` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle no internet | solve scripts patch local Python only | `solve6.sh` |
| 23 | CHECK | Oracle reflective | Incremental Python implementation | `solve1.sh`–`solve6.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir + 0/1 reward | `test.sh:3,30-35` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | all `test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | all `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | M6 blocked+capability→critical untested | Blocker 1 |
| 28 | CHECK | Tests check correctness | CLI subprocess + semantic JSON asserts | `test_m6.py:83-99` |
| 29 | CHECK | Behavior not implementation grep | No source-file grep of agent code | all `test_m*.py` |
| 30 | CHECK | No brittle string matching | Schema-appropriate JSON equality | `test_m6.py` |
| 31 | CHECK | Informative names or docstrings | 26/26 tests documented | `test_m*.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 6 negatives | `rubrics.txt` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All scores valid | `rubrics.txt` |
| 34 | CHECK | Agent …, ±N format | 30 criteria lines | `rubrics.txt` |
| 35 | CHECK | Rubric criteria detailed | Milestone-specific behaviors | `rubrics.txt` |
| 36 | CHECK | Positive phrasing with negative scores | "Agent hardcodes…, -5" pattern | `rubrics.txt:6` |
| 37 | CHECK | Rubric no /tests/ refs | No test references | `rubrics.txt` |
| 38 | CHECK | Rubric no metadata/instruction refs | No task.toml/instruction refs | `rubrics.txt` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None found | `rubrics.txt` |
| 40 | CHECK | Required files present | Milestone layout via #46 | `steps/milestone_*/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email present | anonymous/anonymous | `task.toml:5-6` |
| 43 | UNCHECK | All required metadata fields | Top-level `[agent]`/`[verifier]` invalid for milestones | `task.toml:25-29`; validate ERROR |
| 44 | CHECK | Tags/languages/category applicable | security, objective-c, python, plist | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches pass rates | Declared hard; worst-model 40%; Python hard required | `task.toml:7`; `entire-report.txt:6-7`; `reviewer-checklist-ui.md:62` |
| 46 | CHECK | steps/ milestone layout | 6 milestones under `steps/` | `task.toml:10,31-83` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve6.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m6.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone tests scoped | Each file imports/runs one milestone CLI | `test_mN.py` classes |
| 50 | CHECK | Tests not in Docker image | No COPY tests/ | `Dockerfile:19` |
| 51 | CHECK | Solution not in environment | No solution/ in image | `Dockerfile` |
| 52 | CHECK | Agent can't trivially cheat | Dynamic runtime bundles + policy mutation | `test_m6.py:164-197` |
| 53 | CHECK | Git repos pinned | No git clone | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤80% | `entire-report.txt:6-7` |
| 55 | CHECK | Not too hard/unfair | Spec complete; agent failures are logic bugs not missing info | `entire-report.txt:87-89` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 27, 43 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M6: scan `.m/.mm/.h` for capability markers | `test_dynamic_source_capabilities_create_critical_missing_support`, `test_drift_bundle_with_objective_cxx_capability_usage_is_high_risk`, `test_normalized_support_and_direct_source_scan_boundaries` | covered | `test_m6.py:182-196`, `285-295`, `334-357` |
| M6: `critical` when `missing_runtime_support` non-empty | `test_dynamic_source_capabilities_create_critical_missing_support`, `test_normalized_support_and_direct_source_scan_boundaries` | covered | `test_m6.py:200`, `367-369` |
| M6: `high` when drift + capability usage | `test_drift_bundle_with_objective_cxx_capability_usage_is_high_risk` | covered | `test_m6.py:299-300` |
| M6: `medium` when blocked/drift without capability path | `test_base_register_schema_sorting_and_counts` | covered | `test_m6.py:132-137` |
| M6: **`critical` when blocked + capability usage** | — | **gap** | `instruction.md:16`; no blocked+capability fixture |
| M6: `low` for compliant | `test_base_register_schema_sorting_and_counts`, `test_register_reflects_state_after_apply_without_mutating` | covered | `test_m6.py:136-137`, `408-409` |
| M6: evidence sort by capability/file/line/marker | partial | gap (Low) | marker tiebreaker never discriminates — `entire-report.txt:756-793` |
| M6: read-only; reflect post-apply state | `test_register_reflects_state_after_apply_without_mutating` | covered | `test_m6.py:389-411` |
| M5: `selected_sidecar` null when no sidecar | — | gap (Low) | `entire-report.txt:634-657` |
| M1–M5 core schemas and policy rules | respective `test_m1`–`test_m5` suites | covered | per-test pass rates 8–10/10 in `entire-report.txt:19-39` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_6/instruction.md` | Blocker 1, #27, spec alignment |
| `steps/milestone_6/tests/test_m6.py` | Blocker 1, #27, #28, #31 |
| `steps/milestone_6/solution/solve6.sh` | Claim 1 oracle implements branch |
| `task.toml` | Blocker 2, #43, #45, #46 |
| `environment/Dockerfile` | #15, #20, #50 |
| `steps/milestone_1/tests/test.sh` | #20, #24 |
| `environment/app/verifier-wheels/` | #20 |
| `rubrics.txt` | #32–#39 |
| `entire-report.txt` | Agent stats, LLMaJ adjudication |
| `environment/app/bundles/AcmeWallet/WalletDelegate.m` | Blocker 1 (no markers on static blocked bundle) |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml: Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone
ERROR: task.toml: Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone
INFO/WARNING: 28 warnings (docstring false positives, 6 milestones info, uv hint pattern)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | M6 keychain normalization failures |
| terminus-claude-opus-4-8 | 40.0% (2/5) | Same M6 pattern |
| oracle | 100.0% (3/3) | Report evidence |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | yes (Python hard declaration policy) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Entitlement audit CLI, 6 milestones, security/tool_specific |
| 1 Instruction | ☑ | Per-milestone schema contracts; absolute paths |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, offline wheels |
| 3 Oracle | ☑ | Incremental solves; report 100% pass |
| 4 Verifiers | ☑ | reward.txt OK; M6 coverage gap found |
| 5 Metadata | ☑ | Top-level agent/verifier blocks invalid |
| 6 Rubric | ☑ | 6 blocks, 6 negatives, valid scores |
| 7 LLMaJ & agent evidence | ☑ | Contradicted LLMaJ on M6 blocked branch |
| 8 Novelty & fairness | ☑ | Multi-step CLI; dynamic anti-cheat |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, milestone layout, digest-pinned Dockerfile, offline verifier wheels, rubrics, and Hard difficulty calibration look solid. Two blockers: (1) Milestone 6 never tests the required rule that a blocked bundle with detected capability usage must get `critical` risk — add a dynamic blocked+capability fixture; (2) remove invalid top-level `[agent]`/`[verifier]` from `task.toml` (per-step blocks already exist). Auto-review false positives on instruction length aggregate, pytest baking, and docstrings were rejected on re-audit.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Metadata Issues | yes | 2 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
