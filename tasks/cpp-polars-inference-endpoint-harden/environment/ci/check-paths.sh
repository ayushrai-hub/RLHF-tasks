#!/usr/bin/env bash
set -euo pipefail
required=(
  /app/bin/score-server
  /app/docs/inference-operations-dossier.md
  /app/environment/sidecar/poetry.lock
  /app/environment/config/endpoint_defaults.toml
  /app/environment/config/model_weights.json
)
for path in "${required[@]}"; do
  test -e "$path"
done
