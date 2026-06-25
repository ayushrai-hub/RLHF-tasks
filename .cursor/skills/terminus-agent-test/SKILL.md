---
name: terminus-agent-test
description: Run oracle and AI agent difficulty tests on Terminus tasks using Harbor and stb. Use when testing agent performance, difficulty calibration, or running GPT-5.5 / Claude Opus 4.8 against a task.
---

# Terminus Agent Test

## Prerequisites

```bash
export OPENAI_API_KEY=<portkey-api-key>
export OPENAI_BASE_URL=https://api.portkey.ai/v1
stb keys show   # verify credentials
```

## Oracle (must pass first)

```bash
./scripts/terminus oracle <task-dir>
# or: stb harbor run -a oracle -p <task-dir>
```

## Agent Difficulty Testing

```bash
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 5
./scripts/terminus agent <task-dir> --model claude-opus-4-8 --runs 5
```

Run each model **2–5 times** to estimate pass rate.

## Difficulty Targets

| Rating | Worst-model pass rate |
|--------|----------------------|
| Hard | ≤ 20% |
| Medium | 20–60% |
| Easy | 60–80% |
| Rejected | > 80% |

## Interactive Debugging

```bash
stb harbor tasks start-env -p <task-dir> -i
```

## If Too Easy (>80%)

- Add implicit requirements or edge cases
- Increase environment complexity
- Require multi-step reasoning
- Add tests for behaviors agents commonly skip

## If Too Hard (0% both models)

- Clarify ambiguous instructions
- Ensure tests match prompt (no hidden requirements)
- Verify oracle still passes

## LLMaJ Pre-Submit

```bash
./scripts/terminus ci-check <task-dir>
harbor tasks check -m openai/@openai/gpt-5.5 <task-dir>
```

See `docs/submission-checklist.md` for full CI and LLMaJ check lists.
