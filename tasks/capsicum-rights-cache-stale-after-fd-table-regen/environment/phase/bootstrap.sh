#!/usr/bin/env bash
set -euo pipefail
cd /app/environment
exec cargo run --release --locked --bin k7_invoke -- "$@"
