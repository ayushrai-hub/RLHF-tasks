use crate::types::RuleError;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum RuleKind {
    Directory,
    File,
    Symlink,
    Adjust,
    Remove,
    Exclude,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Rule {
    pub kind: RuleKind,
    pub file: String,
    pub line: usize,
    pub path: String,
    pub mode: Option<u32>,
    pub user: Option<String>,
    pub group: Option<String>,
    pub age_hours: Option<u64>,
    pub argument: Option<String>,
}

pub(crate) fn parse_line(file: &str, line: usize, text: &str) -> Result<Option<Rule>, RuleError> {
    let without_comment = text.split('#').next().unwrap_or("").trim();
    if without_comment.is_empty() {
        return Ok(None);
    }
    let mut fields: Vec<&str> = without_comment.split_whitespace().collect();
    if fields.len() < 2 {
        return Err(err(file, line, "not enough fields"));
    }
    while fields.len() < 7 {
        fields.push("-");
    }
    if fields.len() > 7 {
        return Err(err(file, line, "too many fields"));
    }

    let kind = match fields[0] {
        "d" => RuleKind::Directory,
        "f" => RuleKind::File,
        "L" => RuleKind::Symlink,
        "z" => RuleKind::Adjust,
        "r" => RuleKind::Remove,
        "x" => RuleKind::Exclude,
        _ => return Err(err(file, line, "unknown rule type")),
    };

    let path = fields[1].to_string();
    let mode = parse_mode(fields[2]).map_err(|m| err(file, line, m))?;
    let user = none_dash(fields[3]);
    let group = none_dash(fields[4]);
    let age_hours = parse_age(fields[5]).map_err(|m| err(file, line, m))?;
    let argument = none_dash(fields[6]);

    Ok(Some(Rule {
        kind,
        file: file.to_string(),
        line,
        path,
        mode,
        user,
        group,
        age_hours,
        argument,
    }))
}

fn none_dash(s: &str) -> Option<String> {
    if s == "-" {
        None
    } else {
        Some(s.to_string())
    }
}

fn parse_mode(s: &str) -> Result<Option<u32>, &'static str> {
    if s == "-" {
        return Ok(None);
    }
    u32::from_str_radix(s, 8)
        .map(Some)
        .map_err(|_| "invalid mode")
}

fn parse_age(s: &str) -> Result<Option<u64>, &'static str> {
    if s == "-" || s == "0" {
        return Ok(Some(0));
    }
    if let Some(days) = s.strip_suffix('d') {
        return days
            .parse::<u64>()
            .map(|d| Some(d * 24))
            .map_err(|_| "invalid age");
    }
    if let Some(hours) = s.strip_suffix('h') {
        return hours.parse::<u64>().map(Some).map_err(|_| "invalid age");
    }
    Err("invalid age")
}

fn err(file: &str, line: usize, message: impl Into<String>) -> RuleError {
    RuleError {
        file: file.to_string(),
        line,
        message: message.into(),
    }
}
