# Testing Agent Performance

```bash
export OPENAI_API_KEY=<portkey-key>
export OPENAI_BASE_URL=https://api.portkey.ai/v1

stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

Run each model **5 times** for reliable pass rates.

## Difficulty

| Tier | Worst-model rate |
|------|------------------|
| Hard | ≤20% |
| Medium | 20–60% |
| Easy | 60–80% |
| Rejected | >80% |

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

See [difficulty.md](difficulty.md) and [submission-diversity.md](../submission-diversity.md).
