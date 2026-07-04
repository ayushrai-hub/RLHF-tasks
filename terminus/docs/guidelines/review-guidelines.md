# Review Guidelines

Peer reviewer guide for Terminus Edition 2 submissions.

## Philosophy

- Catch issues before they enter the dataset
- Find **all** issues in one review — don't stop at the first error
- Feedback must be **clear, complete, actionable**
- After revision, task should be accept-ready

## Review Flow

1. Read task description ([prompt-styling.md](prompt-styling.md))
2. Review tests (coverage, docstrings, behavior not implementation)
3. Run test-quality eval flags (helper, not replacement)
4. Check solution (process not answer, deterministic)
5. Verify metadata (difficulty, category, timeouts)
6. Watch agent runs (good vs bad failure reasons)

## Test-Quality Eval Flags

| Flag | Meaning |
|------|---------|
| req-gap | Instruction requires X, no test |
| weak-assertion | Test too loose |
| phantom-spec | Test enforces unstated behavior |
| flaky-execution | Correct solution can fail |
| vacuous-test | Passes regardless of output |

## Common Issues to Flag

### Instructions
- Ambiguous ("make it better")
- Missing output specs
- Relative paths
- Hidden hints in env files

### Tests
- Brittle string matching
- Missing coverage
- Order-dependent tests
- Source code grep tests

### Solution
- Hardcoded answers
- Non-deterministic (no seed)
- Incomplete steps

### Watch For
- Tool specs that can't be verified ("use vim")
- Randomness assumptions in tests
- 20+ tests for simple tasks
- CSV without header spec
- Anti-cheat vectors (decompile, replace binaries, delete tests, git commits)

## Actions

### Approve
No issues; ready for benchmark.

### Request Changes
Be specific: what's wrong, where, how to fix.

**Good:** `test_output_format line 45 uses exact string match — check required fields instead.`

**Bad:** `Tests need work.`

### Portal reviewer note (`review-report.md` section 9)

Copied to the author in the submission portal. Write like a **human peer reviewer** — warm and direct; say what’s good about the task before what needs fixing. **Task-independent** (no `rubrics.md`, checkbox numbers, error categories, LLMaJ names). Avoid audit-bot tone (“re-audit”, “checklist failed”, “meets Edition 2 requirements”). Doc citations stay in sections 2–8 only.

### Decline
Fundamental issues: too easy (>80%), duplicate, flawed concept.

## Local Tools

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus oracle <task-dir>
./scripts/terminus ci-check <task-dir>
```

## Checklists

- Quick: [reviewer-checklist.md](../reviewer-checklist.md)
- Full (severity-tagged): [reviewer-checklist-full.md](../reviewer-checklist-full.md)
