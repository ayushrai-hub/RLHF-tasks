#!/bin/bash
set -euo pipefail

/app/scripts/build.sh
/app/bin/flowgap --csv /app/input/packets.csv --out /app/output.json
