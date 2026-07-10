#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${TASK_APP_DIR:-/app}"
ENV_DIR="$APP_DIR/environment"
BIN_DIR="$APP_DIR/bin"
OUT_DIR="$APP_DIR/output"

mkdir -p "$BIN_DIR" "$OUT_DIR"
cd "$ENV_DIR"
cargo build --quiet --release
cp "$ENV_DIR/target/release/rookline" "$BIN_DIR/rookline"
"$BIN_DIR/rookline" prove \
  --cases "$ENV_DIR/fixtures/public_cases.rtl" \
  --out "$OUT_DIR/tournament-appeal-proof.json"
