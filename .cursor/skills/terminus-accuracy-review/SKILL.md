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
   ./scripts/terminus audit <task-dir> [--report <report-file>]
   ./scripts/terminus review <task-dir> --report <report-file>
   ```
   Parse `entire-report.txt` sections per [submission-export-format.md](../../../docs/guidelines/submission-export-format.md) before adjudicating.
3. Re-read all task artifacts; challenge ChatGPT findings with `file:line` proof
4. Enrich `review-report.md` using table-first structure (sections 1–10 per `prompt.md`)
5. Tag blockers with error categories (internal tracking list in `prompt.md`)
6. **Section 9 reviewer note:** human, conversational tone for the portal — acknowledge strengths, then blockers; no framework citations or audit-bot phrasing (see `prompt.md` §9)
7. Reply in chat: disposition + error categories + CHECK + UNCHECK numbers only

## Portal checkboxes

- **CHECK** = passes (tick in portal)
- **UNCHECK** = fail, unverified, or N/A (leave blank)
- Report must list every number with reason and proof file
- **Rubrics (#32–39):** evaluate the **platform rubric** from `entire-report.txt` / submission export (or `--rubric`); missing `rubric.txt` in the task folder is normal — do not mark N/A when the report includes rubric text
- **Rubric positive cap (main blocker):** sum all `+N` lines from `entire-report.txt` via `scripts/rubric_points.py` or `./scripts/terminus rubric-points` — **>40** only (40 passes)
- **Difficulty (#45):** **CHECK** when `difficulty` in `task.toml` — declared vs platform/agent tiers **never** blocks; informational only
- **Difficulty (#54):** block only when **worst-model** (lowest agent rate) **>80%**

## References

- [prompt.md](../../../prompt.md)
- [reviewer-checklist-ui.md](../../../docs/reviewer-checklist-ui.md)
- [submission-export-format.md](../../../docs/guidelines/submission-export-format.md)
- [templates/review-report.template.md](../../../templates/review-report.template.md)
- [faq.md](../../../docs/faq.md)
