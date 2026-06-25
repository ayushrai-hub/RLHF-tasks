---
name: terminus-accuracy-review
description: Deep accuracy review of a Terminus Edition 2 task. Writes review-report.md with blockers, proof files, CHECK/UNCHECK checkbox numbers, and portal accept/revise note. Use with prompt.md, task folder, and entire-report.txt.
---

# Terminus Accuracy Review

## Deliverable

**File:** `<task-dir>/review-report.md`

## Steps

1. Read [prompt.md](../../../prompt.md)
2. Run:
   ```bash
   ./scripts/terminus validate <task-dir>
   ./scripts/terminus review <task-dir> --report <report-file>
   ```
3. Re-read all task artifacts; challenge ChatGPT findings with `file:line` proof
4. Enrich `review-report.md` using table-first structure (sections 1–10 per `prompt.md`)
5. Tag blockers with error categories (internal tracking list in `prompt.md`)
6. Reply in chat: disposition + error categories + CHECK + UNCHECK numbers only

## Portal checkboxes

- **CHECK** = passes (tick in portal)
- **UNCHECK** = fail, unverified, or N/A (leave blank)
- Report must list every number with reason and proof file

## References

- [prompt.md](../../../prompt.md)
- [reviewer-checklist-ui.md](../../../docs/reviewer-checklist-ui.md)
- [templates/review-report.template.md](../../../templates/review-report.template.md)
- [faq.md](../../../docs/faq.md)
