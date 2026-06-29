#!/bin/bash
set -euo pipefail

cd /app
git apply -p1 /solution/fix.patch
go build -o /app/dstcron ./cmd/dstcron
