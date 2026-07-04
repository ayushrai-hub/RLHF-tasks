# Submission Diversity Requirements

New automated evaluations block certain task properties to improve dataset variance. Applies to **brand new submissions** — tasks already in review or revision queue are exempt.

## Restrictions & Preferences

| Dimension | Policy |
|-----------|--------|
| **Codebase size** | `minimal`, `small`, and `large` all accepted — aim for variety across your portfolio |
| **Milestones** | Non-milestone tasks not blocked; **milestone tasks preferred** (higher pay) |
| **Model difficulty** | Only **medium** and **hard** accepted — **easy blocked** |
| **Python tasks** | Must be **hard** model difficulty to be accepted |
| **Category** | No restrictions |
| **Subcategory** | No restrictions |
| **Languages** | All accepted |

> **Note:** Easy/medium/hard here refers to **model pass rates** on frontier agents (GPT-5.5, Claude Opus 4.8), not the `difficulty` field in `task.toml`.

## Model Difficulty Reference

| Tier | Worst-model pass rate |
|------|----------------------|
| Hard | ≤ 20% |
| Medium | 20–60% |
| Easy | 60–80% |
| **Blocked** | **> 80%** (too easy) |

New submissions rated **easy** by agent evaluation will be blocked.

## Portfolio Tips

- Vary `codebase_size` across submissions
- Consider milestone format for complex multi-step tasks
- Calibrate difficulty before submit: `./scripts/terminus agent <task-dir> --runs 5`
- Python-heavy tasks: target hard tier (≤20% worst-model)

## Verify Before Submit

```bash
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 5
./scripts/terminus agent <task-dir> --model claude-opus-4-8 --runs 5
```

If worst-model pass rate is 60–80% (easy tier), strengthen the task before submitting a new submission.

See [What Makes a Good Task](what-makes-a-good-task.md) and [Submission Checklist](submission-checklist.md).
