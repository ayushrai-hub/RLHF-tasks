#!/usr/bin/env bash
# Seed the demo fixtures into a fresh database via the pay CLI.
set -euo pipefail
APP=/app/pay
CSV=/app/fixtures/payroll.csv
"$APP" init >/dev/null
declare -A seen
tail -n +2 "$CSV" | while IFS=, read -r emp gross mand kind prio cap; do
    [ -z "$emp" ] && continue
    if [ -z "${seen[$emp]:-}" ]; then
        "$APP" add-employee "$emp" --gross "$gross" --mandatory "$mand" >/dev/null 2>&1 || true
        seen[$emp]=1
    fi
    "$APP" add-order "$emp" --kind "$kind" --priority "$prio" --cap "$cap" >/dev/null 2>&1 || true
done
echo "seeded from $CSV"
