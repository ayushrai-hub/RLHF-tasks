# Terminus Review Report: `routenet-tbench-submission`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Sampler logic, verifier depth, pinned Node/PostgreSQL environment, oracle, and difficulty calibration are strong. Distance/seed rules are now clearly specified in `instruction.md`, `SAMPLER.md`, and `SCHEMA.md`. One High blocker remains: tests require pre-existing `/app/output/negatives.json` and `/app/output/audit.json`, but `instruction.md` frames those artifacts as conditional on PostgreSQL already running and implies the verifier will exercise the sampler—causing capable agents to fix the sampler yet fail `test_canonical_negatives_output_exists`. Platform rubric is correctly formatted for a non-milestone task (flat list, 31 positive pts, 7 negatives).

**Insights (concise):**

- Oracle passes 1.0/1.0; `solve.sh` runs `start-system.sh`, sampler CLI, and audit to create canonical artifacts.
- Worst-model pass rate 0% (GPT-5.5); best 80% (Claude Opus 4.8) — hard tier, not too easy.
- `test_canonical_negatives_output_exists` failed 5/9 agent runs while 16/17 other tests often passed — systematic spec gap, not implementation quality.
- Auto-audit false positives on #14 (hash-pinned `requirements.lock`), #20 (pytest baked in image), and #32–#34 (rubric not parsed from export) — manually cleared.
- Platform rubric uses flat `Agent …, ±N` lines (no `# Rubric 2+` headers) — correct for `number_of_milestones = 0`.
- Low-only items: `/app/tests` path in instruction/rubric; optional `test.sh` startup diagnostic.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Canonical artifact contract is ambiguous: tests require `/app/output/negatives.json` and `/app/output/audit.json` to already exist, but instruction says artifacts are required only "When PostgreSQL is running" and that "Automated verification brings up PostgreSQL and exercises the sampler"—agents who repair the sampler without starting Postgres and writing canonical files fail despite passing 16/17 behavioral tests. | `instruction.md:12,26`; `tests/test_outputs.py:27-28,106-128`; `tests/test.sh:13-19` (starts Postgres, does not create canonical files); `solution/solve.sh:144-147`; `entire-report.txt:51-52,90-114` | Remove conditional framing. Explicitly require: run `bash /app/scripts/start-system.sh`, then `node /app/src/cli/sample.js --seed=17 --k=128 --output=/app/output/negatives.json`, then `node /app/scripts/audit.js --output=/app/output/audit.json` before submission. Alternatively, drop the two canonical-existence tests and rely on verifier-driven sampler invocations only. |

*No other High or Medium blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High: artifact/DB startup contract ambiguous; agents must run `start-system.sh` + sampler + audit (ChatGPT) | **Agree** | `instruction.md:12,26`; `test_outputs.py:106-128`; agent stats `test_canonical_negatives_output_exists: 4/9` in `entire-report.txt:51-52`; 4/6 trials at 16/17 in `entire-report.txt:77-80` |
| 2 | Medium: distance/seed issues fixed (ChatGPT) | **Agree** | `instruction.md:5-8` (`MIN_HOPS=2`, `MAX_HOPS=3`, different seeds → different unordered sets); `environment/docs/SAMPLER.md:32-53`; `environment/docs/SCHEMA.md:64-69` |
| 3 | Low: replace `/app/tests` with "test harness files" (ChatGPT / Harbor review) | **Agree** (Low only) | `instruction.md:26` references `/app/tests`; no `/app/tests` in Dockerfile COPY list; harness mounts at `/tests` per `test.sh:19` |
| 4 | Low: clearer PostgreSQL startup diagnostic in `test.sh` (ChatGPT / Harbor review) | **Agree** (Low only) | `test.sh:13` calls `start-system.sh` under `set -euo pipefail` then `set +e` before pytest — failure path works but message could be clearer |
| 5 | Dockerfile FROM digest-pinned Node base appropriate (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:f3a68cf4…`; Node 22 + PostgreSQL 15 co-hosted — justified custom base |
| 6 | Distance window not in SAMPLER.md/SCHEMA.md (entire-report header lines 1–6) | **Disagree** (stale) | Current `SAMPLER.md:32-39`, `SCHEMA.md:64-69`, `instruction.md:7` all specify 2–3 hop train-subgraph window |
| 7 | Seed rules stricter than spec (entire-report header lines 7–8) | **Disagree** (stale) | `instruction.md:8` requires different seeds → different unordered sets; `test_second_seed_produces_a_different_set` matches |
| 8 | AutoEval build failed (entire-report line 10–12) | **Cannot verify** | No AutoEval artifact in task folder; oracle passes locally |
| 9 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` pass | **Agree** | Cross-checked: all major test behaviors now trace to instruction or `/app/docs/` |
| 10 | Harbor review "READY TO USE" | **Partially agree** | Task quality strong, but canonical-artifact spec gap is a real blocker Harbor review did not flag |
| 11 | Non-milestone task must not use milestone rubric format (user request) | **Agree — passes** | `task.toml:9` `number_of_milestones = 0`; platform rubric `entire-report.txt:316-334` is flat list with no `# Rubric 2+` headers per `docs/guidelines/rubrics.md:66` |
| 12 | Rubric positive cap ≤40 (user / rules) | **Agree — passes** | `./scripts/terminus rubric-points entire-report.txt` → 31/40 |
| 13 | Auto-audit #14 unpinned pip | **Disagree** | `requirements.lock:1-15` uses `package==version` + `--hash=sha256:…`; `Dockerfile:39` `--require-hashes --no-deps` |
| 14 | Auto-audit #20 pytest not in image | **Disagree** | `requirements.lock:1-2` includes `pytest==8.4.1`; installed at image build; `test.sh` has no `pip install` |
| 15 | Auto-audit #32–#34 rubric missing | **Disagree** | Platform rubric in `entire-report.txt:316-334`: 12 Agent lines, 7 negatives (lines 328-334) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Two problem paragraphs plus two requirement sections; ~27 lines, not a spec dump | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Reads as engineering bug report, not synthetic checklist | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown | Two `##` sections with bullets; no tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goals and outputs, not a solve script | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Points to docs for contract; no algorithm walkthrough | `instruction.md:3` |
| 6 | CHECK | No design-doc tables | No input→output mapping tables | `instruction.md` |
| 7 | UNCHECK | Well specified | Canonical artifact production workflow underspecified vs tests | Blocker 1 |
| 8 | CHECK | Interesting | Realistic ML graph-sampling bug with Postgres | `instruction.md:1-3` |
| 9 | UNCHECK | Unique | Cannot verify corpus uniqueness from artifacts | — |
| 10 | CHECK | Absolute paths | All paths use `/app/…` | `instruction.md` |
| 11 | CHECK | No task name in instruction | "routenet" not used as task title string | `instruction.md` |
| 12 | CHECK | No canary in instruction | No canary GUID in instruction | `instruction.md` |
| 13 | CHECK | No runtime web fetch | No curl/wget in env code | `environment/` |
| 14 | CHECK | Pinned pip deps | Hash-locked `requirements.lock` with `==` versions | `requirements.lock`, `Dockerfile:39` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:f3a68cf4…` | `Dockerfile:1` |
| 16 | CHECK | Build context in environment/ | COPY limited to environment subtree | `Dockerfile:45-51` |
| 17 | CHECK | No solution in environment | No solve.sh or golden answers in image | `Dockerfile` COPY list |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose does not alter mounts | No docker-compose.yaml | `task.toml` |
| 20 | CHECK | Verifier deps in image | pytest/psycopg2 in `requirements.lock`, baked at build | `Dockerfile:39`, `test.sh` |
| 21 | CHECK | Oracle passes | `./scripts/terminus oracle` → reward 1.0 | oracle run 2026-07-03 |
| 22 | CHECK | Oracle no internet | `solve.sh` local only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Writes real sampler, runs CLI + audit | `solution/solve.sh:7-147` |
| 24 | CHECK | reward.txt on failure | Writes 0 before pytest, 1 on success | `test.sh:10-25` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `test_outputs.py`, `test.sh` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `test.sh:21-25` |
| 27 | UNCHECK | Tests aligned with instructions | Canonical file tests unconditional; instruction conditional on Postgres | Blocker 1 |
| 28 | CHECK | Tests check correctness | Ground truth from live Postgres BFS | `conftest.py:92-141` |
| 29 | CHECK | Behavior not implementation grep | No source grepping in tests | `test_outputs.py` |
| 30 | CHECK | No brittle string matching | Schema/behavior assertions, not long literals | `test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All 17 `test_*` have docstrings | `test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 7 negatives in platform rubric | `entire-report.txt:328-334` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use valid scores | `entire-report.txt:316-334` |
| 34 | CHECK | Agent-line format | 19 criteria, each `Agent …, ±N` | `entire-report.txt:316-334` |
| 35 | CHECK | Rubric detailed/precise | Task-specific process checks | `entire-report.txt:316-334` |
| 36 | CHECK | Positive language on positives | Negatives use negative phrasing with minus scores | `entire-report.txt:316-334` |
| 37 | CHECK | Rubric no /tests/ refs | References `/app/tests/` (non-existent app path), not harness `/tests/` | `entire-report.txt:328` |
| 38 | CHECK | Rubric no metadata refs | No task.toml or instruction.md mentions | `entire-report.txt:316-334` |
| 39 | CHECK | Rubric no oracle/NOP refs | No oracle/NOP lines | `entire-report.txt:316-334` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No stray parent files | Standard task layout only | task root |
| 42 | CHECK | author fields | `author_name`, `author_email` set | `task.toml:4-5` |
| 43 | CHECK | Other metadata | category, tags, timeouts present | `task.toml` |
| 44 | CHECK | Tags/languages match | ML + JS/SQL + postgres tags fit content | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; worst-model 0% → hard tier | `task.toml:6`, `entire-report.txt:37-39` |
| 46 | UNCHECK | Milestone steps layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ in Dockerfile | `Dockerfile` |
| 51 | CHECK | No accessible ground truth | Tests recompute from DB; snapshot intentionally stale | `environment/data/`, LLMaJ anti_cheat |
| 52 | CHECK | Agent cannot trivially cheat inputs | Dynamic multi-seed/k verification | `test_outputs.py` |
| 53 | CHECK | Git pins | No unpinned git clone | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤ 80% | `entire-report.txt:37-39` |
| 55 | UNCHECK | Not unfair | Artifact catch-22 unfair until instruction fixed | Blocker 1, `entire-report.txt:90-114` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Train-subgraph distance 2–3 hops | `test_graph_distance_constraint`, `test_second_seed_satisfies_all_invariants`, `test_smaller_k_is_consistent`, `test_third_seed_invariants_at_small_cardinality` | covered | `instruction.md:7`; `test_outputs.py:204-216` |
| No leakage from train/val/test splits | `test_no_train_edge_leakage`, `test_no_validation_edge_leakage`, `test_no_test_edge_leakage` | covered | `instruction.md:7`; `test_outputs.py:181-201` |
| `source: "postgres"` | `test_source_label_marks_postgres_as_origin`, `test_canonical_negatives_output_exists` | covered | `instruction.md:17`; `test_outputs.py:106-117,157-161` |
| Seeded PRNG determinism | `test_determinism_repeat_same_seed` | covered | `instruction.md:8`; `test_outputs.py:246-252` |
| Different seeds → different unordered sets | `test_second_seed_produces_a_different_set` | covered | `instruction.md:8`; `test_outputs.py:219-224` |
| JSON schema (seed, k, source, negatives) | `test_sampler_writes_required_schema`, `test_negatives_have_correct_count_and_shape` | covered | `instruction.md:14-18`; `test_outputs.py:131-154` |
| Static audit passes | `test_static_audit_reports_ok`, `test_canonical_audit_output_exists` | covered | `instruction.md:20-22`; `test_outputs.py:122-128,275-284` |
| Canonical `/app/output/negatives.json` exists before verify | `test_canonical_negatives_output_exists` | **gap** | Test unconditional; instruction conditional "When PostgreSQL is running" (`instruction.md:12`) |
| Canonical `/app/output/audit.json` exists before verify | `test_canonical_audit_output_exists` | **gap** | Same conditional framing vs unconditional test |
| Agent must start PostgreSQL | (implicit in rubric only) | **gap** | Rubric line 316/333 in export; not in `instruction.md` |
| k=16, k=32 exercised | `test_smaller_k_is_consistent`, `test_third_seed_invariants_at_small_cardinality` | covered (in dossier via SAMPLER.md) | `SAMPLER.md:55`; `test_outputs.py:255-305` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker 1, #7, #27, #55, spec alignment |
| `tests/test_outputs.py` | Blocker 1, canonical tests, all verifier coverage |
| `tests/test.sh` | Blocker 1, #20, #24 |
| `tests/conftest.py` | #28, Postgres fixture behavior |
| `solution/solve.sh` | #21-23, canonical artifact oracle path |
| `environment/Dockerfile` | #14-15, #20, #50 |
| `environment/requirements.lock` | #14, #20 |
| `environment/docs/SAMPLER.md` | Distance/seed adjudication |
| `environment/docs/SCHEMA.md` | Distance/seed adjudication |
| `task.toml` | #45, milestone N/A, metadata |
| `entire-report.txt` | Agent stats, rubric #32-39, instruction sufficiency |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate routenet-tbench-submission
Summary: 0 error(s), 1 warning(s), 1 info
WARNING: pinned_dependencies — pip install uses --require-hashes (false positive; requirements.lock is hash-pinned)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All runs failed |
| terminus-claude-opus-4-8 | 80.0% (4/5) | One non-artifact failure |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle 1.0 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `routenet-tbench-submission`; regular layout; report applies |
| 1 Instruction | ☑ | One High gap on canonical artifacts; distance/seed now clear |
| 2 Environment | ☑ | Digest-pinned Node+PG; tmux+asciinema; deps baked |
| 3 Oracle | ☑ | Passes 1.0; creates canonical files via start-system + CLI |
| 4 Verifiers | ☑ | 17 behavior tests; reward path correct; no runtime installs |
| 5 Metadata | ☑ | hard/ML/javascript+sql; non-milestone |
| 6 Rubric | ☑ | Flat non-milestone format; 31/+ cap OK; 7 negatives |
| 7 LLMaJ & agents | ☑ | Instruction sufficiency fail aligns with artifact gap |
| 8 Novelty & fairness | ☑ | Unfair until artifact contract fixed (#55) |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the broken snapshot sampler is a believable bug, the Postgres-grounded verifier is thorough, and the distance/seed rules are now spelled out clearly in the instruction and docs. Oracle passes cleanly and the difficulty looks right. One thing to fix before we can accept: the tests expect `/app/output/negatives.json` and `/app/output/audit.json` to already be on disk, but the instruction only says those files are required "when PostgreSQL is running" and that verification will bring up Postgres itself. Several capable runs fixed the sampler and passed almost every test but still failed because they never started Postgres during their session and didn't write the canonical files. Please make it explicit that agents must run `bash /app/scripts/start-system.sh`, then the sampler CLI and audit script to create both files before finishing — or drop the two canonical-existence checks if you prefer the verifier to generate everything.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Milestones | no | N/A (non-milestone; rubric format correct) |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
