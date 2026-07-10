use std::collections::HashMap;

use crate::adjudicate::record;
use crate::model::{AppealRecord, MatchEvaluation, MatchRecord, Player};

pub fn evaluate_replay(
    target: &MatchRecord,
    appeal: &AppealRecord,
    players: &HashMap<String, Player>,
) -> MatchEvaluation {
    let replay_record = MatchRecord {
        id: target.id.clone(),
        epoch: appeal.replay_epoch,
        format: target.format.clone(),
        home: target.home.clone(),
        away: target.away.clone(),
        signature: appeal.signature.clone(),
        declared: appeal.declared.clone(),
        moves: appeal.moves.clone(),
    };

    let mut evaluation = record::evaluate_record(
        &replay_record,
        players,
        target.epoch,
        "revoked_at_replay_epoch",
    );
    evaluation.status = if evaluation.status == "accepted" {
        "replay_accepted".to_string()
    } else {
        "replay_rejected".to_string()
    };
    evaluation
}
