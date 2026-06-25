# Terminus Review Report: `exec-profile-cap-bound-drift`

**Generated:** 2026-06-19 (manual audit, table format v2)  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/exec-profile-cap-bound-drift`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 20 warnings) |
| **Oracle** | not executed locally; report shows 100% (3/3) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Revise. The task is otherwise strong — digest-pinned canonical Debian base, thorough 18-test verifier, real C/bash debugging depth, and declared `hard` matches observed tier (Claude 0%). The blocking issue is a spec gap on wrapped-sync gap clearing: `sync_path.sh` must evaluate the post-merge effective mask (`eff_post`) against `post_step.dat` `required`, but `instruction.md` only says post-step rules “govern” gap codes without stating the clearing predicate or that `eff_post` (not `eff_pre`) is the operand. Seven agent trials uniformly failed `test_c02_gap_trace` (3/10 per-test pass). Add explicit wrapped round-one gap-clearing and `open_stamp` replacement rules.

**Insights (concise):**

- ChatGPT’s **non-canonical Debian base** claim is **wrong**: `environment/Dockerfile:1` uses the exact canonical `debian:bookworm-slim` digest from `docs/guidelines/dockerfxile.md:22`.
- Automated script blockers on **#14** (pip) and **#31** (docstrings) are **false positives** — pytest is `==`-pinned on the next line; all 18 tests have docstrings.
- Automated **#45** fail used GPT 60% as worst-model; correct worst model is Claude **0%** → `hard` tier is correct per `docs/guidelines/difficulty.md`.
- LLMaJ `behavior_in_task_description: pass` (`entire-report.txt:119`) overclaims; agent failure analysis (`entire-report.txt:38-76`) correctly identifies the `eff_pre` vs `eff_post` inversion as systematic.
- `test_c04_stamp_subset` / `test_c17_stage_gate_subset` (7/10 pass) show `open_stamp` semantics are partially inferable but should still be stated explicitly.
- Rubric text in `entire-report.txt:347-360` is portal-only; no `rubric.txt` in task folder.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | **High** | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Wrapped round-one gap clearing uses **post-merge** mask (`eff_post & required == required` → `G0`), but instruction never states this predicate or that `sync_d` must check `eff_post`, not `eff_pre`. Broken env checks `eff_pre` (`0xb8 & 0x40 = 0` → `G7`); correct fix checks `eff_post` (`0xf8 & 0x40 = 0x40` → `G0`). | `instruction.md:3`; `environment/q7_launch/sync_path.sh:17-24` (bug: `eff_pre`); `environment/tools/k9_round:46-48` (passes both masks); `solution/solve.sh:75-82` (oracle uses `eff_post`); `tests/test_outputs.py:216-221`; `entire-report.txt:33-34,48-50` (`test_c02_gap_trace` 3/10) | Add to `instruction.md`: for wrapped round-one marks, gap code clears to `G0` when the post-step required subset is present in the **post-merge** effective mask (`eff_post`), not the pre-merge mask. |
| 2 | **Medium** | Instruction Styling, Test Alignment/Coverage Issues | #7, #27 | `stamp_code` on wrapped round-one rows must equal `open_stamp` from `post_step.dat` when the stage gate permits the subset; instruction only says post-step rules “govern” stamp values. Broken `gate_c` returns `0x80` for `wrapped_p1`; tests expect `0x01`. | `instruction.md:3`; `environment/fixtures/q8/post_step.dat:3` (`open_stamp=0x01`); `environment/q5_stage/pick_main.c:11-12` (returns `0x80`); `solution/solve.sh:51-55` (fixes to `0x01`); `tests/test_outputs.py:237-246,413-430`; `entire-report.txt:34-35` (`test_c04` 7/10) | State explicitly: when stage gate permits post-step subset on wrapped round-one rows, `stamp_code` is `open_stamp` from `post_step.dat`. |

*No Environment/Pinning blockers — Debian digest is canonical; pip packages are pinned.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical Debian base image; switch to `ghcr.io/laude-institute/t-bench/c-bookworm` (ChatGPT High; `entire-report.txt:156-182`) | **Disagree** | `environment/Dockerfile:1` = `public.ecr.aws/docker/library/debian@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` — identical digest to canonical list `docs/guidelines/dockerfxile.md:22`. No exemption required. |
| 2 | Wrapped-sync gap clearing must use `eff_post`, not `eff_pre` (ChatGPT High; `entire-report.txt:48-50,70-72`) | **Agree** | Bug: `sync_path.sh:18-20`; fix: `solution/solve.sh:76-78`; test: `test_c02_gap_trace` expects `G0`; 7/7 agent trials failed same symptom. |
| 3 | `open_stamp` replacement semantics undocumented (ChatGPT High; `entire-report.txt:73`) | **Partially agree** | `post_step.dat` has `open_stamp=0x01`; instruction says rules “govern” stamps but not replacement. 7/10 pass on `test_c04` — inferable from fixture + stage-gate sentence, but not explicit. Medium, not standalone High. |
| 4 | `class_tag` must be JSON integer (ChatGPT/`entire-report.txt:74,114`) | **Partially agree** | `instruction.md:3` types only `stamp_code` as JSON integer; `cap_emit.c` emits `%d` for `class_tag`. 1/7 trial string-vs-int failure — Low; note in revision, not primary blocker. |
| 5 | LLMaJ `behavior_in_task_description: pass` (`entire-report.txt:119`) | **Disagree** | Gap-clearing predicate absent from `instruction.md:3` despite enforced in `test_c02_gap_trace` / `test_c15_launch_probe_side_inert`. |
| 6 | LLMaJ `behavior_in_tests: pass` (`entire-report.txt:120`) | **Agree** | Tests c00–c17 cover all instruction-stated behaviors; gaps are **instruction** omissions, not phantom tests. |
| 7 | Difficulty metadata mismatch — hard vs medium (automated `review-report.md` blocker #3) | **Disagree** | Worst model = Claude **0%** ≤ 20% → hard per `docs/guidelines/difficulty.md`. `task.toml:6` correct. Script used max (60%) not min. |
| 8 | #14 pip unpinned / #31 missing docstrings (automated review) | **Disagree** | `environment/Dockerfile:33-35` pins `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`; all `test_c00`–`test_c17` have one-line docstrings in `tests/test_outputs.py`. Validator line-scans pip install line only. |
| 9 | Instruction dense wall-of-text (`entire-report.txt:219-237`) | **Partially agree** | Single dense paragraph in `instruction.md` (4 blocks, ~377 words). Styling concern only; not blocking if spec gaps fixed. |
| 10 | test.sh `$?` after comment fragile (`entire-report.txt:189-216`) | **Partially agree** | `tests/test.sh:14-21` — technically correct; defensive `exit_code=$?` capture is nicer but not a blocker. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1–3 paragraphs max) | 4 short paragraphs, within limit | `instruction.md` |
| 2 | CHECK | Natural prompt tone, not spec document | Incident-report engineering brief | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step dev instructions | States deliverables and paths, not debug steps | `instruction.md` |
| 5 | CHECK | No hints/solving strategies (WHAT not HOW) | Describes broken behaviors and output contract | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | UNCHECK | Instruction well specified | Gap-clearing uses `eff_post` unstated; `open_stamp` replacement vague | Blockers #1–2 |
| 8 | CHECK | Instruction interesting | Realistic Linux capabilities / break-glass debugging | task content |
| 9 | UNCHECK | Instruction unique | Not verified vs TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | All paths absolute | `/app/environment`, `/app/output/…` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No folder name string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in environment code | `environment/` |
| 14 | CHECK | Pinned pip deps with `==` | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:33-35` |
| 15 | CHECK | Base image digest-pinned | `@sha256:4724b8cc…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context in environment/ only | All COPY from environment subtree | `environment/Dockerfile:37-48` |
| 17 | CHECK | No ground truth in environment | Broken stubs only; no solution/tests COPY | `environment/Dockerfile` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose.yaml | task layout |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile`; `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Report: oracle 100% (3/3); solve.sh derives via full pipeline | `entire-report.txt:11`; `solution/solve.sh` |
| 22 | CHECK | Oracle no internet | `make` + local replay only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results (not hardcoded) | Patches sources, rebuilds, drives k9_round chain | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir, pytest, binary 0/1 on failure | `tests/test.sh:6-22` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:18-21` |
| 27 | UNCHECK | Tests aligned with instructions | `eff_post` gap predicate and `open_stamp` replacement tested but not fully specified | Blockers #1–2 |
| 28 | CHECK | Tests check correctness | SHA-256 hashes, journal semantics, bridge inheritance | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | End-to-end toolchain execution | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string asserts | Hash recomputation from fixtures | `tests/test_outputs.py:63-99` |
| 31 | CHECK | Informative test docstrings | All 18 `test_c*` functions have docstrings | `tests/test_outputs.py:186-430` |
| 32 | UNCHECK | Rubrics ≥3 negatives | N/A — no rubric file in task | task layout |
| 33 | UNCHECK | Rubric score set | N/A | task layout |
| 34 | UNCHECK | Rubric Agent format | N/A | task layout |
| 35 | UNCHECK | Rubric criteria precise | N/A | task layout |
| 36 | UNCHECK | Rubric positive language | N/A | task layout |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | task layout |
| 38 | UNCHECK | Rubric no task.toml refs | N/A | task layout |
| 39 | UNCHECK | Rubric no oracle/NOP refs | N/A | task layout |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh | task layout |
| 41 | CHECK | No unnecessary parent files | Clean task folder | task layout |
| 42 | CHECK | author_name/email present | anonymous / anonymous | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | category, subcategories, timeouts | `task.toml` |
| 44 | CHECK | Tags/languages/category match | bash+c, security, tool_specific | `task.toml:6-12` |
| 45 | CHECK | Difficulty matches agent rates | `hard` declared; worst model Claude 0% → hard | `task.toml:6`; `entire-report.txt:6-7` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:11` |
| 50 | CHECK | Tests not in Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | No accessible ground truth in env | solution/tests excluded from image | `environment/Dockerfile` |
| 52 | CHECK | Input data not trivially writable | Hash verification requires correct pipeline | `tests/test_outputs.py:110-111` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 0%; GPT 60% — neither > 80% | `entire-report.txt:6-7` |
| 55 | UNCHECK | Not too hard/unfair | `eff_post` gap rule tested but unstated; 7/7 agents failed same hidden semantic | Blocker #1; `entire-report.txt:48-50` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 9, 27, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| NNP bound routing through `base.dat` | `test_c00_nnp_bound_route` | covered | `instruction.md:3`; `tests/test_outputs.py:186-195` |
| `class_tag` from `auth_table` | `test_c01_auth_table_fidelity` | covered | `instruction.md:3`; `tests/test_outputs.py:198-213` |
| Wrapped r1 gap clears when post-step subset present | `test_c02_gap_trace`, `test_c15_launch_probe_side_inert` | **gap** | Instruction omits `eff_post` predicate; `instruction.md:3` vs `sync_path.sh:18-20` |
| Bound hash convergence sync/direct | `test_c03_bound_delta` | covered | `instruction.md:3`; `tests/test_outputs.py:227-234` |
| Wrapped r1 `open_stamp` + post-step subset in effective hash | `test_c04_stamp_subset`, `test_c17_stage_gate_subset` | **gap** | `open_stamp` replacement not explicit; `instruction.md:3` |
| Journal merge keeps latest seq | `test_c05_journal_merge_required` | covered | `instruction.md:3`; `tests/test_outputs.py:249-257` |
| Idempotent re-publish | `test_c06_warm_replay_stable` | covered | `instruction.md:3`; `tests/test_outputs.py:260-267` |
| R3 bridge inherits r2 ops effective | `test_c07_r3_bridge_inherit` | covered | `instruction.md:3`; `tests/test_outputs.py:271-289` |
| Ops-scope ambient mask merge | `test_c08_ambient_actor_scope` | covered | `instruction.md:3`; `tests/test_outputs.py:292-298` |
| Partial resume / mid-chain publish | `test_c09_partial_resume` | covered | implied by round sequence; `tests/test_outputs.py:301-316` |
| Row sort + `bundle_digest` | `test_c10_row_order_canonical` | covered | `instruction.md:3`; `tests/test_outputs.py:319-323` |
| Ops chain prerequisite for r3 | `test_c11_ops_chain_prerequisite` | covered | `instruction.md:3`; `tests/test_outputs.py:326-342` |
| Generation gate for bridge | `test_c12_generation_gate_bridge` | covered | `instruction.md:3`; `tests/test_outputs.py:345-355` |
| Seq monotonic on re-round | `test_c13_seq_monotonic` | covered | `instruction.md:3`; `tests/test_outputs.py:358-368` |
| Store rebuild from journal tail | `test_c14_journal_store_rebuild` | covered | `instruction.md:3`; `tests/test_outputs.py:371-387` |
| `probe_side.sh` append inert to publish | `test_c15_launch_probe_side_inert` | covered | `instruction.md:2`; `tests/test_outputs.py:390-400` |
| `ops_gen.env` generation=1 | `test_c16_ops_generation_recorded` | covered | `instruction.md:3`; `tests/test_outputs.py:403-410` |
| Direct marks G0 when effective matches base | `test_c02_gap_trace` (direct row) | covered | `instruction.md:3`; `tests/test_outputs.py:220-224` |
| `stamp_code` as JSON integer | all stamp asserts | covered | `instruction.md:3` |
| `class_tag` as JSON integer | `test_c01` hash path | **gap** (minor) | Only `stamp_code` typed; 1/7 agent string failure |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, blockers #1–2, spec alignment |
| `environment/Dockerfile` | #14, #15, canonical base adjudication |
| `environment/q7_launch/sync_path.sh` | Blocker #1 (broken `eff_pre` check) |
| `environment/tools/k9_round` | Blocker #1 (`sync_d` invocation) |
| `environment/q5_stage/pick_main.c` | Blocker #2 (broken `gate_c`) |
| `environment/fixtures/q8/post_step.dat` | Blockers #1–2 |
| `solution/solve.sh` | Oracle gap/stamp fixes |
| `tests/test_outputs.py` | #27, #31, spec alignment |
| `tests/test.sh` | #20, #24 |
| `task.toml` | #45 |
| `entire-report.txt` | Agent stats, external claims |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate exec-profile-cap-bound-drift/
Summary: 0 error(s), 20 warning(s), 2 info
```

Warnings are non-blocking: false-positive pip line scan, false-positive docstring scan, missing `.dockerignore`, milestone preference info.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60% (3/5) | 16–18/18 tests on best trials |
| terminus-claude-opus-4-8 | 0% (0/5) | Uniform `test_c02` / `test_c15` gap failure |
| oracle | 100% (3/3) | Per external report |
| nop | 0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% (Claude) |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

**Per-test pass rates (report):** `test_c02_gap_trace` 3/10, `test_c15_launch_probe_side_inert` 3/10 — systematic spec-gap signal.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `exec-profile-cap-bound-drift`; regular layout; bash+c security task |
| 1 Instruction | ☑ | Dense but valid; **gap-clearing `eff_post` rule missing** |
| 2 Environment | ☑ | Canonical digest-pinned Debian; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | solve.sh patches sources + full pipeline; not re-run locally |
| 4 Verifiers | ☑ | 18 behavior tests; reward block correct; all docstrings present |
| 5 Metadata | ☑ | `hard` matches Claude 0%; tags appropriate |
| 6 Rubric | ☑ | N/A — portal rubric only in report |
| 7 LLMaJ & agent evidence | ☑ | Agent clustering confirms spec gap; LLMaJ overclaimed description coverage |
| 8 Novelty & fairness | ☑ | Multi-bug C/bash repair; unfair only on unstated `eff_post` semantics |
| 9 Long context | ☑ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Verifiers, oracle design, and environment are solid — canonical digest-pinned Debian base, no runtime test installs, and hard difficulty (Claude 0%) are all correct. The blocker is instruction completeness for wrapped-sync round-one semantics: gap code must clear to `G0` when `post_step.dat` `required` is present in the **post-merge** effective mask (`eff_post`), not `eff_pre`, and `stamp_code` must equal `open_stamp` when the stage gate permits the subset. Seven agent trials uniformly failed this unstated rule. Add those two sentences to `instruction.md`; Docker base image change is not required.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Rubric | no | N/A |
