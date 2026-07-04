# Exhibit media signature audit library.
# Driven entirely from BEGIN; configuration is supplied with -v by bin/audit.sh.
# Stages: catalog -> signing_catalog.json, verify -> signature_evidence.json,
# report -> remediation_report.json.

function trim(s) {
    gsub(/^[ \t\r\n]+/, "", s)
    gsub(/[ \t\r\n]+$/, "", s)
    return s
}

function in_list(value, csv,    parts, n, i) {
    n = split(csv, parts, ",")
    for (i = 1; i <= n; i++) {
        if (trim(parts[i]) == value) {
            return 1
        }
    }
    return 0
}

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

function spki_fingerprint(pub,    cmd, line, parts, n, fp) {
    cmd = "openssl pkey -pubin -in '" pub "' -outform DER 2>/dev/null | openssl dgst -" fp_digest " 2>/dev/null"
    fp = ""
    if ((cmd | getline line) > 0) {
        sub(/\r$/, "", line)
        n = split(line, parts, " ")
        fp = parts[n]
    }
    close(cmd)
    return fp
}

function content_digest(media,    cmd, line, parts, n, fp) {
    cmd = "openssl dgst -sha256 '" media "' 2>/dev/null"
    fp = ""
    if ((cmd | getline line) > 0) {
        sub(/\r$/, "", line)
        n = split(line, parts, " ")
        fp = parts[n]
    }
    close(cmd)
    return fp
}

function manifest_text(id, content_hex) {
    return manifest_version "\n" id "\n" "sha256=" content_hex "\n" C_signed_at[id] "\n"
}

function verify_signature(id, content_hex,    pub, sigb64, sigbin, manifest, decode, vcmd, rc) {
    pub = C_pub[id]
    sigb64 = C_sig[id]
    sigbin = "runtime/" id ".sig.bin"
    manifest = "runtime/" id ".manifest"
    printf "%s", manifest_text(id, content_hex) > manifest
    close(manifest)
    decode = "openssl base64 -d -in '" sigb64 "' -out '" sigbin "' 2>/dev/null"
    if (system(decode) != 0) {
        return 0
    }
    if (in_list(C_algo[id], rawin_algos)) {
        vcmd = "openssl pkeyutl -verify -pubin -inkey '" pub "' -rawin -in '" manifest "' -sigfile '" sigbin "' >/dev/null 2>&1"
    } else {
        vcmd = "openssl dgst -" C_digest[id] " -verify '" pub "' -signature '" sigbin "' '" manifest "' >/dev/null 2>&1"
    }
    rc = system(vcmd)
    return (rc == 0)
}

function build_evidence(    i, id, computed, fp_match, content, ok) {
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        if (in_list(C_algo[id], rawin_algos)) {
            E_method[id] = "pkeyutl"
        } else {
            E_method[id] = "dgst"
        }
        computed = spki_fingerprint(C_pub[id])
        E_fpr[id] = computed
        content = content_digest(C_media[id])
        E_content[id] = content
        fp_match = (computed != "" && computed == C_fpr[id])
        E_match[id] = fp_match
        if (!fp_match) {
            E_valid[id] = 0
            E_reason[id] = "fingerprint_mismatch"
            continue
        }
        ok = verify_signature(id, content)
        if (ok) {
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

function image_action(id,    in_window) {
    if (!E_valid[id]) {
        I_reason[id] = E_reason[id]
        return "quarantine"
    }
    if (C_revreason[id] != "") {
        if (in_list(C_revreason[id], retroactive_reasons)) {
            I_reason[id] = C_revreason[id]
            return "quarantine"
        }
        if (C_signed_at[id] >= C_revoked_at[id]) {
            I_reason[id] = "signed_after_revocation"
            return "quarantine"
        }
    }
    in_window = (C_signed_at[id] >= C_not_before[id] && C_signed_at[id] <= C_not_after[id])
    if (!in_window) {
        if (C_exc[id] != "" && C_exc_exp[id] >= audit_time) {
            I_reason[id] = ""
            return "honor_exception"
        }
        I_reason[id] = "signed_outside_validity"
        return "quarantine"
    }
    I_reason[id] = ""
    if (C_status[id] == "active") {
        return "accept"
    }
    return "reinstate"
}

function build_report(    i, id, kid, j, seen, nk) {
    sum_accept = 0
    sum_reinstate = 0
    sum_honor = 0
    sum_quarantine = 0
    sum_revoke = 0
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        I_action[id] = image_action(id)
        if (I_action[id] == "accept") sum_accept++
        else if (I_action[id] == "reinstate") sum_reinstate++
        else if (I_action[id] == "honor_exception") sum_honor++
        else if (I_action[id] == "quarantine") sum_quarantine++
    }
    n_keys = 0
    for (i = 1; i <= n_images; i++) {
        id = order[i]
        kid = C_key[id]
        if (kid in seen) {
            continue
        }
        seen[kid] = 1
        if ((C_status[id] == "retired" || C_status[id] == "revoked") && C_trusted[id]) {
            n_keys++
            K_order[n_keys] = kid
            K_status[kid] = C_status[id]
        }
    }
    for (i = 1; i <= n_keys; i++) {
        for (j = i + 1; j <= n_keys; j++) {
            if (K_order[j] < K_order[i]) {
                nk = K_order[i]; K_order[i] = K_order[j]; K_order[j] = nk
            }
        }
    }
    sum_revoke = n_keys
}

function emit_report(    i, id, recs, rec, krecs) {
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
    krecs = ""
    for (i = 1; i <= n_keys; i++) {
        rec = "    {\n"
        rec = rec "      \"key_id\": " jstr(K_order[i]) ",\n"
        rec = rec "      \"action\": \"revoke_trust\",\n"
        rec = rec "      \"status\": " jstr(K_status[K_order[i]]) "\n"
        rec = rec "    }"
        krecs = krecs (krecs == "" ? "" : ",\n") rec
    }
    print "{" > out_report
    print "  \"audit_time\": " jstr(audit_time) "," >> out_report
    print "  \"image_actions\": [" >> out_report
    if (recs != "") print recs >> out_report
    print "  ]," >> out_report
    print "  \"key_actions\": [" >> out_report
    if (krecs != "") print krecs >> out_report
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
