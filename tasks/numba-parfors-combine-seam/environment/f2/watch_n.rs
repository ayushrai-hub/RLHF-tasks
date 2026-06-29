pub fn inspect_row(note: &str) -> (String, String, u32, i32) {
    let mut principal = String::new();
    let mut label = String::new();
    let mut gen = 0u32;
    let mut action = 0i32;
    for item in note.split_whitespace() {
        if let Some((k, v)) = item.split_once('=') {
            match k {
                "principal" => principal = v.to_string(),
                "label" => label = v.to_string(),
                "gen" => gen = v.parse().unwrap_or(0),
                "action" => action = v.parse().unwrap_or(0),
                _ => {}
            }
        }
    }
    (principal, label, gen, action)
}
