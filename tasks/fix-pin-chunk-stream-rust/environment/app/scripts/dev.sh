#!/usr/bin/env bash
set -euo pipefail
cd /app
export PATH="/usr/local/cargo/bin:${PATH}"
cargo check --workspace --locked
