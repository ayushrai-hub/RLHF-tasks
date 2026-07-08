#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:/app/bin:${PATH}"
cd /app
cargo build --release -q
install -m 0755 target/release/geosynth /app/bin/geosynth
