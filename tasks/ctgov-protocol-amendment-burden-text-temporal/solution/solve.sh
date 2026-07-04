#!/usr/bin/env bash
set -euo pipefail
# Harbor mounts the task's solution/ directory at /solution during an oracle run,
# so analysis.R is read from there rather than copied into the image.
Rscript /solution/analysis.R
