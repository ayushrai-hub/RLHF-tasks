# Terminus Review Report: network-flow-aggregator

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Rust debugging task with excellent anti-cheat coverage and a compliant platform rubric. One confirmed High blocker: `instruction.md` points agents to a non-existent trace path (`/app/environment/traces/...`) while the container and verifier use `/app/traces/sample_trace.csv`. Classification exact values are partially mitigated because thresholds and format live in shipped `classify/src/lib.rs`, but instruction/contract should still document them for fairness. Remove `jobs_test3/` before resubmit. Automated script incorrectly flagged #31 and #54.

**Insights (concise):**

- Wrong trace path is factual and reproducible across `instruction.md`, `Dockerfile`, and `tests/test.sh`.
- Classification thresholds (`normal` < 1M bytes, `risk_score=20`, `Protocol:`/`Bytes:` format) are visible in `classify/src/lib.rs:30-42`; debugging-task convention reduces but does not eliminate the spec gap.
- Worst-model pass rate is **40%** (GPT-5.5), not 100% — task is medium tier, not too easy.
- Platform rubric uses optional `# Rubric 1` header only — **not** milestone multi-block format; format is compliant.
- All 55 `test_*` methods have docstrings; only module-level docstring is missing (validator warning, not a blocker).
- `jobs_test3/` run artifacts should be deleted from the submission folder.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Instruction cites wrong trace path | `instruction.md:3` says `/app/environment/traces/sample_trace.csv`; `environment/Dockerfile:50` `COPY traces/ traces/` → `/app/traces/`; `tests/test.sh:30` runs `/app/traces/sample_trace.csv` | Change instruction to `/app/traces/sample_trace.csv` |
| 2 | Medium | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Classification exact thresholds, risk scores, and details format tested but not stated in instruction or contract | `instruction.md:19-22` only requires 0–100 scores and "protocol name embedded"; `tests/test_outputs.py:227-256,289-300` assert `category=="normal"`, `risk_score==20`, `"Protocol:"`/`"Bytes:"` substrings; `environment/docs/contract.md:20` says "correct risk scores" without numbers | Document tier names/thresholds (`>1M bytes` → `high-volume`/80, `>10k packets` → `high-rate`/60, else `normal`/20), exact normal risk score, and details template `"Protocol: {proto}, Bytes: {n}, Packets: {n}"` — or explicitly instruct agents to preserve the non-bug logic in `classify/src/lib.rs` |
| 3 | Medium | Instruction Styling | #7 | Build command omits `--offline` required in no-network container | `instruction.md:13` `cargo build --workspace --release`; `task.toml:24` `allow_internet=false`; `tests/test.sh:20` `CARGO_NET_OFFLINE=true cargo build --release --offline`; agents in report needed `--offline` | Add `--offline` to instruction build command |

*Low (not blockers alone):* `jobs_test3/` in task parent (#41 cleanup); `codebase_size = "minimal"` should be `"small"` (metadata accuracy); module-level docstring missing in `test_outputs.py`.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Wrong trace path in instruction (ChatGPT / LLMaJ `behavior_in_task_description` / `typos`) | **Agree** | `instruction.md:3` vs `Dockerfile:50` vs `test.sh:30` |
| 2 | Classification under-specified vs tests (ChatGPT High / instruction sufficiency analysis) | **Partially agree** | Tests enforce exact values at `test_outputs.py:227-256,289-300`; thresholds/format ARE in `classify/src/lib.rs:30-42` and fixed oracle at `solution/fixed/classify_lib.rs:15-27` — debugging task mitigates but instruction/contract gap caused systematic GPT classify failures (52–55/55 pass) |
| 3 | Instruction omits `--offline` build flag (ChatGPT Medium) | **Agree** | `instruction.md:13,26` vs `test.sh:20`; `allow_internet=false` |
| 4 | `jobs_test3/` artifacts in ZIP (ChatGPT Low) | **Agree** | `network-flow-aggregator/jobs_test3/` present in task folder |
| 5 | Rubric format acceptable for non-milestone (ChatGPT) | **Agree** | `entire-report.txt:392-408` — single `# Rubric 1` header + flat `Agent …, ±N` lines; per `docs/guidelines/rubrics.md:64` `# Rubric 1` optional, no `# Rubric 2+` |
| 6 | Dockerfile digest pinning OK (ChatGPT) | **Agree** | `Dockerfile:1,26` `rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` |
| 7 | Non-canonical base image blocker (Harbor REVIEW REPORT) | **Disagree** | Report self-corrects ("No issue here on closer inspection"); digest-pinned canonical Rust image |
| 8 | `codebase_size = "minimal"` wrong (Harbor REVIEW REPORT warning) | **Agree** (Low) | 5-crate workspace + lockfile + traces; should be `"small"` — not a High blocker |
| 9 | Classification thresholds acceptable because agents read code (Harbor REVIEW REPORT suggestion) | **Partially agree** | Valid for debugging paradigm; still caused measurable GPT failures and #27/#55 concerns |
| 10 | Test quality review ACCEPT (Harbor TEST QUALITY REVIEW) | **Agree** | Comprehensive behavior tests + anti-cheat; no significant verifier flaws |
| 11 | Automated review #54 too easy at 100% | **Disagree** | `entire-report.txt:23-24` worst model GPT-5.5 **40%** (2/5); Claude 100% is best model, not worst |
| 12 | Automated review #31 missing test docstrings | **Disagree** | All 55 `def test_*` methods have docstrings; only module-level docstring absent (`validate` warning) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~27 lines, under limit | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads like a dev brief, not a spec doc | `instruction.md` |
| 3 | CHECK | No excessive markdown | No heavy headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements list, no numbered solve script | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Describes pipeline stages, not fix walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | UNCHECK | Well specified | Wrong trace path; classify/offline gaps | `instruction.md:3,13,19-22` |
| 8 | CHECK | Interesting | Realistic multi-crate Rust debugging | task content |
| 9 | CHECK | Unique | Network-flow aggregation debugging; no duplicate found in review | — |
| 10 | CHECK | Absolute paths only | All paths absolute (one wrong location) | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No "network-flow-aggregator" string | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Local COPY only | `Dockerfile` |
| 14 | CHECK | Pinned pip deps | `pytest==8.3.2` etc. | `Dockerfile:10,35` |
| 15 | CHECK | FROM digest-pinned | Both stages pinned | `Dockerfile:1,26` |
| 16 | CHECK | Build context in environment/ | No COPY outside env | `Dockerfile` |
| 17 | CHECK | No ground-truth answers in env | Buggy starter code only; no solution leak | `environment/` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose doesn't conflict mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in image; test.sh only cargo/pytest | `Dockerfile`, `test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Docker unavailable locally; static review shows derive-from-build path | `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | Uses `--offline` cargo build | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction | Copies fixed sources, builds, runs binary | `solution/solve.sh` |
| 24 | CHECK | reward.txt always written | Canonical 0/1 block | `test.sh:46-50` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Trace path mismatch; exact classify values not in instruction | blockers 1–2 |
| 28 | CHECK | Tests check correctness | Exact numeric assertions on trace-derived values | `test_outputs.py` |
| 29 | CHECK | Behavior not implementation | Tests JSON output, not source grep | `test_outputs.py` |
| 30 | CHECK | No brittle format-only checks | `"Protocol:"`/`"Bytes:"` match shipped format string in classify code | `classify/src/lib.rs:41-42` |
| 31 | CHECK | Informative test docstrings | All 55 test methods documented | `test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives (-5,-5,-3,-2) | `entire-report.txt:404-407` |
| 33 | CHECK | Rubric scores in {±1,2,3,5} | All lines comply | `entire-report.txt:392-407` |
| 34 | CHECK | Rubric Agent format | 15 Agent lines | `entire-report.txt:392-407` |
| 35 | CHECK | Rubric detailed/precise | Task-specific crate-level criteria | `entire-report.txt:392-407` |
| 36 | CHECK | Rubric positive phrasing | Bad behavior uses negative scores | `entire-report.txt:404-407` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:392-407` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:392-407` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:392-407` |
| 40 | CHECK | Required files present | All core files exist | task folder |
| 41 | UNCHECK | Clean parent directory | `jobs_test3/` run artifacts present | `network-flow-aggregator/jobs_test3/` |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | Complete `[metadata]`, timeouts | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Rust data-processing task | `task.toml:7-12` |
| 45 | UNCHECK | Difficulty matches agent rates | Declared `hard`; worst-model 40% → medium tier | `task.toml:6`, `entire-report.txt:23-24` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked in image | No COPY tests/ | `Dockerfile` |
| 51 | CHECK | Solution not accessible in env | No solution/ COPY | `Dockerfile` |
| 52 | CHECK | Agent can't trivially modify inputs | Instruction prohibits; anti-cheat alternate trace | `instruction.md:24`, `test_outputs.py:411+` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model GPT-5.5 40% | `entire-report.txt:23-24` |
| 55 | UNCHECK | Not too hard/unfair | Wrong trace path + classify doc gap unfair to literal instruction followers | blockers 1–2 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 41, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Trace at stated path | — | **gap** | instruction wrong path; tests use `/app/traces/` |
| Parse 30 records | `test_exact_record_count`, `test_total_flows_exact` | covered | `test_outputs.py:21-25,308-312` |
| Aggregate bytes/packets per protocol | `test_exact_tcp_bytes`, `test_exact_udp_bytes`, etc. | covered | `test_outputs.py:100-160` |
| Flow counts / unique pairs | `test_exact_tcp_flow_count`, `test_tcp_unique_pairs_exact` | covered | `test_outputs.py:171-207` |
| Risk scores 0–100 | `test_risk_scores_in_valid_range` | covered | `test_outputs.py:265-270` |
| Exact risk_score=20 for normal | `test_tcp_risk_score_exact`, `test_udp_risk_score_exact` | **gap** | in code `classify/src/lib.rs:35` not instruction |
| Category `normal` for sample data | `test_tcp_category_normal`, `test_udp_category_normal` | **gap** | thresholds in code not instruction/contract |
| Details with protocol embedded | `test_details_contains_protocol` | partial | instruction weaker than `"Protocol:"` exact substring |
| JSON keys schema | `test_report_has_*` | covered | `instruction.md:20-22`, `test_outputs.py:44-63` |
| Output at `/tmp/test_report.json` | implicit via test.sh | covered | `instruction.md:14`, `test.sh:30` |
| Anti-cheat: process input not hardcode | `test_pipeline_processes_alternate_trace` | covered (not in instruction) | `test_outputs.py:411+` — acceptable anti-cheat |
| Offline cargo build | — | **gap** | `test.sh:20` not instruction |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers 1–3, #7, #27, #55 |
| `environment/Dockerfile` | Blocker 1, #15, #20, #50 |
| `environment/docs/contract.md` | Blocker 2, spec alignment |
| `environment/classify/src/lib.rs` | Blocker 2 adjudication, #30 |
| `tests/test.sh` | Blockers 1, 3, #20 |
| `tests/test_outputs.py` | Blockers 2, #27, #31 |
| `task.toml` | #45, #54 |
| `entire-report.txt` | Agent stats, rubric, LLMaJ, external claims |
| `solution/solve.sh` | #22, #23 |
| `solution/fixed/classify_lib.rs` | Blocker 2 adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: network-flow-aggregator/ ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: informative_test_docstrings — module-level docstring missing
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Failures clustered on classify crate |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Per submission export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no — declared hard, observed medium; not a revision blocker alone |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone Rust task; report matches folder |
| 1 Instruction | ☑ | Wrong trace path confirmed High; classify/offline gaps Medium |
| 2 Environment | ☑ | Digest-pinned, tmux+asciinema, no tests/solution COPY |
| 3 Oracle | ☐ | Not executed (no Docker); static review passes |
| 4 Verifiers | ☑ | Canonical reward block; offline rebuild anti-cheat |
| 5 Metadata | ☑ | `codebase_size` understated; difficulty vs rates noted |
| 6 Rubric | ☑ | Non-milestone flat list with optional `# Rubric 1`; NOT milestone multi-block format |
| 7 LLMaJ & agent evidence | ☑ | Trace path + classify failures verified; #54 automation wrong |
| 8 Novelty & fairness | ☑ | Multi-crate debugging; trace path unfairness confirmed |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Rust debugging task — the multi-crate workspace, rebuild-from-source verifier, and alternate-trace anti-cheat are all well done, and the rubric looks good. Before we can accept, please fix the trace path in `instruction.md`: it currently says `/app/environment/traces/sample_trace.csv` but the container and tests use `/app/traces/sample_trace.csv`. While you're there, document the classification thresholds, normal risk score (20), and details string format the tests expect, and mention `--offline` on the cargo build since the environment has no network. Also remove the `jobs_test3/` folder from the submission zip.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2, 3 |
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

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review network-flow-aggregator/ --report entire-report.txt`._
