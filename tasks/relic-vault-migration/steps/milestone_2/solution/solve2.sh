#!/bin/bash
# Milestone 2 -- Migrate Puzzle Database.
# Reuses the harness completed in milestone 1 to write the binary vault.pack.
set -euo pipefail
mkdir -p /app/out

python /app/harness/migrate.py pack --archive /app/archive --out /app/out
