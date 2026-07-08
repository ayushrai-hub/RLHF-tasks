#!/bin/bash
# Wrapper — rename UUID/submission task folders to canonical slugs
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/terminus/scripts/rename-tasks.py" "$@"
