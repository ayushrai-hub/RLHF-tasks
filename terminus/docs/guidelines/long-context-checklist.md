# Long Context Task Checklist

Use before submitting or accepting any task with `subcategories = ["long_context"]`. Full subtype definitions: [Task Subtypes](../task-subtypes.md#1-long-context-long_context).

## Spec Anchor

Must require reading **large documents** (≥ **50k tokens**). Cannot be solved by keyword search, grep, or simple programmatic parsing.

Allowed content: markdown, txt, PDF, docx, HTML, notebooks, chat logs, emails, papers, docs, logs. Extension alone is insufficient — content must function as long document context.

## Required (all must be true)

- [ ] ≥50k tokens of valid document-like content
- [ ] Long-context files **shipped with task** (not only generated at setup)
- [ ] Documents are **authoritative** to the solution
- [ ] Agent must **read and reason** over documents to solve correctly
- [ ] Cannot be solved by keyword search, grep, field extraction, or top-k stats
- [ ] Content is **not primarily** JSON/JSONL/CSV/TSV/DB dumps or uniform table/log records
- [ ] Corpus is not filler, repeated boilerplate, or many tiny one-line docs
- [ ] Verifier checks outputs depending on **details from long documents**
- [ ] Multiple docs: requires **cross-document** reasoning, not one obvious file
- [ ] Instruction points to document location **without leaking the answer**

## Immediate Rejection / Relabel

- [ ] Under 50k valid tokens
- [ ] Generator script but no shipped corpus
- [ ] Large JSONL/CSV/TSV/DB labeled as long context
- [ ] Uniform machine logs with fixed fields
- [ ] Many tiny files aggregating below 50k
- [ ] Long files used only for keyword search / simple analytics
- [ ] Documents historical, optional, or unrelated to oracle
- [ ] Repeated/filler text to inflate size
- [ ] Main challenge is parser/scheduler/ETL/search over structured data

## Good Task Shapes

- Long handbook/spec with interacting implementation rules
- Policy/underwriting manual with rates, exceptions, edge cases from text
- Multi-file investigation (emails, chats, calendars, HR notes)
- Incident narrative corpus — reconstruct what happened, not parse fixed schema

## EC Self-Review

| Question | If wrong → |
|----------|------------|
| Solvable without reading long docs? | Not long_context |
| Documents are source of truth? | Revise |
| Corpus >50k doc tokens (excl. code/config/structured data)? | Revise |
| More than keyword search / simple parsing? | Relabel |
| Reviewer sees why this tests long-context? | Revise |

Validate: `./scripts/terminus validate <task-dir>` flags `long_context` without large files.
