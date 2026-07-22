# Quick Start Guide

Get up and running with TerminalBench / Terminus Edition 2 in a few minutes.

## Prerequisites

- Access to the **Snorkel Expert Platform**
- Submit via the **Terminus-2nd-Edition** submission node
- Joined Slack `#terminus-2nd-edition` and announcements `terminus-2nd-edition-announcements`
- Set up the **Snorkel CLI** (`snorkelai-stb`) — see the Snorkel CLI user guide
- **Docker Desktop** v24.0.0+ installed and running

With the CLI you can check submission status, generate/refresh API keys, submit tasks, and run harbor agent/oracle jobs.

## Environment Setup

### Option A: Quick setup with uv (recommended)

1. Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install the Snorkel CLI (Python 3.12+):

```bash
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"
```

3. Log in and configure credentials:

```bash
stb login
stb keys refresh   # if AI credentials are missing or expired
```

The CLI manages AI credentials for agent runs. Do **not** use the retired Harbor promptfix wheel or manual `OPENAI_API_KEY` / `OPENAI_BASE_URL` exports.

4. You're ready to author and submit tasks.

### Option B: Manual / editor setup

Useful VS Code extensions: Docker, Python, Markdown, TOML, GitLens.

## Local repo helpers

This automation repo wraps common flows:

```bash
./scripts/terminus doctor
./scripts/terminus validate <task-folder>
./scripts/terminus oracle <task-folder>
./scripts/terminus agent <task-folder> --model gpt-5.5 --runs 3
./scripts/setup-review.sh
```

Platform-native equivalents:

```bash
stb harbor run -a oracle -p <task-folder>
stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

## Related

- [Difficulty Guidelines](difficulty.md) — tiers, one-model Hard early exit, agent calibration
- [Creating a task](creating-task.md)
- [Submission checklist](../submission-checklist.md)
- Platform changelog: `.cursor/rules/terminus-platform-changelog.mdc`
