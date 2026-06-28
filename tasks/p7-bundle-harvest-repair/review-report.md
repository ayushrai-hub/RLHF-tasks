# Terminus Review Report: `p7-bundle-harvest-repair`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (platform: pass) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** none

**Decision (concise):** Strong Ruby/API dual-sink harvest repair task with digest-pinned canonical Ruby base, live verifier reconciliation, ablation anti-cheat, and thorough contract docs. ChatGPT’s two alleged High spec gaps (route `{n}` collapse and SQLite `rec_key` dedup) are **not** blockers — both are normatively specified via `bundle_contract.md` → `b3_stat.rb` header and `runner.rb` PRIMARY KEY + union semantics. Automated script blockers (#14, #31, #54) and the external report’s non-canonical-base claim are false positives on manual audit. Non-milestone platform rubric using optional `# Rubric 1` header is correct per `rubrics.md`.

**Insights (concise):**

- Route collapse rule: `b3_stat.rb:6-7` (`{n}` for all-digit segments); `bundle_contract.md:36,40` normatively points agents there; `test_p9_grid` docstring cites “stat header.”
- Store dedup: `runner.rb:25` `rec_key TEXT PRIMARY KEY`; `bundle_contract.md:32` union-equals-store; `test_o4_store_union` / `test_c4_store_keys` enforce one row per union key.
- `ruby:3.3-slim-bookworm@sha256:e76733e9…` **is** in `CANONICAL_BASE_IMAGES` (`scripts/validate_task.py:71`) — external “non-canonical base” claim is wrong.
- Agent rates: Opus 100% (5/5), GPT-5.5 60% (3/5); worst-model 60% = medium tier, not >80% rejected (#54 passes).
- Declared `difficulty = "hard"` vs observed medium worst-model is informational (#45) — not a revision blocker per review policy.
- Low nits only: `tests/test.sh` omits `mkdir -p /logs/verifier`; stray `Untitled` portal paste in task root; missing module-level pytest docstring.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Route-template `{n}` collapse not explicit in normative docs; agents must infer from tests (ChatGPT High) | **Disagree** | `environment/docs/bundle_contract.md:36,40` defines `route_tmpl` and delegates rollup/collapse rules to `b3_stat.rb` module comment; `environment/rb/p7_pull/lib/b3_stat.rb:6-7` states “replace every all-digit segment with `{n}`”; `tests/test_outputs.py:619-620` docstring: “collapse rule from the stat header” |
| 2 | SQLite `k6_facts` dedup semantics unstated; tests expect one row per unique `rec_key` across profiles (ChatGPT High) | **Disagree** | `environment/rb/p7_pull/lib/runner.rb:25` `rec_key TEXT PRIMARY KEY`; `bundle_contract.md:32` “union of `rec_key` values across all profile CSV files must equal the `k6_facts` key set”; `tests/test_outputs.py:312-323` `test_c4_store_keys`; `367-378` `test_o4_store_union` docstring: “deduplicated union” |
| 3 | LLMaJ `behavior_in_task_description` PASS (entire-report) | **Agree** | `instruction.md:5` + `bundle_contract.md` cover pagination, windows, sinks, rollup; collapse via `b3_stat.rb` reference |
| 4 | LLMaJ Task Instruction Sufficiency FAIL on `{n}` and dedup (entire-report:92-99) | **Disagree** | Same evidence as claims #1–2; trial `GrmDMYG` used `:id` placeholders — agent misread existing spec, not missing spec |
| 5 | Non-canonical Docker base image is primary blocker (entire-report:159-184, 274-278) | **Disagree** | `environment/Dockerfile:3` digest matches `CANONICAL_BASE_IMAGES["public.ecr.aws/docker/library/ruby:3.3-slim-bookworm"]` in `scripts/validate_task.py:71`; `validate` emits no sanctioned-base warning |
| 6 | Snapshot files identical to broken env code (entire-report WARNING) | **Agree (non-blocking)** | `environment/docs/snapshots/*.rb` match broken sources; used by `test_v6_ablate_*` — valid anti-cheat pattern |
| 7 | Percentile formula mismatch test vs solution (entire-report WARNING) | **Agree (non-blocking)** | `tests/test_outputs.py:226-230` vs `solution/patched/b3_stat.rb:128`; both nearest-rank p95; agree on fixtures |
| 8 | Add `mkdir -p /logs/verifier` to test.sh (ChatGPT Low) | **Agree (Low only)** | `tests/test.sh:10-16` writes reward without mkdir; canonical pattern in `docs/guidelines/writing-tests.md:11`; Harbor typically provides mount — not fairness blocker |
| 9 | Set `difficulty = "medium"` to match evaluation (ChatGPT Low) | **Partially agree (informational)** | `entire-report.txt:14,20-21` medium tier on worst model; `#45` mismatch not revision blocker per `prompt.md` |
| 10 | Automated review #14 unpinned pip | **Disagree** | `environment/Dockerfile:23-24` `pytest==8.4.1 pytest-json-ctrf==0.3.5 pytest-randomly==3.16.0` |
| 11 | Automated review #31 missing docstrings | **Disagree** | All 30 `test_*` functions have docstrings; only module-level docstring absent |
| 12 | Automated review #54 worst-model 100% too easy | **Disagree** | `entire-report.txt:19-20` GPT-5.5 60%; worst = 60% (<80%) |
| 13 | Test quality review ACCEPT (entire-report:286-323) | **Agree** | Live API reconciliation + ablation coverage is robust |
| 14 | Platform rubric uses milestone format on non-milestone task | **Disagree** | `task.toml:10` `number_of_milestones = 0`; `entire-report.txt:325-338` has only `# Rubric 1` (optional per `docs/guidelines/rubrics.md:60`); no `# Rubric 2+`; flat `Agent …, ±N` lines |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | Two problem paragraphs + one requirements paragraph | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Operator problem statement, not numbered spec | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Points to contract docs and rebuild rule | `instruction.md:3,5` |
| 5 | CHECK | No hints/solving strategies | WHAT + normative doc refs only | `instruction.md` |
| 6 | CHECK | No design-doc tables | None | `instruction.md` |
| 7 | CHECK | Well specified | Output paths, columns, doc contracts named | `instruction.md:3,5` |
| 8 | CHECK | Interesting | Multi-module Ruby harvest + live API reconciliation | — |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | No task name in instruction | “P7 bundle” is domain label, not folder slug `p7-bundle-harvest-repair` | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local Rails host + fixtures only | `environment/Dockerfile` |
| 14 | CHECK | Pip pinned with == | All pytest packages `==` pinned at image build | `environment/Dockerfile:23-24` |
| 15 | CHECK | FROM digest-pinned | `@sha256:e76733e9…` | `environment/Dockerfile:3` |
| 16 | CHECK | Build context in environment/ | COPY api/rb/net/corpus/docs/scripts only | `environment/Dockerfile:32-37` |
| 17 | CHECK | No ground truth in env | Patched sources in `solution/patched/`; snapshots are broken baselines | `solution/solve.sh:16-18` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no install | Venv in Dockerfile; test.sh calls pytest only | `Dockerfile:22-26`, `tests/test.sh:10` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Docker unavailable); platform oracle 100% | `entire-report.txt:24` |
| 22 | CHECK | Oracle no internet | Local service + bundle install against pre-built image | `solution/solve.sh:12-24` |
| 23 | CHECK | Oracle derives via implementation | Patches three Ruby modules, runs live driver | `solution/solve.sh:15-24` |
| 24 | UNCHECK | reward.txt + mkdir canonical block | Writes 0/1 reward but omits `mkdir -p /logs/verifier` | `tests/test.sh:10-16` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branch | `tests/test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:12-15` |
| 27 | CHECK | Tests aligned with instructions | All assertions trace to instruction + bundle_contract + b3_stat header | §5 below |
| 28 | CHECK | Tests check correctness | Live API walks vs regenerated CSV/DB/rollup | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Driver subprocess + artifact reconciliation | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string matching | Set/key equality, numeric tolerance on `err_share` | `tests/test_outputs.py:233-237` |
| 31 | CHECK | Informative test names/docstrings | 30/30 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubric ≥3 negatives | Four negatives in platform rubric | `entire-report.txt:336-338` |
| 33 | CHECK | Rubric scores ∈ {1,2,3,5} | All lines use ±1,2,3,5 | `entire-report.txt:327-338` |
| 34 | CHECK | Rubric Agent format | Each line `Agent …, ±N` | `entire-report.txt:327-338` |
| 35 | CHECK | Rubric detailed | Task-specific harvest/pagination/dedup checks | `entire-report.txt:327-338` |
| 36 | CHECK | Rubric positive language | Penalties name bad actions with negative scores | `entire-report.txt:336-338` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:327-338` |
| 38 | CHECK | Rubric no instruction.md refs | None | `entire-report.txt:327-338` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:327-338` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | UNCHECK | No stray parent files | `Untitled` portal paste duplicate in task root | `p7-bundle-harvest-repair/Untitled` |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, allow_internet=false, languages | `task.toml` |
| 44 | CHECK | Tags/category applicable | ruby/rails/sqlite/etl + api_integration/db_interaction fit | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches rates | Declared `hard`; worst-model 60% = medium tier | `task.toml:6`, `entire-report.txt:19-20` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:10` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:7` |
| 51 | CHECK | Solution not in env | `solution/` excluded from image | `environment/.dockerignore:6` |
| 52 | CHECK | Agent cannot trivially cheat | Verifier reruns driver against live API each test | `tests/test_outputs.py` `_run_driver` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst model 60% | `entire-report.txt:19-20` |
| 55 | CHECK | Not unfair | Alleged spec gaps refuted; failures are agent execution/spec-reading errors | claims #1–2 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 24, 41, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Header-driven pagination (not body token) | `test_h4_body_hdr_divergence`, `test_q8_cursor_header_chain` | covered | `bundle_contract.md:16-18`; `tests/test_outputs.py:414+` |
| Half-open `until` window | `test_r7_s03_half_open`, `test_h8_edge` | covered | `bundle_contract.md:20-22`; `tests/test_outputs.py:451+` |
| Per-profile CSV unique `rec_key` | `test_k9_retry_keys_unique`, `test_z1_dup` | covered | `bundle_contract.md:32`; `tests/test_outputs.py:521+` |
| Store union = deduplicated keys across profiles | `test_c4_store_keys`, `test_o4_store_union` | covered | `bundle_contract.md:32`; `runner.rb:25`; `tests/test_outputs.py:312+` |
| `route_tmpl` collapse `{n}` for digit segments | `test_p9_grid`, `test_m8_full_reconciliation` | covered | `b3_stat.rb:6-7`; `bundle_contract.md:40`; `tests/test_outputs.py:619+` |
| Cross-sink `rec_at` UTC ISO8601 alignment | `test_u5_cross_sink_mirrors` | covered | `bundle_contract.md:40`; `tests/test_outputs.py:464+` |
| Priority band filtering | `test_y7_beta_subset`, `test_n2_gate` | covered | `k6_levels.txt`; `tests/test_outputs.py:579+` |
| Rollup `req_total` / `err_share` / `tail_p95_ms` | `test_a1_rollup_fields`, `test_l6_tail_local_population`, `test_i7_err_status_spectrum` | covered | `b3_stat.rb:9-12`; `bundle_contract.md:40` |
| `bundle_digest` from store groups | `test_b7_digest_from_store` | covered | `b3_stat.rb:14-20`; `tests/test_outputs.py:341+` |
| Retry dedup after 503 glitch batch | `test_g7_glitch_batch_once` | covered | `bundle_contract.md:18`; `tests/test_outputs.py:545+` |
| Idempotent consecutive runs | `test_t0_idem`, `test_e9_restart_stable` | covered | `tests/test_outputs.py:641+` |
| Ablation: each module fix required | `test_v6_ablate_a/b/c` | covered | `environment/docs/snapshots/`; `tests/test_outputs.py:657+` |
| Live driver rebuild (no static hand-write) | all tests via `_run_driver()` | covered | `instruction.md:3`; `tests/test_outputs.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-8, #10-12, #27, spec alignment |
| `task.toml` | #42-46, #45, milestone N/A |
| `environment/Dockerfile` | #13-20, #50, canonical base claim |
| `environment/docs/bundle_contract.md` | claims #1-2, spec alignment |
| `environment/rb/p7_pull/lib/b3_stat.rb` | route collapse, rollup rules |
| `environment/rb/p7_pull/lib/runner.rb` | PRIMARY KEY store schema |
| `environment/.dockerignore` | #50-51 |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, all tests |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | agent stats, rubric, LLMaJ, external claims |
| `scripts/validate_task.py` | canonical base list |
| `p7-bundle-harvest-repair/Untitled` | #41 stray file |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate p7-bundle-harvest-repair/
Summary: 0 error(s), 3 warning(s), 1 info
Task type detected: regular
```

Warnings: pip multiline false positive (#14 passes on audit); `Untitled` solution-hint pattern; module-level pytest docstring missing (all per-test docstrings present).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100.0% (5/5) | — |
| terminus-gpt5-5 | 60.0% (3/5) | 1 timeout, 1 other |
| oracle | 100.0% (3/3) | platform |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular layout; `number_of_milestones = 0`; Ruby data-processing |
| 1 Instruction | ☑ | Concise; normative doc pointers; no HOW walkthrough |
| 2 Environment | ☑ | Canonical digest-pinned Ruby base; tmux+asciinema; offline |
| 3 Oracle | ☑ | Static review pass; local oracle blocked (no Docker) |
| 4 Verifiers | ☑ | 30 behavior tests; ablation; binary reward; minor mkdir gap |
| 5 Metadata | ☑ | Complete; difficulty calibration note only |
| 6 Rubric | ☑ | Platform rubric valid; `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Instruction-sufficiency FAIL on `{n}`/dedup refuted with file proof |
| 8 Novelty & fairness | ☑ | Multi-bug Ruby repair; live API anti-cheat |
| 9 Long context | ☐ | N/A — not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the digest-pinned Ruby environment, live API verifier, CSV/SQLite/TOML reconciliation, and ablation tests are all in great shape. Oracle and agent runs look healthy for the intended difficulty band. I did not find any real spec-test blockers: the `{n}` route-template rule and shared-store dedup semantics are already spelled out in `bundle_contract.md` and the `b3_stat.rb` module header (with `rec_key` PRIMARY KEY in the runner). Optional cleanup before submit: delete the stray `Untitled` portal paste from the task folder and add `mkdir -p /logs/verifier` to `test.sh` to match the canonical pattern.

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
