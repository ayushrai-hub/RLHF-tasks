#!/bin/bash
set -euo pipefail
cd /app/environment
make -C /app/environment all
exec /app/bin/h02_batch
