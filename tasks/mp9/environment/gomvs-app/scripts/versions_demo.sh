#!/usr/bin/env bash
# Print the published versions of a small module in ascending precedence order.
# Requires network access to the module proxy.
set -euo pipefail
BIN=/app/gomvs
"$BIN" versions "${1:-rsc.io/sampler}"
