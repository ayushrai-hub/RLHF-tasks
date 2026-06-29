#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${ROOT}/bin:${PATH}"
/app/environment/bin/var_check --matrix-full --out "${1:-/app/output/route_audit.json}"
