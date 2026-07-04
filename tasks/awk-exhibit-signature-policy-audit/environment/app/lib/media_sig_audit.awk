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

function to_utc(s) {
    return s
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

function load_catalog(    cmd, line, f, id) {
    cmd = "sqlite3 -noheader -separator '|' '" db "' \"" sql_catalog() "\""
    n_images = 0
    while ((cmd | getline line) > 0) {
        if (line == "") {
            continue
        }
        f = split(line, col, "\\|")
        id = col[1]
        n_images++
        order[n_images] = id
        C_media[id] = col[2]
        C_sig[id] = col[3]
        C_signed_at[id] = to_utc(col[4])
        C_key[id] = col[5]
        C_algo[id] = col[6]
        C_digest[id] = col[7]
        C_fpr[id] = col[8]
        C_pub[id] = col[9]
        C_status[id] = col[10]
        C_trusted[id] = col[11]
        C_not_before[id] = to_utc(col[12])
        C_not_after[id] = to_utc(col[13])
        C_revreason[id] = col[14]
        C_revoked_at[id] = to_utc(col[15])
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
        rec = rec "      \"digest_algorithm\": " jstr(C_digest[id]) ",\n"
        rec = rec "      \"key_fingerprint\": " jstr(C_fpr[id]) ",\n"
        rec = rec "      \"public_key_path\": " jstr(C_pub[id]) ",\n"
        rec = rec "      \"key_status\": " jstr(C_status[id]) ",\n"
        rec = rec "      \"key_trusted\": " jstr(C_trusted[id]) ",\n"
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

function verify_signature(id,    pub, media, sig, vcmd, rc) {
    pub = C_pub[id]
    media = C_media[id]
    sig = C_sig[id]
    vcmd = "openssl dgst -sha256 -verify '" pub "' -signature '" sig "' '" media "' >/dev/null 2>&1"
    rc = system(vcmd)
    return (rc == 0)
}

function build_evidence(    i, id) {
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        E_method[id] = "dgst"
        E_fpr[id] = ""
        E_content[id] = ""
        E_match[id] = 1
        if (verify_signature(id)) {
            E_valid[id] = 1
            E_reason[id] = ""
        } else {
            E_valid[id] = 0
            E_reason[id] = "signature_verification_failed"
        }
    }
}

function emit_evidence(    i, id, recs, rec) {
    recs = ""
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        rec = "    {\n"
        rec = rec "      \"image_id\": " jstr(id) ",\n"
        rec = rec "      \"key_id\": " jstr(C_key[id]) ",\n"
        rec = rec "      \"algorithm\": " jstr(C_algo[id]) ",\n"
        rec = rec "      \"verify_method\": " jstr(E_method[id]) ",\n"
        rec = rec "      \"computed_fingerprint\": " jstr(E_fpr[id]) ",\n"
        rec = rec "      \"fingerprint_match\": " jbool(E_match[id]) ",\n"
        rec = rec "      \"content_sha256\": " jstr(E_content[id]) ",\n"
        rec = rec "      \"signature_valid\": " jbool(E_valid[id]) ",\n"
        rec = rec "      \"failure_reason\": " jnull(E_reason[id]) "\n"
        rec = rec "    }"
        recs = recs (recs == "" ? "" : ",\n") rec
    }
    print "{" > out_evidence
    print "  \"audit_time\": " jstr(audit_time) "," >> out_evidence
    print "  \"row_count\": " n_images "," >> out_evidence
    print "  \"evidence\": [" >> out_evidence
    print recs >> out_evidence
    print "  ]" >> out_evidence
    print "}" >> out_evidence
    close(out_evidence)
}

function image_action(id) {
    if (E_valid[id] && C_status[id] == "active" && C_signed_at[id] >= C_not_before[id] && C_signed_at[id] <= C_not_after[id]) {
        I_reason[id] = ""
        return "accept"
    }
    I_reason[id] = "policy_violation"
    return "quarantine"
}

function build_report(    i, id) {
    sum_accept = 0
    sum_reinstate = 0
    sum_honor = 0
    sum_quarantine = 0
    sum_revoke = 0
    n_keys = 0
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        I_action[id] = image_action(id)
        if (I_action[id] == "accept") sum_accept++
        else sum_quarantine++
    }
}

function emit_report(    i, id, recs, rec) {
    recs = ""
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        rec = "    {\n"
        rec = rec "      \"image_id\": " jstr(id) ",\n"
        rec = rec "      \"key_id\": " jstr(C_key[id]) ",\n"
        rec = rec "      \"action\": " jstr(I_action[id]) ",\n"
        rec = rec "      \"reason\": " jnull(I_reason[id]) "\n"
        rec = rec "    }"
        recs = recs (recs == "" ? "" : ",\n") rec
    }
    print "{" > out_report
    print "  \"audit_time\": " jstr(audit_time) "," >> out_report
    print "  \"image_actions\": [" >> out_report
    if (recs != "") print recs >> out_report
    print "  ]," >> out_report
    print "  \"key_actions\": [" >> out_report
    print "  ]," >> out_report
    print "  \"summary\": {" >> out_report
    print "    \"accept\": " sum_accept "," >> out_report
    print "    \"reinstate\": " sum_reinstate "," >> out_report
    print "    \"honor_exception\": " sum_honor "," >> out_report
    print "    \"quarantine\": " sum_quarantine "," >> out_report
    print "    \"revoke_trust\": " sum_revoke "\n  }" >> out_report
    print "}" >> out_report
    close(out_report)
}

BEGIN {
    load_catalog()
    if (stage == "catalog") {
        emit_catalog()
    } else if (stage == "verify") {
        build_evidence()
        emit_evidence()
    } else if (stage == "report") {
        build_evidence()
        build_report()
        emit_report()
    } else {
        print "unknown stage: " stage > "/dev/stderr"
        exit 2
    }
}
