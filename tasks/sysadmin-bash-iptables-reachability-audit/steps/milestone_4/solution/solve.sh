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


cat > /app/lib/persist.sh <<'PERSISTSH'
persist_normalized() {
    require_cmd sqlite3 || return 1
    require_cmd jq || return 1

    # Idempotency: drop the DB so db_init recreates every table.
    rm -f "$DB_PATH"
    db_init
    local sql_file
    sql_file=$(mktemp)
    log_info "persisting $NORMALIZED_PATH -> $DB_PATH"

    echo "BEGIN;" > "$sql_file"

    # Persist chains with placeholder effective_default_policy / is_dead_chain.
    jq -r 'select(.record_type == "chain") | [
        .table_name, .name, .chain_kind, .default_policy,
        (.packet_count|tostring), (.byte_count|tostring)
    ] | @tsv' "$NORMALIZED_PATH" | \
    awk -F'\t' '
        function esc(s) { gsub(/\047/, "\047\047", s); return s }
        {
            printf "INSERT OR IGNORE INTO chains (table_name, name, chain_kind, default_policy, packet_count, byte_count, effective_default_policy, is_dead_chain, is_effectively_dead_chain) VALUES (\047%s\047,\047%s\047,\047%s\047,\047%s\047,%d,%d,\047\047,0,0);\n",
                esc($1), esc($2), esc($3), esc($4), $5, $6
        }
    ' >> "$sql_file"

    # Persist rules.
    jq -r 'select(.record_type == "rule") | [
        .rule_id, .table_name, .chain, (.position|tostring), .target, .target_args,
        .target_type, .matcher_csv, (.is_unconditional|tostring),
        (.packet_count|tostring), (.byte_count|tostring)
    ] | @tsv' "$NORMALIZED_PATH" | \
    awk -F'\t' '
        function esc(s) { gsub(/\047/, "\047\047", s); return s }
        {
            printf "INSERT OR IGNORE INTO rules (rule_id, table_name, chain, position, target, target_args, target_type, matcher_csv, is_unconditional, packet_count, byte_count) VALUES (\047%s\047,\047%s\047,\047%s\047,%d,\047%s\047,\047%s\047,\047%s\047,\047%s\047,%d,%d,%d);\n",
                esc($1), esc($2), esc($3), $4, esc($5), esc($6), esc($7), esc($8), $9, $10, $11
        }
    ' >> "$sql_file"

    # chain_graph: one row per JUMP or GOTO edge, scoped within the SAME table.
    # Both `-j chain` and `-g chain` transfer control into the target chain,
    # so both create an inbound edge (used for dead-chain detection).
    cat >> "$sql_file" <<'SQL'
INSERT INTO chain_graph (from_table_name, from_chain, to_table_name, to_chain, via_rule_id)
SELECT table_name, chain, table_name, target, rule_id
FROM rules
WHERE target_type IN ('jump','goto');

INSERT INTO rule_audit (rule_id, is_reachable, blocked_by_rule_id)
SELECT r.rule_id,
       CASE WHEN fb.first_blocker_pos IS NULL OR r.position <= fb.first_blocker_pos THEN 1 ELSE 0 END AS is_reachable,
       COALESCE(blocker.rule_id, '') AS blocked_by_rule_id
FROM rules r
LEFT JOIN (
    SELECT table_name, chain, MIN(position) AS first_blocker_pos
    FROM rules
    WHERE is_unconditional = 1 AND target_type IN ('terminal','return','goto')
    GROUP BY table_name, chain
) fb
    ON fb.table_name = r.table_name
   AND fb.chain = r.chain
LEFT JOIN rules blocker
    ON blocker.table_name = r.table_name
   AND blocker.chain = r.chain
   AND blocker.position = fb.first_blocker_pos
   AND r.position > fb.first_blocker_pos;

UPDATE chains SET effective_default_policy = CASE
    WHEN chain_kind = 'user_defined' THEN 'return'
    WHEN EXISTS (
        SELECT 1 FROM rules
        WHERE rules.table_name = chains.table_name
          AND rules.chain = chains.name
          AND rules.is_unconditional = 1
          AND rules.target_type IN ('terminal','goto')
    ) THEN 'preempted'
    ELSE default_policy
END;

UPDATE chains SET is_dead_chain = CASE
    WHEN chain_kind = 'user_defined' AND NOT EXISTS (
        SELECT 1 FROM chain_graph
        WHERE chain_graph.to_table_name = chains.table_name
          AND chain_graph.to_chain = chains.name
    ) THEN 1
    ELSE 0
END;

-- is_effectively_dead_chain: start every user chain at 1, then iteratively
-- flip to 0 any user chain that has at least one LIVE inbound edge. A live
-- inbound edge is one whose via_rule is reachable AND whose source chain is
-- itself live (a builtin chain, or a user chain currently at is_effectively_dead_chain=0).
UPDATE chains SET is_effectively_dead_chain = 1 WHERE chain_kind = 'user_defined';
SQL

    echo "COMMIT;" >> "$sql_file"
    sqlite3 "$DB_PATH" < "$sql_file"
    rm -f "$sql_file"

    # Fixpoint loop: keep flipping chains alive until no further change.
    local prev_signature=""
    local iter=0
    while [ $iter -lt 20 ]; do
        sqlite3 "$DB_PATH" <<'FIXSQL'
UPDATE chains SET is_effectively_dead_chain = 0
WHERE chain_kind = 'user_defined'
  AND EXISTS (
    SELECT 1 FROM chain_graph g
    JOIN rule_audit ra ON ra.rule_id = g.via_rule_id
    LEFT JOIN chains src
      ON src.table_name = g.from_table_name
     AND src.name = g.from_chain
    WHERE g.to_table_name = chains.table_name
      AND g.to_chain = chains.name
      AND ra.is_reachable = 1
      AND (src.chain_kind = 'builtin' OR src.is_effectively_dead_chain = 0)
  );
FIXSQL
        local curr_signature
        curr_signature=$(sqlite3 "$DB_PATH" "SELECT GROUP_CONCAT(table_name||'.'||name||':'||is_effectively_dead_chain, '|') FROM chains ORDER BY table_name, name;")
        if [ "$curr_signature" = "$prev_signature" ]; then
            break
        fi
        prev_signature="$curr_signature"
        iter=$((iter + 1))
    done

    local n_c n_r n_g n_a
    n_c=$(db_exec "SELECT COUNT(*) FROM chains;")
    n_r=$(db_exec "SELECT COUNT(*) FROM rules;")
    n_g=$(db_exec "SELECT COUNT(*) FROM chain_graph;")
    n_a=$(db_exec "SELECT COUNT(*) FROM rule_audit;")
    log_info "DB now has $n_c chains, $n_r rules, $n_g graph edges, $n_a audit rows"
}
PERSISTSH

bash /app/scripts/start_api.sh
rm -rf /app/data/raw /app/data/normalized_iptables.jsonl /app/data/iptables_audit.db /app/reports/iptables_audit.csv
bash /app/bin/ipaudit.sh all


cat > /app/lib/report.sh <<'REPORTSH'
build_report() {
    require_cmd sqlite3 || return 1
    require_cmd awk || return 1

    ensure_dir "$(dirname "$REPORT_PATH")"
    log_info "writing iptables audit report -> $REPORT_PATH"

    local rows_tsv
    rows_tsv=$(sqlite3 -separator $'\t' "$DB_PATH" \
        "SELECT r.rule_id, r.table_name, r.chain, r.position, r.target, r.target_type, r.is_unconditional, a.is_reachable, a.blocked_by_rule_id, r.packet_count FROM rules r JOIN rule_audit a ON a.rule_id = r.rule_id ORDER BY r.table_name ASC, r.chain ASC, r.position ASC;")

    {
        echo "rule_id,table_name,chain,position,target,target_type,is_unconditional,is_reachable,blocked_by_rule_id,packet_count"
        printf '%s\n' "$rows_tsv" | awk -F'\t' '
            function csv_quote(s) {
                if (index(s, ",") > 0 || index(s, "\"") > 0) {
                    gsub(/"/, "\"\"", s)
                    return "\"" s "\""
                }
                return s
            }
            NF == 0 { next }
            {
                sum_uncond += $7
                sum_reach += $8
                sum_packets += $10
                printf "%s,%s,%s,%d,%s,%s,%d,%d,%s,%d\n",
                    csv_quote($1), csv_quote($2), csv_quote($3), $4,
                    csv_quote($5), csv_quote($6),
                    $7, $8, csv_quote($9), $10
            }
            END {
                printf "TOTAL,,,,,,%d,%d,,%d\n",
                    sum_uncond, sum_reach, sum_packets
            }
        '
    } > "$REPORT_PATH"

    local lines
    lines=$(wc -l < "$REPORT_PATH" 2>/dev/null || echo 0)
    log_info "report has $lines lines"
}
REPORTSH

bash /app/scripts/start_api.sh
rm -rf /app/data/raw /app/data/normalized_iptables.jsonl /app/data/iptables_audit.db /app/reports/iptables_audit.csv
bash /app/bin/ipaudit.sh all


cat > /app/lib/trace.sh <<'TRACESH'
build_traces() {
    require_cmd sqlite3 || return 1
    require_cmd awk || return 1

    ensure_dir "$(dirname "$TRACE_REPORT_PATH")"
    log_info "writing packet traces -> $TRACE_REPORT_PATH"

    # Pull the rules (with their computed target_type) and the chain
    # metadata (kind + default_policy) out of the DB into TSV, then run a
    # stack-machine simulation per probe in awk.
    local rules_tsv chains_tsv probes_tsv
    rules_tsv=$(sqlite3 -separator $'\t' "$DB_PATH" \
        "SELECT table_name, chain, position, target, target_type, matcher_csv FROM rules ORDER BY table_name, chain, position;")
    chains_tsv=$(sqlite3 -separator $'\t' "$DB_PATH" \
        "SELECT table_name, name, chain_kind, default_policy FROM chains;")
    probes_tsv=$(awk -F'\t' '
        BEGIN { started = 0 }
        /^#/ { next }
        NF == 0 { next }
        { if (!started) { started = 1; next } print }
    ' "$PROBE_PACKETS_PATH")

    local detail total_line
    detail=$(awk -F'\t' \
            -v rules_tsv="$rules_tsv" \
            -v chains_tsv="$chains_tsv" '
            function csv_quote(s) {
                if (index(s, ",") > 0 || index(s, "\"") > 0) {
                    gsub(/"/, "\"\"", s); return "\"" s "\""
                }
                return s
            }
            # matcher evaluation: every clause must match the probe.
            function matches(m, in_i, out_i, proto, dport, state,   n, tok, i, mod, sset, k, parts, np, j, ok) {
                if (m == "") return 1
                n = split(m, tok, /[ \t]+/)
                i = 1
                while (i <= n) {
                    if (tok[i] == "") { i++; continue }
                    if (tok[i] == "-i")      { if (in_i  != tok[i+1]) return 0; i += 2 }
                    else if (tok[i] == "-o") { if (out_i != tok[i+1]) return 0; i += 2 }
                    else if (tok[i] == "-p") { if (proto != tok[i+1]) return 0; i += 2 }
                    else if (tok[i] == "--dport") { if (dport != tok[i+1]) return 0; i += 2 }
                    else if (tok[i] == "-m") {
                        mod = tok[i+1]
                        if (mod == "state" || mod == "conntrack") {
                            np = split(tok[i+3], parts, ",")
                            ok = 0
                            for (j = 1; j <= np; j++) if (parts[j] == state) ok = 1
                            if (!ok) return 0
                            i += 4
                        } else if (mod == "limit") {
                            i += 2
                        } else { i += 2 }
                    }
                    else if (tok[i] == "--state" || tok[i] == "--ctstate") {
                        np = split(tok[i+1], parts, ",")
                        ok = 0
                        for (j = 1; j <= np; j++) if (parts[j] == state) ok = 1
                        if (!ok) return 0
                        i += 2
                    }
                    else if (tok[i] == "--limit") { i += 2 }
                    else { i++ }
                }
                return 1
            }
            BEGIN {
                # chains: kind[table.chain], policy[table.chain]
                nc = split(chains_tsv, clines, "\n")
                for (i = 1; i <= nc; i++) {
                    if (clines[i] == "") continue
                    split(clines[i], cf, "\t")
                    key = cf[1] "." cf[2]
                    ckind[key] = cf[3]; cpolicy[key] = cf[4]
                }
                # rules grouped per table.chain, in position order.
                nr = split(rules_tsv, rlines, "\n")
                for (i = 1; i <= nr; i++) {
                    if (rlines[i] == "") continue
                    split(rlines[i], rf, "\t")
                    key = rf[1] "." rf[2]
                    cnt[key]++
                    idx = cnt[key]
                    r_pos[key, idx] = rf[3]
                    r_tgt[key, idx] = rf[4]
                    r_type[key, idx] = rf[5]
                    r_match[key, idx] = rf[6]
                }
            }
            NF == 0 { next }
            {
                probe_id = $1; etable = $2; echain = $3
                in_i = $4; out_i = $5; proto = $6; dport = $7; state = $8

                chain = echain; ci = 1; sp = 0
                path = ""; hops = 0; verdict = ""; decided = ""
                guard = 0
                while (1) {
                    guard++
                    if (guard > 100000) { verdict = "LOOP"; decided = ""; break }
                    key = etable "." chain
                    if (ci > cnt[key]) {
                        # fell off the end of the chain
                        if (ckind[key] == "builtin") {
                            verdict = cpolicy[key]; decided = "policy:" key; break
                        }
                        if (sp > 0) { chain = st_chain[sp]; ci = st_idx[sp]; sp--; continue }
                        verdict = cpolicy[etable "." echain]; decided = "policy:" etable "." echain; break
                    }
                    if (!matches(r_match[key, ci], in_i, out_i, proto, dport, state)) { ci++; continue }
                    rid = etable "." chain ":" r_pos[key, ci]
                    path = (path == "" ? rid : path "|" rid); hops++
                    tt = r_type[key, ci]
                    if (tt == "terminal") { verdict = r_tgt[key, ci]; decided = rid; break }
                    if (tt == "non_terminal") { ci++; continue }
                    if (tt == "return") {
                        if (ckind[key] == "builtin") { verdict = cpolicy[key]; decided = "policy:" key; break }
                        if (sp > 0) { chain = st_chain[sp]; ci = st_idx[sp]; sp--; continue }
                        verdict = cpolicy[etable "." echain]; decided = "policy:" etable "." echain; break
                    }
                    if (tt == "jump") { sp++; st_chain[sp] = chain; st_idx[sp] = ci + 1; chain = r_tgt[key, ci]; ci = 1; continue }
                    if (tt == "goto") { chain = r_tgt[key, ci]; ci = 1; continue }
                    ci++
                }
                printf "D\t%s,%s,%s,%s,%s,%d,%s\n",
                    probe_id, etable, echain, verdict, csv_quote(decided), hops, csv_quote(path)
                thops += hops
            }
            END { printf "T\tTOTAL,,,,,%d,\n", thops }
        ' <<< "$probes_tsv")

    {
        echo "probe_id,entry_table,entry_chain,final_verdict,decided_by,hop_count,path"
        # detail rows (prefix D), sorted by probe_id; then the TOTAL row (prefix T)
        printf '%s\n' "$detail" | awk -F'\t' '$1 == "D" { print $2 }' | sort -t, -k1,1
        printf '%s\n' "$detail" | awk -F'\t' '$1 == "T" { print $2 }'
    } > "$TRACE_REPORT_PATH"

    local lines
    lines=$(wc -l < "$TRACE_REPORT_PATH" 2>/dev/null || echo 0)
    log_info "trace report has $lines lines"
}
TRACESH

bash /app/scripts/start_api.sh
rm -rf /app/data/raw /app/data/normalized_iptables.jsonl /app/data/iptables_audit.db /app/reports
bash /app/bin/ipaudit.sh all
