#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES="${SCRIPT_DIR}/patches"

cp "${PATCHES}/reader.go" "${APP_ROOT}/internal/parse/reader.go"
cp "${PATCHES}/sorter.go" "${APP_ROOT}/internal/order/sorter.go"
cp "${PATCHES}/correct.go" "${APP_ROOT}/internal/drift/correct.go"
cp "${PATCHES}/checksum.go" "${APP_ROOT}/internal/validate/checksum.go"
cp "${PATCHES}/types.go" "${APP_ROOT}/internal/format/types.go"
cp "${PATCHES}/replay-pack.sh" "${APP_ROOT}/scripts/replay-pack.sh"
cp "${PATCHES}/replay-unpack.sh" "${APP_ROOT}/scripts/replay-unpack.sh"
chmod +x "${APP_ROOT}/scripts/replay-pack.sh" "${APP_ROOT}/scripts/replay-unpack.sh"

cd "${APP_ROOT}"
go build -mod=vendor -o /app/bin/replay-chronicle ./cmd/replay-chronicle
