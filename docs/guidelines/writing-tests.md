# Writing Tests

Verifier = **Python pytest** always. `test.sh` runs pytest and writes reward file.

## test.sh (canonical)

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

- Reward block = **canonical end** (no trailing `exit`)
- `rc=$?` immediately after pytest (preferred)
- **No** runtime installs (apt, pip, curl, wget, npm)
- Deps pre-installed in Dockerfile

## test_outputs.py

```python
"""Tests for the data processing task."""

def test_output_file_exists():
    """Verify the output file was created."""
    assert Path("/output/result.json").exists()
```

### Principles

1. **Test behavior, not implementation** — run code, check results
2. **Docstrings** on module + every test (CI: `informative_test_docstrings`)
3. **Full prompt coverage** — explicit + implicit + edge cases
4. **One test per requirement** minimum

### Implicit edge cases

Prompt: "function divide two numbers" → also test division by zero.

## Milestone

`steps/milestone_N/tests/test_mN.py` with `class TestMilestoneN` — scores only milestone N.

## Anti-Patterns

- Parsing source for patterns (`assert "if not" in source`)
- Brittle exact string matches
- Order-dependent tests
- Hardcoded random outputs

## CI Validation

`behavior_in_tests`, `behavior_in_task_description`, `informative_test_docstrings`, `ruff`

## Patterns

- File output: pathlib + format checks
- API: `requests` against localhost
- DB: sqlite3 queries
- CLI: `subprocess.run`

Non-Python tasks: pytest calls CLI/service/files — never replace pytest with Jest/JUnit/go test in test.sh.
