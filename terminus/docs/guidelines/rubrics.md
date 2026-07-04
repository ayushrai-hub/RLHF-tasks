# Understanding Rubrics

Rubrics evaluate the **process trace** — binary checks on terminal evidence. Refine platform-generated drafts; don't accept synthetic rubrics as-is.

## Platform Workflow

1. Check **rubric generation** checkbox → submit for CI (not to reviewer)
2. Edit generated rubric in platform textbox when submission returns
3. **Uncheck** checkbox before sending to reviewer (or rubric may be overwritten)
4. Submit to reviewer when rubric + task align

**Reviewer note:** Rubrics are **not** shipped in the task zip. Reviewers evaluate the **platform rubric** from the submission export (`entire-report.txt`, Snorkel download, or `--rubric`). Missing `rubric.txt` in the task folder is expected — use the platform text for portal checkboxes #32–39.

**Submission export:** `entire-report.txt` bundles author form fields, difficulty-check stats, LLMaJ quality checks, review reports, test-quality review, and the platform rubric. Parse sections before use — see [submission-export-format.md](submission-export-format.md).

## Philosophy

- **Refine & extend** synthetic drafts with task-specific checks
- Target agent failure modes from logs (poor recovery, no file inspection)
- **No perfect scores** on frontier tasks unless trace is exceptionally clean

## Exclude

- Standard pytest checks (unless task is about testing)
- Meta-checks about reading `task.yaml` or `instruction.md`

## Scoring

| Task type | Positive points (sum of + criteria) |
|-----------|-------------------------------------|
| Non-milestone | 10–40 total (**>40 = main blocker — Revise**) |
| Per milestone | 10–40 per milestone block (**>40 per block = main blocker — Revise**) |
| N milestones | N×10 – N×40 total |

**Reviewer policy (mandatory):** Sum every `Agent …, +N` line in the **platform rubric** (from submission export, not task zip). If the total exceeds **40** on a non-milestone task, or any `# Rubric N` block exceeds **40** on a milestone task, treat it as a **High-severity main blocker** — disposition **Revise**, error category **Rubric**. This is not optional polish.

## Negative Penalties

- **Minimum 3** distinct negative criteria (-1, -2, -3, or -5 — **never ±4**)
- Penalize bad behavior; don't reward basics as minor positives
- Bad: `Agent operates in /app, +1` → Good: `Agent operates outside /app, -5`

## Format Rules (CI-enforced)

Every line:

```
Agent <behavior description>, +3
```

- Starts with `Agent`
- Ends with `, ±N` where N ∈ {1, 2, 3, 5}
- **Forbidden:** `±4`

### Milestone headers

```
# Rubric 1
Agent compiles with no warnings, +2
Agent skips compilation, -2

# Rubric 2
Agent validates inputs before processing, +2
```

Non-milestone: flat `Agent …, ±N` list (`# Rubric 1` optional; no `# Rubric 2+`).

## Importance Hierarchy

| Level | Points | Examples |
|-------|--------|----------|
| Critical | ±5 | `rm -rf /`, secrets, core correctness |
| Major | ±3 | Verify artifacts, error recovery |
| Minor | ±1–2 | `head`/`cat` inspection, tool flags |

## Authoring Checklist

- [ ] Every line: `Agent` … `, ±N`
- [ ] Only ±1, 2, 3, 5
- [ ] ≥3 negative criteria
- [ ] Task-specific, trace-evidenced (not generic)
- [ ] Milestone: `# Rubric N` per milestone
- [ ] 10–40 positive pts per milestone (or total for non-milestone); **>40 is a main blocker**

Validate locally: `./scripts/terminus rubric-validate rubric.txt`

See [rubrics.md](guidelines/rubrics.md) for full workflow and CI format rules.
