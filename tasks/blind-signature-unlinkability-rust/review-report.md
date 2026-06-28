# Terminus Review Report: `blind-signature-unlinkability-rust`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | pass |
| **Oracle** | not executed (Docker unavailable locally; report 100% 3/3) |
| **CHECK count** | 45 |
| **UNCHECK count** | 10 |

**Error categories (internal):** Task Difficulty, Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Revise. Digest-pinned Rust environment, anti-cheat design, oracle approach, verifier structure, and rubric (platform) are solid. Two real High blockers remain: `task.toml` declares `hard` but worst-model pass rate is 40% (Medium tier), and the KS statistic is numerically verified with an explicit two-sided reference (`i/n` and `(i+1)/n`) that instruction.md does not spell out — a near-perfect agent run (43/45) failed on this alone per `entire-report.txt`. Automated #54 “too easy” is a false positive (worst model is Claude 40%, not GPT 100%).

**Insights (concise):**

- Worst-model rate is **40%** (Claude 2/5), not 100%; tier = **Medium**, not trivial/rejected.
- KS left-side step exists in buggy `adversary.rs` and oracle leaves it intact; removing it is a plausible reading of the high-level KS sentence in `instruction.md:9`.
- Instruction is long (~9 dense paragraphs) but formula-dense debugging spec, not fluff; stylistic length is secondary to the two substantive blockers.
- LLMaJ `behavior_in_task_description` PASS is overstated for KS two-sided steps; `behavior_in_tests` PASS is accurate.
- Rubric in `entire-report.txt` (lines 291–307) meets format/negative-count rules; no `rubric.txt` in task folder (portal-only).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty, Metadata Issues | #45 | Declared `difficulty = "hard"` but observed worst-model pass rate 40% → **Medium** tier (20–60%) | `task.toml:8`; `entire-report.txt:17-19`; `docs/guidelines/difficulty.md:9-12` | Set `difficulty = "medium"` in `task.toml`, or rebalance until worst model ≤20% |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | KS statistic tested to 6 decimals via explicit two-sided formula (`abs(i/n - sc)` and `abs((i+1)/n - sc)`); instruction only gives high-level “max abs diff between empirical CDF and uniform CDF” without both steps | `instruction.md:9`; `tests/test_outputs.py:75-78,387-391`; `environment/src/adversary.rs:36-41`; `entire-report.txt:99-100,106` | Add explicit two-sided KS formula to `instruction.md` (both `i/n` and `(i+1)/n` at each sorted score), or relax `test_ks_statistic_value` / `test_full_independent_recompute` |

*Low note (not a main blocker):* `#1` instruction length (~9 paragraphs) exceeds the 3-paragraph styling guideline, but content is necessary formula specification for a 16-bug pipeline task — trim only if formulas can move without creating new spec gaps.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` but evaluation is Medium (Claude 40%, GPT 100%) | **Agree** | `task.toml:8`; `entire-report.txt:13-19`; worst model = min(40%,100%) = 40% → Medium per `difficulty.md:10-11` |
| 2 | KS contract should match verifier two-sided computation (`i/n` and `(i+1)/n`) | **Agree** | `instruction.md:9` (high-level only); `tests/test_outputs.py:75-78` (both steps); docstring `387-388` says “two-sided”; agent M9yAiuP 43/45 per `entire-report.txt:88,106` |
| 3 | Automated review #54: task too easy (100% worst model) | **Disagree** | Worst model is Claude **40%**, not GPT 100%; `difficulty.md:14` uses worst model for tier floor; #54 should **CHECK** |
| 4 | Instruction too long (#1 blocker) | **Partially agree** | 9 paragraphs / ~783 words in `instruction.md`; exceeds `prompt-styling.md:7` — but dense testable formulas, not synthetic fluff; Low severity for this task type |
| 5 | LLMaJ `behavior_in_task_description` PASS | **Partially agree** | Most formulas explicit; KS two-sided steps missing despite numerical enforcement |
| 6 | Non-canonical Rust base image warning | **Agree (non-blocking)** | `environment/Dockerfile:1` uses `rust:1.85-slim@sha256:…`; digest-pinned; no canonical Rust image — justified per `entire-report.txt:159-176` |
| 7 | `test.sh` `cargo build` may fetch crates offline | **Agree (non-blocking)** | `tests/test.sh:5`; Dockerfile pre-builds at `Dockerfile:19`; task only patches existing deps |
| 8 | Environment instability (ZnkQ5wF file resets) | **Unverified** | `entire-report.txt:105-112`; no reproducible evidence in task artifacts; infrastructure, not task author bug |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 9 dense paragraphs exceed 3-paragraph cap | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone describing a broken audit tool | `instruction.md:1` |
| 3 | CHECK | No excessive markdown formatting | No ##/###/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States formulas/outcomes, not debug workflow | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT to compute, not HOW to find bugs | `instruction.md:15` |
| 6 | CHECK | No design doc style I/O tables | Prose formulas only | `instruction.md` |
| 7 | CHECK | Instruction is well specified | All major metrics have explicit formulas/paths | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Crypto unlinkability auditing is useful | — |
| 9 | UNCHECK | Instruction is unique | Cannot verify vs TB2/TB3 corpus from artifacts | — |
| 10 | CHECK | All paths are absolute | `/app`, `/app/config`, etc. | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction.md | No folder/task name string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content (except packages) | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Python/pip deps pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:7-8` |
| 15 | CHECK | Base image digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment context stays in environment/ | COPY only env subdirs | `environment/Dockerfile:12-17` |
| 17 | CHECK | Environment has no ground-truth answers | Intentional bugs + misleading docs, no precomputed report | `environment/src/*.rs`, `docs/` |
| 18 | CHECK | No privileged/dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh only cargo build + pytest | `environment/Dockerfile:7-8`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not run locally (no Docker); report shows 100% 3/3 | `entire-report.txt:23` |
| 22 | CHECK | Oracle needs no internet | solve.sh patches files + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction (not hardcoded output) | 16 targeted source patches then rebuild/run | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt on failure path | mkdir + echo 0 upfront; echo 1/0 at end | `tests/test.sh:2-3,17-21` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:17-21` |
| 27 | UNCHECK | Tests aligned with instructions | KS two-sided formula enforced but not specified | `instruction.md:9`, `tests/test_outputs.py:75-78` |
| 28 | CHECK | Tests check correctness not just format | Independent `reference()` recomputation | `tests/test_outputs.py:1-104` |
| 29 | CHECK | Tests verify behavior not implementation | No source grep; runs binary + checks JSON | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | `math.isclose` with tolerance | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative docstrings | All 45 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubric ≥3 negative penalties | 5 negatives in platform rubric | `entire-report.txt:303-307` |
| 33 | CHECK | Rubric scores from {±1,2,3,5} | All scores valid | `entire-report.txt:291-307` |
| 34 | CHECK | Rubric format `Agent …, ±N` | One line per criterion | `entire-report.txt:291-307` |
| 35 | CHECK | Rubric criteria detailed and precise | Specific behavioral criteria | `entire-report.txt:291-307` |
| 36 | CHECK | Rubric positive language for negatives | e.g. “Agent lets a profile override…, -5” | `entire-report.txt:303` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path references | `entire-report.txt:291-307` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:291-307` |
| 39 | CHECK | Rubric does not mention oracle/NOP | None | `entire-report.txt:291-307` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary parent files | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | `anonymous` fields | `task.toml:4-5` |
| 43 | CHECK | Other required metadata present | category, timeouts, languages | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | rust, security, cryptography | `task.toml:6,12` |
| 45 | UNCHECK | Difficulty matches observed pass rates | Declared hard; observed Medium (40% worst) | `task.toml:8`, `entire-report.txt:17-19` |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone tests scoped | N/A | `task.toml:10` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | No COPY solution/ | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs | Alternate-input dynamic tests | `tests/test_outputs.py:474-530` |
| 53 | CHECK | Git repos pinned if cloned | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst model 40% < 80% | `entire-report.txt:17-19`, `difficulty.md:57` |
| 55 | UNCHECK | Task not too hard or unfair | KS spec trap penalizes careful readers | `entire-report.txt:99-106`, `instruction.md:9` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 9, 21, 27, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Rolling hash + similarity correlation | `test_correlation_*` | covered | `instruction.md:3`, `tests/test_outputs.py:178-195` |
| Strict detection threshold | `test_detection_is_strictly_above_threshold` | covered | `instruction.md:3`, `tests/test_outputs.py:195` |
| Timing proximity clamped ≥0 | `test_timing_proximity_clamped_nonnegative` | covered | `instruction.md:3` |
| Combined score blend weights | `test_combined_score_blend`, `test_combined_weights_not_swapped` | covered | `instruction.md:3` |
| Greedy one-to-one matching | `test_matching_*` | covered | `instruction.md:5` |
| Advantage = mean of matched | `test_advantage_is_mean_of_matched_not_all_pairs` | covered | `instruction.md:5` |
| unlinkability / security bits | `test_unlinkability_score`, `test_security_bits_*` | covered | `instruction.md:5` |
| Entropy 10 bins log2 | `test_correlation_entropy_bits` | covered | `instruction.md:7` |
| Population batch std | `test_batch_std_is_population` | covered | `instruction.md:7` |
| KS critical value 1.36/sqrt(N) | `test_ks_critical_value_uses_sqrt_n` | covered | `instruction.md:9`, `tests/test_outputs.py:394-400` |
| KS statistic two-sided (i/n and (i+1)/n) | `test_ks_statistic_value`, `test_full_independent_recompute` | **gap** | `instruction.md:9` vs `tests/test_outputs.py:75-78` |
| Commitment strength formulas | `test_commitment_*` | covered | `instruction.md:11` |
| settings.toml authority | `test_*_setting` | covered | `instruction.md:1,15` |
| CLI non-zero without args | `test_cli_no_args_nonzero` | covered | `instruction.md:1` |
| Deterministic 6-decimal output | `test_deterministic_output` | covered | `instruction.md:15` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45, blocker 1 |
| `instruction.md` | #1, #7, #27, blocker 2, KS gap |
| `tests/test_outputs.py` | #27-31, blocker 2, spec alignment |
| `tests/test.sh` | #20, #24 |
| `environment/Dockerfile` | #14-20, #50-51 |
| `environment/src/adversary.rs` | KS two-sided in buggy code |
| `solution/solve.sh` | #22-23, oracle approach |
| `entire-report.txt` | Agent stats, KS agent failure, rubric |
| `docs/guidelines/difficulty.md` | Tier rules, #45, #54 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: blind-signature-unlinkability-rust/ ===
Summary: 0 error(s), 0 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Best model |
| terminus-claude-opus-4-8 | 40.0% (2/5) | 1 timeout, 2 other |
| oracle | 100.0% (3/3) | per report |
| nop | 0.0% (1/1) | per report |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular (non-milestone) Rust security task |
| 1 Instruction | ☑ | Well-specified except KS two-sided steps; long but formula-dense |
| 2 Environment | ☑ | Digest-pinned Rust slim; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☐ | Not run locally (Docker down); static review + report 100% |
| 4 Verifiers | ☑ | Canonical reward pattern; 45 behavior tests; KS gap flagged |
| 5 Metadata | ☑ | difficulty mismatch is sole metadata blocker |
| 6 Rubric | ☑ | Platform rubric in report passes all criteria |
| 7 LLMaJ & agent evidence | ☑ | KS spec failure confirmed; #54 automated false positive corrected |
| 8 Novelty & fairness | ☑ | 16-bug pipeline fair except KS trap |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The digest-pinned Rust environment, verifier design, anti-cheat measures, and rubric are solid. Two blockers remain: `task.toml` lists `hard` but worst-model pass rate is 40% (Medium tier — update to `medium` or rebalance), and the KS statistic is verified with an explicit two-sided formula (`i/n` and `(i+1)/n` per sorted score) that `instruction.md` does not state — a 43/45 agent run failed on this per the evaluation report. Document the two-sided KS steps in the instruction or align the tests.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Metadata Issues | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2 |
| Instruction Styling | yes | 2 |
| Instruction Styling (length only) | note | — |
