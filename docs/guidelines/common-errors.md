# Common Errors

Anti-patterns when creating or reviewing tasks. Maps to reviewer feedback categories.

## Instruction Problems

*Categories: `instruction_styling`, `expose_answers`*

| Bad | Good |
|-----|------|
| "Make it better" | "Reduce runtime by 50%" |
| `Edit config/settings.json` | `Edit /app/config/settings.json` |
| "Process data and save results" | "Process `/data/input.csv` → `/output/results.json`" |
| "Use vim to edit" | "Change port 8080→3000 in `/app/config.txt`" |

See [prompt-styling.md](prompt-styling.md).

## Test Problems

*Categories: `test_alignment`, `test_build`*

- **Brittle string match** → check key content / fields
- **Implementation testing** (grep source) → run code, test behavior
- **Missing docstrings** → every `test_*` needs docstring
- **Order-dependent tests** → each test independent
- **Hardcoded random** → test properties (length, membership)

## Solution Problems

*Category: `oracle`*

- **Hardcoded answers** → derive via commands
- **Non-deterministic** (`ls` without `sort`) → deterministic ordering
- **No error handling** → `set -euo pipefail`

## Environment Problems

*Category: `environment`* (distinct from `pinning`)

| Issue | Fix |
|-------|-----|
| Missing tmux/asciinema | Pre-install in Dockerfile |
| Runtime installs in test.sh | Bake deps in image |
| CLAUDE.md, skills.md, .cursor/ | Remove scaffolding |
| COPY solution/ or tests/ | COPY only agent-facing files |
| privileged / SYS_ADMIN / docker.sock | Standard sandbox |
| mkdir/chown /tests, /oracle | Use /app paths only |
| Heredocs for source | COPY real files |
| environment/ >100 MiB | Trim fixtures |
| Floating/latest base image | Digest-pinned canonical base |

## Cheating

*Categories: `expose_answers`, `test_alignment`*

- Tests baked in image → runtime mount only
- Git clone without pinned commit → `git checkout <sha>`
- Mutable data files → verify computation chain

## Difficulty

*Category: `task_difficulty`*

- Too easy: single-step, tutorials, pattern match
- Unfair: missing info, unreliable env, luck, contradictions

## Quick Reference Table

See full tables in platform docs. Cross-check: [reviewer-checklist-full.md](../reviewer-checklist-full.md), [quality-guidelines.md](quality-guidelines.md).
