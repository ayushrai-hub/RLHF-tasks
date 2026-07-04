#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p /workspace/output /workspace/stampgate-lib/lib/stamp_gate
cp "$SCRIPT_DIR"/StampGate/*.rb /workspace/stampgate-lib/lib/stamp_gate/
cp "$SCRIPT_DIR/jws_verify_helper.py" /tmp/stampgate-oracle-jws-verify.py
chmod +x /tmp/stampgate-oracle-jws-verify.py

if ! curl -sf "http://127.0.0.1:8966/health" >/dev/null 2>&1; then
  /workspace/scripts/start-stampgate-api.sh
fi

ruby /workspace/stampgate-lib/bin/stampgate-audit policy \
  --api http://127.0.0.1:8966 \
  --out /workspace/output/policy-cache.json

ruby /workspace/stampgate-lib/bin/stampgate-audit verify \
  --api http://127.0.0.1:8966 \
  --ledger /workspace/data/assertion-ledger.csv \
  --policy /workspace/output/policy-cache.json \
  --out /workspace/output/jws-window-check.json
