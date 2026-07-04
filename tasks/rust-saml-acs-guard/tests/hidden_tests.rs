use samlacsguard::*;

fn strings(values: &[&str]) -> Vec<String> {
    values.iter().map(|value| (*value).to_string()).collect()
}

fn policy() -> SpPolicy {
    SpPolicy {
        entity_id: "https://sp.example.com/metadata".to_string(),
        acs_url: "https://sp.example.com/saml/acs".to_string(),
        expected_in_response_to: Some("REQ123".to_string()),
        trusted_issuers: strings(&["https://idp.example.com", "https://backup-idp.example.com"]),
        trusted_signers: strings(&["idp-signing-2026", "backup-signing-2026"]),
        allowed_signature_algorithms: strings(&["rsa-sha256", "ecdsa-sha256"]),
        now_utc: "2026-06-27T12:00:00Z".to_string(),
        clock_skew_seconds: 120,
        require_signed_response: true,
        require_signed_assertion: true,
        required_attributes: strings(&["email", "role"]),
    }
}

fn sig(target: &str, signer: &str, algorithm: &str) -> Signature {
    Signature {
        target_id: target.to_string(),
        signer: signer.to_string(),
        algorithm: algorithm.to_string(),
    }
}

fn attr(name: &str, value: &str) -> Attribute {
    Attribute {
        name: name.to_string(),
        value: value.to_string(),
    }
}

fn assertion(id: &str, subject: &str) -> SamlAssertion {
    SamlAssertion {
        id: id.to_string(),
        issuer: "https://idp.example.com".to_string(),
        subject: subject.to_string(),
        audience: "https://sp.example.com/metadata".to_string(),
        recipient: "https://sp.example.com/saml/acs".to_string(),
        in_response_to: Some("REQ123".to_string()),
        not_before: "2026-06-27T11:55:00Z".to_string(),
        not_on_or_after: "2026-06-27T12:05:00Z".to_string(),
        attributes: vec![attr("email", subject), attr("role", "admin")],
    }
}

fn response(assertions: Vec<SamlAssertion>, signatures: Vec<Signature>) -> SamlResponse {
    SamlResponse {
        id: "R1".to_string(),
        issuer: "https://idp.example.com".to_string(),
        destination: "https://sp.example.com/saml/acs".to_string(),
        in_response_to: Some("REQ123".to_string()),
        issue_instant: "2026-06-27T11:59:00Z".to_string(),
        signatures,
        assertions,
    }
}

#[test]
fn parser_handles_nested_assertions_signatures_attributes_and_comments() {
    let parsed = parse_response(
        r#"
        <!-- ignored -->
        <Response Destination="https://sp.example.com/saml/acs" ID="R100" Issuer="https://idp.example.com" IssueInstant="2026-06-27T11:59:00Z" InResponseTo="REQ123">
        <Signature Algorithm="rsa-sha256" Signer="idp-signing-2026" Target="R100"/>
        <Assertion Recipient="https://sp.example.com/saml/acs" Audience="https://sp.example.com/metadata" ID="A100" Issuer="https://idp.example.com" Subject="alice@example.com" NotOnOrAfter="2026-06-27T12:05:00Z" NotBefore="2026-06-27T11:55:00Z" InResponseTo="REQ123">
        <Attribute Value="alice@example.com" Name="email"/>
        <Attribute Name="role" Value="admin"/>
        <Signature Signer="idp-signing-2026" Target="A100" Algorithm="rsa-sha256"/>
        </Assertion>
        </Response>
        "#,
    )
    .unwrap();

    assert_eq!(parsed.id, "R100");
    assert_eq!(
        parsed.signatures,
        vec![
            sig("R100", "idp-signing-2026", "rsa-sha256"),
            sig("A100", "idp-signing-2026", "rsa-sha256"),
        ]
    );
    assert_eq!(parsed.assertions.len(), 1);
    assert_eq!(parsed.assertions[0].id, "A100");
    assert_eq!(
        parsed.assertions[0].attributes,
        vec![attr("email", "alice@example.com"), attr("role", "admin")]
    );
}

#[test]
fn parser_reports_precise_errors_for_structure_and_attributes() {
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Attribute Name=\"email\" Value=\"a\"/>\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\" Extra=\"x\">\n</Response>\n")
            .unwrap_err()
            .line,
        1
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"bad id\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n</Assertion>\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"A1\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n</Response>\n")
            .unwrap_err()
            .line,
        3
    );
}

#[test]
fn signature_wrapping_uses_signed_assertion_target_not_first_assertion() {
    let malicious = SamlAssertion {
        id: "ATTACK".to_string(),
        subject: "mallory@example.com".to_string(),
        attributes: vec![attr("email", "mallory@example.com"), attr("role", "admin")],
        ..assertion("ATTACK", "mallory@example.com")
    };
    let valid = assertion("A1", "alice@example.com");
    let decision = validate_response(
        &policy(),
        &response(
            vec![malicious, valid],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );

    assert!(decision.accepted);
    assert_eq!(decision.subject, Some("alice@example.com".to_string()));
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn duplicate_ids_are_denied_before_signature_checks() {
    let mut second = assertion("A1", "bob@example.com");
    second.attributes = vec![attr("email", "bob@example.com"), attr("role", "admin")];
    let mut p = policy();
    p.trusted_signers.clear();
    let decision = validate_response(
        &p,
        &response(
            vec![assertion("A1", "alice@example.com"), second],
            vec![sig("R1", "unknown", "rsa-sha1"), sig("A1", "unknown", "rsa-sha1")],
        ),
    );

    assert_eq!(decision.accepted, false);
    assert_eq!(decision.reasons, strings(&["duplicate-id"]));
    assert_eq!(decision.assertion_id, None);
}

#[test]
fn response_and_assertion_signature_requirements_are_target_specific() {
    let mut only_assertion_sig = response(
        vec![assertion("A1", "alice@example.com")],
        vec![sig("A1", "idp-signing-2026", "rsa-sha256")],
    );
    assert_eq!(
        validate_response(&policy(), &only_assertion_sig).reasons,
        strings(&["response-signature-required"])
    );

    only_assertion_sig.signatures = vec![sig("R1", "idp-signing-2026", "rsa-sha256")];
    assert_eq!(
        validate_response(&policy(), &only_assertion_sig).reasons,
        strings(&["assertion-signature-required"])
    );
}

#[test]
fn untrusted_signer_and_weak_algorithm_are_distinguished() {
    let untrusted = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![sig("R1", "evil-signer", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")],
        ),
    );
    assert_eq!(untrusted.reasons, strings(&["untrusted-signature"]));

    let weak = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![sig("R1", "idp-signing-2026", "rsa-sha1"), sig("A1", "idp-signing-2026", "rsa-sha256")],
        ),
    );
    assert_eq!(weak.reasons, strings(&["weak-signature-algorithm"]));
}

#[test]
fn global_denials_are_reported_in_documented_order() {
    let mut p = policy();
    p.expected_in_response_to = Some("REQ999".to_string());
    let mut r = response(
        vec![assertion("A1", "alice@example.com")],
        vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")],
    );
    r.issuer = "https://evil.example.com".to_string();
    r.destination = "https://evil.example.com/acs".to_string();
    r.in_response_to = Some("REQ123".to_string());

    assert_eq!(
        validate_response(&p, &r).reasons,
        strings(&["untrusted-issuer", "destination-mismatch", "request-id-mismatch"])
    );
}

#[test]
fn validity_window_honors_skew_and_exclusive_not_on_or_after() {
    let mut p = policy();
    p.clock_skew_seconds = 120;

    let mut early = assertion("A1", "alice@example.com");
    early.not_before = "2026-06-27T12:02:00Z".to_string();
    assert!(validate_response(
        &p,
        &response(vec![early], vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")])
    )
    .accepted);

    let mut too_early = assertion("A2", "alice@example.com");
    too_early.not_before = "2026-06-27T12:02:01Z".to_string();
    assert_eq!(
        validate_response(
            &p,
            &response(vec![too_early], vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A2", "idp-signing-2026", "rsa-sha256")])
        )
        .reasons,
        strings(&["assertion-not-yet-valid"])
    );

    let mut expired = assertion("A3", "alice@example.com");
    expired.not_on_or_after = "2026-06-27T11:58:00Z".to_string();
    assert_eq!(
        validate_response(
            &p,
            &response(vec![expired], vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A3", "idp-signing-2026", "rsa-sha256")])
        )
        .reasons,
        strings(&["assertion-expired"])
    );
}

#[test]
fn malformed_calendar_times_are_rejected_before_other_checks() {
    let mut a = assertion("A1", "alice@example.com");
    a.not_before = "2026-02-29T00:00:00Z".to_string();
    let mut r = response(vec![a], vec![sig("R1", "unknown", "rsa-sha1")]);
    r.issue_instant = "2026-06-31T11:59:00Z".to_string();
    assert_eq!(
        validate_response(&policy(), &r).reasons,
        strings(&["malformed-time"])
    );
}

#[test]
fn assertion_denials_include_audience_recipient_subject_and_attributes_in_order() {
    let mut a = assertion("A1", "");
    a.audience = "https://other-sp.example.com/metadata".to_string();
    a.recipient = "https://sp.example.com/other-acs".to_string();
    a.attributes = vec![attr("email", "alice@example.com")];
    let decision = validate_response(
        &policy(),
        &response(vec![a], vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")]),
    );
    assert_eq!(
        decision.reasons,
        strings(&[
            "audience-mismatch",
            "recipient-mismatch",
            "subject-missing",
            "attribute-missing:role",
        ])
    );
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn valid_later_covered_assertion_can_be_selected_after_invalid_covered_assertion() {
    let mut bad = assertion("A1", "mallory@example.com");
    bad.audience = "https://other-sp.example.com/metadata".to_string();
    let good = assertion("A2", "alice@example.com");
    let decision = validate_response(
        &policy(),
        &response(
            vec![bad, good],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
                sig("A2", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert!(decision.accepted);
    assert_eq!(decision.assertion_id, Some("A2".to_string()));
}

#[test]
fn if_no_covered_assertion_is_valid_first_covered_failure_is_reported() {
    let mut first = assertion("A1", "alice@example.com");
    first.audience = "wrong".to_string();
    let mut second = assertion("A2", "");
    second.attributes = Vec::new();
    let decision = validate_response(
        &policy(),
        &response(
            vec![first, second],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
                sig("A2", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(decision.reasons, strings(&["audience-mismatch"]));
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn response_signature_can_cover_assertions_when_assertion_signature_not_required() {
    let mut p = policy();
    p.require_signed_assertion = false;
    let decision = validate_response(
        &p,
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![sig("R1", "idp-signing-2026", "rsa-sha256")],
        ),
    );
    assert!(decision.accepted);
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn assertion_signatures_can_cover_when_response_signature_not_required() {
    let mut p = policy();
    p.require_signed_response = false;
    let decision = validate_response(
        &p,
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![sig("A1", "idp-signing-2026", "rsa-sha256")],
        ),
    );
    assert!(decision.accepted);
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn required_attributes_are_exact_and_reported_in_policy_order() {
    let mut p = policy();
    p.required_attributes = strings(&["email", "department", "role"]);
    let mut a = assertion("A1", "alice@example.com");
    a.attributes = vec![attr("role", "admin"), attr("email", "alice@example.com")];
    assert_eq!(
        validate_response(
            &p,
            &response(vec![a], vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")])
        )
        .reasons,
        strings(&["attribute-missing:department"])
    );
}

#[test]
fn audit_reports_duplicate_ids_missing_targets_unsigned_objects_weak_algs_and_empty_subjects() {
    let r = response(
        vec![assertion("A1", ""), assertion("A1", "bob@example.com"), assertion("A2", "carol@example.com")],
        vec![
            sig("MISSING", "idp-signing-2026", "rsa-sha256"),
            sig("R1", "idp-signing-2026", "rsa-sha1"),
            sig("A2", "idp-signing-2026", "sha1"),
        ],
    );
    assert_eq!(
        audit_response(&r),
        strings(&[
            "ERROR duplicate-id:A1",
            "ERROR signature-target-missing:MISSING",
            "WARN unsigned-assertion:A1",
            "WARN weak-signature-algorithm:rsa-sha1",
            "WARN weak-signature-algorithm:sha1",
            "WARN empty-subject:A1",
        ])
    );
}

#[test]
fn summary_lines_are_deterministic() {
    let r = response(
        vec![assertion("A1", "alice@example.com"), assertion("A2", "")],
        vec![sig("R1", "idp-signing-2026", "rsa-sha256"), sig("A1", "idp-signing-2026", "rsa-sha256")],
    );
    assert_eq!(
        summary_lines(&r),
        strings(&[
            "response R1 issuer=https://idp.example.com assertions=2 signatures=2",
            "assertion A1 issuer=https://idp.example.com subject=yes attrs=2",
            "assertion A2 issuer=https://idp.example.com subject=no attrs=2",
        ])
    );
}

#[test]
fn assertion_signature_failures_use_relevant_signature_reason() {
    let untrusted = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "stolen-dev-key", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(untrusted.reasons, strings(&["untrusted-signature"]));

    let weak = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha1"),
            ],
        ),
    );
    assert_eq!(weak.reasons, strings(&["weak-signature-algorithm"]));
}

#[test]
fn valid_signature_wins_when_noisy_signatures_target_same_assertion() {
    let decision = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "untrusted-rotation-key", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "dsa-sha1"),
                sig("A1", "backup-signing-2026", "ecdsa-sha256"),
            ],
        ),
    );
    assert!(decision.accepted);
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn duplicate_response_and_assertion_ids_are_detected_and_audited() {
    let r = response(
        vec![assertion("R1", "alice@example.com")],
        vec![sig("R1", "idp-signing-2026", "rsa-sha256")],
    );
    assert_eq!(
        validate_response(&policy(), &r).reasons,
        strings(&["duplicate-id"])
    );
    assert_eq!(audit_response(&r), strings(&["ERROR duplicate-id:R1"]));
}

#[test]
fn parser_rejects_content_after_response_nested_assertions_and_missing_signature_target() {
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n</Response>\n<Signature Target=\"R1\" Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\"/>\n")
            .unwrap_err()
            .line,
        3
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"A1\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n<Assertion ID=\"A2\" Issuer=\"https://idp.example.com\" Subject=\"b\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n")
            .unwrap_err()
            .line,
        3
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Signature Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\"/>\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
}

#[test]
fn parser_rejects_unknown_tags_and_ids_with_illegal_chars() {
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Foo ID=\"A1\"/>\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Signature Target=\"A 1\" Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\"/>\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
}

#[test]
fn leap_day_times_are_valid_but_non_leap_feb_29_is_malformed() {
    let mut p = policy();
    p.now_utc = "2024-02-29T12:00:00Z".to_string();
    let mut a = assertion("A1", "alice@example.com");
    a.not_before = "2024-02-29T11:59:00Z".to_string();
    a.not_on_or_after = "2024-02-29T12:01:00Z".to_string();
    let mut r = response(
        vec![a],
        vec![
            sig("R1", "idp-signing-2026", "rsa-sha256"),
            sig("A1", "idp-signing-2026", "rsa-sha256"),
        ],
    );
    r.issue_instant = "2024-02-29T11:59:30Z".to_string();
    assert!(validate_response(&p, &r).accepted);

    r.assertions[0].not_before = "2023-02-29T11:59:00Z".to_string();
    assert_eq!(
        validate_response(&p, &r).reasons,
        strings(&["malformed-time"])
    );
}

#[test]
fn missing_signature_target_does_not_satisfy_required_response_signature_and_is_audited() {
    let r = response(
        vec![assertion("A1", "alice@example.com")],
        vec![
            sig("R2", "idp-signing-2026", "rsa-sha256"),
            sig("A1", "idp-signing-2026", "rsa-sha256"),
        ],
    );
    assert_eq!(
        validate_response(&policy(), &r).reasons,
        strings(&["response-signature-required"])
    );
    assert_eq!(
        audit_response(&r),
        strings(&["ERROR signature-target-missing:R2", "WARN unsigned-response"])
    );
}

#[test]
fn attributes_are_case_sensitive_and_do_not_use_values_as_names() {
    let mut a = assertion("A1", "alice@example.com");
    a.attributes = vec![
        attr("Email", "alice@example.com"),
        attr("role", "admin"),
        attr("profile", "email"),
    ];
    let decision = validate_response(
        &policy(),
        &response(
            vec![a],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(decision.reasons, strings(&["attribute-missing:email"]));
}

#[test]
fn duplicate_xml_attributes_are_parse_errors() {
    assert_eq!(
        parse_response("<Response ID=\"R1\" ID=\"R2\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n</Response>\n")
            .unwrap_err()
            .line,
        1
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"A1\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n<Attribute Name=\"email\" Name=\"role\" Value=\"a\"/>\n")
            .unwrap_err()
            .line,
        3
    );
}

#[test]
fn only_complete_whole_line_comments_are_ignored() {
    let parsed = parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<!-- verifier trace comment -->\n</Response>\n")
        .unwrap();
    assert_eq!(parsed.id, "R1");

    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<!-- unterminated comment\n</Response>\n")
            .unwrap_err()
            .line,
        2
    );
}

#[test]
fn absent_policy_request_id_allows_absent_response_and_assertion_correlation() {
    let mut p = policy();
    p.expected_in_response_to = None;
    let mut r = response(
        vec![assertion("A1", "alice@example.com")],
        vec![
            sig("R1", "idp-signing-2026", "rsa-sha256"),
            sig("A1", "idp-signing-2026", "rsa-sha256"),
        ],
    );
    r.in_response_to = None;
    r.assertions[0].in_response_to = None;

    let decision = validate_response(&p, &r);
    assert!(decision.accepted);
    assert_eq!(decision.subject, Some("alice@example.com".to_string()));
}

#[test]
fn optional_but_present_bad_response_signature_is_still_rejected() {
    let mut p = policy();
    p.require_signed_response = false;
    let weak = validate_response(
        &p,
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "idp-signing-2026", "dsa-sha1"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(weak.reasons, strings(&["weak-signature-algorithm"]));

    let untrusted = validate_response(
        &p,
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "retired-signing-key", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(untrusted.reasons, strings(&["untrusted-signature"]));
}

#[test]
fn mixed_relevant_signatures_are_weak_when_a_trusted_signer_uses_only_bad_algorithms() {
    let decision = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "unknown-signer", "rsa-sha256"),
                sig("A1", "backup-signing-2026", "sha1"),
            ],
        ),
    );
    assert_eq!(decision.reasons, strings(&["weak-signature-algorithm"]));
}

#[test]
fn response_signature_required_precedes_assertion_signature_errors() {
    let decision = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![sig("A1", "unknown-signer", "rsa-sha256")],
        ),
    );
    assert_eq!(decision.reasons, strings(&["response-signature-required"]));
    assert_eq!(decision.assertion_id, None);
}

#[test]
fn parser_accepts_complex_allowed_ids_and_signature_targets() {
    let parsed = parse_response(
        "<Response ID=\"R:1.2-3_A\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Signature Target=\"R:1.2-3_A\" Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\"/>\n<Assertion ID=\"A:1.2-3_B\" Issuer=\"https://idp.example.com\" Subject=\"alice@example.com\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n<Signature Target=\"A:1.2-3_B\" Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\"/>\n</Assertion>\n</Response>\n",
    )
    .unwrap();
    assert_eq!(parsed.id, "R:1.2-3_A");
    assert_eq!(parsed.assertions[0].id, "A:1.2-3_B");
    assert_eq!(parsed.signatures[1].target_id, "A:1.2-3_B");
}

#[test]
fn audit_duplicate_ids_are_reported_in_discovery_order() {
    let r = response(
        vec![
            assertion("R1", "one@example.com"),
            assertion("A1", "two@example.com"),
            assertion("A1", "three@example.com"),
            assertion("R1", "four@example.com"),
        ],
        vec![
            sig("R1", "idp-signing-2026", "rsa-sha256"),
            sig("A1", "idp-signing-2026", "rsa-sha256"),
        ],
    );
    assert_eq!(
        audit_response(&r),
        strings(&[
            "ERROR duplicate-id:R1",
            "ERROR duplicate-id:A1",
            "ERROR duplicate-id:R1",
        ])
    );
}

#[test]
fn assertion_level_denials_include_all_reasons_in_global_order() {
    let mut a = assertion("A1", "");
    a.issuer = "https://evil-idp.example.com".to_string();
    a.audience = "https://attacker.example.com/metadata".to_string();
    a.recipient = "https://attacker.example.com/acs".to_string();
    a.in_response_to = Some("REQ999".to_string());
    a.not_before = "2026-06-27T12:10:00Z".to_string();
    a.not_on_or_after = "2026-06-27T11:50:00Z".to_string();
    a.attributes = Vec::new();

    let decision = validate_response(
        &policy(),
        &response(
            vec![a],
            vec![
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(
        decision.reasons,
        strings(&[
            "untrusted-issuer",
            "request-id-mismatch",
            "assertion-not-yet-valid",
            "assertion-expired",
            "audience-mismatch",
            "recipient-mismatch",
            "subject-missing",
            "attribute-missing:email",
            "attribute-missing:role",
        ])
    );
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn parser_preserves_spaces_inside_quoted_attribute_values() {
    let parsed = parse_response(
        "<Response IssueInstant=\"2026-06-27T11:59:00Z\" Destination=\"https://sp.example.com/saml/acs\" Issuer=\"https://idp.example.com\" ID=\"R1\" InResponseTo=\"REQ123\">\n<Signature Algorithm=\"rsa-sha256\" Target=\"R1\" Signer=\"idp-signing-2026\"/>\n<Assertion Recipient=\"https://sp.example.com/saml/acs\" Audience=\"https://sp.example.com/metadata\" NotOnOrAfter=\"2026-06-27T12:05:00Z\" NotBefore=\"2026-06-27T11:55:00Z\" Subject=\"Alice Example\" Issuer=\"https://idp.example.com\" ID=\"A1\" InResponseTo=\"REQ123\">\n<Attribute Value=\"alice@example.com\" Name=\"email\"/>\n<Attribute Name=\"role\" Value=\"Security Operations Lead\"/>\n<Signature Signer=\"idp-signing-2026\" Algorithm=\"rsa-sha256\" Target=\"A1\"/>\n</Assertion>\n</Response>\n",
    )
    .unwrap();

    assert_eq!(parsed.assertions[0].subject, "Alice Example");
    assert_eq!(parsed.assertions[0].attributes[1], attr("role", "Security Operations Lead"));
    let decision = validate_response(&policy(), &parsed);
    assert!(decision.accepted);
    assert_eq!(decision.subject, Some("Alice Example".to_string()));
}

#[test]
fn parser_rejects_unterminated_quoted_values_and_raw_angle_brackets() {
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"A1\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n<Attribute Name=\"role\" Value=\"Security Operations Lead/>\n</Assertion>\n</Response>\n")
            .unwrap_err()
            .line,
        3
    );
    assert_eq!(
        parse_response("<Response ID=\"R1\" Issuer=\"https://idp.example.com\" Destination=\"https://sp.example.com/saml/acs\" IssueInstant=\"2026-06-27T11:59:00Z\">\n<Assertion ID=\"A1\" Issuer=\"https://idp.example.com\" Subject=\"a\" Audience=\"https://sp.example.com/metadata\" Recipient=\"https://sp.example.com/saml/acs\" NotBefore=\"2026-06-27T11:55:00Z\" NotOnOrAfter=\"2026-06-27T12:05:00Z\">\n<Attribute Name=\"role\" Value=\"Security <Admin>\"/>\n</Assertion>\n</Response>\n")
            .unwrap_err()
            .line,
        3
    );
}

#[test]
fn valid_response_signature_wins_among_bad_response_signatures() {
    let decision = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1", "unknown-signer", "rsa-sha256"),
                sig("R1", "backup-signing-2026", "rsa-sha1"),
                sig("R1", "idp-signing-2026", "rsa-sha256"),
                sig("A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert!(decision.accepted);
    assert_eq!(decision.assertion_id, Some("A1".to_string()));
}

#[test]
fn signature_target_matching_is_exact_not_prefix_suffix_or_case_insensitive() {
    let decision = validate_response(
        &policy(),
        &response(
            vec![assertion("A1", "alice@example.com")],
            vec![
                sig("R1-extra", "idp-signing-2026", "rsa-sha256"),
                sig("a1", "idp-signing-2026", "rsa-sha256"),
                sig("prefix-A1", "idp-signing-2026", "rsa-sha256"),
            ],
        ),
    );
    assert_eq!(decision.reasons, strings(&["response-signature-required"]));
}

#[test]
fn audit_reports_repeated_missing_signature_targets_in_signature_order() {
    let r = response(
        vec![assertion("A1", "alice@example.com")],
        vec![
            sig("Z9", "idp-signing-2026", "rsa-sha256"),
            sig("R1", "idp-signing-2026", "rsa-sha256"),
            sig("Z9", "backup-signing-2026", "ecdsa-sha256"),
        ],
    );
    assert_eq!(
        audit_response(&r),
        strings(&[
            "ERROR signature-target-missing:Z9",
            "ERROR signature-target-missing:Z9",
            "WARN unsigned-assertion:A1",
        ])
    );
}

#[test]
fn no_assertions_are_denied_even_when_assertion_signing_is_not_required() {
    let mut p = policy();
    p.require_signed_assertion = false;
    let decision = validate_response(
        &p,
        &response(Vec::new(), vec![sig("R1", "idp-signing-2026", "rsa-sha256")]),
    );
    assert_eq!(decision.reasons, strings(&["assertion-signature-required"]));
    assert_eq!(decision.assertion_id, None);
}
