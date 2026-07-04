# Terminus Review Report: `atlasbench-mlflow-governance.`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 44 |
| **UNCHECK count** | 11 |

**Error categories (internal):** Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Go governance-replay task with excellent verifier depth, anti-cheat design, and appropriate difficulty (20–40% pass). Two real blockers: (1) `evidence_chain_digest` instruction text says “all non-digest fields” (includes `action_id`) but verifier/oracle exclude `action_id`, causing systematic near-miss failures; (2) platform rubric uses five `# Rubric N` milestone blocks on a non-milestone task (`number_of_milestones = 0`). Fix digest spec first, then flatten rubric.

**Insights (concise):**

- ChatGPT’s `evidence_chain_digest` claim is **confirmed** with line-level proof in instruction, verifier, and oracle.
- ChatGPT’s rubric-format claim is **confirmed** — `task.toml` has `number_of_milestones = 0` but export has `# Rubric 1`–`# Rubric 5`.
- Agent stats (3/10 on `test_evidence_chain_digest_matches_policy_actions`, 3/10 on lineage fixture) match the digest mismatch root cause.
- LLMaJ `behavior_in_task_description: pass` is **overstated** for digest field inclusion — human adjudication wins.
- Missing error-exit tests and TOML key-order tests are **Low** gaps only — not revision blockers.
- Instruction length/markdown heaviness is justified for schema/digest-heavy long_context task — not listed as blockers.
- Oracle not run locally (Docker unavailable); external report shows 100% (3/3).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27 | `evidence_chain_digest` spec contradicts verifier: instruction says append “all non-digest fields in table column order” (includes `action_id`); verifier hashes only 9 columns excluding `action_id`. Agents following the written spec fail digest tests. | `instruction.md:473` — “all non-digest fields in table column order”; `tests/verifier_helpers.py:135-136` — `SELECT source_file, profile_id, rule_id, target_path, old_value, new_value, exception_id, status, reason_code` (no `action_id`); `solution/engine.go:1926` — oracle also excludes `action_id`; agent stats: `test_evidence_chain_digest_matches_policy_actions` 3/10, `test_lineage_retention_quarantine_and_escaped_ids` 3/10 | Clarify in `instruction.md` that `action_id` is **excluded** from the evidence-chain payload (hash columns `source_file` through `reason_code` only, ordered by `action_id`). |
| 2 | High | Rubric | #34 | Non-milestone task rubric uses five milestone-style `# Rubric N` blocks; Edition 2 requires flat `Agent …, ±N` list for `number_of_milestones = 0`. | `task.toml:10` — `number_of_milestones = 0`; `entire-report.txt:364-409` — `# Rubric 1` … `# Rubric 5`; `docs/guidelines/rubrics.md:64` — “Non-milestone: flat … list (`# Rubric 1` optional; no `# Rubric 2+`)”; `docs/guidelines/submission-export-format.md:63-66` | Merge platform rubric into one flat `Agent …, ±N` list (optional single `# Rubric 1` header only). |

*No other High/Medium revision blockers identified.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `evidence_chain_digest` instruction/verifier mismatch on `action_id` inclusion (ChatGPT / entire-report instruction sufficiency) | **Agree** | `instruction.md:473`; `tests/verifier_helpers.py:131-149`; `solution/engine.go:1919-1930`; 6/7 agent trials failed both digest tests per `entire-report.txt:70-75` |
| 2 | Platform rubric has five `# Rubric N` blocks on non-milestone task (ChatGPT) | **Agree** | `task.toml:10`; `entire-report.txt:364-409`; `docs/guidelines/rubrics.md:64` |
| 3 | Missing error-exit and TOML key-order tests (ChatGPT Low / test-quality review) | **Agree (Low only)** | `instruction.md:18` requires non-zero exit on invalid inputs; no matching test in `tests/test_outputs.py` or `tests/test_verifier.py`; test-quality review `entire-report.txt:297-357` |
| 4 | Instruction is extremely detailed / covers all tested behavior (LLMaJ `behavior_in_task_description`) | **Partially agree** | Broad coverage confirmed, but digest field list at `instruction.md:473` is wrong vs verifier |
| 5 | Task READY TO USE / ACCEPT (Harbor review + test-quality review) | **Disagree on accept** | Digest spec gap is material; rubric format violates non-milestone rules |
| 6 | Solution stub leaks architecture (Harbor review warning) | **Partially agree (not blocker)** | `environment/atlas-harden/engine.go` is broken stub (~350 lines); acceptable fix/extend pattern |
| 7 | Non-canonical base image (Harbor review warning) | **Disagree as blocker** | `environment/Dockerfile:1` digest-pinned `golang:1.24-bookworm`; acceptable for Go task |
| 8 | Test functions lack docstrings (Harbor suggestion) | **Agree (not blocker)** | 16 functions in `tests/test_outputs.py` lack docstrings; `tests/test_verifier.py` module has docstring |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~3007 words / 509 lines — exceeds literal concise limit (justified for schema task but fails checkbox) | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Opens with operational problem statement; engineering tone | `instruction.md:1-6` |
| 3 | UNCHECK | No excessive markdown formatting | 8 `##` and 19 `###` headers plus SQL/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Build/run block is required CLI contract, not algorithm walkthrough | `instruction.md:7-16` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Policy semantics specified; no solve script | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No markdown pipe tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Full schemas, digest formulas, rule IDs, paths | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic MLflow-style governance replay | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct dossier+SQLite evidence replay design | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | Title uses “AtlasBench” not folder slug | `instruction.md:1` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | `pytest==8.4.1`, `pyyaml==6.0.2`, etc. | `environment/Dockerfile:25-28` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY limited to `atlas-harden/`, `data/` | `environment/Dockerfile:33-34` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Stub is incomplete; no solution copied | `environment/atlas-harden/engine.go` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:25-28`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not run locally (Docker unavailable); not independently verified this session | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` copies engine + go build | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | ~2000-line `engine.go` derives outputs | `solution/engine.go` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:11-23` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 reward pattern | `tests/test.sh` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | `evidence_chain_digest` verifier excludes `action_id` but instruction includes it in “non-digest fields” | Blocker 1 proof |
| 28 | CHECK | Tests check for correctness, not just format | Independent digest recomputation, policy outcomes, fixtures | `tests/test_outputs.py`, `tests/test_verifier.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | CLI + DB output assertions only | `tests/` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | URI string asserts match specified redaction outputs | `tests/test_verifier.py:97-102` |
| 31 | UNCHECK | Tests have informative names or docstrings | 16 functions in `test_outputs.py` lack docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 5 negative lines in platform rubric | `entire-report.txt:370-409` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | All scores valid | `entire-report.txt:364-409` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | Lines valid, but non-milestone task must not use `# Rubric 2+` headers | Blocker 2 proof |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific policy/digest/SQLite criteria | `entire-report.txt:364-409` |
| 36 | UNCHECK | Rubric criteria use positive language (not Agent does not do X, +1) | Contains “Agent fails to parse…”, “Agent omits…” with negative scores | `entire-report.txt:379,391,409` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:364-409` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:364-409` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:364-409` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean layout | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | go, security, long_context, db_interaction, mlflow tags match | `task.toml:8-13` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 20%, worst-model 40% | `entire-report.txt:22-24`, `docs/guidelines/difficulty.md` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — not a milestone task | `task.toml:10` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:10` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile) | No tests COPY | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | Solution at `/solution` only at harness time | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Verifier fixtures use novel IDs; dynamic mutation test | `tests/test_verifier.py`, `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 40% | `entire-report.txt:22-24` |
| 55 | CHECK | Task is not too hard or unfair | Failures trace to digest spec ambiguity, not env/tooling (except 1 timeout trial) | `entire-report.txt:59-96` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 32, 33, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 3, 21, 27, 31, 34, 36, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| `evidence_chain_digest` field inclusion | `test_evidence_chain_digest_matches_policy_actions`, `test_lineage_retention_quarantine_and_escaped_ids` | **gap** | `instruction.md:473` vs `tests/verifier_helpers.py:135-136` |
| `value_digest` formula | `test_policy_action_value_digests` | covered | `instruction.md:381-385`, `tests/verifier_helpers.py:126-128` |
| Five policy rules AR-001–LG-005 | multiple policy outcome tests | covered | `tests/test_outputs.py`, `tests/test_verifier.py` |
| SQLite schema (5 tables) | `test_evidence_sqlite_schema_contract` | covered | `instruction.md:346-463`, `tests/test_outputs.py` |
| URI redaction matrix | `test_uri_matrix_redaction_variants`, tracking URI test | covered | `tests/test_verifier.py:86-115` |
| Non-zero exit on invalid inputs | — | gap (Low) | `instruction.md:18`; no negative CLI test |
| TOML deterministic key order | idempotency test only (implicit) | gap (Low) | `instruction.md:338`; test-quality review |
| Idempotent byte-identical reruns | `test_idempotent_second_run_produces_identical_evidence_and_outputs` | covered | `tests/test_outputs.py` |
| Stale output file removal | `test_stale_output_file_removed` | covered | `tests/test_outputs.py` |
| Hidden verifier fixtures | `test_verifier.py` suite | covered | `instruction.md:489-507` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blocker 1, #27, spec alignment |
| `tests/verifier_helpers.py` | Blocker 1, digest tests |
| `tests/test_outputs.py` | #31, spec alignment |
| `tests/test_verifier.py` | Blocker 1, fixture tests |
| `solution/engine.go` | Blocker 1 (oracle digest), #23 |
| `task.toml` | Blocker 2, #44, #45, #46-49 N/A |
| `entire-report.txt` | Blocker 2, agent stats, rubric, adjudication |
| `environment/Dockerfile` | #14-20, #50 |
| `tests/test.sh` | #24-26 |
| `docs/guidelines/rubrics.md` | Blocker 2 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate atlasbench-mlflow-governance.
Summary: 0 error(s), 18 warning(s), 2 info
Task type detected: regular
```

Warnings are docstring gaps and `.dockerignore` info — not blockers.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 20.0% (1/5) | 1 timeout |
| terminus-gpt5-5 | 40.0% (2/5) | |
| oracle | 100.0% (3/3) | per submission export |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model ≤20% supports hard) |

Digest tests: `test_evidence_chain_digest_matches_policy_actions` 3/10; `test_lineage_retention_quarantine_and_escaped_ids` 3/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `atlasbench-mlflow-governance.` matches export (atlas-harden / MLflow governance) |
| 1 Instruction | ☑ | Long but complete; digest line 473 is wrong |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, deps in image |
| 3 Oracle | ☑ | Static review pass; runtime not executed |
| 4 Verifiers | ☑ | Strong coverage; digest helper contradicts instruction |
| 5 Metadata | ☑ | regular layout, hard, security, long_context |
| 6 Rubric | ☑ | Five milestone blocks on non-milestone task |
| 7 LLMaJ & agent evidence | ☑ | Digest mismatch confirmed in agent failure analysis |
| 8 Novelty & fairness | ☑ | No cheating paths; unfair digest ambiguity only |
| 9 Long context | ☑ | `governance-dossier.md` ~244 KB; authoritative |

---

## 9. Reviewer note (copy-paste to portal)

Really strong task overall — the dossier contract, hidden verifier fixtures, SQLite evidence schema, URI redaction matrix, and idempotency checks are all well thought out, and the difficulty calibration looks right. Two things to fix before accept: (1) clarify in `instruction.md` that `action_id` is excluded from the `evidence_chain_digest` payload (the verifier hashes `source_file` through `reason_code` only — that mismatch is why most near-complete runs failed the digest tests); (2) flatten the platform rubric into a single non-milestone `Agent …, ±N` list — `# Rubric 2` through `# Rubric 5` should go away since this isn’t a milestone task.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Instruction Styling | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Environment | no | — |
| Task Difficulty | no | — |
