# Difficulty Guidelines

Difficulty = **agent pass rate** on GPT-5.5 and Claude Opus 4.8 (5 runs each).

## Tiers

| Tier | Criteria |
|------|----------|
| **Hard** | ≤20% on **best** OR **worst** model |
| **Medium** | 20–60% on **worst** model |
| **Easy** | 60–80% on **worst** model |
| **Rejected** | >80% on worst model |

**Best vs worst:** Worst model sets the floor for Easy/Medium. Best model ≤20% can earn Hard even if worst also struggles.

## New Submission Policy

- **Easy blocked** for brand-new submissions
- **Python tasks** must be **hard**
- See [submission-diversity.md](../submission-diversity.md)

## Designing Hard (≤20%)

- Deep domain expertise, 10+ sequential steps
- Subtle debugging, niche tools
- Bespoke rules among common patterns
- Obscure docs, non-obvious root causes

## Designing Medium (20–60%)

- 5–10 steps, some domain knowledge
- Edge cases, easy-to-miss config

## Designing Easy (60–80%)

- Still 3–5 steps, non-trivial
- One or two tricky aspects on standard problems

## Common Mistakes

| Too easy | Too unfair |
|----------|------------|
| Single-step | Impossible requirements |
| Obvious debugging | Ambiguous instructions |
| Common tutorials | Time-dependent results |
| Simple API usage | External dependencies |

## Verify

```bash
./scripts/terminus oracle <task-dir>          # must PASS
./scripts/terminus agent <task-dir> --runs 5   # both models
```

**Good failure:** reasoning errors, missed edge cases  
**Bad failure:** unclear instructions, environment bugs → fix task

## Adjust

| Harder | Easier |
|--------|--------|
| More steps, hidden reqs | Clarify instructions |
| Niche knowledge | Common tech |
| Debugging scenarios | Reduce steps |

**Do not** add hints to instructions to make tasks easier.
