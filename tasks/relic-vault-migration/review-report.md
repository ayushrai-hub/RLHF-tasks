# Terminus Review Report: relic-vault-migration

**Generated:** 2026-06-29  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/relic-vault-migration`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (1 false-positive error, 22 warnings) |
| **Oracle** | pass (report: 100%, 3/3 runs — not re-run locally) |
| **CHECK count** | 52 |
| **UNCHECK count** | 3 |

**Error categories (internal):** Rubric

**Decision (concise):** Task artifacts are strong: milestone layout, digest-pinned Dockerfile with hash-locked verifier deps, independent reference verifiers, synthetic anti-hardcode archives, and hard agent calibration (0% GPT-5.5 / 60% Opus 4.8). The only real blocker is the **platform rubric** — all three milestone blocks have zero negative penalties and every criterion line omits the required `Agent` prefix. The `_id` numeric-sort concern from the submission export is **not** a spec gap. Milestone rubric headers (`# Rubric 1–3`) are correct for this 3-milestone task.

**Insights (concise):**

- Platform rubric totals are in range (16 / 19 / 20 positive pts per block; 55 total) but has **0 negatives** and **0 `Agent …, ±N` lines**.
- Appendix I + milestone-1 instruction both require ascending primary-key sort; `_id` → `"str"` is dtype-only — numeric sort is intended difficulty, not contradiction.
- `validate` error `number_of_milestones (3) != [[steps]] count (4)` is a **false positive**: `task.toml:12` comment text contains `[[steps]]`, inflating the count; only 3 real `[[steps]]` blocks exist.
- Automated FAILs on #14 (pip), #20 (pytest in image), #31 (docstrings) are **false positives** on manual re-audit.
- Chronicle is ~224 KB (~50k+ doc tokens); long_context subcategory is satisfied.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32 | Platform rubric has **0 negative penalty criteria** (need ≥3 total) | `entire-report.txt:376–405` — 28 `+N` lines, no `, -N` lines; Rubric 1/2/3 each have 0 negatives | Add ≥3 distinct negatives on the platform rubric (e.g. lexicographic `_id` sort, hardcoded archive values, broken pack bytes, transcript shortcuts, graded-test tampering). Include relevant negatives in **each** milestone block. |
| 2 | High | Rubric | #34 | Rubric lines omit required `Agent` prefix / `Agent …, ±N` format | `entire-report.txt:377–405` — lines like `/app/out/schema_report.json exists…, +2` (0 lines match `^Agent .+, ±N`) | Rewrite every criterion as `Agent <trace-evidenced behavior>, ±N` per platform rubric CI format. |

*No other High blockers found in task artifacts.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Platform rubrics need negative penalties in all three milestone blocks (ChatGPT High) | **Agree** | `entire-report.txt:376–405` — Rubric 1: +16/0−, Rubric 2: +19/0−, Rubric 3: +20/0− |
| 2 | `_id` lexicographic sort is not a blocker; Appendix I primary-key sort vs dtype rule is consistent (ChatGPT Medium) | **Agree** | `chronicle.md:1031–1033` ascending by primary key; `chronicle.md:1017–1020` `_id` dtype `"str"` only; `steps/milestone_1/instruction.md:75–76` same; `relic_ref.py:221` `sorted(rows, key=lambda r: r[pkey])` on coerced ints |
| 3 | Optional clarity: one sentence that digit `_id` values sort numerically (ChatGPT Low) | **Partially agree** | Spec is discoverable from Appendix I Rule I.4 step 2 + instruction fingerprint steps; optional sentence would reduce agent regressions but not required for accept |
| 4 | Task Instruction Sufficiency FAIL — systematic `_id` sort ambiguity (`entire-report.txt` agent analysis) | **Disagree** | Same as #2; LLMaJ `behavior_in_task_description: pass` (`entire-report.txt:103`); 2/6 trials initially produced correct fingerprint then regressed (`entire-report.txt:71`) |
| 5 | Dockerfile digest-pinned canonical base (ChatGPT) | **Agree** | `environment/Dockerfile:4` `@sha256:01f42367…` |
| 6 | Harbor review: production-ready, no significant weaknesses (`entire-report.txt:221–232`) | **Agree** (artifacts) with rubric caveat | Tests/oracle/env align; rubric platform-side gap remains |
| 7 | `number_of_milestones` mismatch validation error | **Disagree** (not a real defect) | `task.toml:12` comment contains literal `[[steps]]`; actual blocks at `:38`, `:50`, `:62` only |
| 8 | Non-milestone task incorrectly using milestone rubric format (user query) | **Disagree** — N/A | `task.toml:13` `number_of_milestones = 3`; `steps/milestone_{1,2,3}/` layout; `# Rubric 1/2/3` headers are **correct** for milestone tasks |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | M1 instruction ~655 words with JSON schema block — exceeds strict 3-paragraph cap; acceptable long_context milestone opener but strict item fails | `steps/milestone_1/instruction.md` (wc: 655 words) |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Human engineer tone; problem-first framing | `steps/milestone_1/instruction.md:1–12` |
| 3 | CHECK | No excessive markdown formatting | Headers/code blocks proportional to schema spec; not spec-dump bloat | milestone instruction files |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Only deliverable commands (`schema`/`pack`/`relicvault --replay`); no dev walkthrough | `steps/milestone_3/instruction.md:13` "Then run" is output command, not HOW |
| 5 | CHECK | No hints or solving strategies | Counter-intuitive rule *warnings* point to appendices without giving answers | `steps/milestone_1/instruction.md:60–69` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No I/O mapping tables | — |
| 7 | CHECK | Instruction is well specified | Paths, commands, output schemas, appendix references explicit | milestone instruction files |
| 8 | CHECK | Instruction is interesting | Polars ETL + binary pack + C engine replay chain | task design |
| 9 | CHECK | Instruction is unique | Roguelike vault migration with chronicle-appendix spec | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/archive`, `/app/out/…`, etc. | milestone instruction files |
| 11 | CHECK | Task name does not appear in instruction.md | Uses "Relic Vault" product name, not folder slug | `steps/milestone_1/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web | Offline vendored wheels; no runtime fetch | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.lock` pins all packages with `==` + SHA-256 hashes; `--require-hashes` | `environment/requirements.lock:26–35`, `Dockerfile:33–35` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:4` |
| 16 | CHECK | Environment does not use context from outside environment directory | `COPY app/` only | `environment/Dockerfile:38` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Chronicle has rules/contracts, not precomputed outputs | `environment/app/docs/chronicle.md` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest/polars in `requirements.lock`, installed at build; test.sh only runs pytest | `environment/requirements.lock`, `steps/milestone_1/tests/test.sh:9–13` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3) | `entire-report.txt:30` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve scripts write code locally | `steps/milestone_1/solution/solve1.sh` |
| 23 | CHECK | Oracle is reflective of instruction | solve1.sh builds full migrate.py from chronicle rules | `steps/milestone_1/solution/solve1.sh:7–18` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block | `steps/milestone_1/tests/test.sh:14–19` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent | No `/oracle` branching | milestone `test.sh` files |
| 26 | CHECK | Verifier applies binary rewards only | `echo 0` / `echo 1` | `steps/milestone_1/tests/test.sh:15–18` |
| 27 | CHECK | All tests are aligned with instructions | Every tested behavior traced to instruction + appendices | section 5 below |
| 28 | CHECK | Tests check for correctness, not just format | Byte-exact + SHA-256 vs independent `relic_ref.py`; synthetic archives | `steps/milestone_1/tests/test_m1.py:54–68` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grepping | milestone test files |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Byte-exact required by spec (pack, JSON, transcript) | appendices + tests |
| 31 | CHECK | Tests have informative names or docstrings | All 19 `test_*` methods have docstrings (validator misses `-> None:` hint syntax) | `steps/milestone_1/tests/test_m1.py:43–44` et al. |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | **0 negatives** on platform rubric | `entire-report.txt:376–405` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Only +1,+2,+3 used | `entire-report.txt:376–405` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | **0 `Agent` lines** | `entire-report.txt:377–405` |
| 35 | CHECK | Rubric criteria are detailed and precise; positive cap ≤40/block | 16/19/20 pts per block; task-specific criteria | `entire-report.txt:376–405` |
| 36 | CHECK | Rubric criteria use positive language | All lines describe desired behaviors with `+N` | `entire-report.txt:376–405` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No `/tests/` or pytest refs | `entire-report.txt:376–405` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No `task.toml` / `instruction.md` refs | `entire-report.txt:376–405` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:376–405` |
| 40 | CHECK | All required files present | Milestone layout complete | `task.toml`, `steps/`, `environment/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | — |
| 42 | CHECK | author_name and author_email present | `task.toml:6–7` | `task.toml` |
| 43 | CHECK | All other required metadata fields present | category, difficulty, timeouts, steps | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | games/long_context/python+c/polars/C engine | `task.toml:8–21` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; platform HARD; worst-model 0% | `task.toml:8`, `entire-report.txt:20–26` |
| 46 | CHECK | steps/ layout present | 3 milestones under `steps/` | `relic-vault-migration/steps/` |
| 47 | CHECK | Each milestone has solveN.sh | solve1/2/3.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | Each milestone has test_mN.py | test_m1/m2/m3.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Each milestone test file scoped to that milestone | M1 schema only; M2 pack+consulted; M3 engine | milestone test files |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in environment | No solution/tests in image | `environment/Dockerfile:38` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Synthetic archives + reference recompute | `test_m1.py:79–81`, `test_m2.py:103–105` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 0% (GPT-5.5) | `entire-report.txt:25–26` |
| 55 | CHECK | Task is not too hard or unfair | Rules in shipped chronicle appendices; _id sort discoverable | `chronicle.md:996–1049`, `instruction.md:71–83` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 32, 34 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: `schema_report.json` with 4 table keys | `test_report_exists`, `test_report_is_valid_json_object` | covered | `test_m1.py:43–52` |
| M1: Appendix I normalization (snake_case, dtypes, hazard `^` only) | `test_per_table_fields_and_fingerprints` | covered | `test_m1.py:54–68`, `relic_ref.py` |
| M1: SHA-256 fingerprint ascending primary key, PK omitted from hash | `test_per_table_fields_and_fingerprints` | covered | `chronicle.md:1030–1041`, `relic_ref.py:219–221` |
| M1: canonical JSON serialization | `test_report_bytes_are_canonical` | covered | `test_m1.py:70–77` |
| M1: data-driven (no hardcode) | `test_harness_on_synthetic_archive` | covered | `test_m1.py:79+` |
| M2: `vault.pack` RVP1/RVPE, chamber order/stats | `test_pack_header_and_footer`, `test_chambers_ordered_by_depth_with_derived_stats` | covered | `test_m2.py:55–77` |
| M2: byte-exact pack + consulted.json (Appendix V scope) | `test_pack_bytes_are_canonical`, `test_consulted_manifest_is_canonical` | covered | `test_m2.py:79–101` |
| M2: synthetic anti-hardcode | `test_harness_on_synthetic_archive` | covered | `test_m2.py:103+` |
| M3: real C ELF engine (>50 lines) | `test_engine_is_real_c` | covered | `test_m3.py:71–83` |
| M3: headline transcript byte-exact (Appendix IV) | `test_headline_transcript_matches_reference` | covered | `test_m3.py:88–96` |
| M3: ALIVE + DOWNED synthetic runs | `test_engine_on_synthetic_alive_run`, `test_engine_on_synthetic_downed_run` | covered | `test_m3.py:98–110` |
| M2/M3: prior milestone artifacts persist | `test_milestone_1_artifact_persists`, `test_earlier_artifacts_persist` | covered | `test_m2.py:45`, `test_m3.py:67` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `entire-report.txt` | Rubric (#32–39), agent stats (#45, #54), external adjudication |
| `task.toml` | Milestone metadata (#46–49), difficulty (#45) |
| `environment/Dockerfile` | #14–#16, #20, #50 |
| `environment/requirements.lock` | #14 pinned deps |
| `environment/app/docs/chronicle.md` | Long context, Appendix I–V rules, _id sort adjudication |
| `steps/milestone_1/instruction.md` | Fingerprint spec, instruction length (#1) |
| `steps/milestone_*/tests/test_m*.py` | #27–#31, spec alignment |
| `steps/milestone_*/tests/relic_ref.py` | Reference sort behavior |
| `steps/milestone_*/tests/test.sh` | #24–#26 |
| `steps/milestone_*/solution/solveN.sh` | #22–#23 |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml [task.toml]: number_of_milestones (3) != [[steps]] count (4)  [FALSE POSITIVE — comment on line 12]
WARNING: tags 7 entries; test docstring regex false positives; pip install line pattern (hash-locked lockfile OK)
Summary: 1 error(s), 22 warning(s) — no actionable artifact defects from validate
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | M1 fingerprint/sort failures dominate |
| terminus-claude-opus-4-8 | 60.0% (3/5) | M2/M3 near-perfect when M1 passes |
| oracle | 100.0% (3/3) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | HARD |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 3-milestone `games` / `long_context` / `tool_specific` task; report matches folder |
| 1 Instruction | ☑ | Per-milestone instructions; appendix-delegated spec intentional |
| 2 Environment | ☑ | Digest-pinned, offline wheels, tmux/asciinema, build-essential for C |
| 3 Oracle | ☑ | Derives via migrate.py + C engine; report 100% |
| 4 Verifiers | ☑ | Reference impl + synthetic archives; reward canonical |
| 5 Metadata | ☑ | 3 steps, solveN.sh, test_mN.py all present |
| 6 Rubric | ☑ | **Blockers confirmed** — 0 negatives, wrong line format |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL on _id rebutted; quality checks pass |
| 8 Novelty & fairness | ☑ | Anti-cheat strong; no cheating paths found |
| 9 Long context | ☑ | ~224 KB chronicle; appendices authoritative |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the chronicle-driven spec, byte-exact reference checks, synthetic anti-hardcoding archives, and C engine replay tests are all in great shape, and the difficulty calibration looks right. The one thing to fix before accept is the platform rubric: all three milestone blocks currently have only positive criteria and the lines don't use the required `Agent …, ±N` format. Please add at least three distinct negative penalties (spread across the milestone blocks — e.g. lexicographic `_id` sorting, hardcoded shipped-archive values, broken pack bytes, or transcript shortcuts) and rewrite each line to start with `Agent`. I don't think the `_id` sort issue is a spec problem — Appendix I's ascending primary-key rule is clear enough.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1, 2 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
