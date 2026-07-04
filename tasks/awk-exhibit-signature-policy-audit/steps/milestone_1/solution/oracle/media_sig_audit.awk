# Exhibit media signature audit library.
# Driven entirely from BEGIN; configuration is supplied with -v by bin/audit.sh.
# Stages: catalog -> signing_catalog.json, verify -> signature_evidence.json,
# report -> remediation_report.json.

function jstr(s) {
    gsub(/\\/, "\\\\", s)
    gsub(/"/, "\\\"", s)
    return "\"" s "\""
}

function jnull(s) {
    if (s == "") {
        return "null"
    }
    return jstr(s)
}

function jbool(v) {
    if (v) {
        return "true"
    }
    return "false"
}

function to_utc(s,    yr, mo, dy, hh, mm, ss, zone, sign, oh, om, off, epoch) {
    if (s == "") {
        return ""
    }
    yr = substr(s, 1, 4)
    mo = substr(s, 6, 2)
    dy = substr(s, 9, 2)
    hh = substr(s, 12, 2)
    mm = substr(s, 15, 2)
    ss = substr(s, 18, 2)
    zone = substr(s, 20)
    off = 0
    if (zone != "Z" && zone != "") {
        sign = substr(zone, 1, 1)
        oh = substr(zone, 2, 2)
        om = substr(zone, 5, 2)
        off = (oh * 3600) + (om * 60)
        if (sign == "-") {
            off = -off
        }
    }
    epoch = mktime(yr " " mo " " dy " " hh " " mm " " ss) - off
    return strftime("%Y-%m-%dT%H:%M:%SZ", epoch, 1)
}

function fetch_registry(    cursor, pf, rcmd, ccmd, vcmd, line, n, a, kid, i, nextc) {
    cursor = start_cursor
    pf = "runtime/reg_page.json"
    while (cursor != "") {
        system("curl -fsS '" registry_url "/v1/keystates?cursor=" cursor "' -o '" pf "' 2>/dev/null")
        rcmd = "jq -r '.records[] | [.key_id,(.revision|tostring),.as_of,.status,(.trusted|tostring),(.revocation_reason//\"\"),(.revoked_at//\"\")] | @tsv' '" pf "'"
        while ((rcmd | getline line) > 0) {
            sub(/\r$/, "", line)
            n = split(line, a, "\t")
            kid = a[1]
            R_count[kid]++
            i = R_count[kid]
            R_rev[kid, i] = a[2]
            R_asof[kid, i] = a[3]
            R_status[kid, i] = a[4]
            R_trusted[kid, i] = a[5]
            R_reason[kid, i] = a[6]
            R_revoked[kid, i] = a[7]
        }
        close(rcmd)
        ccmd = "jq -r '.next_cursor // empty' '" pf "'"
        nextc = ""
        if ((ccmd | getline nextc) > 0) {
            sub(/\r$/, "", nextc)
        }
        close(ccmd)
        cursor = nextc
    }
    vcmd = "curl -fsS '" registry_url "/v1/voids' 2>/dev/null | jq -r '.expunged[] | [.key_id,.expunged_at] | @tsv'"
    while ((vcmd | getline line) > 0) {
        sub(/\r$/, "", line)
        n = split(line, a, "\t")
        V_void[a[1]] = a[2]
    }
    close(vcmd)
}

function reconcile(kid, db_status, db_trusted, db_reason, db_revoked,    i, best_i, best_rev, asof) {
    best_i = 0
    best_rev = -1
    for (i = 1; i <= R_count[kid]; i++) {
        asof = to_utc(R_asof[kid, i])
        if (asof <= audit_time && (R_rev[kid, i] + 0) > best_rev) {
            best_rev = R_rev[kid, i] + 0
            best_i = i
        }
    }
    if (best_i > 0) {
        REC_trusted = (R_trusted[kid, best_i] == "true")
        if (kid in V_void) {
            REC_status = "revoked"
            REC_reason = "key_expunged"
            REC_revoked = V_void[kid]
        } else {
            REC_status = R_status[kid, best_i]
            REC_reason = R_reason[kid, best_i]
            REC_revoked = R_revoked[kid, best_i]
        }
    } else if (kid in V_void) {
        REC_status = "revoked"
        REC_reason = "key_expunged"
        REC_revoked = V_void[kid]
        REC_trusted = (db_trusted == "1")
    } else {
        REC_status = db_status
        REC_trusted = (db_trusted == "1")
        REC_reason = db_reason
        REC_revoked = db_revoked
    }
    REC_revoked = to_utc(REC_revoked)
}

function sql_catalog() {
    return \
        "SELECT i.image_id, i.media_path, i.signature_path, i.signed_at, " \
        "k.key_id, k.algorithm, k.digest_algorithm, k.fingerprint, k.public_key_path, " \
        "k.status, k.trusted, k.not_before, k.not_after, k.revocation_reason, k.revoked_at, " \
        "e.exception_id, e.expires_at " \
        "FROM images i " \
        "JOIN keys k ON i.key_id = k.key_id " \
        "LEFT JOIN policy_exceptions e ON e.image_id = i.image_id " \
        "ORDER BY i.image_id;"
}

function load_catalog(    cmd, line, f, id, kid) {
    fetch_registry()
    cmd = "sqlite3 -noheader -separator '|' '" db "' \"" sql_catalog() "\""
    n_images = 0
    while ((cmd | getline line) > 0) {
        sub(/\r$/, "", line)
        if (line == "") {
            continue
        }
        f = split(line, col, "\\|")
        id = col[1]
        kid = col[5]
        n_images++
        order[n_images] = id
        C_media[id] = col[2]
        C_sig[id] = col[3]
        C_signed_at[id] = to_utc(col[4])
        C_key[id] = kid
        C_algo[id] = col[6]
        C_digest[id] = col[7]
        C_fpr[id] = col[8]
        C_pub[id] = col[9]
        C_not_before[id] = to_utc(col[12])
        C_not_after[id] = to_utc(col[13])
        reconcile(kid, col[10], col[11], col[14], col[15])
        C_status[id] = REC_status
        C_trusted[id] = REC_trusted
        C_revreason[id] = REC_reason
        C_revoked_at[id] = REC_revoked
        C_exc[id] = col[16]
        C_exc_exp[id] = to_utc(col[17])
    }
    close(cmd)
}

function emit_catalog(    i, id, recs, rec) {
    recs = ""
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        rec = "    {\n"
        rec = rec "      \"image_id\": " jstr(id) ",\n"
        rec = rec "      \"media_path\": " jstr(C_media[id]) ",\n"
        rec = rec "      \"signature_path\": " jstr(C_sig[id]) ",\n"
        rec = rec "      \"key_id\": " jstr(C_key[id]) ",\n"
        rec = rec "      \"algorithm\": " jstr(C_algo[id]) ",\n"
        rec = rec "      \"digest_algorithm\": " jnull(C_digest[id]) ",\n"
        rec = rec "      \"key_fingerprint\": " jstr(C_fpr[id]) ",\n"
        rec = rec "      \"public_key_path\": " jstr(C_pub[id]) ",\n"
        rec = rec "      \"key_status\": " jstr(C_status[id]) ",\n"
        rec = rec "      \"key_trusted\": " jbool(C_trusted[id]) ",\n"
        rec = rec "      \"key_not_before\": " jstr(C_not_before[id]) ",\n"
        rec = rec "      \"key_not_after\": " jstr(C_not_after[id]) ",\n"
        rec = rec "      \"revocation_reason\": " jnull(C_revreason[id]) ",\n"
        rec = rec "      \"revoked_at\": " jnull(C_revoked_at[id]) ",\n"
        rec = rec "      \"signed_at\": " jstr(C_signed_at[id]) ",\n"
        rec = rec "      \"exception_id\": " jnull(C_exc[id]) ",\n"
        rec = rec "      \"exception_expires_at\": " jnull(C_exc_exp[id]) "\n"
        rec = rec "    }"
        recs = recs (recs == "" ? "" : ",\n") rec
    }
    print "{" > out_catalog
    print "  \"suite\": " jstr(suite) "," >> out_catalog
    print "  \"revision\": " jstr(revision) "," >> out_catalog
    print "  \"audit_time\": " jstr(audit_time) "," >> out_catalog
    print "  \"row_count\": " n_images "," >> out_catalog
    print "  \"images\": [" >> out_catalog
    print recs >> out_catalog
    print "  ]" >> out_catalog
    print "}" >> out_catalog
    close(out_catalog)
}

BEGIN {
    load_catalog()
    if (stage == "catalog") {
        emit_catalog()
    } else {
        print "unknown stage: " stage > "/dev/stderr"
        exit 2
    }
}
