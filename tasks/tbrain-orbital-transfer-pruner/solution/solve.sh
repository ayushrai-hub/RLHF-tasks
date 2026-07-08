#!/bin/bash
set -euo pipefail
cd /app
cp /solution/fixed_pruner.js /app/src/pruner.js
npm run check
