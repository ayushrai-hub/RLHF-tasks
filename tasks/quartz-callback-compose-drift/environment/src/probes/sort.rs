pub fn run() -> String {
    let raw = std::env::var("TB_ORDER").unwrap_or_default();
    let mut items: Vec<(usize, usize, String)> = Vec::new();
    for (idx, part) in raw.split(';').filter(|s| !s.is_empty()).enumerate() {
        if let Some((name, lo)) = part.split_once(':') {
            items.push((
                lo.parse().unwrap_or(0),
                crate::qz::n6::q6::tiebreak_index(idx),
                name.to_string(),
            ));
        }
    }
    crate::qz::n1::q1::sort_callbacks(&mut items);
    items
        .iter()
        .map(|(_, _, n)| n.as_str())
        .collect::<Vec<_>>()
        .join(",")
}
