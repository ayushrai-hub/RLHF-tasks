# Terminus Review Report: `telecom-plan-revenue-by-tier`

**Generated:** 2026-06-29 (manual audit)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/telecom-plan-revenue-by-tier`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 1 info) |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** Artifacts are strong: digest-pinned offline env, pytest baked via hashed `requirements.lock`, instruction↔codebook↔tests aligned, hidden-lake generalization, and nine distinct rubric negatives in correct **flat** (non-milestone) format. The automated review falsely flagged #14 and #20. One real blocker remains: GPT-5.5 passed 5/5 (100% worst-model rate >80%), failing #54. Claude Opus 4.8 at 20% supports declared `hard` for #45 but does not excuse the worst-model floor.

**Insights (concise):**

- `subscription_restatement.csv` in `entire-report.txt` agent-failure analysis is **stale** — nowhere in `instruction.md`, codebook, or lake; authoritative file is `subscription_status_corrections.csv`.
- Automated `#14` / `#20` failures are false positives: `environment/requirements.lock` pins `pytest==8.2.0` with sha256 hashes; Dockerfile installs via `--require-hashes -r requirements.lock`; `tests/test.sh` does not runtime-install.
- Platform rubric (lines 159–179 of export) is correctly **non-milestone** flat `Agent …, ±N` — no `# Rubric 2+` headers; 28 positive pts, 9 negatives.
- Voice-minute `floor()` near-miss is caught by `test_final_answer_matches` / hidden lake; codebook `seconds / 60` implies raw floats — optional clarity only (Low).
- `instruction.md` is 6 paragraphs (~585 words) — above the 3-paragraph styling target (#1 UNCHECK) but detail is delegated to shipped `codebook.md` / `question.md` (legitimate pattern); not a standalone blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #54 | Worst-model pass rate 100% (>80% rejected tier) | `entire-report.txt:19-21` — `terminus-gpt5-5: 100.0% (5/5)`; `docs/guidelines/difficulty.md:12` | Harden task so GPT-5.5 worst-model rate drops ≤80% (more decoys, subtler proration/correction traps, or recalibrate after additional agent runs). Claude at 20% shows the task *can* be hard — target is bringing the easy-model rate down. |

*No other High/Medium blockers. Automated #14/#20 are disproven below.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High/Medium blockers; Accept (ChatGPT) | Partially agree | Agree on spec alignment, digest pin, corrections filename, rubric format. **Disagree on Accept** — #54 fails (GPT 100%). |
| 2 | `subscription_restatement.csv` stale filename in instruction (entire-report agent-failure §4) | **Disagree** | `grep` across task: zero hits for `subscription_restatement` or `plan_catalog`. `instruction.md:26` says "authoritative restatement"; lake + tests use `subscription_status_corrections.csv` (`tests/test_outputs.py:44`). JeptUSJ agent assumed wrong names — not an instruction bug. |
| 3 | Verifier robust; hidden lake; anti-naive checks (ChatGPT / test-quality review) | Agree | `test_hidden_lake_generalizes`, `test_naive_pipeline_fails`, `test_corrections_change_billed_set`, `test_proration_changes_recurring` in `tests/test_outputs.py:395-450`; export test-quality review lines 124-155. |
| 4 | Optional: explicit no-floor for voice minutes (ChatGPT Low) | Agree (Low only) | `environment/docs/codebook.md:125-127` "dividing by 60"; reference uses float `duration_sec / 60.0` (`tests/test_outputs.py:115`); oracle R uses `duration_sec / 60` (`solution/solve.sh:84`). Not a spec gap — caught by answer tests. |
| 5 | Optional: dedicated `voice_overage_total_usd` intermediate (ChatGPT / test-quality) | Agree (Low only) | `question.md` schema has no voice-overage field; `test_intermediates_match` checks recurring/data/count only. Voice errors still fail `test_final_answer_matches` / `by_tier`. |
| 6 | Dockerfile digest-pinned canonical base (ChatGPT) | Agree | `environment/Dockerfile:1` `python:3.13-slim-bookworm@sha256:01f42367…`; tmux + asciinema lines 11-12. |
| 7 | LLMaJ `behavior_in_*` all pass (entire-report) | Agree | Cross-checked instruction, tests, Dockerfile, solve.sh — aligned. |
| 8 | Non-milestone task uses milestone rubric format (user concern) | **Disagree** | Platform rubric (`entire-report.txt:159-179`) is flat `Agent …, ±N` with no `# Rubric 1/2` blocks. Matches `docs/guidelines/rubrics.md:64` for non-milestone tasks. `task.toml:10` `number_of_milestones = 0`. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 6 paragraph blocks, ~585 words — above styling target | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer briefing tone; no synthetic anti-patterns | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no ##/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | No HINT_PATTERNS hits | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes WHAT; codebook holds billing rules | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, output fields, doc pointers | `instruction.md:17-51` |
| 8 | CHECK | Instruction is interesting | Real telecom billing reconciliation scenario | — |
| 9 | CHECK | Instruction is unique | Distinct multi-source lake + proration + corrections | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/data`, `/app/analysis.R`, `/app/answer.json` | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No folder-name string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.lock` has `pytest==8.2.0` + hashes; `--require-hashes` install | `environment/requirements.lock:10-12`, `environment/Dockerfile:16-17` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment/ | All COPY from env dir | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stub `analysis.R` returns zeros; codebook defines rules not dollar totals | `environment/analysis.R:17-24` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in lock file + Dockerfile; test.sh only runs pytest | `environment/requirements.lock`, `tests/test.sh:9` |
| 21 | UNCHECK | Oracle passes consistently | Docker unavailable; static review only — oracle logic derives from lake | `solution/solve.sh` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Rscript + local lake only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Full R pipeline: effective dating, corrections, proration, dedup | `solution/solve.sh:28-152` |
| 24 | CHECK | test.sh writes reward.txt | Writes 0/1 to `/logs/verifier/reward.txt` | `tests/test.sh:7-14` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `tests/test.sh` |
| 27 | CHECK | All tests aligned with instructions | Every test traces to instruction + codebook + question | §5 below |
| 28 | CHECK | Tests check for correctness, not just format | Independent Python reference recompute | `tests/test_outputs.py:256-328` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs `Rscript /app/analysis.R`, checks JSON output | `tests/test_outputs.py:331-344` |
| 30 | CHECK | No brittle exact string matching | `ABS_TOL = 0.5` monetary floor | `tests/test_outputs.py:34` |
| 31 | CHECK | Tests have informative names or docstrings | Module + per-test docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 9 negatives in platform rubric | `entire-report.txt:172-179` |
| 33 | CHECK | Rubric scores from {1,2,3,5, negatives} | All ±1,2,3,5 | `entire-report.txt:159-179` |
| 34 | CHECK | Each rubric criterion one line `Agent …, ±N` | 22 flat lines; no milestone headers | `entire-report.txt:159-179` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific trace criteria (decoys, proration, corrections) | `entire-report.txt:159-179` |
| 36 | CHECK | Rubric criteria use positive language | Bad-behavior lines use "Agent [verb]s …, -N" form | `entire-report.txt:172-179` |
| 37 | CHECK | Rubric does not reference /tests/ or pytest | No test-path refs | `entire-report.txt:159-179` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | References codebook behavior, not filenames | `entire-report.txt:159-179` |
| 39 | CHECK | Rubric does not mention oracle or NOP | None | `entire-report.txt:159-179` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean layout | task root |
| 42 | CHECK | author_name and author_email present | `task.toml:4-5` | `task.toml` |
| 43 | CHECK | All other required metadata fields present | timeouts, category, tags, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | `languages=["r"]`, `category=data-processing` | `task.toml` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard` defensible: Claude 20% ≤20% (best-model rule) | `entire-report.txt:19-21`, `docs/guidelines/difficulty.md:9` |
| 46 | UNCHECK | steps/ layout (milestones) | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scoped to milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:14` |
| 51 | CHECK | Solution/ground truth not accessible in environment | solution/ excluded | `environment/.dockerignore:13` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Hidden-seed lake generalization | `tests/test_outputs.py:441-450` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | UNCHECK | Task is not too easy (>80% worst model) | GPT-5.5 100% (5/5) | `entire-report.txt:21` |
| 55 | CHECK | Task is not too hard or unfair | Failures = skipped codebook / R errors / minor float handling; spec in shipped docs | `entire-report.txt:41-99` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 55 |
| **UNCHECK** | 1, 21, 46, 47, 48, 49, 54 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Write `/app/analysis.R`, read `DATALAKE_DIR` fallback `/app/data` | `test_output_schema` (via `_run_agent`) | covered | `instruction.md:33-38`, `tests/test_outputs.py:331-344` |
| Output `/app/answer.json` with 5 fields | `test_output_schema` | covered | `instruction.md:40-46`, `tests/test_outputs.py:359-371` |
| `by_tier` sums to `answer`, 4 tiers | `test_final_answer_matches` | covered | `question.md:13-16`, `tests/test_outputs.py:374-384` |
| Effective-dated rate card (cycle-start) | `test_naive_pipeline_fails` (`answer_latest_card`) | covered | `codebook.md:60-67`, `tests/test_outputs.py:435` |
| Status corrections ≤ cycle end | `test_corrections_change_billed_set` | covered | `codebook.md:38-48`, `tests/test_outputs.py:403-411` |
| In-cycle window by row timestamp | `test_naive_pipeline_fails` (`answer_no_window`) | covered | `codebook.md:12-18`, `tests/test_outputs.py:433` |
| Dedup session_id / call_id | `test_naive_pipeline_fails` (`answer_no_dedup`) | covered | `codebook.md:21-29`, `tests/test_outputs.py:434` |
| Exclude -1 sentinel; bytes→MB | `_collect` + naive tests | covered | `codebook.md:117-121`, `tests/test_outputs.py:99-103` |
| Mid-cycle proration (fee + allowance split) | `test_proration_changes_recurring`, naive proration variants | covered | `codebook.md:69-113`, `tests/test_outputs.py:395-400,437-438` |
| Recurring / data-overage / active-count intermediates | `test_intermediates_match` | covered | `instruction.md:43-50`, `tests/test_outputs.py:386-392` |
| Generalizes beyond committed lake | `test_hidden_lake_generalizes` | covered | `instruction.md:33-36`, `tests/test_outputs.py:441-450` |
| No reading `/tests` | `test_no_forbidden_access` | covered | `tests/test_outputs.py:414-418` |
| Voice minutes = seconds/60 (no floor) | `test_final_answer_matches` (indirect) | covered | `codebook.md:125-127`, `tests/test_outputs.py:115` |
| Dedicated voice-overage intermediate field | — | gap (Low) | Not in schema; caught via totals |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #7, #10, adjudication #2 |
| `environment/Dockerfile` | #14, #15, #20 |
| `environment/requirements.lock` | #14, #20 |
| `environment/docs/codebook.md` | #17, §5, adjudication #4 |
| `environment/docs/question.md` | §5 schema |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | §5, #27-29, adjudication #3 |
| `solution/solve.sh` | #22-23 |
| `task.toml` | #44-46, #54 |
| `entire-report.txt` | #45, #54, §3, rubric #32-39 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate telecom-plan-revenue-by-tier/
Summary: 0 error(s), 1 warning(s), 1 info
INFO: non-milestone (milestones preferred, not blocked)
WARNING: pinned_dependencies — false positive on Dockerfile pip line (lock file has hashes)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Drives #54 failure |
| terminus-claude-opus-4-8 | 20.0% (1/5) | Supports declared `hard` for #45 |
| oracle | 100.0% (3/3) | Per export; not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 100.0% |
| Observed tier (worst-model) | rejected (>80%) |
| Declared difficulty | hard |
| Tier match (#45) | yes (Claude ≤20%) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular R/data-processing task; export matches folder |
| 1 Instruction | ☑ | 6 paras (UNCHECK #1); no stale filename; points to codebook |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; pytest in image; allow_internet=false |
| 3 Oracle | ☐ | Docker down — static review of solve.sh only |
| 4 Verifiers | ☑ | Canonical reward; no runtime installs; strong cross-check + hidden lake |
| 5 Metadata | ☑ | Complete; non-milestone |
| 6 Rubric | ☑ | Flat non-milestone format correct; 9 negatives; 28 positive pts |
| 7 LLMaJ & agent evidence | ☑ | Stale spec-gap claim disproven; #54 confirmed |
| 8 Novelty & fairness | ☑ | Multi-step source selection + billing; anti-cheat solid |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the multi-source lake, codebook-driven billing rules, hidden-seed verifier, and anti-naive pipeline checks are all in great shape, and the rubric is correctly formatted for a non-milestone submission. I didn't find any spec-test gaps or the stale `subscription_restatement.csv` filename the failure analysis mentioned; the real correction file is `subscription_status_corrections.csv` and the docs/tests agree. The one thing blocking accept: GPT-5.5 cleared it 5/5 while Claude was at 20%, so the worst-model pass rate is 100% — above the too-easy threshold. Please harden or recalibrate so the easier frontier model lands at or below 80% before resubmitting.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Oracle Solution Issues | no | — |

---

_Manual audit per `prompt.md`. Automated `./scripts/terminus review` false-flagged #14/#20; corrected above._
