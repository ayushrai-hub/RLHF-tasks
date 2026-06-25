---
name: terminus-create-task
description: Create and scaffold Project Terminus Edition 2 benchmark tasks. Use when the user wants to create, author, initialize, or develop a new Terminus task, instruction.md, task.toml, Dockerfile, solution, or tests.
---

# Terminus Create Task

## Workflow

```
- [ ] Step 1: Initialize scaffold
- [ ] Step 2: Write instruction.md (what, not how)
- [ ] Step 3: Configure task.toml
- [ ] Step 4: Build environment/Dockerfile
- [ ] Step 5: Write solution/solve.sh
- [ ] Step 6: Write tests (test.sh + test_outputs.py)
- [ ] Step 7: Validate locally
- [ ] Step 8: Oracle + agent test
- [ ] Step 9: Rubric on platform + submit
```

## Step 1: Initialize

```bash
stb init <task-name> -p "Terminus-2nd-Edition" -t base      # regular
stb init <task-name> -p "Terminus-2nd-Edition" -t milestone  # milestones
stb init <task-name> -p "Terminus-2nd-Edition" -t ui       # UI building
```

## Step 2–6: Author

Follow rules in `.cursor/rules/terminus-*.mdc` and docs in `docs/guidelines/`.

Key constraints:
- `allow_internet = false`
- Digest-pin all FROM images
- Install tmux + asciinema
- No hints in environment files
- Absolute paths in instructions

## Step 7: Validate

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus check-all <task-dir>
```

Fix all errors before proceeding. See `docs/submission-checklist.md`.

## Step 8: Test

```bash
./scripts/terminus oracle <task-dir>
./scripts/terminus agent <task-dir> --model gpt-5.5 --runs 3
./scripts/terminus agent <task-dir> --model claude-opus-4-8 --runs 3
```

Target: worst-model pass rate < 80%.

## Step 9: Submit

1. Configure rubric on Snorkel platform (≥3 negative rewards)
2. `./scripts/terminus zip <task-dir>`
3. `stb submissions create <task-dir> -p "Terminus-2nd-Edition" --time <minutes>`

## References

- [submission-diversity.md](../../docs/submission-diversity.md)
- [milestones.md](../../docs/guidelines/milestones.md)
- [task-type-taxonomy.md](../../docs/task-type-taxonomy.md)
- [task-requirements.md](../../docs/task-requirements.md)
- [what-makes-a-good-task.md](../../docs/what-makes-a-good-task.md)
- [task-components.md](../../docs/guidelines/task-components.md)
- [dockerfile.md](../../docs/guidelines/dockerfile.md)
- [writing-tests.md](../../docs/guidelines/writing-tests.md)
- [rubric-template.md](../../docs/rubric-template.md)
