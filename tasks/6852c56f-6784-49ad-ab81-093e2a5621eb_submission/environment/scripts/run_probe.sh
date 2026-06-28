#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --offline --quiet
