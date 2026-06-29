#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
patch -d /app -p1 --forward < "${ROOT_DIR}/patch.diff"

cd /app/environment
cargo build --locked --release --bin facility_sim

bash /app/environment/scripts/run_sim_driver.sh
