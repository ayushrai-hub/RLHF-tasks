#!/bin/bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
cd /app/environment
cargo build --release -p streamkit --bin stream-stats
install -m 0755 target/release/stream-stats /usr/local/bin/stream-stats
