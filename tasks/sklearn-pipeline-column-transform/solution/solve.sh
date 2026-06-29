
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd /app
python3 "$SCRIPT_DIR/apply_fixes.py"
bash /app/native/build_native.sh
bash /app/java/compile.sh
bash /app/scripts/run_integration_tests.sh
