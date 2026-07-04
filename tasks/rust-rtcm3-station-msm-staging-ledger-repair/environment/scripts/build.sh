#!/usr/bin/env bash
set -euo pipefail
cd /app
cargo build --release --locked
mkdir -p /app/bin
cp /app/target/release/rtcmctl /app/bin/rtcmctl
chmod +x /app/bin/rtcmctl
