#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/contfrac.cpp" /app/contfrac.cpp
cd /app && g++ -O2 -std=c++17 -o /app/contfrac /app/contfrac.cpp
