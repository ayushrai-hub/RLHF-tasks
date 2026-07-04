#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:${PATH}"
export RUSTUP_HOME="${RUSTUP_HOME:-/usr/local/rustup}"
export CARGO_HOME="${CARGO_HOME:-/usr/local/cargo}"
export CARGO_INCREMENTAL=0
cd /app
cargo build --release --locked
mkdir -p /app/bin
cp /app/target/release/rtcmctl /app/bin/rtcmctl
chmod +x /app/bin/rtcmctl
