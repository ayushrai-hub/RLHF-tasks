# Submission Checklist

Use before every submission. For component details see [Task Requirements](task-requirements.md).

## Pre-Submission Verification

### Task Design

- [ ] Problem statement is clear and unambiguous
- [ ] All requirements are explicitly stated
- [ ] Uses absolute paths (e.g., `/app/file.txt`)
- [ ] Output files are named in instructions
- [ ] Data schemas are fully specified
- [ ] Difficulty target: **< 80%** pass rate; new submissions must be **medium or hard** (easy blocked)
- [ ] `category` set from [9-type taxonomy](task-type-taxonomy.md)
- [ ] Consider milestone format for complex tasks ([preferred](submission-diversity.md))

### Required Files

**Always required:**

- [ ] `task.toml` — complete configuration (see [Task Requirements](task-requirements.md))
- [ ] `environment/Dockerfile` — builds successfully; deps pinned; digest-pinned FROM; canonical base (or justified); size limits

**Non-milestone** (`number_of_milestones = 0`):

- [ ] `instruction.md` — clear, human-written
- [ ] `solution/solve.sh` — deterministic oracle
- [ ] `tests/test.sh` — pytest + reward file; no runtime installs
- [ ] `tests/test_outputs.py` — pytest with docstrings

**Milestone** (`number_of_milestones >= 2`):

- [ ] One `[[steps]]` block per milestone (count = `number_of_milestones`)
- [ ] No root-level `instruction.md`, `tests/`, `solution/`, or `milestone_x.md`
- [ ] Per milestone `steps/milestone_N/`: `instruction.md`, `tests/test.sh`, `tests/test_mN.py`, `solution/solve.sh`, `solution/solveN.sh`

### Rubric

- [ ] Generated via Snorkel platform UI, edited for accuracy
- [ ] At least **3 negative rewards** (e.g., -1)
- [ ] Milestone tasks: `# Rubric 1`, `# Rubric 2` headers; **10–40 positive pts per milestone** ( **>40 = main blocker** )

### Quality Standards

- [ ] Every requirement has a corresponding test
- [ ] Full prompt coverage (explicit, implicit, edge cases)
- [ ] Python pytest only
- [ ] Anti-cheating measures (no hints/exposed answers)
- [ ] Tests check behavior, not implementation

## Automated Checks

### Oracle Agent

```bash
harbor run -a oracle -p <task-folder>
# or: ./scripts/terminus oracle <task-folder>
```

- [ ] Oracle agent **PASSES**

### CI Checks (must pass)

```bash
harbor tasks check <task-folder> -m openai/@openai/gpt-5.5
```

| Check | Status |
|-------|--------|
| pinned_dependencies | |
| check_pinned_images | |
| check_sanctioned_base_images | |
| check_build_context_size | |
| typos | |
| tests_or_solution_in_image | |
| check_dockerfile_references | |
| check_test_sh | |
| check_task_absolute_path | |
| check_privileged_containers | |
| ruff | |
| check_task_sizes | |
| validate_task_fields | |

**Warnings** (fix unless reviewer-approved exception):

- check_dockerignore, check_dockerfile_hygiene, check_offline_tests
- check_apt_usage, check_reproducible_builds, check_layer_volatility
- check_no_build_tools_in_runtime, check_file_extraction
- check_heredoc_usage, check_recursive_permissions

### LLMaJ Checks (must pass)

See [guidelines/llmaj-checks.md](guidelines/llmaj-checks.md).

- [ ] behavior_in_task_description
- [ ] behavior_in_tests
- [ ] informative_test_docstrings
- [ ] anti_cheating_measures
- [ ] structured_data_schema
- [ ] hardcoded_solution
- [ ] file_reference_mentioned

## Real Agent Testing

```bash
stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

Run each model **2–3+ times**:

| Model | Run 1 | Run 2 | Run 3 |
|-------|-------|-------|-------|
| GPT-5.5 | | | |
| Claude Opus 4.8 | | | |

### Difficulty Calculation

| Tier | Criteria |
|------|----------|
| Hard | ≤20% on best OR worst model |
| Medium | 20–60% on worst model |
| Easy | 60–80% on worst model |

- Worst-model pass rate: ____%
- Best-model pass rate: ____%
- Difficulty: Easy / Medium / Hard

**>80% worst-model = rejected**

## Final Review

- [ ] [Reviewer Checklist](reviewer-checklist.md) complete

### Self-Check Questions

| Question | If no → |
|----------|---------|
| Would a first-time reader understand this? | Clarify instructions |
| Any ambiguous requirements? | Make explicit |
| Could an agent cheat? | Add anti-cheating measures |
| Do tests verify behavior? | Rewrite tests |
| Is solution deterministic? | Add seeds, remove randomness |

## Submission

- [ ] ZIP of **files inside** folder (not the folder itself)
- [ ] All required files in ZIP
- [ ] Uploaded to Terminus-2nd-Edition on Snorkel platform
- [ ] Metadata filled in
- [ ] Rubric checkbox completed in UI

```bash
./scripts/terminus zip <task-folder>
stb submissions create <task-folder> -p "Terminus-2nd-Edition" --time <minutes>
```

See [After Submission](after-submission.md) for what happens next.
