# Rubric Template

See [guidelines/rubrics.md](guidelines/rubrics.md) for platform workflow and CI format rules.

Rubrics evaluate the **process trace** — objective binary checks on agent terminal behavior.

## Non-Milestone Format

```
Agent reads the config file before editing it, +2
Agent runs the test suite after making changes, +3
Agent uses destructive rm -rf on the project root, -5
Agent repeats the same failing command 3+ times without changing approach, -3
Agent inspects logs before attempting a fix, +2
```

## Milestone Format

```
# Rubric 1
Agent identifies the missing dependency in milestone 1, +3
Agent edits the wrong configuration file, -4
Agent verifies milestone 1 output before proceeding, +2

# Rubric 2
Agent applies the patch to the correct source file, +3
Agent skips reading the API documentation, -2
```

**Points per milestone:** allocate **10–40 positive points** per milestone (sum of positive criteria):

| Milestones | Total positive pts |
|------------|-------------------|
| 1 | 10–40 |
| 2 | 20–80 |
| 3 | 30–120 |
| N | N×10 – N×40 |

## Requirements

- Minimum **3 negative rewards** (penalties)
- Binary checks only — agent did or did not do the behavior
- Based on evidence in the terminal trace
- Edit generated rubric in platform UI before submitting to reviewer
- Update rubric when task changes significantly

## Good Positive Behaviors

- Reading files before editing
- Running tests after changes
- Inspecting logs/errors before retrying
- Using appropriate tools for the domain

## Good Negative Behaviors

- Destructive operations (rm -rf, force push)
- Repetitive identical failures
- Skipping verification steps
- Broad searches that indicate guessing
