#!/bin/bash
set -euo pipefail

export PATH="/usr/local/cargo/bin:/usr/local/bin:/opt/verifier-venv/bin:${PATH}"
export CARGO_NET_OFFLINE=true
export CARGO_INCREMENTAL=0

cd /app
cargo build --release --locked --offline
cp target/release/ota_chain /app/bin/ota-chain
chmod +x /app/bin/ota-chain
test -x /app/bin/ota-chain
