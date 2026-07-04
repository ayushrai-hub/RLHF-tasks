#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  clean)
    mkdir -p /app/output/inc_store
    echo '{"seq": -99}' > /app/output/inc_store/seed.json
    ;;
  recover)
    mkdir -p /app/output/inc_store
    cp /app/environment/fixtures/inc_seed.json /app/output/inc_store/seed.json
    ;;
  *)
    echo "usage: rst7.sh clean|recover" >&2
    exit 2
    ;;
esac
