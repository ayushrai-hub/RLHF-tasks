# Terminus Task Accuracy Review — Standard Prompt Template

**Use this template for every task accuracy review.** Fill the placeholders, then paste the Invocation block as the agent message. Do not skip scripts or skills — they are required, not optional helpers.

| Placeholder | Replace with |
|-------------|--------------|
| `<task-folder>` | Task directory path (e.g. `tasks/my-task` or `my-task`) |
| `@entire-report.txt` | Path to the Snorkel submission export (or omit + note if absent) |
| `[paste ChatGPT findings]` | External AI/human claims to adjudicate, or `none` |

Full procedure, error categories, portal rules, and report sections: **`@prompt.md`**.  
Report shape: **`@templates/review-report.template.md`**.

---

## Invocation

```
Follow @prompt.md and @.cursor/skills/terminus-accuracy-review/SKILL.md exactly.
Every task review must use this standard template and the repo automations below — do not substitute a lighter ad-hoc review.

Review task: @<task-folder>/
External report: @entire-report.txt
ChatGPT findings: [paste ChatGPT findings]

### Required automations & scripts (run these; do not skip)

Use this repo's Terminus CLI and review tooling before any manual judgment:

1. @terminus-validate — then run:
   ./scripts/terminus validate <task-folder>
2. Full audit (55 portal items → <task-folder>/audit-report.md):
   ./scripts/terminus audit <task-folder> --report entire-report.txt
3. Baseline review report (<task-folder>/review-report.md):
   ./scripts/terminus review <task-folder> --report entire-report.txt
4. Combined gate when useful:
   ./scripts/terminus check-all <task-folder>
5. Rubric positive-point sum (blocker if >40 non-milestone, or >40 per milestone block):
   ./scripts/terminus rubric-points entire-report.txt
6. Optional evidence — do **not** run Docker oracle / llmaj-check; use platform export + static solution review:
   # ./scripts/terminus oracle <task-folder>
   # ./scripts/terminus llmaj-check <task-folder>

Also apply:
- @.cursor/skills/terminus-accuracy-review/SKILL.md (primary review skill)
- @.cursor/skills/terminus-review-task/SKILL.md (peer-review pipeline reference)
- Project rules/docs as needed: @docs/ @docs/guidelines/ @docs/reviewer-checklist-full.md @docs/reviewer-checklist-ui.md @docs/guidelines/submission-export-format.md

Script/validator outputs are evidence to verify — not a substitute for reading the artifacts.

### Independent re-audit (mandatory)

- Re-audit the entire task independently after scripts finish.
- Ignore prior conclusions (ChatGPT, prior reviewers, auto-accept hints) until you verify them yourself.
- Cross-reference every external claim with repository evidence (`file:line`, test names, quotes).
- Verify implementation and behavior, not just wording.
- Deep-dive every potential blocker; assume hidden blockers may exist even if ChatGPT says Accept.
- Trace logic across instruction ↔ environment ↔ solution ↔ tests ↔ metadata ↔ platform rubric.
- Confirm any claimed fixes are real, complete, and consistent across files.
- Base every conclusion on facts: repo evidence, project rules, validator/audit/review outputs.
- Never rely on assumptions or previous reviews. Challenge every claim until proven.

### Deliverable

Write / enrich the final review at:
  <task-folder>/review-report.md

Requirements:
- Structure = sections 1–10 from @prompt.md (table-first; see @templates/review-report.template.md).
- Cover all 55 portal checkboxes (#1–#55) with CHECK or UNCHECK + reason + proof.
- Severity: High / Medium / Low; tag blockers with error categories from @prompt.md.
- Section 9 (portal note): human peer-reviewer tone — task facts only; no framework citations, checkbox numbers, or audit-bot phrasing.
- If Accept: explicitly confirm prior blockers verified fixed and no new blockers after full audit.

### Chat reply (only)

Disposition: Accept | Revise | Decline
Error categories: none | [comma-separated]
CHECK: …
UNCHECK: …

Do not dump the full report in chat.
```

---

## Quick reference (for the human filling this in)

### Authority order (highest wins)

1. `docs/reviewer-checklist-full.md` + `docs/task-requirements.md`
2. `docs/guidelines/`
3. `./scripts/terminus validate` / `audit` / `review` / `check-all` output
4. External reports (`entire-report.txt`, ChatGPT) — verify; do not trust blindly

### Decision rules (summary)

| Condition | Disposition |
|-----------|-------------|
| Any High blocker | Revise or Decline |
| Multiple Medium in same area | Revise |
| Single Medium, no High | Accept with note |
| Low only | Accept |
| Artifacts contradict external “Accept” | Revise — artifacts win |

- **Never block** on `task.toml` difficulty vs platform classified mismatch (#45 is informational).
- **Block on difficulty only** when worst-model pass rate **>80%** (#54).
- **Rubric blocker:** positive points **>40** (non-milestone total) or **>40** in any milestone block.

### Commands cheat sheet

```bash
./scripts/terminus validate <task-folder>
./scripts/terminus audit <task-folder> --report entire-report.txt
./scripts/terminus review <task-folder> --report entire-report.txt
./scripts/terminus check-all <task-folder>
./scripts/terminus rubric-points entire-report.txt
# optional — do not run Docker oracle / llmaj-check; use platform export + static review:
# ./scripts/terminus oracle <task-folder>
# ./scripts/terminus llmaj-check <task-folder>
```
