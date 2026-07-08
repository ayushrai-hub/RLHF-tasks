#!/bin/bash
set -euo pipefail
cd /app
export PATH="/usr/local/cargo/bin:${PATH}"
export CARGO_INCREMENTAL=0
cargo build --release --locked
cp target/release/neural-echo-forge /app/neural-echo-forge
