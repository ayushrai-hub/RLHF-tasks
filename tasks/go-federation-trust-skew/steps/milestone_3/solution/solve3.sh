#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

env_root() {
    if [ -d "/app/environment" ]; then echo "/app/environment"; else echo "$ROOT_DIR/../../../environment"; fi
}

app_root="$(env_root)"

if grep -q 'bindHost' "$app_root/parcel/realm/norm.go" \
   && grep -q 'ResolvePrincipal(e.mp, ext, live)' "$app_root/internal/ward/stage_alias.go" \
   && ! grep -q 'tableEpoch' "$app_root/internal/ward/coordinator.go"; then
    echo "Milestone 3 fixes already present"
    exit 0
fi

cp "$ROOT_DIR/meter/tolerance.go" "$app_root/meter/tolerance.go"
cp "$ROOT_DIR/chorus/chrono/bounds.go" "$app_root/chorus/chrono/bounds.go"
cp "$ROOT_DIR/chorus/chrono/quantize.go" "$app_root/chorus/chrono/quantize.go"
cp "$ROOT_DIR/tally/spool/eligible.go" "$app_root/tally/spool/eligible.go"
cp "$ROOT_DIR/tally/spool/select.go" "$app_root/tally/spool/select.go"
cp "$ROOT_DIR/parcel/realm/norm.go" "$app_root/parcel/realm/norm.go"
cp "$ROOT_DIR/relay/alias/lookup.go" "$app_root/relay/alias/lookup.go"
cp "$ROOT_DIR/internal/ward/stage_alias.go" "$app_root/internal/ward/stage_alias.go"
cp "$ROOT_DIR/internal/ward/coordinator.go" "$app_root/internal/ward/coordinator.go"

cd "$app_root"
go build ./...

echo "Milestone 3 oracle complete"
