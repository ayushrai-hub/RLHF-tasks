pub fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

pub fn string_array(values: &[String]) -> String {
    let mut out = String::from("[");
    for (i, value) in values.iter().enumerate() {
        if i > 0 { out.push(','); }
        out.push('"');
        out.push_str(&esc(value));
        out.push('"');
    }
    out.push(']');
    out
}
