# CI Iteration Workflow

```
Run checks → Identify failures → Fix → Re-run → Repeat
```

## Steps

```bash
harbor tasks check <task-folder> -m openai/@openai/gpt-5.5
```

1. Read output — CI vs LLMaJ sections
2. Fix **one issue** at a time (error messages include file, line, fix hint)
3. Re-run until all pass
4. Then oracle + agent testing

## Error Message Format

- Which check failed
- Where (file + line)
- What's wrong
- How to fix

## Tips

- Fix easy CI issues before LLMaJ quality checks
- Run locally before every platform submit
- One fix at a time for easier debugging

## Pre-Submit Checklist

- [ ] All CI checks pass
- [ ] All LLMaJ checks pass
- [ ] Oracle passes
- [ ] Agents tested (difficulty verified)

See [ci-checks.md](ci-checks.md) for per-check fixes.
