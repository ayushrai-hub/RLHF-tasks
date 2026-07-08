# Terminus Review Report: `mte-loader-interpreter-split`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High (static audit); Medium on oracle (not run locally) |
| **Validation** | warn (0 errors, 2 warnings) |
| **Oracle** | not executed locally (per `entire-report.txt`: 100% 3/3) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** none

**Decision (concise):** The external reviewer’s sole High blocker — non-canonical `debian:bookworm-slim` base — is **incorrect**. `environment/Dockerfile:1` uses the exact digest listed as canonical in `docs/guidelines/dockerfxile.md:22` and `terminus/scripts/validate_task.py:73` (`CANONICAL_BASE_IMAGES`). `./scripts/terminus validate` emits no sanctioned-base warning. Task is otherwise strong: oracle 100%, NOP 0%, worst-model 20% (hard tier), rubric 24/40 pts, `allow_internet = false`, verifier deps baked in image, 12 mutation-style tests. Optional polish only: dense instruction prose; add `binutils` for `readelf` diagnostics (suggestion, not blocker).

**Insights (concise):**

- C arm64 tag-reconciliation task: repair `merge_r8.c`, `walk_k3.c`, `link_emit.c`, `persist_v5.c`, `harness_core.c`; rebuild and regenerate `/app/output/tag_reconcile.json`.
- Tests recompute digests, lineage, counters, and fault observations from live fixtures — no golden-file cheating.
- `task.toml` category is `build-and-dependency-management` (not `security`); matches build/link/reconcile domain.
- Agent failure analysis in export flags global vs per-profile graph-walk ambiguity — informational for author polish, not a blocking spec gap (instruction already says “transitive shared-object graph walk”).

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | **High:** Non-canonical final base image — `debian:bookworm-slim` not approved; must switch or justify (Reviewer Assessment) | **Disagree** | `environment/Dockerfile:1` `FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`; identical entry in `docs/guidelines/dockerfxile.md:22` under “Build Tools & Distros”; `terminus/scripts/validate_task.py:73` `CANONICAL_BASE_IMAGES`; `./scripts/terminus validate` → 0 errors, no `check_sanctioned_base_images` warning |
| 2 | Harbor REVIEW REPORT: Non-Canonical Base Image warning (`entire-report.txt:137-159`) | **Disagree** | Same digest as row 1; Harbor LLMaJ references obsolete `ghcr.io/laude-institute/t-bench/*` framing — Edition 2 canonical list is ECR Docker Library digests in `dockerfxile.md` |
| 3 | Instruction density / domain jargon (`entire-report.txt:162-184`) | **Agree (Low only)** | `instruction.md` is one dense prose block (~374 words); technically complete per LLMaJ quality checks; polish only |
| 4 | Add `binutils` for `readelf` in Dockerfile (`entire-report.txt:191-214`) | **Agree (suggestion)** | `solution/solve.sh` uses `readelf` with `\|\| true`; `build-essential` may include binutils on bookworm-slim — optional hardening, not blocking |
| 5 | Security category mismatch (`entire-report.txt:405-409`) | **N/A** | `task.toml:6` `category = "build-and-dependency-management"`; reviewer correctly notes this is not submitted as `security` |
| 6 | Global vs per-profile graph-walk instruction ambiguity (Agent Failure Analysis) | **Partially agree (Low)** | `instruction.md:13` requires “transitive shared-object graph walk”; export notes agents miscounted scope — author may add one clarifying sentence; tests and oracle align with current text |
| 7 | Automated audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:31-33` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; multiline `pip install` triggers false positive |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 prose paragraphs (lines 1-3, 5-7, 9-19); ~374 words — within budget | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first debugging narrative | `instruction.md:1-3` |
| 3 | CHECK | No excessive markdown formatting | No `##` / tables / code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal and rebuild command, not file-by-file edits | `instruction.md:3` |
| 5 | CHECK | No hints or solving strategies | Describes output schema and semantics, not bug locations | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | JSON schema, digest rules, graph walk, fault_obs, idempotency documented | `instruction.md:5-19` |
| 8 | CHECK | Instruction is interesting | Real arm64 ELF/link reconciliation debugging | `instruction.md:1` |
| 9 | UNCHECK | Instruction is unique | Corpus uniqueness not verified from artifacts | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/tag_reconcile.json`, etc. | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No slug in text | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Local COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:31-33` |
| 15 | CHECK | Base Docker image is pinned by digest | Canonical `@sha256:4724b8cc…` | `environment/Dockerfile:1`, `dockerfxile.md:22` |
| 16 | CHECK | Environment does not use context from outside the environment directory | All COPY from env subdirs | `environment/Dockerfile:35-46` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Broken C sources only; tests/solution excluded | `environment/.dockerignore`, `environment/bridge/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:30-33`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Not run locally; export reports 100% (3/3) | `entire-report.txt` |
| 22 | CHECK | Oracle does not require internet or downloading packages | Patches + `make` + batch run | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Applies patches, rebuilds, runs harness | `solution/solve.sh`, `solution/patches/` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py`, `tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 only | `tests/test.sh` |
| 27 | CHECK | All tests are aligned with instructions | 12 tests cover schema, routing, lineage, walk, fault_obs, idempotency | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check for correctness, not just format | Dynamic recomputation from fixtures + mutations | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | No source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Recomputed expected values | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_z*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives in export | `entire-report.txt:398-401` |
| 33 | CHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | ±2, ±3, ±5 used | `entire-report.txt:390-401` |
| 34 | CHECK | Each rubric criterion is one line starting with Agent, comma, then score | 11 Agent lines | `entire-report.txt:390-401` |
| 35 | CHECK | Rubric criteria are detailed and precise | 24 positive pts (≤40 cap) | `./scripts/terminus rubric-points entire-report.txt` |
| 36 | CHECK | Rubric criteria use positive language | Positive phrasing on reward lines | `entire-report.txt:390-397` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ directory | No /tests/ refs | `entire-report.txt:390-401` |
| 38 | CHECK | Rubric does not reference metadata (task.toml) or instruction.md | No metadata refs | `entire-report.txt:390-401` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:390-401` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | `audit-report.md` / `review-report.md` are reviewer artifacts, not in submission zip | — |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | difficulty, category, tags, timeouts | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | `build-and-dependency-management` fits C build/link repair | `task.toml:6-9` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard`; worst-model 20% | `task.toml:5`, `entire-report.txt:19-21` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — non-milestone | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | `.dockerignore` excludes tests | `environment/.dockerignore` |
| 51 | UNCHECK | Agent cannot modify input data to trivially pass tests | Fixtures writable for mutation tests by design | `tests/test_outputs.py` |
| 52 | CHECK | Git repos pinned to specific commit | No git clone | `environment/Dockerfile` |
| 53 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% ≤80% | `entire-report.txt:19-21` |
| 54 | CHECK | Task is not too hard or unfair | Oracle 100%; agents pass 11/12 on best runs; fair debugging task | `entire-report.txt` |
| 55 | UNCHECK | Instruction sufficiency (platform) | Export flags FAIL on graph-walk ambiguity — informational, not blocking after manual audit | `entire-report.txt:45-94` |

**Quick copy-paste**

**CHECK:** 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 52, 53, 54

**UNCHECK:** 9, 21, 46, 47, 48, 49, 51, 55

---

## 5. Agent performance (from export)

| Model | Pass rate |
|-------|-----------|
| terminus-claude-opus-4-8 | 100% (5/5) |
| terminus-gpt5-5 | 20% (1/5) |
| oracle | 100% (3/3) |
| nop | 0% (0/1) |

**Worst-model:** 20% → `hard` tier. **Rubric:** 24/40 positive pts (PASS).

---

## 6. Reviewer note (copy-paste to portal)

This is a strong C debugging task — multi-module arm64 tag reconciliation with excellent mutation-based tests, oracle at 100%, and proper offline setup (`allow_internet = false`, verifier deps in the image). I disagree with the Needs Revision decision on the Dockerfile: `environment/Dockerfile:1` already uses the sanctioned canonical `debian:bookworm-slim@sha256:4724b8cc…` listed in `docs/guidelines/dockerfxile.md`. No base-image change or justification comment is required. Category is correctly `build-and-dependency-management`. Optional author polish: clarify that the transitive graph walk enumerates all dep fixtures globally (not per-profile routed dep only), and consider adding `binutils` for `readelf` diagnostics. Accept.

---

## 7. Audit log

- [x] Read task.toml, instruction.md, Dockerfile, test.sh, test_outputs.py, solve.sh
- [x] Ran `./scripts/terminus validate` → 0 errors
- [x] Ran `./scripts/terminus audit` + `./scripts/terminus review`
- [x] Adjudicated external reviewer “Needs Revision” base-image claim — **false positive**
- [x] Cross-checked `entire-report.txt` agent stats and rubric
- [ ] Oracle not run locally (export: 100%)
