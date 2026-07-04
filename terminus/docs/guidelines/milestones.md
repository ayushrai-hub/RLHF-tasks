# Understanding Milestones

Milestones divide complex engineering tasks into **sequential, independently verified subtasks**. Harbor calls these **multi-step tasks** — the terms are interchangeable.

## The Milestone Rule

Each stage is a **prerequisite** for the next. The agent works milestones in order; each is verified before the next runs. Files **persist** across milestones in the shared container filesystem.

## Structure

```
your-task/
├── task.toml
├── environment/
│   └── Dockerfile
└── steps/
    ├── milestone_1/
    │   ├── instruction.md
    │   ├── tests/
    │   │   ├── test.sh
    │   │   └── test_m1.py      # class TestMilestone1
    │   └── solution/
    │       ├── solve.sh         # wrapper → solve1.sh
    │       └── solve1.sh
    ├── milestone_2/
    │   └── ...
    └── milestone_3/
        └── ...
```

**No** root-level `instruction.md`, `tests/`, `solution/`, or `milestone_x.md`.

## Components

### 1. Per-Milestone Instructions

- `steps/milestone_N/instruction.md` — prompt for milestone N only
- Milestone 1 includes overall task context
- Later milestones describe new requirements only

### 2. Per-Milestone Verifiers

- `test.sh` — runs pytest, writes `/logs/verifier/reward.txt`
- `test_mN.py` — `TestMilestoneN` class; scores **only** milestone N
- Deterministic; tolerate state from prior milestones

### 3. Per-Milestone Oracle

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve1.sh"
```

- `solve.sh` — thin wrapper
- `solveN.sh` — oracle commands for milestone N only

### 4. task.toml

```toml
version = "2.0"

[metadata]
number_of_milestones = 2
# ... other metadata ...

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
workdir = "/app"

[[steps]]
name = "milestone_1"

[steps.agent]
timeout_sec = 1200.0

[steps.verifier]
timeout_sec = 450.0

[[steps]]
name = "milestone_2"

[steps.agent]
timeout_sec = 1200.0

[steps.verifier]
timeout_sec = 450.0
```

**Rules:**

- `number_of_milestones` must equal `[[steps]]` count
- `[[steps]].name` must be `milestone_1`, `milestone_2`, … matching directory names
- **No** top-level `[agent]` or `[verifier]` — use per-milestone `[steps.agent]` / `[steps.verifier]`
- `[environment]` applies globally (shared container)

### 5. Rubric

- Cover all milestones with `# Rubric 1`, `# Rubric 2`, etc.
- **10–40 positive points per milestone** (sum of positive criteria); **>40 per block or non-milestone total = main blocker (Revise)**
- 2 milestones → 20–80 pts total; 3 → 30–120 pts; same pattern beyond
- ≥3 negative rewards across the full rubric

## Best Practices

| Practice | Why |
|----------|-----|
| No leaky milestones | Milestone 2 must not pass if milestone 1 failed |
| Clear boundaries | Agent knows when each milestone is done |
| 2–5 milestones | Avoid over-segmenting; combine related steps |
| Mind shared filesystem | Milestone 2 sees files from milestone 1; reset paths in solveN.sh if needed |
| No root-level task files | Everything per-milestone under `steps/milestone_N/` |

## Initialize

```bash
stb init my-milestone-task -p "Terminus-2nd-Edition" -t milestone
./scripts/terminus validate ./my-milestone-task
```

See [Submission Diversity](submission-diversity.md) — milestone tasks are preferred for new submissions.
