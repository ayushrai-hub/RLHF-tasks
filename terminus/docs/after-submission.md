# After Submission

## Review Timeline

| Stage | Duration |
|-------|----------|
| Automated CI checks | Immediate |
| Peer review assignment | ~1 day |
| Initial review | 1–7 business days |
| Follow-up reviews | 1–7 business days |
| **Total** | **7–14 business days** |

## Review Process

### 1. Automated Checks

- CI checks (syntax, structure, dependencies)
- LLMaJ checks (quality, completeness)
- Oracle agent run

### 2. Peer Review

Expert reviews: clarity, solution validity, test coverage, anti-cheating, overall quality.

### 3. Agent Evaluation

- GPT-5.5 with Codex agent (5 runs)
- Claude Opus 4.8 with Claude Code (5 runs)

Pass rate determines final difficulty classification.

## Outcomes

### Approved

Task added to benchmark suite; credit recorded.

### Changes Requested

1. Read feedback carefully
2. Make targeted fixes locally
3. Re-run all checks: `./scripts/terminus check-all <task-dir>`
4. Update rubric if task changed significantly
5. Resubmit: `stb submissions update <task-dir> --time <minutes>`

### Declined

Common reasons: too easy, unclear requirements, duplicate task, fundamental design issues.

Review feedback; significantly revise or start fresh. Appeal via Slack if you disagree.

## Addressing Feedback

- Fix only what's requested — don't rewrite everything
- Use [Reviewer Checklist](reviewer-checklist.md) before resubmitting
- Add revision summary note on platform
- Respond politely with evidence if you disagree
- Escalate to `#terminus-2nd-edition` on Slack if needed

## Tips for Faster Acceptance

- Run all checks locally before submitting
- Follow [Submission Checklist](submission-checklist.md) exactly
- Write clear, human-style `instruction.md`
- Address feedback promptly
- Ask questions if feedback is unclear
