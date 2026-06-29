#!/bin/bash
set -euo pipefail

SESSION_OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-out)
      SESSION_OUT="$2"
      shift 2
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$SESSION_OUT" ]]; then
  echo "--session-out required" >&2
  exit 2
fi

mkdir -p "$(dirname "$SESSION_OUT")"
rm -rf /app/output/store

/app/environment/scripts/stop_host.sh || true
/app/environment/scripts/start_host.sh
/app/environment/scripts/build_m3.sh

python3 /app/environment/scripts/step_driver.py suite \
  --seeds /app/environment/data/verifier_seeds.json \
  --session-out "$SESSION_OUT"

/app/environment/scripts/stop_host.sh
