#!/usr/bin/env bash
set -euo pipefail

if ! pg_isready -q 2>/dev/null; then
  service postgresql start >/dev/null 2>&1 || true
fi

for _ in $(seq 1 30); do
  if pg_isready -q 2>/dev/null; then
    exit 0
  fi
  sleep 1
done
echo "postgresql did not become ready" >&2
exit 1
