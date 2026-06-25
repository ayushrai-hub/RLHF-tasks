# Terminus Review Report: `fraudulent-vendor-detection`

**Generated:** 2026-06-21 (manual re-audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/fraudulent-vendor-detection`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per report; not re-run locally) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Task Difficulty, Metadata Issues

**Decision (concise):** Strong Go debugging task with canonical digest-pinned base, offline verifier stack, 66 behavior tests that recompile from source, and solid spec↔test alignment. One High blocker remains: `task.toml` declares `difficulty = "hard"` but worst-model pass rate is Claude Opus 4.8 at 60% (medium tier). Update metadata to `medium` or rebalance until ≤20% on best or worst model. ChatGPT’s sanctioned-base claim and automated #14/#31/#54 blockers are false positives on re-audit.

**Insights (concise):**

- `golang:1.24-bookworm@sha256:1a6d4452…` exactly matches `scripts/validate_task.py` CANONICAL_BASE_IMAGES and `docs/guidelines/dockerfxile.md:11` — no exemption required.
- Pip deps are pinned in `environment/verifier-requirements.txt` (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); validate warning is a multiline `pip install -r` false positive.
- All 66 `test_*` functions have docstrings; only the module-level docstring is missing (validate warning, not #31 fail).
- Worst-model rate is 60% (Claude 3/5), not >80%; #54 passes. GPT-5.5 at 100% does not set the tier floor.
- `environment/docs/operations.md:70-71` incorrectly states `golang:1.22-bookworm` and claims a non-canonical base — stale doc (Low); fix alongside metadata.
- Oracle copies four corrected Go files and rebuilds; report shows 100% (3/3).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared `hard` but observed worst-model tier is **medium** (60%) | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:4-9` Claude 60% (3/5), GPT-5.5 100% (5/5); `docs/guidelines/difficulty.md:9-11` medium = 20–60% on worst model | Set `difficulty = "medium"` or rebalance task until ≤20% on best or worst model |

*No other High-severity blockers on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Declared hard vs observed medium; GPT 100%, Claude 60% (ChatGPT / entire-report L4-9) | **Agree** | `task.toml:6`; `entire-report.txt:7-9`; worst-model 60% → medium per `docs/reviewer-checklist-ui.md:52-57` |
| 2 | Non-sanctioned Go runtime base without exemption (ChatGPT High) | **Disagree** | `environment/Dockerfile:1` uses `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` — exact match in `scripts/validate_task.py:67` and `docs/guidelines/dockerfxile.md:11` |
| 3 | `operations.md` references golang:1.22-bookworm while Dockerfile uses 1.24 (ChatGPT Low / entire-report L156) | **Agree (Low)** | `environment/docs/operations.md:70` says `golang:1.22-bookworm`; `environment/Dockerfile:1` uses `golang:1.24-bookworm`; `environment/go.mod:3` `go 1.22` (compatible minimum, not a runtime mismatch) |
| 4 | `operations.md` claims image is not a Terminal-Bench pinned base (artifact review) | **Agree (Low)** | `environment/docs/operations.md:70-71`: "custom Go base … not a Terminal-Bench pinned image" contradicts canonical list — misleading but not blocking |
| 5 | Tests/solution excluded; verifier deps baked; pinning robust (ChatGPT summary) | **Agree** | `environment/Dockerfile:21-26,28-32`; no COPY of tests/solution; `entire-report.txt:151-159` behavior_in_tests PASS |
| 6 | Solution includes unchanged `batch/spin_k.go` and `blob/grow_k.go` (entire-report L210-228) | **Agree (Low)** | `solution/solve.sh:24-28` copies only four differing files; unchanged files not in oracle tree — cosmetic only |
| 7 | Automated #14 unpinned pip | **Disagree** | `environment/Dockerfile:25-26` installs from `verifier-requirements.txt` with `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` |
| 8 | Automated #31 missing test docstrings | **Disagree** | AST audit: 66/66 `test_*` functions have docstrings; validate flags module-level docstring only |
| 9 | Automated #54 too easy (>80% worst model) | **Disagree** | Worst model is Claude 60%, not GPT 100%; `entire-report.txt:7-8` |
| 10 | Test quality ROBUST / ACCEPT (entire-report L296-334) | **Agree** | 66 tests; fresh binary rebuild in `_build_fresh_binary()`; parity matrix across nine profiles |
| 11 | Instruction sufficiency PASS; failures are agent execution not spec gaps (entire-report L87-125) | **Agree** | `entire-report.txt:123-124`; instruction references `report_schema.md` and `fixture_layout.md` for full contract |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 383 words; `## Requirements` section exceeds prompt-styling length target | `instruction.md` (383 words) |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Finance/AP engineer handoff tone | `instruction.md:1-7` |
| 3 | CHECK | No excessive markdown formatting | One `## Requirements` header and one code block; no tables in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | States goal, paths, and contract refs; no fix walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Names parity outcome and dossier paths; dossier is normative spec for debug task | `instruction.md:16-24` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Output path, rebuild command, view-mode parity, key naming rules stated | `instruction.md:5-24` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic AP fraud / attribution debugging scenario | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Vendor-graph deferred-settlement Go debug pattern; no duplicate in repo | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Title uses plain English, not folder slug | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | `go mod download` at build; no runtime fetch in env code | `environment/Dockerfile:30-31` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | Pins in `verifier-requirements.txt` consumed by Dockerfile | `environment/verifier-requirements.txt:1-2`, `environment/Dockerfile:25-26` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Full digest on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | `COPY . /app/environment` only | `environment/Dockerfile:21` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Buggy source is intentional setup; schema docs are contracts not oracle output | `environment/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock) | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:25-26`, `tests/test.sh:13` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report: oracle 100% (3/3); local oracle blocked by Docker daemon | `entire-report.txt:12-13` |
| 22 | CHECK | Oracle does not require internet or downloading packages | File copy + `go build` only | `solution/solve.sh:24-37` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Installs four corrected Go sources, rebuilds vendorlab | `solution/solve.sh:24-37` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Defaults 0, writes 1/0 after pytest | `tests/test.sh:4-19` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary reward block | `tests/test.sh:15-19` |
| 27 | CHECK | All tests are aligned with instructions (do not test unstated requirements) | Every assertion traces to instruction + linked dossier pages | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Exact trajectories, digests, parity, cap enforcement | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | No `.go` source reads in tests | `tests/test_outputs.py` (no `.go` grep) |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact JSON/digest pins intentional for deterministic audit task | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | 66/66 test functions documented | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A | — |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | N/A | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A | — |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Standard task layout only | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | go/bash data-processing analytics task | `task.toml:7-9` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared hard; worst-model 60% → medium | `task.toml:6`, `entire-report.txt:7-8` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:12` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile:21` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/ not copied; expected values recomputed in tests | `environment/Dockerfile:21` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Tests recompile binary from source; parity checks cross modes | `tests/test_outputs.py:72-115,734-736` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 60% (<80% threshold) | `entire-report.txt:7-8` |
| 55 | CHECK | Task is not too hard or unfair | 60% Claude pass; instruction sufficiency PASS; failures are implementation not missing spec | `entire-report.txt:87-125` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/vendor_audit.json` via runner rebuild | `test_entrypoint_prefix_ledger_emit`, `_run()` | covered | `instruction.md:5-7`; `tests/test_outputs.py:97-115,456-458` |
| line_item / vendor_graph parity, zero phantom tallies | `test_primary_schedule_parity`, `test_matrix_all_bundled_configs_parity` | covered | `instruction.md:18`; `tests/test_outputs.py:515-517,734-736` |
| Invoice rows use `period`/`stage`; ticks use `period_index` | `test_audit_shape_and_fields` | covered | `instruction.md:9`; `tests/test_outputs.py:39,468-470` |
| Warm checkpoint continuation matches cold run | `test_warm_continuation_matches_cold_burst`, `test_warm_prefix_stage_digests_match_cold_burst_prefix` | covered | `instruction.md:24`; `tests/test_outputs.py:530-532` |
| period_failover restore/replay counters | `test_failover_restore_replay_counters_exercised` | covered | `report_schema.md:36`; `tests/test_outputs.py:606-608` |
| Failover audit matches continuous vendor_graph | `test_period_failover_matches_continuous_vendor_graph` | covered | `instruction.md:24`; `tests/test_outputs.py:596-598` |
| North burst rejection sets / triple rejections | `test_burst_exact_rejection_tally`, `test_acme_tick0_accept_pair_reject_third` | covered | `fixture_layout.md`; `tests/test_outputs.py` |
| stage_width filtering (delay_ticks) | `test_delay_width_filter_geometry` | covered | `instruction.md:20`; `tests/test_outputs.py:707-709` |
| bind_slot monotonicity | `test_bind_slot_apply_order_monotonic` | covered | `report_schema.md:80`; `tests/test_outputs.py:694-696` |
| vendor_fingerprint SHA-256 recompute | `test_vendor_fingerprint_recomputed` | covered | `report_schema.md:31`; `tests/test_outputs.py:653-655` |
| All nine bundled profiles in operations.md | `test_matrix_all_bundled_configs_parity` | covered | `operations.md:20-32`; `tests/test_outputs.py:19-29,734-736` |
| Hand-written JSON insufficient (recompile from source) | `_build_fresh_binary()` in every `_run()` | covered | `instruction.md:7`; `tests/test_outputs.py:72-115` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, §5 |
| `task.toml` | #42–45, blocker 1 |
| `environment/Dockerfile` | #13–20, adjudication #2 |
| `environment/verifier-requirements.txt` | #14 |
| `environment/docs/operations.md` | Adjudication #3–4 |
| `environment/docs/report_schema.md` | §5 |
| `environment/docs/fixture_layout.md` | §5 |
| `environment/go.mod` | Adjudication #3 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #25–31, §5 |
| `solution/solve.sh` | #22–23 |
| `scripts/validate_task.py` | Adjudication #2 (canonical base) |
| `docs/guidelines/dockerfxile.md` | Adjudication #2 |
| `docs/guidelines/difficulty.md` | Blocker 1, #45, #54 |
| `entire-report.txt` | §7, adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: fraudulent-vendor-detection/ ===
Summary: 0 error(s), 3 warning(s), 2 info
WARNING: pinned_dependencies — multiline pip -r false positive (packages ARE pinned)
WARNING: informative_test_docstrings — module-level docstring only
INFO: milestone preference, test.sh trailing exit
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | **Worst model** |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `fraudulent-vendor-detection`; regular layout; Go debugging |
| 1 Instruction | ☑ | Well specified; 383 words → #1 UNCHECK |
| 2 Environment | ☑ | Canonical Go base; stale operations.md Go version (Low) |
| 3 Oracle | ☑ | Static review + report 100%; local Docker blocked |
| 4 Verifiers | ☑ | 66 tests; fresh rebuild anti-cheat; canonical reward block |
| 5 Metadata | ☑ | difficulty mismatch → blocker |
| 6 Rubric | N/A | No rubric file in repo (criteria in report are portal-only) |
| 7 LLMaJ & agent evidence | ☑ | Report matches task; all claims adjudicated |
| 8 Novelty & fairness | ☑ | Multi-file Go debug; 60% worst-model; instruction sufficient |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Verifiers, canonical digest-pinned Go base, offline pytest stack, and spec↔test alignment are strong. The remaining blocker is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium tier (Claude Opus 4.8 60% worst-model; GPT-5.5 100%). Update `difficulty` to `medium` or rebalance until the task qualifies as hard. Optional cleanup: fix `environment/docs/operations.md` to reference `golang:1.24-bookworm` and remove the incorrect “not a Terminal-Bench pinned image” note.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Environment | no (Low doc drift only) | — |
| Instruction Styling | no (#1 UNCHECK is Medium, not blocking alone) | — |
| Pinning Issues | no | — |
| Test Alignment/Coverage Issues | no | — |
| Oracle Solution Issues | no | — |

---

_Generated by `./scripts/terminus review` baseline + manual re-audit per `prompt.md`._
