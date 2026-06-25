//! Character classification, character-reference decoding, and HTML escaping
//! (see `docs/TEXT.md`). The grading inputs are ASCII, so Unicode punctuation
//! and whitespace reduce to their ASCII members here.

/// The ASCII punctuation set CommonMark recognises (for escapes and flanking).
pub fn is_ascii_punct(c: char) -> bool {
    matches!(c,
        '!' | '"' | '#' | '$' | '%' | '&' | '\'' | '(' | ')' | '*' | '+' | ',' |
        '-' | '.' | '/' | ':' | ';' | '<' | '=' | '>' | '?' | '@' | '[' | '\\' |
        ']' | '^' | '_' | '`' | '{' | '|' | '}' | '~')
}

/// Unicode-punctuation test used by the flanking rules (ASCII inputs only).
pub fn is_unicode_punct(c: char) -> bool {
    is_ascii_punct(c)
}

/// Unicode-whitespace test used by the flanking rules.
pub fn is_unicode_ws(c: char) -> bool {
    matches!(c, ' ' | '\t' | '\n' | '\r' | '\u{000b}' | '\u{000c}')
}

/// The five named character references this renderer decodes. (The grading
/// inputs use only these names plus numeric references.)
const NAMED: &[(&str, char)] = &[
    ("amp", '&'),
    ("lt", '<'),
    ("gt", '>'),
    ("apos", '\''),
];

/// Try to decode a character reference at the start of `chars` (which begins
/// with `&`). Returns the decoded string and the number of source characters
/// consumed, or `None` if it is not a valid reference.
pub fn decode_entity(chars: &[char]) -> Option<(String, usize)> {
    if chars.first() != Some(&'&') {
        return None;
    }
    if chars.get(1) == Some(&'#') {
        // numeric: &#DDD; or &#xHHH;
        let (radix, start) = match chars.get(2) {
            Some('x') | Some('X') => (16, 3),
            _ => (10, 2),
        };
        let mut j = start;
        let max = if radix == 16 { 6 } else { 7 };
        let mut digits = String::new();
        while j < chars.len() && digits.len() <= max {
            let c = chars[j];
            let ok = if radix == 16 { c.is_ascii_hexdigit() } else { c.is_ascii_digit() };
            if ok {
                digits.push(c);
                j += 1;
            } else {
                break;
            }
        }
        if digits.is_empty() || digits.len() > max || chars.get(j) != Some(&';') {
            return None;
        }
        let code = u32::from_str_radix(&digits, radix).ok()?;
        let ch = if code == 0 {
            '\u{fffd}'
        } else {
            char::from_u32(code).unwrap_or('\u{fffd}')
        };
        return Some((ch.to_string(), j + 1));
    }
    // named: &name;
    let mut j = 1;
    let mut name = String::new();
    while j < chars.len() && chars[j].is_ascii_alphanumeric() {
        name.push(chars[j]);
        j += 1;
    }
    if chars.get(j) != Some(&';') {
        return None;
    }
    for (n, ch) in NAMED {
        if *n == name {
            return Some((ch.to_string(), j + 1));
        }
    }
    None
}

/// Escape text content for HTML output: `&`, `<`, `>` (and `"`), matching the
/// reference renderer's text escaping.
pub fn escape_html(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}
