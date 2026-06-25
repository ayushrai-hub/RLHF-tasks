# Terminus Review Report: `block-inactive-users-access`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt` 3/3; not executed locally) |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Revise. Dockerfile pinning, offline verifier deps, tests/solution exclusion, oracle pass rate, and declared `hard` difficulty (Claude 0% on best model) are solid. One real High blocker remains: `instruction.md` names the deactivated-email re-registration scenario as an “edge case” but never states the required rejection contract (HTTP 409/400, `success: false`, message containing `user already exists`), while `test_deactivated_user_cannot_reregister` enforces all three — driving 7/8 agent trials to fail that test alone. ChatGPT’s `test.sh` canonical-shape claim is not a blocker here: reward is always written at script end.

**Insights (concise):**

- Prior human feedback (`gpu_types`, early `test.sh` exit, Dockerfile `LABEL`) is already addressed in current artifacts.
- Automated review’s #45 difficulty fail is **wrong**: `difficulty.md` allows Hard when **best** model ≤20%; Claude Opus 4.8 is 0/5.
- `test.sh` omits canonical `$PWD` guard and prewrite-0 (`writing-tests.md:11-17`) but always writes binary reward after pytest (`tests/test.sh:80-84`); treat as best-practice gap, not a Revise driver.
- Re-registration is the dominant agent failure mode (3/10 per-test pass rate; 7/8 trials in failure analysis).
- Buggy `auth.service.ts:26-27` only blocks duplicate email when `existing.active` is true — reactivation is a plausible (wrong-for-tests) product choice without explicit instruction.
- Portal rubrics appear in `entire-report.txt:297-308` (6 negatives) but no `rubric.txt` in task folder — rubric checkboxes N/A for file audit.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Deactivated-account re-registration contract is tested but not specified. Instruction only mentions “edge cases … when someone registers with an email that belonged to a deactivated user” (`instruction.md:1`). Verifier requires HTTP 409 or 400, `success: false`, and message containing `user already exists` (case-insensitive). Instruction also states “Authentication rejections must use HTTP 401” (`instruction.md:5`) without carving out registration conflicts. | `instruction.md:1,5`; `tests/test_outputs.py:399-423`; `environment/repo/src/features/auth/services/auth.service.ts:26-27`; `entire-report.txt:43,60-61,80-85`; oracle fix `solution/solve.sh:131-136` | Add explicit requirement: re-registration with a deactivated account’s email must be rejected (HTTP 409 per existing controller pattern, or 400), return `success: false`, and use an application-level duplicate-email message containing `user already exists` — do not allow reactivation or a new account under that email. |

*No other High blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `instruction.md` does not define deactivated-account re-registration behavior; tests require 409/400, `success: false`, `user already exists` (ChatGPT High) | **Agree** | `instruction.md:1`; `tests/test_outputs.py:412-422`; LLMaJ `behavior_in_task_description` fail `entire-report.txt:124`; 3/10 test pass rate `entire-report.txt:43` |
| 2 | `test.sh` not canonical: missing prewrite-0 and `$PWD` guard (ChatGPT High) | **Partially agree** | Missing guard/prewrite vs `writing-tests.md:11-17`; **but** `mkdir -p /logs/verifier` (`test.sh:3`), pytest `--ctrf` (`test.sh:75-78`), binary reward on pass/fail (`test.sh:80-84`), no early exit before pytest. Validate passes `check_test_sh`. **Not a Revise blocker.** |
| 3 | `gpu_types`, `docker_flags`, `gpus` invalid in task.toml (entire-report Major) | **Disagree** (fixed) | Current `task.toml` has no such fields |
| 4 | `test.sh` should not exit early on PostgreSQL failure (entire-report Major) | **Disagree** (fixed) | `test.sh:14-16` logs warning and continues; pytest always runs |
| 5 | Dockerfile `LABEL` must not contain task content (entire-report Major) | **Disagree** | No `LABEL` in `environment/Dockerfile` |
| 6 | LLMaJ: user listing `/users/all` exclusion vague in instruction | **Partially agree** | `instruction.md:1` (“endpoints return data they shouldn't”); `tests/test_outputs.py:326-359`. Implied for trace-the-codebase scope; 8/10 pass rate. **Not a standalone blocker.** |
| 7 | Non-canonical Node base image (entire-report warning) | **Partially agree** | `Dockerfile:1` digest-pinned ECR `node:22-bookworm-slim`. Advisory per `reviewer-checklist-full.md:44`; not blocking. |
| 8 | Difficulty `hard` mismatches 40% worst-model rate (automated review #45) | **Disagree** | `difficulty.md:9-14`: Hard if ≤20% on **best OR worst**; Claude 0% (`entire-report.txt:20`) satisfies Hard via best model |
| 9 | Task “READY TO USE” / no critical issues (entire-report overall) | **Disagree** | Contradicts LLMaJ `behavior_in_task_description` fail and re-registration blocker above |
| 10 | Test quality “ACCEPT / no weaknesses” (entire-report test review) | **Partially agree** | Tests are robust HTTP behavior checks; weakness is instruction gap for re-registration, not test structure |
| 11 | Author rebuttal: clarified stale-token + multi-layer scope | **Partially agree** | `instruction.md:1` mentions tokens before state change; no explicit “401 on protected routes” sentence. Stale-token test passes 9/10 — not a blocker. Re-registration gap remains unfixed. |
| 12 | Pin postgresql/python3; move WORKDIR (entire-report Minor) | **Disagree** (addressed) | `Dockerfile:14,23,28-29` pins `python3`, `postgresql-15`, `postgresql-client-15`; `WORKDIR /app` at line 14 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 paragraphs, ~120 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Security brief tone; no spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose only | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Outcome-oriented trace/fix task | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Names problem space, not file-level HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | Re-registration contract unstated vs verifier | Blocker #1 |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic JWT/Prisma security hardening | — |
| 9 | UNCHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Not verified against corpus | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app` referenced | `instruction.md:1` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Build-time apt/npm only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, etc. | `environment/Dockerfile:31-35` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY from `environment/` only | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Buggy scaffold; oracle not in image | `environment/Dockerfile:37-40` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; no pip in test.sh | `environment/Dockerfile:31-35`; `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Oracle 100% (3/3) per report | `entire-report.txt:25` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Writes TS sources + `npm run build` | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Modifies auth repo/service, middleware, user repo | `solution/solve.sh:1-16` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | mkdir + binary 0/1 after pytest | `tests/test.sh:3,80-84` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | `echo 1` / `echo 0` only | `tests/test.sh:80-84` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Re-registration status/body/message untested in instruction | Blocker #1; `tests/test_outputs.py:412-422` |
| 28 | CHECK | Tests check for correctness, not just format | HTTP status + JSON semantics against live API | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | `requests` against localhost only | `tests/test_outputs.py` |
| 30 | UNCHECK | No brittle exact string matching where flexible checks would work | `user already exists` substring required without instruction | `tests/test_outputs.py:420-422` |
| 31 | CHECK | Tests have informative names or docstrings | Module + per-test docstrings | `tests/test_outputs.py:1-15,136+` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no `rubric.txt` in task folder | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Standard layout complete | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, timeouts, category, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | security/typescript/express/jwt match content | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Hard: Claude 0% ≤20% best-model bar | `entire-report.txt:15-21`; `difficulty.md:9-14` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — regular task | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | — |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | — |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | — |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not copied | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Runtime user creation + DB state manipulation in tests | `tests/test_outputs.py:87-127` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst model 40% | `entire-report.txt:20-21` |
| 55 | UNCHECK | Task is not too hard or unfair (not requiring unavailable info) | Re-registration contract unavailable in instruction | Blocker #1; `entire-report.txt:60-61` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 27, 30, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Inactive users blocked at login (HTTP 401) | `test_inactive_user_login_is_rejected` | covered | `instruction.md:5`; `tests/test_outputs.py:135-154` |
| Active users can still log in | `test_active_user_login_succeeds` | covered | `tests/test_outputs.py:156-168` |
| Stale access token rejected after deactivation | `test_existing_access_token_rejected_after_deactivation` | covered | `instruction.md:1` (edge case named); `tests/test_outputs.py:176-200` |
| Active user token still accepted | `test_active_user_access_token_accepted` | covered | `tests/test_outputs.py:202-221` |
| Refresh rejected for inactive account | `test_refresh_rejected_after_deactivation` | covered | `tests/test_outputs.py:229-257` |
| Active user refresh still works | `test_active_user_refresh_succeeds` | covered | `tests/test_outputs.py:259-276` |
| Active admin can access `/users/all` | `test_active_admin_can_access_admin_route` | covered | `tests/test_outputs.py:284-318` |
| Inactive admin blocked on admin route | `test_inactive_admin_cannot_access_admin_route` | covered | `tests/test_outputs.py:367-391` |
| User listings exclude inactive accounts | `test_user_list_excludes_inactive_accounts` | covered (implicit) | `instruction.md:1`; `tests/test_outputs.py:326-359` |
| Deactivated email cannot re-register (409/400, message) | `test_deactivated_user_cannot_reregister` | **gap** | `instruction.md:1` names scenario only; `tests/test_outputs.py:412-422` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, blocker 1, spec alignment |
| `tests/test_outputs.py` | #27, #30, blocker 1, spec alignment |
| `tests/test.sh` | #24, adjudication claim 2 |
| `task.toml` | #44, #45 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/repo/src/features/auth/services/auth.service.ts` | blocker 1 (buggy register logic) |
| `solution/solve.sh` | #23, oracle register fix |
| `entire-report.txt` | agent stats, LLMaJ, adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: block-inactive-users-access/ ===
Summary: 0 error(s), 3 warning(s), 1 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | 3 non-timeout failures |
| terminus-claude-opus-4-8 | 0.0% (0/5) | 4 timeouts, 1 other |
| oracle | 100.0% (3/3) | per `entire-report.txt` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Best-model rate | 40% (GPT-5.5) / 0% (Claude) |
| Observed tier | hard (via Claude ≤20%) |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular TypeScript security task |
| 1 Instruction | ☑ | Re-registration gap is sole High spec issue |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, deps in image |
| 3 Oracle | ☑ | Real multi-file TS fix; 3/3 per report |
| 4 Verifiers | ☑ | Reward always written; re-registration test misaligned |
| 5 Metadata | ☑ | Valid task.toml; hard justified |
| 6 Rubric | ☑ | Portal rubrics in report only; no local file |
| 7 LLMaJ & agent evidence | ☑ | Re-registration dominant failure pattern |
| 8 Novelty & fairness | ☑ | Unfair only on unstated re-registration contract |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Dockerfile pinning, offline verifier setup, oracle pass rate, and Hard calibration (Claude 0%) look solid. The remaining blocker is instruction↔test alignment on deactivated-account re-registration: the prompt only calls it an “edge case” but the verifier requires HTTP 409/400, `success: false`, and a message containing `user already exists`. Add that exact contract so agents are not steered toward reactivation. Optional: add canonical `$PWD` guard to `test.sh` for parity with `writing-tests.md`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Test Build Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Other | no | — |
