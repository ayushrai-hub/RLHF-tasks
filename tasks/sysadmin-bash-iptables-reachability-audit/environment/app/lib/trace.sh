build_traces() {
    require_cmd sqlite3 || return 1

    ensure_dir "$(dirname "$TRACE_REPORT_PATH")"
    log_info "writing packet traces -> $TRACE_REPORT_PATH"

    # NOTE: quick first pass — does NOT simulate traversal. It just reports,
    # for each probe, the first rule in the entry chain, ignoring jumps,
    # gotos, returns, the call stack, and the default policies. Known gaps:
    # no descent into jumped/goto'd chains, no return handling, no policy
    # fallback, no shadowing by earlier unconditional terminals.
    echo "probe_id,entry_table,entry_chain,final_verdict,decided_by,hop_count,path" > "$TRACE_REPORT_PATH"
    while IFS=$'\t' read -r probe_id etable echain rest; do
        [ "$probe_id" = "probe_id" ] && continue
        case "$probe_id" in \#*) continue ;; esac
        [ -z "$probe_id" ] && continue
        local first
        first=$(sqlite3 "$DB_PATH" "SELECT target FROM rules WHERE table_name='$etable' AND chain='$echain' ORDER BY position LIMIT 1;")
        echo "$probe_id,$etable,$echain,$first,,0," >> "$TRACE_REPORT_PATH"
    done < "$PROBE_PACKETS_PATH"
}
