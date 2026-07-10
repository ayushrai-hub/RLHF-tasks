#!/bin/bash
set -euo pipefail

cat > /app/lib/normalize.sh <<'NORMSH'
normalize_iptables() {
    require_cmd jq || return 1

    ensure_dir "$(dirname "$NORMALIZED_PATH")"
    log_info "normalizing iptables snapshot -> $NORMALIZED_PATH"

    # Build target -> target_type lookup as a JSON object.
    local target_map
    target_map=$(awk -F'\t' 'NR > 1 && NF >= 2 { printf "\"%s\":\"%s\",", $1, $2 }' "$TARGET_CLASSIFICATION_PATH")
    target_map="{${target_map%,}}"

    # Build local-policy override list as a JSON array. Each entry overrides
    # the default classification when its match_kind+match_value pattern fits.
    local overrides_json
    overrides_json=$(awk -F'\t' 'NR > 1 && NF >= 3 {
        gsub(/"/, "\\\"", $2)
        printf "{\"match_kind\":\"%s\",\"match_value\":\"%s\",\"forced_target_type\":\"%s\"},", $1, $2, $3
    }' "$LOCAL_OVERRIDES_PATH")
    overrides_json="[${overrides_json%,}]"

    # Build set of (table, chain) user-defined chain identities — used to
    # classify JUMP targets. A jump can only target a user chain in the
    # SAME table, so a target name shared across tables is not a jump
    # unless the chain exists in the rule's own table.
    local user_chains_json
    user_chains_json=$(jq -c '
        [.tables[] | {table: .name, user_chains: [.chains[] | select(.kind == "user_defined") | .name]}]
        | map({key: .table, value: .user_chains}) | from_entries
    ' "$RAW_DIR/iptables_snapshot.json")

    : > "$NORMALIZED_PATH"

    jq -c '
        .tables[] as $t | $t.chains[] | {
            record_type: "chain",
            table_name: $t.name,
            name, chain_kind: .kind,
            default_policy,
            packet_count, byte_count
        }
    ' "$RAW_DIR/iptables_snapshot.json" >> "$NORMALIZED_PATH"

    jq -c \
        --argjson tmap "$target_map" \
        --argjson user_chains_by_table "$user_chains_json" \
        --argjson overrides "$overrides_json" \
        '
        .tables[] as $t | $t.rules[] |
        .target as $tg |
        (.target_args // "") as $tgargs |
        ((.jump_kind // "jump")) as $jk |
        ($user_chains_by_table[$t.name] // []) as $user_chains |
        (if ($tmap[$tg] // null) != null then $tmap[$tg]
         elif ($user_chains | index($tg)) != null then (if $jk == "goto" then "goto" else "jump" end)
         else "unknown" end) as $base_ttype |
        (reduce $overrides[] as $o ($base_ttype;
            if $o.match_kind == "log_prefix_contains" then
                if $tg == "LOG" and ($tgargs | contains($o.match_value)) then $o.forced_target_type else . end
            elif $o.match_kind == "target_args_contains" then
                if $tgargs | contains($o.match_value) then $o.forced_target_type else . end
            else . end)) as $ttype |
        ((.matcher_text // "") | gsub("^\\s+|\\s+$"; "")) as $m |
        {
            record_type: "rule",
            rule_id: ($t.name + "." + .chain + ":" + (.position|tostring)),
            table_name: $t.name,
            chain, position,
            target, target_args,
            target_type: $ttype,
            matcher_csv: $m,
            is_unconditional: (if $m == "" then 1 else 0 end),
            packet_count, byte_count
        }
    ' "$RAW_DIR/iptables_snapshot.json" >> "$NORMALIZED_PATH"

    local count
    count=$(wc -l < "$NORMALIZED_PATH" 2>/dev/null || echo 0)
    log_info "wrote $count normalized records"
}
NORMSH

bash /app/scripts/start_api.sh
rm -rf /app/data/raw /app/data/normalized_iptables.jsonl /app/data/iptables_audit.db /app/reports/iptables_audit.csv
bash /app/bin/ipaudit.sh fetch
bash /app/bin/ipaudit.sh normalize
