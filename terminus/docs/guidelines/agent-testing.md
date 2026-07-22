# Testing Agent Performance

Auth via Snorkel CLI (no manual `OPENAI_*` exports):

```bash
stb login
stb keys refresh   # if AI credentials are missing or expired

stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

Run each model **5 times** for reliable pass rates (or at least 2–3 locally to gauge). Platform difficulty checks may skip GPT-5.5 when Claude Opus 4.8 already rates Hard — see [difficulty.md](difficulty.md).

## Difficulty

| Tier | Criteria |
|------|----------|
| Hard | ≤20% on **best** OR **worst** model |
| Medium | 20% < worst ≤ 60% |
| Easy | 60% < worst ≤ 80% |
| Rejected | worst > 80% |

## Interpreting Failures

**Good:** reasoning errors, missed edge cases, domain gaps  
**Bad:** ambiguous instructions, env bugs, missing info → revise task

## CLI Wrapper

```bash
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 5
./scripts/terminus agent <task-dir> --model claude-opus-4-8 --runs 5
```

## NOP Agent

Baseline that does nothing — **0% pass expected**. If NOP passes, task/eval is broken.

See [difficulty.md](difficulty.md), [quick-start.md](quick-start.md), and [submission-diversity.md](../submission-diversity.md).
