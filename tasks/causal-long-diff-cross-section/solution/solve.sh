#!/usr/bin/env bash
cp /solution/analysis_correct.R /app/analysis.R
Rscript /app/analysis.R
test -f /app/estimate.json
