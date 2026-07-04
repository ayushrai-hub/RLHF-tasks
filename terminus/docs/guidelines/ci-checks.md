# CI Checks Reference

Run locally:

```bash
./scripts/terminus ci-check <task-dir>
harbor tasks check <task-folder> -m openai/@openai/gpt-5.5
```

## Blocking Checks

| Check | Fix |
|-------|-----|
| `check_pinned_images` | Add `@sha256:<digest>` to every `FROM` |
| `check_sanctioned_base_images` | Use [canonical base](dockerfile.md) or justify |
| `check_build_context_size` | `environment/` ≤ 100 MiB, files ≤ 50 MiB |
| `pinned_dependencies` | Pin pip/npm/etc. with `==` or lockfiles |
| `tests_or_solution_in_image` | Remove `COPY solution/` / `COPY tests/` |
| `check_dockerfile_references` | No refs to solution/test files in Dockerfile |
| `check_test_sh` | pytest + reward.txt; no runtime installs |
| `check_task_absolute_path` | Absolute paths in instructions |
| `check_privileged_containers` | Remove `privileged: true` |
| `validate_task_fields` | Complete `task.toml` |
| `ruff` | `ruff check --fix <task-dir>` |
| `typos` | Fix spelling in names |
| `check_task_sizes` | Reduce oversized task files |

## Warning Checks (fix unless reviewer-approved)

`check_dockerignore`, `check_dockerfile_hygiene`, `check_offline_tests`, `check_apt_usage`, `check_reproducible_builds`, `check_layer_volatility`, `check_no_build_tools_in_runtime`, `check_file_extraction`, `check_heredoc_usage`, `check_recursive_permissions`

## LLMaJ (must pass)

See [llmaj-checks.md](llmaj-checks.md) for per-check fixes.

`behavior_in_task_description`, `behavior_in_tests`, `informative_test_docstrings`, `anti_cheating_measures`, `structured_data_schema`, `hardcoded_solution`, `file_reference_mentioned`

## Iteration

See [ci-iteration.md](ci-iteration.md): fix one failure at a time, re-run until clean.
