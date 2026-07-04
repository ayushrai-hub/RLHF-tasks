# LLMaJ Checks Reference

LLM-as-Judge checks use **GPT-5.5** to evaluate task quality beyond syntax.

## Run Locally

```bash
harbor tasks check <task-folder> -m openai/@openai/gpt-5.5
./scripts/terminus ci-check <task-folder>
# With JSON output:
harbor tasks check -m openai/@openai/gpt-5.5 -o output.json <task-folder>
```

## Checks

### behavior_in_task_description

All tested behavior must appear in `instruction.md`.

**Fix:** Review each test; add explicit requirements to instructions.

```markdown
# instruction.md must mention what tests check:
Output a CSV with headers: id, name, value
```

### behavior_in_tests

All instruction requirements must have tests.

**Fix:** Map each requirement → test function; add missing tests.

### informative_test_docstrings

Every test function needs a docstring explaining what it verifies.

```python
def test_output_file_has_correct_format():
    """Verify output.json contains 'status' and 'items' fields."""
```

### anti_cheating_measures

Task must resist shortcuts: reading tests, editing data files, deleting tests, git history leaks.

**Fix:** Pin git commits; don't expose test logic; verify computation not hardcoded outputs.

### structured_data_schema

Structured outputs (JSON, CSV, etc.) need exact schema in instructions.

```markdown
Output JSON:
{"status": "success"|"error", "count": <int>, "items": [{"id": <int>, "name": <string>}]}
```

### hardcoded_solution

`solve.sh` must show command sequence, not echo answers.

```bash
# Bad: echo "42" > /output/result.txt
# Good: python calculate.py input.txt > /output/result.txt
```

### file_reference_mentioned

Files checked by tests must be named in `instruction.md`.

```markdown
Save results to /output/analysis.json
```

## Quick Reference

| Check | Fix |
|-------|-----|
| behavior_in_task_description | Add requirements to instruction.md |
| behavior_in_tests | Add tests for requirements |
| informative_test_docstrings | Docstrings on all tests |
| anti_cheating_measures | Remove cheat vectors |
| structured_data_schema | Define exact format |
| hardcoded_solution | Derive answers in solve.sh |
| file_reference_mentioned | Name output files in instructions |

## Debugging

1. Read LLMaJ feedback
2. Identify specific test/requirement gap
3. Targeted fix (don't rewrite everything)
4. Re-run `ci-check`

See [ci-iteration.md](ci-iteration.md).
