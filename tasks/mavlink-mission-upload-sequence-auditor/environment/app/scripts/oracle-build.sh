#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:${PATH}"
cd /app
cargo build --release --locked
install -m 0755 target/release/mission-ingest /app/bin/mission-ingest
install -m 0755 target/release/mission-export /app/bin/mission-export
