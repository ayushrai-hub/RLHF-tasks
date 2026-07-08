#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
mkdir -p "$BUILD" /app/output /app/var/grad

export PATH="/usr/local/go/bin:/usr/local/cargo/bin:${PATH}"

cd "$ROOT/xk9"
cargo build --release --offline 2>/dev/null || cargo build --release
install -m 755 "$ROOT/xk9/target/release/corevm" "$BUILD/corevm"

cd "$ROOT"
go mod tidy
go build -o "$BUILD/gradctl-run" ./cmd/gradctl-run
go build -o "$BUILD/gradctl-probe" ./cmd/gradctl-probe
go build -o "$BUILD/gradctl-audit" ./cmd/gradctl-audit
go build -o "$BUILD/gradctl-inspect" ./cmd/gradctl-inspect
