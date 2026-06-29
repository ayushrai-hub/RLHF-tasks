#!/usr/bin/env bash
set -euo pipefail

# Defensive PATH (Directive 5).
export PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
GO_BIN="$(command -v go || echo /usr/local/go/bin/go)"

# Copy oracle source over scaffold; preserves /app/ack_trove and /app/output.
SRC=/solution/oracle_src
if [ -d "$SRC" ]; then
  rm -rf /app/cmd /app/internal /app/go.mod /app/Makefile
  cp -r "$SRC/." /app/
fi

cd /app
mkdir -p /app/bin /app/output
"$GO_BIN" build -trimpath -o /app/bin/qack ./cmd/qack
/app/bin/qack
