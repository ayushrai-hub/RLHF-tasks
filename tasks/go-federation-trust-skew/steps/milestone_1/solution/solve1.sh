#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

env_root() {
    if [ -d "/app/environment" ]; then echo "/app/environment"; else echo "$ROOT_DIR/../../../environment"; fi
}

app_root="$(env_root)"

if grep -q 'return notAfterMs + slackMs' "$app_root/meter/tolerance.go" \
   && grep -q 'return anchorMs' "$app_root/chorus/chrono/quantize.go"; then
    echo "Milestone 1 fixes already present"
    exit 0
fi

cp "$ROOT_DIR/meter/tolerance.go" "$app_root/meter/tolerance.go"
cp "$ROOT_DIR/chorus/chrono/bounds.go" "$app_root/chorus/chrono/bounds.go"
cp "$ROOT_DIR/chorus/chrono/quantize.go" "$app_root/chorus/chrono/quantize.go"

cd "$app_root"
go build ./...

echo "Milestone 1 oracle complete"
