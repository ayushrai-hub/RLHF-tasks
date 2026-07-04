# Terminus Review Report: `lua-pg-tls-profile-drift-triage`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally; platform report: 100% 3/3) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong multi-module Lua/PostgreSQL TLS reconciliation task with pinned offline environment, independent reference verifier, and appropriate hard-tier agent rates (0–20%). Two confirmed High spec↔verifier gaps block acceptance: `inventory_digest` sort order in `reconcile_contract.md` says sort by `serial` but oracle/reference sort full `serial:fingerprint` lines (order diverges for `SN-FRAUD` vs `SN-FRAUD-LEGACY`), and seed `sha256_hex` values are 65 chars for four rows while the contract mandates 64-char SHA-256 with no odd-length normalization rule. Fix contract and/or reference first.

**Insights (concise):**

- ChatGPT’s digest-sort and odd-length-hex findings are **confirmed** with line-level proof; these are the only real blockers.
- Automated `terminus review` blockers for #14, #20, #31 are **false positives** — `requirements.lock` pins with `==`+hashes, pytest is baked in the image, and all eight tests have docstrings.
- `drift_rows` “all inventory vs active” is **not** a blocker — contract already says “inventory row exists” (not “active row”); reference behavior is defensible.
- Platform rubric uses optional `# Rubric 1` header on a non-milestone task — **allowed** per `rubrics.md`; positive total 39 ≤ 40 cap.
- Worst-model pass rate 0% (GPT-5.5); declared `hard` aligns with observed tier.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | `inventory_digest` sort rule in contract says sort active rows by `serial`, but verifier/oracle sort completed `serial:canonical_fingerprint` strings lexicographically — different order for prefix serials | `reconcile_contract.md:25` says “sorting active inventory rows by `serial`”; `tests/test_outputs.py:164-165` `sorted(f"{row['serial']}:{row['fingerprint']}" ...)`; `solution/solve.sh:247-251` `table.sort(digest_lines)`; serial-order `['SN-FRAUD','SN-FRAUD-LEGACY',…]` vs line-order `['SN-FRAUD-LEGACY','SN-FRAUD',…]` (ASCII `-` 45 < `:` 58 at position 9) | Align contract to “sort `serial:canonical_fingerprint` lines lexicographically” **or** change reference/oracle to sort by `serial` then join |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Contract says inventory stores 64-char `sha256_hex`; seed has four 65-char values; canonicalization preserves trailing nibble as single-char segment — behavior undocumented | `reconcile_contract.md:9` “64 hex chars”; `seed_inventory.sql:4-7` SN-LEDGER/SN-FRAUD/SN-FRAUD-LEGACY/SN-SETTLE are 65 chars; `_canonical_fp` / `fpcanon.lua` pair-wise loop keeps odd final nibble; agents dropping nibble fail digest | Fix seed to valid 64-char hex **or** document odd-length normalization in contract |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Digest sort: contract says serial-sort, verifier sorts full lines (ChatGPT / entire-report) | **Agree** | See blocker #1 proof |
| 2 | Odd-length `sha256_hex`: contract says 64 chars, seed has 65-char rows, verifier keeps trailing nibble (ChatGPT) | **Agree** | See blocker #2 proof |
| 3 | Clarify drift_rows checked against all `cert_inventory` rows including revoked/expired (ChatGPT Medium) | **Partially agree** | `reconcile_contract.md:60` “when an inventory row exists” (not “active”); `tests/test_outputs.py:97-98` builds `inventory_all_fps` from all rows; wording could be clearer but is not contradictory — **not a blocker** |
| 4 | Rubric PyYAML “via pip install” wording (ChatGPT Low) | **Agree (Low only)** | `entire-report.txt:347` “pip install or implementing a Lua-based fallback”; deps preinstalled in image — polish only, not a blocker |
| 5 | Dockerfile FROM digest-pinned canonical base (ChatGPT) | **Agree** | `environment/Dockerfile:2` `@sha256:01f42367…` |
| 6 | Decision Needs Revision (ChatGPT) | **Agree** | Blockers #1–#2 confirmed |
| 7 | Automated review: #14 unpinned pip | **Disagree** | `environment/requirements.lock` uses `package==version` with `--hash=sha256`; Dockerfile installs via `--require-hashes` |
| 8 | Automated review: #20 pytest not in image | **Disagree** | `environment/Dockerfile:21-23` installs `pytest==8.4.1` into `/opt/verifier-venv`; `tests/test.sh:14-17` only runs pytest |
| 9 | Automated review: #31 missing docstrings | **Disagree** | All eight `test_*` functions have docstrings at `tests/test_outputs.py:189-269` |
| 10 | Non-milestone task uses milestone rubric format (`# Rubric 1`) | **Disagree (not a blocker)** | `task.toml:9` `number_of_milestones = 0`; `rubrics.md:66` “`# Rubric 1` optional; no `# Rubric 2+`”; single header alone is allowed |
| 11 | Rubric positive total >40 | **Disagree** | Sum of +lines in platform rubric = 39 (≤40 cap) |
| 12 | Instruction sufficiency FAIL in export (entire-report) | **Partially agree** | Failure analysis correctly identifies digest edge cases; root cause is contract/test mismatch, not missing instruction pointer to contract docs |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two paragraphs, ~179 words | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Production-incident tone, not numbered spec | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | No HOW steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Points to contract docs only | `instruction.md` |
| 6 | CHECK | No design doc style tables | None in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Clear output path, fields, and doc references | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic TLS/Postgres ops scenario | — |
| 9 | CHECK | Instruction is unique | Novel multi-module Lua TLS drift task | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | Lockfile pins with hashes | `environment/requirements.lock`, `environment/Dockerfile:21-23` |
| 15 | CHECK | Base Docker image is pinned by digest | Digest-pinned FROM | `environment/Dockerfile:2` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY only environment | `environment/Dockerfile:36` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Contract docs are normative spec, not answers | `environment/docs/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Not executed locally (no Docker); platform 100% unverified here | `entire-report.txt:58` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh writes Lua sources only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Derives via pipeline, no echo of JSON | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:6-23` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No /oracle branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1) | 0/1 reward | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Digest sort + odd-length hex tested but contract contradicts/misses behavior | Blockers #1–#2 |
| 28 | CHECK | Tests check for correctness, not just format | Independent `_ref_reconcile` recompute | `tests/test_outputs.py:75-181` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Field-level equality against reference is appropriate | `tests/test_outputs.py:195-202` |
| 31 | CHECK | Tests have informative names or docstrings | All eight tests have docstrings | `tests/test_outputs.py:189-269` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives in platform rubric | `entire-report.txt:350-352` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All ±1,2,3,5 | `entire-report.txt:337-352` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 15 Agent lines | `entire-report.txt` |
| 35 | CHECK | Rubric criteria are detailed and precise | 39 positive pts ≤40 cap | `entire-report.txt` |
| 36 | CHECK | Rubric criteria use positive language | Positives phrased as fixes; negatives as penalties | `entire-report.txt` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt` |
| 40 | CHECK | All required files present | All present | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | Complete | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | lua/sql/bash, system-administration, TLS/Postgres | `task.toml` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` declared; worst-model 0%; platform classified hard | `task.toml`, `entire-report.txt` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:9` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:9` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:9` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not copied | `environment/Dockerfile:36` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Verifier re-seeds DB each run | `tests/test_outputs.py:24-31` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 0% | `entire-report.txt:52-54` |
| 55 | UNCHECK | Task is not too hard or unfair | Agents following written serial-sort spec fail verifier; odd-length hex undocumented | Blockers #1–#2; `entire-report.txt:89-91` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/out/reconcile_report.json` via pipeline | all tests via `_run_reconcile` | covered | `instruction.md:3`, `tests/test_outputs.py:41-52` |
| Report fields: api_version, rollover_epoch, inventory_digest, trust_anchors, service_bindings, drift_rows | `test_regenerated_doc_header_fields`, `test_regenerated_doc_matches_ref` | covered | `instruction.md:3`, `tests/test_outputs.py:205-202` |
| Digest: active rows, serial sort, `serial:canonical_fingerprint` | `test_digest_gate_active_serials`, `test_regenerated_doc_matches_ref` | **gap** | Contract `reconcile_contract.md:25` vs `tests/test_outputs.py:164-165` sort mismatch |
| Fingerprint canonicalization: 64-char hex → colon octets | `test_binding_gate_four_services`, reference builder | **gap** | Contract `reconcile_contract.md:9` vs 65-char seed `seed_inventory.sql:4-7` |
| 14-day grace window (Amendment 7) | `_ref_reconcile` grace filter | covered | `rollover_runbook.md:5`, `tests/test_outputs.py:81-87` |
| YAML anchor precedence over TOML (Amendment 9) | `test_phantom_toml_anchor_absent` | covered | `rollover_runbook.md:9`, `tests/test_outputs.py:264-269` |
| Service bindings via `role_bindings.client_ca_serial` | `test_binding_gate_four_services` | covered | `reconcile_contract.md:48`, `tests/test_outputs.py:129-146` |
| Drift rows: bare config hex vs canonical when inventory match | `test_drift_gate_normalization` | covered | `reconcile_contract.md:60`, `tests/test_outputs.py:147-163` |
| Hand-written JSON insufficient | `test_static_doc_insufficient` | covered | `instruction.md:5`, `tests/test_outputs.py:246-261` |
| JSON schema validation | `test_regenerated_doc_passes_validator` | covered | `tests/test_outputs.py:189-192` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, #27 |
| `task.toml` | #42–45, #46–49 N/A |
| `environment/Dockerfile` | #13–20, #50 |
| `environment/requirements.lock` | #14 |
| `environment/docs/reconcile_contract.md` | Blockers #1–#2, spec alignment |
| `environment/sql/seed_inventory.sql` | Blocker #2 |
| `environment/manual/rollover_runbook.md` | Grace/precedence rules |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | Blockers #1–#2, #27–31, #55 |
| `solution/solve.sh` | Blocker #1, #23 |
| `entire-report.txt` | #32–39, #45, #54, agent stats, rubric |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate lua-pg-tls-profile-drift-triage/
Summary: 0 error(s), 10 warning(s), 2 info
Task type detected: regular
```

Warnings are informational (missing module docstring validator false-positive on per-test docstrings; non-milestone preference info).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | — |
| terminus-claude-opus-4-8 | 20.0% (1/5) | — |
| oracle | 100.0% (3/3) | platform report only |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes |

Per-test: digest tests (`test_regenerated_doc_matches_ref` 1/10, `test_digest_gate_active_serials` 2/10) dominate failures — consistent with spec edge-case gaps.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular (non-milestone) layout |
| 1 Instruction | ☑ | Concise, absolute paths, delegates to contract docs |
| 2 Environment | ☑ | Digest-pinned base, tmux/asciinema, verifier venv, no tests/solution COPY |
| 3 Oracle | ☑ | Real Lua rewrites; not run locally |
| 4 Verifiers | ☑ | Reference recompute, reward block OK; spec gaps in digest |
| 5 Metadata | ☑ | category/tags/languages fit; `number_of_milestones = 0` |
| 6 Rubric | ☑ | 39 pts, 3 negatives, `# Rubric 1` optional on non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Export failure analysis corroborates digest blockers |
| 8 Novelty & fairness | ☑ | Multi-step, anti-cheat strong; digest spec unfair |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the multi-module Lua pipeline, live PostgreSQL re-seed, and independent reference verifier are well designed, and the difficulty calibration looks right. Two contract issues need fixing before we can accept: (1) `reconcile_contract.md` says to sort active inventory rows by `serial` for the digest, but the verifier and oracle sort the full `serial:canonical_fingerprint` lines, which changes order for prefix serials like `SN-FRAUD` vs `SN-FRAUD-LEGACY`; please align the contract text with the verifier or change the sort in the reference. (2) The contract says inventory `sha256_hex` is 64 characters, but four seed rows are 65 chars and the verifier keeps the trailing nibble as its own segment — either normalize the seed data to 64-char hex or document that odd-length behavior explicitly. Optional polish: clarify drift_rows use all `cert_inventory` rows (not just active), and rephrase the rubric PyYAML line to reference preinstalled deps instead of pip install.

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
