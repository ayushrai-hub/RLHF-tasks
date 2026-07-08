# Terminus Review Report: `reverse-tape-gradient-lab`

**Generated:** 2026-07-04 15:30 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/reverse-tape-gradient-lab`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong reverse-mode autodiff task with excellent Rust/Go split, independent FD verification, mutation coverage, and anti-cheat design. ChatGPT/Harbor “non-canonical Docker base” is **not** a blocker — both final-stage and builder digests match the sanctioned list in `docs/guidelines/dockerfxile.md` and `terminus/scripts/validate_task.py` `CANONICAL_BASE_IMAGES`. Platform rubric is correctly **flat** (non-milestone format; no `# Rubric 2+`; 35/40 pts). Real blockers: `grad_contract.txt` omits two verifier-enforced requirements — `gradctl-probe grad` six-decimal formatting and the top-level `gradient_report.json` schema field `grad_ok` — while `instruction.md` defers all normative behavior to that contract.

**Insights (concise):**

- Final `FROM golang:1.24-bookworm@sha256:1a6d4452…` digest matches sanctioned `public.ecr.aws/docker/library/golang:1.24-bookworm`; Rust builder digest `9f841bbe…` matches sanctioned `rust:1.85-slim` (`environment/Dockerfile:1,8`; `dockerfxile.md:11-12`).
- Agent stats: Claude Opus 4.8 100% (5/5), GPT-5.5 0% (0/5) → worst-model 0% (hard tier); declared `hard` matches platform `hard` — informational only.
- Rubric: 35 positive pts, 6 negatives, flat `Agent …, ±N` list with no milestone blocks (`entire-report.txt:383-399`) — correct non-milestone format.
- Spec gaps drove real agent failures: probe `4,-3` vs `4.000000,-3.000000` (2/5 trials); missing top-level `grad_ok` (1/5 trial) per `entire-report.txt:71-73,92-95`.
- `GRAD_GRAD_TOL` wiring failures (4/5 trials) are agent gaps — contract lines 23, 82-83 explicitly document env override precedence.
- Missing per-test docstrings (#31) and 7 tags are polish only — module docstring present (`tests/test_outputs.py:1`); not Revise drivers.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27 | `gradctl-probe grad` output format enforced by verifier but not normatively specified in contract | `tests/test_outputs.py:378-382` asserts `grad == "4.000000,-3.000000"`; `grad_contract.txt:108` only says “comma-separated gradient components”; no `%.6f` / six-decimal rule for probe (unlike `fd_max` at line 101 and CSV `forward_6`/`backward_6` at line 104) | Add to `grad_contract.txt` Probe section: `gradctl-probe grad <var>` prints comma-separated components each formatted to exactly six decimal places (e.g. `4.000000,-3.000000`) |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #27 | Top-level `gradient_report.json` field `grad_ok` tested but not documented in normative schema | `tests/test_outputs.py:347,415,456,459` assert `report["grad_ok"]`; `environment/internal/export/report.go:54-58` emits top-level `grad_ok`; `grad_contract.txt` lists `/app/output/gradient_report.json` (line 7) and uses `grad_ok` in digests/status (lines 67, 92, 107, 125) but never defines the report JSON schema with top-level `grad_ok`, `fd_max`, `lab_version`, `trials`, digests | Add explicit `gradient_report.json` schema block to `grad_contract.txt` listing top-level fields including `grad_ok` (true when every trial passes FD check) and `fd_max` |

*Non-blockers cleared:* Docker canonical bases (digest match); 7 tags (Low); Cargo.lock generation (Low); rubric format/points; milestone rubric N/A; difficulty metadata; `audit-report.md` in task folder is reviewer-generated artifact not part of submission zip.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Non-canonical Docker base images — `rust:1.85-slim` and `golang:1.24-bookworm` from Docker Hub (ChatGPT High; Harbor CRITICAL `entire-report.txt:162-189`) | **Disagree** | `environment/Dockerfile:8` digest `1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` matches sanctioned `golang:1.24-bookworm` (`dockerfxile.md:11`, `validate_task.py:67`); line 1 digest `9f841bbe…` matches sanctioned `rust:1.85-slim` (`dockerfxile.md:12`, `validate_task.py:68`); `_check_canonical_base` passes on digest match; `./scripts/terminus validate` emits no `check_sanctioned_base_images` warning |
| 2 | `gradctl-probe grad` must print `4.000000,-3.000000` but contract lacks six-decimal rule (ChatGPT High; `entire-report.txt:92`) | **Agree** | `tests/test_outputs.py:382`; `grad_contract.txt:108` vs line 101 (`fd_max` six decimals) |
| 3 | Top-level `grad_ok` in `gradient_report.json` tested but not in public contract schema (ChatGPT High; `entire-report.txt:93-95`) | **Agree** | `tests/test_outputs.py:347`; `report.go:58`; no schema section in `grad_contract.txt` |
| 4 | Tags array has 7 entries — trim to ≤6 (ChatGPT Low; `entire-report.txt:196-214`) | **Agree (Low only)** | `task.toml:13` has 7 tags; `validate` warns; not a Revise driver |
| 5 | Commit `Cargo.lock` instead of generating at build (ChatGPT Low; `entire-report.txt:217-236`) | **Agree (Low only)** | `Dockerfile:6` runs `cargo generate-lockfile`; reproducibility polish only |
| 6 | Harbor NEEDS REVISION for base images (`entire-report.txt:293-298`) | **Disagree** | Same digest evidence as claim 1; precedent: `tasks/rbac-temporal-rust/review-report.md` |
| 7 | LLMaJ `structured_data_schema` PASS — contract documents full `gradient_report.json` schema (`entire-report.txt:127`) | **Partially agree** | Contract references `grad_ok` behaviorally but lacks explicit JSON schema block; LLMaJ overstates documentation completeness |
| 8 | `GRAD_GRAD_TOL` env override is a spec gap (`entire-report.txt:69,91`) | **Disagree** | `grad_contract.txt:23,82-83` documents override precedence; agent wiring failures are implementation gaps |
| 9 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `entire-report.txt:383-399` — flat `Agent …, ±N` list, no `# Rubric 2+`; `task.toml:10` `number_of_milestones = 0`; per `rubrics.md:66` this is correct |
| 10 | Rubric positive total >40 (user concern) | **Disagree** | `./scripts/terminus rubric-points entire-report.txt` → 35/40 PASS |
| 11 | Test quality review ACCEPT (`entire-report.txt:314`) | **Agree** | Independent FD evaluator, mutation tests, cross-surface invariants — sound verifier design |
| 12 | Missing pytest docstrings block acceptance (automated audit #31) | **Disagree (Low)** | 11 `test_*` lack docstrings but module docstring exists (`tests/test_outputs.py:1`); descriptive names; precedent treats as polish |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 prose blocks ~232 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational problem statement, not spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints/strategies | Defers to contract; no walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal + contract authority | `instruction.md:6-7,24` |
| 8 | CHECK | Interesting | Realistic Rust/Go autodiff lab | — |
| 9 | UNCHECK | Unique | Cannot verify vs full TB corpus | — |
| 10 | CHECK | Absolute paths | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name absent | Name not in instruction | `instruction.md` |
| 12 | CHECK | No canary | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | Offline env | `task.toml:24` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1` | `Dockerfile:20` |
| 15 | CHECK | Digest-pinned FROM | Both stages `@sha256:` | `Dockerfile:1,8` |
| 16 | CHECK | Context in environment/ | All COPY from env | `Dockerfile` |
| 17 | CHECK | No ground truth in env | Stubs only; answers computed | `backward.rs`, Go stubs |
| 18 | CHECK | No dangerous Docker | No privileged/socket | `Dockerfile` |
| 19 | CHECK | Compose harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in Dockerfile; test.sh no installs | `Dockerfile:20`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed in this review | — |
| 22 | CHECK | Oracle no internet | solve.sh writes code + rebuild | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Implements real Rust/Go logic | `solution/solve.sh` |
| 24 | CHECK | reward.txt canonical | Writes 0 then 1/0 | `tests/test.sh:3-16` |
| 25 | CHECK | Same verifier logic | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Two contract omissions vs test assertions (blockers 1–2) | `grad_contract.txt`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness | Independent FD audit + cross-surface | `test_independent_gradient_audit` |
| 29 | CHECK | Behavior not implementation | CLI/output checks only | `tests/test_outputs.py` |
| 30 | UNCHECK | No brittle string matching | Exact probe grad string without flexible float parse | `tests/test_outputs.py:382` |
| 31 | UNCHECK | Informative docstrings | 11 tests lack per-function docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 rubric negatives | 6 negatives | `entire-report.txt:395-399` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All valid | `entire-report.txt:383-399` |
| 34 | CHECK | Rubric Agent format | 17 proper lines | `entire-report.txt:383-399` |
| 35 | CHECK | Rubric detailed; ≤40 pts | 35/40 | `rubric-points` output |
| 36 | CHECK | Positive rubric phrasing | Negatives use `-N` | `entire-report.txt:395-399` |
| 37 | CHECK | Rubric no /tests/ refs | Clean | `entire-report.txt:383-399` |
| 38 | CHECK | Rubric no metadata refs | Clean | `entire-report.txt:383-399` |
| 39 | CHECK | Rubric no oracle/NOP | Clean | `entire-report.txt:383-399` |
| 40 | CHECK | Required files present | All present | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in submission | task tree |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Metadata complete | All core fields | `task.toml` |
| 44 | CHECK | Tags/category applicable | `scientific-computing` fits autodiff; languages match | `task.toml:7,12` |
| 45 | CHECK | Difficulty present | `hard` in task.toml; worst-model 0% | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:10` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | .dockerignore + no COPY tests | `environment/.dockerignore` |
| 51 | CHECK | Solution not in env | Excluded from build | `environment/.dockerignore` |
| 52 | CHECK | No trivial cheat path | Independent FD + mutation tests | `tests/test_outputs.py` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:26-27` |
| 55 | CHECK | Not too hard/unfair | Agents reach 10/11; failures are narrow integration gaps | `entire-report.txt:37-48,100-106` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 21, 27, 30, 31, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Contract is normative for all surfaces | all | covered | `instruction.md:6-7` |
| `rebuild.sh` before runs | `test_rebuild_and_reset_run_all` | covered | `tests/test_outputs.py:343` |
| Full graph set `grad_ok` true + probe status ok | `test_rebuild_and_reset_run_all` | **gap** | test asserts top-level `grad_ok`; contract lacks schema (`grad_contract.txt:7`) |
| Cross-surface audit aligned | `test_cross_surface_alignment` | covered | `grad_contract.txt:113-122` |
| Independent FD gradient audit | `test_independent_gradient_audit` | covered | `grad_contract.txt:65-68` |
| Probe grad for shared_square x → `4.000000,-3.000000` | `test_shared_square_probe_grad` | **gap** | `grad_contract.txt:108` lacks six-decimal rule |
| Second-order epoch ≥2, grad starts `2.` | `test_second_order_epoch_increment` | covered | `grad_contract.txt:54-59,109` |
| `GRAD_GRAPH_DIR` mutation | `test_mutation_graph_dir_copy` | covered | `grad_contract.txt:22,127` |
| invalid_broadcast → grad_ok false, status fail, artifacts exist | `test_negative_invalid_broadcast_graph` | covered | `grad_contract.txt:125-126` |
| Session carry without reset | `test_partial_set_s2_without_reset_carries_session` | covered | `grad_contract.txt:70-71,121` |
| inspect projection format | `test_inspect_projection` | covered | `grad_contract.txt:115-116` |
| checkpoint waterline/fingerprint | `test_checkpoint_waterline` | covered | `grad_contract.txt:75-78` |
| `GRAD_GRAD_TOL` env override | `test_policy_env_grad_tol_override` | covered | `grad_contract.txt:23,82-83` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blockers, spec alignment |
| `environment/Dockerfile` | #15, canonical-base adjudication |
| `environment/docs/grad_contract.txt` | #27, blockers 1–2, spec alignment |
| `environment/internal/export/report.go` | blocker 2 (`grad_ok` emission) |
| `tests/test_outputs.py` | #27, #30, #31, blockers, spec alignment |
| `tests/test.sh` | #20, #24 |
| `task.toml` | #44, #45, milestone N/A |
| `entire-report.txt` | #32-39, #45, #54, agent stats, rubric format |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `terminus/scripts/validate_task.py` | `CANONICAL_BASE_IMAGES` adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate reverse-tape-gradient-lab/
Summary: 0 error(s), 14 warning(s), 2 info
Warnings include: 7 tags, missing test docstrings, grad_contract hint patterns
No check_sanctioned_base_images warning
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 100.0% (5/5) | Full pass |
| terminus-gpt5-5 | 0.0% (0/5) | 4 trials at 10/11; 1 at 6/11 |
| oracle | 100.0% (3/3) | Per platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

Per-test pass rates (`entire-report.txt:37-48`): lowest `test_policy_env_grad_tol_override` 6/10; `test_shared_square_probe_grad` 8/10.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular layout; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise; contract-deferred; absolute paths |
| 2 Environment | ☑ | Digest-pinned sanctioned bases; tmux+asciinema; offline |
| 3 Oracle | ☐ | Not executed locally; platform 100% |
| 4 Verifiers | ☑ | Sound design; two contract gaps; missing per-test docstrings |
| 5 Metadata | ☑ | Complete; 7 tags Low only |
| 6 Rubric | ☑ | Flat non-milestone format; 35/40; 6 negatives |
| 7 LLMaJ & agent evidence | ☑ | Spec-gap claims on probe format + grad_ok confirmed; GRAD_GRAD_TOL is agent gap |
| 8 Novelty & fairness | ☑ | Multi-file Rust+Go; anti-cheat strong |
| 9 Long context | N/A | No `long_context` subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really solid autodiff task — the Rust tape kernel plus Go orchestration split is well thought out, the independent finite-difference verifier is strong, and the cross-surface invariants make cheating hard. Docker bases are fine as-is (digests match the approved list). Two small contract gaps to fix before accept: `grad_contract.txt` should explicitly say `gradctl-probe grad` prints each component with six decimal places (tests expect `4.000000,-3.000000`), and it should document the top-level `gradient_report.json` schema including the summary `grad_ok` boolean. Optional polish: trim tags to six and add one-line pytest docstrings.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Instruction Styling | yes | 1, 2 |
| Pinning Issues | no | — |
| Environment | no | — |
| Rubric | no | — |
| Milestones | no | — |
| Metadata Issues | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
