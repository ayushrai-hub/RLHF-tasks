# Terminus Review Report: tls-keyshare-policy-witness

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail |
| **Oracle** | pass (not re-run locally; 100% 3/3 per `entire-report.txt`) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Metadata Issues

**Decision (concise):** The task is otherwise strong: canonical digest-pinned Go 1.24 base, offline verifier, rich gate-ladder tests, anti-cheat stub design, oracle pass rate, and Hard-tier calibration (GPT-5.5 at 20%) all check out. The sole real blocker is `task.toml` declaring `version = "1.0"` instead of the required Edition 2 value `version = "2.0"` — `./scripts/terminus validate` fails on this field.

**Insights (concise):**

- ChatGPT's version finding is confirmed; no other High-severity blockers survive manual re-audit.
- Automated `terminus review` falsely flagged #31 (docstrings) and #45 (difficulty); both disproven on file read.
- LLMaJ "non-canonical base image" is wrong: Dockerfile digest matches `docs/guidelines/dockerfxile.md:11`.
- Agent idempotency failures (34/36) stem from bypassing the named witness binary; instruction frames `/app/bin/keyshare_witness` as the delivery path — agent UX note, not a revision driver.
- Sort-order test omits `observed_ts_ns` tiebreaker (Low); current fixtures do not expose the gap.
- Rubric criteria appear only in `entire-report.txt` (portal UI); task folder has no `rubric.txt` — #32–#39 N/A.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Metadata Issues | #43 | `task.toml` uses `version = "1.0"`; Edition 2 requires `"2.0"` | `task.toml:1`; `docs/task-requirements.md:33`; `./scripts/terminus validate` → `ERROR: version must be "2.0"` | Set `version = "2.0"` in `task.toml` |

*No other High-severity blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: `version = "1.0"` must be `"2.0"` — Needs Revision | **Agree** | `task.toml:1`; validate ERROR; `docs/task-requirements.md:33` |
| 2 | ChatGPT: digest-pinned env, offline verifier, oracle, anti-cheat, schema, gate coverage, Hard calibration all solid | **Agree** | `environment/Dockerfile:1,13-15,32-35`; `tests/test_outputs.py`; `entire-report.txt:15-26,117-127` |
| 3 | LLMaJ CRITICAL (`entire-report.txt:156-174`): version 1.0 vs 2.0 | **Agree** | Same as blocker 1 |
| 4 | LLMaJ WARNING: non-canonical Go base image | **Disagree** | `environment/Dockerfile:1` digest `sha256:1a6d4452...` matches canonical `docs/guidelines/dockerfxile.md:11` |
| 5 | LLMaJ WARNING: instruction lacks inline JSON schema | **Partially agree** (Low) | `instruction.md:3` points to `/app/data/admission_policy/output_envelope.json`; schema is complete there — deliberate indirection for Hard task |
| 6 | Agent analysis (`entire-report.txt:71-115`): idempotency test unfair; agents bypass stub binary | **Partially agree** (not blocker) | `instruction.md:1` names witness at `/app/bin/keyshare_witness`; `main.go:1-6` STUB comment; `test_outputs.py:312-317` re-runs binary; LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:118`) |
| 7 | Test quality (`entire-report.txt:327-357`): sort test omits `observed_ts_ns` | **Partially agree** (Low) | `test_outputs.py:112-120` asserts 3 keys; `output_envelope.json:59` specifies 4; `decision_fields` lacks `observed_ts_ns` — gap theoretical only |
| 8 | Automated review: #31 missing test docstrings | **Disagree** | All 36 `test_*` functions have docstrings (`test_outputs.py:58-333`); validate WARNING is module-level only |
| 9 | Automated review: #45 difficulty mismatch (worst 60% → medium) | **Disagree** | `entire-report.txt:20-21` GPT-5.5 20% (1/5); `docs/guidelines/difficulty.md:9` Hard = ≤20% on **best OR worst** model |
| 10 | Agent analysis: `REJECTED_TYPE` vs `INVALID` underspecified | **Disagree** (as blocker) | `instruction.md:3` lists gate order "type, required, service..."; `test_outputs.py:123-127` pins obs-003 → REJECTED_TYPE; `output_envelope.json:80` type_strict_fields |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | 3 short paragraphs, ~150 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer rollout note, no LLM preamble | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States WHAT (gates, paths, wrinkles) | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | No algorithm walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | No input/output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Binary path, output path, schema ref, verdict enum, gate order | `instruction.md:1-5` |
| 8 | CHECK | Interesting | PQ TLS admission policy witness — real security domain | — |
| 9 | CHECK | Unique | Multi-format config + gate ladder + HMAC seal rescue | — |
| 10 | CHECK | Absolute paths only | All paths `/app/...` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No slug in body | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | `GOPROXY=off`; local data only | `environment/Dockerfile:8,22-30` |
| 14 | CHECK | Pip deps pinned with == | pytest and ctrf pinned | `environment/Dockerfile:15` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452...` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | COPY only env subdirs | `environment/Dockerfile:22-30` |
| 17 | CHECK | No ground truth in env | Stub emits empty envelope only | `environment/keyshare_engine/main.go:14-38` |
| 18 | CHECK | No privileged/docker.sock | Standard RUN/COPY | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:15`, `tests/test.sh:11-12` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:25` |
| 22 | CHECK | Oracle no internet | `GOPROXY=off`, local build | `environment/Dockerfile:8`, `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | ~800-line Go implementation written at runtime | `solution/solve.sh:6+` |
| 24 | CHECK | reward.txt + failure path | Canonical block | `tests/test.sh:2-3,13-17` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards 0/1 | echo 0 or 1 only | `tests/test.sh:14-16` |
| 27 | CHECK | Tests aligned with instructions | Every instruction req traced to tests (§5) | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness | Per-obs verdicts, counts, digest, idempotency | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | JSON output assertions only | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string checks | Structured JSON + digest recompute | `tests/test_outputs.py:286-302` |
| 31 | CHECK | Informative test docstrings | All 36 test methods documented | `tests/test_outputs.py:58-333` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task dir | — |
| 33 | UNCHECK | Rubric scores from allowed set | N/A | — |
| 34 | UNCHECK | Rubric format Agent …, ±N | N/A | — |
| 35 | UNCHECK | Rubric criteria detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task dir | task root |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | UNCHECK | All other required metadata fields present | `version` field wrong value (`1.0` not `2.0`) | `task.toml:1` |
| 44 | CHECK | Tags/languages/category applicable | Go security task; tags match | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches agent pass rates | Declared `hard`; GPT-5.5 20% qualifies Hard tier | `task.toml:6`; `entire-report.txt:20-21`; `docs/guidelines/difficulty.md:9` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | — |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | — |
| 49 | UNCHECK | Milestone tests scoped | N/A | — |
| 50 | CHECK | Tests NOT baked into image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Digest + per-obs checks; shards immutability test | `tests/test_outputs.py:320-325` |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 60% < 80% rejection threshold | `entire-report.txt:20-21` |
| 55 | CHECK | Not unfair | Instruction names binary witness; stub labeled; oracle demonstrates fix | `instruction.md:1`, `main.go:1-6` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 32, 33, 34, 35, 36, 37, 38, 39, 43, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Witness writes `/app/output/expected.json` | `test_output_file_exists_at_pinned_path` | covered | `instruction.md:1`, `test_outputs.py:58-61` |
| Four top-level keys | `test_envelope_has_four_top_level_keys` | covered | `instruction.md:3`, `test_outputs.py:64-67` |
| 36 observations from three shards | `test_total_observations_equals_input_line_count` | covered | `test_outputs.py:70-72` |
| Full verdict closed enum in by_verdict | `test_by_verdict_contains_full_closed_enum` | covered | `instruction.md:3`, `test_outputs.py:81-84` |
| Gate ladder verdict tallies | `test_verdict_counts_match_expected_oracle_tallies` | covered | `test_outputs.py:87-101` |
| successful + rejected = total | `test_successful_and_rejected_sum_to_total` | covered | `test_outputs.py:104-109` |
| Decisions sort chain | `test_decisions_sorted_severity_then_service_then_ts_then_observation` | covered (3/4 keys) | `test_outputs.py:112-120`; `observed_ts_ns` not in decision output |
| REJECTED_TYPE for type gate | `test_rejected_type_on_stringy_timestamp` | covered | `test_outputs.py:123-127` |
| INVALID for missing required field | `test_invalid_when_offered_groups_field_missing` | covered | `test_outputs.py:130-132` |
| UNKNOWN_SERVICE | `test_unknown_service_for_unregistered_service_id` | covered | `test_outputs.py:135-137` |
| GROUP_BANNED + seal rescue | `test_group_banned_*`, `test_seal_rescued_*`, `test_invalid_seal_pin_*` | covered | `test_outputs.py:140-165` |
| QUOTA_EXHAUSTED + seal bypass | `test_quota_exhausted_*`, `test_seal_rescued_does_not_consume_quota_slot` | covered | `test_outputs.py:168-180` |
| Client tier override | `test_client_override_flips_legacy_proxy_to_pq_mandatory` | covered | `test_outputs.py:183-186` |
| Alias → canonical matched_group | `test_group_alias_resolves_to_canonical_in_matched_group` | covered | `test_outputs.py:189-193` |
| Phase/tier outcomes (pre-rollout, grace, pq_mandatory) | `test_pre_rollout_*` through `test_classic_only_*` | covered | `test_outputs.py:196-244` |
| Rate limiting | `test_rate_limited_seventh_handshake_in_window` | covered | `test_outputs.py:246-248` |
| by_service aggregates | `test_by_service_*` | covered | `test_outputs.py:251-283` |
| report_digest SHA-256 prefix | `test_report_digest_*` | covered | `test_outputs.py:286-309` |
| Binary idempotency | `test_idempotent_rerun_yields_identical_envelope` | covered | `instruction.md:1`, `test_outputs.py:312-317` |
| Shard immutability | `test_observation_shards_immutability` | covered | `test_outputs.py:320-325` |
| Global chronological merge | `test_shards_globally_sorted_in_processing_order_implied_by_quota_outcome` | covered | `test_outputs.py:328-333` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker 1, #43, #44, #45 |
| `instruction.md` | #1-12, #27, spec alignment |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/keyshare_engine/main.go` | #17, #55 |
| `environment/admission_policy/output_envelope.json` | #7, spec alignment |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #21, #45, #54, agent stats |
| `docs/guidelines/difficulty.md` | #45 |
| `docs/guidelines/dockerfxile.md` | Adjudication #4 |
| `docs/task-requirements.md` | Blocker 1 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: tls-keyshare-policy-witness/ ===
ERROR: task.toml [task.toml]: version must be "2.0"
WARNING: informative_test_docstrings [tests/test_outputs.py]: Test file should have a module-level docstring
Summary: 1 error(s), 1 warning(s)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Qualifies Hard tier |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Medium tier individually |
| oracle | 100.0% (3/3) | Per `entire-report.txt` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Best-model rate | 20.0% |
| Observed tier | hard (GPT ≤20%) |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task folder matches report; regular layout |
| 1 Instruction | ☑ | Concise, absolute paths, schema via envelope file |
| 2 Environment | ☑ | Canonical Go digest, tmux+asciinema, no tests/solution COPY |
| 3 Oracle | ☑ | Full Go derivation; 100% per report |
| 4 Verifiers | ☑ | Canonical reward block; 36 behavior tests with docstrings |
| 5 Metadata | ☐ | `version = "1.0"` blocks validation |
| 6 Rubric | ☑ | N/A — portal-only |
| 7 LLMaJ & agent evidence | ☑ | Version confirmed; difficulty/idempotency claims challenged |
| 8 Novelty & fairness | ☑ | Multi-step; no cheating paths |
| 9 Long context | ☑ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The digest-pinned Go environment, offline verifier setup, oracle pass rate, anti-cheat design, output schema, gate-ladder coverage, HMAC seal checks, and Hard difficulty calibration all look solid. The only blocking issue is metadata: `task.toml` still uses `version = "1.0"` instead of the required Edition 2 value `version = "2.0"`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
