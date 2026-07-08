use serde_json::Value;

pub fn parse_memory_fields(row: &Value) -> Option<(String, String, String, String, f64, String)> {
    let memory_id = row.get("memory_id")?.as_str()?.to_string();
    let subject = row.get("subject")?.as_str()?.to_string();
    let predicate = row.get("predicate")?.as_str()?.to_string();
    let object = row.get("object")?.as_str()?.to_string();
    if subject.is_empty() || predicate.is_empty() {
        return None;
    }
    let confidence = row.get("confidence")?.as_f64()?;
    if !(0.0..=1.0).contains(&confidence) {
        return None;
    }
    let tier = row.get("tier")?.as_str()?.to_string();
    if !matches!(tier.as_str(), "ephemeral" | "short" | "long") {
        return None;
    }
    Some((memory_id, subject, predicate, object, confidence, tier))
}

pub fn parse_profile_baseline(
    row: &Value,
    subject: &str,
) -> Option<(String, String, String, String, f64, String)> {
    let predicate = row.get("predicate")?.as_str()?.to_string();
    if predicate.is_empty() {
        return None;
    }
    let object = row.get("object")?.as_str()?.to_string();
    let confidence = row.get("confidence")?.as_f64()?;
    if !(0.0..=1.0).contains(&confidence) {
        return None;
    }
    let tier = row.get("tier")?.as_str()?.to_string();
    if !matches!(tier.as_str(), "ephemeral" | "short" | "long") {
        return None;
    }
    let memory_id = format!("profile-{}-{}", subject.replace(':', "-"), predicate);
    Some((
        memory_id,
        subject.to_string(),
        predicate,
        object,
        confidence,
        tier,
    ))
}
