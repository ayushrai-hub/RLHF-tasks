# Terminus Review Report: `landlock-inherited-domain-drift`

**Generated:** 2026-06-18  
**Disposition:** Accept  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/landlock-inherited-domain-drift`

---

## 1. Executive summary

- **Recommendation:** Accept
- **Automated validation:** WARN (0 errors, 11 warnings) — manual re-audit shows all warnings are false positives or non-blocking style notes
- **Checkboxes to CHECK:** 43 items → `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55`
- **Checkboxes to UNCHECK:** 12 items → `32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49` (rubrics N/A — no `rubric.txt`; milestones N/A — regular task)

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

---

## 2. Main blockers (detailed)

**No High-severity blockers after manual re-audit.**

The automated review flagged four failures (#14, #31, #45, #54). All four are **false positives** once artifacts and agent stats are read directly (see adjudication below).

### Low — instruction density (non-blocking)

- **Severity:** Low
- **Section:** INSTRUCTION PROMPT
- **Checkbox:** #2 borderline; still passes
- **What failed:** External report warns instruction is a dense wall of text (`instruction.md:1-6`)
- **Proof files:** `instruction.md:1-6`, `entire-report.txt:176-194`
- **Required fix:** Optional — add headings/bullets for readability. Not blocking; requirements are complete and testable.

### Low — test.sh exit-code capture pattern (non-blocking)

- **Severity:** Low
- **Section:** VERIFIERS
- **What failed:** `$?` checked on line 18 after pytest on line 14–15 without immediate capture
- **Proof files:** `tests/test.sh:14-22`
- **Required fix:** Optional — capture `RESULT=$?` immediately after pytest. Works in practice today.

### Info — validator / script false positives (not blockers)

| Automated flag | Manual verdict | Evidence |
|----------------|----------------|----------|
| #14 unpinned pip | **Disagree** | `environment/Dockerfile:27-30` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` on continuation lines |
| #31 missing docstrings | **Disagree** | All 10 `test_z*` functions have docstrings; validator regex misses `-> None` return annotations (`tests/test_outputs.py:214-215`) |
| #45 difficulty mismatch | **Disagree** | Worst-model pass rate is **Claude 20%** (1/5), not GPT 100%; 20% → `hard` matches `task.toml` |
| #54 too easy | **Disagree** | Worst model 20% ≤ 80%; GPT 100% does not override worst-model tier rule |
| Non-canonical base (external report) | **Disagree** | `golang:1.24-bookworm@sha256:1a6d4452…` is listed in `docs/guidelines/dockerfxile.md:11` |

---

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise | Three prose paragraphs; within limit though dense | `instruction.md:1-6` |
| 2 | Natural prompt tone | Opens as support-ticket narrative; normative doc refs are constraints, not spec boilerplate | `instruction.md:1-2` |
| 3 | No excessive markdown | Plain prose only | `instruction.md` |
| 4 | No step-by-step solve script | Build/run commands are operational constraints for emit, not a debug walkthrough | `instruction.md:3-4` |
| 5 | No hints (WHAT not HOW) | Describes broken behavior and output contract; agents must discover bugs from docs + code | `instruction.md:1-6` |
| 6 | No design-doc tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | Well specified | Output path, 13 columns, round chain, normative doc paths all explicit | `instruction.md:3-6`, `environment/docs/h3_contract.md` |
| 8 | Interesting | Multi-file C/Go/shell pipeline repair with cryptographic contracts | task scope |
| 9 | Unique | Landlock-themed trace-matrix debugging; not a common TB2 duplicate | task content |
| 10 | Absolute paths only | `/app/...` throughout | `instruction.md:1-6` |
| 11 | Task name not in instruction | No "landlock-inherited-domain-drift" string | `instruction.md` |
| 12 | No canary string | None found | `instruction.md` |
| 13 | No web fetch in environment | No runtime URL fetches in env source | `environment/` |
| 14 | Pinned pip dependencies | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:27-30` |
| 15 | Digest-pinned FROM | `@sha256:1a6d4452…` on canonical golang base | `environment/Dockerfile:1` |
| 16 | Context stays in environment/ | COPY only from environment subdirs | `environment/Dockerfile:32-48` |
| 17 | No ground truth in environment | Intentional bugs in source are the task; normative docs define contracts, not pre-computed answers | `environment/d0/`, `environment/docs/k2_field_rules.md` |
| 18 | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | Compose does not alter Harbor mounts | No docker-compose.yaml | task root |
| 20 | Verifier deps baked; test.sh does not install packages | pytest venv in image; test.sh only invokes pytest | `environment/Dockerfile:27-30`, `tests/test.sh:14-15` |
| 21 | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | Oracle no runtime network installs | Patches sources + `make` + `go build` only | `solution/solve.sh:232-244` |
| 23 | Oracle derives answer | Fixes bugs in C/Go/shell, rebuilds, runs full round chain | `solution/solve.sh:5-244` |
| 24 | test.sh reward.txt pattern | mkdir, initial 0, 0/1 on pass/fail | `tests/test.sh:6-22` |
| 25 | Same verifier logic for oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | Binary rewards only | 0 or 1 in reward.txt | `tests/test.sh:18-21` |
| 27 | Tests aligned with instructions | All 10 tests trace to instruction + normative docs (see matrix § below) | `instruction.md`, `tests/test_outputs.py` |
| 28 | Tests check correctness | Python reference oracle computes digests, seal, marks from spec | `tests/test_outputs.py:34-134` |
| 29 | Behavior tests not implementation grep | End-to-end pipeline execution; no source grepping | `tests/test_outputs.py:199-204` |
| 30 | No brittle exact strings | Literals (`h7-v1`, `inherited`, `open`/`hold`) are normative from spec docs | `environment/docs/k2_field_rules.md`, `tests/test_outputs.py` |
| 31 | Informative test docstrings | All 10 tests named `test_zN_aN_*` with one-line docstrings | `tests/test_outputs.py:214-388` |
| 40 | Required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | Clean parent directory | No stray jobs/, README.md, data/ | task root |
| 42 | author fields present | author_name, author_email in task.toml | `task.toml:4-5` |
| 43 | Core metadata fields present | version, category, difficulty, timeouts, resources | `task.toml` |
| 44 | Tags/languages/category match | C/Go/shell debugging with SHA256/FNV contracts; security category fits sandbox/trace theme | `task.toml:7-9` |
| 45 | Difficulty matches pass rates | Declared `hard`; worst-model Claude 20% (1/5) → hard tier | `task.toml:6`, `entire-report.txt:6-7` |
| 50 | Tests not baked into image | No COPY tests/; .dockerignore excludes tests/ | `environment/Dockerfile`, `environment/.dockerignore:10-11` |
| 51 | Solution not accessible in environment | solution/ and tests/ excluded from build context | `environment/.dockerignore:10-11` |
| 52 | Agent cannot trivially modify inputs | Tests rebuild C+Go from source, run full chain, verify computed fields | `tests/test_outputs.py:162-204` |
| 53 | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | Not too easy | Worst-model 20% ≤ 80% threshold | `entire-report.txt:6-7` |
| 55 | Not too hard/unfair | Normative docs sufficient (report: instruction sufficiency PASS); Claude timeouts (4/5) appear to be time-budget not spec gaps | `entire-report.txt:31-32,68-72` |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason |
|---|--------|-------|--------|
| 32 | N/A | Rubrics ≥3 negatives | No `rubric.txt` in task folder (portal rubric in report is separate) |
| 33 | N/A | Rubric scores ±1,2,3,5 | No rubric file |
| 34 | N/A | Rubric Agent-line format | No rubric file |
| 35 | N/A | Rubric criteria precise | No rubric file |
| 36 | N/A | Rubric positive language | No rubric file |
| 37 | N/A | Rubric no /tests/ refs | No rubric file |
| 38 | N/A | Rubric no metadata refs | No rubric file |
| 39 | N/A | Rubric no oracle/NOP refs | No rubric file |
| 46 | N/A | steps/ layout | Regular task (`number_of_milestones = 0`) |
| 47 | N/A | solveN.sh per milestone | Not a milestone task |
| 48 | N/A | test_mN.py per milestone | Not a milestone task |
| 49 | N/A | Milestone test scoping | Not a milestone task |

### Quick copy-paste

**CHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55

**UNCHECK:** 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49

---

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `instruction.md` | #1, #4, #5, #7, #10, #27 |
| `task.toml` | #42, #43, #44, #45 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/h3_contract.md` | #7, #27 |
| `environment/docs/k2_field_rules.md` | #17, #27, #30 |
| `environment/docs/h3_seal.md` | #27 |
| `docs/guidelines/dockerfxile.md` | #15 (canonical base) |
| `solution/solve.sh` | #21, #22, #23 |
| `tests/test.sh` | #20, #24, #26 |
| `tests/test_outputs.py` | #27, #28, #29, #30, #31 |
| `entire-report.txt` | #21, #45, #54, #55 |

---

## 5. Validation output (re-audit)

```
./scripts/terminus validate landlock-inherited-domain-drift/
Summary: 0 error(s), 11 warning(s), 2 info
```

| Warning | Manual verdict |
|---------|----------------|
| 10× missing test docstrings | **False positive** — docstrings present; regex misses `-> None` annotations |
| Unpinned pip | **False positive** — packages pinned on continuation lines |
| Milestone preference info | N/A — regular task allowed |
| Trailing exit info in test.sh | No trailing exit; info only |

**Oracle run:** Not executed locally (Docker daemon unavailable). Report cites oracle 100% (3/3).

---

## 6. Agent performance (from report)

| Model | Pass rate |
|-------|-----------|
| terminus-claude-opus-4-8 | 20.0% (1/5) — 4 timeouts |
| terminus-gpt5-5 | 100.0% (5/5) |
| oracle | 100.0% (3/3) |
| nop | 0.0% (0/1) |

- **Worst-model rate (correct):** 20% (Claude) → tier **hard**
- **Report classified difficulty:** hard ✅
- **Timeout gate:** 4/10 real-agent timeouts (<5; not blocking)
- **All 10 unit tests:** 10/10 pass rate across agents that completed

---

## 7. Audit log

- [x] Phase 0 — Task identity confirmed: `landlock-inherited-domain-drift`, regular layout, category security, difficulty hard
- [x] Phase 1 — `instruction.md` read; 3 paragraphs, absolute paths, normative doc references, no canary/task name
- [x] Phase 2 — `environment/Dockerfile`: canonical golang digest, tmux+asciinema, no tests/solution COPY, allow_internet=false
- [x] Phase 3 — `solution/solve.sh`: patches source bugs, rebuilds, runs chain (not hardcoded JSON)
- [x] Phase 4 — `tests/test.sh` + `test_outputs.py`: reward block, no runtime installs, 10 behavior tests with docstrings
- [x] Phase 5 — `task.toml` metadata complete; timeouts 1800s agent / 1500s verifier
- [x] Phase 6 — No rubric.txt (N/A for #32–39)
- [x] Phase 7 — External report reconciled; report now matches this task (prior report was for springboot-chronos-scheduler)
- [x] Phase 8 — Multi-step debugging (6+ source files); cheating paths closed via rebuild+replay tests
- [x] Spec↔test matrix completed (below)
- [x] All external High claims challenged with file evidence

### Spec ↔ test alignment matrix

| Requirement (instruction / docs) | Test(s) | Status |
|----------------------------------|---------|--------|
| Output `/app/output/h7_trace.json` with rows + summary | test_z0_a0_schema | covered |
| 4 rows in emit order (w0_short/direct, w0_short/svc, w0_long/direct, w0_long/svc) | test_z0_a0_schema | covered |
| 13 row columns per h3_contract.md | test_z0_a0_schema | covered |
| trace_stamp = h7-v1, matrix_seal 16 hex | test_z0_a0_schema, test_z6_a6_seal | covered |
| stage_digest_hex + reach_digest formulas | test_z1_a1_digest | covered |
| w0_long carry suffix from profile_carry.txt | test_z1_a1_digest, test_z3_a3_persist, test_z8_a8_replay | covered |
| self_check_field = sha256(reach+handoff+rules)[:16] | test_z2_a2_align, test_z5_a5_rule_coupling | covered |
| Trace store byte-stable replay | test_z3_a3_persist, test_z5_a5_rule_coupling | covered |
| snap_a/snap_b marks from seeds + admission | test_z4_a4_columns | covered |
| admit_code open/hold per principal | test_z4_a4_columns | covered |
| rule_count coupling | test_z5_a5_rule_coupling | covered |
| matrix_seal FNV-1a emit-order seal | test_z6_a6_seal | covered |
| h7_drv clear resets round.seq / ledger | test_z7_a7_ledger | covered |
| Fresh chain reproducibility | test_z8_a8_replay | covered |
| chain_seq capture-before-advance | test_z9_a9_ledger_capture | covered |
| handoff_label = inherited | test_z2_a2_align (indirect via self_check) | covered (indirect) |

---

## External findings adjudication

### Claim: Non-canonical Dockerfile base image
- **Source:** `entire-report.txt:123-148`
- **Verdict:** Disagree
- **Evidence:** `environment/Dockerfile:1` uses `golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` — exact match in `docs/guidelines/dockerfxile.md:11`
- **Severity:** N/A (not a real issue)
- **Action:** none

### Claim: Verifier timeout too high (1500s)
- **Source:** `entire-report.txt:154-174`
- **Verdict:** Partially agree
- **Evidence:** `task.toml:19-20` — verifier 1500s vs agent 1800s; tests rebuild C+Go per session + 10 full-chain runs
- **Severity:** Low
- **Action:** optional — lower if profiling shows headroom

### Claim: Dense instruction impairs comprehension
- **Source:** `entire-report.txt:176-194`
- **Verdict:** Partially agree
- **Evidence:** `instruction.md:1-6` — three long paragraphs, no headings
- **Severity:** Low
- **Action:** optional formatting improvement

### Claim: Test docstrings missing
- **Source:** validate warnings + automated review #31
- **Verdict:** Disagree
- **Evidence:** `tests/test_outputs.py:215` — `"""Four rows appear in contract emit order…"""`; all 10 tests have docstrings
- **Severity:** N/A
- **Action:** none (validator regex bug with `-> None`)

### Claim: handoff_label never directly asserted
- **Source:** `entire-report.txt:299-329`
- **Verdict:** Partially agree
- **Evidence:** `tests/test_outputs.py:274-276` hardcodes `handoff="inherited"` in self_check oracle; test_z5 uses `row["handoff_label"]` for coupling
- **Severity:** Low
- **Action:** optional direct `assert row["handoff_label"] == "inherited"`

### Claim: Task too easy (GPT 100%)
- **Source:** automated review #45/#54
- **Verdict:** Disagree
- **Evidence:** `entire-report.txt:6-7` — worst model Claude 20%; difficulty tier uses worst-model rate per `docs/reviewer-checklist-ui.md:49-57`
- **Severity:** N/A
- **Action:** none

### Claim: Instruction sufficiency FAIL (prior report)
- **Source:** old entire-report.txt (springboot task)
- **Verdict:** Disagree — wrong task
- **Evidence:** Updated report lines 31-32, 68-72: instruction sufficiency PASS for landlock task
- **Action:** none

---

## 8. Reviewer note (copy-paste to portal)

Accepted. The instruction defines the trace-matrix output contract with absolute paths and normative docs; the environment uses the canonical digest-pinned golang base with tmux/asciinema and verifier deps baked in. Tests rebuild from source and verify end-to-end digest, seal, ledger, and replay behavior without implementation grep. Oracle passes per report (3/3). Worst-model pass rate is 20% (Claude), matching declared hard difficulty. No spec-test gaps or cheating paths found on re-audit. Optional polish: loosen instruction formatting and capture pytest exit code immediately in test.sh.

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus review landlock-inherited-domain-drift/ --report entire-report.txt`._
