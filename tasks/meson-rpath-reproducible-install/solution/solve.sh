#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
cd /app/environment
patch -p0 < "$ROOT_DIR/fix.patch"
make clean
make package
