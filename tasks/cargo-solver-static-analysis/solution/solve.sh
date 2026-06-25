#!/bin/bash
# Oracle solution: rewrite /app/scripts/audit.awk so it correctly maps Cargo
# feature gates (including multi-line / comment-laden / trailing-comma feature
# arrays), extracts every CFL stability rule from the dossier (all four
# annotation formats, active-status only), computes the effective CFL ceiling
# for each feature over its transitive closure, and flags stability violations.
#
# Violations and CFL margins are computed over the TRANSITIVE feature closure of
# each feature, honouring Cargo's per-manifest weak-dependency (`crate?/feature`)
# semantics: a weak enable fires only if that optional crate dependency is also
# strongly activated within the same manifest.
set -euo pipefail

mkdir -p /app/reports

cat > /app/scripts/audit.awk <<'AWK'
#!/usr/bin/gawk -f
# audit.awk — WaveBench Cargo feature-gate and CFL stability auditor (fixed)
#
# Pass Cargo.toml files first, then docs/validation_dossier.md last.

BEGIN {
    in_features = 0
    in_package  = 0
    nfeat       = 0
    accum       = 0
    SEP = "\033"
}

FNR == 1 {
    dossier = (FILENAME ~ /validation_dossier\.md$/) ? 1 : 0
    if (!dossier) { in_features = 0; in_package = 0; accum = 0 }
}

# ================= CARGO PARSING =================
!dossier && /^[[:space:]]*\[package\]/  { in_package = 1; in_features = 0; accum = 0; next }
!dossier && /^[[:space:]]*\[features\]/ { in_features = 1; in_package = 0; accum = 0; next }
!dossier && /^[[:space:]]*\[[^]]+\]/ {
    if ($0 !~ /\[package\]/ && $0 !~ /\[features\]/) { in_package = 0; in_features = 0; accum = 0 }
    next
}

!dossier && in_package && /^[[:space:]]*name[[:space:]]*=/ {
    if (match($0, /"([^"]+)"/, a)) current_crate = a[1]
    next
}

!dossier && in_features {
    line = $0
    sub(/#.*/, "", line)                                   # strip inline comment

    if (accum) {                                           # continuing a multi-line array
        if (line ~ /\]/) { tmp = line; sub(/\].*/, "", tmp); buf = buf " " tmp; emit_feature(fname_acc, buf); accum = 0 }
        else             { buf = buf " " line }
        next
    }

    if (match(line, /^[[:space:]]*([A-Za-z0-9_-]+)[[:space:]]*=[[:space:]]*\[(.*)$/, m)) {
        fname_acc = m[1]; rest = m[2]
        if (rest ~ /\]/) { sub(/\].*/, "", rest); emit_feature(fname_acc, rest) }   # single line
        else             { buf = rest; accum = 1 }                                  # opens multi-line
    }
    next
}

# ================= DOSSIER PARSING =================
dossier && match($0, /^\|[[:space:]]*(R-[0-9]+)[[:space:]]*\|[[:space:]]*(CRITICAL|WARNING|INFO)[[:space:]]*\|/, sm) {
    sev_map[sm[1]] = sm[2]; next
}

dossier && /status=active/ {
    line = $0
    if (match(line, /AUDIT-RULE:[[:space:]]*(R-[0-9]+)/, r)) {
        add_rule(r[1], kv(line,"features"), kv(line,"type"), kv(line,"bound"), kv(line,"source"), kv(line,"severity")); next }
    if (match(line, /STABILITY-BOUND\((R-[0-9]+)\)/, r)) {
        add_rule(r[1], kv(line,"features"), kv(line,"type"), kv(line,"bound"), kv(line,"source"), kv(line,"severity")); next }
    if (match(line, /CFL-ANNOTATION\[(R-[0-9]+)\]/, r)) {
        add_rule(r[1], kv(line,"features"), kv(line,"type"), kv(line,"bound"), kv(line,"source"), kv(line,"severity")); next }
    if (match(line, /\|[[:space:]]*(E-[0-9]+)[[:space:]]*\|.*(GUARD-REQUIRED|PROHIBITED-COMBINATION)\((R-[0-9]+)\)/, r)) {
        add_rule(r[3], kv(line,"features"), kv(line,"type"), kv(line,"bound"), "errata-" r[1], kv(line,"severity")); next }
}

# ================= EMIT =================
END {
    reports = "/app/reports"
    fout = reports "/feature_gates.tsv"
    rout = reports "/cfl_rules.tsv"
    vout = reports "/audit_violations.tsv"
    mout = reports "/cfl_margins.tsv"

    # ---- feature_gates.tsv ----
    print "crate\tfeature_name\tfeature_deps\texternal_deps" > fout
    nl = 0
    for (i = 1; i <= nfeat; i++) L[++nl] = feat_crate[i] "\t" feat_name[i] "\t" feat_fd[i] "\t" feat_ed[i]
    isort(L, nl); for (i = 1; i <= nl; i++) print L[i] >> fout

    # ---- cfl_rules.tsv ----
    print "rule_id\taffected_features\tconstraint_type\tbound_value\tsource" > rout
    nrl = 0
    for (rid in rule_feats) RL[++nrl] = rid "\t" rule_feats[rid] "\t" rule_type[rid] "\t" rule_bound[rid] "\t" rule_src[rid]
    isort(RL, nrl); for (i = 1; i <= nrl; i++) print RL[i] >> rout

    # ---- audit_violations.tsv + cfl_margins.tsv ----
    print "crate\tfeature_name\tviolation_type\tseverity\trule_id" > vout
    print "crate\tfeature_name\teffective_cfl_max\tbinding_rule" > mout
    nv = 0; nm = 0
    for (i = 1; i <= nfeat; i++) {
        delete S
        closure(feat_crate[i], feat_name[i], S)

        # violations
        for (ri in rule_feats) {
            rtype = rule_type[ri]
            if (rtype == "prohibited_combination") {
                np = split(rule_feats[ri], need, "+"); ok = 1
                for (j = 1; j <= np; j++) if (!(need[j] in S)) ok = 0
                if (ok) V[++nv] = feat_crate[i] "\t" feat_name[i] "\tPROHIBITED_COMBINATION\t" sevof(ri) "\t" ri
            } else if (rtype == "requires_guard") {
                if ((rule_feats[ri] in S) && !(rule_bound[ri] in S))
                    V[++nv] = feat_crate[i] "\t" feat_name[i] "\tMISSING_GUARD\t" sevof(ri) "\t" ri
            }
        }

        # effective CFL ceiling = min bound among applicable max_cfl rules (tie -> smallest rule_id)
        bestrule = ""; bestbound = 0
        for (ri in rule_feats) {
            if (rule_type[ri] != "max_cfl") continue
            if (!(rule_feats[ri] in S)) continue
            b = rule_bound[ri] + 0
            if (bestrule == "" || b < bestbound || (b == bestbound && ri < bestrule)) { bestbound = b; bestrule = ri }
        }
        if (bestrule == "") M[++nm] = feat_crate[i] "\t" feat_name[i] "\t\tnone"
        else                M[++nm] = feat_crate[i] "\t" feat_name[i] "\t" sprintf("%.4f", bestbound) "\t" bestrule
    }
    isort(V, nv); for (i = 1; i <= nv; i++) print V[i] >> vout
    isort(M, nm); for (i = 1; i <= nm; i++) print M[i] >> mout
}

# ============ multi-line aware feature recorder ============
function emit_feature(fname, body,    n, toks, i, t, fd, nfd, ed, ned, toklist) {
    nfd = 0; ned = 0; toklist = ""
    n = split(body, toks, ",")
    for (i = 1; i <= n; i++) {
        t = toks[i]; gsub(/[[:space:]"]/, "", t)
        if (t == "") continue
        toklist = toklist (toklist == "" ? "" : SEP) t
        if (t ~ /^dep:/) { sub(/^dep:/, "", t); ed[++ned] = t }
        else            { fd[++nfd] = t }
    }
    nfeat++
    feat_crate[nfeat] = current_crate
    feat_name[nfeat]  = fname
    feat_fd[nfeat]    = join_sorted(fd, nfd)
    feat_ed[nfeat]    = join_sorted(ed, ned)
    raw[current_crate SEP fname] = toklist
}

# ============ transitive feature closure with weak-dep semantics ============
function closure(rc, rf, S,    ACT, LOCAL, changed, keys, nk, kk, parts, m, f, P, np, p, tok, q, c, ft, k) {
    delete ACT; delete LOCAL
    ACT[rc SEP rf] = 1; changed = 1
    while (changed) {
        changed = 0
        nk = 0; for (k in ACT) keys[++nk] = k
        for (kk = 1; kk <= nk; kk++) {
            split(keys[kk], parts, SEP); m = parts[1]; f = parts[2]
            if (!((m SEP f) in raw)) continue
            np = split(raw[m SEP f], P, SEP)
            for (p = 1; p <= np; p++) {
                tok = P[p]; if (tok == "") continue
                if (tok ~ /^dep:/) {
                    c = substr(tok, 5)
                    if (!((m SEP c) in LOCAL)) { LOCAL[m SEP c] = 1; changed = 1 }
                } else if (tok ~ /\?\//) {
                    split(tok, q, "?/"); c = q[1]; ft = q[2]
                    if ((m SEP c) in LOCAL && !((c SEP ft) in ACT)) { ACT[c SEP ft] = 1; changed = 1 }
                } else if (tok ~ /\//) {
                    split(tok, q, "/"); c = q[1]; ft = q[2]
                    if (!((m SEP c) in LOCAL)) { LOCAL[m SEP c] = 1; changed = 1 }
                    if (!((c SEP ft) in ACT)) { ACT[c SEP ft] = 1; changed = 1 }
                } else {
                    if (!((m SEP tok) in ACT)) { ACT[m SEP tok] = 1; changed = 1 }
                }
            }
        }
    }
    for (k in ACT) { split(k, parts, SEP); S[parts[2]] = 1 }
}

# ================= HELPERS =================
function sevof(ri) { return (ri in sev_map) ? sev_map[ri] : rule_sev[ri] }
function kv(s, k,   re, a) { re = k "=([^ |]+)"; if (match(s, re, a)) return a[1]; return "" }
function add_rule(rid, feats, type, bound, src, sev) {
    if (rid in rule_feats) return
    rule_feats[rid] = feats; rule_type[rid] = type; rule_bound[rid] = bound; rule_src[rid] = src; rule_sev[rid] = sev
}
function join_sorted(arr, n,   i, tmp, out) {
    if (n == 0) return ""
    for (i = 1; i <= n; i++) tmp[i] = arr[i]
    isort(tmp, n); out = tmp[1]; for (i = 2; i <= n; i++) out = out "," tmp[i]; return out
}
function isort(arr, n,   i, j, key) {
    for (i = 2; i <= n; i++) { key = arr[i]; j = i - 1
        while (j >= 1 && arr[j] > key) { arr[j+1] = arr[j]; j-- }
        arr[j+1] = key }
}
AWK

gawk -f /app/scripts/audit.awk \
    /app/wavebench/wavebench-core/Cargo.toml \
    /app/wavebench/wavebench-adaptive/Cargo.toml \
    /app/wavebench/wavebench-io/Cargo.toml \
    /app/wavebench/wavebench-vis/Cargo.toml \
    /app/docs/validation_dossier.md

echo "Audit complete. Reports:"
ls -l /app/reports/
