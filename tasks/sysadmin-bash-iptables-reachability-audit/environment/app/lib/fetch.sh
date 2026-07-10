fetch_snapshot() {
    require_cmd curl || return 1

    ensure_dir "$RAW_DIR"
    rm -f "$RAW_DIR"/iptables_snapshot.json

    log_info "fetching iptables snapshot"
    if ! curl -fsS "${API_BASE_URL}/api/iptables-snapshot" -o "$RAW_DIR/iptables_snapshot.json"; then
        log_error "fetch iptables-snapshot failed"
        return 1
    fi
}
