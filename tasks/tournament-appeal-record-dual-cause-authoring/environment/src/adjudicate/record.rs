use std::collections::HashMap;

use crate::model::{MatchEvaluation, MatchRecord, MoveTrace, Player};

const LEGAL_ANNOTATIONS: [&str; 4] = ["clean", "tempo", "appeal", "legacy"];

pub fn evaluate_record(
    record: &MatchRecord,
    players: &HashMap<String, Player>,
    eligibility_epoch: u32,
    revoked_label: &str,
) -> MatchEvaluation {
    let mut errors: Vec<String> = Vec::new();

    let home_player = players.get(&record.home);
    let away_player = players.get(&record.away);
    if home_player.is_none() {
        errors.push(format!("unknown_player:{}", record.home));
    }
    if away_player.is_none() {
        errors.push(format!("unknown_player:{}", record.away));
    }

    if let Some(player) = home_player {
        if !eligible_at(player, eligibility_epoch) {
            errors.push(format!("{}:{}", revoked_label, player.id));
        }
    }
    if let Some(player) = away_player {
        if !eligible_at(player, eligibility_epoch) {
            errors.push(format!("{}:{}", revoked_label, player.id));
        }
    }

    match expected_signature(record, players) {
        Some(expected) => {
            if record.signature != expected {
                errors.push("bad_signature".to_string());
            }
        }
        None => errors.push(format!("unsupported_signature_format:{}", record.format)),
    }

    let mut score_home = 0_u32;
    let mut score_away = 0_u32;
    let mut traces: Vec<MoveTrace> = Vec::new();
    for token in &record.moves {
        let trace = parse_move_token(token);
        if trace.legal {
            if trace.actor == "home" {
                score_home += trace.points;
            } else if trace.actor == "away" {
                score_away += trace.points;
            }
        } else {
            errors.push(trace.reason.clone());
        }
        traces.push(trace);
    }

    let computed_winner = if score_home > score_away {
        Some(record.home.clone())
    } else if score_away > score_home {
        Some(record.away.clone())
    } else {
        None
    };

    match declared_winner(record) {
        Ok(declared) => {
            if declared != computed_winner {
                errors.push("declared_result_mismatch".to_string());
            }
        }
        Err(message) => errors.push(message),
    }

    let status = if errors.is_empty() { "accepted" } else { "rejected" };
    MatchEvaluation {
        id: record.id.clone(),
        home: record.home.clone(),
        away: record.away.clone(),
        status: status.to_string(),
        epoch_used: eligibility_epoch,
        winner: if errors.is_empty() { computed_winner } else { None },
        score_home,
        score_away,
        errors,
        move_trace: traces,
    }
}

fn eligible_at(player: &Player, epoch: u32) -> bool {
    if epoch < player.registered {
        return false;
    }
    match player.revoked {
        Some(revoked_epoch) => epoch < revoked_epoch,
        None => true,
    }
}

fn expected_signature(record: &MatchRecord, players: &HashMap<String, Player>) -> Option<String> {
    let prefix = match record.format.as_str() {
        "v1" => "LEGACY",
        "v2" => "SIG",
        _ => return None,
    };
    let home = players.get(&record.home)?;
    let away = players.get(&record.away)?;
    Some(format!(
        "{}:{}:{}:{}:{}:{}:{}",
        prefix, record.id, record.home, record.away, record.epoch, home.key, away.key
    ))
}

fn declared_winner(record: &MatchRecord) -> Result<Option<String>, String> {
    match record.declared.as_str() {
        "home" => Ok(Some(record.home.clone())),
        "away" => Ok(Some(record.away.clone())),
        "draw" => Ok(None),
        other => Err(format!("invalid_declared_result:{}", other)),
    }
}

fn parse_move_token(raw: &str) -> MoveTrace {
    let mut reason = "ok".to_string();
    let mut legal = true;
    let mut actor = "unknown".to_string();
    let mut points = 0_u32;
    let mut annotation = String::new();

    let chars: Vec<char> = raw.chars().collect();
    if chars.len() < 5 {
        return invalid_trace(raw, "malformed_move");
    }

    match chars[0] {
        'H' => actor = "home".to_string(),
        'A' => actor = "away".to_string(),
        _ => {
            legal = false;
            reason = format!("invalid_actor:{}", chars[0]);
        }
    }

    match chars.get(1).and_then(|ch| ch.to_digit(10)) {
        Some(value @ 1..=2) => points = value,
        Some(value) => {
            legal = false;
            reason = format!("invalid_points:{}", value);
        }
        None => {
            legal = false;
            reason = "invalid_points".to_string();
        }
    }

    let bracket_start = raw.find('[');
    let bracket_end = raw.rfind(']');
    match (bracket_start, bracket_end) {
        (Some(start), Some(end)) if end > start && end == raw.len() - 1 => {
            annotation = raw[start + 1..end].to_string();
            match canonical_annotation(&annotation) {
                Some(canonical) => annotation = canonical,
                None => {
                    legal = false;
                    reason = format!("illegal_annotation:{}", annotation);
                }
            }
        }
        _ => {
            legal = false;
            reason = "missing_annotation".to_string();
        }
    }

    MoveTrace {
        raw: raw.to_string(),
        actor,
        points,
        annotation,
        legal,
        reason,
    }
}

fn invalid_trace(raw: &str, reason: &str) -> MoveTrace {
    MoveTrace {
        raw: raw.to_string(),
        actor: "unknown".to_string(),
        points: 0,
        annotation: String::new(),
        legal: false,
        reason: reason.to_string(),
    }
}

fn canonical_annotation(raw: &str) -> Option<String> {
    let lowered = raw.trim().to_ascii_lowercase();
    let alias = lowered.split('-').next().unwrap_or("");
    if LEGAL_ANNOTATIONS.contains(&alias) {
        Some(alias.to_string())
    } else {
        None
    }
}
