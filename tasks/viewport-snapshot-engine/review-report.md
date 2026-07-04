# Terminus Review Report: viewport-snapshot-engine

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (false-positive `[[steps]]` count in comment; see §7) |
| **Oracle** | not executed (Harbor local config error) |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong four-milestone viewport snapshot task with excellent reference tests, offline Dockerfile, and correct milestone rubric layout. One real High blocker: milestone 1 root-positioning prose and Rubric 1 line both read as forcing the root border-box to `[0,0]`, while the reference/tests treat viewport `(0,0)` as the parent content origin and place the root at its own `box[x,y]`. Agent data (5/6 trials, 0% GPT-5.5) corroborates systematic misreads. Fix that wording; align rubric line 497.

**Insights (concise):**

- Milestone rubric format (`# Rubric 1`–`4`) is **correct** — this is a 4-milestone task (`number_of_milestones = 4`); not a non-milestone task mis-formatted.
- Per-block rubric positives are within cap (18/22/19/21); summed 80 across blocks is not the milestone rule.
- `task.toml` line 12 comment contains literal `[[steps]]`, triggering validator false error (actual step count is 4).
- Automated `#1` (769 combined words) and `#14` (no `==` on pip line) are false positives — per-milestone instructions are ~180–200 words; pip uses `--require-hashes` + lockfile.
- M1 designed case 0 already uses root `box: [4,6,…]` (`reference.py:305`); 2/3 designed cases use `[0,0]` root, so random cases carry most nonzero-root signal.
- Oracle static review shows real algorithm (`walk(case["root"], -1, 0, 0)` → `ox + bx`); not hardcoded.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues, Rubric | #7, #27, #55 | Root-positioning rule is ambiguous and conflicts with verifier behavior for nonzero root `box[x,y]`. | `steps/milestone_1/instruction.md:3` — *"The root's box top-left is the viewport origin"* reads as equating root position to `(0,0)`. General rule at `:1` says `x,y` are relative to parent's content origin. Reference: `steps/milestone_1/tests/reference.py:37-41,61` — `go(case["root"], -1, 0, 0)` then `x = origin_x + box[0]` → root absolute `[box[0], box[1], …]`. Random roots: `reference.py:287-289` uses `rng.randint(-6,6)` for root x/y. Platform rubric line 497: *"Agent places the root node's border-box top-left at the viewport origin, +2"* repeats the same reading. Agent export: `entire-report.txt:75-100` — 5/6 trials forced root to `[0,0]`; `test_random_cases` 5/10 pass on M1. | Rewrite M1 to state explicitly: viewport `(0,0)` is the root's parent content origin; the root's absolute border-box top-left is `box[0], box[1]` (not forced to `[0,0]`). Update platform Rubric 1 line 497 to match. Optional: add one explicit worked example `box:[4,6,80,80]` → absolute `[4,6,80,80]`. |

*No other High/Medium blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Root-positioning wording is ambiguous; tests expect `box[x,y]` not forced `[0,0]` (ChatGPT High) | **Agree** | `instruction.md:3` vs `reference.py:39-41,61`; rubric `entire-report.txt:497` |
| 2 | Platform rubric line 497 conflicts with verifier (ChatGPT High) | **Agree** | `entire-report.txt:497` vs `reference.py:61` |
| 3 | Add explicit nonzero-root example in instruction (ChatGPT Low) | **Partially agree** | Helpful but not blocking; `reference.py:305` already tests `[4,6,…]` in designed case 0 |
| 4 | Instruction sufficiency FAIL — systematic root misread (export analysis) | **Agree** | `entire-report.txt:55-100`; worst-model 0%, M1 `test_random_cases` 5/10 |
| 5 | Designed cases mask nonzero-root bug because most roots are `[0,0]` (export) | **Partially agree** | Cases 1–2 use `[0,0]` (`reference.py:316-323`); case 0 uses `[4,6]` (`reference.py:305`) — masks partially, not fully |
| 6 | M2 tests enforce canonical JSON not stated in M2 instruction (test-quality review) | **Partially agree (Low)** | M1 `:1` and M3 `:6` specify canonical JSON; M2 inherits cumulative context — not a blocker |
| 7 | Missing root-level `[agent]`/`[verifier]` in task.toml (Harbor review warning) | **Disagree as blocker** | Per-step timeouts present `task.toml:40-74`; Harbor review itself says non-blocking for multi-step |
| 8 | `number_of_milestones != [[steps]]` validation error | **Disagree as substantive blocker** | Comment `task.toml:12` contains literal `[[steps]]`; actual blocks at lines 37,47,57,67 = 4 |
| 9 | Rubric positive total 80 > 40 cap (automated review) | **Disagree** | Milestone rule is per `# Rubric N` block ≤40; blocks are 18/22/19/21 (`entire-report.txt:493-549`) |
| 10 | Non-milestone task using milestone rubric format | **Disagree** | `task.toml:13` `number_of_milestones = 4`; `# Rubric 1`–`4` is required format per `docs/guidelines/rubrics.md:55-66` |
| 11 | Instruction too long / unpinned pip (#1, #14 automated) | **Disagree** | Per-file word counts 202/180/189/198; `Dockerfile:25` `--require-hashes -r requirements.lock` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Each milestone instruction is ~2 paragraphs, 180–200 words | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering brief, not synthetic expert preamble | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | No ##/tables/code fences | all `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only | all `instruction.md` |
| 5 | CHECK | No hints/solving strategies | No leaked algorithms | all `instruction.md` |
| 6 | CHECK | No design-doc tables | None | — |
| 7 | UNCHECK | Well specified | Root rule ambiguous (#7 blocker) | `steps/milestone_1/instruction.md:3` |
| 8 | CHECK | Interesting | Real layout/viewport engine problem | task content |
| 9 | UNCHECK | Unique | Not verified against full TB2/TB3 corpus | — |
| 10 | CHECK | Absolute paths | `/app/viewport.py` in M1 | `steps/milestone_1/instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No "viewport-snapshot-engine" string | all `instruction.md` |
| 12 | CHECK | No canary string | None found | all `instruction.md` |
| 13 | CHECK | No web content fetch | Offline task | `task.toml:27`, `Dockerfile` |
| 14 | CHECK | Pinned pip deps | Hash-locked `requirements.lock` | `Dockerfile:23-25` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `Dockerfile:4` |
| 16 | CHECK | Context in environment/ | Only `requirements.lock` copied | `Dockerfile:23` |
| 17 | CHECK | No ground truth in env | No answers in image | `.dockerignore`, `Dockerfile` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `Dockerfile` |
| 19 | CHECK | Compose doesn't alter mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | Venv baked; test.sh only pytest | `Dockerfile:24-25`, `steps/milestone_1/tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed locally | Harbor error |
| 22 | CHECK | Oracle no internet | solve scripts only `cp` | `solve1.sh` |
| 23 | CHECK | Oracle reflective | Full `viewport.py` implementation | `steps/milestone_1/solution/viewport.py:77` |
| 24 | CHECK | reward.txt canonical block | Present all milestones | `steps/milestone_1/tests/test.sh:14-17` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | all `test_m*.py` |
| 26 | CHECK | Binary rewards | 0/1 only | `test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Root rule instruction↔test mismatch | blocker #1 |
| 28 | CHECK | Tests check correctness | Reference comparison, not format-only | `test_m1.py:41-45` |
| 29 | CHECK | Behavior not implementation grep | Black-box subprocess | `test_m1.py:24-37` |
| 30 | CHECK | No brittle string matching | Canonical JSON specified in M1/M3 | `steps/milestone_1/instruction.md:1` |
| 31 | CHECK | Informative test docstrings | All `test_*` documented | `test_m1.py` et al. |
| 32 | CHECK | ≥3 negative rubric criteria | 12 negatives across 4 blocks | `entire-report.txt:503-549` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | No ±4 | `entire-report.txt:493-549` |
| 34 | CHECK | Rubric format `Agent …, ±N` | 50 lines | `entire-report.txt:493-549` |
| 35 | CHECK | Rubric detailed; per-block ≤40 pts | 18/22/19/21 per block | `entire-report.txt:493-549` |
| 36 | CHECK | Positive phrasing in rubric | Negatives name bad behavior directly | `entire-report.txt:503-549` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:493-549` |
| 38 | CHECK | Rubric no task.toml/instruction refs | Clean | `entire-report.txt:493-549` |
| 39 | CHECK | Rubric no oracle/NOP mentions | Clean | `entire-report.txt:493-549` |
| 40 | CHECK | Required files present | Milestone layout complete | `steps/milestone_*` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Python layout/encoding task | `task.toml:9-20` |
| 45 | CHECK | Difficulty field present | `hard`; worst-model 0% | `task.toml:8`, `entire-report.txt:15-21` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/` | `task.toml`, directory tree |
| 47 | CHECK | solveN.sh per milestone | solve1–4.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1–4.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone tests scoped | Each file tests one milestone | `test_m1.py`–`test_m4.py` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests | `environment/.dockerignore:5` |
| 51 | CHECK | Solution not in environment | No solution COPY | `Dockerfile` |
| 52 | CHECK | Agent can't trivially mutate inputs | Scenarios generated at verify time | `test_m1.py:27-30`, `reference.py` |
| 53 | CHECK | No unpinned git clone | None | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:19-21` |
| 55 | UNCHECK | Not unfair | Systematic spec ambiguity drove 5/6 failures | `entire-report.txt:75-100` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 21, 27, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Root absolute geometry from viewport origin | `test_designed_cases`, `test_random_cases` | **gap** | `instruction.md:3` ambiguous; `reference.py:61` uses origin `(0,0)+box` |
| Child content origin = border TL + border/padding − scroll | `test_designed_cases`, `test_random_cases` | covered | `instruction.md:3`, `reference.py:57-60` |
| Canonical JSON output | `test_output_is_canonical_json` | covered | `instruction.md:1`, `test_m1.py:55-63` |
| Deep chain border/padding/scroll accumulation | `test_designed_cases` case 0 | covered | `reference.py:303-313`, `test_m1.py:75-79` |
| Viewport half-open clip + padding-box ancestors | `test_designed_cases` M2 | covered | `milestone_2/instruction.md`, `reference.py:327-350` |
| Self-clip exclusion | `test_self_clip_and_padding_box` | covered | `test_m2.py`, `reference.py:345-349` |
| Interactive candidates + reading order | `test_reading_order_and_membership` M3 | covered | `milestone_3/instruction.md`, `reference.py:353-370` |
| DVS1 binary frame + custom CRC + deltas | `test_frame_bytes_reconstruct` M4 | covered | `milestone_4/instruction.md`, `reference.py:197-233` |
| M2 canonical JSON serialization | all M2 tests | covered (inherited) | M1 `:1` specifies canonical; M3 `:6` reaffirms |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_1/instruction.md` | Blocker #1, #7, #27, #55 |
| `steps/milestone_1/tests/reference.py` | Blocker #1, spec alignment |
| `steps/milestone_1/tests/test_m1.py` | #27, #28, agent stats cross-check |
| `task.toml` | #45, #46, validation note |
| `environment/Dockerfile` | #14, #15, #20 |
| `entire-report.txt` | Rubric #32–39, agent stats, external adjudication |
| `docs/guidelines/rubrics.md` | Milestone rubric format confirmation |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate viewport-snapshot-engine/
ERROR: number_of_milestones (4) != [[steps]] count (5)  ← false positive: comment line 12 contains "[[steps]]"
WARNING: long_context subtype (N/A — subcategories empty)
WARNING: pinned_dependencies pip line (false positive — uses --require-hashes)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 80.0% (4/5) | One partial failure |
| terminus-gpt5-5 | 0.0% (0/5) | All failed |
| oracle | 100.0% (3/3) | Per export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (field present; rates align) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone Python layout task; report matches folder |
| 1 Instruction | ☑ | Root wording is sole High spec issue |
| 2 Environment | ☑ | Digest-pinned base, hash-locked venv, tmux/asciinema |
| 3 Oracle | ☑ | Static review pass; runtime not executed |
| 4 Verifiers | ☑ | reward.txt, no runtime installs, reference isolation |
| 5 Metadata | ☑ | Milestone layout correct; comment `[[steps]]` trips validator |
| 6 Rubric | ☑ | Milestone format correct; line 497 conflicts with tests |
| 7 Agent evidence | ☑ | Export confirms root-misread pattern |
| 8 Fairness | ☑ | Strong task undermined by one ambiguous sentence |
| 9 Long context | N/A | `subcategories = []` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the four-milestone structure, independent reference tests with randomized trees, and offline Dockerfile are all in great shape. The milestone rubric blocks are formatted correctly and each stays under the point cap. One fix before we can accept: milestone 1 says the root's box top-left "is the viewport origin," and Rubric 1 says to place the root at the viewport origin — many agents read that as forcing absolute `[0,0]`, but your tests (and the reference) expect viewport `(0,0)` to be the parent content origin so the root lands at its own `box[x,y]` (e.g. `[4,6,…]` stays `[4,6,…]`). Please state that explicitly in the instruction and update the matching rubric line. Small housekeeping: reword the `task.toml` comment so it doesn't contain the literal `[[steps]]` token (it trips local validation).

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 1 |
| Metadata Issues | no | — (validator false positive only; optional comment fix) |
| Milestones | no | — (layout correct) |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
| Exposing Hints/Answers | no | — |
| Other | no | — |
