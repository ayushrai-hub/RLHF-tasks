#!/bin/bash
set -euo pipefail

LIB_DIR="/app/lib"
CONFIG_PATH="/app/config/ipaudit.conf"

# shellcheck disable=SC1091
source "$CONFIG_PATH"
# shellcheck disable=SC1091
source "$LIB_DIR/log.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/util.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/db.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/fetch.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/normalize.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/persist.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/report.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/trace.sh"

stage="${1:-all}"

case "$stage" in
    fetch)     fetch_snapshot ;;
    normalize) normalize_iptables ;;
    persist)   persist_normalized ;;
    report)    build_report ;;
    trace)     build_traces ;;
    all)
        fetch_snapshot
        normalize_iptables
        persist_normalized
        build_report
        build_traces
        ;;
    *)
        log_error "unknown stage: $stage"
        echo "usage: ipaudit.sh {fetch|normalize|persist|report|all}" >&2
        exit 2
        ;;
esac
