# Terminus Review Report: offline-service-reconciler

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn (0 errors, `.dockerignore` warning only) |
| **Oracle** | pass (3/3 from submission export) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** none

**Decision (concise):** Accept. No High-severity blockers after re-auditing against `entire-report.txt`, ChatGPT, Platform Changelog, and the **Submission Checklist**. Spec↔test coverage, oracle/NOP/agent rates, and Dockerfile posture all clear the reviewer High bar. `#44` is Medium only. **Platform rubric missing from export → #32–39 N/A (not Revise):** Submission Checklist tells authors to include a UI rubric, but the Reviewer Checklist UI + export-format rules explicitly N/A those boxes when the platform rubric section is absent.

**Insights (concise):**

- **Author vs reviewer on platform rubric:** Submission Checklist says every submission *should* include an edited Snorkel UI rubric (≥3 negatives). That is an **author pre-submit** duty. Reviewer rules still say: if the export has **no** platform rubric body, mark #32–39 **N/A** — do not invent a High Rubric fail from emptiness. Task artifacts themselves stay Acceptable.
- **Jun 29 platform gate:** do **not** retag to blocked `debugging` / `software-engineering`; keep `system-administration` for this in-review non-milestone task.
- `tool_specific` unfit; `codebase_size = "small"` correct (28 env files excl. Dockerfile).
- Spec-gap “freshest-only candidates” claim is false; all 16 `test_*` have docstrings; LLMaJ/CI quality items from the Submission Checklist that appear in the export are PASS.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept; no High/Medium blockers (ChatGPT) | Agree | Re-audit: no High findings; only Medium metadata fit (#44). Oracle 3/3, NOP 0%, worst-model 60% ≤80%. |
| 2 | Dockerfile digest-pinned; `allow_internet=false`; no runtime installs (ChatGPT) | Agree | `environment/Dockerfile:1` `@sha256:01f42367…`; `task.toml` `allow_internet = false`; `tests/test.sh` only runs pytest + reward write. |
| 3 | Verifier covers authority, per-field, digest, idempotency, signature, alias, metamorphic checks (ChatGPT) | Agree | `tests/test_outputs.py` `test_g01`–`test_g16` + helpers `_expected_full`, `_field_level`, `_signature_gating`, `_override_tracks`, `_deletion_tracks`. |
| 4 | Missing Agent-generated / platform rubric is optional / not Needs Revision (ChatGPT) | Agree (with nuance) | **Author workflow (Understanding Rubrics / Submission Checklist):** generate via CI checkbox → edit textbox → **uncheck** regenerate before Send to Reviewer; refine synthetic draft; ≥3 negatives; 10–40 positive pts (non-milestone); `Agent …, ±N` with ±1/2/3/5 only; no pytest/meta `instruction.md` checks; non-milestone = flat list (`# Rubric 1` optional, no `# Rubric 2+`). **Reviewer side:** those quality rules apply **when a platform rubric body exists**. Export has none (`entire-report.txt` ends ~L301). → #32–39 **N/A / UNCHECK**, not High Revise for emptiness. Soft: author should still complete UI rubric if they revise. |
| 5 | Task Instruction Sufficiency FAIL; freshest-only candidate reading is a documentation gap (entire-report analysis) | Disagree | `rules_contract.md:77-82` and `run_contract.md:38-40` require candidates for **every** claim considered across surfaces. `_candidate_counts` (`test_outputs.py:208-217`) expects all `r1` files + optional r2/r3. Freshest-only is agent misread, not missing spec. |
| 6 | Signature-gating failures are implementation gaps, not spec gaps (entire-report) | Agree | `rules_contract.md:33-35`; buggy `g_extract_k.sh:16-19` calls `verify_sig.sh` then always emits r2 (aborts under `set -e`); oracle patch wraps in `if`. |
| 7 | Non-canonical Python base for bash task (Harbor REVIEW REPORT warning) | Disagree as blocker | Image is the sanctioned Python 3.13 digest; needed for baked pytest. Cosmetic language/base pairing only. |
| 8 | RECOMMENDATION READY TO USE / test quality ACCEPT (Harbor reports) | Agree | Aligns with artifact re-audit. |
| 9 | LLMaJ all quality checks PASS (entire-report) | Agree | Spot-checked: schemas in `run_contract.md`, no tests/solution in image (`COPY . /app/environment`), metamorphic anti-cheat present. |
| 10 | Auto `terminus review` blocker: 1 test missing docstring (#31) | Disagree | AST check: all 16 `test_g*` have docstrings (`test_outputs.py:469-619`). `audit-report.md` #31 PASS. |
| 11 | Audit #44 FAIL: category should be `debugging` / `software-engineering` | Partially agree | Thematic fit is debugging-like, but **Jun 29 changelog** blocks net-new submissions in `debugging` / `software-engineering`. Current `system-administration` avoids the blocked set; do not force a retag. Remaining Medium: imperfect category + unfit `tool_specific`. |
| 12 | `subcategories = ["tool_specific"]` fits (task.toml implicit) | Disagree | `docs/task-subtypes.md`: tool_specific = Blender/FFmpeg/Graphviz-class SDKs. Bash fleet reconciliation is not tool_specific. Folded into #44 Medium. |
| 13 | Non-milestone task wrongly uses milestone rubric format (user check) | N/A / pass | No platform rubric; Jun 3: non-milestone = flat `Agent …, ±N` (`# Rubric 1` optional, no `# Rubric 2+`). Nothing to reject. |
| 14 | Jun 29: new milestones + debugging/SE categories blocked (Platform Changelog) | Agree — not a blocker here | Task is non-milestone (`number_of_milestones = 0`) and category is `system-administration`, not a blocked label. Already in review queue (exempt tone for any thematically similar work). |
| 15 | Jun 12: final runtime base must be canonical or justified (Changelog) | Pass | `python:3.13-slim-bookworm@sha256:01f42367…` is on the sanctioned Python list; needed for baked pytest. |
| 16 | May 15 / May 27: `allow_internet=false`; no runtime installs; digest pins (Changelog) | Pass | `task.toml` + Dockerfile pin + `test.sh` pytest-only. |
| 17 | May 27: reward block is canonical end; no trailing `exit` required | Pass | `tests/test.sh` ends at reward write; do not flag missing exit. |
| 18 | May 27 / May 19: no hidden walkthroughs / no AI scaffolding filenames | Pass | Contracts read as engineering specs; no `CLAUDE.md` / `skills.md` in env. |
| 19 | Submission Checklist — required files / non-milestone layout | Pass | `task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/test.sh`, `tests/test_outputs.py` present |
| 20 | Submission Checklist — absolute paths, named outputs, schemas | Pass | Paths `/app/...`; outputs named; schemas in `r6/run_contract.md` |
| 21 | Submission Checklist — difficulty &lt;80% worst-model | Pass | Worst-model 60% (`entire-report.txt`); medium tier |
| 22 | Submission Checklist — oracle + LLMaJ quality set | Pass | Oracle 3/3; export LLMaJ all ✓ for listed checks |
| 23 | Submission Checklist — anti-cheat / behavior tests / docstrings | Pass | Metamorphic g09/g10; behavior asserts; all `test_*` docstrings |
| 24 | Submission Checklist — CI/dockerfile/test.sh expectations | Pass | Digest pins, sanctioned Python base, no tests in image, reward block, no runtime installs; only soft warn: missing `.dockerignore` |
| 25 | Submission Checklist / Understanding Rubrics — include + refine platform rubric | Author gap only | Expected author path: generate → edit → uncheck regen → submit with edited text. Export textbox empty → reviewer cannot score #32–39; **not** applied as “failed ≥3 negatives / failed format” High. Soft note only. |
| 26 | Rubrics Guidelines — positive cap / format / excludes (conditional) | N/A here | Cannot score >40, ±4, pytest/meta lines, or milestone `# Rubric 2+` without a body. Non-milestone genuinely has no rubric text to violate those rules. |

### Submission Checklist + Rubrics Guidelines matrix (author ↔ this review)

| Checklist area | Status | Notes |
|----------------|--------|-------|
| Task design (clarity, abs paths, outputs, schemas) | ✓ | `instruction.md` + `r6` contracts |
| Required non-milestone files | ✓ | Complete regular layout |
| Difficulty &lt;80% worst | ✓ | 60% Claude |
| Oracle passes | ✓ | 3/3 |
| LLMaJ set in export | ✓ | All listed PASS |
| Anti-cheat / behavior / docstrings | ✓ | Metamorphic + AST docstrings |
| Platform rubric in UI (generate/edit/uncheck regen) | ✗ in export | Author *should* per Understanding Rubrics + Submission Checklist; reviewer #32–39 = **N/A**, not Revise |
| If rubric existed: ≥3 negatives, 10–40 +, format, no ±4, no pytest/meta | N/A | No body to lint; authoring checklist not enforceable as High |
| Warnings (`.dockerignore`) | warn | validate flagged; Low / fix-if-touching |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~341 words; 4 short prose blocks + one command fence; contracts offloaded | `instruction.md` |
| 2 | CHECK | Natural prompt, not synthetic spec | Engineer incident tone; no “You are an expert…” | `instruction.md` |
| 3 | CHECK | No excessive markdown | No `##`/`###`; light bold; one code fence | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | What/where only; no fix walkthrough | `instruction.md` |
| 5 | CHECK | No hints / solve strategies | Points to contracts, not which module to patch | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Entry, outputs, contracts, constraints named | `instruction.md`, `r6/*.md` |
| 8 | CHECK | Interesting / useful | Realistic airgapped fleet inventory reconciliation | `instruction.md` |
| 9 | UNCHECK | Unique vs corpus | Full TB2/TB3/E1 uniqueness not verifiable locally | — |
| 10 | CHECK | Absolute paths | Actionable paths are `/app/...`; `r1/` shorthand only after `/app/environment` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | Name absent | `instruction.md` |
| 12 | CHECK | No canary string | No canary patterns | `instruction.md` |
| 13 | CHECK | No web fetch in env | No curl/wget fetch of task content | `environment/Dockerfile` |
| 14 | CHECK | Pip pins with `==` | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:12` |
| 15 | CHECK | FROM digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context only environment/ | `COPY . /app/environment` from env build context | `environment/Dockerfile:15` |
| 17 | CHECK | No solution/ground truth in env | Contracts define rules, not golden inventory; patches only in `solution/` | `environment/`, `solution/` |
| 18 | CHECK | No privileged/dangerous ops | No docker.sock / SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose mounts | No docker-compose | task layout |
| 20 | CHECK | Verifier deps in image; no test.sh installs | venv + pip in image; test.sh pytest only | `Dockerfile`, `tests/test.sh` |
| 21 | CHECK | Oracle consistent | Oracle 100% (3/3) | `entire-report.txt:30` |
| 22 | CHECK | Oracle offline | Patches + local pipeline only | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction | Targeted patches then real pipeline regenerate | `solve.sh`, `*.patch` |
| 24 | CHECK | reward.txt on success/fail | Binary write after pytest | `tests/test.sh:10-14` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test.sh`, `test_outputs.py` |
| 26 | CHECK | Binary rewards | `echo 1` / `echo 0` only | `tests/test.sh` |
| 27 | CHECK | Tests align with instructions | Requirements map to g01–g16; “freshest-only” claim contradicted by contracts | §5 table |
| 28 | CHECK | Correctness not format-only | Resolution, digests, metamorphic, signature fallback | `test_outputs.py` |
| 29 | CHECK | Behavior not implementation grep | Runs pipeline; asserts artifacts | `test_outputs.py` |
| 30 | CHECK | No brittle exact-string traps | Structured JSON / counts / roles | `test_outputs.py` |
| 31 | CHECK | Informative names/docstrings | All 16 `test_*` have docstrings (AST) | `test_outputs.py:469-619` |
| 32 | UNCHECK | ≥3 negative rubric criteria | N/A — no platform rubric in export | `entire-report.txt` |
| 33 | UNCHECK | Rubric scores in allowed set | N/A — no rubric | — |
| 34 | UNCHECK | `Agent …, ±N` format | N/A — no rubric | — |
| 35 | UNCHECK | Detailed precise criteria | N/A — no rubric | — |
| 36 | UNCHECK | Positive language | N/A — no rubric | — |
| 37 | UNCHECK | No /tests/ references | N/A — no rubric | — |
| 38 | UNCHECK | No task.toml/instruction refs | N/A — no rubric | — |
| 39 | UNCHECK | No oracle/NOP mentions | N/A — no rubric | — |
| 40 | CHECK | Required files present | Regular layout complete | task root |
| 41 | CHECK | No stray parent junk | No jobs/README/data noise in task dir | task root |
| 42 | CHECK | author fields | Present | `task.toml:5-6` |
| 43 | CHECK | Other required metadata | category, tags, codebase_size, timeouts, milestones=0 | `task.toml` |
| 44 | UNCHECK | Tags/languages/category applicable | `tool_specific` unfit; category is thematically loose vs bug-fix work but **must stay off** blocked `debugging`/`software-engineering` (Jun 29). `languages`/`tags`/`codebase_size` OK | `task.toml`, taxonomy + Platform Changelog Jun 29 |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"` present; declared vs platform medium is informational only | `task.toml`, `entire-report.txt` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | — |
| 48 | UNCHECK | test_mN.py per milestone | N/A | — |
| 49 | UNCHECK | Milestone test scoping | N/A | — |
| 50 | CHECK | Tests not in image | No `COPY tests/` | `Dockerfile:15` |
| 51 | CHECK | Solution inaccessible in env | Solution not copied; env has buggy sources only | `Dockerfile`, `solution/` |
| 52 | CHECK | Cannot trivially pass by mutating inputs | Metamorphic tests restore overrides; baseline immutability checked; expected oracle derives from live surfaces | `test_g07`, `test_g09`, `test_g10` |
| 53 | CHECK | Git clones pinned | No git clone | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:25-26` |
| 55 | CHECK | Not unfair / not luck-based | Contracts ship in env; signature rule documented; agent miss is implementation | `r6/rules_contract.md`, failure analysis |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 32, 33, 34, 35, 36, 37, 38, 39, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Pipeline regenerates inventory + report; checker accepts | `test_g01_terminal` | covered | `instruction.md:9-14`; `test_outputs.py:469-478` |
| Digest binds inventory ↔ report (`run_contract.md`) | `test_g02_align` | covered | `run_contract.md:63-86`; `test_g02` |
| Authority order; retire removals | `test_g03_deep_gate` | covered | `rules_contract.md:16-26,70-75` |
| Full candidate sets on surviving hosts | `test_g04_smoke_guard` | covered | `run_contract.md:38-40`; `_candidate_counts` |
| Baseline visibility with all r1 candidates | `test_g05_visibility_seen` | covered | `rules_contract.md:77-82` |
| Idempotent recover via `run_entry.sh` after `rst_step.sh` | `test_g06_idem_hold` | covered | `run_contract.md:88-103` |
| Baseline immutable; tamper rejected | `test_g07_frozen_touch` | covered | `instruction.md:35-38` |
| Log/r1 claim-count alignment | `test_g08_cross_fmt` | covered | sampled log + ledger r1 candidates |
| Live operator override (anti-hardcode) | `test_g09_override_tracks_input` | covered | metamorphic `_override_tracks` |
| Deletion tracks input (anti-hardcode) | `test_g10_deletion_tracks_input` | covered | `_deletion_tracks` |
| Cross-artifact role/surface/epoch | `test_g11_cross_artifact_consistency` | covered | `_cross_artifact` |
| Per-field role/region resolution | `test_g12_field_level_authority` | covered | `rules_contract.md:44-53` |
| Signature gating → ignore all r2 | `test_g13_signature_gating` | covered | `rules_contract.md:33-35` |
| Sparse host (operator-only) | `test_g14_sparse_host` | covered | `rules_contract.md:28-31` |
| Alias chain fixpoint | `test_g15_alias_resolution` | covered | `rules_contract.md:55-63` |
| Alias cycle removed | `test_g16_alias_cycle_removed` | covered | `rules_contract.md:65-68` |
| Phantom: freshest-only r1 candidates as sole interpretation | — | phantom (not required) | Contracts require all considered claims |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–12, #27, section 9 |
| `task.toml` | #42–45, category/subcategory/codebase_size |
| `environment/Dockerfile` | #13–16, #18, #20, #50 |
| `environment/r6/rules_contract.md` | #27, #55, adjudication 5–6 |
| `environment/r6/run_contract.md` | schemas, candidates, recovery |
| `environment/r4/kx/g_extract_k.sh` | intended bug vs g13 |
| `tests/test.sh` | #20, #24–26 |
| `tests/test_outputs.py` | #27–31, #52, alignment table |
| `solution/solve.sh` + patches | #22–23 |
| `entire-report.txt` | #21, #45, #54, agent stats, LLMaJ |
| `docs/task-type-taxonomy.md` | #44 category |
| `docs/task-subtypes.md` | #44 tool_specific |
| `docs/faq.md` | codebase_size file bands |
| Platform Changelog (Jun 29 etc.) | category/milestone gate; Dockerfile; rubrics; test.sh |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate offline-service-reconciler/
→ 0 error(s), 1 warning(s): Non-trivial environment/ should include .dockerignore
INFO: Milestone tasks preferred (non-milestone not blocked)
INFO: missing module-level docstring (recommended only)

./scripts/terminus audit … --report entire-report.txt
→ APPROVED WITH WARNINGS; #44 heuristic FAIL (category)

./scripts/terminus review … --report entire-report.txt
→ baseline report rewritten by this manual enrichment
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 80.0% (4/5) | Best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | Worst model |
| oracle | 100.0% (3/3) | Consistent |
| nop | 0.0% (0/1) | Fails as required |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium (20–60% band, inclusive edge) |
| Declared difficulty | hard (`task.toml`) |
| Platform classified | medium |
| Tier match (#45) | field present → CHECK; mismatch informational only |
| Too easy (#54) | no (60% ≤ 80%) |

**Category confidence:** High on facts, nuanced on policy — primary *activity* is bug-find/fix (taxonomy `debugging`), but **Jun 29 eval blocks net-new `debugging` / `software-engineering`**. Leaving `system-administration` is the safe/allowed metadata choice for this in-review submission; do not Revise solely to force a blocked category label. Residual Medium: `tool_specific` subcategory.

**codebase_size confidence:** High — `find environment -type f ! -name Dockerfile` → **28 files** → `small` (20+; not `large`). May 3/May 11: `minimal` re-allowed platform-wide (N/A here).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular non-milestone; report matches bash reconciler domain |
| 1 Instruction | ☑ | Concise, absolute paths, contracts referenced; no canary/name |
| 2 Environment | ☑ | Digest pin, tmux/asciinema, offline, no tests COPY |
| 3 Oracle | ☑ | Patch-then-run; export 3/3 |
| 4 Verifiers | ☑ | Docstrings OK; reward path OK; no runtime installs; alignment OK |
| 5 Metadata | ☑ | Fields present; #44 Medium (`tool_specific`); Jun 29 — keep off blocked categories |
| 6 Rubric | ☑ | Understanding Rubrics = author UI workflow + quality when present; export empty → #32–39 N/A (not High for missing body) |
| 7 LLMaJ & agents | ☑ | Quality PASS; sufficiency FAIL adjudicated False for candidates |
| 8 Novelty & fairness | ☑ | Multi-bug debug; metamorphic anti-cheat |
| 9 Long context | ☑ | N/A — not tagged |
| 10 Submission Checklist | ☑ | Folded; only author-side rubric skip + `.dockerignore` warn |

---

## 9. Reviewer note (copy-paste to portal)

Nice offline bash reconciliation task — clear contracts, strong metamorphic anti-cheat, a clean patch-based oracle, and agent rates that feel right for medium. The Dockerfile is digest-pinned with verifier deps baked in and internet off. I would accept as-is. Mild notes only: `tool_specific` isn’t a great subcategory fit, and the package I got didn’t include the platform rubric text so those scoreboxes weren’t checkable — worth adding/editing the UI rubric on the platform if you revise for anything else. Leave the top-level category alone.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Time Based Tests | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no (Medium #44 note only; not blocking) | — |
| Milestones | no | — |
| Uses Internet | no | — |
| Agent Timeout | no | — |
| Wrong Coding Language | no | — |
| Canary Strings | no | — |
| Rubric | no (absent body → N/A #32–39; Understanding Rubrics quality gates apply only when text exists) | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |

*No blocking categories. Error categories: none.*
