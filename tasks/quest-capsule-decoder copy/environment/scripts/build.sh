#!/bin/bash
# Build the SQLite cartridge from its SQL source and prepare the output directory.
set -euo pipefail

CART_DIR=/app/cartridges
DB="$CART_DIR/quests.cartridge.db"

rm -f "$DB"
sqlite3 "$DB" < "$CART_DIR/quests.cartridge.sql"
mkdir -p /app/out
