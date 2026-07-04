#!/bin/bash
# Benchmark runner for file-deduplicator
set -euo pipefail

DATA_DIR="${1:-/app/data/sample_files}"
OUTPUT_DIR="/app/output"
REPORT_FILE="${OUTPUT_DIR}/benchmark_report.json"
CONFIG_FILE="/app/benchmarks/bench_config.json"

mkdir -p "$OUTPUT_DIR"

# Generate fresh test data
bash /app/scripts/generate_test_data.sh "$DATA_DIR"

echo "Running benchmark..."

# Time the execution
START_TIME=$(date +%s%N)
/app/target/release/file-deduplicator \
    --paths "$DATA_DIR" \
    --output "$REPORT_FILE" \
    --dry-run \
    --verbose
END_TIME=$(date +%s%N)

ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))
echo "Benchmark completed in ${ELAPSED_MS}ms"

# Verify report exists and check expected values
if [ -f "$REPORT_FILE" ]; then
    echo "Report generated at $REPORT_FILE"

    EXPECTED_GROUPS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['expected_duplicate_groups'])")
    EXPECTED_FILES=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['expected_duplicate_files'])")

    ACTUAL_GROUPS=$(python3 -c "import json; r=json.load(open('$REPORT_FILE')); print(r['dedup']['duplicate_groups'])")
    ACTUAL_FILES=$(python3 -c "import json; r=json.load(open('$REPORT_FILE')); print(r['dedup']['duplicate_files'])")

    echo "Duplicate groups: expected=$EXPECTED_GROUPS actual=$ACTUAL_GROUPS"
    echo "Duplicate files: expected=$EXPECTED_FILES actual=$ACTUAL_FILES"

    if [ "$ACTUAL_GROUPS" -eq "$EXPECTED_GROUPS" ] && [ "$ACTUAL_FILES" -eq "$EXPECTED_FILES" ]; then
        echo "Benchmark PASSED"
    else
        echo "Benchmark FAILED"
        exit 1
    fi
else
    echo "ERROR: No report generated"
    exit 1
fi
