#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
cd /app/environment
patch -p1 < "$ROOT_DIR/fix.patch"
make build
