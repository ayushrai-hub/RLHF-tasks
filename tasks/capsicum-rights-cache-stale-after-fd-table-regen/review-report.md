# Terminus Review Report: capsicum-rights-cache-stale-after-fd-table-regen

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker unavailable locally; platform export reports 100% 3/3) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Rust systems-debugging task with excellent verifiers, anti-cheat, and a flat rubric within the 40-point cap. Two contract gaps block acceptance: `k7_contract.md` says WAL `ward_gen`/`frame_gen` “align” on sync records, but `test_k10_tranche_bind_shift` requires scenario 3 sync WAL `frame_gen - ward_gen == 2`; and emit-gate recomputation against tampered checkpoints is only implied, not stated as an independent k7_z2 rule. Fix contract text before resubmit.

**Insights (concise):**

- Baseline (no agent edits) passes 28/29 tests; dominant failure is `test_k10_tranche_bind_shift` (2/10 agent runs).
- `k7_contract.md` is normative per `instruction.md`; sync WAL delta rule must live there, not only in test docstrings.
- Platform rubric is **flat** (no `# Rubric N` blocks), 27 positive points, 4 negatives — correct non-milestone format.
- `#14` pip audit FAIL is a false positive: `requirements.lock` uses `==` + `--hash=sha256:` with `--require-hashes --no-deps`.
- Digest-pinned Rust base and WORKDIR `/app/environment` are intentional, not blockers.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Sync WAL generation delta unstated and contradicts contract wording | `environment/docs/k7_contract.md:66` says “WAL `ward_gen` and `frame_gen` align on sync records”; `tests/test_outputs.py:539-548` (`test_k10_tranche_bind_shift`) asserts `frame_gen - ward_gen == 2` on scenario 3 sync WAL tail; s3 fixtures `a0.tree` gen=15 / `b0.tree` gen=17 plus write-phase bumps yield delta 2 at sync WAL capture (`engine.rs:183-186`, `wal_append` before `sync_once`) | In `k7_contract.md` Sync section, replace “align” with explicit deny-tranche rule: on scenario 3 sync WAL records, `frame_gen - ward_gen == 2` (tree skew preserved through write bumps; `sync_once` aligns live rows after WAL append). Cross-reference scenario 3 deny semantics. |
| 2 | Medium | Test Alignment/Coverage Issues | #27, #55 | Emit gate must independently recompute checkpoint/WAL state; contract implies but does not state k7_z2 rule | `k7_contract.md:42-44` documents seal recomputation and “valid only when … match recomputation” plus “k7_z2 refuses emit on drift”; broken `engine.rs:245-256` trusts stored `cp.valid`; tests `test_k11_double_rebuild_stable` (`559-566`), `test_k14_corrupt_crc_rejected` (`631-639`), `test_k23_stale_seal_checkpoint_rejected` (`698-707`), `test_k24_truncated_log_rejected` (`740-748`) tamper checkpoint/WAL with `valid=True` and expect emit failure; oracle patches `checkpoint_ready` to recompute seal (`solution/solve.sh:401-416`) | Add explicit emit-gate bullet in Checkpoint section: `k7_z2` must recompute `order_seal`, verify WAL CRC chain, and compare `wal_seq` against intact log at emit time — must not trust stored `valid` alone when recompute diverges. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Sync-generation contract contradicts verifier: contract “align” vs `frame_gen - ward_gen == 2` on scenario 3 (ChatGPT / entire-report §4) | **Agree** | `k7_contract.md:66`; `test_outputs.py:546-548`; agent stats `test_k10_tranche_bind_shift: 2/10` in `entire-report.txt:67,94-96` |
| 2 | k7_z2 must recompute WAL/checkpoint and reject tampering even when `valid=true` forced (ChatGPT) | **Partially agree** | Contract has recomputation algorithm + drift refusal (`k7_contract.md:42-44`); missing explicit “k7_z2 recomputes at emit, does not trust stored valid” rule; tests k11/k14/k23/k24 prove behavior; 5/10 agent runs failed seal cluster |
| 3 | Hidden overlay, rebuild verifier, WAL CRC, fingerprint checks are strong (ChatGPT) | **Agree** | `test_k26_hidden_epoch_overlay_store_keys`; mandatory `cargo build` in tests; `test_k14`; `test_k05`/`test_k29`; hidden manifest under `tests/hidden/` |
| 4 | Optional: final WORKDIR `/app/environment` should be explicit (ChatGPT Low) | **Agree (Low, non-blocking)** | `environment/Dockerfile:46`; `instruction.md` already references `/app/environment` paths |
| 5 | Optional: invoke `/opt/verifier-venv/bin/pytest` directly in test.sh (ChatGPT Low) | **Agree (Low, non-blocking)** | `tests/test.sh:14` uses bare `pytest`; PATH includes venv (`Dockerfile:61`) — works today |
| 6 | Dockerfile FROM digest-pinned Rust base acceptable (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:9f841bbe…`; no canonical Rust image required for Rust toolchain task |
| 7 | `#14` unpinned pip (automated audit) | **Disagree** | `requirements.lock:4-21` uses `package==version` + `--hash=sha256:`; `Dockerfile:26-27` `--require-hashes --no-deps -r` — fully pinned |
| 8 | LLMaJ `behavior_in_task_description` PASS | **Agree with caveat** | Behaviors in `instruction.md` + referenced `k7_contract.md`; caveat: sync WAL delta and emit-gate recompute gaps remain |
| 9 | LLMaJ `behavior_in_tests` PASS | **Agree** | 29 tests cover schema, WAL, checkpoint, cross-view, hidden overlay, idempotency |
| 10 | Harbor review “READY TO USE” / no blockers | **Disagree** | Misses sync WAL delta spec gap driving 7/10 agent failures on k10 |
| 11 | Non-milestone task uses milestone rubric format | **Disagree** | `task.toml:11` `number_of_milestones = 0`; platform rubric (`entire-report.txt:331-346`) is flat `Agent …, ±N` list with no `# Rubric 2+` headers; 27 positive pts total — correct non-milestone layout |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 short paragraphs, ~209 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem narrative, not synthetic spec | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcome + contract ref, not module walkthrough | `instruction.md` |
| 5 | CHECK | WHAT not HOW hints | Describes repair goal; defers detail to contract | `instruction.md` |
| 6 | CHECK | No design-doc tables in instruction | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, output schema, contract reference | `instruction.md` |
| 8 | CHECK | Interesting | Real Capsicum/Rust WAL debugging scenario | task content |
| 9 | CHECK | Unique | Specialized rights-cache/fd-table replay; no duplicate in review scope | subjective |
| 10 | CHECK | Absolute paths | All paths absolute | `instruction.md` |
| 11 | CHECK | No task name in instruction | Folder name absent | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures | `environment/` |
| 14 | CHECK | Pinned pip deps | `==` + hashes in lock file; `--require-hashes` install | `requirements.lock`, `Dockerfile:26-27` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:` on Rust base | `Dockerfile:1` |
| 16 | CHECK | Build context scoped | COPY only under environment | `Dockerfile:34-44` |
| 17 | CHECK | No ground truth in env | Contract describes schema/rules, not oracle patches | `k7_contract.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest stack in Dockerfile; test.sh no installs | `Dockerfile:25-27`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Platform export: oracle 100% (3/3); local run blocked (no Docker) | `entire-report.txt:31` |
| 22 | CHECK | Oracle offline | solve.sh patches + cargo build only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives output | Runs k7_invoke/k7_z2 pipeline after source fixes | `solution/solve.sh:457-465` |
| 24 | CHECK | Canonical reward block | Writes 0/1 to reward.txt on pass/fail | `tests/test.sh:6-21` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | Phantom sync WAL delta; emit-gate recompute not explicit in contract | Blockers 1–2 |
| 28 | CHECK | Tests check correctness | Replay integration, tamper rejection, cross-view invariants | `tests/test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string matching | Structural/behavioral asserts with tolerances where needed | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | All 29 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives in platform rubric | `entire-report.txt:342-345` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use allowed magnitudes | `entire-report.txt:331-345` |
| 34 | CHECK | Agent …, ±N format | 15 properly formatted lines | `entire-report.txt:331-345` |
| 35 | CHECK | Rubric detailed; positive cap | 27 positive pts (≤40); flat non-milestone list | `terminus rubric-points` |
| 36 | CHECK | Positive rubric language | “Agent repairs…”, “Agent runs…” phrasing | `entire-report.txt:331-341` |
| 37 | CHECK | Rubric avoids /tests/ | No pytest or /tests/ references | platform rubric |
| 38 | CHECK | Rubric avoids instruction.md/task.toml | References `/app/environment/...` paths only | platform rubric |
| 39 | CHECK | Rubric avoids oracle/NOP | No oracle/NOP mentions | platform rubric |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | security + rust/bash match content | `task.toml:7-9` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; worst-model 0% → hard tier | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:11` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:11` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:11` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile` |
| 51 | CHECK | Solution not in env | No solution/ COPY | `Dockerfile` |
| 52 | CHECK | Agent cannot trivially cheat | Rebuild-from-source + hidden overlay digest | `tests/test_outputs.py`, `tests/hidden/` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% ≤80% | `entire-report.txt:25-27` |
| 55 | UNCHECK | Not unfair | Systematic spec gap on k10 (7/10 trials); partial emit-gate ambiguity | Blockers 1–2, agent analysis |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Emit `/app/output/k7_trace.json` with rows + chain_fingerprint | k05, k06, k28, k29 | covered | `instruction.md:2`; tests load report |
| Cross-view generation reconcile on hot scenarios | k01, k02, k18, k25 | covered | `instruction.md:2`; `k7_contract.md:46-48` |
| Transition action_code 6/7/9 on scenarios 2–4 | k09, k10, k15, k21 | covered | `k7_contract.md:18,52-56` |
| Hold-store ward keys use fragment digest | k01, k03, k26 | covered | `instruction.md:2`; `k7_contract.md:30` |
| WAL bust-before-success, monotone seq, ≥25 records | k03, k04, k08, k16 | covered | `k7_contract.md:34-36` |
| Checkpoint order_seal 0xBEEF mixing | k17, k20 | covered | `k7_contract.md:42-43` |
| k7_z2 refuses drift / tampered checkpoint | k11, k14, k23, k24 | gap (partial spec) | Contract implies; emit-gate recompute not explicit |
| Sync WAL ward_gen/frame_gen on scenario 3 deny tranche | k10 | **gap** | Contract says “align”; test requires delta 2 |
| ≥18 rows full chain | k21, k28 | covered | `k7_contract.md:62` |
| Hidden fixture overlay store keys | k26 | covered | verifier-only `tests/hidden/seq/s1/i0.frag` |
| Rebuild before grade | k07, k27 | covered | `instruction.md:3` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–7, #10–12, spec alignment |
| `environment/docs/k7_contract.md` | Blockers 1–2, sync/checkpoint rules |
| `environment/Dockerfile` | #14–16, #20, #50 |
| `environment/requirements.lock` | #14 pinning proof |
| `environment/src/engine.rs` | WAL append order, broken checkpoint_ready |
| `environment/cases/seq/s3/*.tree` | s3 gen skew (15 vs 17) |
| `tests/test_outputs.py` | k10, k11, k14, k23, k24, all verifier behavior |
| `tests/test.sh` | #24, #20 |
| `tests/hidden/` | #52 anti-cheat |
| `solution/solve.sh` | #23, oracle checkpoint/sync fixes |
| `task.toml` | #43–45, milestone N/A |
| `entire-report.txt` | Agent stats, platform rubric, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate capsicum-rights-cache-stale-after-fd-table-regen/
Summary: 0 error(s), 1 warning(s), 2 info
WARNING: pinned_dependencies — false positive (lock file uses == + hashes)
INFO: non-milestone task (milestones preferred but not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Dominant miss: k10 (7/10 trials) |
| terminus-claude-opus-4-8 | 0.0% (0/5) | Same k10 cluster |
| oracle | 100.0% (3/3) | platform export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

**Rubric format check (non-milestone):** Flat `Agent …, ±N` list in platform export; no `# Rubric 2+` headers; 27 positive points (cap 40). **Not** milestone-block format — correct.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches export; regular layout; `number_of_milestones=0` |
| 1 Instruction | ☑ | Concise; references k7_contract as normative |
| 2 Environment | ☑ | Digest-pinned Rust; tmux+asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Derives via patches + pipeline; platform 100% |
| 4 Verifiers | ☑ | 29 behavioral tests; rebuild enforced; reward canonical |
| 5 Metadata | ☑ | security/rust; allow_internet=false |
| 6 Rubric | ☑ | Flat format; 27/+ cap OK; 4 negatives |
| 7 LLMaJ & agents | ☑ | Spec gap confirmed on k10 despite LLMaJ PASS |
| 8 Novelty & fairness | ☑ | Multi-module Rust debug; k10 gap unfair |
| 9 Long context | N/A | not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Capsicum replay task — the rebuild-from-source verifier, hidden fixture overlay, WAL integrity checks, and flat rubric are all in great shape, and difficulty calibration looks right at 0% agent pass with a clean oracle.

Two contract fixes before accept: in `k7_contract.md` Sync section, document that scenario 3 sync WAL records must have `frame_gen - ward_gen == 2` (deny-tranche tree skew through write bumps) instead of saying ward_gen and frame_gen “align” on sync records — that wording drove most agent failures on k10. Also add an explicit checkpoint emit-gate rule that `k7_z2` recomputes `order_seal`, CRC chain, and `wal_seq` at emit and rejects tampered checkpoint files even when `valid` is forced true.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Milestones | no | N/A (non-milestone task; rubric correctly flat) |
| Task Difficulty | no | 0% pass rate appropriate |
