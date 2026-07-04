#!/bin/bash
set -euo pipefail

cd /app
git apply /solution/fix.patch
go build -o /app/ckptplan ./cmd/ckptplan
