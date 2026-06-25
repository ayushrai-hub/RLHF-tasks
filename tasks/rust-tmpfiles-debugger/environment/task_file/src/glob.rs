pub(crate) fn has_glob(pattern: &str) -> bool {
    pattern.contains('*') || pattern.contains('?') || pattern.contains('[')
}

pub(crate) fn matches(pattern: &str, path: &str) -> bool {
    if !has_glob(pattern) {
        return pattern == path;
    }
    simple_match(pattern.as_bytes(), path.as_bytes())
}

fn simple_match(pattern: &[u8], text: &[u8]) -> bool {
    if pattern.is_empty() {
        return text.is_empty();
    }
    match pattern[0] {
        b'*' => {
            for i in 0..=text.len() {
                if simple_match(&pattern[1..], &text[i..]) {
                    return true;
                }
            }
            false
        }
        b'?' => !text.is_empty() && simple_match(&pattern[1..], &text[1..]),
        b'[' => false,
        c => !text.is_empty() && c == text[0] && simple_match(&pattern[1..], &text[1..]),
    }
}
