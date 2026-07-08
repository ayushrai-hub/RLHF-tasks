pub fn pretty(rows: &[serde_json::Value]) -> String {
    let digest = crate::pack_mix_k7::digest_lines(rows);
    let body = rows
        .iter()
        .map(|r| r.to_string())
        .collect::<Vec<_>>()
        .join("\n");
    format!("{digest}\n{body}")
}
