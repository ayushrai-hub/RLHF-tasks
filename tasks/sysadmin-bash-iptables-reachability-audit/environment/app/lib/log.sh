log_info()  { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO  $*"  >&2; }
log_warn()  { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARN  $*"  >&2; }
log_error() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR $*"  >&2; }
