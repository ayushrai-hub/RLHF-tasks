# Writing Oracle Solution

`solution/solve.sh` — expert script that reliably completes the task. Milestone: `steps/milestone_N/solution/solveN.sh` + wrapper `solve.sh`.

## Structure

```bash
#!/bin/bash
set -euo pipefail

cd /app
# Step-by-step commands — derive answer, don't echo it
sed -i 's/bug/fix/' main.py
python -c "from main import process; assert process('') == []"
```

## Principles

| Principle | Detail |
|-----------|--------|
| Command sequence | Show steps, not hardcoded final answer |
| Deterministic | Seeds for randomness; no network |
| Human-written | Not LLM-generated |
| Idempotent | Safe to re-run |
| Fail fast | `set -euo pipefail` |

## Milestone Wrapper

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve1.sh"
```

## Anti-Patterns

```bash
# WRONG
echo "42" > /output/answer.txt

# RIGHT
python calculate.py > /output/answer.txt
```

## Test

```bash
harbor tasks start-env -p <task-folder> -i   # manual steps
./scripts/terminus oracle <task-folder>       # automated
```

Oracle must **PASS** before agent testing.

See [oracle-agent.md](oracle-agent.md).
