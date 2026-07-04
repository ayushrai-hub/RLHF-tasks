#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -m 0644 "${SCRIPT_DIR}/oracle/media_sig_audit.awk" /app/lib/media_sig_audit.awk
/app/bin/audit.sh catalog >/dev/null
/app/bin/audit.sh verify >/dev/null
/app/bin/audit.sh report >/dev/null
