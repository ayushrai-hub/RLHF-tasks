#!/bin/bash
set -euo pipefail

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
