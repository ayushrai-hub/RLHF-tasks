use samlacsguard::*;

fn policy() -> SpPolicy {
    SpPolicy {
        entity_id: "https://sp.example.com/metadata".to_string(),
        acs_url: "https://sp.example.com/saml/acs".to_string(),
        expected_in_response_to: Some("REQ123".to_string()),
        trusted_issuers: vec!["https://idp.example.com".to_string()],
        trusted_signers: vec!["idp-signing-2026".to_string()],
        allowed_signature_algorithms: vec!["rsa-sha256".to_string()],
        now_utc: "2026-06-27T12:00:00Z".to_string(),
        clock_skew_seconds: 120,
        require_signed_response: true,
        require_signed_assertion: true,
        required_attributes: vec!["email".to_string()],
    }
}

#[test]
fn parses_response_open_tag() {
    let parsed = parse_response(
        r#"<Response ID="R1" Issuer="https://idp.example.com" Destination="https://sp.example.com/saml/acs" InResponseTo="REQ123" IssueInstant="2026-06-27T11:59:00Z">
</Response>"#,
    )
    .unwrap();
    assert_eq!(parsed.id, "R1");
    assert_eq!(parsed.issuer, "https://idp.example.com");
    assert_eq!(parsed.in_response_to, Some("REQ123".to_string()));
}

#[test]
fn accepts_simple_constructed_response() {
    let mut response = parse_response(
        r#"<Response ID="R1" Issuer="https://idp.example.com" Destination="https://sp.example.com/saml/acs" InResponseTo="REQ123" IssueInstant="2026-06-27T11:59:00Z">
</Response>"#,
    )
    .unwrap();
    response.signatures.push(Signature {
        target_id: "R1".to_string(),
        signer: "idp-signing-2026".to_string(),
        algorithm: "rsa-sha256".to_string(),
    });
    response.assertions.push(SamlAssertion {
        id: "A1".to_string(),
        issuer: "https://idp.example.com".to_string(),
        subject: "alice@example.com".to_string(),
        audience: "https://sp.example.com/metadata".to_string(),
        recipient: "https://sp.example.com/saml/acs".to_string(),
        in_response_to: Some("REQ123".to_string()),
        not_before: "2026-06-27T11:55:00Z".to_string(),
        not_on_or_after: "2026-06-27T12:05:00Z".to_string(),
        attributes: vec![Attribute {
            name: "email".to_string(),
            value: "alice@example.com".to_string(),
        }],
    });
    response.signatures.push(Signature {
        target_id: "A1".to_string(),
        signer: "idp-signing-2026".to_string(),
        algorithm: "rsa-sha256".to_string(),
    });

    let decision = validate_response(&policy(), &response);
    assert!(decision.accepted);
    assert_eq!(decision.subject, Some("alice@example.com".to_string()));
}

#[test]
fn summary_reports_response_and_assertion_counts() {
    let mut response = parse_response(
        r#"<Response ID="R1" Issuer="https://idp.example.com" Destination="https://sp.example.com/saml/acs" IssueInstant="2026-06-27T11:59:00Z">
</Response>"#,
    )
    .unwrap();
    response.assertions.push(SamlAssertion {
        id: "A1".to_string(),
        issuer: "https://idp.example.com".to_string(),
        subject: "".to_string(),
        audience: "https://sp.example.com/metadata".to_string(),
        recipient: "https://sp.example.com/saml/acs".to_string(),
        in_response_to: None,
        not_before: "2026-06-27T11:55:00Z".to_string(),
        not_on_or_after: "2026-06-27T12:05:00Z".to_string(),
        attributes: Vec::new(),
    });
    assert_eq!(
        summary_lines(&response),
        vec![
            "response R1 issuer=https://idp.example.com assertions=1 signatures=0".to_string(),
            "assertion A1 issuer=https://idp.example.com subject=no attrs=0".to_string(),
        ]
    );
}
