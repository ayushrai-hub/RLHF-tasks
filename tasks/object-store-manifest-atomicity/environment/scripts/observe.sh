#!/bin/bash
set -euo pipefail
cd /app/environment
make replay-smoke
