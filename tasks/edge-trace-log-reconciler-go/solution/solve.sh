#!/bin/bash
set -euo pipefail

cp /solution/log_reconciler.go /workspace/log_reconciler.go
mkdir -p /workspace/out
go run /workspace/log_reconciler.go /workspace/task_file/config.json /workspace/task_file/events.jsonl /workspace/out/report.json
