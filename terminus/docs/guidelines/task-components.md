# Task Components

Every Harbor task has required components that work together. Milestone tasks use `steps/` instead of root-level files — see [Task Requirements](../task-requirements.md#milestone-tasks).

## File Structure (Regular)

```
my-task-folder/
├── instruction.md          # Human-styled agent instructions
├── task.toml               # Metadata and configuration
├── environment/
│   ├── Dockerfile          # Single-container setup
│   ├── docker-compose.yaml # Optional: multi-container
│   └── [build files]
├── solution/
│   └── solve.sh            # Oracle solution
├── tests/
│   ├── test.sh             # Verifier entry point
│   └── test_outputs.py     # Python pytest assertions
└── README.md               # Optional
```

## 1. instruction.md

Human-written, realistic engineering prompts. Six principles:

1. **Concise** — no fluff
2. **Well specified** — clear requirements
3. **Interesting** — real problems
4. **No answers/hints** — what, not how
5. **Unique** — not derivative
6. **Absolute paths** — `/app/file.txt` always

## 2. task.toml

See [task-requirements.md](../task-requirements.md) for full schema.

Key fields: `category`, `subcategories`, `number_of_milestones`, `codebase_size`, `languages`, `tags` (3–6), timeouts, `allow_internet = false`.

## 3. environment/

Build context stays in `environment/` — prevents accidental COPY of task files.

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:<digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip install numpy==1.26.4 pandas==2.1.0

COPY app/ /app/
# Do NOT copy solution or tests
```

Container paths: `/logs/verifier/`, `/logs/agent/`, `/oracle/`, `/tests/`

## 4. solution/solve.sh

```bash
#!/bin/bash
set -euo pipefail
cd /app
# Step-by-step commands that reliably solve the task
```

- Deterministic, human-written, demonstrates command sequence
- No hardcoded final answers

## 5. tests/test.sh

```bash
#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

Reward block is canonical end — no trailing `exit` required.

## 6. tests/test_outputs.py

```python
"""Tests for the bug fix task."""

def test_empty_input_returns_empty_list():
    """Verify empty input is handled gracefully."""
    ...
```

- Docstring on file and every test function
- Test behavior, not implementation

## Milestone Layout

See [milestones.md](milestones.md) for full guide.

```
steps/milestone_1/ ... milestone_2/ ...
```

## Validation Checklist

Run: `./scripts/terminus validate <task-dir>`

See [submission-checklist.md](../submission-checklist.md) for full pre-submit workflow.
