# Terminus Review Report: `cronq-submission`

**Generated:** 2026-06-19 (manual re-audit)  
**Disposition:** Accept  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/cronq-submission`

---

## 1. Executive summary

- **Recommendation:** Accept
- **Confidence:** High (artifact + spec-test audit); Medium (local oracle blocked — Docker daemon unavailable)
- **Automated validation:** WARN — 0 errors, 3 warnings (2 false positives on manual re-check)
- **External report match:** **Matches** — `entire-report.txt` describes this Java `cronq` cron-parser debugging task
- **ChatGPT findings:** **Agree** — Accept; no High/Medium/Low issues found on re-audit
- **Checkboxes to CHECK:** 42 items → `1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55`
- **Checkboxes to UNCHECK:** 13 items → `10, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49`

> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.

---

## 2. Main blockers (detailed)

**No blocking issues.** Automated script flagged four failures; manual re-audit overturned three and downgraded one.

### Overturned: #14 — pip dependencies pinned (script false positive)

- **Severity:** N/A (passes)
- **Checkbox:** **CHECK #14**
- **What automated script claimed:** Unpinned `pip install`
- **Manual finding:** `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` are explicitly `==`-pinned.
- **Proof files:** `environment/Dockerfile:20-22`

### Overturned: #45 / #54 — difficulty tier (script bug: used `max()` not `min()`)

- **Severity:** N/A (passes)
- **Checkboxes:** **CHECK #45, #54**
- **What automated script claimed:** Worst-model 100% → trivial/too easy
- **Manual finding:** Agent rates from report: Claude Opus 4.8 **0%** (0/5), GPT-5.5 **100%** (5/5). Worst model = **0%** → **Hard** tier (≤20%). Declared `difficulty = "hard"` in `task.toml` is correct. `scripts/review_checklist.py:167-169` incorrectly uses `max(agent_rates)` for “worst model.”
- **Proof files:** `entire-report.txt:6-7`, `task.toml:8`, `docs/guidelines/difficulty.md:7-12`

### Downgraded (optional polish, not blocking): #10 — relative paths in instruction

- **Severity:** Low
- **Checkbox:** leave **#10 UNCHECKED**
- **What failed:** `./build.sh` (line 8) and unqualified `docs/PROTOCOL.md`, `data/cases/`, `manifest.json` (lines 14–19) are not absolute `/app/...` paths.
- **Proof files:** `instruction.md:8,14,18-19`
- **Why not blocking:** `/app` is established in line 1; paths are unambiguous in context. Validator emits only a warning. Suggested fix: rewrite as `/app/build.sh`, `/app/docs/PROTOCOL.md`, `/app/data/cases/`, `/app/data/manifest.json`.

### Note (Low — optional): instruction does not foreground exit-code debugging

- **Severity:** Low
- **Checkbox:** does not block any item
- **What:** `instruction.md` focuses on wrong fire times; exit codes 2/3 are only in `PROTOCOL.md` §5, not called out in the prompt.
- **Proof files:** `instruction.md:1-15`, `environment/app/docs/PROTOCOL.md:88-94`, `tests/test_outputs.py:268-296`
- **Why not blocking:** Error paths already work in the buggy baseline; tests verify documented protocol behavior, not unstated requirements. External report agrees (`entire-report.txt:154-175`).

---

## 3. Portal checkbox decisions

### CHECK these (pass — tick in portal)

| # | Label | Reason | Proof |
|---|-------|--------|-------|
| 1 | Instruction is concise | ~200 words, 3 short prose blocks; no headers/tables | `instruction.md` |
| 2 | Natural prompt tone | Engineer bug brief (“spitting out wrong fire times”); not synthetic spec voice | `instruction.md:1-5` |
| 3 | No excessive markdown | Plain prose; no `##`/tables/code fences in instruction | `instruction.md` |
| 4 | No step-by-step solve instructions | Build/run example is usage context, not “fix file X then Y” choreography | `instruction.md:7-9` |
| 5 | No hints / solving strategies | Does not name the six bugs or which files to patch | `instruction.md`, `environment/app/docs/TROUBLESHOOTING.md` |
| 6 | No design-doc I/O tables | No mapping tables in instruction (tables in PROTOCOL.md are contract docs) | `instruction.md` |
| 7 | Well specified | Clear deliverable: match `PROTOCOL.md` for all valid expressions; edit `/app/src` only | `instruction.md:11-25` |
| 8 | Interesting | Realistic multi-bug Java cron debugging with protocol contract | task content |
| 9 | Unique | Java cronq CLI with bespoke protocol rules; distinct from typical single-bug tasks | task identity |
| 11 | Task name not in instruction | `cronq-submission` / task slug absent | `instruction.md` |
| 12 | No canary string | None detected | `instruction.md` |
| 13 | No runtime web fetch | `allow_internet = false`; local fixtures/docs only | `task.toml:34`, `environment/` |
| 14 | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:20-22` |
| 15 | Digest-pinned FROM | `eclipse-temurin:21-jdk-jammy@sha256:25d1276...` | `environment/Dockerfile:1` |
| 16 | Environment self-contained | COPY limited to `app/` under `environment/` | `environment/Dockerfile:24` |
| 17 | No ground-truth answers in env | Manifest covers 5/9 cases; 4 hidden; docs are contract not patch map | `environment/app/data/manifest.json`, `tests/test_outputs.py:37-69` |
| 18 | No dangerous Docker ops | No privileged / docker.sock | `environment/Dockerfile` |
| 19 | Compose mount safety | No `docker-compose.yaml` | task root |
| 20 | Verifier deps in image | pytest pre-installed; `test.sh` does not install packages | `environment/Dockerfile:20-22`, `tests/test.sh` |
| 21 | Oracle passes consistently | Report: oracle 100% (3/3); `solve.sh` patches 6 bugs + smoke check (local oracle blocked: Docker daemon down) | `entire-report.txt:11`, `solution/solve.sh:1-120` |
| 22 | Oracle no runtime network | `solve.sh` edits local Java sources + `./build.sh` only | `solution/solve.sh` |
| 23 | Oracle derives via implementation | Six targeted source patches in Matcher/FieldParser/NextCalculator; not echo of test answers | `solution/solve.sh:12-108` |
| 24 | reward.txt canonical block | Seeds 0 upfront; writes 0/1 on build fail and pytest result | `tests/test.sh:4-7,23-24,38-42` |
| 25 | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | Binary rewards only | 0 or 1 in `reward.txt` | `tests/test.sh:38-42` |
| 27 | Tests aligned with instructions | Every assertion traces to `PROTOCOL.md` §1–5 (designated source of truth in instruction) | matrix § below |
| 28 | Tests check correctness | Exact fire-time values vs hand-computed expectations; not format-only | `tests/test_outputs.py` |
| 29 | Behavior tests not implementation grep | Shells out to `java -jar /app/cronq.jar`; no source-file reads | `tests/test_outputs.py:95-102` |
| 30 | No brittle matching where flexible would work | Exact timestamps required for cron scheduling — appropriate | `tests/test_outputs.py` |
| 31 | Informative docstrings | All 25 `test_*` functions documented | `tests/test_outputs.py` |
| 40 | Required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | Clean parent directory | No stray jobs/README at task root | task root |
| 42 | author fields present | `author_name`, `author_email` in task.toml | `task.toml:6-7` |
| 43 | Other metadata present | category, subcategories, timeouts, environment block complete | `task.toml` |
| 44 | Tags/languages/category match | `debugging`, `java`, `tool_specific`, cron tags fit content | `task.toml:8-16` |
| 45 | Difficulty matches agent rates | Worst model Claude 0% → Hard; matches `difficulty = "hard"` | `entire-report.txt:6-7`, `task.toml:8` |
| 50 | Tests not in image | Dockerfile COPYs only `app/` | `environment/Dockerfile:24` |
| 51 | Solution not accessible in env | No `solution/` or `tests/` COPY | `environment/Dockerfile` |
| 52 | Agent cannot trivially cheat | SHA-256 guards on `/app/data/` and `/app/docs/`; 6 verifier-only expressions | `tests/test_outputs.py:26-31,299-379` |
| 53 | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | Not too easy | Worst-model 0% ≪ 80% rejection threshold | `entire-report.txt:6-7` |
| 55 | Not too hard/unfair | Protocol complete; 3/5 Claude runs reached 21–22/25; failures are implementation misses + 2 timeouts, not missing spec | `entire-report.txt:56-93` |

### UNCHECK these (fail, unverified, or N/A — leave blank in portal)

| # | Status | Label | Reason | Proof |
|---|--------|-------|--------|-------|
| 10 | fail | All paths absolute | `./build.sh`, `docs/PROTOCOL.md`, `data/cases/` not `/app/...` prefixed | `instruction.md:8,14,18-19` |
| 32 | na | Rubric ≥3 negatives | No `rubric.txt` in task folder (portal UI entry) | task root |
| 33 | na | Rubric score set | [N/A] | — |
| 34 | na | Rubric format | [N/A] | — |
| 35 | na | Rubric detailed | [N/A] | — |
| 36 | na | Rubric positive language | [N/A] | — |
| 37 | na | Rubric no /tests/ refs | [N/A] | — |
| 38 | na | Rubric no instruction.md refs | [N/A] | — |
| 39 | na | Rubric no oracle/NOP | [N/A] | — |
| 46 | na | Milestone steps/ layout | `number_of_milestones = 0` | `task.toml:12` |
| 47 | na | solveN.sh per milestone | [N/A] | — |
| 48 | na | test_mN.py per milestone | [N/A] | — |
| 49 | na | Milestone test scoping | [N/A] | — |

### Quick copy-paste

**CHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55

**UNCHECK:** 10, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49

---

## 4. Proof file index

| File | Related checkboxes |
|------|-------------------|
| `instruction.md` | #1–9, #10, #11, #27 |
| `task.toml` | #42–45, #46 |
| `environment/Dockerfile` | #13–20, #50, #53 |
| `environment/app/docs/PROTOCOL.md` | #17, #27 |
| `environment/app/data/manifest.json` | #17, #51, #52 |
| `solution/solve.sh` | #21–23 |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, #52 |
| `entire-report.txt` | #21, #45, #54, #55 |

---

## 5. Validation output (re-audit)

```
./scripts/terminus validate cronq-submission/
Summary: 0 error(s), 3 warning(s), 2 info
```

| Warning | Manual verdict |
|---------|----------------|
| `long_context` subtype | **False positive** — `subcategories = ["tool_specific"]` only; docs ~8 KB total, not long-context | `task.toml:11` |
| `pinned_dependencies` pip | **False positive** — pytest packages are `==`-pinned | `environment/Dockerfile:20-22` |
| `check_task_absolute_path` | **Valid Low** — `./build.sh` and relative doc paths; see blocker #10 | `instruction.md:8,14` |

Oracle: **not executed locally** (Docker daemon unavailable). External report: oracle 100% (3/3). Static review of `solve.sh` confirms six independent source patches + rebuild + smoke check.

---

## 6. Agent performance (from report)

| Model | Pass rate | Runs |
|-------|-----------|------|
| terminus-claude-opus-4-8 | 0.0% | 0/5 |
| terminus-gpt5-5 | 100.0% | 5/5 |
| oracle | 100.0% | 3/3 |
| nop | 0.0% | 0/1 |

- **Worst-model rate:** 0% → tier **Hard** (matches `task.toml`)
- **Timeout gate:** 2/10 real-agent runs (<5) — pass
- **Solvable:** yes — all 25 unit tests passed on ≥1 agent run
- **Systematic failure:** 3/5 Claude runs fixed 4–6 bugs but missed `NextCalculator.advance()` minute-floor on hour jump (`tests/test_outputs.py:354-364`); 2/5 timed out with no edits. Agent errors, not spec gaps.

---

## 7. Audit log

- [x] Phase 0 — Task identity: `cronq-submission` matches report (`entire-report.txt:47` cronq Java task); regular layout; `debugging` / `tool_specific` / `hard`
- [x] Phase 1 — `instruction.md`: concise natural prompt; PROTOCOL.md as contract; relative-path note (#10)
- [x] Phase 2 — `environment/Dockerfile`: digest-pinned JDK 21 base (non-canonical but justified); tmux+asciinema; no tests/solution COPY; pip pinned
- [x] Phase 3 — `solution/solve.sh`: six deterministic patches; no hardcoded JSON answers
- [x] Phase 4 — `tests/test.sh` + `test_outputs.py`: reward block; 25 behavior tests with docstrings; SHA-256 anti-cheat; 6 off-grid expressions
- [x] Phase 5 — `task.toml`: metadata complete; `allow_internet = false`
- [x] Phase 6 — Rubric: no file in repo; sample rubric lines in report (`entire-report.txt:267-279`) are portal-only — N/A for file checks
- [x] Phase 7 — External report + ChatGPT adjudicated with file evidence
- [x] Phase 8 — Novelty/fairness: 6 independent bugs; manifest partial; verifier-only cases close cheating paths
- [x] Phase 9 — Long context: N/A (`tool_specific` only)

### Spec ↔ test alignment matrix (selected)

| Requirement (instruction / PROTOCOL.md) | Test(s) | Status |
|----------------------------------------|---------|--------|
| Five-field cron syntax | `test_output_shape`, error tests | covered |
| DOM/DOW OR when both restricted (§2) | `test_friday_thirteenth_is_a_union`, `test_dom_dow_union_first_or_wednesday` | covered |
| Strictly after `--from` (§3) | `test_daily_midnight_skips_the_start_minute`, `test_strictly_after_excludes_exact_start_offgrid` | covered |
| Step anchor `v/k` at v (§1) | `test_stepped_hours_start_at_the_base`, `test_single_value_step_anchors_at_value_offgrid` | covered |
| Range step `a-b/k` capped at b (§1) | `test_range_step_respects_range_ceiling_offgrid` | covered |
| SUN=0 DOW mapping (§1) | `test_sunday_by_name_offgrid` | covered |
| JSON output schema (§4) | `test_output_shape`, `test_times_are_iso_utc_on_the_minute` | covered |
| Exit codes 2/3 (§5) | `test_bad_expression_exits_2`, `test_unsatisfiable_expression_exits_3` | covered |
| Leave `/app/data` and `/app/docs` unchanged | `test_data_dir_unchanged`, `test_docs_dir_unchanged` | covered |
| Hour-jump minute lands on field value (implicit in correct output) | `test_hour_jump_resets_minute_to_field_floor_offgrid` | covered (output derivable from §1+§3) |

---

## External findings adjudication

### Claim: ChatGPT Accept — no severity issues
- **Source:** User message / ChatGPT assessment
- **Verdict:** Agree
- **Evidence:** Manual audit found no High/Medium blockers; difficulty tier correct at Hard
- **Severity:** —
- **Action:** none

### Claim: LLMaJ `behavior_in_tests` PASS
- **Source:** `entire-report.txt:99`
- **Verdict:** Agree
- **Evidence:** All 25 tests map to PROTOCOL.md §1–5; matrix above
- **Severity:** —
- **Action:** none

### Claim: LLMaJ `behavior_in_task_description` PASS
- **Source:** `entire-report.txt:98`
- **Verdict:** Partially agree
- **Evidence:** Instruction designates PROTOCOL.md as source of truth (`instruction.md:13-15`); exit codes in §5 not foregrounded in instruction — Low only
- **Severity:** Low
- **Action:** optional instruction sentence mentioning exit-code contract

### Claim: Instruction sufficiency FAIL — hour-jump minute-floor not explicit
- **Source:** `entire-report.txt:46,72-75,93`
- **Verdict:** Partially agree
- **Evidence:** PROTOCOL.md does not spell out `advance()` minute-floor algorithm, but expected output for `45 6 * * *` is derivable from field semantics; 3 agents missed implementation bug, not spec misunderstanding alone
- **Severity:** Low
- **Action:** optional PROTOCOL.md example; not blocking

### Claim: Non-canonical Docker base image
- **Source:** `entire-report.txt:133-152`
- **Verdict:** Agree (non-blocking)
- **Evidence:** Java JDK 21 requires `eclipse-temurin`; digest-pinned; canonical list is Python/Node-oriented
- **Severity:** Low
- **Action:** propose canonical Java base; not blocking Accept

### Claim: Difficulty HARD
- **Source:** `entire-report.txt:1`
- **Verdict:** Agree
- **Evidence:** Claude 0% worst model ≤20%
- **Severity:** —
- **Action:** none

### Claim: Automated script Revise (#10, #14, #45, #54)
- **Source:** Initial `review-report.md` from `./scripts/terminus review`
- **Verdict:** Disagree (3/4 overturned)
- **Evidence:** #14 pinned; #45/#54 script uses `max()` not `min()` for worst model; #10 Low only
- **Severity:** —
- **Action:** fix `review_checklist.py` worst-model calculation

---

## 8. Reviewer note (copy-paste to portal)

Accepted. The instruction is a clear Java cron debugging brief with `PROTOCOL.md` as the normative contract; tests verify end-to-end CLI behavior across nine bundled cases plus six off-grid expressions, with SHA-256 guards on data and docs. The Dockerfile is digest-pinned, verifier deps are baked in, and tests/solution are not copied into the image. Oracle passes per platform report (3/3); worst-model pass rate is 0% (Claude Opus 4.8), matching declared Hard difficulty. Optional polish: use absolute `/app/...` paths throughout `instruction.md`.

---

_Report enriched after manual audit per `prompt.md`. Automated baseline from `./scripts/terminus review cronq-submission/ --report entire-report.txt`._
