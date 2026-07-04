#!/usr/bin/env bash
set -euo pipefail
test -f /app/environment/config/pipeline.json
test -f /app/environment/docs/reconcile_contract.md
test -x /app/bin/ingressctl
