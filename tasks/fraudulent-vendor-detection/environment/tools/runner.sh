#!/bin/bash
set -euo pipefail

export PATH="/usr/local/go/bin:${PATH}"
cd /app/environment

if [ ! -x /app/bin/vendorlab ] || find . -name '*.go' -newer /app/bin/vendorlab 2>/dev/null | grep -q .; then
  go build -trimpath -ldflags="-s -w" -o /app/bin/vendorlab ./cmd/vendorlab
fi

cfg="${1:?config path}"
out="${2:?output path}"
mkdir -p "$(dirname "$out")"
exec /app/bin/vendorlab --config "$cfg" --out "$out"
