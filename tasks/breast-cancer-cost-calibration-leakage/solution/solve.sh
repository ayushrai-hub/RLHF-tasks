#!/bin/bash
set -euo pipefail
cp /solution/analysis.R /app/analysis.R
Rscript --vanilla /app/analysis.R
