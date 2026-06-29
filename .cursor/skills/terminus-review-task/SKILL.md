---
name: terminus-review-task
description: Peer review Project Terminus Edition 2 task submissions. Use when reviewing, accepting, revising, or adjudicating Terminus tasks, or when the user asks for a reviewer checklist evaluation.
---

# Terminus Review Task

## Get Assignment

```bash
stb reviews get -p "Terminus-2nd-Edition"
stb reviews download <REVIEW_ID>
stb reviews feedback <REVIEW_ID>
```

## Review Pipeline

```
- [ ] 1. Structure (regular / milestone / multi-container)
- [ ] 2. Instructions — prompt styling, no hints, absolute paths
- [ ] 3. Environment — Dockerfile, pinning, canonical base, no cheats
- [ ] 4. Oracle — deterministic, no hardcoded answers, passes
- [ ] 5. Verifiers — reward.txt, no runtime installs, behavior tests
- [ ] 6. LLMaJ alignment — instructions ↔ tests ↔ schema ↔ files
- [ ] 7. Rubric — use **platform rubric** from submission report (`entire-report.txt`); format, ≥3 negatives, no test/metadata refs; **>40 positive pts = main blocker** (non-milestone total or per milestone block)
- [ ] 8. Metadata — task.toml complete, tags/category accurate
- [ ] 9. Agent runs — block only if worst-model (lowest rate) **>80%**; **never** block on `task.toml` vs platform difficulty mismatch (#45 always CHECK when field present)
- [ ] 10. Test-quality eval flags (req-gap, phantom-spec, etc.)
- [ ] 11. Parse `entire-report.txt` sections — [submission-export-format.md](../../docs/guidelines/submission-export-format.md) (author text vs difficulty stats vs quality checks vs platform rubric)
```

## Local Testing

```bash
./scripts/terminus validate <downloaded-task-dir>
./scripts/terminus oracle <downloaded-task-dir>
./scripts/terminus llmaj-check <downloaded-task-dir>
```

## Decision

**Accept:** `stb reviews accept <REVIEW_ID> --time <min> -n "notes"`  
**Revise:** `stb reviews revise <REVIEW_ID> --notes "..." --time <min>`  
**Skip:** `stb reviews skip <REVIEW_ID> --reason ... --rationale "..."`

## Portal reviewer note (section 9)

Copied to the submission portal for the author. Write like a **human peer reviewer** — acknowledge what’s good (“nice task”, “solid verifiers”), then what to fix. **Task-independent** (no `rubrics.md`, checkbox numbers, error categories, LLMaJ names, “re-audit”, “checklist failed”). Framework traceability stays in sections 2–8.

## Internal revision notes (for report sections 2–8)

```markdown
## Instructions (High)
- instruction.md: [issue] → [fix]. See docs/guidelines/prompt-styling.md

## Tests (High)
- tests/test_outputs.py:test_X — req-gap: instruction requires Y, no test

## Environment (High)
- environment/Dockerfile: [issue] → [fix]

## Rubric (High)
- Platform rubric positive total >40 (non-milestone) or any milestone block >40 — trim on platform; see docs/guidelines/rubrics.md
- [criterion]: references tests — remove; see docs/guidelines/rubrics.md
```

## Checklists

- Quick: [reviewer-checklist.md](../../docs/reviewer-checklist.md)
- **Full (severity-tagged):** [reviewer-checklist-full.md](../../docs/reviewer-checklist-full.md)
- **Accuracy review (external reports):** [prompt.md](../../prompt.md) + skill `terminus-accuracy-review`
- Process: [review-guidelines.md](../../docs/guidelines/review-guidelines.md)
- LLMaJ: [llmaj-checks.md](../../docs/guidelines/llmaj-checks.md)
- Agent Review: [agent-review.md](../../docs/guidelines/agent-review.md)
- Quality: [quality-guidelines.md](../../docs/guidelines/quality-guidelines.md)
- Common errors: [common-errors.md](../../docs/guidelines/common-errors.md)
