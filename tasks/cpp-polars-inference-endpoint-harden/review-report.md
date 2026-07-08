# Terminus Review Report: `cpp-polars-inference-endpoint-harden`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong multi-language hard task with live HTTP verifiers, lockfile fail-closed checks, and a valid flat rubric (27/40 pts). The sole High blocker is digest-contract ambiguity: `policy_seq` dossier text says “sorted keys” but lists keys in non-lexicographic order, and `feature_digest` never specifies fixed six-decimal float serialization that the verifier enforces. Agent runs show systematic 9/10 near-misses on exactly these two tests.

**Insights (concise):**

- Dossier Section 10 key listing order produces digest `5a7c476adfe3d481`; verifier lex sort produces `cdb57de3f1c16e31` — matches all three `test_policy_seq_matches_dossier` agent failures in the export.
- Verifier `feature_digest` uses `{:.6f}` fixed-width floats (`tests/test_outputs.py:75`); dossier Section 7 only says “canonical feature JSON with sorted keys” with no float-width rule — matches the one `test_scores_match_reference` failure.
- Platform rubric uses `# Rubric 1` on a non-milestone task; `rubrics.md` allows optional `# Rubric 1` — not a blocker. Positive total is 27 (≤40).
- Worst-model pass rate 20% (GPT-5.5) fits hard tier; Claude 100% is informational only.
- Missing unknown-channel HTTP test is low risk — `batch_gate.cpp` uses the same `unknown_category` gate for region and channel (`environment/src/batch_gate.cpp:42-56`).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Canonical digest byte strings are tested but not fully specified in the public contract chain (`instruction.md` → `audit_contract.md` → dossier). `policy_seq`: dossier says “sorted keys” then lists keys in dossier-table order (`unknown_category` before `polars_pin`), which is not lexicographic; verifier hashes lex-sorted JSON (`json.dumps(..., sort_keys=True)`). `feature_digest`: dossier omits fixed six-decimal float formatting; verifier requires `{:.6f}` per key. | `environment/data/generate_dossier.py:71,93`; `environment/docs/audit_contract.md:25,31-39`; `tests/test_outputs.py:34-36,73-77`; agent export lines 76-82, 96-99 | In dossier Section 10 and/or `audit_contract.md`, state explicitly: (1) policy JSON keys sorted lexicographically (ASCII), compact JSON, no spaces — e.g. equivalent to Python `json.dumps(obj, sort_keys=True, separators=(",", ":"))`; (2) feature JSON float values serialized as fixed six-decimal strings (e.g. `0.420000`, `1.000000`). Remove or relabel the misleading key-order example in Section 10. |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Canonical `policy_seq` under-specified; dossier lists keys in non-lex order while verifier uses lex sort (ChatGPT / entire-report instruction sufficiency) | **Agree** | `generate_dossier.py:93` lists `max_batch_rows, null_fill, unknown_category, polars_pin, score_precision`; `test_outputs.py:35` uses `sort_keys=True` → digest `cdb57de3f1c16e31`; listed order → `5a7c476adfe3d481` (matches export line 77) |
| 2 | `feature_digest` requires fixed six-decimal floats not stated in spec (ChatGPT / entire-report) | **Agree** | `test_outputs.py:75` `{round(features[k], 6):.6f}`; `generate_dossier.py:71` only “canonical feature JSON with sorted keys”; compact `0.42` vs `0.420000` yields different hashes |
| 3 | Task otherwise strong: live HTTP, lockfile, sidecar, rejection semantics, idempotency (ChatGPT) | **Agree** | `tests/test_outputs.py:119-233`; `test.sh:9-20`; `Dockerfile:11-12` |
| 4 | Optional: add unknown-channel rejection test (ChatGPT / test-quality review) | **Agree** (Low only) | `test_unknown_region_rejected` at `test_outputs.py:184-202`; no channel variant; same gate at `batch_gate.cpp:50-56` |
| 5 | Optional: add `python` to `languages` metadata (ChatGPT / Harbor review) | **Partially agree** (Low) | `task.toml:11` `["cpp","toml"]`; sidecar is Python — metadata imprecision, not a revision blocker |
| 6 | Non-canonical GCC base image is a blocker (Harbor review warning) | **Disagree** | `Dockerfile:1` digest-pinned `gcc:13-bookworm`; C++ build requires g++; no canonical C++ base in list — justified deviation |
| 7 | Non-milestone task uses `# Rubric 1` milestone header format (user question) | **Disagree** (not a blocker) | `task.toml:9` `number_of_milestones = 0`; `rubrics.md:66` “`# Rubric 1` optional; no `# Rubric 2+`”; export has only `# Rubric 1`, no `# Rubric 2` |
| 8 | Rubric positive total >40 (automated concern) | **Disagree** | Export lines 340-353: +2+5+3+2+3+3+3+3+1+2 = **27** ≤ 40 |
| 9 | LLMaJ `behavior_in_task_description` PASS vs instruction-sufficiency FAIL | **Partially agree** | LLMaJ correct on behavioral reqs; sufficiency analysis correct on digest micro-format gaps not in instruction chain |
| 10 | `test.sh` uvx offline brittleness (Harbor review) | **Disagree** (not a blocker) | `Dockerfile:23-24` pre-caches uvx tools; `test.sh:9-14` offline invocation is standard Terminus pattern |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 short paragraphs, ~233 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as incident brief, not spec boilerplate | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcomes and artifact paths, not edit script | `instruction.md` |
| 5 | CHECK | No hints/solve strategies | No walkthrough of which files to patch | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | No input→output mapping tables | `instruction.md` |
| 7 | UNCHECK | Well specified | Digest serialization rules incomplete vs verifier | Blocker 1; `generate_dossier.py:71,93` |
| 8 | CHECK | Interesting | Realistic ML-serving hardening scenario | `instruction.md` |
| 9 | CHECK | Unique | No duplicate found in local corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary in instruction | No canary string | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Data generated at build; no runtime curl | `Dockerfile:37`; env sources |
| 14 | CHECK | Pinned pip/apt versions | `pytest==8.4.1`, apt `=version` pins | `Dockerfile:5-14,24` |
| 15 | CHECK | FROM digest-pinned | `@sha256:930f2ebe...` | `Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | `COPY . /app/environment/` | `Dockerfile:35` |
| 17 | CHECK | No ground-truth answers in env | Broken stubs intentional; operative values require dossier parse | `environment/src/*.cpp` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `Dockerfile` |
| 19 | CHECK | Compose doesn't alter mounts | No docker-compose | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | uvx/pytest baked; test.sh only runs pytest | `Dockerfile:23-24`; `test.sh:9-14` |
| 21 | UNCHECK | Oracle passes consistently | Harbor oracle not run in this review environment | `./scripts/terminus oracle` exited without result |
| 22 | CHECK | Oracle no internet | solve.sh only writes local C++ sources and make | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Patches ratified_policy, lock_guard, sidecar_exec, batch_gate; runs make + audit | `solution/solve.sh` |
| 24 | CHECK | reward.txt on pass/fail | Writes 0 or 1 | `test.sh:16-20` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `test.sh`; `test_outputs.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `test.sh:16-20` |
| 27 | UNCHECK | Tests aligned with instructions | Digest byte rules tested but under-specified | Blocker 1 |
| 28 | CHECK | Tests check correctness | Live HTTP + independent reference math | `test_outputs.py:106-153` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `test_outputs.py` |
| 30 | CHECK | No brittle format-only checks | Assertions on scores, digests, rejection tallies | `test_outputs.py` |
| 31 | CHECK | Informative test docstrings | Every `test_*` has docstring | `test_outputs.py:127-233` |
| 32 | CHECK | ≥3 negative rubric criteria | Three negatives (-5, -5, -3) | `entire-report.txt:351-353` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | No ±4 | `entire-report.txt:340-353` |
| 34 | CHECK | Agent …, ±N format | 13 criteria, correct format | `entire-report.txt:340-353` |
| 35 | CHECK | Rubric detailed; ≤40 positives | 27 positive pts | `entire-report.txt:340-349` |
| 36 | CHECK | Positive phrasing | Bad behaviors use negative scores, positive wording | `entire-report.txt:351-353` |
| 37 | CHECK | Rubric no /tests/ refs | No test path references | `entire-report.txt:340-353` |
| 38 | CHECK | Rubric no instruction.md refs | References dossier/audit paths only | `entire-report.txt:341` |
| 39 | CHECK | Rubric no oracle/NOP | No oracle mentions | `entire-report.txt:340-353` |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README; `audit-report.md` is reviewer-generated only | task root listing |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, category, tags present | `task.toml` |
| 44 | CHECK | Tags/languages applicable | cpp/toml primary; python sidecar covered by tags | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard`; worst-model 20% → hard tier | `task.toml:6`; `entire-report.txt:38-44` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile:35` |
| 51 | CHECK | Solution not in environment | tests/solution siblings, not copied | `Dockerfile:35` |
| 52 | CHECK | Agent can't trivially pass | Requires rebuild + live serving + dossier policy | `test_outputs.py:119-123` |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:43-44` |
| 55 | UNCHECK | Not too hard/unfair | Unstated digest serialization causes systematic 9/10 failures | `entire-report.txt:66-99`; Blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/batch_audit.json` via audit script | `test_audit_regenerates` | covered | `instruction.md:3`; `test_outputs.py:127-132` |
| `policy_seq` from ratified policy | `test_policy_seq_matches_dossier` | **gap** | Dossier key-order ambiguity; `generate_dossier.py:93` vs `test_outputs.py:35` |
| `lock_digest` from `polars==<pin>` | `test_lock_digest_matches_pin` | covered | `generate_dossier.py:95`; `test_outputs.py:39-41,139-142` |
| Ridge scores + `feature_digest` | `test_scores_match_reference` | **gap** | Six-decimal format unstated; `generate_dossier.py:71` vs `test_outputs.py:75` |
| Scores sorted by `row_id` | `test_scores_sorted_by_row_id` | covered | `generate_dossier.py:89`; `test_outputs.py:155-159` |
| Idempotent back-to-back audits | `test_idempotent_rerun` | covered | `instruction.md:5`; `test_outputs.py:161-165` |
| Oversize batch rejection | `test_oversize_batch_rejected` | covered | `generate_dossier.py:83`; `test_outputs.py:167-182` |
| Unknown categorical rejection | `test_unknown_region_rejected` | covered (region only) | `generate_dossier.py:83`; `test_outputs.py:184-202` |
| Missing required keys rejection | `test_missing_column_rejected` | covered | `generate_dossier.py:83`; `test_outputs.py:204-215` |
| Lock probe fail-closed | `test_tampered_lock_fail_closed` | covered | `generate_dossier.py:99-101`; `test_outputs.py:217-233` |
| Lockfile before sidecar | implied by tamper test + dossier | covered | `generate_dossier.py:99-101` |
| Forward null-fill sidecar mode | via score correctness test | covered | `generate_dossier.py:69,111`; `test_scores_match_reference` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-6, #10-12, #27, Blocker 1 |
| `task.toml` | #45, #46-49 N/A, metadata |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/data/generate_dossier.py` | Blocker 1, spec alignment |
| `environment/docs/audit_contract.md` | Blocker 1, schema |
| `environment/src/batch_gate.cpp` | unknown channel/regional gate |
| `environment/src/ratified_policy.cpp` | broken policy_seq order (starter) |
| `environment/src/row_scorer.cpp` | feature_digest uses setprecision(6) in starter |
| `tests/test_outputs.py` | #27-31, Blocker 1, all alignment rows |
| `tests/test.sh` | #20, #24-26 |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #45, #54, agent stats, rubric, external claims |
| `docs/guidelines/rubrics.md` | rubric format (# Rubric 1 optional) |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: cpp-polars-inference-endpoint-harden/ ===
Summary: 0 error(s), 1 warning(s), 1 info
Task type detected: regular
WARNING: check_dockerignore — Non-trivial environment/ should include .dockerignore
INFO: submission-diversity — Milestone tasks preferred (non-milestone not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Per export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

**Per-test pass rates (export):** `test_policy_seq_matches_dossier` 7/10; `test_scores_match_reference` 9/10; all others 10/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task name matches folder; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Strong tone; digest spec gap flagged |
| 2 Environment | ☑ | Digest-pinned GCC base justified; tmux+asciinema present |
| 3 Oracle | ☐ | Not executed locally (Harbor unavailable) |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, live HTTP tests |
| 5 Metadata | ☑ | Fields complete; optional python tag note only |
| 6 Rubric | ☑ | 27/40 pts; 3 negatives; `# Rubric 1` OK for non-milestone |
| 7 Agent evidence | ☑ | 9/10 systematic digest failures support spec gap |
| 8 Novelty & fairness | ☑ | Multi-step; digest ambiguity unfair |
| 9 Long context | — | Not tagged `long_context`; dossier still shipped |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the live HTTP verifier, lockfile tamper check, dossier-driven policy repair, and sidecar null-fill path are all well thought out, and the rubric looks good at 27 points with sensible negatives. One thing to fix before accept: the exact byte strings for `policy_seq` and `feature_digest` need to be spelled out in the dossier and/or `audit_contract.md`. Right now Section 10 says “sorted keys” but lists them in table order (which gives the wrong hash), and nothing states that feature floats must be fixed six-decimal strings like `0.420000`. Agents are consistently passing 9/10 tests and failing only on those serialization details — please document lexicographic JSON key order (compact, no spaces) for policy and `{:.6f}` formatting for feature values.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
