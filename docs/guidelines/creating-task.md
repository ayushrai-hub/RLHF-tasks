# Creating a Task

## 1. Choose Skeleton

```bash
stb init <task-name> -p "Terminus-2nd-Edition" -t base       # regular
stb init <task-name> -p "Terminus-2nd-Edition" -t milestone # milestones
stb init <task-name> -p "Terminus-2nd-Edition" -t ui         # UI building
```

## 2. Naming

Kebab-case, descriptive: `parse-json-logs`, `configure-nginx-ssl`

❌ `task1`, `my-task`, `test`

## 3. Develop

| Step | Guide |
|------|-------|
| Instructions | [prompt-styling.md](prompt-styling.md) |
| Metadata | [task-components.md](task-components.md) |
| Environment | [docker-environment.md](docker-environment.md) |
| Solution | [oracle-solution.md](oracle-solution.md) |
| Tests | [writing-tests.md](writing-tests.md) |
| Rubric | [rubrics.md](rubrics.md) (platform UI) |

## 4. Validate

```bash
./scripts/terminus check-all ./<task-name>
./scripts/terminus oracle ./<task-name>
./scripts/terminus ci-check ./<task-name>
./scripts/terminus agent ./<task-name> --runs 5
./scripts/terminus zip ./<task-name>
```

## 5. Submit

Platform: Terminus-2nd-Edition → upload ZIP (files inside folder) → rubric checkbox → CI → reviewer

See [submission-checklist.md](../submission-checklist.md).
