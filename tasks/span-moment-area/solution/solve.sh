#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
patch -p1 -d /app/environment < oracle.patch
bash /app/environment/scripts/build.sh

/app/environment/bin/beam-envelope \
  --stage /app/environment/fixtures/simple/deck_base.beam \
  --combine service \
  --out /tmp/envelope_simple.json

test -s /tmp/envelope_simple.json
