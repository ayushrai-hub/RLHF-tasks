# Terminus Review Report: `fanotify-bind-watch-gap (2)`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform export 3/3; local run blocked by folder name) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** No real blockers found. Spec, contract, verifiers, rubric, Dockerfile, and anti-cheat design align. The submission export’s instruction-sufficiency FAIL and automated audit #14 pip FAIL are stale/false positives. Platform rubric is correctly flat (non-milestone), 23 positive points, 5 negatives. Accept.

**Insights (concise):**

- `audit_contract.md` now explicitly defines `retention_stamp` byte-string formula and `published/` entry-probe sync — closes prior agent-analysis gaps.
- Platform rubric is **not** in milestone block format (no `# Rubric N` headers); flat `Agent …, ±N` list is correct for `number_of_milestones = 0`.
- Automated audit #14 flags unpinned pip because `==` is on continuation lines; Dockerfile lines 29–30 pin `pytest==8.4.1` and `pytest-json-ctrf==0.3.5`.
- Worst-model pass rate 60% (GPT-5.5) → medium tier; declared `hard` in `task.toml` is informational only, not a blocker.
- Verifier rebuilds Go binary, independently recomputes all digest fields, and vc09 blocks static JSON.
- Optional polish only: trim internal tags (`frontier-hard`, `fp-recon`); consider one sentence naming “multi-file Go repair” in instruction.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium blockers | **Agree** | Full artifact re-audit; no spec/rubric/env/verifier gaps rise to High/Medium |
| 2 | ChatGPT: retention_stamp formula now explicit in contract | **Agree** | `environment/docs/audit_contract.md:81-88` — `hex(sha256(str(wave_gen) + "\|" + fixture_body))[0:16]` |
| 3 | ChatGPT: published-entry sync rule now explicit | **Agree** | `environment/docs/audit_contract.md:52-56` — `published/` must hold one regular file per fixture gen file after batch close |
| 4 | ChatGPT: Dockerfile digest pinning OK | **Agree** | `environment/Dockerfile:2` — `@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` |
| 5 | ChatGPT: canonical Ubuntu base acceptable for Go/fs task | **Agree** | Digest-pinned Ubuntu with pinned `golang-go=2:1.22~2build1`, tmux, asciinema; no canonical Go base required |
| 6 | ChatGPT: metadata difficulty mismatch optional polish | **Agree** | `task.toml:6` `hard` vs export `Difficulty: ✅ MEDIUM`; per `prompt.md` never blocks |
| 7 | ChatGPT: tag cleanup optional (`frontier-hard`, `fp-recon`) | **Agree** | `task.toml:12` — Low polish only |
| 8 | ChatGPT: add one sentence naming multi-file Go repair | **Agree** | `instruction.md:7` says “Repair the Go sources” but doesn’t say “multiple files”; Low polish |
| 9 | Export: Instruction Sufficiency ❌ FAIL (stamp vague, published implicit) | **Disagree** | Stale analysis; contract now documents both (`audit_contract.md:52-56`, `:81-88`); LLMaJ `behavior_in_*` all pass |
| 10 | Export: agents failed on retention_stamp self-reference | **Partially agree** | Historical agent runs; contract + broken `StampFor` in `environment/emit/trace/writer.go:39-43` make formula derivable; not a current spec blocker |
| 11 | Harbor REVIEW: non-canonical base image warning | **Partially agree** | Warning only; digest-pinned Ubuntu with Go toolchain is functional and justified |
| 12 | Harbor REVIEW: instruction highly abstract | **Partially agree** | Intentional for debugging task; goal clear at `instruction.md:7-9`; Low, not Revise |
| 13 | Harbor TEST QUALITY: ACCEPT | **Agree** | 12 tests with independent digest recompute; vc09 anti-static |
| 14 | Automated audit #14: unpinned pip | **Disagree** | False positive — checker requires `==` on same line as `pip install`; `environment/Dockerfile:28-30` pins packages on continuation lines |
| 15 | Automated review #41: stray `audit-report.md` | **Disagree** | Reviewer-tooling artifact from `./scripts/terminus audit`; not part of author submission |
| 16 | User concern: non-milestone task in milestone rubric format | **Disagree** | Export rubric (`entire-report.txt:283-295`) is flat list; no `# Rubric N` headers — correct per `docs/guidelines/rubrics.md:66` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~183 words, 5 short prose blocks; within practical concise budget | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Symptom-first engineer voice; no synthetic scaffolding | `instruction.md:1-9` |
| 3 | CHECK | No excessive markdown | Plain prose, no ##/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Describes repair goal + contract pointer, not fix steps | `instruction.md:7-9` |
| 5 | CHECK | No hints/strategies | No file-level bug map or patch walkthrough | `instruction.md`, env Go sources |
| 6 | CHECK | No design-doc tables in instruction | Tables live in contract doc (allowed) | `instruction.md` |
| 7 | CHECK | Well specified | Clear output path, fields, contract reference, rebuild requirement | `instruction.md:7-9` |
| 8 | CHECK | Interesting | Realistic Go fs/watch/bind-mount debugging scenario | task content |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against full TB2/TB3 index from artifacts alone | — |
| 10 | CHECK | Absolute paths | All paths absolute (`/app/...`) | `instruction.md:7-11` |
| 11 | CHECK | Task name not in instruction | No “fanotify-bind-watch-gap” string | `instruction.md` |
| 12 | CHECK | No canary string | None detected | `instruction.md` |
| 13 | CHECK | No web content fetch | No runtime fetch in env code | `environment/` |
| 14 | CHECK | Pinned pip `==` | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:29-30` |
| 15 | CHECK | FROM digest-pinned | Ubuntu 24.04 `@sha256:…` | `environment/Dockerfile:2` |
| 16 | CHECK | Context in environment/ only | `COPY . /app/environment` | `environment/Dockerfile:33` |
| 17 | CHECK | No ground-truth answers in env | Broken Go code + normative contract only; no golden JSON | `environment/`, `.dockerignore` |
| 18 | CHECK | No privileged/dangerous Docker | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter Harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh clean | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:27-30`, `tests/test.sh:14` |
| 21 | CHECK | Oracle passes | Platform export: oracle 100% (3/3) | `entire-report.txt:29` |
| 22 | CHECK | Oracle no internet | solve.sh writes/builds Go locally | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | Heredoc Go fixes + build + audit run | `solution/solve.sh:11+` |
| 24 | CHECK | reward.txt canonical block | Writes 0/1 on pass/fail; no trailing exit | `tests/test.sh:6-20` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:16-19` |
| 27 | CHECK | Tests aligned with instruction | All assertions trace to instruction + contract | §5 below |
| 28 | CHECK | Tests check correctness | Digest recompute, miss_gap, gen_skew, idempotency | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Crypto digests require exact hex; contract-defined | `audit_contract.md:1` |
| 31 | CHECK | Informative test docstrings | All 12 `test_vc*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 5 negatives | `entire-report.txt:291-295` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All lines use ±2,3,5 | `entire-report.txt:283-295` |
| 34 | CHECK | `Agent …, ±N` format | 13 properly formatted lines | `entire-report.txt:283-295` |
| 35 | CHECK | Rubric detailed; positive cap | 23 positive pts (≤40) | `entire-report.txt:283-290` |
| 36 | CHECK | Positive language on positives | Negative lines use `-N` scores appropriately | `entire-report.txt:291-295` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:283-295` |
| 38 | CHECK | Rubric no metadata/instruction refs | None | `entire-report.txt:283-295` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:283-295` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary parent files | Standard task layout; `audit-report.md` is reviewer-generated only | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, timeouts, allow_internet, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | Go+Bash fs/watch/mount debugging fits system-administration | `task.toml:7-12` |
| 45 | CHECK | Difficulty field present | `hard` declared; platform medium; worst-model 60% — informational | `task.toml:6`, export |
| 46 | UNCHECK | steps/ milestone layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | `.dockerignore` excludes tests/ | `environment/.dockerignore:14` |
| 51 | CHECK | Solution not accessible | `.dockerignore` excludes solution/ | `environment/.dockerignore:13` |
| 52 | CHECK | Agent can't trivially mutate inputs | Tests wipe workspace via setup script; fixtures read from env | `tests/test_outputs.py:135-147` |
| 53 | CHECK | No unpinned git clone | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:24-25` |
| 55 | CHECK | Not too hard/unfair | Contract specifies all formulas; agents pass 60–100% | `audit_contract.md`, export stats |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output at `/app/output/arrival_trace.json` with runs, report_digest, replay_token | `test_vc01_fresh_run_shape` | covered | `instruction.md:9`, `tests/test_outputs.py:158-177` |
| Four scenarios in matrix order | `test_vc01_fresh_run_shape` | covered | `audit_contract.md:9`, `tests/test_outputs.py:161-163` |
| Per-row fields (scenario, wave_gen, edge_fp_*, miss_gap, gen_skew, retention_stamp, row_seal) | `test_vc01_fresh_run_shape` | covered | `instruction.md:9`, `tests/test_outputs.py:167-177` |
| `miss_gap = 0` all scenarios | `test_vc03_auth_gap_after_close` | covered | `audit_contract.md:66`, `tests/test_outputs.py:202-206` |
| `gen_skew = 0` all scenarios | `test_vc03`, `test_vc06`, `test_vc11`, `test_vc12` | covered | `audit_contract.md:46`, `tests/test_outputs.py` |
| edge_fp_host/work formulas | `test_vc04_edge_fp_divergence` | covered | `audit_contract.md:28-36`, `tests/test_outputs.py:209-219` |
| Published entry probe (file count) | `test_vc05_green_count_mismatch` | covered | `audit_contract.md:52-56`, `tests/test_outputs.py:222-230` |
| pause_trap wave_gen=2, gaps zero | `test_vc06_pause_trap_clear` | covered | `audit_contract.md:76`, `tests/test_outputs.py:233-240` |
| wave_twice wave_gen=2 alignment | `test_vc07_second_wave_drift` | covered | `audit_contract.md:75`, `tests/test_outputs.py:243-250` |
| retention_stamp from fixture body | `test_vc08_stamp_body_match` | covered | `audit_contract.md:81-88`, `tests/test_outputs.py:253-259` |
| Anti-static / rebuild required | `test_vc09_regen_required` | covered | `instruction.md:7`, `tests/test_outputs.py:262-286` |
| report_digest + replay_token recompute | `test_vc10_envelope_digest_match` | covered | `audit_contract.md:102-120`, `tests/test_outputs.py:288-303` |
| stale_marker no recycle, gen_skew zero | `test_vc11_stale_marker_skew` | covered | `audit_contract.md:50-51,77`, `tests/test_outputs.py:306-315` |
| Idempotent report_digest/replay_token | `test_vc02_dual_run_digest_stable` | covered | `audit_contract.md:124-126`, `tests/test_outputs.py:185-191` |
| Hand-written JSON insufficient | `test_vc09_regen_required` | covered | `instruction.md:7` |

No phantom requirements or untested instruction mandates found.

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, spec alignment |
| `environment/docs/audit_contract.md` | #27, #55, stamp/published adjudication |
| `environment/Dockerfile` | #14-15, #20 |
| `environment/.dockerignore` | #50-51 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #21-23 |
| `task.toml` | #43-45, milestone N/A |
| `entire-report.txt` | #32-39, #45, #54, agent stats, rubric format |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: fanotify-bind-watch-gap (2)/ ===
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — pip line heuristic (false positive; packages pinned on continuation lines)
INFO: non-milestone task preferred for new submissions
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst reference model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best reference model |
| oracle | 100.0% (3/3) | Platform export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

Per-test pass rates (export): 9–10/10 on all 12 tests; no systematic spec-gap signal.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Go fs debugging task; folder matches export |
| 1 Instruction | ☑ | Abstract but clear; contract carries formulas |
| 2 Environment | ☑ | Digest-pinned Ubuntu, offline, tmux/asciinema, no tests/solution in image |
| 3 Oracle | ☑ | Platform 3/3; local oracle blocked by `(2)` in folder name |
| 4 Verifiers | ☑ | 12 pytest tests, rebuild enforcement, canonical reward block |
| 5 Metadata | ☑ | allow_internet=false; timeouts plausible |
| 6 Rubric | ☑ | Flat non-milestone format; 23/+ cap OK; 5 negatives |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL stale; quality checks pass; 60% worst model OK |
| 8 Novelty & fairness | ☑ | Multi-file Go coordination; contract-closed cheating paths |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The contract is tight — retention_stamp and published/ sync are spelled out clearly, the verifier rebuilds the Go binary and independently recomputes every digest field, and static JSON shortcuts are blocked. Dockerfile pinning and offline setup look good. The platform rubric is the correct flat format for a non-milestone task (23 positive points, five distinct negatives). I didn’t find any blocking spec-test gaps. Optional polish if you want: trim internal tags like `frontier-hard`, and maybe add one line in the instruction that this is a multi-file Go source repair — but neither is required to accept.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Uses Internet | no | — |

---

_Generated by `./scripts/terminus review` and enriched via manual audit per `prompt.md`._
