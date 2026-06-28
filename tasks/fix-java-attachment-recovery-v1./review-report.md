# Terminus Review Report: `fix-java-attachment-recovery-v1.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, 5 warnings) |
| **Oracle** | pass (platform: 100% 3/3; local harbor CLI unavailable) |
| **CHECK count** | 54 |
| **UNCHECK count** | 1 |

**Error categories (internal):** none

**Decision (concise):** This is a well-built 4-milestone Java/Maven debugging task with digest-pinned offline environment, SHA-256 input guards, progressive per-milestone verifiers, and a full integration oracle in milestone 4. ChatGPT’s M3 coverage concern is factually accurate (11-row spot checks) but not a revision blocker: it matches the M3 instruction scope, mirrors M1/M2 edge-case patterns, and M4 calls `assert_report_matches_expected` on every row and summary field. Root-level `[agent]`/`[verifier]` in `task.toml` is intentionally omitted per milestone spec. Platform rubric correctly uses `# Rubric 1`–`# Rubric 4` for this milestone task.

**Insights (concise):**

- Claude 0% / GPT-5.5 80% (4/5) — worst model exactly at 80% boundary, not >80% rejected tier.
- M3 verifier spot-checks 11 rounding-sensitive IDs against `expected_report()`; M4 verifies all 26 eligible rows + summaries + sort + JSON formatting.
- `requirements.lock` pins pytest 8.4.1 with `==` and sha256 hashes; installed in Dockerfile — not a pinning or runtime-install violation.
- `docs/guidelines/milestones.md:99` requires per-step timeouts only — Harbor review warning about root `[agent]`/`[verifier]` is incorrect for milestone layout.
- Rubric has 12 negatives across 4 blocks (13 positive pts each); format matches milestone task, not a flat non-milestone rubric.
- Automated `terminus review` false-flagged #1 (concatenated all milestone instructions), #14, and #20 — all overturned on manual audit.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M3 tests do not fully verify calculation changes; only 11 attachments spot-checked; no full report, netAttachment, or summary totals (ChatGPT High) | Partially agree | `steps/milestone_3/tests/test_m3.py:25-40` checks 11 IDs for `layerCreditAmount`/`tierAdjustmentAmount`/`trancheHoldbackAmount` only. `steps/milestone_4/tests/test_m4.py:40-47` calls `assert_report_matches_expected` for all rows including `netAttachment` and all summary totals. M3 instruction (`steps/milestone_3/instruction.md:5`) scopes confirmation to “rounding-sensitive attachments such as ATT-028 and ATT-031”. Pattern matches M1 (count/IDs) and M2 (9 tier-adjustment edges). Gap exists but is closed at M4 — not a spec-test blocker. |
| 2 | Partial M3 implementation could pass while producing wrong totals (ChatGPT) | Disagree (as blocker) | Wrong engine logic on untested rows fails M4 `assert_report_matches_expected` (`test_helpers.py:296-326`). M3 partial credit before M4 fix is normal milestone progression. Agent M3 pass rate 20% (6/30 per-test in export) shows tests catch real errors. |
| 3 | netAttachment never verified in M3 (TEST QUALITY REVIEW / ChatGPT) | Disagree (as M3 gap) | `netAttachment` is required in M4 instruction (`steps/milestone_4/instruction.md:1`) and tested in M4 (`test_m4.py:47`). Not an M3 instruction requirement. |
| 4 | Missing root-level `[agent]` and `[verifier]` in task.toml (Harbor REVIEW REPORT) | Disagree | `docs/guidelines/milestones.md:99`: “**No** top-level `[agent]` or `[verifier]` — use per-milestone `[steps.agent]` / `[steps.verifier]`”. `task.toml:25-59` has four `[[steps]]` blocks with per-step timeouts — correct. |
| 5 | M1 instruction lacks explicit output schema (Harbor WARNING) | Disagree (as blocker) | M1 references `/app/docs/pricing-policy.md` for schema; M1 tests only need `attachmentCount` and ID set (`test_m1.py:19-29`). Low clarity note only. |
| 6 | LLMaJ `behavior_in_tests` PASS — all documented behavior tested | Agree | Cross-checked: M1 eligibility, M2 pipeline/basis, M3 rounding/holdback edges, M4 full report — all instruction behaviors have corresponding assertions somewhere in the milestone chain. |
| 7 | Task needs revision for M3 test strengthening (ChatGPT Decision) | Disagree | Strengthening M3 with `assert_report_matches_expected` would duplicate M4 and blur milestone boundaries. Optional enhancement, not required for accept. |
| 8 | Rubric uses milestone `# Rubric N` headers — wrong for non-milestone task (user question) | Disagree | `task.toml:10` sets `number_of_milestones = 4`. `entire-report.txt:568-602` has `# Rubric 1`–`# Rubric 4` — correct per `docs/guidelines/submission-export-format.md:64`. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone `instruction.md` is 2 short paragraphs (M1 ~120 words, M2–M4 ~80–100 words) | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem narrative + requirements; not spec-table style | `steps/milestone_1/instruction.md:1-7` |
| 3 | CHECK | No excessive markdown | No `##`/tables/code blocks in instructions | milestone instructions |
| 4 | CHECK | No step-by-step dev walkthrough | Maven regen lines are output verification, not implementation steps | `steps/milestone_3/instruction.md:5` |
| 5 | CHECK | No hints/solving strategies | Describes WHAT (eligibility, pipeline, formulas); points to policy docs | milestone instructions |
| 6 | CHECK | No design-doc tables | None in instructions | — |
| 7 | CHECK | Well specified | Clear per-milestone goals, absolute paths, named edge IDs | milestone instructions |
| 8 | CHECK | Interesting | Realistic multi-module Java financial batch debugging | task structure |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `steps/milestone_1/instruction.md:1-7` |
| 11 | CHECK | Task name not in instruction | No “fix-java-attachment-recovery” string | milestone instructions |
| 12 | CHECK | No canary string | None found | milestone instructions |
| 13 | CHECK | No web content fetch | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1` + hashes in `requirements.lock` | `environment/requirements.lock:11-12`, `Dockerfile:14-16` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e` | `environment/Dockerfile:2` |
| 16 | CHECK | Context in environment/ only | `COPY app/` only | `environment/Dockerfile:20` |
| 17 | CHECK | No ground truth in env | Bugs intentional; no answer leakage in docs comments | env grep |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest via `requirements.lock` in Dockerfile; `test.sh` has no pip/apt | `Dockerfile:14-16`, `steps/milestone_3/tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform oracle 100% (3/3) | `entire-report.txt:26` |
| 22 | CHECK | Oracle offline | `mvn -o`, no network in solve scripts | `steps/milestone_3/solution/apply_milestone_3.sh` |
| 23 | CHECK | Oracle derives answers | apply scripts write Java business logic, run Maven | `steps/milestone_3/solution/apply_milestone_3.sh:6-40` |
| 24 | CHECK | reward.txt canonical block | mkdir + 0 pre-write + 1/0 on result | `steps/milestone_3/tests/test.sh:3-16` |
| 25 | CHECK | Same logic oracle/agent | No `/oracle` branching | test.sh files |
| 26 | CHECK | Binary rewards | 0 or 1 only | `steps/milestone_3/tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | Each milestone test matches its instruction scope; no phantom reqs | spec alignment §5 |
| 28 | CHECK | Tests check correctness | Numeric money assertions via `expected_report()` oracle | `test_m3.py`, `test_m4.py` |
| 29 | CHECK | Behavior not implementation | Runs Maven batch, asserts JSON output | `test_helpers.py:337-347` |
| 30 | CHECK | No brittle matching (unfair) | M4 Gson regex checks are instruction-required format | `test_m4.py:54-77` |
| 31 | CHECK | Informative docstrings | Module + test docstrings present | `test_m3.py:1,17` |
| 32 | CHECK | ≥3 negative rubric criteria | 12 negatives across 4 blocks | `entire-report.txt:573-602` |
| 33 | CHECK | Scores in ±1,2,3,5 | All lines use ±1,3,5 | `entire-report.txt:568-602` |
| 34 | CHECK | Agent …, ±N format | 24 criteria, all `Agent …, ±N` | `entire-report.txt:568-602` |
| 35 | CHECK | Rubric detailed/precise | Task-specific: loader keys, pipeline order, HALF_DOWN, Gson | platform rubric |
| 36 | CHECK | Positive phrasing | Bad behaviors use negative scores (e.g. hardcoding, -5) | `entire-report.txt:573-602` |
| 37 | CHECK | No /tests/ references | None in rubric | platform rubric |
| 38 | CHECK | No task.toml/instruction refs | None in rubric | platform rubric |
| 39 | CHECK | No oracle/NOP mentions | None in rubric | platform rubric |
| 40 | CHECK | Required files present | Milestone layout: `environment/Dockerfile`, `task.toml`, per-step tests/solution | `task.toml`, `steps/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author fields | `anonymous` / `anonymous` | `task.toml:5-6` |
| 43 | CHECK | Other metadata | difficulty, category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages/category match | java, maven, bigdecimal, data-processing | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: best-model 0%, worst 80% at boundary | `entire-report.txt:21-22`, `difficulty.md` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/`; no root instruction/tests | `steps/milestone_*` |
| 47 | CHECK | solveN.sh per milestone | solve1.sh–solve4.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1.py–test_m4.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone scope | Each test file targets its milestone requirements only | `test_m1.py`–`test_m4.py` |
| 50 | CHECK | Tests not in image | `COPY app/` only; no tests COPY | `environment/Dockerfile:20` |
| 51 | CHECK | No accessible solution in env | solution/ not in image | `environment/Dockerfile` |
| 52 | CHECK | Input tampering blocked | SHA-256 guards on attachments + config | `test_helpers.py:15-74` |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80.0% — not >80% | `entire-report.txt:22` |
| 55 | CHECK | Not too hard/unfair | Failures from agent reasoning/timeouts, not spec gaps | `entire-report.txt:79-114` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: production loader reads attachment-rules.properties | `test_milestone1_minimum_threshold_loaded_from_properties` | covered | `test_m1.py:32-50` |
| M1: case-insensitive approved + minimum boundary + exposure > 0 | `test_milestone1_eligible_recovery_count` | covered | `test_m1.py:19-29` |
| M1: 26 eligible rows, boundary IDs ATT-003 in / ATT-006,026,030 out | same | covered | `test_m1.py:24-29` |
| M2: layer credit before tier adjustment | `test_milestone2_pipeline_intermediate_amounts` | covered | `test_m2.py:61-66` inequality check |
| M2: post-layer basis for plus/premium on layer lines | same | covered | `test_m2.py:48-52`, `expected_m2_tier_adjustment` |
| M2: non-layer keeps baseAttachment basis | same | covered | `test_m2.py:71-80` ATT-011 |
| M3: layer credit on baseAttachment | `test_milestone3_layer_and_holdback_rounding` | covered | `test_m3.py:25-37` layerCreditAmount fields |
| M3: HALF_DOWN rounding exceptions | same | covered | ATT-028 tier+layer, ATT-031 holdback |
| M3: processingFeeAmount in holdback taxable base | same | covered | trancheHoldbackAmount on high-fee rows ATT-015, ATT-017 |
| M3: amount-based premium rates (not tier alone) | same | covered | oracle `compute_expected` premium_threshold logic vs spot values |
| M4: netAttachment formula | `test_milestone4_report_schema_and_totals` | covered | `test_m4.py:47`, `assert_report_matches_expected` |
| M4: sort netAttachment desc, id asc | same | covered | `test_m4.py:49-51` |
| M4: generatedAt ISO-8601 | same | covered | `test_m4.py:45-46` |
| M4: Gson pretty-print colon spacing | `test_milestone4_gson_pretty_print_spacing` | covered | `test_m4.py:54-61` |
| M4: two-decimal JSON literals | `test_milestone4_money_fields_have_two_decimal_places` | covered | `test_m4.py:64-77` |
| M3: full report / all eligible rows / netAttachment at M3 stage | — | deferred to M4 | intentional milestone split; M4 full oracle |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, #46, metadata, milestone timeouts |
| `steps/milestone_1/instruction.md` | #1, #7, #10, M1 alignment |
| `steps/milestone_2/instruction.md` | M2 alignment |
| `steps/milestone_3/instruction.md` | M3 alignment, ChatGPT claim 1 |
| `steps/milestone_4/instruction.md` | M4 alignment, netAttachment scope |
| `steps/milestone_1/tests/test_m1.py` | M1 coverage |
| `steps/milestone_2/tests/test_m2.py` | M2 coverage |
| `steps/milestone_3/tests/test_m3.py` | M3 spot-check adjudication |
| `steps/milestone_4/tests/test_m4.py` | M4 full integration |
| `steps/milestone_3/tests/test_helpers.py` | `assert_report_matches_expected`, SHA guards, oracle |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/requirements.lock` | #14 pinning |
| `entire-report.txt` | agent stats, rubric, LLMaJ, test quality |
| `docs/guidelines/milestones.md` | root timeout adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate fix-java-attachment-recovery-v1./
Summary: 0 error(s), 5 warning(s), 4 info
Task type detected: milestone
Warnings: TestMilestoneN class naming (info-level style), pip hash pin validator false positive
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 0.0% (0/5) | Hardest model |
| terminus-gpt5-5 | 80.0% (4/5) | At easy-tier boundary |
| oracle | 100.0% (3/3) | Platform runs |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier | easy (at boundary) |
| Declared difficulty | hard |
| Tier match (#45) | yes — best-model 0% supports hard per difficulty.md |

Per-milestone pass rates (5 trials): M1 60%, M2 20%, M3 20%, M4 80%. M2/M3 chokepoints; infrastructure timeouts in 3/5 trials per export analysis.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone Java task; report matches folder |
| 1 Instruction | ☑ | Per-milestone instructions concise, absolute paths |
| 2 Environment | ☑ | Digest-pinned, offline, tmux+asciinema, pytest in image |
| 3 Oracle | ☑ | apply_milestone_N.sh writes real Java; platform 100% |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, behavior tests |
| 5 Metadata | ☑ | task.toml v2.0, per-step timeouts correct for milestones |
| 6 Rubric | ☑ | 4 milestone blocks, 12 negatives, correct format |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated ChatGPT + TEST QUALITY + Harbor warnings |
| 8 Novelty & fairness | ☑ | Anti-cheat SHA guards; no cheating in agent runs |
| 9 Long context | N/A | not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task — the multi-module Maven setup, SHA-256 input guards, and progressive milestone verifiers are all in great shape. I re-checked the M3 coverage concern: milestone 3 intentionally spot-checks rounding-sensitive rows (ATT-028, ATT-031, and peers) while milestone 4 runs the full report oracle on every eligible attachment, netAttachment, and summary totals, so partial engine bugs can’t slip through the full task. The platform rubric correctly uses four `# Rubric` blocks for this milestone task, and the per-step `task.toml` timeouts match the milestone layout spec. Good to accept from my side.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |

*No categories apply — disposition Accept.*
