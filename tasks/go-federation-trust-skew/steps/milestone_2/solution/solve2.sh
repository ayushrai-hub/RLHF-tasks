#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

env_root() {
    if [ -d "/app/environment" ]; then echo "/app/environment"; else echo "$ROOT_DIR/../../../environment"; fi
}

app_root="$(env_root)"

if grep -q 'return gen == live' "$app_root/tally/spool/eligible.go" \
   && grep -q 'return notAfterMs + slackMs' "$app_root/meter/tolerance.go" \
   && ! grep -q 'gen-1' "$app_root/tally/spool/select.go"; then
    echo "Milestone 2 fixes already present"
    exit 0
fi

cp "$ROOT_DIR/meter/tolerance.go" "$app_root/meter/tolerance.go"
cp "$ROOT_DIR/chorus/chrono/bounds.go" "$app_root/chorus/chrono/bounds.go"
cp "$ROOT_DIR/chorus/chrono/quantize.go" "$app_root/chorus/chrono/quantize.go"
cp "$ROOT_DIR/tally/spool/eligible.go" "$app_root/tally/spool/eligible.go"
cp "$ROOT_DIR/tally/spool/select.go" "$app_root/tally/spool/select.go"

cd "$app_root"
go build ./...

echo "Milestone 2 oracle complete"
