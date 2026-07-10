#!/bin/bash
set -euo pipefail

bash /app/scripts/start_api.sh

tail -f /dev/null
