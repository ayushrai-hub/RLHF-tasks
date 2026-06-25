#!/usr/bin/gawk -f
# audit.awk — WaveBench Cargo feature-gate and CFL stability auditor
# Version 0.7.2 (development)
#
# Known issues:
#   #247  dep: prefix mishandled — optional external deps appear in feature_deps column
#   #251  ?/ optional-dep syntax split incorrectly — part before ?/ treated as external dep
#   #259  feature arrays that span multiple lines (or carry trailing commas / inline
#         comments) are parsed only by the single line that holds the `=`, so the rest
#         of the array is dropped
#   #263  CFL rule extraction only reads AUDIT-RULE lines; misses STABILITY-BOUND,
#         CFL-ANNOTATION, GUARD-REQUIRED, and PROHIBITED-COMBINATION annotations
#   #268  violation check only looks at a feature's DIRECT deps; it never resolves the
#         transitive feature graph or the crate?/feature weak-dependency rules, so it
#         misses cross-crate violations and mis-handles the guarded-* features
#   #270  cfl_margins.tsv is never produced — there is no effective-CFL-ceiling pass
#   #271  TSV headers use wrong column names
#   #279  Output rows not sorted — order depends on AWK associative-array iteration
#
# Usage:
#   gawk -f audit.awk \
#       wavebench/wavebench-core/Cargo.toml \
#       wavebench/wavebench-adaptive/Cargo.toml \
#       wavebench/wavebench-io/Cargo.toml \
#       wavebench/wavebench-vis/Cargo.toml \
#       docs/validation_dossier.md

BEGIN {
    out_features   = "/app/reports/feature_gates.tsv"
    out_rules      = "/app/reports/cfl_rules.tsv"
    out_violations = "/app/reports/audit_violations.tsv"

    # BUG #271: wrong column names in all three headers
    print "feature\tcrate\tdeps\ttype"          > out_features
    print "rule\tfeature\tbound\tsource"        > out_rules
    print "crate\tfeature\tviolation\tseverity" > out_violations

    current_crate = ""
    in_package    = 0
    in_features   = 0
    dossier_mode  = 0
    feat_seq      = 0
}

FNR == 1 {
    if (FILENAME ~ /validation_dossier\.md$/) dossier_mode = 1
    else { dossier_mode = 0; in_package = 0; in_features = 0 }
}

# ===================== CARGO.TOML PARSING =====================
!dossier_mode && /^\[package\]/  { in_package = 1; in_features = 0 }
!dossier_mode && in_package && /^name\s*=/ {
    match($0, /"([^"]+)"/, arr)
    if (arr[1] != "") { current_crate = arr[1]; in_package = 0 }
}
!dossier_mode && /^\[features\]/ { in_features = 1; in_package = 0 }
!dossier_mode && /^\[[a-z]/ && !/^\[features\]/ && !/^\[package\]/ { in_features = 0; in_package = 0 }

!dossier_mode && in_features && /^[a-z_-]/ {
    if (!match($0, /^([a-z][a-z0-9_-]*)\s*=\s*\[([^\]]*)\]/, arr)) next
    fname = arr[1]; deps_raw = arr[2]
    feat_deps = ""; ext_deps = ""

    n = split(deps_raw, deps_arr, /[",[:space:]]+/)
    for (i = 1; i <= n; i++) {
        d = deps_arr[i]
        if (d == "") continue
        if (d ~ /^dep:/) {
            # BUG #247: stripped dep name should go to ext_deps; instead kept as feature dep
            sub(/^dep:/, "", d)
            feat_deps = feat_deps (feat_deps ? "," : "") d
        } else if (d ~ /\?\//) {
            # BUG #251: ?/ split — part before ?/ wrongly treated as external dep
            n2 = split(d, parts, "?/")
            ext_deps  = ext_deps  (ext_deps  ? "," : "") parts[1]
            feat_deps = feat_deps (feat_deps ? "," : "") parts[2]
        } else {
            feat_deps = feat_deps (feat_deps ? "," : "") d
        }
    }

    # BUG #271 wrong columns; BUG #279 no sorting
    ftype = (ext_deps != "") ? "mixed" : "feature"
    all_deps = feat_deps (feat_deps && ext_deps ? "," : "") ext_deps
    print fname "\t" current_crate "\t" all_deps "\t" ftype > out_features

    key = current_crate SUBSEP fname
    store_crate[key] = current_crate
    store_fname[key] = fname
    store_fdeps[key] = feat_deps
    feat_keys[++feat_seq] = key
}

# ===================== DOSSIER PARSING =====================
# BUG #263: only AUDIT-RULE lines handled; STABILITY-BOUND / CFL-ANNOTATION /
# GUARD-REQUIRED / PROHIBITED-COMBINATION annotations are silently dropped.
dossier_mode && /^AUDIT-RULE:/ {
    if (!match($0, /AUDIT-RULE: (R-[0-9]+) features=([^ ]+) type=([^ ]+) bound=([^ ]+) source=([^ ]+)/, m)) next
    print m[1] "\t" m[2] "\t" m[4] "\t" m[5] > out_rules
}

# ===================== VIOLATION CHECK =====================
# BUG #268: only flags the literal feature named "unstable-integrator" using its
# direct deps; no transitive closure, no weak-dependency handling.
END {
    for (k = 1; k <= feat_seq; k++) {
        key = feat_keys[k]
        if (store_fname[key] == "unstable-integrator")
            print store_crate[key] "\t" store_fname[key] "\tUNSTABLE_FEATURE\tWARNING" > out_violations
    }
}
