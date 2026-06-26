#!/bin/bash
set -e

# Validate the verification report output against expected structure
REPORT="${1:-/app/output/verification_report.json}"

if [ ! -f "$REPORT" ]; then
    echo "ERROR: Report not found at $REPORT"
    exit 1
fi

# Check required top-level keys
for key in summary pair_analysis timing_analysis entropy_assessment batch_consistency security settings_used; do
    if ! grep -q "\"$key\"" "$REPORT"; then
        echo "ERROR: Missing required key '$key' in report"
        exit 1
    fi
done

# Validate summary fields
for field in total_pairs flagged_pairs distinguishing_advantage unlinkability_score is_unlinkable; do
    if ! grep -q "\"$field\"" "$REPORT"; then
        echo "ERROR: Missing summary field '$field'"
        exit 1
    fi
done

# Check that total_pairs equals sessions * signatures (6*5=30)
TOTAL=$(python3 -c "import json; r=json.load(open('$REPORT')); print(r['summary']['total_pairs'])")
if [ "$TOTAL" -ne 30 ]; then
    echo "ERROR: Expected total_pairs=30, got $TOTAL"
    exit 1
fi

echo "PASS: Report structure validated successfully"
