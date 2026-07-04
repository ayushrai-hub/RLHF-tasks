#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p /workspace/output /workspace/stampgate-lib/lib/stamp_gate
cp "$SCRIPT_DIR"/StampGate/util.rb /workspace/stampgate-lib/lib/stamp_gate/
cp "$SCRIPT_DIR"/StampGate/policy_client.rb /workspace/stampgate-lib/lib/stamp_gate/

if ! curl -sf "http://127.0.0.1:8966/health" >/dev/null 2>&1; then
  /workspace/scripts/start-stampgate-api.sh
fi

ruby /workspace/stampgate-lib/bin/stampgate-audit policy \
  --api http://127.0.0.1:8966 \
  --out /workspace/output/policy-cache.json
