use std::fmt::Write as _;

#[derive(Debug, Clone)]
pub enum Json {
    Null,
    Bool(bool),
    Int(i64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    pub fn as_str(&self) -> Option<&str> {
        if let Json::Str(s) = self {
            Some(s)
        } else {
            None
        }
    }
    pub fn as_arr(&self) -> Option<&[Json]> {
        if let Json::Arr(a) = self {
            Some(a)
        } else {
            None
        }
    }
    pub fn as_obj(&self) -> Option<&[(String, Json)]> {
        if let Json::Obj(o) = self {
            Some(o)
        } else {
            None
        }
    }
    pub fn get(&self, k: &str) -> Option<&Json> {
        self.as_obj()
            .and_then(|o| o.iter().find(|(kk, _)| kk == k).map(|(_, v)| v))
    }
}

pub fn parse(input: &str) -> Result<Json, String> {
    let mut p = Parser {
        bytes: input.as_bytes(),
        pos: 0,
    };
    p.skip_ws();
    let v = p.parse_value()?;
    p.skip_ws();
    if p.pos != p.bytes.len() {
        return Err(format!("trailing content at offset {}", p.pos));
    }
    Ok(v)
}

struct Parser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }
    fn skip_ws(&mut self) {
        while let Some(b) = self.peek() {
            if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' {
                self.pos += 1;
            } else {
                break;
            }
        }
    }
    fn parse_value(&mut self) -> Result<Json, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'"') => self.parse_string().map(Json::Str),
            Some(b'{') => self.parse_object(),
            Some(b'[') => self.parse_array(),
            Some(b't') | Some(b'f') => self.parse_bool(),
            Some(b'n') => self.parse_null(),
            Some(b'-') | Some(b'0'..=b'9') => self.parse_number(),
            Some(b) => Err(format!("unexpected byte 0x{b:02x} at {}", self.pos)),
            None => Err("unexpected end of input".into()),
        }
    }
    fn parse_string(&mut self) -> Result<String, String> {
        if self.peek() != Some(b'"') {
            return Err(format!("expected '\"' at {}", self.pos));
        }
        self.pos += 1;
        let mut out = String::new();
        while let Some(b) = self.peek() {
            self.pos += 1;
            match b {
                b'"' => return Ok(out),
                b'\\' => {
                    let esc = self.peek().ok_or_else(|| "trailing backslash".to_string())?;
                    self.pos += 1;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'n' => out.push('\n'),
                        b't' => out.push('\t'),
                        b'r' => out.push('\r'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'u' => {
                            if self.pos + 4 > self.bytes.len() {
                                return Err("truncated \\u escape".into());
                            }
                            let hex = std::str::from_utf8(&self.bytes[self.pos..self.pos + 4])
                                .map_err(|_| "non-ASCII \\u escape".to_string())?;
                            let n = u32::from_str_radix(hex, 16)
                                .map_err(|_| "bad \\u escape".to_string())?;
                            self.pos += 4;
                            // Handle surrogate pairs for code points beyond the BMP.
                            if (0xD800..=0xDBFF).contains(&n) {
                                if self.bytes.get(self.pos) == Some(&b'\\')
                                    && self.bytes.get(self.pos + 1) == Some(&b'u')
                                {
                                    let hex2 = std::str::from_utf8(
                                        &self.bytes[self.pos + 2..self.pos + 6],
                                    )
                                    .map_err(|_| "non-ASCII \\u escape".to_string())?;
                                    let n2 = u32::from_str_radix(hex2, 16)
                                        .map_err(|_| "bad \\u escape".to_string())?;
                                    self.pos += 6;
                                    let c = 0x10000 + ((n - 0xD800) << 10) + (n2 - 0xDC00);
                                    if let Some(ch) = char::from_u32(c) {
                                        out.push(ch);
                                    } else {
                                        return Err("invalid surrogate pair".into());
                                    }
                                } else {
                                    return Err("lone high surrogate".into());
                                }
                            } else if let Some(c) = char::from_u32(n) {
                                out.push(c);
                            } else {
                                return Err("invalid code point in \\u escape".into());
                            }
                        }
                        _ => return Err(format!("bad escape \\{}", esc as char)),
                    }
                }
                _ => {
                    // Pull in any UTF-8 continuation bytes for this leading byte.
                    if b < 0x80 {
                        out.push(b as char);
                    } else {
                        let len = if b >= 0xF0 {
                            4
                        } else if b >= 0xE0 {
                            3
                        } else {
                            2
                        };
                        let start = self.pos - 1;
                        let end = start + len;
                        if end > self.bytes.len() {
                            return Err("truncated UTF-8 in string".into());
                        }
                        let s = std::str::from_utf8(&self.bytes[start..end])
                            .map_err(|_| "invalid UTF-8 in string".to_string())?;
                        out.push_str(s);
                        self.pos = end;
                    }
                }
            }
        }
        Err("unterminated string".into())
    }
    fn parse_object(&mut self) -> Result<Json, String> {
        self.pos += 1;
        let mut out = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(Json::Obj(out));
        }
        loop {
            self.skip_ws();
            let k = self.parse_string()?;
            self.skip_ws();
            if self.peek() != Some(b':') {
                return Err(format!("expected ':' at {}", self.pos));
            }
            self.pos += 1;
            let v = self.parse_value()?;
            out.push((k, v));
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(Json::Obj(out));
                }
                _ => return Err(format!("expected ',' or '}}' at {}", self.pos)),
            }
        }
    }
    fn parse_array(&mut self) -> Result<Json, String> {
        self.pos += 1;
        let mut out = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(Json::Arr(out));
        }
        loop {
            let v = self.parse_value()?;
            out.push(v);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b']') => {
                    self.pos += 1;
                    return Ok(Json::Arr(out));
                }
                _ => return Err(format!("expected ',' or ']' at {}", self.pos)),
            }
        }
    }
    fn parse_bool(&mut self) -> Result<Json, String> {
        if self.bytes[self.pos..].starts_with(b"true") {
            self.pos += 4;
            Ok(Json::Bool(true))
        } else if self.bytes[self.pos..].starts_with(b"false") {
            self.pos += 5;
            Ok(Json::Bool(false))
        } else {
            Err(format!("invalid boolean at {}", self.pos))
        }
    }
    fn parse_null(&mut self) -> Result<Json, String> {
        if self.bytes[self.pos..].starts_with(b"null") {
            self.pos += 4;
            Ok(Json::Null)
        } else {
            Err(format!("invalid null at {}", self.pos))
        }
    }
    fn parse_number(&mut self) -> Result<Json, String> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        while let Some(b) = self.peek() {
            if b.is_ascii_digit() {
                self.pos += 1;
            } else {
                break;
            }
        }
        let s = std::str::from_utf8(&self.bytes[start..self.pos])
            .map_err(|_| "non-ASCII number".to_string())?;
        let n: i64 = s.parse().map_err(|_| format!("bad integer: {s}"))?;
        Ok(Json::Int(n))
    }
}

pub fn serialize(v: &Json) -> String {
    let mut out = String::new();
    write(v, &mut out);
    out
}

fn write(v: &Json, out: &mut String) {
    match v {
        Json::Null => out.push_str("null"),
        Json::Bool(true) => out.push_str("true"),
        Json::Bool(false) => out.push_str("false"),
        Json::Int(n) => {
            let _ = write!(out, "{}", n);
        }
        Json::Str(s) => write_string(s, out),
        Json::Arr(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write(item, out);
            }
            out.push(']');
        }
        Json::Obj(entries) => {
            out.push('{');
            for (i, (k, val)) in entries.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_string(k, out);
                out.push(':');
                write(val, out);
            }
            out.push('}');
        }
    }
}

fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

pub fn collect(pairs: &[(&str, Json)]) -> Json {
    let entries: Vec<(String, Json)> = pairs
        .iter()
        .map(|(k, v)| ((*k).to_string(), v.clone()))
        .collect();
    Json::Obj(entries)
}
