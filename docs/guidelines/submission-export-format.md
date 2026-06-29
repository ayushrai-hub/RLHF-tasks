# Submission Export Format (`entire-report.txt`)

Snorkel / Terminus submission downloads and reviewer packages often include a single text blob — commonly `entire-report.txt` — that merges **author form fields**, **system difficulty runs**, **LLMaJ quality checks**, **automated review reports**, and the **platform rubric**. Review tools and skills must treat each region separately.

**Do not** treat the whole file as one document type. **Do** map sections first, then apply the right checklist phase to each.

---

## Section map (typical order)

| Section key | Portal / form label | How to recognize | Used for |
|-------------|---------------------|------------------|----------|
| `difficulty_explanation` | Difficulty Explanation (optional) | Header `Difficulty Explanation (optional)` then author prose | Context only — not normative spec |
| `solution_explanation` | Solution Explanation (optional) | Header `Solution Explanation (optional)` | Context only — **never** treat as oracle ground truth |
| `verification_explanation` | Verification Explanation (optional) | Header `Verification Explanation (optional)` | Context only |
| `difficulty_check` | Summary / difficulty check results | `Difficulty: ✅ HARD\|MEDIUM\|EASY`, `Agent Performance:`, `Unit Tests Results:` | **#45, #54**, section 7 agent stats, per-test pass rates |
| `instruction_sufficiency` | Analysis on Agent Failures | `Task Instruction Sufficiency:` or `Analysis on Agent Failures:` | Adjudicate spec-gap claims (#27, #55) |
| `quality_check` | Quality check summary | `## Quality Check Results` or `Quality Check Results` + `behavior_in_*` lines | LLMaJ alignment hints; cross-check with artifacts |
| `review_report` | (system) Harbor / validator review | `REVIEW REPORT:` banner block | Warnings/suggestions — verify against task files |
| `test_quality` | Test Quality Report | `TEST QUALITY REVIEW:` banner block | Test-suite quality; per-milestone blocks when present |
| `platform_rubric` | Agent-generated rubric(s) | `# Rubric N` headers **or** trailing `Agent …, ±N` lines **or** `Agent-generated rubric` label | **Checkboxes #32–39** |
| `agent_review` | Agent review (optional) | `Agent review` header when populated | Advisory agent-run narrative |
| `comments_for_reviewer` | Comments for Reviewer (optional) | Header `Comments for Reviewer (optional)` then author prose | Author context for reviewers — not normative spec |
| `reviewer_feedback` | Reviewer Feedback | Header `Reviewer Feedback` (optional notes from a prior review cycle) | Prior reviewer notes — verify claims against artifacts; may be stale on re-submission |

Sections may be **blank** during initial author submission (`Quality check summary`, `Agent review`, `Test Quality Report` — "disregard if blank"). Absence is normal pre-CI.

---

## What each section is **not**

| Section | Not used for |
|---------|----------------|
| Author explanations | Instruction requirements (#7, #27) — spec is `instruction.md` + env contract |
| Solution explanation | Oracle verification (#23) — use `solution/solve.sh` |
| Quality check `pass` lines | Automatic Accept — re-verify against files |
| Review report `READY TO USE` | Automatic Accept — artifacts win |
| Platform rubric alone | Task correctness — rubric is process trace only |
| Reviewer Feedback | Automatic Revise/Accept — re-verify every claim in task files |
| Comments for Reviewer | Instruction requirements — author justification only |

---

## Rubric extraction priority

When evaluating **#32–39**:

1. `--rubric rubric.txt` (explicit file)
2. `task-dir/rubric.txt` or `rubrics.txt`
3. `platform_rubric` section from submission export:
   - `# Rubric 1` … `# Rubric N` (milestone tasks)
   - Flat `Agent …, ±N` list after test-quality block (non-milestone)
   - Lines after `Agent-generated rubric` label

Missing `rubric.txt` in the task zip is **expected**. Mark rubric checkboxes N/A only when **no** platform rubric appears in the export.

---

## Milestone vs non-milestone rubric shape

| Task type | Expected platform rubric |
|-----------|-------------------------|
| `number_of_milestones = 0` | Flat `Agent …, ±N` lines; optional single `# Rubric 1` only |
| `number_of_milestones ≥ 2` | `# Rubric 1`, `# Rubric 2`, … one block per milestone |

Mismatch (e.g. four `# Rubric` blocks on a non-milestone task) is a **Rubric** finding (#32–39), not a task-layout error.

---

## CLI / automation

```bash
./scripts/terminus review <task-dir> --report entire-report.txt
```

`review_checklist.py` calls `parse_submission_export()` to split the blob before:

- `parse_report()` → agent pass rates, difficulty tier
- `extract_platform_rubric()` → rubric checkboxes
- External adjudication hints → scoped to the matching section

---

## Author form ↔ export

The submission form fields map to export sections as follows:

| Form field | Export section |
|------------|----------------|
| Difficulty Explanation | `difficulty_explanation` |
| Solution Explanation | `solution_explanation` |
| Verification Explanation | `verification_explanation` |
| Summary (difficulty check) | `difficulty_check` + often `instruction_sufficiency` |
| Quality check summary | `quality_check` |
| Agent review | `agent_review` |
| Test Quality Report | `test_quality` |
| Agent-generated rubric(s) | `platform_rubric` |
| Comments for Reviewer | `comments_for_reviewer` |
| Reviewer Feedback | `reviewer_feedback` |

---

See also: [rubrics.md](rubrics.md), [reviewer-checklist-ui.md](../reviewer-checklist-ui.md), [prompt.md](../../prompt.md).
