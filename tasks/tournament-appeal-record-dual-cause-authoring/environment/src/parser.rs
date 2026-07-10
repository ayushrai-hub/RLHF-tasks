use std::collections::HashMap;

use crate::model::{AppealRecord, Case, MatchRecord, Player};

pub fn parse_cases(raw: &str) -> Result<Vec<Case>, String> {
    let mut cases: Vec<Case> = Vec::new();
    let mut current: Option<Case> = None;

    for (index, raw_line) in raw.lines().enumerate() {
        let line_no = index + 1;
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut parts = line.split_whitespace();
        let kind = parts.next().unwrap_or("");
        match kind {
            "case" => {
                if current.is_some() {
                    return Err(format!("line {}: nested case is not allowed", line_no));
                }
                let id = parts
                    .next()
                    .ok_or_else(|| format!("line {}: case id is required", line_no))?;
                current = Some(Case {
                    id: id.to_string(),
                    players: Vec::new(),
                    matches: Vec::new(),
                    appeals: Vec::new(),
                });
            }
            "endcase" => {
                let finished = current
                    .take()
                    .ok_or_else(|| format!("line {}: endcase without case", line_no))?;
                cases.push(finished);
            }
            "player" => {
                let case = current
                    .as_mut()
                    .ok_or_else(|| format!("line {}: player outside case", line_no))?;
                let id = parts
                    .next()
                    .ok_or_else(|| format!("line {}: player id is required", line_no))?;
                let kv = collect_kv(parts, line_no)?;
                case.players.push(Player {
                    id: id.to_string(),
                    key: required(&kv, "key", line_no)?.to_string(),
                    registered: parse_u32(required(&kv, "registered", line_no)?, "registered", line_no)?,
                    revoked: parse_revoked(required(&kv, "revoked", line_no)?, line_no)?,
                });
            }
            "match" => {
                let case = current
                    .as_mut()
                    .ok_or_else(|| format!("line {}: match outside case", line_no))?;
                let id = parts
                    .next()
                    .ok_or_else(|| format!("line {}: match id is required", line_no))?;
                let kv = collect_kv(parts, line_no)?;
                case.matches.push(MatchRecord {
                    id: id.to_string(),
                    epoch: parse_u32(required(&kv, "epoch", line_no)?, "epoch", line_no)?,
                    format: required(&kv, "format", line_no)?.to_string(),
                    home: required(&kv, "home", line_no)?.to_string(),
                    away: required(&kv, "away", line_no)?.to_string(),
                    signature: required(&kv, "sig", line_no)?.to_string(),
                    declared: required(&kv, "declared", line_no)?.to_string(),
                    moves: split_moves(required(&kv, "moves", line_no)?),
                });
            }
            "appeal" => {
                let case = current
                    .as_mut()
                    .ok_or_else(|| format!("line {}: appeal outside case", line_no))?;
                let id = parts
                    .next()
                    .ok_or_else(|| format!("line {}: appeal id is required", line_no))?;
                let kv = collect_kv(parts, line_no)?;
                case.appeals.push(AppealRecord {
                    id: id.to_string(),
                    target: required(&kv, "target", line_no)?.to_string(),
                    epoch: parse_u32(required(&kv, "epoch", line_no)?, "epoch", line_no)?,
                    replay_epoch: parse_u32(required(&kv, "replay_epoch", line_no)?, "replay_epoch", line_no)?,
                    signature: required(&kv, "sig", line_no)?.to_string(),
                    declared: required(&kv, "declared", line_no)?.to_string(),
                    moves: split_moves(required(&kv, "moves", line_no)?),
                });
            }
            other => return Err(format!("line {}: unknown record kind {}", line_no, other)),
        }
    }

    if current.is_some() {
        return Err("unterminated case at end of file".to_string());
    }
    if cases.is_empty() {
        return Err("case file contains no cases".to_string());
    }
    Ok(cases)
}

fn collect_kv<'a, I>(parts: I, line_no: usize) -> Result<HashMap<String, String>, String>
where
    I: Iterator<Item = &'a str>,
{
    let mut kv = HashMap::new();
    for part in parts {
        let (key, value) = part
            .split_once('=')
            .ok_or_else(|| format!("line {}: expected key=value token, got {}", line_no, part))?;
        if key.is_empty() || value.is_empty() {
            return Err(format!("line {}: empty key or value in {}", line_no, part));
        }
        kv.insert(key.to_string(), value.to_string());
    }
    Ok(kv)
}

fn required<'a>(kv: &'a HashMap<String, String>, key: &str, line_no: usize) -> Result<&'a str, String> {
    kv.get(key)
        .map(String::as_str)
        .ok_or_else(|| format!("line {}: missing {}", line_no, key))
}

fn parse_u32(value: &str, field: &str, line_no: usize) -> Result<u32, String> {
    value
        .parse::<u32>()
        .map_err(|_| format!("line {}: {} must be an unsigned integer", line_no, field))
}

fn parse_revoked(value: &str, line_no: usize) -> Result<Option<u32>, String> {
    if value == "none" {
        Ok(None)
    } else {
        Ok(Some(parse_u32(value, "revoked", line_no)?))
    }
}

fn split_moves(value: &str) -> Vec<String> {
    if value == "-" {
        return Vec::new();
    }
    value
        .split(',')
        .filter(|item| !item.trim().is_empty())
        .map(|item| item.trim().to_string())
        .collect()
}
