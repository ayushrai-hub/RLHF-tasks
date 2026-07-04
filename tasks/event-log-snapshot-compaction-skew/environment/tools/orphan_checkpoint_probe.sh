#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --quiet -- orphan-checkpoint --scenario "$1"
