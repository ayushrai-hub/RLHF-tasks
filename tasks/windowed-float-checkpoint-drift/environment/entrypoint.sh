#!/bin/bash
set -uo pipefail
mkdir -p /app/output /app/var /logs/verifier /logs/agent
exec "$@"
