build_report() {
    require_cmd sqlite3 || return 1

    ensure_dir "$(dirname "$REPORT_PATH")"
    log_info "writing iptables audit report -> $REPORT_PATH"

    echo "rule_id,table_name,chain,position,target,target_type,is_unconditional,is_reachable,blocked_by_rule_id,packet_count" > "$REPORT_PATH"

    sqlite3 -separator ',' "$DB_PATH" \
        "SELECT rule_id, table_name, chain, position, target, target_type, is_unconditional, 0, '', packet_count FROM rules ORDER BY table_name, chain" \
        >> "$REPORT_PATH"

    local lines
    lines=$(wc -l < "$REPORT_PATH" 2>/dev/null || echo 0)
    log_info "report has $lines lines"
}
