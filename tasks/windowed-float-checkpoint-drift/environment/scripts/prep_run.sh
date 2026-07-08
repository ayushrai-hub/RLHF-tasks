#!/bin/bash
set -euo pipefail
# Verifier prep hook; ensures environment scripts remain executable in the pipeline.
test -x /app/environment/scripts/build_stats.sh
