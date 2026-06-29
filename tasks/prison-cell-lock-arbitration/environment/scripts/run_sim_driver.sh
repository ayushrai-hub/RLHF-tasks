#!/usr/bin/env bash
set -euo pipefail
cd /app/environment
export PATH="/usr/local/cargo/bin:${PATH}"
exec ./target/release/facility_sim --output /app/output/failover_trace.json
