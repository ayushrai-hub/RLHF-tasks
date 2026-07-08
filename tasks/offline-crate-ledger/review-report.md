# Terminus Review Report: offline-crate-ledger

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (Docker daemon unavailable in review environment) |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Strong Rust bug-fix task with solid black-box verifiers, pinned environment, and appropriate difficulty (worst-model 20%). Pre-release ordering is now documented in `resolver-contract.md`. Two real blockers remain: (1) the agent-visible contract still omits fixed-point iteration and stale-constraint retraction tested by `test_version_reselection_drops_dependencies_from_no_longer_selected_version` (6/10 agent runs); (2) the platform rubric uses forbidden `+4` scores. Pip pinning (#14) and non-milestone `# Rubric 1` format are **not** blockers on re-audit.

**Insights (concise):**
- ChatGPT's fixed-point/retraction finding is **confirmed** — `resolver-contract.md` ends at version-selection rules with no iteration or retraction language.
- Pre-release ordering **is** documented (`resolver-contract.md:37-39`); prior reviewer feedback on that point appears addressed.
- Dockerfile pip packages **are** `==`-pinned (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); automated #14 fail is a false positive.
- Non-milestone task using `# Rubric 1` alone is **allowed** per `docs/guidelines/rubrics.md` ("`# Rubric 1` optional; no `# Rubric 2+`").
- Rubric positive total 37/40 — under cap; typo `offline-crate-ledgerfor` is Low only.
- Oracle statically reviewed: `solve.sh` writes a full iterative resolver (fixed-point loop), not hardcoded output.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | Agent-visible `resolver-contract.md` does not state that resolution must iterate to a fixed point or discard/re-derive constraints and feature-driven dependencies when a package's selected version changes. `test_version_reselection_drops_dependencies_from_no_longer_selected_version` enforces this (6/10 agent pass). | `environment/docs/resolver-contract.md:35-48` — version selection only; no iteration/retraction. `tests/test_outputs.py:224-258` — expects `app@1.5.0` + `crypto@1.8.0` after policy forces downgrade, with `2.5.0` absent. `entire-report.txt:42,57` — universal agent failure on this test. | Add an explicit contract section: resolution repeats until selections and feature-driven deps stabilize; constraints/deps from a superseded version must be retracted and rebuilt from the newly selected version only. |
| 2 | Medium | Rubric | #33 | Platform rubric uses forbidden `+4` score (allowed set is ±1, ±2, ±3, ±5 only). | `entire-report.txt:187` — `Agent generates deterministic lockfile JSON …, +4`. `docs/guidelines/rubrics.md:52-53` — "Forbidden: ±4". | Change `+4` to `+3` or `+5` on the platform rubric (total stays ≤40). |

*No other real blockers found on manual re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Fixed-point/retraction rule missing from agent-visible contract (ChatGPT High) | **Agree** | `resolver-contract.md:35-48` has yanked/pre-release/highest-version rules only; no fixed-point or stale-constraint retraction. Test at `test_outputs.py:224-258`. |
| 2 | Pre-release ordering still missing (prior reviewer in `entire-report.txt:1`) | **Disagree** (resolved) | `resolver-contract.md:37-39` — "Pre-release versions sort below their corresponding final release". |
| 3 | Verifier is strong overall (ChatGPT Medium/Low) | **Agree** | 11 integration tests with dynamic registries; `entire-report.txt:99-137` test-quality review ROBUST. Not a blocker. |
| 4 | Rubric typo `offline-crate-ledgerfor` (ChatGPT Low) | **Agree** | `entire-report.txt:189`. Low severity; not a blocker. |
| 5 | Rubric within point cap, outcome-based (ChatGPT) | **Agree** | `./scripts/terminus rubric-points` → 37/40 PASS. Not a blocker. |
| 6 | Dockerfile digest pinning acceptable (ChatGPT) | **Agree** | `environment/Dockerfile:1` — `rust:1.85-slim@sha256:9f841bbe…`. |
| 7 | LLMaJ: specs sufficient, failures are implementation errors (`entire-report.txt:67-68`) | **Partially agree** | Correct for most behaviors and for agents that infer algorithm from source; **disagree** for reselection/retraction — that semantics is tested but not stated in contract or instruction beyond vague bug list. |
| 8 | Instruction sufficiency analysis PASS (`entire-report.txt:45`) | **Partially agree** | Instruction + contract cover three named bugs and output schemas; **gap** remains on fixed-point retraction rule driving hardest test. |
| 9 | Non-milestone task uses milestone rubric format (`# Rubric 1`) | **Disagree as blocker** | `docs/guidelines/rubrics.md:66` — "`# Rubric 1` optional; no `# Rubric 2+`" for non-milestone. Single header is valid. |
| 10 | Audit #14 unpinned pip | **Disagree** | `environment/Dockerfile:16-18` — `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`. False positive from line-continuation parse. |
| 11 | Audit #36 negative rubric phrasing | **Disagree** | `entire-report.txt:191` is a **negative** criterion (`-5`); negative phrasing is correct. Audit PASS on re-read. |
| 12 | Audit #41 stray `audit-report.md` | **Disagree as task blocker** | File generated by `./scripts/terminus audit` during review; not part of author submission zip. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~4 sentences, bug-fix framing | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Conversational bug report, not synthetic spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no tables/headers in instruction | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States goal + doc refs only | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | No algorithm walkthrough in instruction | `instruction.md` |
| 6 | CHECK | No design-doc tables in instruction | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified goal | Clear bugs + normative doc paths | `instruction.md:1-5` |
| 8 | CHECK | Interesting | Realistic offline resolver bug-fix | — |
| 9 | UNCHECK | Unique vs corpus | Cannot verify against TB2/TB3 index from artifacts | — |
| 10 | CHECK | Absolute paths | `/app/docs/resolver-contract.md`, `/app/docs/lock-schema.md` | `instruction.md:3` |
| 11 | CHECK | Task name not in instruction | No `offline-crate-ledger` string | `instruction.md` |
| 12 | CHECK | No canary strings | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline resolver; `allow_internet=false` | `task.toml:23`, `environment/` |
| 14 | CHECK | Pip deps pinned with == | Both pytest packages use `==` | `environment/Dockerfile:17-18` |
| 15 | CHECK | Base image digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Build context within environment/ | COPY only Cargo, src, docs, README | `environment/Dockerfile` |
| 17 | CHECK | No ground-truth answers in env | Buggy starter code only; docs are contracts not solutions | `environment/src/resolve.rs` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime install | pytest in Dockerfile; test.sh only builds Rust + pytest | `environment/Dockerfile:15-18`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed — Docker daemon permission denied in review env | — |
| 22 | CHECK | Oracle needs no internet | `cargo build --locked` only | `solution/solve.sh`, `tests/test.sh:16` |
| 23 | CHECK | Oracle is real implementation | Full resolver with fixed-point loop in heredoc | `solution/solve.sh:272-354` |
| 24 | CHECK | test.sh writes reward.txt on pass/fail | Canonical 0/1 block | `tests/test.sh:9-10,33-37` |
| 25 | CHECK | Same verifier logic for oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh` |
| 27 | UNCHECK | Tests aligned with instructions | `test_version_reselection_*` tests retraction not stated in contract/instruction | `test_outputs.py:224-258`, `resolver-contract.md` |
| 28 | CHECK | Tests check correctness | Assert versions, exit codes, JSON structure, lock preservation | `tests/test_outputs.py` |
| 29 | CHECK | Behavior tests not implementation grep | Black-box CLI invocation | `tests/test_outputs.py:23-39` |
| 30 | CHECK | No brittle string matching | Parsed JSON + targeted byte checks | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | All 11 tests documented | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:191-194` |
| 33 | UNCHECK | Rubric scores from {±1,±2,±3,±5} | One `+4` line | `entire-report.txt:187` |
| 34 | CHECK | Agent …, ±N format | 15 properly formatted lines | `entire-report.txt:179-194` |
| 35 | CHECK | Rubric detailed; positive ≤40 | 37 positive points | `terminus rubric-points` |
| 36 | CHECK | Positive criteria use positive language | Negatives correctly phrased; positives affirmative | `entire-report.txt:179-190` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:179-194` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | `entire-report.txt:179-194` |
| 39 | CHECK | Rubric no oracle/NOP refs | None | `entire-report.txt:179-194` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary submission files | No jobs/, stray README in task root | task root |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | CHECK | Other metadata present | category, languages, timeouts, tags | `task.toml` |
| 44 | CHECK | Tags/category/languages match | Rust CLI resolver | `task.toml:6-12` |
| 45 | CHECK | Difficulty field present | `difficulty=medium` (vs platform hard — informational) | `task.toml:6`, `entire-report.txt:16-22` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones=0` | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:5` |
| 51 | CHECK | Solution not accessible in env | `.dockerignore` excludes solution/ | `environment/.dockerignore:4` |
| 52 | CHECK | Agent cannot trivially cheat | Ephemeral tmp_path fixtures; must fix Rust binary | `tests/test_outputs.py` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤80% | `entire-report.txt:21-22` |
| 55 | UNCHECK | Not too hard/unfair | Retraction semantics tested but undocumented — contributed to 4/4 near-miss trials on hardest test | `entire-report.txt:57-83` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 9, 21, 27, 33, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Feature-gated deps must appear in lockfile | `test_aliases_features_*`, `test_alias_feature_union_*` | covered | `instruction.md:1`; tests pass feature propagation |
| Yanked versions excluded | `test_yanked_versions_*` | covered | `instruction.md:1`; `resolver-contract.md:37` |
| Conflicts must not overwrite lock | `test_conflicting_*`, `test_feature_conflict_*`, `test_output_failure_*` | covered | `instruction.md:1`; `resolver-contract.md:15-16` |
| Pre-release sorts below final | `test_yanked_versions_*` | covered | `resolver-contract.md:37-39` |
| Deterministic byte-identical output | `test_repeated_success_*` | covered | `resolver-contract.md:46-47` |
| Parent dirs created on success | `test_success_from_absent_lock_*` | covered | `resolver-contract.md:47-48` |
| Alias → canonical package merge | `test_aliases_features_*` | partial | Workspace format in contract; feature/constraint merge implied by tests not spelled out |
| Transitive + iterative resolution | `test_aliases_features_*`, `test_feature_conflict_*` | gap | Contract lacks propagation/iteration rules; instruction names feature bug only |
| Version reselection drops stale deps | `test_version_reselection_*` | **gap** | Not in contract or instruction; 6/10 agent pass |
| `dep`/`feature` line formats with optional `features=` on deps | multiple tests | partial | Parser supports; contract mentions lines exist (`resolver-contract.md:32-33`) but not full grammar |
| Lock/report JSON schema | all success/conflict tests | covered | `lock-schema.md` |
| Exit codes 0/1/2 | multiple tests | covered | `resolver-contract.md:12-16` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-11, spec alignment |
| `environment/docs/resolver-contract.md` | Blocker 1, claims 1-2, #27, #55 |
| `environment/docs/lock-schema.md` | #27 partial, schema alignment |
| `environment/Dockerfile` | #14-15, #20, claim 6/10 |
| `environment/src/resolve.rs` | Buggy starter (monotonic constraints) |
| `tests/test_outputs.py` | Blocker 1, #27-31, spec alignment |
| `tests/test.sh` | #20, #24-26 |
| `solution/solve.sh` | #22-23 (static) |
| `task.toml` | #44-45, #46-49 N/A |
| `entire-report.txt` | #32-39, #54, agent stats, rubric, external claims |
| `docs/guidelines/rubrics.md` | #33, claim 9 |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: offline-crate-ledger ===
Summary: 0 error(s), 1 warning(s), 1 info
WARNING: pinned_dependencies — pip line-continuation heuristic (false positive; packages are ==-pinned)
INFO: submission-diversity — non-milestone task
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | — |
| terminus-claude-opus-4-8 | 20% (1/5) | — |
| oracle | 100% (3/3) per report | not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | medium |
| Platform classified | hard |
| Tier match (#45) | informational only — not a blocker |

**Hardest test:** `test_version_reselection_drops_dependencies_from_no_longer_selected_version` — 6/10 passes (`entire-report.txt:42`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Rust resolver; report matches task |
| 1 Instruction | ☑ | Concise bug-fix; points to contract docs |
| 2 Environment | ☑ | Digest-pinned Rust image; tmux+asciinema; pip pinned |
| 3 Oracle | ☐ | Not executed (Docker); static review PASS |
| 4 Verifiers | ☑ | 11 black-box tests; canonical reward block |
| 5 Metadata | ☑ | Complete; category/tags appropriate |
| 6 Rubric | ☑ | 37/40 positives; `+4` format violation; `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Near-miss pattern confirms retraction as key gap |
| 8 Novelty & fairness | ☑ | Multi-rule resolver; no obvious cheat path |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid resolver task — the verifier suite is thorough, the environment is clean with a pinned Rust base, and difficulty calibration looks right (agents struggle on the subtle parts without being impossible). Pre-release ordering in `resolver-contract.md` is a nice improvement. Two things before accept: please add an explicit rule that resolution iterates to a fixed point and must drop/rebuild constraints and feature-driven dependencies whenever a package's selected version changes (stale deps from a superseded version cannot linger). Also change the one `+4` rubric line to `+3` or `+5` — only ±1/2/3/5 are allowed.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Time Based Tests | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Uses Internet | no | — |
| Agent Timeout | no | — |
| Wrong Coding Language | no | — |
| Canary Strings | no | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |
