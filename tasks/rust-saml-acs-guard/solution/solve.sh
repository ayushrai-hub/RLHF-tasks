#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/cargo/bin:$PATH"
export APP_DIR="${APP_DIR:-/app/task_file}"

python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["APP_DIR"]) / "src" / "lib.rs"
path.write_text(r'''use std::collections::{BTreeSet, HashSet};

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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SigStatus {
    Missing,
    Untrusted,
    Weak,
    Valid,
}

pub fn parse_response(input: &str) -> Result<SamlResponse, ParseError> {
    let mut response: Option<SamlResponse> = None;
    let mut current: Option<SamlAssertion> = None;
    let mut closed = false;

    for (idx, raw) in input.lines().enumerate() {
        let line_no = idx + 1;
        let line = raw.trim();
        if line.is_empty() || (line.starts_with("<!--") && line.ends_with("-->")) {
            continue;
        }
        if closed {
            return Err(parse_error(line_no, "content after response"));
        }
        if line.starts_with("<Response ") {
            if response.is_some() || current.is_some() {
                return Err(parse_error(line_no, "nested response"));
            }
            let attrs = parse_attrs(line_no, line, "Response", false, &["ID", "Issuer", "Destination", "InResponseTo", "IssueInstant"])?;
            let id = get_attr(line_no, &attrs, "ID")?;
            validate_id(line_no, &id)?;
            response = Some(SamlResponse {
                id,
                issuer: get_attr(line_no, &attrs, "Issuer")?,
                destination: get_attr(line_no, &attrs, "Destination")?,
                in_response_to: opt_attr(&attrs, "InResponseTo"),
                issue_instant: get_attr(line_no, &attrs, "IssueInstant")?,
                signatures: Vec::new(),
                assertions: Vec::new(),
            });
        } else if line == "</Response>" {
            if current.is_some() {
                return Err(parse_error(line_no, "unclosed assertion"));
            }
            if response.is_none() {
                return Err(parse_error(line_no, "response not open"));
            }
            closed = true;
        } else if line.starts_with("<Assertion ") {
            if response.is_none() || current.is_some() {
                return Err(parse_error(line_no, "invalid assertion"));
            }
            let attrs = parse_attrs(
                line_no,
                line,
                "Assertion",
                false,
                &[
                    "ID",
                    "Issuer",
                    "Subject",
                    "Audience",
                    "Recipient",
                    "InResponseTo",
                    "NotBefore",
                    "NotOnOrAfter",
                ],
            )?;
            let id = get_attr(line_no, &attrs, "ID")?;
            validate_id(line_no, &id)?;
            current = Some(SamlAssertion {
                id,
                issuer: get_attr(line_no, &attrs, "Issuer")?,
                subject: get_attr(line_no, &attrs, "Subject")?,
                audience: get_attr(line_no, &attrs, "Audience")?,
                recipient: get_attr(line_no, &attrs, "Recipient")?,
                in_response_to: opt_attr(&attrs, "InResponseTo"),
                not_before: get_attr(line_no, &attrs, "NotBefore")?,
                not_on_or_after: get_attr(line_no, &attrs, "NotOnOrAfter")?,
                attributes: Vec::new(),
            });
        } else if line == "</Assertion>" {
            let assertion = current
                .take()
                .ok_or_else(|| parse_error(line_no, "assertion not open"))?;
            response
                .as_mut()
                .ok_or_else(|| parse_error(line_no, "response not open"))?
                .assertions
                .push(assertion);
        } else if line.starts_with("<Signature ") {
            if response.is_none() {
                return Err(parse_error(line_no, "response not open"));
            }
            let attrs = parse_attrs(line_no, line, "Signature", true, &["Target", "Signer", "Algorithm"])?;
            let target = get_attr(line_no, &attrs, "Target")?;
            validate_id(line_no, &target)?;
            response.as_mut().unwrap().signatures.push(Signature {
                target_id: target,
                signer: get_attr(line_no, &attrs, "Signer")?,
                algorithm: get_attr(line_no, &attrs, "Algorithm")?,
            });
        } else if line.starts_with("<Attribute ") {
            let attrs = parse_attrs(line_no, line, "Attribute", true, &["Name", "Value"])?;
            let attribute = Attribute {
                name: get_attr(line_no, &attrs, "Name")?,
                value: get_attr(line_no, &attrs, "Value")?,
            };
            current
                .as_mut()
                .ok_or_else(|| parse_error(line_no, "attribute outside assertion"))?
                .attributes
                .push(attribute);
        } else {
            return Err(parse_error(line_no, "unknown tag"));
        }
    }

    if current.is_some() {
        return Err(parse_error(input.lines().count().max(1), "unclosed assertion"));
    }
    if !closed {
        return Err(parse_error(input.lines().count().max(1), "unclosed response"));
    }
    response.ok_or_else(|| parse_error(1, "missing response"))
}

pub fn validate_response(policy: &SpPolicy, response: &SamlResponse) -> Decision {
    if parse_time(&policy.now_utc).is_none()
        || parse_time(&response.issue_instant).is_none()
        || response.assertions.iter().any(|assertion| {
            parse_time(&assertion.not_before).is_none()
                || parse_time(&assertion.not_on_or_after).is_none()
        })
    {
        return denied(vec!["malformed-time".to_string()], None);
    }

    if has_duplicate_ids(response) {
        return denied(vec!["duplicate-id".to_string()], None);
    }

    let mut global = Vec::new();
    if !policy.trusted_issuers.contains(&response.issuer) {
        global.push("untrusted-issuer".to_string());
    }
    if response.destination != policy.acs_url {
        global.push("destination-mismatch".to_string());
    }
    if let Some(expected) = &policy.expected_in_response_to {
        if response.in_response_to.as_ref() != Some(expected) {
            global.push("request-id-mismatch".to_string());
        }
    }
    if !global.is_empty() {
        return denied(global, None);
    }

    let response_sig = signature_status(policy, response, &response.id);
    if let Some(reason) = signature_problem(response_sig, policy.require_signed_response, "response-signature-required") {
        return denied(vec![reason.to_string()], None);
    }

    let mut covered = Vec::new();
    let mut assertion_signature_problem: Option<&str> = None;
    for (idx, assertion) in response.assertions.iter().enumerate() {
        let status = signature_status(policy, response, &assertion.id);
        if policy.require_signed_assertion {
            match status {
                SigStatus::Valid => covered.push(idx),
                SigStatus::Untrusted if assertion_signature_problem.is_none() => {
                    assertion_signature_problem = Some("untrusted-signature");
                }
                SigStatus::Weak if assertion_signature_problem.is_none() => {
                    assertion_signature_problem = Some("weak-signature-algorithm");
                }
                _ => {}
            }
        } else if response_sig == SigStatus::Valid || status == SigStatus::Valid {
            covered.push(idx);
        }
    }
    if covered.is_empty() {
        if let Some(reason) = assertion_signature_problem {
            return denied(vec![reason.to_string()], None);
        }
        return denied(vec!["assertion-signature-required".to_string()], None);
    }

    let mut first_failure: Option<(Vec<String>, String)> = None;
    for idx in covered {
        let assertion = &response.assertions[idx];
        let reasons = assertion_reasons(policy, assertion);
        if reasons.is_empty() {
            return Decision {
                accepted: true,
                subject: Some(assertion.subject.clone()),
                reasons: Vec::new(),
                assertion_id: Some(assertion.id.clone()),
            };
        }
        if first_failure.is_none() {
            first_failure = Some((reasons, assertion.id.clone()));
        }
    }

    let (reasons, assertion_id) = first_failure.unwrap_or_else(|| {
        (
            vec!["assertion-signature-required".to_string()],
            String::new(),
        )
    });
    denied(reasons, if assertion_id.is_empty() { None } else { Some(assertion_id) })
}

pub fn audit_response(response: &SamlResponse) -> Vec<String> {
    let mut findings = Vec::new();
    let mut ids = HashSet::new();
    ids.insert(response.id.clone());
    for assertion in &response.assertions {
        if !ids.insert(assertion.id.clone()) {
            findings.push(format!("ERROR duplicate-id:{}", assertion.id));
        }
    }

    let all_ids = response_ids(response);
    for signature in &response.signatures {
        if !all_ids.contains(&signature.target_id) {
            findings.push(format!("ERROR signature-target-missing:{}", signature.target_id));
        }
    }
    if !response.signatures.iter().any(|sig| sig.target_id == response.id) {
        findings.push("WARN unsigned-response".to_string());
    }
    let mut reported_unsigned = BTreeSet::new();
    for assertion in &response.assertions {
        if !response.signatures.iter().any(|sig| sig.target_id == assertion.id)
            && reported_unsigned.insert(assertion.id.clone())
        {
            findings.push(format!("WARN unsigned-assertion:{}", assertion.id));
        }
    }
    for signature in &response.signatures {
        if is_weak_algorithm(&signature.algorithm) {
            findings.push(format!(
                "WARN weak-signature-algorithm:{}",
                signature.algorithm
            ));
        }
    }
    for assertion in &response.assertions {
        if assertion.subject.is_empty() {
            findings.push(format!("WARN empty-subject:{}", assertion.id));
        }
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

fn assertion_reasons(policy: &SpPolicy, assertion: &SamlAssertion) -> Vec<String> {
    let mut reasons = Vec::new();
    let now = parse_time(&policy.now_utc).unwrap();
    let not_before = parse_time(&assertion.not_before).unwrap();
    let not_on_or_after = parse_time(&assertion.not_on_or_after).unwrap();
    let skew = policy.clock_skew_seconds.max(0);

    if !policy.trusted_issuers.contains(&assertion.issuer) {
        reasons.push("untrusted-issuer".to_string());
    }
    if let Some(expected) = &policy.expected_in_response_to {
        if assertion.in_response_to.as_ref() != Some(expected) {
            reasons.push("request-id-mismatch".to_string());
        }
    }
    if now + skew < not_before {
        reasons.push("assertion-not-yet-valid".to_string());
    }
    if now - skew >= not_on_or_after {
        reasons.push("assertion-expired".to_string());
    }
    if assertion.audience != policy.entity_id {
        reasons.push("audience-mismatch".to_string());
    }
    if assertion.recipient != policy.acs_url {
        reasons.push("recipient-mismatch".to_string());
    }
    if assertion.subject.is_empty() {
        reasons.push("subject-missing".to_string());
    }
    for required in &policy.required_attributes {
        if !assertion.attributes.iter().any(|attr| attr.name == *required) {
            reasons.push(format!("attribute-missing:{}", required));
        }
    }
    reasons
}

fn signature_problem(status: SigStatus, required: bool, missing_reason: &str) -> Option<&str> {
    match status {
        SigStatus::Missing if required => Some(missing_reason),
        SigStatus::Missing => None,
        SigStatus::Untrusted => Some("untrusted-signature"),
        SigStatus::Weak => Some("weak-signature-algorithm"),
        SigStatus::Valid => None,
    }
}

fn signature_status(policy: &SpPolicy, response: &SamlResponse, target: &str) -> SigStatus {
    let relevant = response
        .signatures
        .iter()
        .filter(|sig| sig.target_id == target)
        .collect::<Vec<_>>();
    if relevant.is_empty() {
        return SigStatus::Missing;
    }
    let trusted = relevant
        .iter()
        .filter(|sig| policy.trusted_signers.contains(&sig.signer))
        .collect::<Vec<_>>();
    if trusted.is_empty() {
        return SigStatus::Untrusted;
    }
    if trusted
        .iter()
        .any(|sig| policy.allowed_signature_algorithms.contains(&sig.algorithm))
    {
        SigStatus::Valid
    } else {
        SigStatus::Weak
    }
}

fn has_duplicate_ids(response: &SamlResponse) -> bool {
    let mut seen = HashSet::new();
    if !seen.insert(response.id.clone()) {
        return true;
    }
    response
        .assertions
        .iter()
        .any(|assertion| !seen.insert(assertion.id.clone()))
}

fn response_ids(response: &SamlResponse) -> HashSet<String> {
    let mut ids = HashSet::new();
    ids.insert(response.id.clone());
    for assertion in &response.assertions {
        ids.insert(assertion.id.clone());
    }
    ids
}

fn is_weak_algorithm(algorithm: &str) -> bool {
    matches!(algorithm, "rsa-sha1" | "dsa-sha1" | "sha1")
}

fn parse_attrs(
    line: usize,
    tag: &str,
    name: &str,
    self_closing: bool,
    allowed: &[&str],
) -> Result<Vec<(String, String)>, ParseError> {
    let prefix = format!("<{} ", name);
    let suffix = if self_closing { "/>" } else { ">" };
    if !tag.starts_with(&prefix) || !tag.ends_with(suffix) {
        return Err(parse_error(line, "invalid tag"));
    }
    let inner = &tag[prefix.len()..tag.len() - suffix.len()];
    let mut attrs = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    let bytes = inner.as_bytes();
    let mut pos = 0;
    while pos < bytes.len() {
        while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
            pos += 1;
        }
        if pos == bytes.len() {
            break;
        }

        let key_start = pos;
        while pos < bytes.len() && bytes[pos].is_ascii_alphanumeric() {
            pos += 1;
        }
        if key_start == pos || pos >= bytes.len() || bytes[pos] != b'=' {
            return Err(parse_error(line, "invalid attribute"));
        }
        let key = &inner[key_start..pos];
        if !allowed.contains(&key) {
            return Err(parse_error(line, "unknown attribute"));
        }
        if !seen.insert(key.to_string()) {
            return Err(parse_error(line, "duplicate attribute"));
        }

        pos += 1;
        if pos >= bytes.len() || bytes[pos] != b'"' {
            return Err(parse_error(line, "invalid attribute"));
        }
        pos += 1;

        let value_start = pos;
        while pos < bytes.len() && bytes[pos] != b'"' {
            if bytes[pos] == b'<' || bytes[pos] == b'>' {
                return Err(parse_error(line, "invalid attribute value"));
            }
            pos += 1;
        }
        if pos >= bytes.len() {
            return Err(parse_error(line, "invalid attribute"));
        }
        let value = &inner[value_start..pos];
        pos += 1;
        if pos < bytes.len() && !bytes[pos].is_ascii_whitespace() {
            return Err(parse_error(line, "invalid attribute value"));
        }
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

fn opt_attr(attrs: &[(String, String)], key: &str) -> Option<String> {
    attrs
        .iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.clone())
}

fn validate_id(line: usize, id: &str) -> Result<(), ParseError> {
    if id.is_empty()
        || !id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.' | b':'))
    {
        return Err(parse_error(line, "invalid id"));
    }
    Ok(())
}

fn parse_time(value: &str) -> Option<i64> {
    if value.len() != 20 || !value.ends_with('Z') {
        return None;
    }
    if value.as_bytes()[4] != b'-'
        || value.as_bytes()[7] != b'-'
        || value.as_bytes()[10] != b'T'
        || value.as_bytes()[13] != b':'
        || value.as_bytes()[16] != b':'
    {
        return None;
    }
    let year: i32 = value[0..4].parse().ok()?;
    let month: i32 = value[5..7].parse().ok()?;
    let day: i32 = value[8..10].parse().ok()?;
    let hour: i32 = value[11..13].parse().ok()?;
    let minute: i32 = value[14..16].parse().ok()?;
    let second: i32 = value[17..19].parse().ok()?;
    if year < 1
        || !(1..=12).contains(&month)
        || hour > 23
        || minute > 59
        || second > 59
        || day < 1
        || day > days_in_month(year, month)
    {
        return None;
    }
    let days = days_from_civil(year, month, day);
    Some(days * 86_400 + hour as i64 * 3600 + minute as i64 * 60 + second as i64)
}

fn days_from_civil(year: i32, month: i32, day: i32) -> i64 {
    let year = year as i64 - if month <= 2 { 1 } else { 0 };
    let era = if year >= 0 { year } else { year - 399 } / 400;
    let year_of_era = year - era * 400;
    let month = month as i64;
    let day = day as i64;
    let day_of_year = (153 * (month + if month > 2 { -3 } else { 9 }) + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    era * 146_097 + day_of_era - 719_468
}

fn days_in_month(year: i32, month: i32) -> i32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn is_leap(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn denied(reasons: Vec<String>, assertion_id: Option<String>) -> Decision {
    Decision {
        accepted: false,
        subject: None,
        reasons,
        assertion_id,
    }
}

fn parse_error(line: usize, message: &str) -> ParseError {
    ParseError {
        line,
        message: message.to_string(),
    }
}
''')
PY

cd "$APP_DIR"
cargo test --release --locked
