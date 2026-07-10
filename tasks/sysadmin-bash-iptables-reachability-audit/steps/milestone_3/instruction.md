Fix `/app/lib/report.sh` so `/app/reports/iptables_audit.csv` is the shaped rollup of `/app/data/iptables_audit.db`. The report header, column order, detail-row sourcing, sort order, integer rendering, and the final `TOTAL` row shape are all specified in `/app/docs/SCHEMA.md` under the "Report shape" section.

The report is derived from `rule_audit` joined with `rules`. Source `is_reachable` and `blocked_by_rule_id` from `rule_audit` (the audit columns exist only there). Derive the detail-row count from the data — do not hardcode.

After editing, run `bash /app/scripts/start_api.sh && bash /app/bin/ipaudit.sh all` to regenerate `/app/reports/iptables_audit.csv`. Do not modify anything under `/app/api/` or `/app/db/schema.sql`.
