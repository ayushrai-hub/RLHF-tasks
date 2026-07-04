# Terminus Review Report: `awk-exhibit-signature-policy-audit`

**Generated:** 2026-07-04 16:45 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/awk-exhibit-signature-policy-audit`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 100% 3/3; local Harbor oracle unavailable) |
| **CHECK count** | 53 |
| **UNCHECK count** | 2 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** Spec, environment, anti-cheat, and rubrics are solid — everything except difficulty calibration holds up. After re-checking agent evidence, declared `hard` is not supported: Opus 4.8 passes 5/5 in the platform export, M2 per-test rates are 10/10, and the normative `signing_policy.md` reduces the task to straight policy implementation. GPT-5.5’s headline 20% (1/5) rides on milestone all-or-nothing grading and edge-case slips, not on agents lacking the reasoning to solve end-to-end; trajectory review indicates GPT at 5/5 with Opus’s two misses being output-token exhaustion (M3) and M1 timeout after bugs were already identified — execution artifacts, not task hardness. Observed tier is **medium** (worst-model ~60% if Opus credited at 3/5), not hard. Author should either harden the task materially or re-tier to medium before acceptance.

**Insights (concise):**

- Platform export: Opus **100% (5/5)**, GPT **20% (1/5)** — but failure analysis shows GPT trial LFJVDzc passed **12/17 individual tests** with **0.0 reward** because no milestone was fully clean (`entire-report.txt:54`).
- Per-test pass rates: M2 nearly all **10/10**; M1/M3 authority tests **6–8/10** — agents reach correct logic on most assertions once engaged.
- Failure analysis documents **tooling/execution** failures (heredoc escaping, tmux crash, type coercion) alongside policy edge cases — not unavailable information (`entire-report.txt:64-68,80`).
- `signing_policy.md` is a complete normative spec (reconciliation, manifest, revocation taxonomy) — strongest models implement it directly.
- Rubric, Dockerfile, milestone layout, and anti-cheat design remain clean; difficulty is the sole revision driver.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 (informational), author action | Declared `hard` / platform HARD not supported by agent evidence; strongest model 5/5; task is policy-doc implementation | `entire-report.txt:14-20,30-47,52-93`; `task.toml:6`; `signing_policy.md:55-145` | Re-tier to **medium** in `task.toml` and resubmit, **or** add genuine difficulty (remove/shrink normative policy walkthrough, add non-obvious integration traps, tighten milestone gates only after reasoning is tested) |

*Note:* Formal **#54** auto-blocker (>80% worst-model) is **not** triggered if Opus is credited at 3/5 (60% worst) per trajectory review. It **would** trigger if both reference models are 5/5 (export already shows Opus 100%; peer credits GPT 100%).

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | GPT-5.5 solved 5/5 (100%) — peer trajectory review | **Partially agree** | Export header says 20% (`entire-report.txt:20`); failure analysis shows near-complete individual test success and tooling-only failures (`entire-report.txt:54,64-68,80`). Trajectory-level 5/5 not in export — credited on peer review; undermines hard-tier floor. |
| 2 | Opus misses are token-limit (M3) and M1 timeout after bugs found — not reasoning | **Partially agree** | Export shows Opus **100% (5/5)** (`entire-report.txt:19`) — contradicts “two misses” unless reviewing a different batch. Failure analysis separately documents execution/tooling failures for other trials (`entire-report.txt:64-68`). Substance: failures are not “unavailable info” gaps. |
| 3 | MEDIUM tier rides on execution artifacts, not real difficulty | **Agree** | Opus 100% + M2 10/10 + policy-as-spec + milestone-gated GPT stat → observed **medium**, not hard |
| 4 | Strongest model treats this as straight policy-doc implementation | **Agree** | `signing_policy.md` specifies reconciliation, manifest, verify methods, remediation taxonomy line-by-line; instructions point agents there |
| 5 | Everything else clean (spec, anti-cheat, env, rubric) — peer reviewer | **Agree** | Prior artifact review unchanged — milestone layout, authority tests, hashed lock, per-block rubric caps |
| 6 | ChatGPT Accept — no blockers | **Partially agree** | Agree on artifact quality; **disagree** on difficulty — hard classification not defensible |
| 7 | Platform classified HARD (`entire-report.txt:14`) | **Disagree as accurate** | Opus 100%; GPT 20% is milestone-gate artifact; observed tier medium |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | Each milestone 1–2 paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational engineering scenario | `steps/milestone_1/instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose | milestone instructions |
| 4 | CHECK | No step-by-step HOW | WHAT + policy/schema refs | milestone instructions |
| 5 | CHECK | No hints/strategies | Policy doc is normative spec, not solve hints | milestone instructions |
| 6 | CHECK | No design-doc tables | None | milestone instructions |
| 7 | CHECK | Well specified | Paths, commands, schemas explicit | milestone instructions |
| 8 | CHECK | Interesting | Realistic crypto/registry audit | task content |
| 9 | UNCHECK | Unique | Corpus dedup not verifiable | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | milestone instructions |
| 11 | CHECK | Task name not in instruction | Clean | milestone instructions |
| 12 | CHECK | No canary string | None | milestone instructions |
| 13 | CHECK | No runtime web fetch in env | Local registry from shipped pages | `environment/app/bin/trust_registry.py` |
| 14 | CHECK | Pip pinned with == | Hashed lock file | `environment/requirements.lock:21-41` |
| 15 | CHECK | FROM digest-pinned | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY app/ only | `environment/Dockerfile:31` |
| 17 | CHECK | No ground truth in env | README describes components only | `environment/app/README.md` |
| 18 | CHECK | No privileged Docker | Standard image | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No compose | — |
| 20 | CHECK | Verifier deps in image | pytest in lock; baked at build | `requirements.lock:41`; `test.sh:12` |
| 21 | CHECK | Oracle passes | Platform 100% (3/3) | `entire-report.txt:24` |
| 22 | CHECK | Oracle no network | Copies oracle AWK | `solve1.sh:4-5` |
| 23 | CHECK | Oracle derives answer | Full AWK implementation | `solution/oracle/media_sig_audit.awk` |
| 24 | CHECK | reward.txt canonical block | 0/1 on pass/fail | `steps/milestone_1/tests/test.sh:3-18` |
| 25 | CHECK | Same verifier for oracle/agent | No branching | milestone tests |
| 26 | CHECK | Binary reward | 0 or 1 | `test.sh` |
| 27 | CHECK | Tests aligned with instructions | Policy + schemas normative | `signing_policy.md`; LLMaJ PASS |
| 28 | CHECK | Tests check correctness | Authority equality + discriminators | `test_m1.py:53-69` |
| 29 | CHECK | Behavior not implementation grep | Output comparison only | milestone tests |
| 30 | CHECK | No brittle string matching | Authority equality appropriate | `test_m1.py:55` |
| 31 | CHECK | Informative test names or docstrings | All documented | `test_m1.py:1` |
| 32 | CHECK | ≥3 negative rubric criteria | 13 negatives | `entire-report.txt:464-500` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | Compliant | `entire-report.txt:455-500` |
| 34 | CHECK | Agent …, ±N format | 41 lines | `entire-report.txt:455-500` |
| 35 | CHECK | Rubric detailed; positive cap | Per-block 23/28/33 ≤40 | `entire-report.txt:455-500` |
| 36 | CHECK | Positive language in rubric | Negatives on bad behavior | `entire-report.txt:464-500` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:455-500` |
| 38 | CHECK | Rubric no instruction.md refs | Clean | `entire-report.txt:455-500` |
| 39 | CHECK | Rubric no oracle/NOP mentions | Clean | `entire-report.txt:455-500` |
| 40 | CHECK | Required files present | Milestone layout complete | task tree |
| 41 | CHECK | Clean parent directory | No stray author files | task tree |
| 42 | CHECK | author_name/email present | Set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | Complete | `task.toml` |
| 44 | CHECK | Tags/languages/category match | security; awk/bash/sql | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `hard` present — **observed tier medium** (informational mismatch) | `task.toml:6`; `entire-report.txt:18-20` |
| 46 | CHECK | Milestone steps layout | `steps/milestone_{1,2,3}/` | task tree |
| 47 | CHECK | solveN.sh per milestone | solve1/2/3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/2/3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone test scope | Each file tests its stage only | `test_m1.py`, `test_m2.py`, `test_m3.py` |
| 50 | CHECK | Tests not in image | .dockerignore excludes tests/steps | `.dockerignore:12-14` |
| 51 | CHECK | Solution not accessible | .dockerignore excludes solution | `.dockerignore:12` |
| 52 | CHECK | Anti-cheat solid | Authority + mutation + tamper tests | `test_m1.py:71-94`; `test_m2.py:79+` |
| 53 | CHECK | No unpinned git clone | None | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst) | Worst ~60% (Opus 3/5 per trajectory) or 20% (export GPT) — both ≤80% | `entire-report.txt:18-20`; peer adjudication |
| 55 | UNCHECK | Not too hard/unfair | Fair spec, but **under-calibrated as hard** — frontier models implement end-to-end | `entire-report.txt:18-47`; `signing_policy.md` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: catalog output + reconciliation | `test_catalog_runs`, `test_reconciliation_discriminators`, `test_matches_authority` | covered | `test_m1.py:42-69` |
| M1: live registry | `test_reads_live_registry` | covered | `test_m1.py:71-94` |
| M2: signature evidence + OpenSSL paths | `test_verify_runs`, `test_method_fingerprint_and_content`, `test_tamper_flips_validity` | covered | `test_m2.py:40-80` |
| M3: remediation taxonomy | `test_discriminating_cases`, `test_registry_drives_report` | covered | `test_m3.py:53-94` |
| All: schema conformance | `test_matches_schema` per milestone | covered | milestone test files |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `entire-report.txt` | Agent stats, failure analysis, rubric, difficulty adjudication |
| `task.toml` | Declared difficulty, milestone metadata |
| `signing_policy.md` | Normative spec completeness → medium-tier reasoning |
| `environment/Dockerfile` | #14, #15, #20 |
| `steps/milestone_*/tests/test_m*.py` | Spec alignment, anti-cheat |
| `steps/milestone_*/instruction.md` | Instruction quality |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate awk-exhibit-signature-policy-audit/
Summary: 0 error(s), 2 warning(s) — tags (7), pip pin heuristic (false positive)
```

### Agent performance

| Model | Export headline | Trajectory / failure-analysis read |
|-------|-----------------|----------------------------------|
| terminus-claude-opus-4-8 | **100% (5/5)** | Strongest model solves all milestones |
| terminus-gpt5-5 | **20% (1/5)** | Peer credits **5/5** on trajectory; export failure analysis shows 12/17 tests passed with 0 reward on near-miss trial |
| oracle | 100% (3/3) | Reference |

| Metric | Export | Adjudicated |
|--------|--------|-------------|
| Worst-model rate | 20% (GPT) | **~60%** if Opus 3/5 per peer; **100%** if both models 5/5 |
| Observed tier | hard (via GPT 20%) | **medium** |
| Declared / platform | hard / HARD | **Overstated** |
| #54 (>80%) | Pass (20% ≤ 80%) | Pass unless both models truly 5/5 |

Per-test: M2 **10/10** on all tests; M1 authority **7/10**; M3 authority **6/10** (`entire-report.txt:30-47`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope | ☑ | awk-exhibit-signature-policy-audit |
| 1 Instruction | ☑ | Clean; policy doc is complete spec |
| 2 Environment | ☑ | Pinned, offline, anti-cheat solid |
| 3 Oracle | ☑ | Platform 100% |
| 4 Verifiers | ☑ | Authority-based; mutation tests |
| 5 Metadata | ☑ | Difficulty field **overstated** |
| 6 Rubric | ☑ | Per-block caps pass |
| 7 Agent evidence | ☑ | **Revised** — hard not supported |
| 8 Fairness | ☑ | Fair but not hard |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the spec is clear, the anti-cheat design is excellent (authority recomputation, tamper/mutation tests, golden exclusion), and the environment and rubrics look great. The one thing I’d push back on is difficulty: Opus passes 5/5 in the platform stats, M2 is essentially solved at 10/10, and the policy doc gives agents a complete implementation blueprint. GPT’s 20% headline looks like milestone all-or-nothing grading and execution slips (timeouts, token limits) more than agents lacking the reasoning to finish. I’d call this **medium**, not hard — please either re-tier to medium or add real difficulty (less hand-holding in the policy doc, trickier integration) before we accept as a hard benchmark.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | **yes** | 1 |
| Metadata Issues | no | — (difficulty mismatch alone not tagged per rules; rolled into Task Difficulty) |
| All others | no | — |

---

_Report updated after peer difficulty challenge. Prior Accept on artifact quality stands; disposition changed to **Revise** on difficulty calibration only._
