#!/usr/bin/env bash
set -euo pipefail
cd /app
export PATH="/usr/local/cargo/bin:${PATH}"
cargo fmt --all
cargo clippy --workspace --locked -- -D warnings
