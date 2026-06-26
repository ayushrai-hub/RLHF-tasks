#!/usr/bin/env bash
set -euo pipefail
Rscript "$(dirname "$0")/analysis.R"
