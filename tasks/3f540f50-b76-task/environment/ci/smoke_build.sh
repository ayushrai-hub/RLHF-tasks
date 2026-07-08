#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
go build -o /tmp/registeraudit ./cmd/registeraudit
echo smoke ok
