# Terminus Review Report: `nftables-atomic-rollback-journal`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong Go debugging task with digest-pinned offline env, realistic broken stubs, independent Python verifier, and oracle pass (1.0). Agent runs show systematic near-misses (avg ~5.1/7 tests) driven by three verifier-critical semantics not spelled out in `instruction.md`: counter formula (`len(canonical_rows)` vs `max(seq)`), replay dedup key/winner rule, and entry list sort order. External automated review’s non-canonical-base-image claim is incorrect — the Dockerfile uses the sanctioned `debian:bookworm-slim` digest. Revise instruction only; no env/oracle rebuild required.

**Insights (concise):**

- ChatGPT’s three High spec-gap claims are confirmed with `instruction.md` ↔ `tests/test_outputs.py:_expected_report` line evidence; agent failure analysis in `entire-report.txt` correlates (5/8 trials fail `test_spill_rows_are_ordered_before_hashing` on counter).
- `debian:bookworm-slim@sha256:4724b8cc…` matches the canonical list in `docs/guidelines/dockerfxile.md` — disagree with `entire-report.txt` “non-canonical base” blocker.
- `go.mod` declares Go 1.21 while Dockerfile installs `golang-go=2:1.19~1`; oracle builds — Low/informational only.
- Platform rubric in `entire-report.txt` uses optional `# Rubric 1` (valid for non-milestone per `docs/guidelines/rubrics.md`); one criterion (“deduplication by Seq”) misstates verifier dedup — fix on platform, not a task-folder blocker.
- Worst-model 40% (medium tier) vs declared `hard` is defensible (best-model 0%); not a revision blocker per `docs/guidelines/difficulty.md`.
- Automated `terminus review` false positives on #14 (pip is `==`-pinned) and #31 (all seven tests have docstrings).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Top-level `counter` formula is ambiguous. Instruction says keep the greatest values from metadata/manifest/records; agents reasonably infer `max(seq)` or max counter fields. Verifier requires `max(layout.counter, persisted.counter, len(canonical_rows))`. | `instruction.md:9` (“greatest values implied by … replayed records”); `tests/test_outputs.py:110` (`counter = max(..., len(rows))`); `solution/solve.sh:221-223` (`if len(rows) > auth.Counter { auth.Counter = len(rows) }`); `entire-report.txt:62-64,84-85` | State explicitly: `counter = max(layout manifest counter, persisted epoch.json counter, count of canonical journal rows after dedup)`. |
| 2 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Replay duplicate contract lacks dedup key and winner rule. Instruction only says duplicates must not change the canonical view. Verifier dedups on `(seq, run_id, phase, rule_id, action)` and keeps the row with highest `(epoch, source_order)`; extra fields (`source`, `priority`, `mark`, full JSON) are not part of the key. | `instruction.md:5` (“duplicate replay rows must not change the canonical view”); `tests/test_outputs.py:43-54` (`key = (seq, run_id, phase, rule_id, action)`; `rank = (epoch, source_index)`); `solution/solve.sh:98-99` (`journalKey` same five fields); `entire-report.txt:63,86-87` | Document the exact duplicate key tuple, journal file merge order (`batch.json`, `batch.replay.json`, `batch.shadow.json`, `batch.spill.json`), and `(epoch, source_order)` winner tie-break. |
| 3 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | Report `entries` list sort order is enforced by full JSON equality but not specified. Verifier sorts by `(rule_id, epoch, action)`. | `instruction.md:3` (fields only, no ordering); `tests/test_outputs.py:144` (`entries.sort(key=lambda e: (e["rule_id"], e["epoch"], e["action"]))`); `tests/test_outputs.py:228,269` (`assert report == _expected_report(...)`); `solution/solve.sh:252-259`; `entire-report.txt:64,88` | Add normative ordering: entries sorted by `(rule_id, epoch, action)` (runs by `(run_id, phase)`, checkpoints by `(run_id, phase)` if documenting full contract). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Counter formula ambiguous: instruction implies max(seq); verifier uses `max(layout, persisted, len(canonical_rows))` (ChatGPT / `entire-report.txt:62-64,84-85`) | **Agree** | `instruction.md:9`; `tests/test_outputs.py:110`; oracle `solution/solve.sh:221-223` |
| 2 | Dedup key needs exact tuple `(seq, run_id, phase, rule_id, action)` with `(epoch, source_order)` winner; extra fields excluded (ChatGPT / `entire-report.txt:63,86-87`) | **Agree** | `instruction.md:5`; `tests/test_outputs.py:46-50`; `solution/solve.sh:58-64,98-99` |
| 3 | Entry sort order `(rule_id, epoch, action)` not documented (ChatGPT / `entire-report.txt:64,88`) | **Agree** | `instruction.md:3`; `tests/test_outputs.py:144`; equality asserts at `:228`, `:269` |
| 4 | Non-canonical base image must switch to `ghcr.io/.../go-1-23` (`entire-report.txt:154-180`) | **Disagree** | `environment/Dockerfile:1` uses `debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` — same digest as canonical entry in `docs/guidelines/dockerfxile.md:22` |
| 5 | `go.mod` Go 1.21 vs Dockerfile `golang-go` 1.19 mismatch (`entire-report.txt:187-206`) | **Partially agree** | `environment/go.mod:3` (`go 1.21`); `environment/Dockerfile:11` (`golang-go=2:1.19~1`); oracle pass confirms no current build break — Low only |
| 6 | LLMaJ `behavior_in_task_description` PASS (`entire-report.txt:115`) | **Partially agree** | Schema/behavior mostly named, but counter/dedup/entry-order semantics above are tested via `_expected_report` yet absent from `instruction.md` |
| 7 | LLMaJ `Task Instruction Sufficiency` FAIL — systematic spec gaps (`entire-report.txt:48,80-90`) | **Agree** | Correlates with blockers 1–3 and per-test failure rates (`test_spill_rows_are_ordered_before_hashing`: 2/10) |
| 8 | Platform rubric uses milestone header on non-milestone task (`entire-report.txt:281-298`) | **Disagree** (not a format violation) | `task.toml:9` (`number_of_milestones = 0`); `docs/guidelines/rubrics.md:60` (“`# Rubric 1` optional” for non-milestone) |
| 9 | Rubric criterion “deduplication by Seq” (`entire-report.txt:288`) | **Agree** (misaligned, platform-only) | Verifier uses 5-tuple key at `tests/test_outputs.py:46`, not Seq-only; rubric not in task folder — author should fix on platform |
| 10 | Automated review #14 unpinned pip / #31 missing docstrings (`review-report.md` baseline) | **Disagree** | `environment/Dockerfile:24-25` (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); all seven `test_*` functions have docstrings at `tests/test_outputs.py:223-333` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Three short paragraphs | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineering brief, not spec tables | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose only | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcome/commands, not patch steps | `instruction.md:1-2` |
| 5 | CHECK | No hints/solving strategies | Describes contract, not file-level fix map | `instruction.md` |
| 6 | CHECK | No design-doc tables | None present | `instruction.md` |
| 7 | UNCHECK | Well specified | Counter/dedup/entry-order gaps (#27 blockers) | `instruction.md:5,9`; `tests/test_outputs.py:110,144` |
| 8 | CHECK | Interesting | Realistic journal/replay audit debugging | Task design |
| 9 | CHECK | Unique | nftables journal replay theme; no duplicate in repo | Task content |
| 10 | CHECK | Absolute paths | `/app/environment`, `/app/output/audit_report.json` | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | Name absent | `instruction.md` |
| 12 | CHECK | No canary string | None | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline fixtures only | `environment/` |
| 14 | CHECK | Pip pinned with `==` | pytest pins present | `environment/Dockerfile:24-25` |
| 15 | CHECK | Base image digest-pinned | `@sha256:…` on FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment | COPY paths under build context | `environment/Dockerfile:27-43` |
| 17 | CHECK | No ground truth in env | Stubs broken; overview documents public digest format only | `environment/docs/overview.md:38` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No docker-compose | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:22-25`, `tests/test.sh` |
| 21 | CHECK | Oracle passes | Mean reward 1.0 | `./scripts/terminus oracle` 2026-06-27 |
| 22 | CHECK | Oracle no internet | solve.sh writes Go sources and builds locally | `solution/solve.sh` |
| 23 | CHECK | Oracle derives via pipeline | Implements journal load, dedup, reconcile, emit | `solution/solve.sh:50-305` |
| 24 | CHECK | reward.txt on pass/fail | Canonical block | `tests/test.sh:6-20` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh:16-19` |
| 27 | UNCHECK | Tests aligned with instructions | Hidden counter/dedup/entry-order semantics | Blockers 1–3 |
| 28 | CHECK | Tests check correctness | Full `_expected_report` equality | `tests/test_outputs.py:228` |
| 29 | CHECK | Behavior not implementation grep | Output JSON vs recomputed expected | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle string-only | Structural + hash correctness | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All seven tests documented | `tests/test_outputs.py:223-333` |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric in task folder | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric `Agent …, ±N` format | N/A | — |
| 35 | UNCHECK | Rubric detailed/precise | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no instruction.md refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | Task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | Task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | timeouts, category, tags present | `task.toml` |
| 44 | CHECK | Tags/languages/category match | Go/bash, system-administration, nftables | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches rates | `hard` defensible: best-model 0%, worst 40% | `entire-report.txt:24-25`; `docs/guidelines/difficulty.md` |
| 46 | UNCHECK | Milestone steps/ layout | N/A (`number_of_milestones = 0`) | `task.toml:9` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked in image | `.dockerignore` excludes `tests/` | `environment/.dockerignore:15` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:14` |
| 52 | CHECK | No trivial input mutation cheat | Agent must fix Go pipeline; output derived | `tests/test_outputs.py` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 40% ≤ 80% | `entire-report.txt:24-25` |
| 55 | UNCHECK | Not unfair / unavailable info | Undocumented counter/dedup/entry order forces inference from hidden verifier logic | Blockers 1–3; `entire-report.txt:107-111` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Output `/app/output/audit_report.json` with schema fields | All tests + `_assert_report_shape` | covered | `instruction.md:1,3`; `tests/test_outputs.py:175-206` |
| Phases `apply` / `settle`; no boolean verdict fields | All tests | covered | `instruction.md:3`; `tests/test_outputs.py:209-217` |
| sha256 64-char lowercase hashes | All tests | covered | `environment/docs/overview.md:38`; `tests/test_outputs.py:186` |
| Companion journals + malformed primary recovery | `test_corrupt_primary_batch_uses_replay_companions` | covered | `instruction.md:5`; `tests/test_outputs.py:235-254` |
| Duplicate replay idempotent canonical view | `test_duplicate_replay_is_idempotent` | **gap** (dedup key/winner unstated) | `instruction.md:5`; `tests/test_outputs.py:43-54,310-329` |
| Later row replaces rule state incl. undo | Gate/depot/yard tests via `_rules` | covered | `instruction.md:5`; `tests/test_outputs.py:61-70` |
| Empty phase zero spans | `test_empty_phase_records_still_have_deterministic_checkpoint` | covered | `instruction.md:5`; `tests/test_outputs.py:332-356` |
| Epoch = max(layout, persisted, record epochs) | All `_expected_report` | covered | `instruction.md:9`; `tests/test_outputs.py:109` |
| Counter = max(layout, persisted, len(canonical_rows)) | `test_spill_rows_are_ordered_before_hashing`, lane probe | **gap** | `instruction.md:9`; `tests/test_outputs.py:110,257-270` |
| Entry order deterministic | Full equality asserts | **gap** | `tests/test_outputs.py:144`; `instruction.md:3` |
| Cross-profile isolation | `test_cross_profile_state_does_not_bleed` | covered | `tests/test_outputs.py:273-285` |
| Lane probe green ≠ audit authority | `test_laneprobe_green_is_not_audit_authority` | covered | `instruction.md:1-2`; `tests/test_outputs.py:288-307` |
| Spill/out-of-order stability | `test_spill_rows_are_ordered_before_hashing` | covered (ordering by seq in canonical rows) | `instruction.md:5`; `tests/test_outputs.py:257-270` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | Blockers 1–3, #7, #27, #55, spec table |
| `tests/test_outputs.py` | Blockers 1–3, #27-31, spec table |
| `solution/solve.sh` | Blockers 1–2, #21-23, oracle alignment |
| `environment/Dockerfile` | #14-15, base-image adjudication |
| `environment/go.mod` | Go version note |
| `environment/docs/overview.md` | #17, hash format |
| `environment/.dockerignore` | #50-51 |
| `task.toml` | #44-49, metadata |
| `entire-report.txt` | Agent stats, external claims |
| `docs/guidelines/dockerfxile.md` | Base image adjudication |
| `docs/guidelines/rubrics.md` | Rubric format adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: nftables-atomic-rollback-journal ===
Summary: 0 error(s), 2 warning(s), 2 info
Task type detected: regular
Warnings: pinned_dependencies (false positive on pip), informative_test_docstrings (module-level only)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | All other failures |
| terminus-claude-opus-4-8 | 40.0% (2/5) | 1 timeout, 2 other |
| oracle | 100.0% (3/3 platform; 1/1 local) | Local oracle 1.0 |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% supports hard) |

Per-test pass rates (`entire-report.txt:38-45`): `test_spill_rows_are_ordered_before_hashing` 2/10 — primary counter-formula signal.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; `nftables-atomic-rollback-journal`; matches report |
| 1 Instruction | ☑ | Three High spec gaps confirmed |
| 2 Environment | ☑ | Canonical debian digest; offline; tmux/asciinema; no solution/tests COPY |
| 3 Oracle | ☑ | Passes locally; implements same semantics as verifier |
| 4 Verifiers | ☑ | 7 behavior tests; reward block OK; no runtime installs |
| 5 Metadata | ☑ | `number_of_milestones = 0`; category/tags fit |
| 6 Rubric | N/A | No `rubric.txt` in repo; platform rubric reviewed informally |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL aligns with blockers; hack check clean |
| 8 Novelty & fairness | ☑ | Multi-file Go pipeline; unfair only where spec silent |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task overall — the offline Go environment, crash/replay fixtures, lane-probe separation, and end-to-end verifier design are all in great shape, and the oracle passes cleanly. The one thing holding this back is a few audit-report semantics that the tests enforce strictly but the instruction leaves implicit. Please spell out that top-level `counter` is `max(layout counter, persisted counter, number of canonical rows after dedup)` — not `max(seq)`; that duplicate journal rows are keyed by `(seq, run_id, phase, rule_id, action)` with the highest `(epoch, source_order)` winning; and that `entries` are sorted by `(rule_id, epoch, action)`. Those are small documentation additions and should unblock agents that are already passing 6/7 tests. Optional cleanup: align `go.mod` with the installed Go toolchain (1.19 vs 1.21). On the platform rubric, `# Rubric 1` alone is fine for a non-milestone task, but change “deduplication by Seq” to match the 5-field replay key above.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2, 3 |
| Test Alignment/Coverage Issues | yes | 1, 2, 3 |
| Environment | no | — |
| Pinning Issues | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no (N/A in repo) | — |
| Task Difficulty | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus review nftables-atomic-rollback-journal --report entire-report.txt`; oracle run 2026-06-27._
