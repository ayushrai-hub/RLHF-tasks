#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
bash apply_t2_pull.sh
bash apply_tape_lane.sh
bash apply_delta_lane.sh
bash apply_k9_filter.sh
bash apply_k9_mux.sh
bash apply_stage_seal.sh
cmake -S /app/environment -B /app/build -G Ninja
ninja -C /app/build
mkdir -p /app/output /app/var/vlt_journal
/app/build/vlt_run /app/environment/fixtures/z7bind.json /app/output/vlt_report.json --reset
