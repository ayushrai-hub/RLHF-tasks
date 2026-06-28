# Terminus Review Report: `ssh-bastion-policy-reload`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (100% 3/3 per platform report; not re-run locally) |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Test Build Issues

**Decision (concise):** Strong TypeScript audit-reconciliation task with canonical digest-pinned Node 22 base, offline env, variant-generation anti-hardcoding, idempotence checks, and Hard-calibrated agent rates (GPT-5.5 0%, Claude 80%). Three real blockers: (1) `instruction.md` shows a one-entry `policy_plan.json` sample while `entries_total: 3` and tests require alice/bob/carol — systematic agent misread; (2) highest-`seq` audit precedence for duplicate users is tested but unstated; (3) `test.sh` omits `mkdir -p /logs/verifier`. entire-report “non-canonical base image” claim is **false** — Dockerfile matches `docs/guidelines/dockerfxile.md` exactly.

**Insights (concise):**

- Automated review false positives on #1 (14 “paragraphs” from JSON blank lines), #6 (pipe format `user|role|seq|action` triggers table regex), and #31 (all four `test_*` have docstrings; only module-level missing — WARNING not blocker).
- LLMaJ `behavior_in_task_description` FAIL and 5/6 agent trials adding `role === "admin"` filters confirm the misleading one-entry example is the primary spec defect, not missing difficulty.
- Non-milestone task (`number_of_milestones = 0`); rubric not in repo — portal rubric must use **flat** `Agent …, ±N` format per `docs/guidelines/rubrics.md:60`, not multi-block `# Rubric 1`/`# Rubric 2` milestone layout.
- `#45` declared `hard` is defensible (best-model 0% ≤20%); `#54` passes at exactly 80% worst-model (not >80%).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | `policy_plan.json` example shows one entry (`alice`) while same instruction shows `entries_total: 3` and tests require three non-revoked active users regardless of role | `instruction.md:13-24` (one entry); `instruction.md:50` (`entries_total: 3`); `tests/test_outputs.py:13-17,90` (`EXPECTED_BASE` alice/bob/carol); `environment/docs/reload_contract.md:12` (no role filter); `entire-report.txt:50-57,72-76,108` (5/6 agents added admin-only filter; LLMaJ FAIL) | Update sample to all three entries (alice admin/3, bob maintainer/8, carol readonly/5) **or** add explicit rule: emit one entry per non-revoked active user regardless of role; mark partial examples as partial |
| 2 | High | Test Alignment/Coverage Issues | #27 | Latest audit record per user (highest `seq`) supersedes earlier grants — tested for Bob but not documented | `environment/fixtures/session-audit.jsonl:4,8` (bob operator seq 4 then maintainer seq 8); `tests/test_outputs.py:15` expects `("maintainer", 8)`; `reload_contract.md:12` lists matching records but no dedup/precedence rule; oracle `solution/oracle.patch:23-26` uses `record.seq > previous.seq` | Add to `instruction.md` or `reload_contract.md`: for each user, use the highest-`seq` grant within active generation ≤ checkpoint; if latest is revoked, user goes only in `revoke_manifest.json` |
| 3 | High | Test Build Issues | #24 | `test.sh` missing `mkdir -p /logs/verifier` before reward write | `tests/test.sh:9-16` (no mkdir); `docs/guidelines/writing-tests.md:11` canonical block requires mkdir | Add `mkdir -p /logs/verifier` per canonical `test.sh` template |

*No other High blockers. entire-report non-canonical Docker base claim rejected — see adjudication row 3.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Sample `policy_plan.json` shows only alice; verifier expects alice/bob/carol (ChatGPT High) | **Agree** | `instruction.md:16-23` vs `tests/test_outputs.py:13-17,90`; agent pattern `entire-report.txt:50-57`; LLMaJ `behavior_in_task_description` FAIL `entire-report.txt:108` |
| 2 | Latest-record-per-user rule tested but unstated; Bob seq 8 supersedes seq 4 (ChatGPT High) | **Partially agree** (gap real; severity Medium–High) | `session-audit.jsonl:4,8`; `test_outputs.py:15`; `reload_contract.md:12` silent on precedence; `entire-report.txt:274-291` calls “minor oracle-drift”; agent failures cite admin filter not bob seq |
| 3 | Non-canonical Docker base must use ghcr.io t-bench registry (entire-report CRITICAL) | **Disagree** | `environment/Dockerfile:1` = `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf4…`; matches canonical table `docs/guidelines/dockerfxile.md:10-11` exactly |
| 4 | test.sh exit-code capture fragile (entire-report WARNING) | **Agree** (non-blocker) | `tests/test.sh:9-12` uses `$?` immediately after pytest — works today; `rc=$?` pattern preferred per `writing-tests.md:20` |
| 5 | Digest-pinned env, offline setup, deterministic driver, idempotence, variant test, oracle, Hard calibration solid (ChatGPT summary) | **Agree** | `Dockerfile:1,7-14`; `task.toml:27` `allow_internet=false`; `test_outputs.py:118-135,138-160`; oracle 100% `entire-report.txt:27`; GPT 0% `entire-report.txt:23` |
| 6 | LLMaJ `behavior_in_tests` PASS / tests cover idempotence and variant | **Agree** | `entire-report.txt:109`; `test_outputs.py` four tests with field-level assertions |
| 7 | Task Instruction Sufficiency FAIL — systematic spec defect (entire-report agent analysis) | **Agree** | Root cause `entire-report.txt:68-76` matches blocker 1 evidence |
| 8 | Non-milestone task must not use milestone rubric format (user) | **Agree — N/A in repo** | `task.toml:12` `number_of_milestones = 0`; no `rubric.txt` in task folder; `docs/guidelines/rubrics.md:60` requires flat format for non-milestone; verify platform rubric is not `# Rubric 1`…`# Rubric N` multi-block |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~241 words; prose is short — 14 “blocks” are JSON schema examples split on blank lines | `instruction.md`; automated false positive |
| 2 | CHECK | Natural prompt tone | Reads like an engineer repair brief | `instruction.md:1-7` |
| 3 | CHECK | No excessive markdown | One `## Hints`; JSON schemas are required output spec | `instruction.md:66-68` |
| 4 | CHECK | No step-by-step dev steps | States command and outputs, not edit walkthrough | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Hints point to contract docs (allowed spec files) | `instruction.md:66-68`; `reload_contract.md` |
| 6 | CHECK | No design-doc I/O tables | No markdown tables; pipe format in digest spec triggered false positive | `instruction.md:64` |
| 7 | UNCHECK | Well specified | Misleading one-entry example + unstated latest-seq rule | §2 blockers 1–2 |
| 8 | CHECK | Interesting | Real audit-reconciliation debugging scenario | task design |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/src`, `/app/output`, `/app/fixtures` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | Folder name absent | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env | `environment/` |
| 14 | CHECK | Pinned pip deps | No pip; apt packages version-pinned | `Dockerfile:7-14` |
| 15 | CHECK | Digest-pinned FROM | Canonical ECR Node 22 digest | `Dockerfile:1`; `dockerfxile.md:10-11` |
| 16 | CHECK | Context in environment/ only | COPY package.json, src, fixtures, docs only | `Dockerfile:16-19` |
| 17 | CHECK | No ground truth in env | Stale user-map is intentional input, not answer | `user-map.json`; `reload.ts:77` BUG comment |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:12`; `tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) per platform | `entire-report.txt:27` |
| 22 | CHECK | Oracle offline | patch + local node driver only | `solution/solve.sh:11-16` |
| 23 | CHECK | Oracle not hardcoded | Applies patch, runs driver, sanity-checks | `solution/solve.sh`; `oracle.patch` |
| 24 | UNCHECK | reward.txt + mkdir + failure path | Missing `mkdir -p /logs/verifier` | `tests/test.sh:9-16`; §2 blocker 3 |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`; `test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `tests/test.sh:12-15` |
| 27 | UNCHECK | Tests aligned with instructions | One-entry example vs three-entry test; latest-seq unstated | §2 blockers 1–2 |
| 28 | CHECK | Tests check correctness | Field-level role/seq/generation/digest assertions | `test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Runs driver, checks JSON outputs | `test_outputs.py:25-41` |
| 30 | CHECK | No brittle exact matching | Expected values derived from fixture semantics | `test_outputs.py:13-17` |
| 31 | CHECK | Informative docstrings | All four `test_*` have docstrings | `test_outputs.py:83,97,118,138` |
| 32 | UNCHECK | ≥3 negative rubric criteria | N/A — no rubric in repo | — |
| 33 | UNCHECK | Rubric scores in {±1,2,3,5} | N/A | — |
| 34 | UNCHECK | Rubric `Agent …, ±N` format | N/A | — |
| 35 | UNCHECK | Rubric detailed/precise | N/A | — |
| 36 | UNCHECK | Positive language for negatives | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A | — |
| 40 | CHECK | Required files present | env + instruction + solution + tests + task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task root |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | timeouts, category, tags, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category match | TypeScript repair + system-administration | `task.toml:7-10` |
| 45 | CHECK | Difficulty matches agent rates | `hard` defensible: best-model 0% ≤20% | `entire-report.txt:22-23`; `difficulty.md:9-14` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — regular task | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | — |
| 48 | UNCHECK | test_mN.py per milestone | N/A | — |
| 49 | UNCHECK | Milestone test scoping | N/A | — |
| 50 | CHECK | Tests not baked in image | No COPY tests/ | `Dockerfile:16-19` |
| 51 | CHECK | Solution not in environment | No solution COPY | `Dockerfile` |
| 52 | CHECK | Agent cannot trivially pass | Variant gen-7 test prevents hardcoding | `test_outputs.py:138-160` |
| 53 | CHECK | Git repos pinned | No git clone | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 80% — not >80% | `entire-report.txt:22-23` |
| 55 | UNCHECK | Not too hard/unfair | Misleading example caused identical systematic agent misread | `entire-report.txt:50-57,68-76` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 24, 27, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Derive outputs from fixtures; no hardcoded JSON | all tests via `_run()` | covered | `instruction.md:7`; `test_outputs.py:25-41` |
| `policy_plan.json` sorted by user, `allow-user` action | `test_base_*`, `test_variant_*` | covered | `instruction.md:27`; `test_outputs.py:79-80` |
| All non-revoked active users in plan (any role) | `test_base_policy_plan_*` | **gap** | Example shows alice only `instruction.md:16-23`; test expects 3 users `test_outputs.py:13-17` |
| Revoked users only in revoke manifest | `test_base_*` | covered | `test_outputs.py:91,94`; dan revoked `session-audit.jsonl:7` |
| Latest grant per user wins (Bob maintainer/8) | `test_base_*` | **gap** | `test_outputs.py:15`; `reload_contract.md:12` no precedence rule |
| `reload_report.json` summary + checks + plan_digest | `test_report_*` | covered | `instruction.md:43-64`; `test_outputs.py:97-115` |
| Idempotent driver rerun | `test_driver_output_is_idempotent` | covered | `instruction.md:7`; `test_outputs.py:118-135` |
| Variant generation from reload-state | `test_variant_generation_*` | covered | `instruction.md:7`; `test_outputs.py:138-160` |
| Filter by active generation + checkpoint | base + variant | covered | `reload-state.env`; `test_outputs.py:89,153-154` |
| `entries_total` = len(plan entries) | `test_report_*` | covered | `test_outputs.py:106`; example contradicts visually `instruction.md:50` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers 1–2, #7, #27, #55, adjudication 1–2 |
| `environment/docs/reload_contract.md` | Blockers 1–2, spec alignment |
| `environment/fixtures/session-audit.jsonl` | Blocker 2, bob dual records |
| `environment/Dockerfile` | #15, adjudication 3 (canonical base) |
| `tests/test_outputs.py` | Blockers 1–2, #27–31, spec alignment |
| `tests/test.sh` | Blocker 3, #24 |
| `task.toml` | #43–45, milestone/rubric N/A |
| `solution/oracle.patch` | Blocker 2, #23 |
| `entire-report.txt` | Agent stats, LLMaJ, adjudication |
| `docs/guidelines/dockerfxile.md` | Adjudication 3 |
| `docs/guidelines/rubrics.md` | Rubric format check (adjudication 8) |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: ssh-bastion-policy-reload/ ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: informative_test_docstrings — module-level docstring missing (all test_* docstrings present)
INFO: submission-diversity — non-milestone not blocked; TypeScript task (not Python hard requirement)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Supports Hard tier |
| terminus-claude-opus-4-8 | 80.0% (4/5) | At easy-tier boundary |
| oracle | 100.0% (3/3) | Stable |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst) | easy (borderline) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% ≤20% justifies hard) |

Per-test pass rates (`entire-report.txt:35-38`): `test_base_policy_plan_*` 4/10, `test_report_*` 5/10 — failures align with admin-only filter from misleading example.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone TypeScript task; matches report domain |
| 1 Instruction | ☑ | Misleading example + missing latest-seq rule |
| 2 Environment | ☑ | Canonical digest-pinned Node 22; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Patch + driver; 100% platform pass |
| 4 Verifiers | ☑ | Strong tests; test.sh missing mkdir |
| 5 Metadata | ☑ | Fields complete; `number_of_milestones = 0` |
| 6 Rubric | ☑ | Not in repo — N/A checkboxes; author must use flat non-milestone format on platform |
| 7 LLMaJ & agent evidence | ☑ | behavior_in_task_description FAIL confirmed; behavior_in_tests PASS |
| 8 Novelty & fairness | ☑ | Variant test + stale map anti-cheat; example unfair until fixed |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the audit-reconciliation setup, variant-generation test, pinned offline Node environment, and anti-hardcoding design are all in great shape, and oracle runs cleanly. Three things to fix before accept: the `policy_plan.json` example in the instruction shows only alice but the report sample says `entries_total: 3` and the verifier expects alice, bob, and carol (this tripped most agents into adding an admin-only filter); please show all three active entries or state explicitly that every non-revoked user gets a plan entry regardless of role. Also document that when a user has multiple grants in the active generation, the highest `seq` record wins (Bob maintainer at seq 8, not operator at seq 4). Finally, add `mkdir -p /logs/verifier` to `test.sh` per the canonical reward block. If your platform rubric uses milestone-style `# Rubric 1`/`# Rubric 2` blocks, switch to a flat non-milestone rubric list.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Test Build Issues | yes | 3 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no (N/A in repo) | — |
| Task Difficulty | no | — |
