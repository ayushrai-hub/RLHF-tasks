# Terminus Review Report: edge-device-drift-classification-auditor

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** No High or Medium blockers. Prior revision items (REVOKE_MODEL clearing `model_version`, post-sort dedup tiebreak, consistency hash, nested JSON key order, verifier baseline immutability, hard difficulty) are present in spec and tests. Platform rubric is correctly flat (non-milestone format) at 32 positive points with 7 negatives. Automated `./scripts/terminus review` false-positived #20 and #31; manual file read overturns both.

**Insights (concise):**

- `requirements.lock` installs `pytest==8.4.1` in `Dockerfile` L27–28; `test.sh` runs pytest only — #20 passes despite missing literal string `pytest` in Dockerfile.
- All 14 `test_*` functions have docstrings (`test_outputs.py` L170–339); validate regex misses return-type annotations — #31 passes.
- Platform rubric (`entire-report.txt` L327–349) is a flat `Agent …, ±N` list with no `# Rubric 2+` headers — correct for `number_of_milestones = 0`.
- Worst-model pass rate 60% (GPT-5.5) is medium tier; `task.toml` declares `hard` — informational only, not a blocker.
- `rule_catalog.json` L18–20 documents equal-seq dedup tiebreak (`scenario_50_example`); `test_equal_seq_dedup_keeps_lexicographic_region` enforces it.
- Dockerfile creates `taskagent` but never `USER taskagent` — optional Low polish, not blocking.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept; prior blockers addressed (REVOKE_MODEL, dedup, hash, nested JSON, baseline, hard difficulty) | Agree | `rule_catalog.json` L18–20,L122; `solve.sh` L318–320; `test_outputs.py` L95–105,L277–283,L324–327,L170–180 |
| 2 | ChatGPT: Dockerfile creates taskagent but no USER switch (Low) | Agree | `Dockerfile` L29–30, no `USER` directive |
| 3 | ChatGPT: digest-pinned Go base, no base-image blocker | Agree | `Dockerfile` L3 `@sha256:1a6d4452…`; comment L1–2 justifies Go 1.24 |
| 4 | Automated `terminus review`: #20 pytest missing from Dockerfile (High) | Disagree | `requirements.lock` L11–12; `Dockerfile` L27–28 `pip3 install … -r /tmp/requirements.lock`; `test.sh` L3–4,L15–16 no installs |
| 5 | Automated `terminus review`: #31 14 tests missing docstrings (High) | Disagree | `test_outputs.py` L170–171,L216–217,…,L332–333 — all 14 `test_*` have `"""…"""` docstrings |
| 6 | `entire-report.txt` L322 prior reviewer: needs REVOKE_MODEL, dedup, hash, baseline, hard | Agree (resolved) | Author note L324; artifacts above; `task.toml` L6 `difficulty = "hard"` |
| 7 | Harbor review: non-canonical base image (Warning) | Partially agree | `Dockerfile` L1–3; digest-pinned + Go 1.24 justification — acceptable per `reviewer-checklist-full.md` canonical-or-justified |
| 8 | Harbor review: dense instruction readability (Suggestion) | Agree | `instruction.md` L1–5 three dense paragraphs — Low only; requirements testable via spec refs |
| 9 | Agent failure analysis: dedup/sort interaction implicit | Partially agree | Was implicit; now explicit in `rule_catalog.json` L18–20 and `instruction.md` L3 sort-then-`first_wins` |
| 10 | Test quality review: most scenarios structurally only | Agree | `test_outputs.py` L170–213 contract + perturb anti-cheat; 13 targeted scenario tests — adequate, not blocking |
| 11 | LLMaJ: all quality checks pass | Agree | `entire-report.txt` L94–104 |
| 12 | Platform classified difficulty MEDIUM vs task.toml hard | Agree (informational) | `entire-report.txt` L16,L157; `task.toml` L6 — not a blocker per `prompt.md` #45 policy |
| 13 | Rubric positive cap and format | Agree | `entire-report.txt` L327–349 flat list; 32 pts ≤ 40; 7 negatives |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraphs, ~196 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering repair brief deferring to normative spec files | `instruction.md` L1–5 |
| 3 | CHECK | No excessive markdown formatting | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes and constraints, not dev steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT to fix/output; algorithms in spec not instruction | `instruction.md` L1 |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, behavioral rules + spec refs | `instruction.md` L1–5 |
| 8 | CHECK | Instruction is interesting | Realistic edge ML drift-audit debugging | — |
| 9 | UNCHECK | Instruction is unique | Full TB2/TB3 corpus not searched; unique in this repo | repo grep |
| 10 | CHECK | All paths in instruction are absolute | `/app/…` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Absent | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env | `Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `requirements.lock` hash-pinned `==` | `requirements.lock` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452…` | `Dockerfile` L3 |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY only env paths | `Dockerfile` L35–40 |
| 17 | CHECK | Environment does not contain solution or ground truth | Starter `reconcile.go` is broken scaffold; spec is normative rules not answers | `environment/engine/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in `requirements.lock`; pip install in Dockerfile; test.sh only runs pytest | `Dockerfile` L27–28; `test.sh` L15–16 |
| 21 | UNCHECK | Oracle passes consistently | Docker daemon unavailable locally; not executed | oracle run 2026-07-03 |
| 22 | CHECK | Oracle does not require internet | Writes Go source + `make build/audit` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full algorithmic `reconcile.go` implementation | `solution/solve.sh` L6+ |
| 24 | CHECK | test.sh writes reward.txt; handles failure | Canonical 0/1 block | `test.sh` L6,L18–22 |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `test.sh`, `test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `test.sh` L18–22 |
| 27 | CHECK | All tests aligned with instructions | Every assertion traces to instruction or normative spec | §5 below |
| 28 | CHECK | Tests check correctness not just format | Numeric/hash/flag-detail assertions on 13 scenarios + contract | `test_outputs.py` |
| 29 | CHECK | Tests verify behavior not implementation | `make audit` output JSON only | `test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | `pytest.approx` for floats; exact values warranted for flags/IDs | `test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | 14/14 `test_*` have docstrings | `test_outputs.py` L170–339 |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 7 negatives | `entire-report.txt` L343–349 |
| 33 | CHECK | Rubric scores from allowed set | ±1,2,3,5 only | `entire-report.txt` L327–349 |
| 34 | CHECK | Each rubric line starts with Agent, comma, score | 23 Agent lines | `entire-report.txt` L327–349 |
| 35 | CHECK | Rubric criteria detailed and precise | 32 positive pts (≤40) | `rubric-points` output |
| 36 | CHECK | Rubric uses positive language | Good behavior +N; bad behavior -N | `entire-report.txt` L327–349 |
| 37 | CHECK | Rubric does not reference /tests/ | None | `entire-report.txt` L327–349 |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | None | `entire-report.txt` L327–349 |
| 39 | CHECK | Rubric does not mention oracle or NOP | None | `entire-report.txt` L327–349 |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task dir |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task dir |
| 42 | CHECK | author_name and author_email present | Set | `task.toml` L4–5 |
| 43 | CHECK | All other required metadata fields present | version, timeouts, env block | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | go/bash/js ML edge task | `task.toml` L7–18 |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty` present; declared hard vs platform medium — not blocking | `task.toml` L6; `entire-report.txt` L16–22 |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml` L9 |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml` L9 |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml` L9 |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml` L9 |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `Dockerfile`; `.dockerignore` L17 |
| 51 | CHECK | Solution not accessible in environment | solution/ excluded | `.dockerignore` L16 |
| 52 | CHECK | Agent cannot trivially modify inputs | Baseline SHA256 + read-only fixtures/spec | `test_outputs.py` L151–180; `Dockerfile` L42–46 |
| 53 | CHECK | Git repos pinned to commit | No git clone | `Dockerfile` |
| 54 | CHECK | Task is not too easy | Worst-model 60% ≤ 80% | `entire-report.txt` L20–22 |
| 55 | CHECK | Task is not too hard or unfair | Rules in spec; agent failures are implementation errors | `rule_catalog.json`; agent analysis L48–66 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/build/drift_audit_report.json` via `make audit` | `test_solution_contract_integrity` | covered | `test_outputs.py` L14,L133–134 |
| 65 fixtures manifest order | `test_solution_contract_integrity` | covered | L182–185 |
| Immutable fixtures/spec/assets/Makefile/go.mod | `test_solution_contract_integrity` | covered | L170–180 |
| Alphabetical JSON keys (nested) | `test_solution_contract_integrity` | covered | L95–105,L202 |
| Compact deterministic encoding | `test_solution_contract_integrity` | covered | L204–211 |
| status CONSISTENT / DRIFT_DETECTED | `test_solution_contract_integrity` | covered | L190–197 |
| STALE_CALIBRATION detail = version | `test_stale_calibration_detail_is_version` | covered | L216–221 |
| policy_overrides calibration_gate | `test_policy_override_disables_stale_calibration` | covered | L236–240 |
| OUT_OF_RANGE_QUANT + QUANT_MISMATCH | `test_dual_quant_flags_per_channel` | covered | L223–233 |
| METADATA_CORRUPT + inference without lock | `test_weights_digest_and_inference_without_lock_row` | covered | L243–254 |
| Post-replay after skipped duplicate | `test_post_audit_after_skipped_duplicate` | covered | L256–264 |
| REGION_DIVERGENCE + FEATURE_SCALE_DRIFT same region | `test_same_region_dual_post_audit_flags` | covered | L266–275 |
| Equal-seq dedup lex-first region | `test_equal_seq_dedup_keeps_lexicographic_region` | covered | L277–283 |
| DUPLICATE_SAMPLE preserves Welford | `test_duplicate_rejected_lock_preserves_welford` | covered | L285–291 |
| Agreeing classes skip REGION_DIVERGENCE | `test_agreeing_classes_skip_region_divergence` | covered | L294–300 |
| SET_CALIBRATION before REGISTER_REGION | `test_set_calibration_before_region_register` | covered | L303–315 |
| L2 threshold 0.5 suppresses drift | `test_l2_strict_threshold_suppresses_drift` | covered | L318–321 |
| consistency_hash multi-region | `test_multi_region_unlocked_inference_hash` | covered | L324–330 |
| REGISTER_REGION before LOCK at equal seq | `test_equal_seq_register_before_lock` | covered | L332–339 |
| REVOKE_MODEL clears model_version | contract across 65 scenarios + rule_catalog | covered | `rule_catalog.json` L122; structural pass all scenarios |
| Anti-cheat perturbation | `_grading_setup` | covered | L107–148 |
| Binary at `/app/build/driftaudit` not `/app/driftaudit` | `test_solution_contract_integrity` | covered | L212–213 |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, §5 |
| `task.toml` | #42–45, #46–49 N/A |
| `environment/Dockerfile` | #13–20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `environment/spec/rule_catalog.json` | §5 REVOKE_MODEL, dedup, adjudication |
| `environment/spec/output_schema.json` | §5 schema alignment |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, §5 |
| `solution/solve.sh` | #22–23 |
| `entire-report.txt` | #32–39, §7, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate edge-device-drift-classification-auditor/
Summary: 0 error(s), 16 warning(s), 1 info
```

Warnings are docstring-regex false positives and `rule_catalog.json` hint-pattern heuristics — not blockers after manual read.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Per export |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — CHECK #45 |

### Rubric (platform)

| Field | Value |
|-------|-------|
| Format | Flat `Agent …, ±N` — **not** milestone `# Rubric N` blocks |
| Positive total | 32 |
| Negative count | 7 |
| Cap status | PASS (32/40) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone Go/Node task |
| 1 Instruction | ☑ | Dense but complete; defers to spec |
| 2 Environment | ☑ | Pinned, offline, tmux/asciinema, baseline |
| 3 Oracle | ☑ | Algorithmic solve.sh; oracle not run (no Docker) |
| 4 Verifiers | ☑ | 14 tests + contract; deps in image |
| 5 Metadata | ☑ | hard, machine-learning, tool_specific |
| 6 Rubric | ☑ | Flat non-milestone format; 32 pts; 7 negatives |
| 7 Agent evidence | ☑ | 60% worst — not too easy |
| 8 Fairness | ☑ | Dedup rule now explicit in spec |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice work on this one — the spec files are thorough, the verifier is strong (perturbation anti-cheat, baseline immutability, nested key-order checks, and targeted scenario tests), and the platform rubric is correctly formatted for a non-milestone task at 32 positive points. Prior feedback on REVOKE_MODEL, post-sort dedup tiebreaking, consistency hash, and hard difficulty all look addressed. I didn't find any blocking spec-test gaps. Optional polish: consider `USER taskagent` in the Dockerfile if you want the agent runtime explicitly unprivileged — not required given baseline checks.

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
