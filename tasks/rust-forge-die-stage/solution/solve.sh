#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app
cp "$ROOT_DIR/fixed/"*.rs src/

mkdir -p /app/bin /app/output /app/output/state
/usr/local/cargo/bin/cargo build --release --locked
install -m 0755 target/release/forge_stage /app/bin/forge_stage

/app/bin/forge_stage --stage /app/fixtures/bundle_delta \
  --emit-log /app/output/forge_log.jsonl \
  --emit-report /app/output/forge_report.json \
  --die-root /app/data/dies \
  --state-dir /app/output/state

/app/bin/forge_stage --stage-recover /app/fixtures/bundle_recovery \
  --emit-log /app/output/recover_log.jsonl \
  --emit-report /app/output/recover_report.json \
  --die-root /app/data/dies \
  --state-dir /app/output/state \
  --snapshot /app/snapshot/forge_baseline.json

test -s /app/output/forge_report.json
test -s /app/output/recover_report.json
