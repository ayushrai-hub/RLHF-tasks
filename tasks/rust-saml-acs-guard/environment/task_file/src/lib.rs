#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SpPolicy {
    pub entity_id: String,
    pub acs_url: String,
    pub expected_in_response_to: Option<String>,
    pub trusted_issuers: Vec<String>,
    pub trusted_signers: Vec<String>,
    pub allowed_signature_algorithms: Vec<String>,
    pub now_utc: String,
    pub clock_skew_seconds: i64,
    pub require_signed_response: bool,
    pub require_signed_assertion: bool,
    pub required_attributes: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SamlResponse {
    pub id: String,
    pub issuer: String,
    pub destination: String,
    pub in_response_to: Option<String>,
    pub issue_instant: String,
    pub signatures: Vec<Signature>,
    pub assertions: Vec<SamlAssertion>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SamlAssertion {
    pub id: String,
    pub issuer: String,
    pub subject: String,
    pub audience: String,
    pub recipient: String,
    pub in_response_to: Option<String>,
    pub not_before: String,
    pub not_on_or_after: String,
    pub attributes: Vec<Attribute>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Signature {
    pub target_id: String,
    pub signer: String,
    pub algorithm: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Attribute {
    pub name: String,
    pub value: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Decision {
    pub accepted: bool,
    pub subject: Option<String>,
    pub reasons: Vec<String>,
    pub assertion_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ParseError {
    pub line: usize,
    pub message: String,
}

pub fn parse_response(input: &str) -> Result<SamlResponse, ParseError> {
    let mut response: Option<SamlResponse> = None;
    for (idx, raw) in input.lines().enumerate() {
        let line_no = idx + 1;
        let line = raw.trim();
        if line.is_empty() || line.starts_with("<!--") {
            continue;
        }
        if line.starts_with("<Response ") {
            let attrs = parse_attrs(line_no, line, "Response", false)?;
            response = Some(SamlResponse {
                id: get_attr(line_no, &attrs, "ID")?,
                issuer: get_attr(line_no, &attrs, "Issuer")?,
                destination: get_attr(line_no, &attrs, "Destination")?,
                in_response_to: attrs.iter().find(|(k, _)| k == "InResponseTo").map(|(_, v)| v.clone()),
                issue_instant: get_attr(line_no, &attrs, "IssueInstant")?,
                signatures: Vec::new(),
                assertions: Vec::new(),
            });
        }
    }
    response.ok_or_else(|| parse_error(1, "missing response"))
}

pub fn validate_response(policy: &SpPolicy, response: &SamlResponse) -> Decision {
    if response.issuer != policy.trusted_issuers.get(0).cloned().unwrap_or_default() {
        return denied("untrusted-issuer", None);
    }
    if response.destination != policy.acs_url {
        return denied("destination-mismatch", None);
    }
    if let Some(assertion) = response.assertions.first() {
        Decision {
            accepted: true,
            subject: Some(assertion.subject.clone()),
            reasons: Vec::new(),
            assertion_id: Some(assertion.id.clone()),
        }
    } else {
        denied("assertion-signature-required", None)
    }
}

pub fn audit_response(response: &SamlResponse) -> Vec<String> {
    let mut findings = Vec::new();
    if !response.signatures.iter().any(|sig| sig.target_id == response.id) {
        findings.push("WARN unsigned-response".to_string());
    }
    findings
}

pub fn summary_lines(response: &SamlResponse) -> Vec<String> {
    let mut lines = vec![format!(
        "response {} issuer={} assertions={} signatures={}",
        response.id,
        response.issuer,
        response.assertions.len(),
        response.signatures.len()
    )];
    for assertion in &response.assertions {
        lines.push(format!(
            "assertion {} issuer={} subject={} attrs={}",
            assertion.id,
            assertion.issuer,
            if assertion.subject.is_empty() { "no" } else { "yes" },
            assertion.attributes.len()
        ));
    }
    lines
}

fn parse_attrs(line: usize, tag: &str, name: &str, self_closing: bool) -> Result<Vec<(String, String)>, ParseError> {
    let prefix = format!("<{} ", name);
    let suffix = if self_closing { "/>" } else { ">" };
    if !tag.starts_with(&prefix) || !tag.ends_with(suffix) {
        return Err(parse_error(line, "invalid tag"));
    }
    let inner = &tag[prefix.len()..tag.len() - suffix.len()];
    let mut attrs = Vec::new();
    for part in inner.split_whitespace() {
        let Some((key, value)) = part.split_once("=\"") else {
            return Err(parse_error(line, "invalid attribute"));
        };
        let Some(value) = value.strip_suffix('"') else {
            return Err(parse_error(line, "invalid attribute"));
        };
        attrs.push((key.to_string(), value.to_string()));
    }
    Ok(attrs)
}

fn get_attr(line: usize, attrs: &[(String, String)], key: &str) -> Result<String, ParseError> {
    attrs
        .iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.clone())
        .ok_or_else(|| parse_error(line, "missing attribute"))
}

fn denied(reason: &str, assertion_id: Option<String>) -> Decision {
    Decision {
        accepted: false,
        subject: None,
        reasons: vec![reason.to_string()],
        assertion_id,
    }
}

fn parse_error(line: usize, message: &str) -> ParseError {
    ParseError {
        line,
        message: message.to_string(),
    }
}
