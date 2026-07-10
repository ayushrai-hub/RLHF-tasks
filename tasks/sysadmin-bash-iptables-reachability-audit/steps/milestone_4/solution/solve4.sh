#!/bin/bash
set -euo pipefail

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
