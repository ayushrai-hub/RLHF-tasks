#!/usr/bin/env bash
# Wrapper — reorganize script lives in terminus/scripts/
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/terminus/scripts/reorganize-tasks.sh" "$@"
