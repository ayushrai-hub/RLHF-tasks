#!/usr/bin/env bash
# Session start hook: inject Terminus automation context
set -euo pipefail

python3 -c "
import json
msg = '''Terminus automation system active. Key commands:
- ./scripts/terminus validate <task-dir>
- ./scripts/terminus check-all <task-dir>
- Skills: @terminus-create-task, @terminus-review-task, @terminus-validate, @terminus-agent-test
- Docs: docs/guidelines/, docs/reviewer-checklist.md'''
print(json.dumps({'additional_context': msg}))
"
