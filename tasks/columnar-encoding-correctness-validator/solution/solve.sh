#!/usr/bin/env bash
set -euo pipefail

cd /app

SOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SOL_DIR}/reconcile.go" /app/codec/reconcile/reconcile.go

make build

test -x /app/bin/columnar-validator
test "$(wc -c < /app/bin/columnar-validator | tr -d ' ')" -gt 2048

mkdir -p /app/output
rm -f /app/output/encoding_integrity_report.json
/app/bin/columnar-validator
test -s /app/output/encoding_integrity_report.json
