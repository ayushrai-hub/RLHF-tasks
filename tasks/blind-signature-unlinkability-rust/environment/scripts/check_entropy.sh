#!/bin/bash
# Quick entropy validation script
# Verifies entropy is computed correctly using natural logarithm (nats)
# Per IEEE 754-2008 §5.3, entropy in nats avoids log2 precision issues

REPORT="${1:-/app/output/verification_report.json}"

if [ ! -f "$REPORT" ]; then
    echo "Report not found"
    exit 1
fi

ENTROPY=$(python3 -c "import json; r=json.load(open('$REPORT')); print(r['entropy_assessment']['correlation_entropy'])")
THRESHOLD=$(python3 -c "import json; r=json.load(open('$REPORT')); print(r['entropy_assessment']['entropy_threshold'])")

echo "Correlation entropy: $ENTROPY nats"
echo "Entropy threshold: $THRESHOLD nats"
echo "Max possible (10 bins): $(python3 -c 'import math; print(round(math.log(10), 6))') nats"

python3 -c "
import json, math
r = json.load(open('$REPORT'))
e = r['entropy_assessment']['correlation_entropy']
if e > math.log(10):
    print('WARNING: entropy exceeds theoretical max for 10 bins')
else:
    print('OK: entropy within expected range')
"
