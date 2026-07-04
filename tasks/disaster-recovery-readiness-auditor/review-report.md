# Terminus Review Report: disaster-recovery-readiness-auditor

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn (0 errors, 95 warnings) |
| **Oracle** | not executed (Docker daemon unavailable locally) |
| **CHECK count** | 47 |
| **UNCHECK count** | 8 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues

**Decision (concise):** Strong offline corpus, pinned environment, and trap-heavy verifier. Two real spec↔test gaps block acceptance: (1) handbook wording treats all three `manifest_gates` fields as inclusion gates while the verifier only scopes on `audit_included` + `dr_audit_cycle` and uses `replication_audited` only for replication evidence; (2) tests require every gap `evidence_source` path in `dr_readiness_report.md` but the policy report schema lists headings only. Rubric format/points are fine for a non-milestone task (39/40, flat `Agent …, ±N` list). `__pycache__` and missing per-test docstrings are not blockers.

**Insights (concise):**

- Worst-model 0% (Opus 0/5), best 20% (GPT-5.5 1/5) — appropriately hard; platform classified `hard` matches `task.toml`.
- Platform rubric is **not** in milestone format: flat 17 `Agent …, ±N` lines, no `# Rubric 2+` headers; 39 positive points (≤40 cap).
- `regional-failover-policy.md` line 49 + canonical row formats make gap `evidence_source` = corpus `source_relpath` derivable; ChatGPT’s separate “format” claim is overstated.
- Oracle `solve.py` mirrors `reference_solver.py` and embeds report evidence paths in gap bullets — confirms tested report shape exists but is undocumented in policy schema.
- 93 tests lack docstrings but all have descriptive `test_*` names — satisfies checkbox #31 (“names **or** docstrings”).
- Entire-report Harbor review “READY TO USE” and LLMaJ `behavior_in_*` PASS are directionally right on environment quality but miss the policy/report spec gaps.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #7, #27, #55 | **Manifest scoping contract is ambiguous.** Handbook says scoped systems must “pass every gate in `manifest_gates`” (`dr-readiness-handbook.md:27`), and policy lists three fields including `replication_audited_field` (`dr-audit-policy.json:17-21`). Verifier scopes only on `audit_included` + `dr_audit_cycle` (`reference_solver.py:149-154`) and uses `replication_audited` only to filter replication lag (`reference_solver.py:156-162`, `regional-failover-policy.md:47`). `payments-ledger` has `replication_audited: false` but must appear in assessment (`payments-ledger.json:10`, `test_payments_replication_lag_ignored_when_not_audited`, `test_each_scoped_system_present_in_assessment`). Literal reading excludes payments-ledger. | `environment/architecture_docs/dr-readiness-handbook.md:27-28`; `environment/architecture_docs/dr-audit-policy.json:17-21`; `tests/reference_solver.py:149-162`; `environment/infrastructure_manifests/payments-ledger.json:8-10`; `tests/test_outputs.py:716-718`, `832-833` | Split scope gates (`audit_included`, `dr_audit_cycle`) from evidence filter (`replication_audited`) in handbook and/or policy `manifest_gates` section. State explicitly that `replication_audited: false` systems remain in scope; replication lag is ignored for RPO only. |
| 2 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | **Report narrative requirements are phantom-tested.** Policy `dr_readiness_report` schema defines title, headings, and `executive_summary_fields` only — no per-gap evidence paths (`dr-audit-policy.json:78-90`). Tests require every gap `evidence_source` string to appear literally in `dr_readiness_report.md`, including strict RTO gaps when `meets_rto` is true (`test_outputs.py:686-694`, `806-812`). Instruction delegates report schema to the same policy file (`instruction.md:3`). | `environment/architecture_docs/dr-audit-policy.json:78-90`; `tests/test_outputs.py:686-694`, `806-812`; `solution/solve.py:661-671` | Add report content rules to policy schema or handbook: each `rto_exceeded` / `rpo_exceeded` gap row in the report must cite the gap’s `evidence_source` corpus path (and runbook `source_relpath` / blocker `evidence_source` where applicable). |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Manifest scoping ambiguous: `replication_audited` in `manifest_gates` but not a scope gate (ChatGPT High) | **Agree** | Handbook `pass every gate in manifest_gates` vs `manifest_qualifies()` only checking two fields; payments-ledger counterexample above |
| 2 | Markdown report must include gap `evidence_source` paths but policy doesn’t require it (ChatGPT High) | **Agree** | Policy report schema headings-only; `test_report_sections_reference_assessment_and_gaps` asserts each `gap["evidence_source"] in text` |
| 3 | `evidence_source` must be corpus-relative path, not record-type label (ChatGPT Medium) | **Partially agree** (not a blocker) | Canonical rows end with `<source_relpath>` (`dr-readiness-handbook.md:7-19`); annex: “keep the source from the record” (`regional-failover-policy.md:49`); `reference_solver.py` sets `evidence_source` from regex `source` group (`383`, `487`). Format is inferable; explicit one-liner in policy would help but does not drive Revise alone. |
| 4 | Remove `__pycache__` from solution/ and tests/ (ChatGPT Low) | **Agree** (cosmetic only) | `solution/__pycache__/`, `tests/__pycache__/` present; no functional impact |
| 5 | Dockerfile digest-pinned canonical base (ChatGPT) | **Agree** | `environment/Dockerfile:3` — `python:3.13-slim-bookworm@sha256:01f42367…` |
| 6 | Entire-report REVIEW “READY TO USE” (Harbor automated review) | **Disagree** on acceptance | Report praises policy as “unambiguous” but misses blockers 1–2 above |
| 7 | LLMaJ `behavior_in_task_description: pass` | **Partially agree** | Most behavior is in referenced policy files; report-content and manifest-scope nuances are under-documented |
| 8 | Instruction sufficiency FAIL on some agent runs citing manifest ambiguity (`entire-report.txt:134`) | **Partially agree** | Run `tbench-task__9aYtCQ6` analysis aligns with blocker 1; other runs failed on implementation precision per same section |
| 9 | `test.sh` re-executes agent solution (Harbor warning) | **Agree** (not a blocker) | `tests/test.sh:20-24`; instruction specifies `/app/solution/solve.py` — consistent pattern |
| 10 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | Platform rubric (`entire-report.txt:336-352`) is flat `Agent …, ±N` list with no `# Rubric 2+`; `task.toml` `number_of_milestones = 0` — correct non-milestone format |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 3 short paragraphs (~149 words) | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem narrative + output delegation; not a formal spec doc | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables in instruction | `instruction.md` |
| 4 | CHECK | No step by step instructions | No numbered solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT (four artifacts, policy authority) not HOW | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O tables in instruction | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Manifest-scope and report-content gaps (blockers 1–2) | `dr-readiness-handbook.md:27`; `dr-audit-policy.json:78-90` |
| 8 | CHECK | Instruction is interesting | Realistic DR readiness audit scenario | `instruction.md` |
| 9 | CHECK | Instruction is unique | Distinct corpus/policy/trap design vs typical tasks | task content |
| 10 | CHECK | All paths in instruction are absolute | `/app/...` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in body | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab web content | COPY local data only | `environment/Dockerfile` |
| 14 | CHECK | Pinned pip dependencies | `requirements.lock` with hashes in image build | `environment/Dockerfile:20-22` |
| 15 | CHECK | Base image digest-pinned | `@sha256:01f42367…` | `environment/Dockerfile:3` |
| 16 | CHECK | Environment self-contained | COPY only under environment data dirs | `environment/Dockerfile:25-34` |
| 17 | CHECK | No ground truth answers in env | Policy/handbook are normative specs, not golden outputs | corpus files |
| 18 | CHECK | No dangerous Docker capabilities | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter Harbor mounts | No docker-compose in task | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally (Docker unavailable); export shows 100% (3/3) | `entire-report.txt:31` |
| 22 | CHECK | Oracle no internet | solve.py reads local corpus only | `solution/solve.py` |
| 23 | CHECK | Oracle reflective of instruction | Full corpus scan pipeline, not hardcoded outputs | `solution/solve.py` |
| 24 | CHECK | test.sh reward.txt canonical block | mkdir, trap, 0/1 reward | `tests/test.sh:4-34` |
| 25 | CHECK | Same verifier logic for oracle and agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:30-33` |
| 27 | UNCHECK | Tests aligned with instructions | Phantom report requirements; manifest gate ambiguity | blockers 1–2 |
| 28 | CHECK | Tests check correctness | Reference-solver equality + trap tests | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior not implementation | Asserts on output artifacts, not agent source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching | Deterministic JSON/MD equality appropriate for task | `tests/test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | 93 descriptive `test_*` names; module docstring present | `tests/test_outputs.py` |
| 32 | CHECK | Rubric ≥3 negatives | 4 negatives in platform rubric | `entire-report.txt:349-352` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use allowed magnitudes | `entire-report.txt:336-352` |
| 34 | CHECK | Rubric `Agent …, ±N` one-line format | 17 valid Agent lines | `entire-report.txt:336-352` |
| 35 | CHECK | Rubric criteria detailed | Task-specific DR behaviors | `entire-report.txt:336-352` |
| 36 | CHECK | Rubric positive language for negatives | Bad behavior scored negative, not “does not” + positive | `entire-report.txt:349-352` |
| 37 | CHECK | Rubric no /tests/ references | None found | `entire-report.txt:336-352` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None found | `entire-report.txt:336-352` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None found | `entire-report.txt:336-352` |
| 40 | CHECK | Required files present | Dockerfile, instruction, task.toml, solve.sh, test.sh | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task root | task tree |
| 42 | CHECK | author_name/email present | Set in task.toml | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | timeouts, category, tags, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | python, system-administration, DR tags match | `task.toml` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"`; worst-model 0% | `task.toml:6`, `entire-report.txt:21-27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Per-milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in env | No solution COPY | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially cheat | Reference solver + decoys required | `tests/reference_solver.py`, corpus |
| 53 | CHECK | No unpinned git clone | No git in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst-model 0% | `entire-report.txt:26-27` |
| 55 | UNCHECK | Not too hard/unfair | Spec gaps on manifest scope and report evidence paths cause fair-agent failures | blockers 1–2; `entire-report.txt:99-101` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Four output files under `/app/` | `test_*_exists` (×4) | covered | `instruction.md:5`; `test_outputs.py` |
| Decision logic in `dr-audit-policy.json` | reference equality tests | covered | `instruction.md:3` |
| Scoped systems: manifest + AUDIT_SCOPE | `test_scoped_systems_require_audit_scope_and_manifest` | **gap** | handbook “every gate” vs two-gate solver |
| `replication_audited` filters replication only | `test_payments_replication_lag_ignored_when_not_audited` | **gap** | not explicit in handbook scope section |
| Gap `evidence_source` from evidence_priority | `test_each_gap_evidence_source_matches_reference` | covered | `regional-failover-policy.md:49` |
| Gap `evidence_source` = corpus path | `test_gap_evidence_sources_are_documented_paths` | covered | canonical `<source_relpath>` formats |
| Report headings per policy | `test_report_required_headings_in_order` | covered | `dr-audit-policy.json:80-87` |
| Report includes gap evidence paths | `test_report_sections_reference_assessment_and_gaps` | **phantom** | not in policy report schema |
| Strict RTO gaps listed in report even when `meets_rto` | `test_report_lists_strict_rto_gaps_not_meets_rto_only` | **phantom** | identity-core grace case; schema silent |
| Readiness score formula | `test_readiness_score_matches_formula` | covered | `dr-audit-policy.json:108-122` |
| Failover timeline from postmortem only | `test_failover_steps_limited_to_postmortem_source` | covered | `regional-failover-policy.md:43` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, blocker 2 |
| `task.toml` | #40-45, #46-49 N/A, rubric format |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/architecture_docs/dr-audit-policy.json` | blockers 1-2, spec alignment |
| `environment/architecture_docs/dr-readiness-handbook.md` | blocker 1 |
| `environment/compliance_requirements/regional-failover-policy.md` | blocker 1, evidence_source derivation |
| `environment/infrastructure_manifests/payments-ledger.json` | blocker 1 |
| `tests/reference_solver.py` | blocker 1, oracle behavior |
| `tests/test_outputs.py` | blockers 2, #27-31 |
| `tests/test.sh` | #20, #24-26 |
| `solution/solve.py` | blocker 2 (oracle report shape) |
| `entire-report.txt` | #45, #54, rubric #32-39, agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate disaster-recovery-readiness-auditor.
→ 0 errors, 95 warnings (93 missing per-test docstrings; solution-hint warnings on regional-failover-policy.md)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | |
| terminus-claude-opus-4-8 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) per export | not re-run locally |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes (informational) |

**Rubric:** 39 positive points / 40 cap — PASS. Flat non-milestone format (no `# Rubric 2+`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `disaster-recovery-readiness-auditor.`; regular layout; report matches task |
| 1 Instruction | ☑ | Concise; policy delegation; scope/report gaps found |
| 2 Environment | ☑ | Digest-pinned base, tmux/asciinema, offline, no tests/solution COPY |
| 3 Oracle | ☑ | solve.py derives outputs; Docker oracle not run |
| 4 Verifiers | ☑ | Canonical test.sh; spec gaps on report tests |
| 5 Metadata | ☑ | Complete; hard; non-milestone |
| 6 Rubric | ☑ | 39 pts; flat format; 4 negatives — not milestone rubric |
| 7 LLMaJ & agent evidence | ☑ | Adjudicated entire-report claims |
| 8 Novelty & fairness | ☑ | Multi-step; spec gaps affect fairness (#55) |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work overall — the corpus is rich, the Dockerfile is pinned and offline, and the trap tests are thorough. Two doc fixes before accept: clarify in the handbook/policy that `replication_audited` is an evidence filter only (scope gates are `audit_included` + matching `dr_audit_cycle`, so systems like payments-ledger stay in scope), and spell out in the `dr_readiness_report` schema that each gap row in the markdown must include the gap’s `evidence_source` corpus path (tests already check this, including strict RTO gaps under grace). Optional cleanup: drop committed `__pycache__` dirs.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Rubric | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Milestones | no | N/A (non-milestone) |
| Pinning Issues | no | — |
| Task Difficulty | no | 0% worst-model |
| Other | no | __pycache__ cosmetic only |
