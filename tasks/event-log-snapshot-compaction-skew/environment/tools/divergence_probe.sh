#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --quiet -- probe --scenario "$1"
