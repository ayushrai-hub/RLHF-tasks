# Terminus Review Report: `pipe-sigpipe-writer-batch`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; not re-run locally — Docker unavailable) |
| **CHECK count** | 41 |
| **UNCHECK count** | 14 |

**Error categories (internal):** Task Difficulty

**Decision (concise):** The task is well-built: digest-pinned canonical Ubuntu 24.04 base, offline verifier deps, canonical `test.sh` reward block, binary rebuild anti-cheat, and strong spec↔test alignment per LLMaJ. The **only real blocker** is metadata: `task.toml` declares `difficulty = "hard"` while agent evaluation places the task in the **Medium** tier (worst model Claude 60%). Update `difficulty` to `"medium"` or rebalance until worst-model pass rate ≤20%.

**Insights (concise):**

- `ubuntu:24.04@sha256:0d39fcc…` **is** on the canonical base list (`docs/guidelines/dockerfxile.md:23`) — external report’s “non-canonical base” claim is false.
- All 12 `test_*` functions have one-line docstrings; validate’s “missing docstrings” warning is a false positive (docstring follows multi-line signature).
- Worst-model rate is **60%** (Claude), not 100% — `#54` passes; GPT-5.5 at 100% does not set the tier floor per `docs/guidelines/difficulty.md`.
- README line 28 wording on `pack_k1`–`pack_k8` vs missing bundled `pack_k7` is a **Low** doc typo, not a blocker.
- Go task (not Python) — Medium tier is acceptable for new submissions once metadata matches.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Task Difficulty | #45 | Declared `hard` but observed **Medium** tier | `task.toml:6` `difficulty = "hard"`; `entire-report.txt:1-7` Claude 60% (worst), GPT 100%, classified MEDIUM | Set `difficulty = "medium"` **or** rebalance task until worst-model ≤20% |

*No other High blockers.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `difficulty = "hard"` mismatches Medium evaluation (ChatGPT) | **Agree** | `task.toml:6`; `entire-report.txt:1-7` worst-model Claude 60% → Medium per `docs/guidelines/difficulty.md` |
| 2 | README says bundled stems `pack_k1`–`pack_k8` but skips `pack_k7` (ChatGPT Low) | **Agree** (Low only) | `environment/README.md:28`; fixtures dir has k1–k6,k8 only; k7 created at runtime in `test_runtime_pack_k_discovery` |
| 3 | Non-canonical Docker base image (entire-report CRITICAL) | **Disagree** | `environment/Dockerfile:1` uses `ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` — listed in `docs/guidelines/dockerfxile.md:23` |
| 4 | Inflated time estimates (entire-report WARNING) | **Partially agree** (not blocker) | `task.toml:12-13` expert 1440 / junior 3600 min; single Medium metadata issue per `reviewer-checklist-full.md` |
| 5 | Category should be `debugging` not `system-administration` (entire-report SUGGESTION) | **Partially agree** (not blocker) | `task.toml:7`; core work is multi-file Go debugging; single Medium metadata note |
| 6 | 13 tests missing docstrings (automated review) | **Disagree** | All 12 `test_*` in `tests/test_outputs.py:279-528` have `"""…"""` docstrings |
| 7 | Task too easy — worst-model 100% (automated review #54) | **Disagree** | `entire-report.txt:7` Claude 60% is worst model; 60% ≤80% → not rejected |
| 8 | LLMaJ `behavior_in_tests` / `behavior_in_task_description` pass | **Agree** | `entire-report.txt:92-93` confirmed by manual trace of instruction+README vs tests |
| 9 | Oracle 100% (3/3) | **Agree** (not re-run) | `entire-report.txt:11`; `solution/solve.sh` patches source + `go build` + runs driver |
| 10 | Hack check clean | **Agree** | `entire-report.txt:56-59`; `test_verify_overwrites_hand_written_outputs` enforces rebuild |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 4 short problem/requirement paragraphs; README holds schema detail | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer incident narrative, not LLM walkthrough | `instruction.md:1-13` |
| 3 | CHECK | No excessive markdown | No heavy headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step solve steps | States WHAT (fix source, rebuild, regenerate); no bug-by-bug guide | `instruction.md:5-7` |
| 5 | CHECK | No hints/solving strategies | README is normative contract (schemas/digests), not fix walkthrough | `environment/README.md`, `docs/guidelines/prompt-styling.md` |
| 6 | CHECK | No design-doc I/O tables | Instruction lists output fields inline, not mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, paths, outputs, README as contract | `instruction.md:5-11` |
| 8 | CHECK | Interesting | Multi-file Go relay debugging with crypto audit chains | task content |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app/environment`, `/app/output/…`, `/app/data/fixtures/` | `instruction.md:5-11` |
| 11 | CHECK | Task name not in instruction | No `pipe-sigpipe-writer-batch` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md`, `environment/` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in env code at runtime | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:28` |
| 15 | CHECK | Base image digest-pinned | Canonical `ubuntu:24.04@sha256:0d39fcc…` | `environment/Dockerfile:1`, `docs/guidelines/dockerfxile.md:23` |
| 16 | CHECK | Context in environment/ only | `COPY . /app/environment` from env dir | `environment/Dockerfile:34` |
| 17 | CHECK | No ground-truth answers in env | Broken scaffold + normative README contract (allowed) | `environment/README.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter Harbor mounts | No `docker-compose.yaml` | task root |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; `test.sh` only runs pytest | `environment/Dockerfile:27-28`, `tests/test.sh:11` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle no runtime network | `solve.sh` copies patches, builds, runs locally | `solution/solve.sh` |
| 23 | CHECK | Oracle derives results | Patches Go sources + `go build` + driver run | `solution/solve.sh:12-86` |
| 24 | CHECK | reward.txt + failure path | Writes 0 first, 1/0 after pytest | `tests/test.sh:3-16` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards 0/1 | `echo 0` / `echo 1` only | `tests/test.sh:4,14-16` |
| 27 | CHECK | Tests aligned with instructions | All README contract areas covered | §5 below; `entire-report.txt:93` |
| 28 | CHECK | Tests check correctness | Independent openssl digest replay | `tests/test_outputs.py:24-61,299` |
| 29 | CHECK | Behavior not implementation grep | No source grepping in tests | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Computed seals/fingerprints | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | 12/12 `test_*` have docstrings | `tests/test_outputs.py:282,306,323,344,358,367,375,389,417,437,478,493` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README at task root | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, allow_internet=false, verifier/agent timeouts | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Go+bash, pipes/signals/recovery tags fit; category loose but acceptable | `task.toml:7-10` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared hard; observed medium (60% worst) | `task.toml:6`, `entire-report.txt:1-7` |
| 46 | UNCHECK | steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:14` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:14` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:14` |
| 49 | UNCHECK | Milestone scope | N/A | `task.toml:14` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:24`, `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:23` |
| 52 | CHECK | Agent can't trivially cheat | Binary rebuild + digest verification | `tests/test_outputs.py:388-413`, `_rebuild_driver` pattern |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 60% ≤80% | `entire-report.txt:7` |
| 55 | CHECK | Not too hard/unfair | Spec sufficient per LLMaJ; agents reach 60%+ | `entire-report.txt:64,7` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / README) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Rebuild driver from `/app/environment` | all (via `_rebuild_driver`) | covered | `tests/test_outputs.py` fixtures |
| Six output files with correct schemas | all tests load outputs | covered | paths `tests/test_outputs.py:10-15` |
| Delayed sidecar reconcile seals | `test_delayed_sidecar_reconcile` | covered | `tests/test_outputs.py:279-300` |
| Post-recycle byte totals + wave_slice | `test_post_recycle_wave_byte_totals` | covered | `tests/test_outputs.py:303-319` |
| Wrap wave_slice invariants | `test_wrap_large_wave_trace_totals` | covered | `tests/test_outputs.py:322-338` |
| Multi-recycle pending flush | `test_multi_recycle_checkpoint_totals` | covered | `tests/test_outputs.py:341-354` |
| Journal seq monotonic | `test_journal_sequence_no_gaps` | covered | `tests/test_outputs.py:357-363` |
| Journal link hash chain | `test_journal_link_hash_chain` | covered | `tests/test_outputs.py:366-371` |
| Idempotent reruns | `test_repeat_run_produces_identical_links` | covered | `tests/test_outputs.py:374-385` |
| Overwrite hand-written outputs | `test_verify_overwrites_hand_written_outputs` | covered | `tests/test_outputs.py:388-413` |
| Cross-run ledger chain advance | `test_cross_run_chain_advance` | covered | `tests/test_outputs.py:416-433` |
| Resume offset epoch gate | `test_preload_offset_epoch_gate` | covered | `tests/test_outputs.py:436-442` |
| Overlay-wins chunk divisor / wave_slices | `test_overlay_slice_policy_fineness` | covered | `tests/test_outputs.py:477-489` |
| Runtime `pack_k*` discovery | `test_runtime_pack_k_discovery` | covered | `tests/test_outputs.py:492-528` |
| Config merge overlay-wins | implied by slice test + `_load_chunk_divisor` | covered | `tests/test_outputs.py:445-456` |

No spec gaps or phantom requirements found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | #45 blocker, #42-44, #46-49 N/A |
| `instruction.md` | #1-12, #27 |
| `environment/Dockerfile` | #13-20, #15 canonical base |
| `environment/README.md` | #5, #17, pack_k7 claim, spec alignment |
| `environment/.dockerignore` | #50, #51 |
| `environment/data/fixtures/` | pack_k7 bundled claim |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | agent stats, oracle, LLMaJ, external claims |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `docs/guidelines/difficulty.md` | #45, #54 tier rules |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate pipe-sigpipe-writer-batch/
Summary: 0 error(s), 15 warning(s), 2 info
```

Warnings are non-blocking: false-positive missing docstrings, solution-hint heuristic on README build section, non-milestone info.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | Does not set tier floor |
| terminus-claude-opus-4-8 | 60.0% (3/5) | **Worst model** |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | **no** |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `pipe-sigpipe-writer-batch`; regular layout; Go+bash |
| 1 Instruction | ☑ | Concise incident prompt; README contract pattern valid |
| 2 Environment | ☑ | Canonical digest-pinned Ubuntu 24.04; tmux+asciinema; offline deps |
| 3 Oracle | ☑ | Source-patch + build + run; 100% per report |
| 4 Verifiers | ☑ | Canonical reward block; behavior tests; all docstrings present |
| 5 Metadata | ☐ | **Blocker:** difficulty mismatch |
| 6 Rubric | ☑ | N/A — portal rubric not in task folder |
| 7 LLMaJ & agent evidence | ☑ | Reconciled external report; challenged false claims |
| 8 Novelty & fairness | ☑ | Multi-step debugging; anti-cheat solid |
| 9 Long context | ☑ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, Dockerfile pinning, and spec-to-test alignment look solid. The remaining blocker is difficulty metadata: `task.toml` lists `hard` but evaluation shows medium tier (worst model Claude 60%, GPT-5.5 100%). Update `difficulty` to `medium` or rebalance until worst-model pass rate qualifies as hard (≤20%). Optional Low fix: clarify README line 28 that bundled fixtures are k1–k6 and k8, with k7 as a runtime-discovery example.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Task Difficulty | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |

---

*Manual re-audit per `prompt.md` — 2026-06-24*
