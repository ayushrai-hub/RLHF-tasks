#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --quiet -- staging-roundtrip --scenario "$1"
