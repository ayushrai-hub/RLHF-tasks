# Oracle Agent

Runs `solution/solve.sh` in the container, then tests. **Must pass** before submission.

```bash
stb harbor run -a oracle -p <task-folder>
./scripts/terminus oracle <task-folder>
```

Oracle runs **3 times** in CI.

## Expected

```
Building Docker environment...
Running oracle solution...
Running tests...
RESULT: PASS
```

## Debug Workflow

1. Read which step failed
2. `harbor tasks start-env -p <task-folder> -i` — run commands manually
3. Fix `solve.sh` or `environment/Dockerfile`
4. Re-run oracle

## Common Issues

| Error | Fix |
|-------|-----|
| command not found | Add dep to Dockerfile |
| file not found | Absolute paths; check COPY |
| permission denied | chmod in Dockerfile |
| test assertion failed | Fix solution logic or tests |
| timeout | Optimize or increase `timeout_sec` |

## Oracle vs Real Agents

| | Oracle | Real agents |
|---|--------|-------------|
| Solution | Your solve.sh | Agent-generated |
| Must pass? | Yes | May fail (desired) |
| Purpose | Task validity | Difficulty |

See [interactive-container.md](interactive-container.md).
