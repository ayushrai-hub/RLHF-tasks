# Difficulty Guidelines

Task difficulty is determined by accuracy when run against frontier AI models. This guide helps you design tasks at the right difficulty level.

## Difficulty Levels

Difficulty is calculated from accuracy across two evaluation models. The threshold that applies depends on the tier:

| Tier | Criteria | Notes |
|------|----------|-------|
| **Hard** | Accuracy ≤ 20% on the **best** model, **OR** ≤ 20% on the **worst** model | Deep expertise, multi-step reasoning, or niche knowledge |
| **Medium** | 20% < accuracy ≤ 60% on the **worst** model | Moderate complexity, some domain knowledge |
| **Easy** | 60% < accuracy ≤ 80% on the **worst** model | Straightforward but still non-trivial |
| **Rejected** | Worst model **> 80%** | Too easy to be useful as training signal — not accepted |

### Why "best" vs "worst" model?

Both models are normally run against every task (see [one-model early exit](#one-model-early-exit-for-hard-tasks) for the exception). The **worst** model sets the difficulty floor for most tasks: if even the weaker model can solve it most of the time, the task is Easy. The **best** model matters for the hardest tasks: a task where the strongest model still only scores ≤ 20% earns Hard even if the worst model also struggles, because the failure isn't just a weak-model artifact.

## Evaluation Process

Each task is evaluated against:

- **Claude Opus 4.8** with Claude Code agent
- **GPT-5.5** with Codex agent
- **5 runs each** to determine average accuracy

### One-model early exit for Hard tasks

Difficulty checks run **Claude Opus 4.8 first**. If Opus 4.8 already rates your task as Hard (≤ 20% accuracy), the **GPT-5.5 run is skipped** and the task is finalized as Hard.

This doesn't lose rigor: a task is Hard whenever **either** model scores ≤ 20%, so an Opus-4.8 Hard result already settles the rating — the GPT-5.5 run couldn't change it. The practical effect is that you'll sometimes see difficulty results from **only one model** instead of two. That's **expected behavior, not a bug** — if GPT-5.5 results are missing on a Hard-rated task, **do not flag it**. Tasks that aren't Hard on Opus 4.8 still run against both models.

## New Submission Policy

- **Easy blocked** for brand-new submissions
- **Python tasks** must be **hard**
- See [submission-diversity.md](../submission-diversity.md)

## Designing for Difficulty

### Hard (≤ 20% on best or worst model)

Requires one or more of:

- Deep domain expertise — knowledge LLMs haven't seen much
- Complex multi-step reasoning — 10+ sequential steps
- Subtle debugging — root cause analysis required
- Niche tools/languages — less common technologies

Techniques: bespoke rules buried in common patterns; obscure documentation; non-obvious root causes; domain-specific knowledge (blockchains, scientific computing).

### Medium (20–60% on worst model)

- Moderate complexity — 5–10 steps
- Some domain knowledge — common but not trivial
- Clear requirements — but non-obvious solution

Techniques: combine familiar concepts; edge cases; easy-to-miss configuration.

### Easy (60–80% on worst model)

Still non-trivial — not one-liners; multi-step (at least 3–5); clear success criteria. Standard tasks with one or two tricky aspects; well-known problems with specific constraints.

## Common Mistakes

| Too easy | Too unfair |
|----------|------------|
| Single-step solutions | Impossible requirements |
| Obvious debugging / pattern matching | Ambiguous instructions (luck) |
| Common tutorials in training data | Time-dependent / random results |
| Simple well-documented API usage | External dependency / env issues |

## Testing Your Difficulty

### 1. Oracle (must PASS)

```bash
stb harbor run -a oracle -p <task-folder>
# or: ./scripts/terminus oracle <task-folder>
```

### 2. Real agents (2–3+ runs each to gauge rate)

```bash
# GPT-5.5
stb harbor run -m @openai/gpt-5.5 -p <task-folder>

# Claude Opus 4.8
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

Auth: `stb login` / `stb keys refresh` (CLI manages AI credentials — no manual `OPENAI_API_KEY` / Harbor promptfix wheel). See [quick-start.md](quick-start.md).

Remember: the **worst** model's pass rate determines Easy/Medium for most tasks.

### 3. Analyze failures

- **Good:** agent misunderstood complexity, missed edge case
- **Bad:** ambiguous requirements, environment issues → fix the task

## Adjusting Difficulty

| Harder | Easier |
|--------|--------|
| More steps, hidden requirements | Reduce step count |
| Niche knowledge | Make requirements more explicit |
| Debugging scenarios, edge cases | Common technologies |
| | Simplify environment |

**Do not** add hints to instructions just to make tasks easier.

## Reviewer policy (portal #45 / #54)

- **Worst model** = **lowest** pass rate among models that ran (GPT-5.5 and/or Claude Opus 4.8).
- **#45:** **CHECK** when `difficulty` is present in `task.toml`. Mismatch vs platform `Difficulty: …` or vs agent-rate tier is **informational only** — never a blocker.
- **#54:** Block only when worst-model rate **>80%** (task too easy).
- **Single-model Hard exports:** missing GPT-5.5 (or only Claude present) on a Hard-rated task is **expected** after the Jul 21, 2026 early-exit policy — not a revision reason. See `.cursor/rules/terminus-platform-changelog.mdc`.
