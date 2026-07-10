normalize_iptables() {
    require_cmd jq || return 1

    ensure_dir "$(dirname "$NORMALIZED_PATH")"
    log_info "normalizing iptables snapshot -> $NORMALIZED_PATH"

    : > "$NORMALIZED_PATH"

    # Chain records — pass through with table_name but no audit-stage classifications.
    jq -c '
        .tables[] as $t | $t.chains[] | {
            record_type: "chain",
            table_name: $t.name,
            name, chain_kind: .kind,
            default_policy,
            packet_count, byte_count
        }
    ' "$RAW_DIR/iptables_snapshot.json" >> "$NORMALIZED_PATH"

    # Rule records — pass through fields but do NOT classify target_type
    # and do NOT compute is_unconditional.
    jq -c '
        .tables[] as $t | $t.rules[] | {
            record_type: "rule",
            rule_id: ($t.name + "." + .chain + ":" + (.position|tostring)),
            table_name: $t.name,
            chain, position,
            target, target_args,
            target_type: "unknown",
            matcher_csv: .matcher_text,
            is_unconditional: 0,
            packet_count, byte_count
        }
    ' "$RAW_DIR/iptables_snapshot.json" >> "$NORMALIZED_PATH"

    local count
    count=$(wc -l < "$NORMALIZED_PATH" 2>/dev/null || echo 0)
    log_info "wrote $count normalized records"
}
