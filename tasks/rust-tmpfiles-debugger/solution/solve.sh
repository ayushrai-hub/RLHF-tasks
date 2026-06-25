#!/bin/bash
set -euo pipefail

SRC=/app/task_file/src
mkdir -p /app/task_file/output

cat > "$SRC/glob.rs" <<'RUST_EOF'
pub(crate) fn has_glob(pattern: &str) -> bool {
    pattern.contains('*') || pattern.contains('?') || pattern.contains('[')
}

pub(crate) fn matches(pattern: &str, path: &str) -> bool {
    if !has_glob(pattern) {
        return pattern == path;
    }
    let p = pattern.as_bytes();
    let t = path.as_bytes();
    let mut memo = vec![vec![None; t.len() + 1]; p.len() + 1];
    match_from(p, t, 0, 0, &mut memo)
}

fn match_from(
    pattern: &[u8],
    text: &[u8],
    pi: usize,
    ti: usize,
    memo: &mut [Vec<Option<bool>>],
) -> bool {
    if let Some(v) = memo[pi][ti] {
        return v;
    }
    let ans = if pi == pattern.len() {
        ti == text.len()
    } else {
        match pattern[pi] {
            b'*' => {
                let mut ok = match_from(pattern, text, pi + 1, ti, memo);
                let mut nt = ti;
                while !ok && nt < text.len() {
                    nt += 1;
                    ok = match_from(pattern, text, pi + 1, nt, memo);
                }
                ok
            }
            b'?' => ti < text.len() && match_from(pattern, text, pi + 1, ti + 1, memo),
            b'[' => {
                if ti >= text.len() {
                    false
                } else if let Some((ok, next_pi)) = class_match(pattern, pi, text[ti]) {
                    ok && match_from(pattern, text, next_pi, ti + 1, memo)
                } else {
                    ti < text.len()
                        && pattern[pi] == text[ti]
                        && match_from(pattern, text, pi + 1, ti + 1, memo)
                }
            }
            c => ti < text.len() && c == text[ti] && match_from(pattern, text, pi + 1, ti + 1, memo),
        }
    };
    memo[pi][ti] = Some(ans);
    ans
}

fn class_match(pattern: &[u8], open: usize, c: u8) -> Option<(bool, usize)> {
    let mut i = open + 1;
    let mut ok = false;
    let mut saw = false;
    while i < pattern.len() {
        if pattern[i] == b']' && saw {
            return Some((ok, i + 1));
        }
        saw = true;
        if i + 2 < pattern.len() && pattern[i + 1] == b'-' && pattern[i + 2] != b']' {
            let lo = pattern[i];
            let hi = pattern[i + 2];
            if lo <= c && c <= hi {
                ok = true;
            }
            i += 3;
        } else {
            if pattern[i] == c {
                ok = true;
            }
            i += 1;
        }
    }
    None
}
RUST_EOF

cat > "$SRC/parser.rs" <<'RUST_EOF'
use crate::types::RuleError;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum RuleKind {
    Directory,
    File,
    Symlink,
    Adjust,
    Remove,
    RecursiveRemove,
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
    let mut fields = split_fields(text).map_err(|m| err(file, line, m))?;
    if fields.is_empty() {
        return Ok(None);
    }
    if fields.len() < 2 {
        return Err(err(file, line, "not enough fields"));
    }
    while fields.len() < 7 {
        fields.push("-".to_string());
    }
    if fields.len() > 7 {
        return Err(err(file, line, "too many fields"));
    }

    let kind = match fields[0].as_str() {
        "d" => RuleKind::Directory,
        "f" => RuleKind::File,
        "L" => RuleKind::Symlink,
        "z" => RuleKind::Adjust,
        "r" => RuleKind::Remove,
        "R" => RuleKind::RecursiveRemove,
        "x" => RuleKind::Exclude,
        _ => return Err(err(file, line, "unknown rule type")),
    };

    let path = normalize_path(&fields[1]).map_err(|m| err(file, line, m))?;
    let mode = parse_mode(&fields[2]).map_err(|m| err(file, line, m))?;
    let user = parse_identity(&fields[3]).map_err(|m| err(file, line, m))?;
    let group = parse_identity(&fields[4]).map_err(|m| err(file, line, m))?;
    let age_hours = parse_age(&fields[5]).map_err(|m| err(file, line, m))?;
    let argument = none_dash(&fields[6]);
    if matches!(kind, RuleKind::Symlink) && argument.is_none() {
        return Err(err(file, line, "symlink target is required"));
    }

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

pub(crate) fn normalize_path(path: &str) -> Result<String, &'static str> {
    if !path.starts_with('/') {
        return Err("path must be absolute");
    }
    let mut parts: Vec<&str> = Vec::new();
    for part in path.split('/') {
        match part {
            "" | "." => {}
            ".." => return Err("path must not contain '..'"),
            other => parts.push(other),
        }
    }
    if parts.is_empty() {
        Ok("/".to_string())
    } else {
        Ok(format!("/{}", parts.join("/")))
    }
}

fn split_fields(text: &str) -> Result<Vec<String>, &'static str> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut quote: Option<char> = None;
    let mut in_field = false;
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        if let Some(q) = quote {
            if ch == '\\' {
                if let Some(next) = chars.next() {
                    cur.push(next);
                } else {
                    cur.push('\\');
                }
            } else if ch == q {
                quote = None;
            } else {
                cur.push(ch);
            }
            in_field = true;
            continue;
        }
        match ch {
            '#' => break,
            '\'' | '"' => {
                quote = Some(ch);
                in_field = true;
            }
            '\\' => {
                if let Some(next) = chars.next() {
                    cur.push(next);
                } else {
                    cur.push('\\');
                }
                in_field = true;
            }
            c if c.is_whitespace() => {
                if in_field {
                    out.push(std::mem::take(&mut cur));
                    in_field = false;
                }
            }
            c => {
                cur.push(c);
                in_field = true;
            }
        }
    }
    if quote.is_some() {
        return Err("unterminated quote");
    }
    if in_field {
        out.push(cur);
    }
    Ok(out)
}

fn none_dash(s: &str) -> Option<String> {
    if s == "-" {
        None
    } else {
        Some(s.to_string())
    }
}

fn parse_identity(s: &str) -> Result<Option<String>, &'static str> {
    if s == "-" {
        Ok(None)
    } else if s.is_empty() {
        Err("empty identity field")
    } else {
        Ok(Some(s.to_string()))
    }
}

fn parse_mode(s: &str) -> Result<Option<u32>, &'static str> {
    if s == "-" {
        return Ok(None);
    }
    if !(s.len() == 3 || s.len() == 4) || !s.bytes().all(|b| (b'0'..=b'7').contains(&b)) {
        return Err("invalid mode");
    }
    u32::from_str_radix(s, 8)
        .map(Some)
        .map_err(|_| "invalid mode")
}

fn parse_age(s: &str) -> Result<Option<u64>, &'static str> {
    if s == "-" || s == "0" {
        return Ok(Some(0));
    }
    let mut total = 0u64;
    let mut digits = String::new();
    let mut saw_part = false;
    for ch in s.chars() {
        if ch.is_ascii_digit() {
            digits.push(ch);
            continue;
        }
        let mult = match ch {
            'h' => 1,
            'd' => 24,
            'w' => 24 * 7,
            _ => return Err("invalid age"),
        };
        if digits.is_empty() {
            return Err("invalid age");
        }
        let amount = digits.parse::<u64>().map_err(|_| "invalid age")?;
        if amount == 0 {
            return Err("invalid age");
        }
        total = total.saturating_add(amount.saturating_mul(mult));
        digits.clear();
        saw_part = true;
    }
    if !digits.is_empty() || !saw_part {
        return Err("invalid age");
    }
    Ok(Some(total))
}

fn err(file: &str, line: usize, message: impl Into<String>) -> RuleError {
    RuleError {
        file: file.to_string(),
        line,
        message: message.into(),
    }
}
RUST_EOF

cat > "$SRC/plan.rs" <<'RUST_EOF'
use crate::glob;
use crate::parser::{normalize_path, parse_line, Rule, RuleKind};
use crate::types::{Action, ConfigFile, EntryKind, FsEntry, Plan, RuleError, TmpfilesConfig};
use std::collections::{BTreeMap, HashSet};

impl TmpfilesConfig {
    pub fn compile_plan(&self) -> Plan {
        let mut rules = Vec::new();
        let mut errors = Vec::new();
        let files = selected_files(&self.files);

        for file in &files {
            for (idx, line) in file.text.lines().enumerate() {
                match parse_line(&file.name, idx + 1, line) {
                    Ok(Some(rule)) => rules.push(rule),
                    Ok(None) => {}
                    Err(e) => errors.push(e),
                }
            }
        }
        errors.sort_by(|a, b| a.file.cmp(&b.file).then(a.line.cmp(&b.line)));

        let entries = normalized_entries(&self.entries);
        let by_path: BTreeMap<String, FsEntry> =
            entries.iter().map(|e| (e.path.clone(), e.clone())).collect();

        let mut protection = Protection::default();
        for rule in rules.iter().filter(|r| matches!(r.kind, RuleKind::Exclude)) {
            for ent in matching_entries(&entries, &rule.path) {
                protection.exact.insert(ent.path.clone());
                if ent.kind == EntryKind::Directory {
                    protection.dirs.push(ent.path.clone());
                }
            }
        }
        protection.dirs.sort();
        protection.dirs.dedup();

        let mut actions = Vec::new();
        let mut claimed = HashSet::new();
        for rule in &rules {
            match rule.kind {
                RuleKind::Directory => claim_ensure(
                    &mut actions,
                    &mut errors,
                    &mut claimed,
                    &by_path,
                    rule,
                    EntryKind::Directory,
                    None,
                ),
                RuleKind::File => claim_ensure(
                    &mut actions,
                    &mut errors,
                    &mut claimed,
                    &by_path,
                    rule,
                    EntryKind::File,
                    rule.argument.clone(),
                ),
                RuleKind::Symlink => claim_ensure(
                    &mut actions,
                    &mut errors,
                    &mut claimed,
                    &by_path,
                    rule,
                    EntryKind::Symlink,
                    rule.argument.clone(),
                ),
                RuleKind::Adjust => {
                    for ent in matching_entries(&entries, &rule.path) {
                        if claimed.insert(ent.path.clone()) {
                            actions.push(Action::Adjust {
                                path: ent.path.clone(),
                                mode: rule.mode,
                                user: rule.user.clone(),
                                group: rule.group.clone(),
                            });
                        }
                    }
                }
                RuleKind::Remove | RuleKind::RecursiveRemove | RuleKind::Exclude => {}
            }
        }

        let mut removed = HashSet::new();
        for rule in rules
            .iter()
            .filter(|r| matches!(r.kind, RuleKind::Remove | RuleKind::RecursiveRemove))
        {
            match rule.kind {
                RuleKind::Remove => {
                    for ent in matching_entries(&entries, &rule.path) {
                        if protection.contains(&ent.path) || !age_ok(&ent, rule) {
                            continue;
                        }
                        if removed.insert(ent.path.clone()) {
                            actions.push(Action::Remove {
                                path: ent.path.clone(),
                            });
                        }
                    }
                }
                RuleKind::RecursiveRemove => {
                    let mut candidates = recursive_candidates(&entries, rule);
                    candidates.sort_by(|a, b| {
                        path_depth(&a.path)
                            .cmp(&path_depth(&b.path))
                            .then(a.path.cmp(&b.path))
                    });
                    for ent in candidates {
                        if removed_ancestor(&removed, &ent.path) {
                            continue;
                        }
                        if protection.contains(&ent.path) || !age_ok(&ent, rule) {
                            continue;
                        }
                        if ent.kind == EntryKind::Directory
                            && has_blocking_descendant(&entries, &ent.path, rule, &protection)
                        {
                            continue;
                        }
                        if removed.insert(ent.path.clone()) {
                            actions.push(Action::Remove {
                                path: ent.path.clone(),
                            });
                        }
                    }
                }
                _ => {}
            }
        }

        actions.sort_by(action_cmp_key);
        errors.sort_by(|a, b| a.file.cmp(&b.file).then(a.line.cmp(&b.line)));
        Plan { actions, errors }
    }
}

fn selected_files(files: &[ConfigFile]) -> Vec<ConfigFile> {
    let mut selected: BTreeMap<String, (u8, String, ConfigFile)> = BTreeMap::new();
    for file in files {
        let (base, priority) = basename_and_priority(&file.name);
        match selected.get(&base) {
            Some((old_priority, old_name, _))
                if *old_priority < priority
                    || (*old_priority == priority && old_name <= &file.name) => {}
            _ => {
                selected.insert(base, (priority, file.name.clone(), file.clone()));
            }
        }
    }
    selected.into_values().map(|(_, _, file)| file).collect()
}

fn basename_and_priority(name: &str) -> (String, u8) {
    let trimmed = name.trim_end_matches('/');
    let base = trimmed
        .rsplit('/')
        .next()
        .filter(|s| !s.is_empty())
        .unwrap_or(trimmed)
        .to_string();
    let priority = if trimmed.starts_with("/etc/tmpfiles.d/") {
        0
    } else if trimmed.starts_with("/run/tmpfiles.d/") {
        1
    } else if trimmed.starts_with("/usr/local/lib/tmpfiles.d/") {
        2
    } else if trimmed.starts_with("/usr/lib/tmpfiles.d/") {
        3
    } else {
        4
    };
    (base, priority)
}

fn normalized_entries(entries: &[FsEntry]) -> Vec<FsEntry> {
    let mut by_path: BTreeMap<String, FsEntry> = BTreeMap::new();
    for ent in entries {
        if let Ok(path) = normalize_path(&ent.path) {
            by_path.entry(path.clone()).or_insert_with(|| {
                let mut copy = ent.clone();
                copy.path = path;
                copy
            });
        }
    }
    by_path.into_values().collect()
}

fn claim_ensure(
    actions: &mut Vec<Action>,
    errors: &mut Vec<RuleError>,
    claimed: &mut HashSet<String>,
    entries: &BTreeMap<String, FsEntry>,
    rule: &Rule,
    kind: EntryKind,
    argument: Option<String>,
) {
    if !claimed.insert(rule.path.clone()) {
        return;
    }
    if let Some(existing) = entries.get(&rule.path) {
        if existing.kind != kind {
            errors.push(RuleError {
                file: rule.file.clone(),
                line: rule.line,
                message: "existing path has the wrong kind".to_string(),
            });
        } else if rule.mode.is_some() || rule.user.is_some() || rule.group.is_some() {
            actions.push(Action::Adjust {
                path: rule.path.clone(),
                mode: rule.mode,
                user: rule.user.clone(),
                group: rule.group.clone(),
            });
        }
    } else {
        actions.push(Action::Create {
            path: rule.path.clone(),
            kind,
            mode: rule.mode,
            user: rule.user.clone(),
            group: rule.group.clone(),
            argument,
        });
    }
}

fn matching_entries<'a>(entries: &'a [FsEntry], pattern: &str) -> Vec<&'a FsEntry> {
    let mut matches: Vec<&FsEntry> = entries
        .iter()
        .filter(|e| glob::matches(pattern, &e.path))
        .collect();
    matches.sort_by(|a, b| a.path.cmp(&b.path));
    matches
}

fn age_ok(ent: &FsEntry, rule: &Rule) -> bool {
    match rule.age_hours {
        Some(hours) => ent.mtime_hours_ago >= hours,
        None => true,
    }
}

fn recursive_candidates(entries: &[FsEntry], rule: &Rule) -> Vec<FsEntry> {
    let mut out: BTreeMap<String, FsEntry> = BTreeMap::new();
    let roots = matching_entries(entries, &rule.path);
    for root in roots {
        out.insert(root.path.clone(), root.clone());
        if root.kind == EntryKind::Directory {
            for ent in entries.iter().filter(|e| is_descendant(&e.path, &root.path)) {
                out.insert(ent.path.clone(), ent.clone());
            }
        }
    }
    out.into_values().collect()
}

fn has_blocking_descendant(
    entries: &[FsEntry],
    root: &str,
    rule: &Rule,
    protection: &Protection,
) -> bool {
    entries
        .iter()
        .filter(|e| is_descendant(&e.path, root))
        .any(|e| protection.contains(&e.path) || !age_ok(e, rule))
}

fn removed_ancestor(removed: &HashSet<String>, path: &str) -> bool {
    removed.iter().any(|root| is_descendant(path, root))
}

fn is_descendant(path: &str, root: &str) -> bool {
    if root == "/" {
        path != "/"
    } else {
        path.len() > root.len()
            && path.starts_with(root)
            && path.as_bytes().get(root.len()) == Some(&b'/')
    }
}

fn path_depth(path: &str) -> usize {
    path.split('/').filter(|p| !p.is_empty()).count()
}

#[derive(Default)]
struct Protection {
    exact: HashSet<String>,
    dirs: Vec<String>,
}

impl Protection {
    fn contains(&self, path: &str) -> bool {
        self.exact.contains(path) || self.dirs.iter().any(|root| is_descendant(path, root))
    }
}

fn action_cmp_key(a: &Action, b: &Action) -> std::cmp::Ordering {
    action_path(a)
        .cmp(action_path(b))
        .then(action_kind_rank(a).cmp(&action_kind_rank(b)))
}

fn action_path(a: &Action) -> &String {
    match a {
        Action::Create { path, .. } => path,
        Action::Adjust { path, .. } => path,
        Action::Remove { path } => path,
    }
}

fn action_kind_rank(a: &Action) -> u8 {
    match a {
        Action::Create { .. } => 0,
        Action::Adjust { .. } => 1,
        Action::Remove { .. } => 2,
    }
}
RUST_EOF

cat > /app/task_file/output/fix_report.json <<'JSON_EOF'
{
  "bugs_fixed": [
    {"file": "src/plan.rs", "method": "selected_files", "description": "Apply tmpfiles.d basename masking by root priority before processing selected files by basename."},
    {"file": "src/parser.rs", "method": "split_fields", "description": "Parse quoted fields, escapes, and comments without splitting spaces inside quoted values."},
    {"file": "src/parser.rs", "method": "normalize_path", "description": "Normalize absolute paths and reject relative paths or paths containing parent traversal."},
    {"file": "src/parser.rs", "method": "parse_mode", "description": "Validate mode fields as exactly three or four octal digits."},
    {"file": "src/parser.rs", "method": "parse_age", "description": "Support inclusive compound hour, day, week, zero, and dash age values for cleanup rules."},
    {"file": "src/glob.rs", "method": "matches", "description": "Implement full-pattern glob matching for star, question mark, and bracket classes."},
    {"file": "src/plan.rs", "method": "TmpfilesConfig::compile_plan:excludes", "description": "Collect every exclude rule before cleanup so later excludes still protect matching paths."},
    {"file": "src/plan.rs", "method": "normalized_entries", "description": "Normalize and de-duplicate filesystem snapshot entries while preserving the first caller-provided entry."},
    {"file": "src/plan.rs", "method": "claim_ensure", "description": "Treat create rules as ensure rules that adjust matching existing paths and error on wrong-kind paths."},
    {"file": "src/plan.rs", "method": "recursive_candidates", "description": "Implement recursive cleanup over matched directories and descendants without duplicate removals."},
    {"file": "src/plan.rs", "method": "has_blocking_descendant", "description": "Prevent recursive parent removals that would delete protected or too-young descendants."},
    {"file": "src/plan.rs", "method": "action_cmp_key", "description": "Sort final actions deterministically by normalized path and action kind."}
  ]
}
JSON_EOF

cd /app/task_file
cargo test --release >/tmp/tmpfiles_audit_solve.log
echo "solve.sh complete"
