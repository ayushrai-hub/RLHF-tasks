#!/usr/bin/env bash
set -euo pipefail
cd /app
mkdir -p /app/build /app/output
gcc -std=c11 -O2 -Wall /app/native/drift/current_adjust.c /app/native/drift/current_math.c -lm -o /app/build/current_adjust
gcc -std=c11 -O2 -Wall /app/native/drift/repair_duration_adjust.c /app/native/drift/repair_duration.c -lm -o /app/build/repair_duration
lua5.4 /app/policies/splice/emit_rules.lua > /app/build/splice_rules.csv
cargo run --quiet --bin glassreef-planner -- --mission-id glassreef-primary --output /app/output/repair_plan.json
