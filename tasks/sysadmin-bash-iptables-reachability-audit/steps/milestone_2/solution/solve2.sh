#!/bin/bash
set -euo pipefail

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
