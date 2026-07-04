#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --quiet -- double-fold --scenario "$1"
